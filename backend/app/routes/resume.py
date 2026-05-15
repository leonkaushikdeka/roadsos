"""
Resume endpoint and additional incident utilities.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.incident import IncidentStatusResponse, IncidentInitiateResponse

router = APIRouter(prefix="/v1/incident", tags=["Incidents"])


@router.get("/{incident_id}/resume", response_model=IncidentInitiateResponse)
async def resume_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Resume an existing incident — returns current state and next question."""
    result = await db.execute(
        text("""
            SELECT id, session_id, language, triage_transcript, severity, status
            FROM incidents WHERE id = :id
        """),
        {"id": incident_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident_id_val, session_id, language, transcript, severity, status = row

    if status == "closed":
        raise HTTPException(status_code=410, detail="This incident has been closed")

    # Determine next question based on existing transcript
    transcript_list = transcript if isinstance(transcript, list) else []

    if severity:
        # Triage already complete
        first_question = f"Triage complete. Severity: {severity}. Dispatch in progress."
    elif not transcript_list:
        first_question = "Are you the victim, or are you helping someone else?"
    else:
        # Resume from where we left off — get last state
        last_entry = transcript_list[-1]
        first_question = "Let's continue. " + last_entry.get("text", "How is the person doing now?")

    return IncidentInitiateResponse(
        incident_id=incident_id_val,
        session_id=session_id or f"SOS-{incident_id_val[:8].upper()}",
        triage_state=severity or "active",
        first_question=first_question,
        language=language,
    )


@router.post("/{incident_id}/close")
async def close_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Mark incident as closed after resolution."""
    result = await db.execute(
        text("""
            UPDATE incidents SET status = 'closed', closed_at = :now
            WHERE id = :id AND status != 'closed'
            RETURNING id, status
        """),
        {"id": incident_id, "now": datetime.utcnow()},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found or already closed")

    return {"status": "closed", "incident_id": incident_id}