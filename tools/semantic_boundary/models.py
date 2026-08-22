"""
M4.2b-A — Contratto dati del Semantic Boundary Resolver.

Definisce la richiesta di risoluzione semantica (SemanticResolutionRequest),
il suo contesto di dialogo (DialogueTurn), l'evidenza deterministica
compatta ereditata da M4.2a (SemanticEvidence) e l'esito della risoluzione
(SemanticResolution).

Deliberatamente autonomo da tools.episodes: SemanticEvidence NON importa
tools.episodes.models.BoundaryCandidate. M4.2a resta la fonte autorevole
della candidate generation, ma M4.2b consuma solo un sottoinsieme
compatto e stabile dei suoi campi (vedi docs/M4.2B_SEMANTIC_BOUNDARY_RESOLVER.md,
sezione "Evidence policy"). candidate_class/candidate_score sono evidenza
di supporto, mai la decisione stessa — vedi resolver.py e evaluation.py.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Versione di questo contratto/pipeline di risoluzione semantica.
# Distinta da FEATURE_VERSION di M4.2a (tools/episodes/models.py) e da
# ACNF_SCHEMA_VERSION (tools/chatgpt/models.py): evolvono indipendentemente.
RESOLVER_VERSION = "m4.2b-0.1"

DECISION_SAME_EPISODE = "SAME_EPISODE"
DECISION_BOUNDARY = "BOUNDARY"
DECISION_UNCERTAIN = "UNCERTAIN"

VALID_DECISIONS = frozenset({DECISION_SAME_EPISODE, DECISION_BOUNDARY, DECISION_UNCERTAIN})


class SemanticBoundaryError(Exception):
    """Eccezione base del package. Mai catturata silenziosamente dai chiamanti."""


class RequestValidationError(SemanticBoundaryError):
    """Sollevata quando una SemanticResolutionRequest (o i suoi componenti) è malformata."""


class ResolutionValidationError(SemanticBoundaryError):
    """Sollevata quando un esito di risoluzione (decision/confidence/...) è invalido."""


@dataclass
class DialogueTurn:
    """
    Un singolo turno di dialogo visibile incluso nel contesto del judge.

    Corrisponde a un nodo dialogue visibile della Dialogue Timeline
    Projection di M4.2a (content_type in {text, multimodal_text}) — mai a
    un nodo thoughts/reasoning_recap. content_type è opzionale e puramente
    informativo per il judge: la selezione di visibilità è già avvenuta a
    monte, in M4.2a.
    """

    node_id: str
    role: str
    text: str
    content_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "text": self.text,
            "content_type": self.content_type,
        }


@dataclass
class SemanticEvidence:
    """
    Sottoinsieme compatto e strutturato dell'evidenza deterministica di
    M4.2a, passato al judge come evidenza di supporto — mai come decisione.

    candidate_class (LOW/MEDIUM/HIGH) e candidate_score sono un Boundary
    Evidence Score, non una probabilità di boundary semantico (vedi Gold
    Pilot 001, docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md). Il
    resolver e l'evaluator non devono mai derivare la decisione da questi
    due campi da soli.
    """

    candidate_class: str
    candidate_score: float
    time_gap_seconds: Optional[float]
    time_gap_bucket: str
    lexical_shift_score: float
    opening_markers: List[str] = field(default_factory=list)
    closure_markers: List[str] = field(default_factory=list)
    resume_markers: List[str] = field(default_factory=list)
    transition_markers: List[str] = field(default_factory=list)
    intermediate_node_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_class": self.candidate_class,
            "candidate_score": self.candidate_score,
            "time_gap_seconds": self.time_gap_seconds,
            "time_gap_bucket": self.time_gap_bucket,
            "lexical_shift_score": self.lexical_shift_score,
            "opening_markers": list(self.opening_markers),
            "closure_markers": list(self.closure_markers),
            "resume_markers": list(self.resume_markers),
            "transition_markers": list(self.transition_markers),
            "intermediate_node_count": self.intermediate_node_count,
        }


@dataclass
class SemanticResolutionRequest:
    """
    Richiesta di risoluzione semantica per una singola transizione
    candidate. Contiene tutto e solo ciò che un SemanticJudge può usare
    per decidere — nessuna memoria di progetto nascosta, nessuna
    retrieval, nessuna altra conversazione (vedi context.py).
    """

    candidate_id: str
    conversation_id: str

    before_node_id: str
    after_node_id: str

    before_context: List[DialogueTurn]
    after_context: List[DialogueTurn]

    m4_2a_evidence: SemanticEvidence

    resolver_version: str = RESOLVER_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "conversation_id": self.conversation_id,
            "before_node_id": self.before_node_id,
            "after_node_id": self.after_node_id,
            "before_context": [turn.to_dict() for turn in self.before_context],
            "after_context": [turn.to_dict() for turn in self.after_context],
            "m4_2a_evidence": self.m4_2a_evidence.to_dict(),
            "resolver_version": self.resolver_version,
        }


@dataclass
class SemanticResolution:
    """
    Esito di risoluzione semantica per una candidate transition.

    confidence è auto-valutazione del judge/resolver, NON una probabilità
    calibrata globalmente finché una validazione futura non lo dimostra
    (vedi docs, sezione "Confidence semantics").
    """

    candidate_id: str
    decision: str
    confidence: float
    reason: str
    resolver_version: str
    judge_name: str
    judge_version: str
    resolution_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "resolver_version": self.resolver_version,
            "judge_name": self.judge_name,
            "judge_version": self.judge_version,
            "resolution_hash": self.resolution_hash,
        }


def validate_dialogue_turn(turn: DialogueTurn) -> None:
    if not isinstance(turn.node_id, str) or not turn.node_id:
        raise RequestValidationError("DialogueTurn.node_id must be a non-empty string")
    if not isinstance(turn.role, str) or not turn.role:
        raise RequestValidationError("DialogueTurn.role must be a non-empty string")
    if not isinstance(turn.text, str):
        raise RequestValidationError("DialogueTurn.text must be a string")


def validate_evidence(evidence: SemanticEvidence) -> None:
    if not isinstance(evidence.candidate_class, str) or not evidence.candidate_class:
        raise RequestValidationError("SemanticEvidence.candidate_class must be a non-empty string")
    if not isinstance(evidence.candidate_score, (int, float)):
        raise RequestValidationError("SemanticEvidence.candidate_score must be numeric")
    if evidence.time_gap_seconds is not None and evidence.time_gap_seconds < 0:
        raise RequestValidationError("SemanticEvidence.time_gap_seconds must be >= 0 when present")
    if not isinstance(evidence.time_gap_bucket, str) or not evidence.time_gap_bucket:
        raise RequestValidationError("SemanticEvidence.time_gap_bucket must be a non-empty string")
    if not isinstance(evidence.lexical_shift_score, (int, float)):
        raise RequestValidationError("SemanticEvidence.lexical_shift_score must be numeric")
    for marker_field_name in ("opening_markers", "closure_markers", "resume_markers", "transition_markers"):
        markers = getattr(evidence, marker_field_name)
        if not isinstance(markers, list) or not all(isinstance(m, str) for m in markers):
            raise RequestValidationError(f"SemanticEvidence.{marker_field_name} must be a list of strings")
    if not isinstance(evidence.intermediate_node_count, int) or evidence.intermediate_node_count < 0:
        raise RequestValidationError("SemanticEvidence.intermediate_node_count must be a non-negative int")


def validate_request(request: SemanticResolutionRequest) -> None:
    """
    Valida una SemanticResolutionRequest end-to-end. Non solleva mai
    silenziosamente: ogni violazione produce un RequestValidationError con
    un messaggio specifico.
    """
    if not isinstance(request.candidate_id, str) or not request.candidate_id:
        raise RequestValidationError("candidate_id is required and must be a non-empty string")
    if not isinstance(request.conversation_id, str) or not request.conversation_id:
        raise RequestValidationError("conversation_id is required and must be a non-empty string")
    if not isinstance(request.before_node_id, str) or not request.before_node_id:
        raise RequestValidationError("before_node_id is required and must be a non-empty string")
    if not isinstance(request.after_node_id, str) or not request.after_node_id:
        raise RequestValidationError("after_node_id is required and must be a non-empty string")

    if not request.before_context:
        raise RequestValidationError("before_context must contain at least the endpoint turn")
    if not request.after_context:
        raise RequestValidationError("after_context must contain at least the endpoint turn")

    for turn in request.before_context:
        validate_dialogue_turn(turn)
    for turn in request.after_context:
        validate_dialogue_turn(turn)

    if request.before_context[-1].node_id != request.before_node_id:
        raise RequestValidationError("before_context must end with the before_node_id endpoint turn")
    if request.after_context[0].node_id != request.after_node_id:
        raise RequestValidationError("after_context must start with the after_node_id endpoint turn")

    validate_evidence(request.m4_2a_evidence)

    if not isinstance(request.resolver_version, str) or not request.resolver_version:
        raise RequestValidationError("resolver_version is required and must be a non-empty string")


def validate_decision(decision: str) -> None:
    if decision not in VALID_DECISIONS:
        raise ResolutionValidationError(
            f"invalid decision {decision!r}: must be one of {sorted(VALID_DECISIONS)}"
        )


def validate_confidence(confidence: float) -> None:
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ResolutionValidationError("confidence must be numeric")
    if not (0.0 <= float(confidence) <= 1.0):
        raise ResolutionValidationError(f"confidence must be within [0.0, 1.0], got {confidence!r}")


def validate_resolution(resolution: SemanticResolution) -> None:
    if not isinstance(resolution.candidate_id, str) or not resolution.candidate_id:
        raise ResolutionValidationError("candidate_id is required and must be a non-empty string")
    validate_decision(resolution.decision)
    validate_confidence(resolution.confidence)
    if not isinstance(resolution.reason, str) or not resolution.reason:
        raise ResolutionValidationError("reason must be a non-empty string")
    if not isinstance(resolution.resolver_version, str) or not resolution.resolver_version:
        raise ResolutionValidationError("resolver_version must be a non-empty string")
    if not isinstance(resolution.judge_name, str) or not resolution.judge_name:
        raise ResolutionValidationError("judge_name must be a non-empty string")
    if not isinstance(resolution.judge_version, str) or not resolution.judge_version:
        raise ResolutionValidationError("judge_version must be a non-empty string")
    if not isinstance(resolution.resolution_hash, str) or not resolution.resolution_hash:
        raise ResolutionValidationError("resolution_hash must be a non-empty string")
