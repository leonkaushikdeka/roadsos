"""
Resume endpoint — returns first question for an existing incident
without creating a new one.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/v1/incident", tags=["Incident Start"])


@router.get("/{incident_id}/start")
async def start_triage(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Get the first triage question for an existing incident."""
    # Validate UUID
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID")

    result = await db.execute(
        text("""
            SELECT id, session_id, language, severity, status
            FROM incidents WHERE id = :id
        """),
        {"id": incident_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    db_id, session_id, language, severity, status = row

    if status == "closed":
        raise HTTPException(status_code=410, detail="This incident has been closed")

    # If triage already complete, return summary
    if severity:
        return {
            "incident_id": db_id,
            "session_id": session_id or f"SOS-{db_id[:8].upper()}",
            "first_question": f"Triage complete. Severity: {severity}. Dispatch in progress.",
            "triage_complete": True,
            "severity": severity,
            "language": language,
        }

    # First question based on existing transcript
    transcript_result = await db.execute(
        text("""
            SELECT triage_transcript
            FROM incidents WHERE id = :id
        """),
        {"id": incident_id},
    )
    t_row = transcript_result.fetchone()
    transcript = t_row[0] if t_row else None

    if transcript and isinstance(transcript, list) and len(transcript) > 0:
        last = transcript[-1]
        return {
            "incident_id": db_id,
            "session_id": session_id or f"SOS-{db_id[:8].upper()}",
            "first_question": "Let's continue. " + last.get("text", "How is the person doing now?"),
            "triage_complete": False,
            "language": language,
        }

    return {
        "incident_id": db_id,
        "session_id": session_id or f"SOS-{db_id[:8].upper()}",
        "triage_state": "INIT",
        "first_question": "Are you the victim, or are you helping someone else?",
        "triage_complete": False,
        "language": language,
    }