"""
M4.2b-A — Hashing canonico deterministico per richieste ed esiti di
risoluzione semantica.

Autonomo di proposito, come tools/episodes/hashing.py: non importa
tools.chatgpt.hashing né tools.episodes.hashing. Lo schema di identità di
M4.2b non deve essere accoppiato agli interni del normalizzatore ACNF o
del boundary evidence engine, anche se ne ricalca intenzionalmente la
convenzione di serializzazione canonica (JSON UTF-8, chiavi ordinate,
separatori stabili, non-ASCII preservato, SHA-256).
"""

import hashlib
import json
from typing import Any, Dict

from tools.semantic_boundary.models import SemanticResolutionRequest


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


def compute_request_hash(request: SemanticResolutionRequest) -> str:
    """
    Hash deterministico dell'intera SemanticResolutionRequest. Stesso
    input semantico (stesso candidate_id, stesso contesto, stessa
    evidenza, stessa resolver_version) produce sempre lo stesso hash;
    qualunque variazione di un campo semantico lo cambia.
    """
    return canonical_hash(request.to_dict())


def compute_resolution_hash(
    *,
    candidate_id: str,
    decision: str,
    confidence: float,
    reason: str,
    resolver_version: str,
    judge_name: str,
    judge_version: str,
) -> str:
    """
    Hash deterministico dell'esito di risoluzione, calcolato sui campi
    normalizzati dell'esito. resolution_hash NON partecipa al proprio
    stesso hash — i chiamanti passano i campi separatamente, mai un
    SemanticResolution già costruito con un resolution_hash placeholder.
    """
    payload: Dict[str, Any] = {
        "candidate_id": candidate_id,
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "resolver_version": resolver_version,
        "judge_name": judge_name,
        "judge_version": judge_version,
    }
    return canonical_hash(payload)
