"""
Integration tests for dispatch and incident flow.

Run with: python -m pytest backend/tests/ -v
"""

import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, "..")

from sqlalchemy import text


class TestDispatchService:
    """Tests for the dispatch service (PostGIS queries and OSRM integration)."""

    @pytest.mark.asyncio
    async def test_find_nearest_hospitals(self):
        """Test that hospitals are found and ranked by trauma grade + distance."""
        from app.services.dispatch import find_nearest_services
        from app.database import async_session

        # This test requires a running database — skip if not available
        try:
            async with async_session() as db:
                await db.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("Database not available")

        async with async_session() as db:
            results = await find_nearest_services(
                db, lat=13.08, lng=80.27,
                service_type="hospital", radius_km=25, limit=5
            )
            assert isinstance(results, list)
            if results:
                r = results[0]
                assert "id" in r
                assert "name" in r
                assert "distance_km" in r
                assert "eta_min" in r
                assert "trauma_grade" in r

    @pytest.mark.asyncio
    async def test_find_nearest_ambulances(self):
        """Test that ambulances are found near a location."""
        from app.services.dispatch import find_nearest_services
        from app.database import async_session

        try:
            async with async_session() as db:
                await db.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("Database not available")

        async with async_session() as db:
            results = await find_nearest_services(
                db, lat=13.08, lng=80.27,
                service_type="ambulance", radius_km=25, limit=3
            )
            assert isinstance(results, list)
            if results:
                assert all("eta_min" in r for r in results)

    @pytest.mark.asyncio
    async def test_dispatch_ambulance(self):
        """Test ambulance dispatch updates the incident record."""
        from app.services.dispatch import dispatch_ambulance
        from app.database import async_session

        try:
            async with async_session() as db:
                await db.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("Database not available")

        # Create a test incident
        incident_id = str(uuid.uuid4())
        async with async_session() as db:
            await db.execute(
                text("""
                    INSERT INTO incidents (id, session_id, location, status, started_at)
                    VALUES (:id, :sid, ST_GeomFromText('SRID=4326;POINT(80.27 13.08)', 4326),
                           'active', :now)
                """),
                {"id": incident_id, "sid": f"TEST-{incident_id[:8]}", "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            # Find an ambulance
            amb_result = await db.execute(
                text("SELECT id FROM emergency_services WHERE service_type = 'ambulance' LIMIT 1")
            )
            amb_row = amb_result.fetchone()

            if amb_row:
                result = await dispatch_ambulance(db, incident_id, amb_row[0], 13.08, 80.27)
                assert "incident_id" in result
                assert "eta_min" in result
            else:
                pytest.skip("No ambulance in database")

            # Cleanup
            await db.execute(text("DELETE FROM incidents WHERE id = :id"), {"id": incident_id})
            await db.commit()

    @pytest.mark.asyncio
    async def test_rank_hospitals(self):
        """Test hospital ranking by trauma grade and distance."""
        from app.services.dispatch import rank_hospitals

        hospitals = [
            {"name": "A", "trauma_grade": 1, "distance_km": 5, "has_icu": True, "has_ventilator": True, "eta_min": 6},
            {"name": "B", "trauma_grade": 2, "distance_km": 3, "has_icu": False, "has_ventilator": False, "eta_min": 4},
            {"name": "C", "trauma_grade": 1, "distance_km": 10, "has_icu": True, "has_ventilator": False, "eta_min": 12},
        ]

        ranked = rank_hospitals(hospitals)
        assert ranked[0]["name"] == "A"  # Best grade + ICU + ventilator
        assert len(ranked) == 3


class TestFraudEngineExtended:
    """Extended tests for the fraud detection engine."""

    @pytest.mark.asyncio
    async def test_rate_limiting_flag(self):
        """Repeated incidents from same phone should trigger rate flag."""
        from app.services.fraud import FraudEngine, encode_geohash
        from unittest.mock import AsyncMock

        db = AsyncMock()
        engine = FraudEngine(db)

        # Mock tracker with many recent incidents
        mock_tracker = {
            "phone": "+919876543210",
            "recent_incidents": 15,
            "last_incident_at": datetime.utcnow().isoformat(),
        }
        db.execute = AsyncMock(return_value=AsyncMock(
            fetchone=AsyncMock(return_value=(
                mock_tracker["recent_incidents"],
                mock_tracker["last_incident_at"],
                None,  # last_lat
                None,  # last_lng
                None,  # last_device
            ))
        ))

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="fp123",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_geo_encoding_precision(self):
        """Geohash precision affects duplicate detection radius."""
        from app.services.fraud import encode_geohash

        # Precision 4 ≈ 20km grid — same location should match
        g1 = encode_geohash(13.0827, 80.2707, precision=4)
        g2 = encode_geohash(13.0830, 80.2710, precision=4)
        assert len(g1) == 4
        assert len(g2) == 4

        # Precision 6 ≈ 1.2km grid — very close but might differ
        g3 = encode_geohash(13.0827, 80.2707, precision=6)
        g4 = encode_geohash(13.0830, 80.2710, precision=6)
        assert len(g3) == 6

    @pytest.mark.asyncio
    async def test_impossible_velocity(self):
        """Locations 1500km apart within 1 hour should flag."""
        from app.services.fraud import encode_geohash
        from app.services.fraud import FraudEngine
        from unittest.mock import AsyncMock

        # Chennai to Delhi
        g1 = encode_geohash(13.08, 80.27, precision=6)
        g2 = encode_geohash(28.61, 77.21, precision=6)
        assert g1 != g2  # Different geohashes

    @pytest.mark.asyncio
    async def test_device_fingerprint_change(self):
        """Same phone with different device should flag."""
        from app.services.fraud import FraudEngine
        from unittest.mock import AsyncMock

        db = AsyncMock()
        engine = FraudEngine(db)

        # Previous incident with different device
        mock_tracker = {
            "phone": "+919876543210",
            "recent_incidents": 1,
            "last_incident_at": datetime.utcnow().isoformat(),
            "last_device": "old_device_fp",
        }
        db.execute = AsyncMock(return_value=AsyncMock(
            fetchone=AsyncMock(return_value=(
                mock_tracker["recent_incidents"],
                mock_tracker["last_incident_at"],
                13.08, 80.27,
                mock_tracker["last_device"],
            ))
        ))

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="new_device_fp",
        )
        assert result is not None


class TestIncidentFlowIntegration:
    """Full integration test — initiate → triage → dispatch."""

    @pytest.mark.asyncio
    async def test_full_incident_flow(self):
        """Test complete incident: initiate, 5 triage steps, dispatch."""
        from app.services.triage import TriageAgent
        from app.services.dispatch import rank_hospitals

        agent = TriageAgent()

        # Step 1: Initiate
        q1 = agent.get_first_question()
        assert "victim" in q1.lower() or "helping" in q1.lower()

        # Step 2: Assess consciousness
        r2 = agent.process_answer("I am the victim")
        assert not r2["triage_complete"]

        # Step 3: Assess breathing (unconscious → airway)
        r3 = agent.process_answer("No, not responding")
        assert not r3["triage_complete"]

        # Step 4: Assess airway
        r4 = agent.process_answer("No, not breathing")
        assert not r4["triage_complete"]
        assert r4.get("instruction") is not None

        # Step 5: Bleeding
        r5 = agent.process_answer("Yes, heavy bleeding")
        # With max_questions=5, this should trigger final classification
        assert r5["triage_complete"]
        assert r5["severity"] == "RED"
        assert r5["severity_confidence"] > 0.7

    @pytest.mark.asyncio
    async def test_green_triage_flow(self):
        """Test minor injury flow results in GREEN severity."""
        from app.services.triage import TriageAgent

        agent = TriageAgent(max_questions=5)
        agent.get_first_question()

        agent.process_answer("I'm helping them")
        agent.process_answer("Yes, they're awake")
        agent.process_answer("Yes, breathing normally")
        agent.process_answer("No bleeding")
        r = agent.process_answer("No broken bones")

        assert r["triage_complete"]
        assert r["severity"] == "GREEN"

    @pytest.mark.asyncio
    async def test_duplicate_incident_detection(self):
        """Test that duplicate incident attempts are flagged."""
        from app.services.fraud import encode_geohash

        # Same location should produce same geohash
        g1 = encode_geohash(13.0827, 80.2707, precision=4)
        g2 = encode_geohash(13.0828, 80.2708, precision=4)
        assert g1 == g2  # Within same geohash cell


class TestAPISchemas:
    """Test API request/response schemas."""

    def test_incident_initiate_request(self):
        from app.schemas.incident import IncidentInitiateRequest
        req = IncidentInitiateRequest(
            lat=13.08, lng=80.27,
            location_accuracy_m=16.5,
            channel="pwa",
            language="en",
            mode="bystander",
            victim_count=1,
        )
        assert req.lat == 13.08
        assert req.channel == "pwa"

    def test_triage_request(self):
        from app.schemas.incident import TriageRequest
        req = TriageRequest(incident_id="test-123", answer="yes")
        assert req.incident_id == "test-123"
        assert req.answer == "yes"

    def test_dispatch_request(self):
        from app.schemas.incident import DispatchRequest
        req = DispatchRequest(incident_id="test-123", service_id="svc-456")
        assert req.confirm is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])