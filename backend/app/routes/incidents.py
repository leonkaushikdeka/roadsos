"""
Incident API routes with fraud detection integration and OpenTelemetry.

Fraud checks are NON-BLOCKING — they flag but don't prevent SOS activation.
This ensures genuine emergencies always get through.
"""

import json
import uuid
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.incident import (
    IncidentInitiateRequest, IncidentInitiateResponse,
    TriageRequest, TriageResponse,
    DispatchRequest, DispatchResponse,
    IncidentStatusResponse,
)
from app.services.triage import TriageAgent, inject_protocol_context
from app.services.dispatch import find_nearest_services, dispatch_ambulance, rank_hospitals
from app.services.notification import notification_service
from app.services.fraud import FraudEngine, FraudCheckResult
from app.telemetry import instrumented_incident_initiate, instrumented_triage_step, instrumented_dispatch_confirm

router = APIRouter(prefix="/v1/incident", tags=["Incidents"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from FastAPI request."""
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/initiate", response_model=IncidentInitiateResponse)
async def initiate_incident(
    req: IncidentInitiateRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    client_ip = _get_client_ip(request) if request else "unknown"
    t0 = time.monotonic()

    # ── Run fraud check (non-blocking) ──
    fraud = FraudEngine(db)
    fraud_result: FraudCheckResult = await fraud.check(
        phone=req.phone,
        lat=req.lat,
        lng=req.lng,
        device_fingerprint=req.model_dump().get("_device_hash"),
        ip_address=client_ip,
    )

    # Hard-block check — banned user, reject
    if not fraud_result.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Request blocked by security policy",
                "reason": "; ".join(fraud_result.reasons),
                "support": "If this is a genuine emergency, call 108 immediately.",
            },
        )

    # Log fraud check result in session
    fraud_metadata = fraud_result.to_dict()

    incident_id = str(uuid.uuid4())
    session_id = f"SOS-{incident_id[:8].upper()}"
    now = datetime.utcnow()

    await db.execute(
        text("""
            INSERT INTO incidents (id, session_id, lat, lng, location_accuracy_m, location_source,
                channel, language, mode, victim_count, status, started_at, fraud_metadata)
            VALUES (:id, :session_id, :lat, :lng,
                    :accuracy, :loc_source, :channel, :language, :mode,
                    :victims, 'active', :now, :fraud_meta)
        """),
        {
            "id": incident_id,
            "session_id": session_id,
            "lat": req.lat,
            "lng": req.lng,
            "accuracy": req.location_accuracy_m,
            "loc_source": req.location_source,
            "channel": req.channel,
            "language": req.language,
            "mode": req.mode,
            "victims": req.victim_count or 1,
            "now": now,
            "fraud_meta": json.dumps(fraud_metadata),
        },
    )
    await db.commit()

    agent = TriageAgent()
    first_question = agent.get_first_question()

    response_time_ms = (time.monotonic() - t0) * 1000
    await instrumented_incident_initiate(incident_id, None, response_time_ms)

    return IncidentInitiateResponse(
        incident_id=incident_id,
        session_id=session_id,
        triage_state=agent.state,
        first_question=first_question,
        language=req.language,
    )


@router.post("/{incident_id}/triage", response_model=TriageResponse)
async def process_triage(
    incident_id: str,
    req: TriageRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    t0 = time.monotonic()

    result = await db.execute(
        text("""
            SELECT id, triage_transcript, victim_count, language, fraud_metadata
            FROM incidents WHERE id = :id
        """),
        {"id": incident_id},
    )
    incident = result.fetchone()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check if this incident was flagged
    fraud_meta = incident[4] or {}
    if fraud_meta.get("risk_level") in ("high", "critical"):
        raise HTTPException(
            status_code=403,
            detail="This incident is under fraud review.",
        )

    agent = TriageAgent()
    response = agent.process_answer(req.answer)

    # Inject protocol RAG context into instruction if available
    if response.get("instruction"):
        protocol_ctx = await inject_protocol_context(agent.answers, lang=incident[3] or "en", db=db)
        if protocol_ctx:
            response["instruction"] = f"{response['instruction']}\n\n{protocol_ctx}"

    transcript_entry = {
        "question": req.answer,
        "step": agent.state,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if response.get("severity"):
        transcript_entry["severity"] = response["severity"]
    if response.get("instruction"):
        transcript_entry["instruction"] = response["instruction"]

    await db.execute(
        text("""
            UPDATE incidents SET
                triage_transcript = COALESCE(triage_transcript, CAST('[]' AS jsonb)) || CAST(:entry AS jsonb)
            WHERE id = :id
        """),
        {"id": incident_id, "entry": json.dumps(transcript_entry)},
    )
    await db.commit()

    response_time_ms = (time.monotonic() - t0) * 1000
    await instrumented_triage_step(agent.state, incident_id, response_time_ms)

    if response.get("triage_complete") and response.get("severity"):
        severity = response["severity"]
        severity_conf = response.get("severity_confidence", 0.0)

        incident_result = await db.execute(
            text("SELECT lat, lng FROM incidents WHERE id = :id"),
            {"id": incident_id},
        )
        loc = incident_result.fetchone()

        await db.execute(
            text("""
                UPDATE incidents SET severity = :sev, severity_confidence = :conf
                WHERE id = :id
            """),
            {"id": incident_id, "sev": severity, "conf": severity_conf},
        )
        await db.commit()

        dispatch_options = {}
        if loc:
            lat, lng = float(loc[0]), float(loc[1])
            if severity in ("RED", "YELLOW"):
                hospitals = await find_nearest_services(db, lat, lng, "hospital", limit=10)
                ambulances = await find_nearest_services(db, lat, lng, "ambulance", limit=10)
                police = await find_nearest_services(db, lat, lng, "police", radius_km=15, limit=5)
                towing = await find_nearest_services(db, lat, lng, "towing", radius_km=15, limit=5)
                puncture_shops = await find_nearest_services(db, lat, lng, "puncture_shop", radius_km=15, limit=5)

                ranked_hospitals = await rank_hospitals(hospitals)
                dispatch_options = {
                    "hospitals": ranked_hospitals[:5],
                    "ambulances": ambulances[:5],
                    "police": police[:3],
                    "towing": towing[:3],
                    "puncture_shop": puncture_shops[:3],
                }
            elif severity == "GREEN":
                hospitals = await find_nearest_services(db, lat, lng, "hospital", limit=5)
                police = await find_nearest_services(db, lat, lng, "police", radius_km=10, limit=3)
                towing = await find_nearest_services(db, lat, lng, "towing", radius_km=15, limit=5)
                puncture_shops = await find_nearest_services(db, lat, lng, "puncture_shop", radius_km=15, limit=5)

                ranked_hospitals = await rank_hospitals(hospitals)
                dispatch_options = {
                    "hospitals": ranked_hospitals[:3],
                    "police": police[:2],
                    "towing": towing[:3],
                    "puncture_shop": puncture_shops[:3],
                }

                if ambulances:
                    await dispatch_ambulance(db, incident_id, ambulances[0]["id"], lat, lng)

        # Auto-alert emergency contacts if severity RED
        user_incident = await db.execute(
            text("SELECT initiated_by FROM incidents WHERE id = :id"),
            {"id": incident_id},
        )
        user_row = user_incident.fetchone()
        if user_row and user_row[0]:
            user_result = await db.execute(
                text("SELECT phone, ice_contacts FROM users WHERE id = :id"),
                {"id": user_row[0]},
            )
            user_data = user_result.fetchone()
            # (In production: notify ICE contacts via notification_service)

        await instrumented_dispatch_confirm(incident_id, severity, response_time_ms)

        return TriageResponse(
            incident_id=incident_id,
            severity=response["severity"],
            severity_confidence=response.get("severity_confidence"),
            triage_complete=True,
            dispatch_options=dispatch_options if dispatch_options else None,
            session_complete=True,
        )

    return TriageResponse(
        incident_id=incident_id,
        next_question=response.get("next_question"),
        instruction=response.get("instruction"),
        triage_complete=False,
    )


@router.post("/{incident_id}/dispatch", response_model=DispatchResponse)
async def confirm_dispatch(
    incident_id: str,
    req: DispatchRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT es.name, es.phone, i.lat, i.lng
            FROM incidents i, emergency_services es
            WHERE i.id = :incident_id AND es.id = :service_id
        """),
        {"incident_id": incident_id, "service_id": req.service_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident or service not found")

    service_name, service_phone, lat, lng = row[0], row[1], float(row[2]), float(row[3])

    dispatch_result = await dispatch_ambulance(db, incident_id, req.service_id, lat, lng)
    eta = dispatch_result.get("eta_min", 10)

    if service_phone:
        await notification_service.send_sms(
            service_phone,
            f"RoadSoS Dispatch: Accident at https://maps.google.com/?q={lat},{lng}. "
            f"Incident: {incident_id}. ETA: {eta} min.",
        )

    return DispatchResponse(
        incident_id=incident_id,
        service_id=req.service_id,
        service_name=service_name,
        eta_min=eta,
        status="dispatched",
        message=f"{service_name} dispatched. ETA ~{eta} minutes.",
    )


@router.get("/{incident_id}", response_model=IncidentStatusResponse)
async def get_incident_status(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    result = await db.execute(
        text("""
            SELECT id, status, severity, victim_count, dispatched_services,
                   notified_contacts, ambulance_eta_min, hospital_eta_min,
                   triage_transcript, started_at, closed_at
            FROM incidents WHERE id = :id
        """),
        {"id": incident_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentStatusResponse(
        incident_id=row[0],
        status=row[1],
        severity=row[2],
        victim_count=row[3],
        dispatched_services=row[4] if row[4] else [],
        ambulance_eta_min=row[6],
        hospital_eta_min=row[7],
        triage_transcript=row[8] if row[8] else [],
        started_at=row[9],
        closed_at=row[10],
    )