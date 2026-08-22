"""
M4.2b-A — Costruzione deterministica dell'input per il judge.

Nessun provider LLM è implementato in questo pass. Questo modulo prepara
solo la rappresentazione strutturata e stabile che un futuro adapter
(cloud, Ollama, ecc.) userebbe per interrogare un modello — instruction
testuale in inglese + contesto + evidenza, sempre nello stesso ordine e
formato per la stessa request. Nessun chain-of-thought viene richiesto:
il judge deve restituire solo decision/confidence/reason, mai un
ragionamento esteso.
"""

from typing import Any, Dict

from tools.semantic_boundary.models import SemanticResolutionRequest

# Testo di istruzione statico e deterministico. In inglese per convenzione
# Atlas (testo tecnico di prompt in inglese, vedi CLAUDE.md/istruzioni
# M4.2b). Deliberatamente privo di esempi few-shot o di tuning contro il
# Gold Pilot: quel tuning è esplicitamente fuori scope per M4.2b-A.
TASK_INSTRUCTION = """\
TASK:
Determine whether the two sides of this candidate transition belong to the \
SAME_EPISODE, a BOUNDARY, or are UNCERTAIN.

DEFINITION OF SAME_EPISODE:
Same coherent professional task, problem, decision, or deliverable, \
including its normal implementation, review, testing, debugging, \
correction and immediate follow-up.

DEFINITION OF BOUNDARY:
A new coherent professional work unit begins, with a materially different \
goal, problem, or deliverable, even if it belongs to the same project.

DEFINITION OF UNCERTAIN:
The supplied context is insufficient, or the transition itself does not \
allow a reliable decision.

IMPORTANT DISTINCTIONS:
- a new substep is not a boundary;
- question -> answer is not a boundary;
- implementation -> review is not a boundary;
- test -> fix -> retest is not a boundary;
- a new tool or strategy for the same problem is not a boundary;
- a new deliverable can be a boundary;
- an explicit move to a different problem can be a boundary;
- a long time gap is evidence, not proof;
- a lexical shift is evidence, not proof;
- markers are evidence, not proof.

OUTPUT:
Return only a structured decision (SAME_EPISODE, BOUNDARY, or UNCERTAIN), \
a confidence in [0.0, 1.0], and a short, concise, auditable, semantic \
reason. Do not include chain-of-thought or long narrative explanations.\
"""


def build_judge_input(request: SemanticResolutionRequest) -> Dict[str, Any]:
    """
    Costruisce il payload strutturato e deterministico da sottoporre al
    judge: stessa request semantica -> stesso payload, sempre. Non
    include mai policy/istruzioni ridondanti oltre TASK_INSTRUCTION, né
    dati esterni alla request (nessuna retrieval, nessuna altra
    conversazione, nessuna memoria di progetto nascosta).
    """
    return {
        "task_instruction": TASK_INSTRUCTION,
        "candidate_id": request.candidate_id,
        "conversation_id": request.conversation_id,
        "before_node_id": request.before_node_id,
        "after_node_id": request.after_node_id,
        "before_context": [turn.to_dict() for turn in request.before_context],
        "after_context": [turn.to_dict() for turn in request.after_context],
        "m4_2a_evidence": request.m4_2a_evidence.to_dict(),
    }


def render_judge_prompt(request: SemanticResolutionRequest) -> str:
    """
    Rende il judge input come testo piano deterministico, per adapter
    testuali (es. un modello locale via prompt libero). La struttura è
    stabile: stessa request -> stesso testo, sempre.
    """
    payload = build_judge_input(request)

    lines = [payload["task_instruction"], "", "CONTEXT BEFORE:"]
    for turn in payload["before_context"]:
        lines.append(f"- [{turn['role']}] ({turn['node_id']}): {turn['text']}")

    lines.append("")
    lines.append("CONTEXT AFTER:")
    for turn in payload["after_context"]:
        lines.append(f"- [{turn['role']}] ({turn['node_id']}): {turn['text']}")

    evidence = payload["m4_2a_evidence"]
    lines.append("")
    lines.append("M4.2A EVIDENCE (supporting, not decisive):")
    lines.append(f"- candidate_class: {evidence['candidate_class']}")
    lines.append(f"- candidate_score: {evidence['candidate_score']}")
    lines.append(f"- time_gap_seconds: {evidence['time_gap_seconds']}")
    lines.append(f"- time_gap_bucket: {evidence['time_gap_bucket']}")
    lines.append(f"- lexical_shift_score: {evidence['lexical_shift_score']}")
    lines.append(f"- opening_markers: {evidence['opening_markers']}")
    lines.append(f"- closure_markers: {evidence['closure_markers']}")
    lines.append(f"- resume_markers: {evidence['resume_markers']}")
    lines.append(f"- transition_markers: {evidence['transition_markers']}")
    lines.append(f"- intermediate_node_count: {evidence['intermediate_node_count']}")

    return "\n".join(lines)
