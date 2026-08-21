"""
M4.1 — OpenAI export -> ACNF v0.1 normalizer.

Transforms raw ChatGPT export data (as exposed by export_reader.py) into
the Atlas Conversation Normal Form: conversations, mapping-graph nodes, and
asset records, with deterministic canonical hashes.

No semantic interpretation, summarization, classification, or LLM
inference happens here. The OpenAI mapping graph is preserved structurally
— it is never flattened into a chronological message sequence. Structural
anomalies are recorded, never silently dropped.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .export_reader import ChatGPTExportReader, ExportReaderError
from .hashing import canonical_hash, compute_acquisition_id, compute_asset_hash, compute_conversation_hash, compute_node_hash
from .models import (
    ACNF_SCHEMA_VERSION,
    ASSET_STORAGE_KIND_EXPORTED,
    ASSET_STORAGE_KIND_REFERENCE_ONLY,
    AcquisitionMeta,
    Anomaly,
    AssetRecord,
    ConversationRecord,
    LibraryFileRecord,
    NodeRecord,
)
from . import validation as validation_mod

# Observed asset-pointer URI schemes. Detection is keyed on the scheme
# prefix rather than on a fixed set of content_type names, so unknown
# pointer-carrying structures (new part types, deeper nesting) are picked
# up the same way as the ones seen so far.
ASSET_POINTER_RE = re.compile(r"(file-service|sediment)://([A-Za-z0-9_.\-]+)")

# Pointer schemes observed (CHATGPT-ACQ-001 RC1) to legitimately carry no
# physical export payload: sediment:// asset ids appear only inside
# conversation JSON. A sediment reference is classified reference-only
# unless a physical <asset_id>.dat member is actually present in the
# export — see _classify_asset_storage below. file-service:// is not in
# this set: it is the "exported" class, where a missing physical member
# remains a genuine anomaly.
REFERENCE_ONLY_SCHEMES: Set[str] = {"sediment"}

# Top-level OpenAI conversation fields ACNF models explicitly. Everything
# else found on a raw conversation dict is preserved verbatim in
# ConversationRecord.source_metadata rather than dropped.
MODELED_CONVERSATION_FIELDS: Set[str] = {
    "id",
    "conversation_id",
    "title",
    "create_time",
    "update_time",
    "current_node",
    "default_model_slug",
    "is_archived",
    "is_starred",
    "memory_scope",
    "mapping",
}


class NormalizationResult:
    """Aggregate output of normalizing one export ZIP."""

    def __init__(self) -> None:
        self.acquisition: Optional[AcquisitionMeta] = None
        self.conversations: List[ConversationRecord] = []
        self.nodes: List[NodeRecord] = []
        self.assets: List[AssetRecord] = []
        self.library_files: List[LibraryFileRecord] = []
        self.anomalies: List[Anomaly] = []
        self.conversation_asset_file_names_count: int = 0
        self.physical_dat_asset_count: int = 0


def _extract_asset_pointers(content: Any) -> List[Dict[str, Any]]:
    """
    Recursively inspect a message's content structure for structured
    asset-reference pointers — file-service:// and sediment:// observed
    forms, at any nesting depth, including pointers nested inside larger
    structures such as real_time_user_audio_video_asset_pointer (which
    wraps its own audio_asset_pointer / video_container_asset_pointer
    sub-objects). Detection scans every string value in every dict for
    the URI scheme, not just a fixed "asset_pointer" key or a fixed list
    of content_type names, so it stays forward-compatible with unknown
    pointer-like structures.

    Returns one entry per distinct asset id, in first-seen (deterministic)
    order: {"asset_id", "pointer_uri", "content_type", "scheme"}.
    content_type is the content_type of the dict that carried the pointer
    string, when present. scheme is the pointer URI scheme (e.g.
    "file-service", "sediment"), used downstream to classify asset
    storage_kind — it is not included in NodeRecord.asset_refs, which
    only exposes {"asset_id", "pointer_uri", "content_type"}. No
    interpretation of what the referenced asset is — only identity
    extraction.
    """
    found: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, str):
                    m = ASSET_POINTER_RE.search(value)
                    if m:
                        asset_id = m.group(2)
                        if asset_id not in seen_ids:
                            seen_ids.add(asset_id)
                            found.append(
                                {
                                    "asset_id": asset_id,
                                    "pointer_uri": m.group(0),
                                    "content_type": node.get("content_type"),
                                    "scheme": m.group(1),
                                }
                            )
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(content)
    return found


def _synthetic_conversation_id(raw: Dict[str, Any]) -> str:
    """
    Deterministic fallback conversation id derived from the canonical
    SHA-256 of the raw conversation content itself — never random. Two
    runs over the same malformed input must produce the same id.
    """
    return "synthetic-conv-" + canonical_hash(raw)


def _resolve_conversation_identity(raw: Dict[str, Any], anomalies: List[Anomaly]) -> Tuple[str, str]:
    """
    Resolve (conversation_id, source_id) from raw's `conversation_id` and
    `id` fields, which the real OpenAI schema carries as distinct
    identities. conversation_id prefers raw conversation_id, falling back
    to raw id; source_id prefers raw id, falling back to raw
    conversation_id. When both are present and differ, both are preserved
    exactly as given — neither is silently overwritten. When neither is
    present, a deterministic synthetic id is used for both and an anomaly
    is recorded.
    """
    raw_id = raw.get("id")
    raw_conversation_id = raw.get("conversation_id")
    has_id = isinstance(raw_id, str) and raw_id != ""
    has_conversation_id = isinstance(raw_conversation_id, str) and raw_conversation_id != ""

    if has_conversation_id:
        conversation_id = raw_conversation_id
    elif has_id:
        conversation_id = raw_id
    else:
        conversation_id = _synthetic_conversation_id(raw)

    if has_id:
        source_id = raw_id
    elif has_conversation_id:
        source_id = raw_conversation_id
    else:
        source_id = conversation_id

    if not has_id and not has_conversation_id:
        anomalies.append(
            Anomaly(
                "missing_conversation_id",
                conversation_id,
                None,
                "Conversation has neither id nor conversation_id; a deterministic synthetic id "
                "derived from the canonical SHA-256 of the raw conversation content was assigned",
            )
        )

    return conversation_id, source_id


def _synthetic_library_file_id(raw: Dict[str, Any]) -> str:
    """
    Deterministic fallback library_file_id derived from the canonical
    SHA-256 of the raw library_files.json entry itself — never random. Two
    runs over the same malformed record must produce the same id.
    """
    return "synthetic-libfile-" + canonical_hash(raw)


def _resolve_library_file_identity(
    raw: Dict[str, Any], anomalies: List[Anomaly]
) -> Tuple[str, Optional[str]]:
    """
    Resolve (library_file_id, source_file_id) from a raw library_files.json
    entry. The real OpenAI schema carries two distinct identities per
    record: raw["id"]["id"] (the libfile_* record identity, alongside its
    sibling raw["id"]["partition_key"]) and raw["file_id"] (the file_*
    source/content identity). Both survive verbatim in raw_record
    regardless of what happens here; this only derives the scalar ids.

    When raw["id"] is missing or not shaped as {"id": <str>, ...}, a
    deterministic synthetic id is assigned instead and an anomaly is
    recorded. When raw["file_id"] is missing, source_file_id is None and an
    anomaly is recorded — this never affects library_file_id resolution or
    determinism.
    """
    raw_id = raw.get("id")
    library_file_id: Optional[str] = None
    if isinstance(raw_id, dict):
        candidate = raw_id.get("id")
        if isinstance(candidate, str) and candidate != "":
            library_file_id = candidate

    if library_file_id is None:
        library_file_id = _synthetic_library_file_id(raw)
        anomalies.append(
            Anomaly(
                "malformed_library_file_id",
                None,
                None,
                "library_files.json entry has a missing or malformed id (expected "
                '{"id": {"id": <str>, ...}}); a deterministic synthetic id derived from the '
                "canonical SHA-256 of the raw entry was assigned",
            )
        )

    raw_file_id = raw.get("file_id")
    source_file_id = raw_file_id if isinstance(raw_file_id, str) and raw_file_id != "" else None
    if source_file_id is None:
        anomalies.append(
            Anomaly(
                "missing_library_file_source_id",
                None,
                None,
                f"library_files.json entry (library_file_id={library_file_id!r}) has no file_id",
            )
        )

    return library_file_id, source_file_id


def _resolve_original_filename(asset_map: Dict[str, Any], asset_id: str) -> Optional[str]:
    """
    Look up asset_id's original filename in the raw conversation_asset_file_names
    mapping. Tries both the bare id (file-XXXX) and the .dat-suffixed physical
    filename as keys, since the exact key format cannot be verified without a
    real export locally (see report Open Questions).
    """
    for key in (asset_id, f"{asset_id}.dat"):
        value = asset_map.get(key)
        if isinstance(value, str):
            return value
    return None


def _walk_current_path(
    mapping: Dict[str, Any],
    current_node_id: Optional[str],
    anomalies: List[Anomaly],
    conversation_id: str,
) -> Set[str]:
    """
    Return the set of node ids on the current path: the ancestor chain
    from current_node_id up to and including the technical root. Guards
    against cycles and dangling parent references; anomalies are
    recorded, never raised.
    """
    path: Set[str] = set()
    if current_node_id is None:
        return path

    node_id: Optional[str] = current_node_id
    visited: Set[str] = set()
    while node_id is not None:
        if node_id in visited:
            anomalies.append(
                Anomaly("current_path_cycle", conversation_id, node_id, "Cycle detected while walking the current path")
            )
            break
        visited.add(node_id)
        entry = mapping.get(node_id)
        if not isinstance(entry, dict):
            anomalies.append(
                Anomaly(
                    "dangling_current_path_node",
                    conversation_id,
                    node_id,
                    "current_node path references a node id not present in mapping",
                )
            )
            break
        path.add(node_id)
        node_id = entry.get("parent")
    return path


def _classify_asset_storage(
    scheme: Optional[str],
    asset_id: str,
    physical_dat_names: Optional[Set[str]],
) -> Tuple[str, Optional[str]]:
    """
    Decide an asset's storage_kind and expected physical_filename from its
    pointer scheme and, when known, the export's actual physical .dat
    inventory. A physical member actually present always wins: any asset
    id with a real <asset_id>.dat member in the export is "exported",
    regardless of which scheme referenced it. Otherwise, a
    REFERENCE_ONLY_SCHEMES pointer (observed: sediment://) is classified
    "reference_only" with no expected physical filename — a physical
    payload is not expected for this class, per the CHATGPT-ACQ-001 RC1
    finding. Every other scheme stays "exported" with an expected (but
    possibly missing) physical filename, so a genuinely missing
    file-service:// asset remains a real anomaly.
    """
    expected_physical_filename = f"{asset_id}.dat"
    has_known_physical = physical_dat_names is not None and expected_physical_filename in physical_dat_names
    if has_known_physical:
        return ASSET_STORAGE_KIND_EXPORTED, expected_physical_filename
    if scheme in REFERENCE_ONLY_SCHEMES:
        return ASSET_STORAGE_KIND_REFERENCE_ONLY, None
    return ASSET_STORAGE_KIND_EXPORTED, expected_physical_filename


def normalize_conversation(
    raw: Dict[str, Any],
    asset_map: Dict[str, Any],
    anomalies: List[Anomaly],
    physical_dat_names: Optional[Set[str]] = None,
) -> Tuple[ConversationRecord, List[NodeRecord], List[AssetRecord]]:
    """
    Normalize one raw OpenAI conversation dict into ACNF records.

    physical_dat_names, when provided, is the export's full set of
    physical *.dat member names (see ChatGPTExportReader.physical_dat_filenames),
    used to classify each newly discovered asset's storage_kind (see
    _classify_asset_storage). When None (e.g. direct unit-test calls with
    no export to inspect), classification falls back to scheme alone.
    """
    conversation_id, source_id = _resolve_conversation_identity(raw, anomalies)

    source_metadata = {k: v for k, v in raw.items() if k not in MODELED_CONVERSATION_FIELDS}

    mapping = raw.get("mapping")
    if not isinstance(mapping, dict):
        mapping = {}
        anomalies.append(Anomaly("missing_mapping", conversation_id, None, "Conversation has no mapping graph"))

    current_node_id = raw.get("current_node")
    current_path_ids = _walk_current_path(mapping, current_node_id, anomalies, conversation_id)

    children_count: Dict[str, int] = {}
    for node_id, entry in mapping.items():
        if not isinstance(entry, dict):
            continue
        parent_id = entry.get("parent")
        if parent_id is not None:
            children_count[parent_id] = children_count.get(parent_id, 0) + 1

    technical_root_count = 0
    message_count = 0
    node_records: List[NodeRecord] = []
    asset_records: List[AssetRecord] = []
    seen_assets: Set[str] = set()

    for node_id, entry in mapping.items():
        if not isinstance(entry, dict):
            anomalies.append(Anomaly("invalid_node_entry", conversation_id, node_id, "Mapping entry is not an object"))
            continue

        parent_id = entry.get("parent")
        message = entry.get("message")
        is_technical_root = parent_id is None and message is None

        if is_technical_root:
            technical_root_count += 1
        elif parent_id is None and message is not None:
            anomalies.append(
                Anomaly("root_like_node_with_message", conversation_id, node_id, "Node has no parent but carries a message")
            )

        role: Optional[str] = None
        created_at: Optional[float] = None
        content_type: Optional[str] = None
        content: Any = None
        message_id: Optional[str] = None
        asset_refs: List[Dict[str, Any]] = []
        asset_pointers: List[Dict[str, Any]] = []
        has_message = isinstance(message, dict)

        if has_message:
            message_id = message.get("id")
            if not message_id:
                anomalies.append(
                    Anomaly(
                        "message_missing_id",
                        conversation_id,
                        node_id,
                        "Message object present but missing id",
                    )
                )
            author = message.get("author")
            if isinstance(author, dict):
                role = author.get("role")
            created_at = message.get("create_time")
            content = message.get("content")
            if isinstance(content, dict):
                content_type = content.get("content_type")
            asset_pointers = _extract_asset_pointers(content)
            # Occurrence-level reference metadata (pointer_uri, content_type)
            # is kept at the node level, not folded into the deduplicated
            # physical AssetRecord — see NodeRecord.asset_refs docstring.
            asset_refs = [
                {
                    "asset_id": p["asset_id"],
                    "pointer_uri": p["pointer_uri"],
                    "content_type": p["content_type"],
                }
                for p in asset_pointers
            ]
            message_count += 1
        elif not is_technical_root:
            anomalies.append(
                Anomaly(
                    "empty_non_root_node",
                    conversation_id,
                    node_id,
                    "Node has a parent but no message and is not the technical root",
                )
            )

        is_current_path = node_id in current_path_ids

        node_hash = compute_node_hash(
            conversation_id=conversation_id,
            node_id=node_id,
            parent_id=parent_id,
            message_id=message_id,
            has_message=has_message,
            role=role,
            created_at=created_at,
            content_type=content_type,
            content=content,
            asset_refs=asset_refs,
        )

        node_records.append(
            NodeRecord(
                conversation_id=conversation_id,
                node_id=node_id,
                parent_id=parent_id,
                message_id=message_id,
                has_message=has_message,
                role=role,
                created_at=created_at,
                content_type=content_type,
                content=content,
                asset_refs=asset_refs,
                is_technical_root=is_technical_root,
                is_current_path=is_current_path,
                node_hash=node_hash,
            )
        )

        for pointer in asset_pointers:
            asset_id = pointer["asset_id"]
            if asset_id in seen_assets:
                continue
            seen_assets.add(asset_id)
            storage_kind, physical_filename = _classify_asset_storage(
                pointer.get("scheme"), asset_id, physical_dat_names
            )
            original_filename = _resolve_original_filename(asset_map, asset_id)
            # A reference-only asset (see _classify_asset_storage) is not
            # expected to appear in conversation_asset_file_names.json —
            # that map describes physical export assets — so its absence
            # there is not flagged; for an exported asset it remains
            # diagnostically relevant.
            if original_filename is None and storage_kind == ASSET_STORAGE_KIND_EXPORTED:
                anomalies.append(
                    Anomaly(
                        "unresolved_asset_filename",
                        conversation_id,
                        node_id,
                        f"No original filename found in conversation_asset_file_names for {asset_id}",
                    )
                )
            asset_records.append(
                AssetRecord(
                    asset_id=asset_id,
                    physical_filename=physical_filename,
                    original_filename=original_filename,
                    mime_type=None,
                    size_bytes=None,
                    sha256=None,
                    storage_kind=storage_kind,
                )
            )

    if technical_root_count == 0:
        anomalies.append(Anomaly("no_technical_root", conversation_id, None, "No technical root node found"))
    elif technical_root_count > 1:
        anomalies.append(
            Anomaly("multiple_technical_roots", conversation_id, None, f"{technical_root_count} technical root nodes found")
        )

    has_branches = any(count > 1 for count in children_count.values())
    node_hashes_for_conv = [(n.node_id, n.node_hash) for n in node_records]

    conversation_hash = compute_conversation_hash(
        conversation_id=conversation_id,
        source_id=source_id,
        title=raw.get("title"),
        created_at=raw.get("create_time"),
        updated_at=raw.get("update_time"),
        current_node_id=current_node_id,
        default_model_slug=raw.get("default_model_slug"),
        archived=raw.get("is_archived"),
        starred=raw.get("is_starred"),
        memory_scope=raw.get("memory_scope"),
        source_metadata=source_metadata,
        node_hashes=node_hashes_for_conv,
    )

    conversation_record = ConversationRecord(
        conversation_id=conversation_id,
        source_id=source_id,
        title=raw.get("title"),
        created_at=raw.get("create_time"),
        updated_at=raw.get("update_time"),
        current_node_id=current_node_id,
        default_model_slug=raw.get("default_model_slug"),
        archived=raw.get("is_archived"),
        starred=raw.get("is_starred"),
        memory_scope=raw.get("memory_scope"),
        node_count=len(node_records),
        message_count=message_count,
        has_branches=has_branches,
        source_metadata=source_metadata,
        conversation_hash=conversation_hash,
    )

    return conversation_record, node_records, asset_records


def normalize_export(zip_path: Path, schema_version: str = ACNF_SCHEMA_VERSION) -> NormalizationResult:
    """Normalize an entire ChatGPT export ZIP into ACNF records."""
    result = NormalizationResult()

    with ChatGPTExportReader(zip_path) as reader:
        asset_map = reader.conversation_asset_file_names()
        result.conversation_asset_file_names_count = len(asset_map)

        try:
            manifest: Dict[str, Any] = reader.manifest()
        except ExportReaderError as exc:
            manifest = {}
            result.anomalies.append(Anomaly("missing_manifest", None, None, str(exc)))

        # Generic physical-asset inventory: every *.dat member in the ZIP,
        # whether or not any conversation message references it, so no
        # physical asset silently disappears from the normalized output.
        # Computed up front (not after the conversation loop) so per-asset
        # storage_kind classification can consult actual physical
        # presence — see _classify_asset_storage.
        physical_dat_names = reader.physical_dat_filenames()
        physical_dat_names_set: Set[str] = set(physical_dat_names)
        result.physical_dat_asset_count = len(physical_dat_names)

        # Assets are identified by asset_id, deduped across the whole
        # export (not per-conversation): the same physical asset must
        # keep one stable identity regardless of how many
        # conversations/messages reference it (first-seen metadata wins,
        # in deterministic shard/array order).
        assets_by_id: Dict[str, AssetRecord] = {}

        for raw_conversation in reader.iter_conversations():
            conversation_record, node_records, asset_records = normalize_conversation(
                raw_conversation, asset_map, result.anomalies, physical_dat_names=physical_dat_names_set
            )
            result.conversations.append(conversation_record)
            result.nodes.extend(node_records)

            for asset in asset_records:
                if asset.asset_id not in assets_by_id:
                    assets_by_id[asset.asset_id] = asset

        for name in physical_dat_names:
            asset_id = name[: -len(".dat")]
            if asset_id in assets_by_id:
                continue
            assets_by_id[asset_id] = AssetRecord(
                asset_id=asset_id,
                physical_filename=name,
                original_filename=_resolve_original_filename(asset_map, asset_id),
                mime_type=None,
                size_bytes=None,
                sha256=None,
                storage_kind=ASSET_STORAGE_KIND_EXPORTED,
            )

        for asset in assets_by_id.values():
            # Reference-only assets (see _classify_asset_storage) have no
            # expected physical member — physical_filename is None — so no
            # physical-presence check or missing_physical_asset anomaly
            # applies to them; sha256/size_bytes stay None.
            if asset.storage_kind == ASSET_STORAGE_KIND_EXPORTED:
                if reader.has_asset(asset.physical_filename):
                    asset.sha256 = reader.hash_asset_sha256(asset.physical_filename)
                    asset.size_bytes = reader.file_size(asset.physical_filename)
                else:
                    result.anomalies.append(
                        Anomaly(
                            "missing_physical_asset",
                            None,
                            None,
                            f"Physical asset file not found in export: {asset.physical_filename} "
                            f"(asset_id={asset.asset_id})",
                        )
                    )
            asset.asset_hash = compute_asset_hash(
                asset_id=asset.asset_id,
                physical_filename=asset.physical_filename,
                original_filename=asset.original_filename,
                mime_type=asset.mime_type,
                size_bytes=asset.size_bytes,
                sha256=asset.sha256,
                storage_kind=asset.storage_kind,
            )
            result.assets.append(asset)

        raw_library_files = reader.library_files()
        if raw_library_files is not None:
            if isinstance(raw_library_files, list):
                for entry in raw_library_files:
                    if isinstance(entry, dict):
                        library_file_id, source_file_id = _resolve_library_file_identity(
                            entry, result.anomalies
                        )
                        result.library_files.append(
                            LibraryFileRecord(
                                library_file_id=library_file_id,
                                source_file_id=source_file_id,
                                raw_record=entry,
                            )
                        )
                    else:
                        result.anomalies.append(
                            Anomaly(
                                "invalid_library_file_record",
                                None,
                                None,
                                "library_files.json entry is not an object",
                            )
                        )
            else:
                result.anomalies.append(
                    Anomaly(
                        "invalid_library_files_structure",
                        None,
                        None,
                        "library_files.json does not contain a JSON array",
                    )
                )

        source_sha256 = reader.source_sha256()

    acquisition_id = compute_acquisition_id(source_sha256, schema_version)
    result.acquisition = AcquisitionMeta(
        acquisition_id=acquisition_id,
        source_filename=Path(zip_path).name,
        source_sha256=source_sha256,
        normalized_schema_version=schema_version,
        export_metadata=manifest,
        normalized_at=datetime.now(timezone.utc).isoformat(),
    )
    return result


def write_output(result: NormalizationResult, output_dir: Path) -> None:
    """Write acquisition.json, conversations.jsonl, nodes.jsonl, assets.jsonl, library_files.jsonl."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    assert result.acquisition is not None
    with open(output_dir / "acquisition.json", "w", encoding="utf-8") as f:
        json.dump(result.acquisition.to_dict(), f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")

    _write_jsonl(output_dir / "conversations.jsonl", (c.to_dict() for c in result.conversations))
    _write_jsonl(output_dir / "nodes.jsonl", (n.to_dict() for n in result.nodes))
    _write_jsonl(output_dir / "assets.jsonl", (a.to_dict() for a in result.assets))
    _write_jsonl(output_dir / "library_files.jsonl", (r.to_dict() for r in result.library_files))


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
            f.write("\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize a ChatGPT export ZIP into ACNF v0.1")
    parser.add_argument("export_zip", type=Path, help="Path to the ChatGPT export ZIP")
    parser.add_argument("output_dir", type=Path, help="Directory to write normalized ACNF output into")
    parser.add_argument(
        "--expected-baseline",
        choices=sorted(validation_mod.EXPECTED_BASELINES.keys()),
        default=None,
        help="Compare validation metrics against a known baseline acquisition (e.g. chatgpt-acq-001)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    try:
        result = normalize_export(args.export_zip)
    except ExportReaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_output(result, args.output_dir)

    expected = validation_mod.EXPECTED_BASELINES.get(args.expected_baseline) if args.expected_baseline else None
    report = validation_mod.validate(result, expected=expected, expected_baseline_name=args.expected_baseline)
    validation_mod.write_validation_json(report, args.output_dir)

    print(f"Normalized {len(result.conversations)} conversations, {len(result.nodes)} nodes, {len(result.assets)} assets")
    print(f"Anomalies: {len(result.anomalies)}")
    if expected is not None:
        print(f"Baseline validation ({args.expected_baseline}): {'PASSED' if report.passed else 'FAILED'}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
