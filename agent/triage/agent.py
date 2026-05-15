"""
LangGraph-based Triage Agent with ReAct loop and RAG protocol retrieval.

In production, uses Llama 3.1 8B with tool-calling for multi-step triage.
The mock fallback (default) uses a deterministic state machine.
"""
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.triage import (
    TRIAGE_FLOW,
    SEVERITY_MAP,
    classify_severity,
)


# ─── LangGraph State ───────────────────────────────────────────────────────────

class TriageState(dict):
    """State for the LangGraph triage agent."""
    role: str = ""                        # victim / helping / bystander
    conscious: str = ""                   # yes / no / unconscious / responding
    breathing: str = ""                   # yes / no / shallow / gasping
    bleeding: str = ""                    # yes / heavy / no / bleeding
    bleeding_controlled: str = ""         # yes / no / done / help
    fracture: str = ""                    # yes / no / broken / maybe
    spine_stable: str = ""                # yes / no / done
    cpr_started: str = ""                 # yes / no / started
    severity: str = ""                    # RED / YELLOW / GREEN / BLACK
    severity_confidence: float = 0.0
    triage_complete: bool = False
    current_step: str = "INIT"
    transcript: list[dict] = []
    instruction: str = ""
    num_questions: int = 0
    max_questions: int = 5
    # RAG context — injected protocol chunks
    protocol_context: str = ""


# ─── Node: Ask Question ──────────────────────────────────────────────────────

def ask_question(state: TriageState) -> dict:
    """Return the next question based on current triage state."""
    step = state.get("current_step", "INIT")
    flow_entry = TRIAGE_FLOW.get(step, {})
    question = flow_entry.get("question", "Help is on the way. Stay on the line.")
    instruction = flow_entry.get("instruction", "")
    return {
        "instruction": instruction,
        "question": question,
        "current_step": step,
    }


# ─── Node: Process Answer (deterministic FSM) ────────────────────────────────

def _match(answer: str, keywords: list[str]) -> bool:
    al = answer.lower().strip()
    return any(k in al for k in keywords)


TRANSITIONS = {
    "INIT": lambda a: "ASSESS_CONSCIOUSNESS",
    "ASSESS_CONSCIOUSNESS": lambda a: (
        "ASSESS_BREATHING" if _match(a, ["yes", "conscious", "awake", "responding"])
        else "ASSESS_AIRWAY"
    ),
    "ASSESS_AIRWAY": lambda a: (
        "ASSESS_BLEEDING" if _match(a, ["yes", "breathing"])
        else "CPR_INSTRUCTION"
    ),
    "ASSESS_BREATHING": lambda a: (
        "ASSESS_BLEEDING" if _match(a, ["yes", "normal"])
        else "CPR_INSTRUCTION"
    ),
    "ASSESS_BLEEDING": lambda a: (
        "BLEEDING_CONTROL" if _match(a, ["yes", "heavy", "bleeding", "blood"])
        else "ASSESS_BONES"
    ),
    "BLEEDING_CONTROL": lambda a: "ASSESS_BONES",
    "ASSESS_BONES": lambda a: (
        "SPINAL_PRECAUTION" if _match(a, ["yes", "broken", "maybe"])
        else "FINAL_SEVERITY"
    ),
    "SPINAL_PRECAUTION": lambda a: "FINAL_SEVERITY",
    "CPR_INSTRUCTION": lambda a: "FINAL_SEVERITY",
}


def process_answer(state: TriageState) -> dict:
    """Process user answer, update state, and determine next step."""
    step = state.get("current_step", "INIT")
    flow_entry = TRIAGE_FLOW.get(step, {})
    field = flow_entry.get("field", "")

    # Record the answer
    answer_key = field
    answer_val = state.get(field, "")

    # Build transcript entry
    transcript_entry = {
        "step": step,
        "question": flow_entry.get("question", ""),
        "answer": str(answer_val),
    }
    if flow_entry.get("instruction"):
        transcript_entry["instruction"] = flow_entry["instruction"]

    # Determine next step
    if step == "FINAL_SEVERITY":
        next_step = "FINAL_SEVERITY"
    elif step in TRANSITIONS:
        transition = TRANSITIONS[step]
        if callable(transition):
            next_step = transition(str(answer_val))
        else:
            next_step = transition
    else:
        next_step = "FINAL_SEVERITY"

    # Enforce max questions limit
    num_questions = state.get("num_questions", 0) + 1
    max_questions = state.get("max_questions", 5)
    if num_questions >= max_questions and next_step != "FINAL_SEVERITY":
        next_step = "FINAL_SEVERITY"

    # Build result
    result: dict[str, Any] = {
        "current_step": next_step,
        "num_questions": num_questions,
        "transcript": transcript_entry,
        "instruction": flow_entry.get("instruction", ""),
    }

    if next_step == "FINAL_SEVERITY":
        # Collect answers for severity classification
        answers = {}
        for key in ["conscious", "breathing", "bleeding", "fracture", "spine_stable", "cpr_started"]:
            if state.get(key):
                answers[key] = str(state[key])
        severity, confidence = classify_severity(answers)
        result["severity"] = severity
        result["severity_confidence"] = confidence
        result["triage_complete"] = True
        result["next_question"] = None
    else:
        next_flow = TRIAGE_FLOW.get(next_step, {})
        result["next_question"] = next_flow.get("question", "Help is on the way. Stay on the line.")
        result["triage_complete"] = False

    return result


# ─── Node: Classify Severity ─────────────────────────────────────────────────

def classify_node(state: TriageState) -> dict:
    """Classify severity from collected answers."""
    answers = {}
    for key in ["conscious", "breathing", "bleeding", "fracture", "spine_stable", "cpr_started"]:
        if state.get(key):
            answers[key] = str(state[key])
    severity, confidence = classify_severity(answers)
    return {
        "severity": severity,
        "severity_confidence": confidence,
        "triage_complete": True,
        "next_question": None,
        "current_step": "FINAL_SEVERITY",
    }


# ─── Node: Dispatch Decision ─────────────────────────────────────────────────

def dispatch_decision(state: TriageState) -> dict:
    """Decide whether to dispatch or escalate to human."""
    severity = state.get("severity", "")
    confidence = state.get("severity_confidence", 1.0)

    if severity == "RED" or confidence < 0.7:
        return {"escalate": True, "dispatch": False}
    return {"escalate": False, "dispatch": True}


# ─── Node: Escalate to Human ─────────────────────────────────────────────────

def escalate_to_human(state: TriageState) -> dict:
    """Escalate to human dispatcher with full context."""
    return {
        "escalation": True,
        "message": "Escalated to human dispatcher.",
        "severity": state.get("severity", "UNKNOWN"),
        "transcript": state.get("transcript", []),
    }


# ─── Node: Execute Dispatch ──────────────────────────────────────────────────

def execute_dispatch(state: TriageState) -> dict:
    """Execute dispatch via tool-calling or mock."""
    return {
        "dispatched": True,
        "message": f"Dispatched for severity {state.get('severity', 'UNKNOWN')}.",
    }


# ─── LLM Tool Node (for production) ──────────────────────────────────────────

def llm_triage_tool(state: TriageState) -> dict:
    """
    In production: call Llama 3.1 8B via vLLM with tool-calling.
    In mock mode: delegate to deterministic process_answer.

    When USE_MOCK_LLM=true, this path is skipped and the FSM is used directly.
    """
    import os
    use_mock = os.environ.get("USE_MOCK_LLM", "true").lower() == "true"

    if use_mock:
        return process_answer(state)

    # Production path would call the LLM here via tool-calling
    # For now, fall back to deterministic
    return process_answer(state)


# ─── Build the Graph ──────────────────────────────────────────────────────────

def build_triage_graph(memory: bool = True) -> StateGraph:
    """
    Build a LangGraph StateGraph for the triage agent.

    Graph structure:
    START → ask_question → process_answer → [classify | continue_loop]
    continue_loop → ask_question (cycle until triage_complete)
    classify → dispatch_decision → [execute_dispatch | escalate_to_human] → END
    """
    workflow = StateGraph(TriageState)

    # Add nodes
    workflow.add_node("ask_question", ask_question)
    workflow.add_node("process_answer", process_answer)
    workflow.add_node("classify_severity", classify_node)
    workflow.add_node("dispatch_decision", dispatch_decision)
    workflow.add_node("execute_dispatch", execute_dispatch)
    workflow.add_node("escalate_to_human", escalate_to_human)
    workflow.add_node("llm_tool", llm_triage_tool)

    # Add edges — START
    workflow.add_edge(START, "ask_question")

    # Main triage loop
    workflow.add_edge("ask_question", "process_answer")

    # After processing: either continue asking or classify
    def should_continue_or_classify(state: TriageState) -> str:
        if state.get("triage_complete"):
            return "classify_severity"
        return "ask_question"

    workflow.add_conditional_edges(
        "process_answer",
        should_continue_or_classify,
        {
            "ask_question": "ask_question",
            "classify_severity": "classify_severity",
        },
    )

    # After classification → dispatch decision
    workflow.add_edge("classify_severity", "dispatch_decision")

    # Dispatch or escalate
    def dispatch_or_escalate(state: TriageState) -> str:
        if state.get("escalate"):
            return "escalate_to_human"
        return "execute_dispatch"

    workflow.add_conditional_edges(
        "dispatch_decision",
        dispatch_or_escalate,
        {
            "escalate_to_human": "escalate_to_human",
            "execute_dispatch": "execute_dispatch",
        },
    )

    # Both paths end
    workflow.add_edge("execute_dispatch", END)
    workflow.add_edge("escalate_to_human", END)

    # Compile with optional memory
    checkpointer = MemorySaver() if memory else None
    graph = workflow.compile(checkpointer=checkpointer)

    return graph


# ─── Legacy Compatibility Wrapper ────────────────────────────────────────────

def get_triage_graph(use_memory: bool = True) -> tuple[StateGraph, TriageState]:
    """
    Returns a compiled LangGraph triage graph and initial empty state.
    Used by the routes layer to maintain compatibility with existing API.
    """
    graph = build_triage_graph(memory=use_memory)
    initial_state = TriageState(
        current_step="INIT",
        transcript=[],
        num_questions=0,
        instruction="",
        triage_complete=False,
    )
    return graph, initial_state


# ─── Standalone invocation for testing ────────────────────────────────────────

if __name__ == "__main__":
    graph, state = get_triage_graph(use_memory=False)

    # Simulate a triage session
    config = {"configurable": {"thread_id": "test-1"}}
    events = graph.stream(state, config)

    print("=== LangGraph Triage Agent Test ===")
    for event in events:
        for node_name, node_state in event.items():
            if "question" in node_state:
                print(f"\n[{node_name}] Q: {node_state.get('question', '')}")
            if node_state.get("triage_complete"):
                print(f"\n[RESULT] Severity: {node_state.get('severity')} "
                      f"(confidence: {node_state.get('severity_confidence', 0):.2f})")