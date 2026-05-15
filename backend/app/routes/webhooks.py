import json
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.services.triage import TriageAgent, LegacyTriageAgent
from app.services.notification import notification_service
from app.config import settings

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/webhook", tags=["Webhooks"])

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create a Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


SESSION_TTL = 3600  # 1 hour


async def get_session_state(session_key: str) -> dict:
    """Load session state from Redis, or return fresh state."""
    redis = await get_redis()
    data = await redis.get(f"wa_session:{session_key}")
    if data:
        return json.loads(data)
    return {
        "agent_state": "INIT",
        "answers": {},
        "questions_asked": 0,
        "incident_id": None,
        "triage_complete": False,
        "severity": None,
    }


async def save_session_state(session_key: str, state: dict):
    """Persist session state to Redis with TTL."""
    redis = await get_redis()
    await redis.setex(
        f"wa_session:{session_key}",
        SESSION_TTL,
        json.dumps(state),
    )


async def get_voice_session_state(session_key: str) -> dict:
    """Load voice session state from Redis, or return fresh state."""
    redis = await get_redis()
    data = await redis.get(f"voice_session:{session_key}")
    if data:
        return json.loads(data)
    return {
        "agent_state": "INIT",
        "answers": {},
        "questions_asked": 0,
        "triage_complete": False,
        "severity": None,
    }


async def save_voice_session_state(session_key: str, state: dict):
    """Persist voice session state to Redis with TTL."""
    redis = await get_redis()
    await redis.setex(
        f"voice_session:{session_key}",
        SESSION_TTL,
        json.dumps(state),
    )


@router.post("/whatsapp")
async def whatsapp_webhook(req: Request):
    body = await req.json()
    logger.info(f"WhatsApp webhook: {json.dumps(body)[:200]}")

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        from_number = msg.get("from", "")
        msg_type = msg.get("type", "text")

        # Extract text from message (handle text, interactive, and location types)
        text_body = ""
        location_data = None
        if msg_type == "text":
            text_body = msg.get("text", {}).get("body", "").lower().strip()
        elif msg_type == "interactive":
            text_body = (
                msg.get("interactive", {}).get("button_reply", {}).get("title", "")
                or msg.get("interactive", {}).get("list_reply", {}).get("title", "")
            ).lower().strip()
        elif msg_type == "location":
            location_data = msg.get("location", {})
            text_body = "location_shared"

        session_key = f"wa:{from_number}"
        session = await get_session_state(session_key)

        # If user shared their location, store it in session
        if location_data:
            session["lat"] = location_data.get("latitude")
            session["lng"] = location_data.get("longitude")
            session["location_name"] = location_data.get("name", "")

        # Handle initial SOS trigger keywords
        if text_body in ("sos", "help", "accident", "emergency", "hi", "hello") and session.get("agent_state") == "INIT":
            session["agent_state"] = "INIT"
            session["answers"] = {}
            session["questions_asked"] = 0
            session["triage_complete"] = False
            session["severity"] = None

        # Initialize agent with persisted state or create fresh
        agent = LegacyTriageAgent()
        agent.state = session.get("agent_state", "INIT")
        agent.answers = session.get("answers", {})
        agent.questions_asked = session.get("questions_asked", 0)

        # If this is the very first message, get the first question instead
        if agent.state == "INIT" and agent.questions_asked == 0:
            first_q = agent.get_first_question()
            session["agent_state"] = agent.state
            await save_session_state(session_key, session)

            intro = (
                "RoadSoS Emergency AI Assistant.\n"
                "I will ask you a few quick questions to get help to you faster.\n\n"
                f"{first_q}\n\n"
                "Please also share your location using WhatsApp's location feature (paperclip > Location)."
            )
            if not settings.use_mock_dispatch:
                await notification_service.send_whatsapp(from_number, intro)
            else:
                logger.info(f"[MOCK] WhatsApp reply to {from_number}: {intro}")
            return {"status": "ok"}

        response = agent.process_answer(text_body)

        # Persist updated state
        session["agent_state"] = agent.state
        session["answers"] = agent.answers
        session["questions_asked"] = agent.questions_asked
        session["triage_complete"] = response.get("triage_complete", False)
        if response.get("severity"):
            session["severity"] = response["severity"]
        await save_session_state(session_key, session)

        reply = response.get("next_question") or response.get("instruction") or "Help is on the way."
        if response.get("triage_complete"):
            severity = response.get("severity", "UNKNOWN")
            reply = (
                f"[TRIAGE COMPLETE - Severity: {severity}]\n"
                f"Ambulance has been dispatched to your location. Stay on the line. "
                f"Help is on the way."
            )
            # Clean up session after triage complete
            redis = await get_redis()
            await redis.delete(f"wa_session:{session_key}")

        if not settings.use_mock_dispatch:
            await notification_service.send_whatsapp(from_number, reply)
        else:
            logger.info(f"[MOCK] WhatsApp reply to {from_number}: {reply}")

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)

    return {"status": "ok"}


@router.post("/twilio/voice")
async def twilio_voice_webhook(req: Request):
    form = await req.form()
    speech_result = form.get("SpeechResult", "").lower().strip()
    caller = form.get("From", "")
    logger.info(f"Twilio voice from {caller}: {speech_result}")

    from twilio.twiml.voice_response import VoiceResponse, Gather

    resp = VoiceResponse()

    session_key = f"voice:{caller}"
    session = await get_voice_session_state(session_key)

    # Handle first call / no speech result (initial greeting)
    if not speech_result or (session.get("agent_state") == "INIT" and not speech_result):
        agent = LegacyTriageAgent()
        session["agent_state"] = agent.state = "INIT"
        session["answers"] = agent.answers = {}
        session["questions_asked"] = agent.questions_asked = 0
        question = agent.get_first_question()

        # Persist initial state
        await save_voice_session_state(session_key, session)

        gather = Gather(input="speech", language="en-IN", speechTimeout="auto", action="/v1/webhook/twilio/voice")
        gather.say(
            "RoadSoS emergency assistant. I am an AI assistant. Call 108 if you can. I will help while you wait. "
            + question,
            voice="alice", language="en-IN",
        )
        resp.append(gather)
        resp.redirect("/v1/webhook/twilio/voice")
        return HTMLResponse(str(resp))

    # Skip if already complete
    if session.get("triage_complete"):
        severity = session.get("severity", "RED")
        resp.say(
            f"Triage is already complete. Severity level: {severity}. "
            f"Ambulance is on its way. Stay on the line. Help is coming.",
            voice="alice", language="en-IN",
        )
        redis = await get_redis()
        await redis.delete(f"voice_session:{session_key}")
        return HTMLResponse(str(resp))

    # Restore agent state
    agent = LegacyTriageAgent()
    agent.state = session.get("agent_state", "INIT")
    agent.answers = session.get("answers", {})
    agent.questions_asked = session.get("questions_asked", 0)

    response = agent.process_answer(speech_result)

    # Persist updated state
    session["agent_state"] = agent.state
    session["answers"] = agent.answers
    session["questions_asked"] = agent.questions_asked
    session["triage_complete"] = response.get("triage_complete", False)
    if response.get("severity"):
        session["severity"] = response["severity"]
    await save_voice_session_state(session_key, session)

    if response.get("triage_complete"):
        resp.say(
            f"Triage complete. Severity level: {response.get('severity', 'RED')}. "
            f"Ambulance is on its way. Stay on the line. Help is coming.",
            voice="alice", language="en-IN",
        )
        redis = await get_redis()
        await redis.delete(f"voice_session:{session_key}")
    else:
        question = response.get("next_question", "")
        instruction = response.get("instruction", "")
        msg = f"{instruction} {question}" if instruction else question
        gather = Gather(input="speech", language="en-IN", speechTimeout="auto", action="/v1/webhook/twilio/voice")
        gather.say(msg, voice="alice", language="en-IN")
        resp.append(gather)
        resp.redirect("/v1/webhook/twilio/voice")

    return HTMLResponse(str(resp))


@router.get("/whatsapp")
async def whatsapp_verify(req: Request):
    verify_token = req.query_params.get("hub.verify_token")
    challenge = req.query_params.get("hub.challenge")
    if verify_token == settings.whatsapp_verify_token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")