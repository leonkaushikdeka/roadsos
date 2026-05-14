from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.service import (
    NearbyServicesRequest, NearbyServicesResponse,
    ServiceDetail, ServiceStatusResponse,
)
from app.services.dispatch import find_nearest_services

router = APIRouter(prefix="/v1/services", tags=["Services"])


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
