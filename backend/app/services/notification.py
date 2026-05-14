import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    async def send_sms(self, to: str, message: str) -> bool:
        logger.info(f"SMS to {to}: {message[:60]}...")
        if settings.use_mock_dispatch:
            return True
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                    data={"From": settings.twilio_sms_number, "To": to, "Body": message},
                )
                return resp.is_success
        except Exception as e:
            logger.error(f"SMS failed: {e}")
            return False

    async def send_whatsapp(self, to: str, message: str) -> bool:
        logger.info(f"WhatsApp to {to}: {message[:60]}...")
        if settings.use_mock_dispatch:
            return True
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {settings.whatsapp_api_token}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": message},
                    },
                )
                return resp.is_success
        except Exception as e:
            logger.error(f"WhatsApp failed: {e}")
            return False

    async def notify_emergency_contacts(self, phone: str, incident_id: str, lat: float, lng: str) -> None:
        message = (
            f"RoadSoS ALERT: Someone at your emergency contact had an accident. "
            f"Incident: {incident_id}. Location: https://maps.google.com/?q={lat},{lng}. "
            f"Help has been dispatched."
        )
        await self.send_sms(phone, message)

    async def notify_hospital(self, hospital_phone: str, incident_packet: dict) -> bool:
        message = (
            f"RoadSoS PRE-ALERT: Incoming trauma patient. "
            f"Severity: {incident_packet.get('severity', 'UNKNOWN')}. "
            f"Victims: {incident_packet.get('victim_count', 1)}. "
            f"ETA: ~{incident_packet.get('eta_min', '?')} min. "
            f"Mechanism: {incident_packet.get('mechanism', 'RTA')}. "
            f"Incident: {incident_packet.get('incident_id')}"
        )
        return await self.send_sms(hospital_phone, message)


notification_service = NotificationService()
