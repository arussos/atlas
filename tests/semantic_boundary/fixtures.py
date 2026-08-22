"""Fixture di supporto sintetiche per i test di tools.semantic_boundary. Nessun dato reale."""

from typing import Any, Dict, List, Optional

from tools.semantic_boundary.models import DialogueTurn


def make_turn(node_id: str, role: str = "user", text: Optional[str] = None) -> DialogueTurn:
    return DialogueTurn(node_id=node_id, role=role, text=text if text is not None else f"text-{node_id}")


def make_timeline(node_ids: List[str]) -> List[DialogueTurn]:
    """Timeline sintetica alternando ruoli user/assistant, un turno per node_id."""
    turns = []
    for i, node_id in enumerate(node_ids):
        role = "user" if i % 2 == 0 else "assistant"
        turns.append(make_turn(node_id, role=role, text=f"turn {i}: {node_id}"))
    return turns


def make_candidate_dict(
    *,
    candidate_id: str = "cand-1",
    conversation_id: str = "conv-1",
    before_node_id: str = "n2",
    after_node_id: str = "n3",
    candidate_class: str = "MEDIUM",
    candidate_score: float = 0.5,
    time_gap_seconds: Optional[float] = 120.0,
    time_gap_bucket: str = "short",
    lexical_shift_score: float = 0.3,
    opening_markers: Optional[List[str]] = None,
    closure_markers: Optional[List[str]] = None,
    resume_markers: Optional[List[str]] = None,
    transition_markers: Optional[List[str]] = None,
    intermediate_node_count: int = 0,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "conversation_id": conversation_id,
        "before_node_id": before_node_id,
        "after_node_id": after_node_id,
        "candidate_class": candidate_class,
        "candidate_score": candidate_score,
        "time_gap_seconds": time_gap_seconds,
        "time_gap_bucket": time_gap_bucket,
        "lexical_shift_score": lexical_shift_score,
        "opening_markers": opening_markers if opening_markers is not None else [],
        "closure_markers": closure_markers if closure_markers is not None else [],
        "resume_markers": resume_markers if resume_markers is not None else [],
        "transition_markers": transition_markers if transition_markers is not None else [],
        "intermediate_node_count": intermediate_node_count,
    }
