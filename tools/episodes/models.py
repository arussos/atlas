"""
M4.2a — Strutture dati del candidate boundary.

BoundaryCandidate è un record di feature deterministico e spiegabile
sulla transizione tra due nodi *dialogue visibili* consecutivi, così come
selezionati dalla Dialogue Timeline Projection (tools/episodes/projection.py)
— non tra due nodi-messaggio consecutivi del current path. candidate_class
(LOW/MEDIUM/HIGH) NON è una decisione di episodio — esprime solo quanta
evidenza deterministica di un possibile boundary è stata trovata. La
decisione finale SAME_EPISODE / NEW_EPISODE / UNCERTAIN appartiene a M4.2b.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Identifica la versione di questa logica di feature-extraction.
# Deliberatamente distinta da ACNF_SCHEMA_VERSION (tools/chatgpt/models.py):
# le due evolvono in modo indipendente — un cambiamento alla logica di
# scoring/marker di M4.2a non implica un cambio di schema ACNF, e viceversa.
#
# RC2 (m4.2a-0.2): i vertici candidati sono i nodi dialogue visibili
# proiettati (text/multimodal_text) invece di tutti i nodi-messaggio del
# current path. La run RC1 su dati reali ha mostrato che >99% delle
# transizioni assistant->assistant erano artefatti di nodi
# thoughts/reasoning_recap usati come vertici di boundary — vedi
# docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md. Versione incrementata
# perché le identità dei candidate RC1 e RC2 non collidano mai.
FEATURE_VERSION = "m4.2a-0.2"

CANDIDATE_CLASS_LOW = "LOW"
CANDIDATE_CLASS_MEDIUM = "MEDIUM"
CANDIDATE_CLASS_HIGH = "HIGH"


@dataclass
class BoundaryCandidate:
    """Un record di candidate boundary per una singola coppia di messaggi consecutivi."""

    candidate_id: str
    conversation_id: str

    before_node_id: Optional[str]
    after_node_id: Optional[str]
    before_message_id: Optional[str]
    after_message_id: Optional[str]
    sequence_index: int

    before_role: Optional[str]
    after_role: Optional[str]

    before_created_at: Optional[float]
    after_created_at: Optional[float]
    time_gap_seconds: Optional[float]
    time_gap_bucket: str

    explicit_opening_markers: List[str]
    explicit_closure_markers: List[str]
    explicit_resume_markers: List[str]
    explicit_transition_markers: List[str]

    lexical_similarity: float
    lexical_shift_score: float

    before_text_length: int
    after_text_length: int

    candidate_score: float
    candidate_class: str

    reasons: List[str]

    # Provenance dei nodi-messaggio non visibili del current path (es.
    # thoughts, reasoning_recap) che la Dialogue Timeline Projection ha
    # saltato tra before_node_id e after_node_id. Ordinati come incontrati
    # sul current path. Vuoti quando i due nodi visibili erano direttamente
    # adiacenti sul current path. Il contenuto non viene mai copiato qui —
    # ACNF resta la fonte autorevole (vedi tools/episodes/projection.py).
    intermediate_node_ids: List[str]
    intermediate_content_types: List[str]
    intermediate_node_count: int

    feature_version: str
    candidate_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "conversation_id": self.conversation_id,
            "before_node_id": self.before_node_id,
            "after_node_id": self.after_node_id,
            "before_message_id": self.before_message_id,
            "after_message_id": self.after_message_id,
            "sequence_index": self.sequence_index,
            "before_role": self.before_role,
            "after_role": self.after_role,
            "before_created_at": self.before_created_at,
            "after_created_at": self.after_created_at,
            "time_gap_seconds": self.time_gap_seconds,
            "time_gap_bucket": self.time_gap_bucket,
            "explicit_opening_markers": self.explicit_opening_markers,
            "explicit_closure_markers": self.explicit_closure_markers,
            "explicit_resume_markers": self.explicit_resume_markers,
            "explicit_transition_markers": self.explicit_transition_markers,
            "lexical_similarity": self.lexical_similarity,
            "lexical_shift_score": self.lexical_shift_score,
            "before_text_length": self.before_text_length,
            "after_text_length": self.after_text_length,
            "candidate_score": self.candidate_score,
            "candidate_class": self.candidate_class,
            "reasons": self.reasons,
            "intermediate_node_ids": self.intermediate_node_ids,
            "intermediate_content_types": self.intermediate_content_types,
            "intermediate_node_count": self.intermediate_node_count,
            "feature_version": self.feature_version,
            "candidate_hash": self.candidate_hash,
        }


@dataclass
class Anomaly:
    """Un'anomalia strutturale rilevata durante la ricostruzione del current
    path o il raggruppamento dei nodi ACNF. Mai silenziosa — sempre
    registrata, mai sollevata come eccezione."""

    type: str
    conversation_id: Optional[str]
    node_id: Optional[str]
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "conversation_id": self.conversation_id,
            "node_id": self.node_id,
            "detail": self.detail,
        }
