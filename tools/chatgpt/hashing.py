"""
M4.1 — Deterministic canonical hashing for ACNF records.

Canonical serialization: UTF-8 JSON, sorted keys, stable (",", ":")
separators, non-ASCII characters preserved rather than escaped. Hash
algorithm: SHA-256.

Operational metadata (e.g. the acquisition's normalization timestamp) must
never be passed into these functions — callers are responsible for
excluding it before calling canonical_hash(). is_current_path is
deliberately excluded from compute_node_hash(): it reflects which branch
happens to be "current" in a given export, not the content of the node
itself, and must not cause a node's identity hash to change across
acquisitions when nothing about the node's own content changed.
"""

import hashlib
import json
from typing import Any, Dict, Optional, Sequence, Tuple


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize obj to canonical JSON bytes (UTF-8, sorted keys, stable separators)."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_hash(obj: Any) -> str:
    """Return the SHA-256 hex digest of obj's canonical JSON serialization."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def compute_node_hash(
    *,
    conversation_id: str,
    node_id: str,
    parent_id: Optional[str],
    message_id: Optional[str],
    has_message: bool,
    role: Optional[str],
    created_at: Optional[float],
    content_type: Optional[str],
    content: Any,
    asset_refs: Sequence[Dict[str, Any]],
) -> str:
    """
    Compute a node's canonical content-identity hash.

    asset_refs is a sequence of structured reference dicts
    ({"asset_id", "pointer_uri", "content_type"}); it is sorted by its
    canonical JSON form before hashing, since reference order is an
    artifact of scan order, not semantic content, and dicts are not
    orderable via plain sorted(). is_technical_root and is_current_path
    are intentionally excluded: the former is a pure function of
    parent_id/has_message already in the payload, and the latter is
    derived from external (branch-selection) state, not node content.
    has_message is included because a node whose message object is
    present but malformed (e.g. missing id) is structurally different
    from a node with no message at all, even though message_id is None in
    both cases.
    """
    sorted_asset_refs = sorted(asset_refs, key=canonical_json_bytes)
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "node_id": node_id,
        "parent_id": parent_id,
        "message_id": message_id,
        "has_message": has_message,
        "role": role,
        "created_at": created_at,
        "content_type": content_type,
        "content": content,
        "asset_refs": sorted_asset_refs,
    }
    return canonical_hash(payload)


def compute_conversation_hash(
    *,
    conversation_id: str,
    source_id: str,
    title: Optional[str],
    created_at: Optional[float],
    updated_at: Optional[float],
    current_node_id: Optional[str],
    default_model_slug: Optional[str],
    archived: Optional[bool],
    starred: Optional[bool],
    memory_scope: Optional[str],
    source_metadata: Dict[str, Any],
    node_hashes: Sequence[Tuple[str, str]],
) -> str:
    """
    Compute a conversation's canonical content-identity hash.

    node_hashes is a sequence of (node_id, node_hash) pairs; it is sorted
    before hashing so that graph structure and every node's content are
    covered without the hash depending on mapping iteration order.
    current_node_id is included deliberately: which branch is "current" is
    itself a conversation-level fact worth tracking across acquisitions.
    source_metadata (unmodelled top-level conversation fields) is included
    so that a source-side metadata change is detectable across
    acquisitions; canonical_hash's sort_keys=True already makes its key
    order irrelevant.
    """
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "source_id": source_id,
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "current_node_id": current_node_id,
        "default_model_slug": default_model_slug,
        "archived": archived,
        "starred": starred,
        "memory_scope": memory_scope,
        "source_metadata": source_metadata,
        "node_hashes": sorted(node_hashes),
    }
    return canonical_hash(payload)


def compute_asset_hash(
    *,
    asset_id: str,
    physical_filename: Optional[str],
    original_filename: Optional[str],
    mime_type: Optional[str],
    size_bytes: Optional[int],
    sha256: Optional[str],
    storage_kind: str,
) -> str:
    """
    Compute an asset record's canonical content-identity hash.

    Deliberately excludes any conversation/message provenance and any
    per-reference detail (pointer URI, pointer content_type): the same
    physical asset must hash identically no matter which conversation or
    message happens to reference it, or how any given occurrence
    described it. That reference-level detail is preserved separately via
    NodeRecord.asset_refs, not folded into asset identity.

    storage_kind participates in the hash: it is part of the asset's own
    identity (exported vs. reference-only), not provenance, and two
    reference-only assets whose other fields are all None must still
    hash deterministically and distinctly from an exported asset with the
    same None fields.
    """
    payload: Dict[str, Any] = {
        "asset_id": asset_id,
        "physical_filename": physical_filename,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "storage_kind": storage_kind,
    }
    return canonical_hash(payload)


def compute_acquisition_id(source_sha256: str, normalized_schema_version: str) -> str:
    """
    Deterministic acquisition identifier: a pure function of the source
    export's content hash and the schema version, not of wall-clock time.
    Re-normalizing the same export produces the same acquisition_id.
    """
    return canonical_hash(
        {
            "source_sha256": source_sha256,
            "normalized_schema_version": normalized_schema_version,
        }
    )
