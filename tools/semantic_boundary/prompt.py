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
# Gold Pilot: quel tuning è esplicitamente fuori scope per M4.2b-A/C.
#
# v0.2 (M4.2b-C): stessa struttura generale di v0.1, con una definizione
# più operativa di EPISODE (unit of work, non project/topic/system) e una
# sezione esplicita su candidate_score per prevenire confidence anchoring.
# Nessun esempio derivato dal Gold Pilot: vedi
# docs/M4.2B_SEMANTIC_BOUNDARY_RESOLVER.md, sezione M4.2b-C, §6.
TASK_INSTRUCTION = """\
TASK:
Determine whether the two sides of this candidate transition belong to the \
SAME_EPISODE, a BOUNDARY, or are UNCERTAIN.

DEFINITION OF EPISODE:
An episode is a coherent operational work unit centered on one concrete \
task, problem, decision, investigation, or deliverable. It is defined by \
what is being worked on, not by the surrounding project, customer, \
system, technology, or general topic.

DEFINITION OF SAME_EPISODE:
The two sides belong to the same coherent operational work unit, \
including its normal implementation, review, testing, debugging, \
correction and immediate follow-up.

DEFINITION OF BOUNDARY:
A new coherent operational work unit begins: a materially different \
task, problem, decision, investigation, or deliverable, even if it \
starts immediately after the previous one and even if it belongs to the \
same project.

DEFINITION OF UNCERTAIN:
The supplied context does not allow a semantically reliable distinction \
between SAME_EPISODE and BOUNDARY.

WHAT DOES NOT, BY ITSELF, IMPLY SAME_EPISODE:
- the same project;
- the same customer;
- the same system or technology;
- the same broad topic;
- temporal proximity (a new work unit can start immediately after the \
previous one).
None of the above is sufficient on its own to decide SAME_EPISODE. The \
decision must rest on whether the concrete task, problem, decision, \
investigation, or deliverable is the same or has materially changed.

IMPORTANT DISTINCTIONS — remain SAME_EPISODE:
- a new substep of the same work unit;
- question -> answer;
- implementation -> review;
- implementation -> test;
- test -> fix -> retest;
- debugging of the same problem;
- correction of the same deliverable;
- a new tool or strategy for the same problem;
- an ordinary immediate follow-up of the same work unit.

IMPORTANT DISTINCTIONS — can be BOUNDARY:
- a new deliverable;
- an explicit move to a materially different task, problem, decision, or \
investigation, even inside the same project, customer, system, or topic.
None of the following, by itself, is sufficient to establish a boundary: \
a lexical shift alone, a new message alone, a change of interlocutor \
alone, a time gap alone, or a marker alone. A boundary requires that a \
new coherent operational work unit has actually started.

CANDIDATE_SCORE AND OTHER M4.2A SIGNALS:
candidate_score is a Boundary Evidence Score produced by a deterministic \
upstream detector. It is NOT a probability of BOUNDARY, NOT a semantic \
confidence, and NOT a target value for your confidence. Do not copy \
candidate_score into your confidence, do not derive your confidence from \
it mathematically, and do not treat candidate_class as a pre-made \
decision. candidate_score, candidate_class, time gap, lexical shift, and \
markers are supporting evidence only, to be weighed alongside the \
dialogue context — never a substitute for your own semantic judgment. \
Your confidence must reflect only how reliable you consider your own \
semantic classification to be, given the available context.

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
