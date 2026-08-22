"""
M4.2a — Scoring deterministico e trasparente dei boundary candidate (v0.1).

I pesi vivono qui, nominati ed espliciti — mai sparsi come magic number nel
resto della pipeline. Questa è un'euristica di base, non calibrata su dati
reali del corpus (vedi docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md,
sezione "Candidate score" / evidence score): soglie e pesi potranno essere
rivisti in futuro tramite un lavoro di benchmark esplicito, mai calibrati
silenziosamente sul dataset reale.

IMPORTANTE (M4.2a — passata di chiusura/freeze): questo modulo non è stato
toccato in questa passata. Pesi, soglie e semantica dello score restano
identici — vedi la sezione "Boundary Evidence Score" della documentazione
per come interpretare candidate_score senza modificarne il calcolo.
"""

from dataclasses import dataclass
from typing import Dict, List

from .models import CANDIDATE_CLASS_HIGH, CANDIDATE_CLASS_LOW, CANDIDATE_CLASS_MEDIUM
from .timegap import (
    TIME_GAP_BUCKET_1D_7D,
    TIME_GAP_BUCKET_1H_3H,
    TIME_GAP_BUCKET_1M_5M,
    TIME_GAP_BUCKET_3H_12H,
    TIME_GAP_BUCKET_5M_15M,
    TIME_GAP_BUCKET_12H_1D,
    TIME_GAP_BUCKET_15M_30M,
    TIME_GAP_BUCKET_30M_1H,
    TIME_GAP_BUCKET_GE_7D,
    TIME_GAP_BUCKET_LT_1M,
    TIME_GAP_BUCKET_UNKNOWN,
)

# Contributo normalizzato per bucket di time-gap, in [0, 1]. Monotono
# crescente con la lunghezza del gap; UNKNOWN contribuisce 0 — un gap
# sconosciuto non è evidenza in nessuna direzione, non "certamente un
# boundary".
TIME_GAP_BUCKET_SCORES: Dict[str, float] = {
    TIME_GAP_BUCKET_LT_1M: 0.0,
    TIME_GAP_BUCKET_1M_5M: 0.1,
    TIME_GAP_BUCKET_5M_15M: 0.2,
    TIME_GAP_BUCKET_15M_30M: 0.3,
    TIME_GAP_BUCKET_30M_1H: 0.4,
    TIME_GAP_BUCKET_1H_3H: 0.5,
    TIME_GAP_BUCKET_3H_12H: 0.65,
    TIME_GAP_BUCKET_12H_1D: 0.8,
    TIME_GAP_BUCKET_1D_7D: 0.9,
    TIME_GAP_BUCKET_GE_7D: 1.0,
    TIME_GAP_BUCKET_UNKNOWN: 0.0,
}


@dataclass(frozen=True)
class BoundaryScoreConfig:
    """
    Configurazione dei pesi, nominata ed esplicita, per candidate_score.
    Ogni contributo è documentato qui; nessun magic number nascosto altrove
    nella pipeline.

    time_gap_weight è deliberatamente limitato abbastanza in basso che il
    massimo contributo possibile del solo time gap (time_gap_weight * 1.0
    == 0.20) resti sotto low_threshold (0.35) — il time gap da solo non
    deve mai forzare nemmeno una classificazione MEDIUM, tantomeno HIGH
    (vedi doc, sezioni sul candidate score / evidence score).
    resume_marker_weight è negativo: un marker esplicito di continuità è
    evidenza *contro* un boundary.
    """

    time_gap_weight: float = 0.20
    opening_marker_weight: float = 0.30
    closure_marker_weight: float = 0.20
    transition_marker_weight: float = 0.20
    resume_marker_weight: float = -0.25
    lexical_shift_weight: float = 0.25

    low_threshold: float = 0.35
    high_threshold: float = 0.65


DEFAULT_SCORE_CONFIG = BoundaryScoreConfig()


def compute_candidate_score(
    *,
    time_gap_bucket: str,
    opening_markers: List[str],
    closure_markers: List[str],
    resume_markers: List[str],
    transition_markers: List[str],
    lexical_shift_score: float,
    config: BoundaryScoreConfig = DEFAULT_SCORE_CONFIG,
) -> float:
    """Calcola candidate_score come somma pesata dei contributi delle feature, clamped a [0.0, 1.0]."""
    time_gap_contribution = config.time_gap_weight * TIME_GAP_BUCKET_SCORES.get(time_gap_bucket, 0.0)
    opening_contribution = config.opening_marker_weight * (1.0 if opening_markers else 0.0)
    closure_contribution = config.closure_marker_weight * (1.0 if closure_markers else 0.0)
    transition_contribution = config.transition_marker_weight * (1.0 if transition_markers else 0.0)
    resume_contribution = config.resume_marker_weight * (1.0 if resume_markers else 0.0)
    lexical_contribution = config.lexical_shift_weight * lexical_shift_score

    score = (
        time_gap_contribution
        + opening_contribution
        + closure_contribution
        + transition_contribution
        + resume_contribution
        + lexical_contribution
    )
    return max(0.0, min(1.0, score))


def classify_candidate(score: float, config: BoundaryScoreConfig = DEFAULT_SCORE_CONFIG) -> str:
    """LOW < low_threshold <= MEDIUM < high_threshold <= HIGH. Non è una decisione di episodio."""
    if score < config.low_threshold:
        return CANDIDATE_CLASS_LOW
    if score < config.high_threshold:
        return CANDIDATE_CLASS_MEDIUM
    return CANDIDATE_CLASS_HIGH
