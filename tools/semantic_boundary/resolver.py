"""
M4.2b-A — Runner provider-indipendente del Semantic Boundary Resolver.

Orchestrazione: candidate grezzo (evidenza compatta M4.2a) + timeline dei
turni visibili di una conversazione -> SemanticResolutionRequest ->
SemanticJudge.resolve() -> SemanticResolution. Nessuna logica semantica
vive qui: questo modulo sa solo come costruire la request in modo
deterministico, invocare un judge qualunque (fake o futuro reale) e
assemblare/validare l'esito. Un fallimento del judge non viene mai
inghiottito silenziosamente — vedi run_resolutions.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from tools.semantic_boundary.context import (
    DEFAULT_AFTER_WINDOW,
    DEFAULT_BEFORE_WINDOW,
    clip_context,
)
from tools.semantic_boundary.hashing import compute_resolution_hash
from tools.semantic_boundary.judge import JudgeError, SemanticJudge
from tools.semantic_boundary.models import (
    RESOLVER_VERSION,
    DialogueTurn,
    RequestValidationError,
    ResolutionValidationError,
    SemanticEvidence,
    SemanticResolution,
    SemanticResolutionRequest,
    validate_request,
    validate_resolution,
)

# Chiavi obbligatorie di un candidate record grezzo (dict) in input.
# Deliberatamente un dict semplice, non tools.episodes.models.BoundaryCandidate:
# M4.2b non importa M4.2a, consuma solo questo sottoinsieme documentato di
# campi (vedi docs/M4.2B_SEMANTIC_BOUNDARY_RESOLVER.md).
_REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "conversation_id",
    "before_node_id",
    "after_node_id",
    "candidate_class",
    "candidate_score",
    "time_gap_seconds",
    "time_gap_bucket",
    "lexical_shift_score",
    "opening_markers",
    "closure_markers",
    "resume_markers",
    "transition_markers",
    "intermediate_node_count",
)


def _evidence_from_candidate_dict(candidate: Dict[str, Any]) -> SemanticEvidence:
    return SemanticEvidence(
        candidate_class=candidate["candidate_class"],
        candidate_score=candidate["candidate_score"],
        time_gap_seconds=candidate["time_gap_seconds"],
        time_gap_bucket=candidate["time_gap_bucket"],
        lexical_shift_score=candidate["lexical_shift_score"],
        opening_markers=list(candidate["opening_markers"]),
        closure_markers=list(candidate["closure_markers"]),
        resume_markers=list(candidate["resume_markers"]),
        transition_markers=list(candidate["transition_markers"]),
        intermediate_node_count=candidate["intermediate_node_count"],
    )


def build_request(
    candidate: Dict[str, Any],
    visible_turns: List[DialogueTurn],
    *,
    before_window: int = DEFAULT_BEFORE_WINDOW,
    after_window: int = DEFAULT_AFTER_WINDOW,
    resolver_version: str = RESOLVER_VERSION,
) -> SemanticResolutionRequest:
    """
    Costruisce e valida una SemanticResolutionRequest da un candidate
    record grezzo (dict) e dalla timeline completa dei turni dialogue
    visibili della sua conversazione. Solleva RequestValidationError su
    qualunque record malformato — mai un fallback silenzioso.
    """
    missing = [field_name for field_name in _REQUIRED_CANDIDATE_FIELDS if field_name not in candidate]
    if missing:
        raise RequestValidationError(f"malformed candidate record: missing field(s) {missing}")

    before_context, after_context = clip_context(
        visible_turns,
        candidate["before_node_id"],
        candidate["after_node_id"],
        before_window=before_window,
        after_window=after_window,
    )

    request = SemanticResolutionRequest(
        candidate_id=candidate["candidate_id"],
        conversation_id=candidate["conversation_id"],
        before_node_id=candidate["before_node_id"],
        after_node_id=candidate["after_node_id"],
        before_context=before_context,
        after_context=after_context,
        m4_2a_evidence=_evidence_from_candidate_dict(candidate),
        resolver_version=resolver_version,
    )
    validate_request(request)
    return request


def resolve_candidate(request: SemanticResolutionRequest, judge: SemanticJudge) -> SemanticResolution:
    """
    Risolve una singola request tramite il judge fornito e assembla il
    SemanticResolution finale, calcolandone il resolution_hash. Propaga
    JudgeError se il judge fallisce: non viene mai catturata qui.
    """
    validate_request(request)

    judge_response = judge.resolve(request)
    judge_response.validate()

    resolution_hash = compute_resolution_hash(
        candidate_id=request.candidate_id,
        decision=judge_response.decision,
        confidence=judge_response.confidence,
        reason=judge_response.reason,
        resolver_version=request.resolver_version,
        judge_name=judge_response.judge_name,
        judge_version=judge_response.judge_version,
    )

    resolution = SemanticResolution(
        candidate_id=request.candidate_id,
        decision=judge_response.decision,
        confidence=judge_response.confidence,
        reason=judge_response.reason,
        resolver_version=request.resolver_version,
        judge_name=judge_response.judge_name,
        judge_version=judge_response.judge_version,
        resolution_hash=resolution_hash,
    )
    validate_resolution(resolution)
    return resolution


@dataclass
class ResolutionFailure:
    """Fallimento esplicito e osservabile per un singolo candidate, mai inghiottito silenziosamente."""

    candidate_id: str
    error_type: str
    error_message: str


def run_resolutions(
    candidates_with_turns: Sequence[Tuple[Dict[str, Any], List[DialogueTurn]]],
    judge: SemanticJudge,
    *,
    before_window: int = DEFAULT_BEFORE_WINDOW,
    after_window: int = DEFAULT_AFTER_WINDOW,
    resolver_version: str = RESOLVER_VERSION,
) -> Tuple[List[SemanticResolution], List[ResolutionFailure]]:
    """
    Esegue in batch build_request + resolve_candidate per una sequenza di
    (candidate grezzo, timeline visibile della sua conversazione). Un
    fallimento su un singolo candidate (record malformato o JudgeError)
    non interrompe il batch: viene raccolto come ResolutionFailure
    esplicito, mai scartato silenziosamente.
    """
    resolutions: List[SemanticResolution] = []
    failures: List[ResolutionFailure] = []

    for candidate, visible_turns in candidates_with_turns:
        candidate_id = candidate.get("candidate_id", "<missing candidate_id>")
        try:
            request = build_request(
                candidate,
                visible_turns,
                before_window=before_window,
                after_window=after_window,
                resolver_version=resolver_version,
            )
            resolution = resolve_candidate(request, judge)
            resolutions.append(resolution)
        except (RequestValidationError, ResolutionValidationError, ValueError, JudgeError) as exc:
            failures.append(
                ResolutionFailure(
                    candidate_id=candidate_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

    return resolutions, failures
