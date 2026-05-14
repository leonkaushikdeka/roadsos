"""
Triage service — LangGraph agent wrapper with RAG protocol retrieval.

This module bridges the FastAPI routes layer with the LangGraph triage agent
and the retrieval-augmented protocol corpus.
"""
import json
import os
from typing import Optional

from app.config import settings
from app.services.protocol_rag import search_protocols

# Import the legacy triage flow for backward compatibility (tests, etc.)
from app.services.triage import (
    TRIAGE_FLOW,
    SEVERITY_MAP,
    classify_severity,
)


# ─── LangGraph Agent Lazy Loader ─────────────────────────────────────────────

_graph = None


def _get_graph():
    """Lazily load the LangGraph triage graph."""
    global _graph
    if _graph is None:
        from agent.triage.agent import build_triage_graph
        _graph = build_triage_graph(memory=True)
    return _graph


# ─── Protocol-Enhanced Triage ────────────────────────────────────────────────

def _inject_protocol_context(answers: dict, lang: str = "en") -> str:
    """
    Retrieve relevant protocol chunks via RAG and format them as context.
    Injected into the agent's instruction field for each triage step.
    """
    try:
        # Build a query from the current answers
        query_parts = []
        if answers.get("bleeding"):
            query_parts.append("bleeding control")
        if answers.get("breathing") in ("no", "gasping", "shallow"):
            query_parts.append("CPR airway management")
        if answers.get("fracture"):
            query_parts.append("fracture spinal immobilization")
        if answers.get("conscious") in ("no", "unconscious"):
            query_parts.append("unconscious patient recovery position")

        if not query_parts:
            return ""

        query = " ".join(query_parts)
        chunks = search_protocols(query, lang=lang, top_k=2)

        if chunks:
            context_lines = ["⚕️ PROTOCOL GUIDANCE:"]
            for chunk in chunks:
                context_lines.append(f"  • {chunk['chunk_text'][:200]}")
            return "\n".join(context_lines)
    except Exception:
        # RAG failure should not break triage
        pass
    return ""


# ─── TriageAgent (LangGraph-backed) ─────────────────────────────────────────

class TriageAgent:
    """
    LangGraph-backed triage agent.

    When USE_MOCK_LLM=true (default), uses the deterministic FSM inside
    the LangGraph graph. No vLLM or model download required.

    When USE_MOCK_LLM=false, the graph's llm_tool node calls the LLM
    via tool-calling (vLLM on a single A10G GPU).
    """

    def __init__(self, max_questions: int = 5, use_llm: bool = False):
        self.max_questions = max_questions
        self.use_llm = use_llm
        self.graph = _get_graph()
        self.thread_id = f"session-{id(self)}"
        self.config = {"configurable": {"thread_id": self.thread_id}}

        # Current state snapshot
        self.state = "INIT"
        self.answers: dict = {}
        self.questions_asked = 0
        self.transcript: list[dict] = []
        self._lang = "en"

    def get_first_question(self) -> str:
        """Reset and return the first triage question."""
        from agent.triage.agent import TriageState
        initial = TriageState(
            current_step="INIT",
            transcript=[],
            num_questions=0,
            instruction="",
            triage_complete=False,
            max_questions=self.max_questions,
        )
        events = self.graph.stream(initial, self.config)
        for event in events:
            for node_name, node_state in event.items():
                if node_state.get("question"):
                    self.state = node_state.get("current_step", "INIT")
                    return node_state["question"]
        return "Are you the victim, or are you helping someone else?"

    def process_answer(self, answer: str) -> dict:
        """
        Process a user answer through the LangGraph agent.
        Returns the next question, instruction, severity, etc.
        """
        # Feed the answer into the graph
        input_state = {"current_step": self.state}

        # Map answer to the appropriate field based on current step
        step = self.state
        flow_entry = TRIAGE_FLOW.get(step, {})
        field = flow_entry.get("field", "")
        if field:
            input_state[field] = answer.lower().strip()

        events = self.graph.stream(input_state, self.config)

        result: dict = {
            "next_question": None,
            "instruction": None,
            "severity": None,
            "severity_confidence": None,
            "triage_complete": False,
        }

        for event in events:
            for node_name, node_state in event.items():
                if node_state.get("question"):
                    result["next_question"] = node_state["question"]
                if node_state.get("instruction"):
                    result["instruction"] = node_state["instruction"]
                if node_state.get("triage_complete"):
                    result["triage_complete"] = True
                if node_state.get("severity"):
                    result["severity"] = node_state["severity"]
                if node_state.get("severity_confidence"):
                    result["severity_confidence"] = node_state["severity_confidence"]
                if node_state.get("current_step"):
                    self.state = node_state["current_step"]

        # Inject RAG protocol context into instruction
        if result.get("instruction") and self._lang:
            protocol_ctx = _inject_protocol_context(self.answers, lang=self._lang)
            if protocol_ctx:
                result["instruction"] = f"{result['instruction']}\n\n{protocol_ctx}"

        # Track transcript
        self.questions_asked += 1
        self.transcript.append({
            "step": self.state,
            "question": flow_entry.get("question", ""),
            "answer": answer.lower().strip(),
        })
        if result.get("severity"):
            self.transcript[-1]["severity"] = result["severity"]
        if result.get("instruction"):
            self.transcript[-1]["instruction"] = result["instruction"]

        return result

    def set_language(self, lang: str):
        self._lang = lang

    def get_transcript(self) -> list[dict]:
        return self.transcript

    def get_state(self) -> str:
        return self.state


# ─── Legacy TriageAgent alias (for backward compatibility) ───────────────────

class LegacyTriageAgent:
    """
    Drop-in replacement using the original deterministic FSM.
    Used by tests and the WhatsApp/IVR webhooks that don't need LangGraph.
    """

    def __init__(self):
        self.state = "INIT"
        self.answers = {}
        self.questions_asked = 0

    def get_first_question(self) -> str:
        self.state = "INIT"
        return TRIAGE_FLOW["INIT"]["question"]

    def process_answer(self, answer: str) -> dict:
        if self.state == "FINAL_SEVERITY":
            severity, confidence = classify_severity(self.answers)
            return {
                "severity": severity,
                "severity_confidence": confidence,
                "triage_complete": True,
                "next_question": None,
            }

        current = TRIAGE_FLOW.get(self.state)
        if not current:
            return {"next_question": None, "triage_complete": True}

        self.questions_asked += 1
        answer_lower = answer.lower().strip()

        field = current["field"]
        self.answers[field] = answer_lower

        next_step = None
        for keyword, nxt in current.get("next", {}).items():
            if keyword in answer_lower or answer_lower in keyword:
                next_step = nxt
                break

        if not next_step:
            next_step = list(current["next"].values())[0]

        if self.questions_asked >= settings.max_triage_questions:
            next_step = "FINAL_SEVERITY"

        result = {
            "next_question": None,
            "instruction": None,
            "severity": None,
            "severity_confidence": None,
            "triage_complete": False,
        }

        if current.get("instruction"):
            result["instruction"] = current["instruction"]

        if next_step == "FINAL_SEVERITY":
            self.state = "FINAL_SEVERITY"
            severity, confidence = classify_severity(self.answers)
            result.update({
                "severity": severity,
                "severity_confidence": confidence,
                "triage_complete": True,
                "next_question": None,
            })
        else:
            self.state = next_step
            next_flow = TRIAGE_FLOW.get(next_step, {})
            result["next_question"] = next_flow.get("question", "Help is on the way. Stay on the line.")
            if next_flow.get("instruction"):
                result["instruction"] = next_flow["instruction"]

        return result


def get_triage_agent(use_langgraph: bool = True) -> TriageAgent:
    if use_langgraph:
        return TriageAgent()
    return LegacyTriageAgent()