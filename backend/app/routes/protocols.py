"""
Offline bundle endpoint for the PWA service worker.

Returns the 50 most common first-aid protocols as a single JSON payload
for service worker precaching.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/v1/protocols", tags=["Protocols"])


@router.get("/offline-bundle")
async def get_offline_bundle(
    lang: str = "en",
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Return protocol chunks as a single JSON bundle for offline caching.
    """
    result = await db.execute(
        text("""
            SELECT id, source, language, protocol_type, chunk_text, tags
            FROM protocol_chunks
            WHERE language = :lang
            ORDER BY
                CASE protocol_type
                    WHEN 'bleeding_control' THEN 1
                    WHEN 'cpr' THEN 2
                    WHEN 'spinal_precautions' THEN 3
                    WHEN 'shock_management' THEN 4
                    WHEN 'fracture_management' THEN 5
                    WHEN 'recovery_position' THEN 6
                    WHEN 'burns_first_aid' THEN 7
                    ELSE 99
                END,
                id
            LIMIT :limit
        """),
        {"lang": lang, "limit": limit},
    )

    protocols = []
    for row in result.fetchall():
        protocols.append({
            "id": row[0],
            "source": row[1],
            "language": row[2],
            "type": row[3],
            "text": row[4],
            "tags": list(row[5]) if row[5] else [],
        })

    return {
        "lang": lang,
        "count": len(protocols),
        "protocols": protocols,
    }