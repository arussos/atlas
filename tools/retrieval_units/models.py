"""
M5.1 — Strutture dati RetrievalUnit.

Un RetrievalUnit NON è un episodio: è una finestra deterministica,
overlapping e non semantica di nodi dialogue visibili consecutivi del
current path di una conversazione ACNF. Il testo è dato derivato,
ricostruibile dai node_ids — ACNF resta la fonte di verità.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Versione della logica di projection M5.1. Deliberatamente distinta da
# ACNF_SCHEMA_VERSION (tools/chatgpt/models.py) e da FEATURE_VERSION
# (tools/episodes/models.py): evolvono in modo indipendente. Partecipa
# all'identità di ogni unit — un cambio di policy (window/stride/
# rendering) deve incrementarla, così le identità di due versioni di
# policy non collidono mai.
PROJECTION_VERSION = "0.1"

# Literal esatto richiesto dal contratto M5.1 per la sorgente ChatGPT.
SOURCE_TYPE_CHATGPT = "chatgpt"

# Policy di windowing v0.1 — deliberatamente semplice e non semantica.
# Finestre di 6 nodi dialogue visibili, stride 3 (overlap 3 nodi / 50%).
# L'ultima finestra può contenere meno di 6 nodi; nessuna coda viene
# scartata — ogni nodo visibile appartiene ad almeno una finestra.
WINDOW_SIZE = 6
WINDOW_STRIDE = 3


@dataclass
class RetrievalUnit:
    """
    Una finestra deterministica di nodi dialogue visibili consecutivi.

    Convenzione ordinali: ordinal_start / ordinal_end sono 0-based ed
    entrambi INCLUSIVI, riferiti alla sequenza dei soli nodi dialogue
    visibili della conversazione (stessa convenzione 0-based di
    sequence_index in M4.2a). message_count == ordinal_end -
    ordinal_start + 1 == len(node_ids).

    Identità vs contenuto: retrieval_unit_id è stabile per la stessa
    identità logica (projection_version, conversation_id, node_ids
    ordinati) e NON include acquisition_id — la stessa unit logica vista
    in un export successivo resta riconoscibile. content_hash rileva
    invece cambi materiali di contenuto/provenance tra acquisizioni.

    intermediate_node_ids è solo provenance ordinata dei nodi tecnici
    non visibili saltati dalla Dialogue Timeline Projection strettamente
    tra i nodi visibili inclusi nella finestra — il loro contenuto non
    entra mai in text (resta recuperabile in ACNF).
    """

    retrieval_unit_id: str
    projection_version: str
    source_type: str

    acquisition_id: str
    acnf_schema_version: str

    conversation_id: str
    source_id: Optional[str]
    conversation_title: Optional[str]
    source_conversation_hash: Optional[str]

    node_ids: List[str]
    first_node_id: str
    last_node_id: str

    ordinal_start: int
    ordinal_end: int
    message_count: int

    start_timestamp: Optional[float]
    end_timestamp: Optional[float]

    intermediate_node_ids: List[str]

    text: str
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retrieval_unit_id": self.retrieval_unit_id,
            "projection_version": self.projection_version,
            "source_type": self.source_type,
            "acquisition_id": self.acquisition_id,
            "acnf_schema_version": self.acnf_schema_version,
            "conversation_id": self.conversation_id,
            "source_id": self.source_id,
            "conversation_title": self.conversation_title,
            "source_conversation_hash": self.source_conversation_hash,
            "node_ids": self.node_ids,
            "first_node_id": self.first_node_id,
            "last_node_id": self.last_node_id,
            "ordinal_start": self.ordinal_start,
            "ordinal_end": self.ordinal_end,
            "message_count": self.message_count,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "intermediate_node_ids": self.intermediate_node_ids,
            "text": self.text,
            "content_hash": self.content_hash,
        }
