import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/admin", tags=["Admin"])


@router.post("/seed")
async def seed_database_endpoint():
    """Seed emergency services and protocol data into the database."""
    try:
        from app.seed.run import seed_database
        await seed_database()
        return {"status": "ok", "message": "Database seeded successfully"}
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_heatmap(
    days: int = 30,
    state: str = None,
    db: AsyncSession = Depends(get_db),
):
    state_filter = ""
    params = {"since": datetime.utcnow() - timedelta(days=days)}
    if state:
        state_filter = " AND location_state = :state"
        params["state"] = state

    sql = text(f"""
        SELECT
            lng, lat, severity,
            COUNT(*) as incident_count,
            DATE(started_at) as date
        FROM incidents
        WHERE started_at >= :since
        {state_filter}
        GROUP BY lng, lat, severity, DATE(started_at)
        ORDER BY date DESC, incident_count DESC
        LIMIT 1000
    """)

    result = await db.execute(sql, params)
    points = []
    for row in result.fetchall():
        points.append({
            "lng": float(row[0]),
            "lat": float(row[1]),
            "severity": row[2],
            "count": row[3],
            "date": row[4].isoformat(),
        })

    return {"incidents": points, "total": len(points)}


@router.get("/stats")
async def get_stats(days: int = 30, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    sql = text("""
        SELECT
            COUNT(*) as total_incidents,
            COUNT(*) FILTER (WHERE severity = 'RED') as red_count,
            COUNT(*) FILTER (WHERE severity = 'YELLOW') as yellow_count,
            COUNT(*) FILTER (WHERE severity = 'GREEN') as green_count,
            COUNT(*) FILTER (WHERE status = 'closed') as closed_count,
            ROUND(AVG(ambulance_eta_min)) as avg_eta
        FROM incidents WHERE started_at >= :since
    """)
    result = await db.execute(sql, {"since": since})
    row = result.fetchone()
    return {
        "total_incidents": row[0],
        "red_count": row[1],
        "yellow_count": row[2],
        "green_count": row[3],
        "closed_count": row[4],
        "avg_eta_min": row[5],
        "period_days": days,
    }
