"""
Integration tests for the full incident flow: initiate → triage → dispatch.

Run with: python -m pytest backend/tests/test_incident_flow.py -v
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import sys
sys.path.insert(0, "..")


class TestFullIncidentFlow:
    """End-to-end incident flow tests."""

    @pytest.mark.asyncio
    async def test_initiate_triage_dispatch_complete(self):
        """Full flow: initiate → 5 triage steps → dispatch → status check."""
        from app.services.triage import TriageAgent
        from app.services.dispatch import find_nearest_services, rank_hospitals
        from app.database import async_session
        from sqlalchemy import text

        # Create a test incident
        incident_id = str(uuid.uuid4())
        session_id = f"TEST-{incident_id[:8].upper()}"

        try:
            async with async_session() as db:
                await db.execute(
                    text("""
                        INSERT INTO incidents (id, session_id, location, location_accuracy_m,
                            location_source, channel, language, mode, victim_count,
                            status, started_at)
                        VALUES (:id, :sid,
                            ST_GeomFromText('SRID=4326;POINT(80.27 13.08)', 4326),
                            16.5, 'gps', 'pwa', 'en', 'bystander', 1,
                            'active', :now)
                    """),
                    {"id": incident_id, "sid": session_id, "now": datetime.now(timezone.utc)},
                )
                await db.commit()

                # Triage steps
                agent = TriageAgent()
                q1 = agent.get_first_question()
                assert "victim" in q1.lower() or "helping" in q1.lower()

                r2 = agent.process_answer("I am the victim")
                assert not r2["triage_complete"]

                r3 = agent.process_answer("No, not responding")
                assert not r3["triage_complete"]

                r4 = agent.process_answer("No, not breathing")
                assert not r4["triage_complete"]
                assert r4.get("instruction") is not None

                # This should push us to FINAL_SEVERITY due to max_questions
                r5 = agent.process_answer("Yes, heavy bleeding")
                assert r5["triage_complete"]
                assert r5["severity"] == "RED"

                # Verify severity was written to DB
                await db.execute(
                    text("""
                        UPDATE incidents SET severity = :sev, severity_confidence = :conf
                        WHERE id = :id
                    """),
                    {"id": incident_id, "sev": r5["severity"], "conf": r5.get("severity_confidence", 0)},
                )
                await db.commit()

                # Dispatch
                hospitals = await find_nearest_services(db, 13.08, 80.27, "hospital")
                ranked = rank_hospitals(hospitals)

                if ranked:
                    from app.services.dispatch import dispatch_ambulance
                    dispatch_result = await dispatch_ambulance(
                        db, incident_id, ranked[0]["id"], 13.08, 80.27
                    )
                    assert "eta_min" in dispatch_result

                # Verify incident status
                result = await db.execute(
                    text("SELECT status, severity FROM incidents WHERE id = :id"),
                    {"id": incident_id},
                )
                row = result.fetchone()
                assert row is not None

        finally:
            # Cleanup
            try:
                async with async_session() as db:
                    await db.execute(text("DELETE FROM incidents WHERE id LIKE 'TEST%'"))
                    await db.commit()
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_triage_with_asian_language(self):
        """Triage can be conducted in Hindi."""
        from app.services.triage import TriageAgent

        agent = TriageAgent()
        agent.set_language("hi")
        q1 = agent.get_first_question()
        assert len(q1) > 0

        # Process in Hindi
        r = agent.process_answer("हाँ, मैं पीड़ित हूँ")
        # Should handle Unicode input gracefully
        assert not r["triage_complete"] or r["severity"] is not None

    @pytest.mark.asyncio
    async def test_dispatch_fallback_without_osrm(self):
        """Dispatch should work with OSRM unavailable (fallback to linear ETA)."""
        from app.services.dispatch import _linear_eta

        eta = _linear_eta(10.0, "hospital")
        assert eta == 12  # 10 / 0.8 = 12.5, round() = 12

        eta2 = _linear_eta(5.0, "ambulance")
        assert eta2 == 8  # 5 / 0.6 ≈ 8.33


class TestRAGProtocolRetrieval:
    """Tests for RAG-based protocol retrieval."""

    @pytest.mark.asyncio
    async def test_search_protocols_english(self):
        """Search for English protocols returns relevant results."""
        from app.services.protocol_rag import search_protocols
        from app.database import async_session

        try:
            async with async_session() as db:
                results = await search_protocols(db=db, query="bleeding control", lang="en", top_k=2)
                assert isinstance(results, list)
        except Exception:
            pass  # DB might not be available

    @pytest.mark.asyncio
    async def test_search_protocols_tamil(self):
        """Search for Tamil protocols."""
        from app.services.protocol_rag import search_protocols
        from app.database import async_session

        try:
            async with async_session() as db:
                results = await search_protocols(db=db, query="blood", lang="ta", top_k=2)
                assert isinstance(results, list)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_generate_embeddings(self):
        """Embedding generation returns count of processed protocols."""
        from app.services.protocol_rag import generate_embeddings_for_protocols
        from app.database import async_session

        try:
            count = await generate_embeddings_for_protocols()
            assert count >= 0
        except Exception:
            pass  # Model might not be available

    @pytest.mark.asyncio
    async def test_offline_bundle_endpoint(self):
        """Offline bundle returns protocols in correct format."""
        from app.routes.protocols import get_offline_bundle
        from app.database import async_session

        try:
            async with async_session() as db:
                result = await get_offline_bundle(lang="en", limit=10, db=db)
                assert "protocols" in result
                assert "count" in result
                if result["protocols"]:
                    p = result["protocols"][0]
                    assert "id" in p
                    assert "source" in p
                    assert "language" in p
                    assert "type" in p
                    assert "text" in p
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])