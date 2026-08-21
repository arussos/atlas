"""
M4.1 — Atlas Conversation Normal Form (ACNF) v0.1 data structures.

These dataclasses define the normalized, model-independent representation
produced by the ChatGPT export normalizer. They carry no OpenAI-specific
behavior — they are the target shape of the OpenAI -> ACNF boundary and are
serialized as-is into conversations.jsonl / nodes.jsonl / assets.jsonl.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

ACNF_SCHEMA_VERSION = "0.1"

# Observed OpenAI export asset storage classes (see docs, "Asset storage
# classes" section, added after the CHATGPT-ACQ-001 RC1 real-data run).
# ASSET_STORAGE_KIND_EXPORTED: the export is expected to (and normally
# does) carry a physical <asset_id>.dat member for this asset.
# ASSET_STORAGE_KIND_REFERENCE_ONLY: a logical reference discovered only
# inside conversation JSON (observed for sediment:// pointers), with no
# physical payload in the export. Absence of a physical member for a
# reference-only asset is expected source behavior, not data loss.
ASSET_STORAGE_KIND_EXPORTED = "exported"
ASSET_STORAGE_KIND_REFERENCE_ONLY = "reference_only"


@dataclass
class NodeRecord:
    """
    A single OpenAI mapping-graph node, normalized but not flattened.

    asset_refs is a list of structured asset-reference records — one per
    distinct asset pointer found in this node's content — each shaped as
    {"asset_id", "pointer_uri", "content_type"}. This is occurrence-level
    metadata (how *this* node referenced the asset) and is deliberately
    kept here rather than on AssetRecord: AssetRecord is deduplicated
    globally by asset_id across the whole export, so occurrence-level
    detail (which may legitimately differ between two nodes referencing
    the same physical asset) would be silently discarded by "first-seen
    wins" if it lived there instead. The full raw pointer object (e.g.
    width/height/format) is not duplicated into asset_refs — it already
    survives verbatim in `content`.
    """

    conversation_id: str
    node_id: str
    parent_id: Optional[str]
    message_id: Optional[str]
    has_message: bool
    role: Optional[str]
    created_at: Optional[float]
    content_type: Optional[str]
    content: Any
    asset_refs: List[Dict[str, Any]]
    is_technical_root: bool
    is_current_path: bool
    node_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "message_id": self.message_id,
            "has_message": self.has_message,
            "role": self.role,
            "created_at": self.created_at,
            "content_type": self.content_type,
            "content": self.content,
            "asset_refs": self.asset_refs,
            "is_technical_root": self.is_technical_root,
            "is_current_path": self.is_current_path,
            "node_hash": self.node_hash,
        }


@dataclass
class ConversationRecord:
    """A single conversation's metadata and graph-level aggregates."""

    conversation_id: str
    source_id: str
    title: Optional[str]
    created_at: Optional[float]
    updated_at: Optional[float]
    current_node_id: Optional[str]
    default_model_slug: Optional[str]
    archived: Optional[bool]
    starred: Optional[bool]
    memory_scope: Optional[str]
    node_count: int
    message_count: int
    has_branches: bool
    source_metadata: Dict[str, Any]
    conversation_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "source_id": self.source_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_node_id": self.current_node_id,
            "default_model_slug": self.default_model_slug,
            "archived": self.archived,
            "starred": self.starred,
            "memory_scope": self.memory_scope,
            "node_count": self.node_count,
            "message_count": self.message_count,
            "has_branches": self.has_branches,
            "source_metadata": self.source_metadata,
            "conversation_hash": self.conversation_hash,
        }


@dataclass
class AssetRecord:
    """
    A distinct logical asset, identified independently of any message or
    conversation that happens to reference it, and independently of how
    any given reference described it. Provenance and reference-level
    detail (which conversation/node/message referenced this asset, via
    which pointer URI, as which content_type) are preserved separately
    via NodeRecord.asset_refs, not here: this record is deduplicated
    globally by asset_id across the whole export, so any field that could
    legitimately vary between two occurrences of the same physical asset
    must not live here, or "first-seen wins" dedup would silently discard
    the other occurrence's version of it.

    Logical asset existence is modeled separately from physical asset
    existence: storage_kind == ASSET_STORAGE_KIND_REFERENCE_ONLY means
    this asset was discovered only as a pointer inside conversation JSON
    (observed for sediment:// references) and the export carries no
    physical payload for it — physical_filename/sha256/size_bytes stay
    None in that case, and this is not treated as data loss. storage_kind
    == ASSET_STORAGE_KIND_EXPORTED means the export is expected to carry
    a physical member for this asset (observed for file-service://
    references and orphan .dat members); if that physical member is
    absent, that remains a genuine anomaly.
    """

    asset_id: str
    physical_filename: Optional[str]
    original_filename: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    sha256: Optional[str]
    storage_kind: str
    asset_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "physical_filename": self.physical_filename,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "storage_kind": self.storage_kind,
            "asset_hash": self.asset_hash,
        }


@dataclass
class LibraryFileRecord:
    """
    One record from library_files.json, preserved losslessly. This is a
    distinct metadata source from conversation asset references (see
    AssetRecord) — library files are not asset references and no
    relationship to conversations/assets is inferred that isn't present
    in the source.

    The real OpenAI schema carries two distinct identities per record,
    which are kept separate rather than collapsed into one:

    library_file_id -> raw["id"]["id"], the libfile_* record identity
        (raw["id"]["partition_key"] is its sibling field; both survive
        verbatim in raw_record).
    source_file_id  -> raw["file_id"], the file_* source/content identity.

    library_file_id is always populated: if raw["id"] is missing or
    malformed, a deterministic fallback derived from the record's own
    content is used instead (see normalizer._resolve_library_file_identity)
    and an anomaly is recorded — raw_record is preserved either way.
    """

    library_file_id: str
    source_file_id: Optional[str]
    raw_record: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_file_id": self.library_file_id,
            "source_file_id": self.source_file_id,
            "raw_record": self.raw_record,
        }


@dataclass
class AcquisitionMeta:
    """Top-level metadata describing one normalization run over one export."""

    acquisition_id: str
    source_filename: str
    source_sha256: str
    normalized_schema_version: str
    export_metadata: Dict[str, Any]
    normalized_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "acquisition_id": self.acquisition_id,
            "source_filename": self.source_filename,
            "source_sha256": self.source_sha256,
            "normalized_schema_version": self.normalized_schema_version,
            "export_metadata": self.export_metadata,
            "normalized_at": self.normalized_at,
        }


@dataclass
class Anomaly:
    """A structural anomaly detected during normalization. Never silent."""

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
