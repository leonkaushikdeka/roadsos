"""
Triage service — LangGraph agent wrapper with RAG protocol retrieval.

This module bridges the FastAPI routes layer with the LangGraph triage agent
and the retrieval-augmented protocol corpus.

Exports: TRIAGE_FLOW, SEVERITY_MAP, classify_severity, _match,
         TriageAgent, LegacyTriageAgent, get_triage_agent
"""
import json
import os
from typing import Optional

from app.config import settings
from app.services.protocol_rag import search_protocols


# ─── Helper ─────────────────────────────────────────────────────────────────

def _match(answer: str, keywords: list[str]) -> bool:
    """Check if any keyword is a substring of the answer."""
    al = answer.lower().strip()
    return any(k in al for k in keywords)


# ─── Triage FSM Definition ──────────────────────────────────────────────────

TRIAGE_FLOW = {
    "INIT": {
        "question": "Are you the victim, or are you helping someone else?",
        "field": "role",
        "next": {
            "victim": "ASSESS_CONSCIOUSNESS",
            "helping": "ASSESS_CONSCIOUSNESS",
            "bystander": "ASSESS_CONSCIOUSNESS",
        },
    },
    "ASSESS_CONSCIOUSNESS": {
        "question": "Is the person responding to your voice or touch?",
        "field": "conscious",
        "next": {
            "yes": "ASSESS_BREATHING",
            "conscious": "ASSESS_BREATHING",
            "awake": "ASSESS_BREATHING",
            "responding": "ASSESS_BREATHING",
            "no": "ASSESS_AIRWAY",
            "unconscious": "ASSESS_AIRWAY",
            "not": "ASSESS_AIRWAY",
        },
    },
    "ASSESS_AIRWAY": {
        "question": "Is the person breathing? Look for chest rising/falling.",
        "field": "breathing",
        "instruction": "Tilt the head back gently to open the airway. Look, listen, and feel for breathing for 10 seconds.",
        "next": {
            "yes": "ASSESS_BLEEDING",
            "breathing": "ASSESS_BLEEDING",
            "shallow": "ASSESS_BLEEDING",
            "no": "CPR_INSTRUCTION",
            "not": "CPR_INSTRUCTION",
            "gasping": "CPR_INSTRUCTION",
        },
    },
    "ASSESS_BREATHING": {
        "question": "Is the person breathing normally?",
        "field": "breathing",
        "next": {
            "yes": "ASSESS_BLEEDING",
            "normal": "ASSESS_BLEEDING",
            "no": "CPR_INSTRUCTION",
            "not": "CPR_INSTRUCTION",
            "shallow": "ASSESS_BLEEDING",
            "gasping": "CPR_INSTRUCTION",
        },
    },
    "ASSESS_BLEEDING": {
        "question": "Is there any visible bleeding?",
        "field": "bleeding",
        "next": {
            "yes": "BLEEDING_CONTROL",
            "heavy": "BLEEDING_CONTROL",
            "bleeding": "BLEEDING_CONTROL",
            "blood": "BLEEDING_CONTROL",
            "no": "ASSESS_BONES",
            "none": "ASSESS_BONES",
        },
    },
    "BLEEDING_CONTROL": {
        "question": "Apply firm, direct pressure with a clean cloth. Are you doing this now?",
        "field": "bleeding_controlled",
        "instruction": "Apply firm pressure with a clean cloth directly on the wound. Keep pressing — do not lift to check. If blood soaks through, add another cloth on top.",
        "next": {
            "yes": "ASSESS_BONES",
            "done": "ASSESS_BONES",
            "no": "ASSESS_BONES",
            "help": "ASSESS_BONES",
        },
    },
    "ASSESS_BONES": {
        "question": "Does the person have any obvious broken bones or inability to move limbs?",
        "field": "fracture",
        "next": {
            "yes": "SPINAL_PRECAUTION",
            "broken": "SPINAL_PRECAUTION",
            "maybe": "SPINAL_PRECAUTION",
            "no": "FINAL_SEVERITY",
            "none": "FINAL_SEVERITY",
        },
    },
    "SPINAL_PRECAUTION": {
        "question": "Do NOT move the person. Hold their head and neck still with both hands. Understood?",
        "field": "spine_stable",
        "instruction": "Do NOT move the person. Hold head and neck still with both hands. Wait for professional help. Any movement could cause permanent spinal damage.",
        "next": {
            "yes": "FINAL_SEVERITY",
            "done": "FINAL_SEVERITY",
            "no": "FINAL_SEVERITY",
            "understood": "FINAL_SEVERITY",
        },
    },
    "CPR_INSTRUCTION": {
        "question": "Place the heel of your hand on the centre of the chest. Push hard and fast — 100-120 compressions/min, at least 5cm deep. Are you starting now?",
        "field": "cpr_started",
        "instruction": "Place heel of hand on centre of chest. Push hard and fast at 100–120 compressions/min. Depth: at least 5cm. Do not stop until help arrives.",
        "next": {
            "yes": "FINAL_SEVERITY",
            "started": "FINAL_SEVERITY",
            "no": "FINAL_SEVERITY",
        },
    },
}


SEVERITY_MAP = {
    "not_breathing": ("RED", 0.95),
    "unconscious_bleeding": ("RED", 0.90),
    "unconscious": ("RED", 0.85),
    "cpr_needed": ("RED", 0.92),
    "heavy_bleeding": ("YELLOW", 0.80),
    "bleeding_conscious": ("YELLOW", 0.75),
    "fracture_conscious": ("YELLOW", 0.70),
    "minor": ("GREEN", 0.85),
    "default": ("YELLOW", 0.65),
}


_NEGATIONS = ("no", "not", "none", "don't", "doesn't", "isn't", "can't", "cannot", "without")


def _first_word(answer: str) -> str:
    """Extract first word, stripped of punctuation."""
    word = answer.split()[0] if answer.split() else ""
    return word.rstrip(",.!?;:")


def _is_positive(answer: str, pos_keywords: tuple[str, ...]) -> bool:
    """Check if answer positively affirms any keyword (not negated)."""
    if not answer:
        return False
    negated = _first_word(answer) in _NEGATIONS
    has_keyword = any(k in answer for k in pos_keywords)
    return has_keyword and not negated


def _is_negative(answer: str) -> bool:
    """Check if answer is a negative response."""
    if not answer:
        return True
    return _first_word(answer) in _NEGATIONS


def classify_severity(answers: dict) -> tuple[str, float]:
    """Classify incident severity from collected triage answers."""
    breathing = answers.get("breathing", "").lower()
    conscious = answers.get("conscious", "").lower()
    bleeding = answers.get("bleeding", "").lower()
    fracture = answers.get("fracture", "").lower()
    cpr = answers.get("cpr_started", "").lower()

    # RED: life-threatening
    if (breathing and _is_negative(breathing)) or _is_positive(breathing, ("gasping",)) or _is_positive(cpr, ("yes", "started")):
        return SEVERITY_MAP["not_breathing"]
    if conscious and _is_negative(conscious) and _is_positive(bleeding, ("yes", "heavy", "bleeding", "blood")):
        return SEVERITY_MAP["unconscious_bleeding"]
    if conscious and _is_negative(conscious):
        return SEVERITY_MAP["unconscious"]

    # YELLOW: moderate
    if _is_positive(bleeding, ("yes", "heavy", "bleeding", "blood")) and _is_positive(conscious, ("yes", "awake", "responding", "conscious")):
        return SEVERITY_MAP["bleeding_conscious"]
    if _is_positive(bleeding, ("yes", "heavy", "bleeding", "blood")):
        return SEVERITY_MAP["heavy_bleeding"]
    if _is_positive(fracture, ("yes", "broken", "maybe")):
        return SEVERITY_MAP["fracture_conscious"]

    # GREEN: stable
    if _is_negative(bleeding) and _is_negative(fracture) and _is_positive(conscious, ("yes", "awake", "responding", "conscious")):
        return SEVERITY_MAP["minor"]

    return SEVERITY_MAP["default"]


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

def _build_protocol_query(answers: dict) -> str:
    """Build a search query from current triage answers."""
    query_parts = []
    if answers.get("bleeding"):
        query_parts.append("bleeding control")
    if answers.get("breathing") in ("no", "gasping", "shallow"):
        query_parts.append("CPR airway management")
    if answers.get("fracture"):
        query_parts.append("fracture spinal immobilization")
    if answers.get("conscious") in ("no", "unconscious"):
        query_parts.append("unconscious patient recovery position")
    return " ".join(query_parts)


async def inject_protocol_context(answers: dict, lang: str = "en", db=None) -> str:
    """
    Retrieve relevant protocol chunks via RAG and format them as context.
    Requires an async database session. Returns empty string on failure.
    """
    try:
        query = _build_protocol_query(answers)
        if not query:
            return ""

        chunks = await search_protocols(query, lang=lang, top_k=2, db=db)

        if chunks:
            context_lines = ["PROTOCOL GUIDANCE:"]
            for chunk in chunks:
                context_lines.append(f"  - {chunk['chunk_text'][:200]}")
            return "\n".join(context_lines)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Protocol RAG failed: {e}")
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
        self.state = "INIT"
        self.answers: dict = {}
        self.questions_asked = 0
        self.transcript: list[dict] = []
        self._lang = "en"

    def get_first_question(self) -> str:
        """Return the first triage question from the FSM."""
        self.state = "INIT"
        flow_entry = TRIAGE_FLOW.get("INIT", {})
        return flow_entry.get("question", "Are you the victim, or are you helping someone else?")

    def process_answer(self, answer: str) -> dict:
        """
        Process a user answer through the deterministic FSM.
        Returns the next question, instruction, severity, etc.
        """
        step = self.state
        flow_entry = TRIAGE_FLOW.get(step, {})
        field = flow_entry.get("field", "")
        answer_lower = answer.lower().strip()

        # Record the answer
        if field:
            self.answers[field] = answer_lower

        # Determine next step via FSM transitions
        next_map = flow_entry.get("next", {})
        next_step = None
        for keyword, target in next_map.items():
            if _match(answer_lower, [keyword]):
                next_step = target
                break
        if next_step is None:
            # Default: pick first transition target
            next_step = list(next_map.values())[0] if next_map else "FINAL_SEVERITY"

        # Enforce max questions
        self.questions_asked += 1
        if self.questions_asked >= self.max_questions and next_step != "FINAL_SEVERITY":
            next_step = "FINAL_SEVERITY"

        self.state = next_step

        result: dict = {
            "next_question": None,
            "instruction": flow_entry.get("instruction"),
            "severity": None,
            "severity_confidence": None,
            "triage_complete": False,
        }

        if next_step == "FINAL_SEVERITY":
            severity, confidence = classify_severity(self.answers)
            result["severity"] = severity
            result["severity_confidence"] = confidence
            result["triage_complete"] = True
        else:
            next_flow = TRIAGE_FLOW.get(next_step, {})
            result["next_question"] = next_flow.get("question", "Help is on the way.")
            if next_flow.get("instruction"):
                result["instruction"] = next_flow["instruction"]

        # Track transcript
        self.transcript.append({
            "step": step,
            "question": flow_entry.get("question", ""),
            "answer": answer_lower,
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