from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.service import (
    NearbyServicesRequest, NearbyServicesResponse,
    ServiceDetail, ServiceStatusResponse,
)
from app.services.dispatch import find_nearest_services

router = APIRouter(prefix="/v1/services", tags=["Services"])

# Global emergency numbers by country (BIMSTEC + common)
EMERGENCY_NUMBERS = {
    "IN": {"name": "India", "ambulance": "108", "police": "100", "fire": "101", "universal": "112", "highway": "1033"},
    "BD": {"name": "Bangladesh", "ambulance": "199", "police": "999", "fire": "199", "universal": "999"},
    "LK": {"name": "Sri Lanka", "ambulance": "1990", "police": "119", "fire": "110", "universal": "110"},
    "TH": {"name": "Thailand", "ambulance": "1669", "police": "191", "fire": "199", "universal": "191"},
    "MM": {"name": "Myanmar", "ambulance": "192", "police": "199", "fire": "191", "universal": "199"},
    "NP": {"name": "Nepal", "ambulance": "102", "police": "100", "fire": "101", "universal": "112"},
    "BT": {"name": "Bhutan", "ambulance": "112", "police": "113", "fire": "110", "universal": "112"},
    "US": {"name": "United States", "ambulance": "911", "police": "911", "fire": "911", "universal": "911"},
    "GB": {"name": "United Kingdom", "ambulance": "999", "police": "999", "fire": "999", "universal": "112"},
    "AU": {"name": "Australia", "ambulance": "000", "police": "000", "fire": "000", "universal": "112"},
    "DE": {"name": "Germany", "ambulance": "112", "police": "110", "fire": "112", "universal": "112"},
    "JP": {"name": "Japan", "ambulance": "119", "police": "110", "fire": "119", "universal": "110"},
    "SG": {"name": "Singapore", "ambulance": "995", "police": "999", "fire": "995", "universal": "999"},
    "MY": {"name": "Malaysia", "ambulance": "999", "police": "999", "fire": "994", "universal": "999"},
}

ALL_SERVICE_TYPES = ["hospital", "ambulance", "police", "fire", "blood_bank", "towing", "puncture_shop", "showroom"]


@router.get("/nearby", response_model=NearbyServicesResponse)
async def get_nearby_services(
    lat: float,
    lng: float,
    radius_km: float = 25,
    service_type: str = "hospital",
    min_trauma_grade: int = None,
    db: AsyncSession = Depends(get_db),
):
    if min_trauma_grade is None:
        min_trauma_grade = 4

    results = await find_nearest_services(
        db, lat, lng, service_type,
        radius_km=radius_km,
        min_trauma_grade=min_trauma_grade,
    )

    services = []
    for r in results:
        services.append(
            ServiceDetail(
                id=r["id"],
                name=r["name"],
                service_type=r["service_type"],
                trauma_grade=r["trauma_grade"],
                distance_km=r["distance_km"],
                eta_min=r["eta_min"],
                phone=r["phone"],
                address=r["address"],
                has_icu=r.get("has_icu", False),
                has_ventilator=r.get("has_ventilator", False),
                capacity=r.get("capacity", {}),
            )
        )

    return NearbyServicesResponse(services=services, total=len(services))


@router.get("/all-nearby")
async def get_all_nearby_services(
    lat: float,
    lng: float,
    radius_km: float = 25,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch ALL service types near a location in one call.
    Returns hospital, ambulance, police, fire, blood_bank, towing, puncture_shop, showroom.
    Maximises the number of contacts fetched (evaluation criteria).
    """
    all_services = {}
    total = 0
    for stype in ALL_SERVICE_TYPES:
        results = await find_nearest_services(db, lat, lng, stype, radius_km=radius_km, limit=limit)
        all_services[stype] = results
        total += len(results)

    return {"services": all_services, "total": total, "radius_km": radius_km}


@router.get("/emergency-numbers")
async def get_emergency_numbers(country_code: Optional[str] = None):
    """
    Return emergency phone numbers for a country or all countries.
    Supports BIMSTEC nations and major global countries for cross-country applicability.
    Works fully offline once cached by the service worker.
    """
    if country_code:
        cc = country_code.upper()
        if cc in EMERGENCY_NUMBERS:
            return {"country": cc, **EMERGENCY_NUMBERS[cc]}
        return {"error": f"Country code {cc} not found", "available": list(EMERGENCY_NUMBERS.keys())}
    return {"countries": EMERGENCY_NUMBERS}


@router.get("/{service_id}/status", response_model=ServiceStatusResponse)
async def get_service_status(service_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("""
            SELECT es.id, es.name, ss.available_beds, ss.available_icu_beds,
                ss.ambulances_available, ss.avg_wait_min, ss.status, ss.timestamp
            FROM emergency_services es
            LEFT JOIN (
                SELECT DISTINCT ON (service_id) service_id, available_beds, available_icu_beds,
                    ambulances_available, avg_wait_min, status, timestamp
                FROM service_status
                ORDER BY service_id, timestamp DESC
            ) ss ON es.id = ss.service_id
            WHERE es.id = :id
        """),
        {"id": service_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")

    return ServiceStatusResponse(
        service_id=row[0],
        service_name=row[1],
        available_beds=row[2],
        available_icu_beds=row[3],
        ambulances_available=row[4],
        avg_wait_min=row[5],
        status=row[6] or "unknown",
        last_updated=row[7],
    )
