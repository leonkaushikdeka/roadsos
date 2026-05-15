import math
import httpx
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

SERVICE_PRIORITY = {
    "hospital": 1,
    "ambulance": 2,
    "police": 3,
    "fire": 4,
    "blood_bank": 5,
    "towing": 6,
    "puncture_shop": 7,
    "showroom": 8,
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _get_osrm_eta(start_lng: float, start_lat: float, end_lng: float, end_lat: float) -> Optional[float]:
    if not settings.osm_routing_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = (
                f"{settings.osm_routing_url}/route/v1/driving/"
                f"{start_lng},{start_lat};{end_lng},{end_lat}"
                f"?overview=false"
            )
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                routes = data.get("routes", [])
                if routes:
                    return routes[0].get("duration", 0) / 60.0
    except Exception as e:
        logger.debug(f"OSRM routing unavailable: {e}")
    return None


def _linear_eta(distance_km: float, service_type: str) -> float:
    speed_map = {
        "hospital": 0.8, "ambulance": 0.6, "police": 0.5, "fire": 0.5,
        "blood_bank": 0.6, "towing": 0.4, "puncture_shop": 0.5, "showroom": 0.5,
    }
    speed = speed_map.get(service_type, 0.5)
    return max(1, round(distance_km / speed))


async def find_nearest_services(
    db: AsyncSession,
    lat: float,
    lng: float,
    service_type: str,
    radius_km: float = 25,
    min_trauma_grade: Optional[int] = None,
    limit: int = 5,
    use_osrm: bool = True,
) -> list[dict]:
    trauma_filter = ""
    if min_trauma_grade and service_type == "hospital":
        trauma_filter = f"AND trauma_grade <= {min_trauma_grade}"

    sql = text(f"""
        SELECT id, name, service_type, trauma_grade,
               lat, lng, phone, address, has_icu, has_ventilator, capacity
        FROM emergency_services
        WHERE service_type = :service_type
        {trauma_filter}
        ORDER BY
            CASE WHEN service_type = 'hospital' THEN trauma_grade ELSE 0 END ASC
    """)

    result = await db.execute(sql, {"service_type": service_type})

    candidates = []
    for row in result.fetchall():
        svc_lat, svc_lng = float(row[4]), float(row[5])
        distance_km = _haversine_km(lat, lng, svc_lat, svc_lng)
        if distance_km > radius_km:
            continue

        eta_min = None
        if use_osrm:
            eta_min = await _get_osrm_eta(lng, lat, svc_lng, svc_lat)
        if eta_min is None:
            eta_min = _linear_eta(distance_km, service_type)

        candidates.append({
            "id": row[0],
            "name": row[1],
            "service_type": row[2],
            "trauma_grade": row[3],
            "distance_km": round(distance_km, 2),
            "phone": row[6],
            "address": row[7],
            "has_icu": row[8],
            "has_ventilator": row[9],
            "capacity": row[10] if row[10] else {},
            "eta_min": round(eta_min, 1),
            "lat": svc_lat,
            "lng": svc_lng,
        })

    candidates.sort(key=lambda s: s["distance_km"])
    return candidates[:limit]


async def dispatch_ambulance(
    db: AsyncSession,
    incident_id: str,
    service_id: str,
    lat: float,
    lng: float,
    use_osrm: bool = True,
) -> dict:
    amb_result = await db.execute(
        text("SELECT lat, lng FROM emergency_services WHERE id = :id"),
        {"id": service_id},
    )
    amb_row = amb_result.fetchone()

    eta_min = None
    if use_osrm and amb_row and amb_row[0] is not None:
        eta_min = await _get_osrm_eta(amb_row[1], amb_row[0], lng, lat)

    if eta_min is None and amb_row and amb_row[0] is not None:
        distance_km = _haversine_km(lat, lng, float(amb_row[0]), float(amb_row[1]))
        eta_min = _linear_eta(distance_km, "ambulance")

    if eta_min is None:
        eta_min = 10

    dispatch_info = {
        "type": "ambulance",
        "service_id": service_id,
        "dispatched_at": datetime.utcnow().isoformat(),
    }

    sql = text("""
        UPDATE incidents
        SET status = 'ambulance_dispatched',
            dispatched_services = COALESCE(dispatched_services, CAST('[]' AS jsonb)) || CAST(:dispatch_info AS jsonb),
            ambulance_eta_min = :eta
        WHERE id = :incident_id
        RETURNING id, ambulance_eta_min
    """)

    result = await db.execute(sql, {
        "incident_id": incident_id,
        "dispatch_info": str(dispatch_info).replace("'", '"'),
        "eta": eta_min,
    })
    await db.commit()
    row = result.fetchone()
    return {"incident_id": row[0], "eta_min": row[1]} if row else {}


async def rank_hospitals(services: list[dict]) -> list[dict]:
    def score(svc):
        s = 0
        if svc.get("trauma_grade"):
            s += (5 - svc["trauma_grade"]) * 10
        if svc.get("has_icu"):
            s += 15
        if svc.get("has_ventilator"):
            s += 10
        distance_km = svc.get("distance_km", 100)
        s += max(0, 20 - distance_km)
        eta = svc.get("eta_min", 100)
        s += max(0, 10 - eta)
        return s

    return sorted(services, key=score, reverse=True)
