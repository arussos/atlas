"""
M5.1 — Hashing canonico deterministico per i record RetrievalUnit.

Autonomo di proposito, come tools/episodes/hashing.py rispetto a
tools/chatgpt/hashing.py: lo schema di identità di M5.1 non deve essere
accoppiato agli interni di M4.1/M4.2a, anche se la convenzione di
serializzazione canonica (JSON UTF-8, chiavi ordinate, separatori
stabili, non-ASCII preservato, SHA-256) la ricalca intenzionalmente.

Identità vs contenuto (vedi docs/M5.1_CHATGPT_RETRIEVAL_UNITS.md):

- compute_retrieval_unit_id: identità logica stabile. Basata solo su
  projection_version + conversation_id + node_ids ordinati. NON include
  acquisition_id — la stessa unit logica in un export successivo deve
  restare riconoscibilmente la stessa unit. Mai UUID/random.

- compute_content_hash: rilevamento di cambi materiali di contenuto/
  provenance. Se la stessa identità logica cambia contenuto tra
  acquisizioni, retrieval_unit_id resta stabile e content_hash cambia.
"""

import hashlib
import json
from typing import Any, List, Optional


def canonical_json_bytes(obj: Any) -> bytes:
    """Serializza obj in byte JSON canonici (UTF-8, chiavi ordinate, separatori stabili)."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_hash(obj: Any) -> str:
    """Restituisce il digest esadecimale SHA-256 della serializzazione JSON canonica di obj."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def compute_retrieval_unit_id(
    *,
    projection_version: str,
    conversation_id: str,
    node_ids: List[str],
) -> str:
    """
    Identità deterministica e stabile della unit logica. Due run sullo
    stesso ACNF — o su due acquisizioni diverse in cui questa unit ha
    identica identità conversation/node — assegnano lo stesso
    retrieval_unit_id alla stessa finestra (conversation_id, node_ids
    ordinati, projection_version).
    """
    return canonical_hash(
        {
            "projection_version": projection_version,
            "conversation_id": conversation_id,
            "node_ids": list(node_ids),
        }
    )


def compute_content_hash(
    *,
    retrieval_unit_id: str,
    text: str,
    node_hashes: List[Optional[str]],
    intermediate_node_ids: List[str],
) -> str:
    """
    SHA-256 della rappresentazione canonica del contenuto della unit.

    Copre l'identità (retrieval_unit_id), il testo renderizzato e i
    node_hash ACNF ordinati dei nodi visibili inclusi — così un cambio di
    contenuto sorgente a parità di identità logica cambia content_hash
    anche se il testo estratto restasse identico. La provenance dei nodi
    intermedi partecipa: saltare un insieme diverso di nodi tecnici tra
    gli stessi nodi visibili è una unit materialmente diversa (stessa
    scelta di M4.2a per candidate_hash).
    """
    return canonical_hash(
        {
            "retrieval_unit_id": retrieval_unit_id,
            "text": text,
            "node_hashes": list(node_hashes),
            "intermediate_node_ids": list(intermediate_node_ids),
        }
    )
