"""
M4.2a — Hashing canonico deterministico per i record boundary candidate.

Autonomo di proposito: non importa tools.chatgpt.hashing. Lo schema di
identità di M4.2a non deve essere accoppiato agli interni del normalizzatore
OpenAI RAW -> ACNF, anche se la convenzione di serializzazione canonica
(JSON UTF-8, chiavi ordinate, separatori stabili, non-ASCII preservato) la
ricalca intenzionalmente.
"""

import hashlib
import json
from typing import Any, Dict


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


def compute_candidate_id(
    *,
    conversation_id: str,
    before_node_id: str,
    after_node_id: str,
    feature_version: str,
) -> str:
    """
    Identità deterministica del candidate — mai un UUID casuale. Due run
    sullo stesso ACNF devono assegnare lo stesso candidate_id alla stessa
    transizione (conversation_id, before_node_id, after_node_id).
    """
    return canonical_hash(
        {
            "conversation_id": conversation_id,
            "before_node_id": before_node_id,
            "after_node_id": after_node_id,
            "feature_version": feature_version,
        }
    )


def compute_candidate_hash(candidate_payload: Dict[str, Any]) -> str:
    """
    SHA-256 sull'intero contenuto canonico di un candidate. candidate_payload
    non deve includere candidate_hash stesso (auto-referenziale) — i
    chiamanti costruiscono il payload senza di esso e aggiungono l'hash
    risultante in seguito.
    """
    return canonical_hash(candidate_payload)
