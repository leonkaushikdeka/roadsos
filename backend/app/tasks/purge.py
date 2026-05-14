"""
Celery tasks for RoadSoS background jobs.

Includes:
- Data retention purge (auto-delete incidents older than retention window)
"""
import json
import logging
from datetime import datetime, timedelta
from celery import Celery
from app.config import settings
from app.database import engine, async_session

logger = logging.getLogger(__name__)

celery_app = Celery(
    "roadsos_tasks",
    broker=settings.celery_broker_url,
    backend=None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "purge-old-incidents": {
            "task": "app.tasks.purge.purge_old_incidents",
            "schedule": 3600.0,  # Every hour
        },
    },
    task_routes={
        "app.tasks.purge.purge_old_incidents": {"queue": "data-cleanup"},
    },
)


@celery_app.task(bind=True, max_retries=3)
async def purge_old_incidents(self):
    """
    Delete incidents where closed_at < NOW() - retention window.
    Also:
    - Null out location data before deletion (DPDP compliance)
    - Purge triage entries for those incidents
    """
    from sqlalchemy import text

    retention_hours = settings.data_retention_hours
    cutoff = datetime.utcnow() - timedelta(hours=retention_hours)

    logger.info(f"Purging incidents older than {retention_hours}h (cutoff: {cutoff.isoformat()})")

    try:
        async with async_session() as session:
            # Step 1: Find incidents to purge
            find_sql = text("""
                SELECT id FROM incidents
                WHERE status = 'closed'
                  AND closed_at < :cutoff
            """)
            result = await session.execute(find_sql, {"cutoff": cutoff})
            incident_ids = [row[0] for row in result.fetchall()]

            if not incident_ids:
                logger.info("No incidents to purge")
                return {"purged": 0, "anonymized": 0}

            logger.info(f"Found {len(incident_ids)} incidents to purge")

            # Step 2: Anonymize location data before deletion
            anonymize_sql = text("""
                UPDATE incidents
                SET location = NULL
                WHERE id = ANY(:ids)
            """)
            await session.execute(anonymize_sql, {"ids": incident_ids})

            # Step 3: Delete triage entries for these incidents
            delete_triage_sql = text("""
                UPDATE incidents
                SET triage_transcript = '[]'::jsonb
                WHERE id = ANY(:ids)
            """)
            await session.execute(delete_triage_sql, {"ids": incident_ids})

            # Step 4: Delete the incidents
            delete_sql = text("""
                DELETE FROM incidents
                WHERE id = ANY(:ids)
            """)
            await session.execute(delete_sql, {"ids": incident_ids})
            await session.commit()

            purged_count = len(incident_ids)
            logger.info(f"Purged {purged_count} incidents")

            return {
                "purged": purged_count,
                "anonymized": purged_count,  # All were anonymized before deletion
            }

    except Exception as exc:
        logger.error(f"Purge task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)