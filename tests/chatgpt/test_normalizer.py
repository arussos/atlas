"""
M4.1 — Tests for tools/chatgpt/normalizer.py

Covers: graph preservation (technical root, current path, branching,
off-path nodes), asset reference/provenance preservation, structural
anomaly detection, and end-to-end determinism across two normalization
runs of the same synthetic export.
"""

import json
import zipfile

from tools.chatgpt.normalizer import normalize_conversation, normalize_export, write_output
from tests.chatgpt.fixtures import _msg, branching_fixture, multimodal_fixture, write_synthetic_export

_branching_fixture = branching_fixture
_multimodal_fixture = multimodal_fixture
_write_synthetic_export = write_synthetic_export


# ---------------------------------------------------------------------------
# Graph preservation
# ---------------------------------------------------------------------------


def test_technical_root_identified():
    conv, nodes, _ = normalize_conversation(_branching_fixture(), {}, [])
    roots = [n for n in nodes if n.is_technical_root]
    assert len(roots) == 1
    assert roots[0].node_id == "root"
    assert roots[0].role is None
    assert roots[0].message_id is None


def test_no_node_lost():
    raw = _branching_fixture()
    conv, nodes, _ = normalize_conversation(raw, {}, [])
    assert len(nodes) == len(raw["mapping"])
    assert conv.node_count == len(raw["mapping"])


def test_current_path_correct():
    conv, nodes, _ = normalize_conversation(_branching_fixture(current_node="c_user"), {}, [])
    by_id = {n.node_id: n for n in nodes}

    on_path = {"root", "a_user", "a_asst", "b_user", "b2_asst", "c_user"}
    for node_id in on_path:
        assert by_id[node_id].is_current_path is True, node_id

    assert by_id["b1_asst"].is_current_path is False


def test_off_path_branch_preserved_not_deleted():
    conv, nodes, _ = normalize_conversation(_branching_fixture(current_node="c_user"), {}, [])
    node_ids = {n.node_id for n in nodes}
    assert "b1_asst" in node_ids  # off-path but still present


def test_branching_detected():
    conv, nodes, _ = normalize_conversation(_branching_fixture(), {}, [])
    assert conv.has_branches is True


def test_no_branching_on_linear_conversation():
    raw = _branching_fixture()
    # remove one of the two branches to make it linear
    del raw["mapping"]["b1_asst"]
    conv, nodes, _ = normalize_conversation(raw, {}, [])
    assert conv.has_branches is False


def test_message_count_excludes_technical_root():
    raw = _branching_fixture()
    conv, nodes, _ = normalize_conversation(raw, {}, [])
    # 7 mapping entries, 1 is the technical root -> 6 messages
    assert conv.message_count == 6
    assert conv.node_count == 7


def test_current_path_switches_with_current_node():
    conv, nodes, _ = normalize_conversation(_branching_fixture(current_node="b1_asst"), {}, [])
    by_id = {n.node_id: n for n in nodes}
    assert by_id["b1_asst"].is_current_path is True
    assert by_id["b2_asst"].is_current_path is False
    assert by_id["c_user"].is_current_path is False


# ---------------------------------------------------------------------------
# Asset preservation
# ---------------------------------------------------------------------------


def test_asset_reference_extracted_and_resolved():
    asset_map = {"file-2DDLLAw1iPRMn5T7MiTVqFLC.dat": "image.png"}
    conv, nodes, assets = normalize_conversation(_multimodal_fixture(), asset_map, [])

    user_node = next(n for n in nodes if n.node_id == "user_1")
    assert user_node.asset_refs == [
        {
            "asset_id": "file-2DDLLAw1iPRMn5T7MiTVqFLC",
            "pointer_uri": "file-service://file-2DDLLAw1iPRMn5T7MiTVqFLC",
            "content_type": "image_asset_pointer",
        }
    ]

    assert len(assets) == 1
    asset = assets[0]
    assert asset.asset_id == "file-2DDLLAw1iPRMn5T7MiTVqFLC"
    assert asset.storage_kind == "exported"
    assert asset.physical_filename == "file-2DDLLAw1iPRMn5T7MiTVqFLC.dat"
    assert asset.original_filename == "image.png"
    # pointer_uri/content_type are occurrence-level and live on the node's
    # asset_refs entry above, not on the deduplicated physical AssetRecord.
    assert not hasattr(asset, "pointer_uri")
    assert not hasattr(asset, "source_type")


def test_asset_reference_unresolved_flags_anomaly():
    anomalies: list = []
    conv, nodes, assets = normalize_conversation(_multimodal_fixture(), {}, anomalies)
    assert assets[0].original_filename is None
    assert any(a.type == "unresolved_asset_filename" for a in anomalies)


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def test_dangling_parent_flagged():
    raw = {
        "id": "conv-dangling",
        "current_node": "orphan",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "orphan": {"id": "orphan", "parent": "ghost", "message": _msg("m-o", "user", "hi", 1.0)},
        },
    }
    anomalies: list = []
    conv, nodes, _ = normalize_conversation(raw, {}, anomalies)
    assert any(a.type == "dangling_current_path_node" for a in anomalies)
    # the orphan node itself must still be preserved, not dropped
    assert any(n.node_id == "orphan" for n in nodes)


def test_no_technical_root_flagged():
    raw = {
        "id": "conv-no-root",
        "current_node": "a",
        "mapping": {
            "a": {"id": "a", "parent": None, "message": _msg("m-a", "user", "hi", 1.0)},
        },
    }
    anomalies: list = []
    normalize_conversation(raw, {}, anomalies)
    assert any(a.type == "no_technical_root" for a in anomalies)


def test_multiple_technical_roots_flagged():
    raw = {
        "id": "conv-two-roots",
        "current_node": None,
        "mapping": {
            "root1": {"id": "root1", "parent": None, "message": None},
            "root2": {"id": "root2", "parent": None, "message": None},
        },
    }
    anomalies: list = []
    normalize_conversation(raw, {}, anomalies)
    assert any(a.type == "multiple_technical_roots" for a in anomalies)


def test_current_path_cycle_does_not_hang():
    raw = {
        "id": "conv-cycle",
        "current_node": "x",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "x": {"id": "x", "parent": "y", "message": _msg("m-x", "user", "x", 1.0)},
            "y": {"id": "y", "parent": "x", "message": _msg("m-y", "assistant", "y", 2.0)},
        },
    }
    anomalies: list = []
    conv, nodes, _ = normalize_conversation(raw, {}, anomalies)
    assert any(a.type == "current_path_cycle" for a in anomalies)
    assert len(nodes) == 3  # nothing lost despite the cycle


def test_empty_non_root_node_flagged():
    raw = {
        "id": "conv-empty-node",
        "current_node": "a",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "a": {"id": "a", "parent": "root", "message": None},
        },
    }
    anomalies: list = []
    normalize_conversation(raw, {}, anomalies)
    assert any(a.type == "empty_non_root_node" for a in anomalies)


# ---------------------------------------------------------------------------
# End-to-end determinism
# ---------------------------------------------------------------------------


def test_two_runs_produce_identical_canonical_hashes(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)

    result1 = normalize_export(zip_path)
    result2 = normalize_export(zip_path)

    # acquisition_id is a pure function of source content, not wall-clock time
    assert result1.acquisition.acquisition_id == result2.acquisition.acquisition_id
    # normalization timestamp is operational metadata and is expected to vary
    # (both calls happen microseconds apart) — it must not be relied upon
    # for identity, which is exactly what acquisition_id/content hashes verify.

    conv_hashes_1 = sorted((c.conversation_id, c.conversation_hash) for c in result1.conversations)
    conv_hashes_2 = sorted((c.conversation_id, c.conversation_hash) for c in result2.conversations)
    assert conv_hashes_1 == conv_hashes_2

    node_hashes_1 = sorted((n.conversation_id, n.node_id, n.node_hash) for n in result1.nodes)
    node_hashes_2 = sorted((n.conversation_id, n.node_id, n.node_hash) for n in result2.nodes)
    assert node_hashes_1 == node_hashes_2

    asset_hashes_1 = sorted((a.asset_id, a.asset_hash) for a in result1.assets)
    asset_hashes_2 = sorted((a.asset_id, a.asset_hash) for a in result2.assets)
    assert asset_hashes_1 == asset_hashes_2


def test_write_output_produces_expected_files(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    out_dir = tmp_path / "normalized"
    write_output(result, out_dir)

    assert (out_dir / "acquisition.json").exists()
    assert (out_dir / "conversations.jsonl").exists()
    assert (out_dir / "nodes.jsonl").exists()
    assert (out_dir / "assets.jsonl").exists()

    acquisition = json.loads((out_dir / "acquisition.json").read_text(encoding="utf-8"))
    assert acquisition["source_filename"] == "export.zip"
    assert acquisition["normalized_schema_version"] == "0.1"

    conv_lines = (out_dir / "conversations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(conv_lines) == 2
    for line in conv_lines:
        record = json.loads(line)
        assert "conversation_hash" in record


def test_end_to_end_asset_sha256_and_size_populated(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    asset = next(a for a in result.assets if a.asset_id == "file-2DDLLAw1iPRMn5T7MiTVqFLC")
    assert asset.sha256 is not None
    assert asset.size_bytes == len(b"fake-image-bytes")
    assert asset.asset_hash != ""


def test_missing_physical_asset_flags_anomaly_without_crashing(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations-000.json", json.dumps([_multimodal_fixture()]))
        zf.writestr("conversation_asset_file_names.json", json.dumps({}))
        # deliberately omit the physical file-*.dat asset

    result = normalize_export(zip_path)
    assert any(a.type == "missing_physical_asset" for a in result.anomalies)
    asset = result.assets[0]
    assert asset.sha256 is None


# ---------------------------------------------------------------------------
# Deterministic missing conversation id (no random identifiers) — item 1
# ---------------------------------------------------------------------------


def _no_id_fixture() -> dict:
    return {
        "current_node": "root",
        "mapping": {"root": {"id": "root", "parent": None, "message": None}},
    }


def test_missing_conversation_id_is_deterministic_not_random():
    anomalies1: list = []
    anomalies2: list = []
    conv1, _, _ = normalize_conversation(_no_id_fixture(), {}, anomalies1)
    conv2, _, _ = normalize_conversation(_no_id_fixture(), {}, anomalies2)

    assert conv1.conversation_id == conv2.conversation_id
    assert conv1.conversation_id.startswith("synthetic-conv-")
    assert any(a.type == "missing_conversation_id" for a in anomalies1)


def test_missing_conversation_id_deterministic_across_full_export_runs(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([_no_id_fixture()]))

    result1 = normalize_export(zip_path)
    result2 = normalize_export(zip_path)

    assert result1.conversations[0].conversation_id == result2.conversations[0].conversation_id
    assert result1.conversations[0].conversation_hash == result2.conversations[0].conversation_hash
    assert result1.acquisition.acquisition_id == result2.acquisition.acquisition_id


# ---------------------------------------------------------------------------
# id vs conversation_id preserved distinctly — item 2
# ---------------------------------------------------------------------------


def test_id_and_conversation_id_preserved_distinctly_when_different():
    raw = {
        "id": "conv-source-abc",
        "conversation_id": "conv-outer-xyz",
        "current_node": "root",
        "mapping": {"root": {"id": "root", "parent": None, "message": None}},
    }
    conv, _, _ = normalize_conversation(raw, {}, [])
    assert conv.conversation_id == "conv-outer-xyz"
    assert conv.source_id == "conv-source-abc"


def test_conversation_id_falls_back_to_id_when_conversation_id_absent():
    raw = _branching_fixture()
    assert "conversation_id" not in raw
    conv, _, _ = normalize_conversation(raw, {}, [])
    assert conv.conversation_id == "conv-branch"
    assert conv.source_id == "conv-branch"


def test_source_id_falls_back_to_conversation_id_when_id_absent():
    raw = {
        "conversation_id": "conv-only-outer",
        "current_node": "root",
        "mapping": {"root": {"id": "root", "parent": None, "message": None}},
    }
    conv, _, _ = normalize_conversation(raw, {}, [])
    assert conv.conversation_id == "conv-only-outer"
    assert conv.source_id == "conv-only-outer"


# ---------------------------------------------------------------------------
# Unmodelled top-level metadata preservation — item 3
# ---------------------------------------------------------------------------


def test_unmodelled_top_level_metadata_preserved():
    raw = _branching_fixture()
    raw["conversation_template_id"] = "tmpl-1"
    raw["is_do_not_remember"] = True
    raw["plugin_ids"] = ["plugin-a"]
    conv, _, _ = normalize_conversation(raw, {}, [])
    assert conv.source_metadata["conversation_template_id"] == "tmpl-1"
    assert conv.source_metadata["is_do_not_remember"] is True
    assert conv.source_metadata["plugin_ids"] == ["plugin-a"]
    # explicitly modeled fields must not be duplicated into source_metadata
    assert "id" not in conv.source_metadata
    assert "mapping" not in conv.source_metadata
    assert "title" not in conv.source_metadata


def test_source_metadata_change_affects_conversation_hash():
    raw1 = _branching_fixture()
    raw2 = _branching_fixture()
    raw2["pinned_time"] = "2026-01-01T00:00:00Z"
    conv1, _, _ = normalize_conversation(raw1, {}, [])
    conv2, _, _ = normalize_conversation(raw2, {}, [])
    assert conv1.conversation_hash != conv2.conversation_hash


# ---------------------------------------------------------------------------
# Structured asset pointer extraction — item 4
# ---------------------------------------------------------------------------


def test_sediment_audio_pointer_extracted_is_reference_only():
    mapping = {
        "root": {"id": "root", "parent": None, "message": None},
        "user_1": {
            "id": "user_1",
            "parent": "root",
            "message": {
                "id": "m-audio",
                "author": {"role": "user"},
                "create_time": 1.0,
                "content": {
                    "content_type": "multimodal_text",
                    "parts": [
                        {
                            "content_type": "audio_asset_pointer",
                            "asset_pointer": "sediment://file_0000000098dcabcdef",
                            "format": "wav",
                        }
                    ],
                },
            },
        },
    }
    raw = {"id": "conv-audio", "current_node": "user_1", "mapping": mapping}
    anomalies = []
    conv, nodes, assets = normalize_conversation(raw, {}, anomalies)
    node = next(n for n in nodes if n.node_id == "user_1")
    assert node.asset_refs == [
        {
            "asset_id": "file_0000000098dcabcdef",
            "pointer_uri": "sediment://file_0000000098dcabcdef",
            "content_type": "audio_asset_pointer",
        }
    ]
    assert len(assets) == 1
    # RC1 real-data finding (CHATGPT-ACQ-001): sediment:// asset ids are
    # logical references only — the export carries no physical <id>.dat
    # payload for them. See docs/M4.1_CHATGPT_LOSSLESS_NORMALIZER.md.
    assert assets[0].asset_id == "file_0000000098dcabcdef"
    assert assets[0].storage_kind == "reference_only"
    assert assets[0].physical_filename is None
    assert assets[0].sha256 is None
    assert assets[0].size_bytes is None
    assert not any(a.type == "unresolved_asset_filename" for a in anomalies)


def test_nested_real_time_audio_video_pointer_extracted():
    mapping = {
        "root": {"id": "root", "parent": None, "message": None},
        "user_1": {
            "id": "user_1",
            "parent": "root",
            "message": {
                "id": "m-rt",
                "author": {"role": "user"},
                "create_time": 1.0,
                "content": {
                    "content_type": "real_time_user_audio_video_asset_pointer",
                    "audio_asset_pointer": {
                        "content_type": "audio_asset_pointer",
                        "asset_pointer": "sediment://file_aaa111",
                    },
                    "video_container_asset_pointer": {
                        "content_type": "video_container_asset_pointer",
                        "asset_pointer": "sediment://file_bbb222",
                    },
                },
            },
        },
    }
    raw = {"id": "conv-rt", "current_node": "user_1", "mapping": mapping}
    conv, nodes, assets = normalize_conversation(raw, {}, [])
    node = next(n for n in nodes if n.node_id == "user_1")

    refs_by_id = {r["asset_id"]: r for r in node.asset_refs}
    assert set(refs_by_id) == {"file_aaa111", "file_bbb222"}
    assert refs_by_id["file_aaa111"]["content_type"] == "audio_asset_pointer"
    assert refs_by_id["file_aaa111"]["pointer_uri"] == "sediment://file_aaa111"
    assert refs_by_id["file_bbb222"]["content_type"] == "video_container_asset_pointer"
    assert refs_by_id["file_bbb222"]["pointer_uri"] == "sediment://file_bbb222"

    assert {a.asset_id for a in assets} == {"file_aaa111", "file_bbb222"}


def test_image_file_service_pointer_extracted():
    # Same shape already covered by test_asset_reference_extracted_and_resolved,
    # asserted again here explicitly against the new structured extractor
    # per the review's item-4 test list.
    conv, nodes, assets = normalize_conversation(_multimodal_fixture(), {}, [])
    node = next(n for n in nodes if n.node_id == "user_1")
    ref = node.asset_refs[0]
    assert ref["pointer_uri"] == "file-service://file-2DDLLAw1iPRMn5T7MiTVqFLC"
    assert ref["content_type"] == "image_asset_pointer"


# ---------------------------------------------------------------------------
# Asset identity independent of message/conversation provenance — item 5
# ---------------------------------------------------------------------------


def test_same_physical_asset_referenced_by_two_conversations_has_one_identity(tmp_path):
    zip_path = tmp_path / "export.zip"
    conv_a = multimodal_fixture()
    conv_a["id"] = "conv-a"
    conv_b = multimodal_fixture()
    conv_b["id"] = "conv-b"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv_a, conv_b]))
        zf.writestr(
            "conversation_asset_file_names.json",
            json.dumps({"file-2DDLLAw1iPRMn5T7MiTVqFLC.dat": "image.png"}),
        )
        zf.writestr("file-2DDLLAw1iPRMn5T7MiTVqFLC.dat", b"fake-image-bytes")

    result = normalize_export(zip_path)

    matching = [a for a in result.assets if a.asset_id == "file-2DDLLAw1iPRMn5T7MiTVqFLC"]
    assert len(matching) == 1

    referencing_conv_ids = {
        n.conversation_id
        for n in result.nodes
        if any(r["asset_id"] == "file-2DDLLAw1iPRMn5T7MiTVqFLC" for r in n.asset_refs)
    }
    assert referencing_conv_ids == {"conv-a", "conv-b"}


def _pointer_content(pointer_uri: str, content_type: str) -> dict:
    return {
        "content_type": "multimodal_text",
        "parts": [{"content_type": content_type, "asset_pointer": pointer_uri}],
    }


def _single_node_conversation(conv_id: str, msg_id: str, pointer_uri: str, content_type: str) -> dict:
    mapping = {
        "root": {"id": "root", "parent": None, "message": None},
        "n1": {
            "id": "n1",
            "parent": "root",
            "message": {
                "id": msg_id,
                "author": {"role": "user"},
                "create_time": 1.0,
                "content": _pointer_content(pointer_uri, content_type),
            },
        },
    }
    return {"id": conv_id, "current_node": "n1", "mapping": mapping}


def test_differing_reference_metadata_preserved_independently_per_node(tmp_path):
    """
    Two nodes in two different conversations reference the same physical
    asset_id ("SHARED123") but describe it differently (a contrived but
    legal case: different scheme, different content_type). Physical-asset
    dedup must collapse them to one AssetRecord, but neither occurrence's
    own pointer_uri/content_type may be lost or overwritten by the
    other's — "first-seen wins" must apply only to physical identity, not
    to per-node reference metadata.
    """
    zip_path = tmp_path / "export.zip"
    conv_a = _single_node_conversation("conv-a", "m-a", "file-service://SHARED123", "image_asset_pointer")
    conv_b = _single_node_conversation("conv-b", "m-b", "sediment://SHARED123", "audio_asset_pointer")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv_a, conv_b]))

    result = normalize_export(zip_path)

    # Physical asset inventory: exactly one record for the shared asset_id
    # (proves same physical asset used by two different nodes exists once).
    matching = [a for a in result.assets if a.asset_id == "SHARED123"]
    assert len(matching) == 1
    # AssetRecord no longer carries any reference-level field at all, so
    # there is nothing for "first-seen wins" to silently substitute.
    assert not hasattr(matching[0], "pointer_uri")
    assert not hasattr(matching[0], "source_type")

    node_a = next(n for n in result.nodes if n.conversation_id == "conv-a" and n.node_id == "n1")
    node_b = next(n for n in result.nodes if n.conversation_id == "conv-b" and n.node_id == "n1")

    ref_a = next(r for r in node_a.asset_refs if r["asset_id"] == "SHARED123")
    ref_b = next(r for r in node_b.asset_refs if r["asset_id"] == "SHARED123")

    # Both references remain independently preserved, each retaining its
    # own (differing) pointer_uri/content_type — proving reference
    # metadata may differ without changing physical asset identity, and
    # that neither occurrence silently overwrote the other's.
    assert ref_a["pointer_uri"] == "file-service://SHARED123"
    assert ref_a["content_type"] == "image_asset_pointer"
    assert ref_b["pointer_uri"] == "sediment://SHARED123"
    assert ref_b["content_type"] == "audio_asset_pointer"


# ---------------------------------------------------------------------------
# Physical asset inventory — item 7
# ---------------------------------------------------------------------------


def test_orphan_physical_dat_file_not_lost(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("file-ORPHAN12345.dat", b"unreferenced-bytes")

    result = normalize_export(zip_path)

    assert result.physical_dat_asset_count == 1
    orphan = next(a for a in result.assets if a.asset_id == "file-ORPHAN12345")
    assert orphan.physical_filename == "file-ORPHAN12345.dat"
    assert orphan.sha256 is not None
    assert orphan.size_bytes == len(b"unreferenced-bytes")


# ---------------------------------------------------------------------------
# Message count semantics — item 8
# ---------------------------------------------------------------------------


def test_malformed_message_without_id_still_counted_and_flagged():
    raw = {
        "id": "conv-malformed-msg",
        "current_node": "a",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "a": {
                "id": "a",
                "parent": "root",
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["hi"]},
                },
            },
        },
    }
    anomalies: list = []
    conv, nodes, _ = normalize_conversation(raw, {}, anomalies)
    node_a = next(n for n in nodes if n.node_id == "a")

    assert node_a.has_message is True
    assert node_a.message_id is None
    assert conv.message_count == 1
    assert any(a.type == "message_missing_id" for a in anomalies)


# ---------------------------------------------------------------------------
# library_files.json preservation — item 6
# ---------------------------------------------------------------------------


def _lib_entry(libfile_id: str, file_id: str, **extra) -> dict:
    entry = {
        "id": {"id": libfile_id, "partition_key": libfile_id},
        "file_id": file_id,
    }
    entry.update(extra)
    return entry


def test_library_files_preserved(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr(
            "library_files.json",
            json.dumps(
                [
                    _lib_entry("libfile_ABC", "file_XYZ", name="doc.pdf", size=123),
                    _lib_entry("libfile_DEF", "file_UVW", name="notes.txt"),
                ]
            ),
        )

    result = normalize_export(zip_path)

    assert len(result.library_files) == 2
    ids = {r.library_file_id for r in result.library_files}
    assert ids == {"libfile_ABC", "libfile_DEF"}
    source_ids = {r.source_file_id for r in result.library_files}
    assert source_ids == {"file_XYZ", "file_UVW"}
    names = {r.raw_record["name"] for r in result.library_files}
    assert names == {"doc.pdf", "notes.txt"}
    # the full raw record must survive losslessly, not just id/name
    lib1 = next(r for r in result.library_files if r.library_file_id == "libfile_ABC")
    assert lib1.raw_record == _lib_entry("libfile_ABC", "file_XYZ", name="doc.pdf", size=123)
    assert lib1.raw_record["id"]["partition_key"] == "libfile_ABC"


def test_library_files_absent_produces_no_records(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))

    result = normalize_export(zip_path)
    assert result.library_files == []


def test_write_output_writes_library_files_jsonl(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr(
            "library_files.json", json.dumps([_lib_entry("libfile_ABC", "file_XYZ", name="doc.pdf")])
        )

    result = normalize_export(zip_path)
    out_dir = tmp_path / "normalized"
    write_output(result, out_dir)

    assert (out_dir / "library_files.jsonl").exists()
    lines = (out_dir / "library_files.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["library_file_id"] == "libfile_ABC"
    assert record["source_file_id"] == "file_XYZ"
    assert record["raw_record"]["name"] == "doc.pdf"
    assert record["raw_record"]["id"]["partition_key"] == "libfile_ABC"


# ---------------------------------------------------------------------------
# RC3 real-data finding (CHATGPT-ACQ-001) — library file identity
# normalization: raw["id"] is {"id", "partition_key"}, distinct from
# raw["file_id"]. See docs/M4.1_CHATGPT_LOSSLESS_NORMALIZER.md.
# ---------------------------------------------------------------------------


def test_library_file_nested_id_and_file_id_normalized(tmp_path):
    """Item A: normal real shape produces distinct scalar ids and a
    losslessly preserved raw_record."""
    zip_path = tmp_path / "export.zip"
    raw_entry = {"id": {"id": "libfile_ABC", "partition_key": "libfile_ABC"}, "file_id": "file_XYZ"}
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps([raw_entry]))

    result = normalize_export(zip_path)

    assert len(result.library_files) == 1
    record = result.library_files[0]
    assert record.library_file_id == "libfile_ABC"
    assert record.source_file_id == "file_XYZ"
    assert record.raw_record == raw_entry
    assert not any(a.type in ("malformed_library_file_id", "missing_library_file_source_id") for a in result.anomalies)


def test_library_file_partition_key_survives_in_raw_record(tmp_path):
    """Item B: partition_key is not discarded even though it plays no role
    in scalar identity resolution."""
    zip_path = tmp_path / "export.zip"
    raw_entry = {"id": {"id": "libfile_ABC", "partition_key": "some-other-partition"}, "file_id": "file_XYZ"}
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps([raw_entry]))

    result = normalize_export(zip_path)

    record = result.library_files[0]
    assert record.raw_record["id"]["partition_key"] == "some-other-partition"
    assert record.library_file_id == "libfile_ABC"


def test_library_files_distinct_ids_stay_distinct_with_matching_metadata(tmp_path):
    """Item C: two records with different libfile ids remain distinct even
    when every other field matches."""
    zip_path = tmp_path / "export.zip"
    entries = [
        {"id": {"id": "libfile_ONE", "partition_key": "p"}, "file_id": "file_SAME", "name": "same.pdf"},
        {"id": {"id": "libfile_TWO", "partition_key": "p"}, "file_id": "file_SAME", "name": "same.pdf"},
    ]
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps(entries))

    result = normalize_export(zip_path)

    assert len(result.library_files) == 2
    ids = {r.library_file_id for r in result.library_files}
    assert ids == {"libfile_ONE", "libfile_TWO"}


def test_library_file_malformed_id_gets_deterministic_fallback(tmp_path):
    """Item D: malformed/missing raw id produces a deterministic fallback
    and an anomaly, without losing raw_record."""
    zip_path = tmp_path / "export.zip"
    raw_entry = {"file_id": "file_XYZ", "name": "orphan.pdf"}  # no "id" at all
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps([raw_entry]))

    result1 = normalize_export(zip_path)
    result2 = normalize_export(zip_path)

    record1 = result1.library_files[0]
    record2 = result2.library_files[0]
    assert record1.library_file_id == record2.library_file_id  # deterministic, not random
    assert record1.library_file_id.startswith("synthetic-libfile-")
    assert record1.raw_record == raw_entry
    assert any(a.type == "malformed_library_file_id" for a in result1.anomalies)


def test_library_file_malformed_id_shape_also_falls_back(tmp_path):
    """raw["id"] present but not the expected {"id": <str>, ...} shape is
    also treated as malformed, not silently accepted."""
    zip_path = tmp_path / "export.zip"
    raw_entry = {"id": "libfile_FLAT_STRING", "file_id": "file_XYZ"}
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps([raw_entry]))

    result = normalize_export(zip_path)

    record = result.library_files[0]
    assert record.library_file_id.startswith("synthetic-libfile-")
    assert record.raw_record == raw_entry
    assert any(a.type == "malformed_library_file_id" for a in result.anomalies)


def test_library_file_missing_source_file_id_preserved_as_none(tmp_path):
    """Item E: missing source file_id is preserved as None plus an
    anomaly, without affecting library_file_id determinism."""
    zip_path = tmp_path / "export.zip"
    raw_entry = {"id": {"id": "libfile_ABC", "partition_key": "libfile_ABC"}}  # no file_id
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([]))
        zf.writestr("library_files.json", json.dumps([raw_entry]))

    result1 = normalize_export(zip_path)
    result2 = normalize_export(zip_path)

    assert result1.library_files[0].source_file_id is None
    assert result1.library_files[0].library_file_id == "libfile_ABC"
    assert result1.library_files[0].library_file_id == result2.library_files[0].library_file_id
    assert result1.library_files[0].raw_record == raw_entry
    assert any(a.type == "missing_library_file_source_id" for a in result1.anomalies)


# ---------------------------------------------------------------------------
# RC1 real-data finding (CHATGPT-ACQ-001) — asset storage classes (M4.1 RC2)
#
# The first real-data run identified 122 sediment:// asset ids referenced
# only inside conversation JSON, with no physical <asset_id>.dat member in
# the export. These are logical/reference-only assets, not missing files:
# see docs/M4.1_CHATGPT_LOSSLESS_NORMALIZER.md, "Asset storage classes".
# ---------------------------------------------------------------------------


def test_sediment_image_reference_with_no_physical_dat_is_reference_only(tmp_path):
    zip_path = tmp_path / "export.zip"
    conv = _single_node_conversation(
        "conv-sed-img", "m-img", "sediment://file_0000000098dc71f6889f91e3db3e2290", "image_asset_pointer"
    )
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv]))
        zf.writestr("conversation_asset_file_names.json", json.dumps({}))
        # deliberately no physical file_0000000098dc71f6889f91e3db3e2290.dat member

    result = normalize_export(zip_path)

    asset = next(a for a in result.assets if a.asset_id == "file_0000000098dc71f6889f91e3db3e2290")
    assert asset.storage_kind == "reference_only"
    assert asset.physical_filename is None
    assert asset.sha256 is None
    assert asset.size_bytes is None

    node = next(n for n in result.nodes if n.conversation_id == "conv-sed-img" and n.node_id == "n1")
    assert any(r["asset_id"] == "file_0000000098dc71f6889f91e3db3e2290" for r in node.asset_refs)

    assert not any(a.type == "missing_physical_asset" for a in result.anomalies)
    assert not any(a.type == "unresolved_asset_filename" for a in result.anomalies)


def test_sediment_audio_reference_with_no_physical_dat_is_reference_only(tmp_path):
    zip_path = tmp_path / "export.zip"
    conv = _single_node_conversation("conv-sed-audio", "m-audio", "sediment://file_deadbeef987654321", "audio_asset_pointer")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv]))
        # conversation_asset_file_names.json omitted entirely — must not matter

    result = normalize_export(zip_path)

    asset = next(a for a in result.assets if a.asset_id == "file_deadbeef987654321")
    assert asset.storage_kind == "reference_only"
    assert asset.physical_filename is None
    assert asset.sha256 is None
    assert asset.size_bytes is None
    assert not any(a.type == "missing_physical_asset" for a in result.anomalies)
    assert not any(a.type == "unresolved_asset_filename" for a in result.anomalies)


def test_file_service_asset_with_valid_dat_is_exported(tmp_path):
    zip_path = tmp_path / "export.zip"
    conv = _single_node_conversation("conv-fs-valid", "m-fs-valid", "file-service://file-VALID123", "image_asset_pointer")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv]))
        zf.writestr("conversation_asset_file_names.json", json.dumps({"file-VALID123.dat": "photo.jpg"}))
        zf.writestr("file-VALID123.dat", b"real-bytes")

    result = normalize_export(zip_path)

    asset = next(a for a in result.assets if a.asset_id == "file-VALID123")
    assert asset.storage_kind == "exported"
    assert asset.physical_filename == "file-VALID123.dat"
    assert asset.sha256 is not None
    assert asset.size_bytes == len(b"real-bytes")
    assert not any(a.type == "missing_physical_asset" for a in result.anomalies)


def test_file_service_asset_missing_physical_dat_still_anomalous(tmp_path):
    # Weakening validation for sediment:// reference-only assets must not
    # weaken it for file-service:// assets: a genuinely missing exported
    # physical asset remains a real anomaly.
    zip_path = tmp_path / "export.zip"
    conv = _single_node_conversation("conv-fs-missing", "m-fs-missing", "file-service://file-GONE456", "image_asset_pointer")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv]))
        zf.writestr("conversation_asset_file_names.json", json.dumps({}))
        # deliberately omit file-GONE456.dat

    result = normalize_export(zip_path)

    asset = next(a for a in result.assets if a.asset_id == "file-GONE456")
    assert asset.storage_kind == "exported"
    assert asset.physical_filename == "file-GONE456.dat"
    assert asset.sha256 is None
    assert any(a.type == "missing_physical_asset" and "file-GONE456" in a.detail for a in result.anomalies)
    assert any(a.type == "unresolved_asset_filename" for a in result.anomalies)


def test_reference_only_asset_hash_deterministic_across_repeated_runs(tmp_path):
    zip_path = tmp_path / "export.zip"
    conv = _single_node_conversation("conv-sed-det", "m-sed-det", "sediment://file_detabc123", "image_asset_pointer")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", json.dumps({"export_files": ["conversations-000.json"]}))
        zf.writestr("conversations-000.json", json.dumps([conv]))

    result1 = normalize_export(zip_path)
    result2 = normalize_export(zip_path)

    asset1 = next(a for a in result1.assets if a.asset_id == "file_detabc123")
    asset2 = next(a for a in result2.assets if a.asset_id == "file_detabc123")
    assert asset1.storage_kind == "reference_only" == asset2.storage_kind
    assert asset1.asset_hash == asset2.asset_hash
    assert asset1.asset_hash != ""
