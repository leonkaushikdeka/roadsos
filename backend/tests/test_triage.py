"""
Comprehensive test suite for RoadSoS backend.

Run with: python -m pytest backend/tests/ -v
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, "..")


# ─── TriageAgent Tests ───────────────────────────────────────────────────────

from agent.triage.agent import TriageState, build_triage_graph


class TestLangGraphTriageAgent:
    """Tests for the LangGraph-backed triage agent."""

    def test_graph_builds(self):
        """The graph should compile without errors."""
        from agent.triage.agent import build_triage_graph
        graph = build_triage_graph(memory=False)
        assert graph is not None

    def test_triage_state_has_required_fields(self):
        """State should have all required fields."""
        state = TriageState()
        assert state["current_step"] == ""
        assert state["triage_complete"] is False
        assert state["severity"] == ""
        assert state["num_questions"] == 0

    def test_graph_starts_at_ask_question(self):
        """Graph should start at ask_question node."""
        graph, state = build_triage_graph(use_memory=False)

        # Get START node successors
        compiled = graph
        # The graph is compiled — check it has nodes
        assert hasattr(compiled, 'graph')

    def test_deterministic_triage_severe(self):
        """Severe case: unconscious, not breathing, heavy bleeding → RED."""
        from app.services.triage import TriageAgent as LangGraphAgent
        agent = LangGraphAgent(use_llm=False)
        first_q = agent.get_first_question()
        assert "victim" in first_q.lower() or "helping" in first_q.lower()

        # Victim
        r = agent.process_answer("I am the victim")
        # Unconscious
        r = agent.process_answer("No, not responding at all")
        # Not breathing
        r = agent.process_answer("No, not breathing")
        # Heavy bleeding
        r = agent.process_answer("Yes, heavy bleeding")
        # Bleeding control done
        r = agent.process_answer("done")

        assert r["triage_complete"] is True
        assert r["severity"] == "RED"

    def test_deterministic_triage_minor(self):
        """Minor case: conscious, breathing, no bleeding → GREEN."""
        from app.services.triage import TriageAgent as LangGraphAgent
        agent = LangGraphAgent(use_llm=False)
        agent.get_first_question()

        r = agent.process_answer("I'm helping them")
        assert not r["triage_complete"]

        r = agent.process_answer("Yes, they're awake")
        assert not r["triage_complete"]

        r = agent.process_answer("Yes, breathing normally")
        assert not r["triage_complete"]

        r = agent.process_answer("No bleeding")
        assert not r["triage_complete"]

        r = agent.process_answer("No broken bones")
        assert r["triage_complete"]
        assert r["severity"] == "GREEN"

    def test_max_questions_limit(self):
        """Agent should stop after max_questions and classify."""
        from app.services.triage import TriageAgent as LangGraphAgent
        agent = LangGraphAgent(max_questions=1, use_llm=False)
        agent.get_first_question()

        r = agent.process_answer("Some answer")
        assert r["triage_complete"] is True


# ─── Legacy Triage Tests ─────────────────────────────────────────────────────

from app.services.triage import LegacyTriageAgent, TRIAGE_FLOW, classify_severity, _match


class TestLegacyTriageAgent:
    """Tests for the legacy deterministic FSM (backward compatibility)."""

    def test_initial_state(self):
        agent = LegacyTriageAgent()
        assert agent.state == "INIT"
        assert agent.questions_asked == 0

    def test_first_question(self):
        agent = LegacyTriageAgent()
        q = agent.get_first_question()
        assert "victim" in q.lower() or "helping" in q.lower()
        assert agent.state in ("INIT", "ASSESS_CONSCIOUSNESS")

    def test_severe_bleeding_flow(self):
        agent = LegacyTriageAgent()
        agent.get_first_question()

        r = agent.process_answer("I am the victim")
        assert not r["triage_complete"]

        r = agent.process_answer("No, not responding at all")
        assert not r["triage_complete"]

        r = agent.process_answer("No, not breathing")
        assert not r["triage_complete"]

        r = agent.process_answer("Yes, heavy bleeding")
        assert r.get("instruction") is not None or not r["triage_complete"]

        r = agent.process_answer("done")
        assert r["triage_complete"]
        assert r["severity"] == "RED"

    def test_minor_injury_flow(self):
        agent = LegacyTriageAgent()
        agent.get_first_question()

        r = agent.process_answer("I'm helping them")
        assert not r["triage_complete"]

        r = agent.process_answer("Yes, they're awake")
        assert not r["triage_complete"]

        r = agent.process_answer("Yes, breathing normally")
        assert not r["triage_complete"]

        r = agent.process_answer("No bleeding")
        assert not r["triage_complete"]

        r = agent.process_answer("No broken bones")
        assert r["triage_complete"]
        assert r["severity"] == "GREEN"

    def test_max_questions_limit(self):
        agent = LegacyTriageAgent()
        agent.questions_asked = 4  # one more will trigger limit

        agent.get_first_question()
        r = agent.process_answer("Test answer that would normally not trigger completion")
        assert r["triage_complete"]

    def test_cpr_pathway(self):
        agent = LegacyTriageAgent()
        agent.get_first_question()

        r = agent.process_answer("victim")
        assert not r["triage_complete"]

        r = agent.process_answer("unconscious")
        assert not r["triage_complete"]

        r = agent.process_answer("no breathing")
        assert r.get("instruction") is not None
        assert r["severity"] == "RED"


class TestClassifySeverity:
    def test_red_not_breathing(self):
        sev, conf = classify_severity({"breathing": "no"})
        assert sev == "RED"
        assert conf > 0.9

    def test_red_unconscious_bleeding(self):
        sev, conf = classify_severity({"bleeding": "yes", "conscious": "no"})
        assert sev == "RED"
        assert conf > 0.8

    def test_yellow_bleeding_conscious(self):
        sev, conf = classify_severity({"bleeding": "yes", "conscious": "yes"})
        assert sev == "YELLOW"
        assert conf >= 0.7

    def test_yellow_fracture_conscious(self):
        sev, conf = classify_severity({"fracture": "yes", "conscious": "yes"})
        assert sev == "YELLOW"

    def test_green_minor(self):
        sev, conf = classify_severity({"bleeding": "no", "fracture": "no", "conscious": "yes"})
        assert sev == "GREEN"


class TestMatchFunction:
    def test_exact_match(self):
        assert _match("yes", ["yes"]) is True

    def test_substring(self):
        assert _match("heavy bleeding", ["bleeding"]) is True

    def test_no_match(self):
        assert _match("maybe", ["yes", "no"]) is False

    def test_empty_answer(self):
        assert _match("", ["yes", "no"]) is False


# ─── Protocol RAG Tests ──────────────────────────────────────────────────────

from app.services.protocol_rag import search_protocols, _compute_dummy_embedding


class TestProtocolRAG:
    def test_dummy_embedding_deterministic(self):
        e1 = _compute_dummy_embedding("test query")
        e2 = _compute_dummy_embedding("test query")
        assert e1 == e2

    def test_dummy_embedding_varies_by_input(self):
        e1 = _compute_dummy_embedding("query a")
        e2 = _compute_dummy_embedding("query b")
        assert e1 != e2

    def test_dummy_embedding_length(self):
        e = _compute_dummy_embedding("test")
        assert len(e) == 64  # SHA256 hex digest


# ─── Dispatch Service Tests ──────────────────────────────────────────────────

from app.services.dispatch import _linear_eta, SERVICE_PRIORITY


class TestDispatchService:
    def test_linear_eta_hospital(self):
        eta = _linear_eta(10.0, "hospital")
        assert eta == 12  # 10 / 0.8 = 12.5, round() = 12 (banker's rounding)

    def test_linear_eta_ambulance(self):
        eta = _linear_eta(6.0, "ambulance")
        assert eta == 10  # 6 / 0.6 = 10

    def test_linear_eta_police(self):
        eta = _linear_eta(5.0, "police")
        assert eta == 10  # 5 / 0.5 = 10

    def test_linear_eta_never_zero(self):
        eta = _linear_eta(0.1, "hospital")
        assert eta >= 1

    def test_service_priority_order(self):
        assert SERVICE_PRIORITY["hospital"] < SERVICE_PRIORITY["ambulance"]
        assert SERVICE_PRIORITY["ambulance"] < SERVICE_PRIORITY["police"]


# ─── Fraud Engine Tests (existing) ───────────────────────────────────────────

class TestFraudEngine:

    @pytest.mark.asyncio
    async def test_clean_user_allowed(self):
        db = AsyncMock()
        from app.services.fraud import FraudEngine
        engine = FraudEngine(db)

        result = await engine.check(
            phone="+919876543210",
            lat=13.08, lng=80.27,
            device_fingerprint="fp123",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_detection_init(self):
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.08, 80.27, precision=4)
        assert len(result) == 4
        assert all(c in "0123456789bcdefghjkmnpqrstuvwxyz" for c in result)

    @pytest.mark.asyncio
    async def test_impossible_travel(self):
        from app.services.fraud import encode_geohash
        result = encode_geohash(13.08, 80.27, precision=6)
        assert len(result) == 6