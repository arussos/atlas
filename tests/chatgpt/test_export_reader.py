"""
M4.1 — Tests for tools/chatgpt/export_reader.py

All fixtures are synthetic ZIPs built in-memory/on tmp_path — no real
ChatGPT export data is used, per M4.1 raw-data policy.
"""

import json
import zipfile

import pytest

from tools.chatgpt.export_reader import ChatGPTExportReader, ExportReaderError


def _write_zip(path, files: dict) -> None:
    """
    Write a ZIP at path. `files` maps archive member name -> content.
    dict/list values are JSON-encoded; str/bytes values are written as-is.
    """
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            if isinstance(content, (dict, list)):
                zf.writestr(name, json.dumps(content))
            elif isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, str(content))


def _minimal_conversation(conv_id: str = "conv-1") -> dict:
    return {
        "id": conv_id,
        "title": "Test",
        "create_time": 1700000000.0,
        "update_time": 1700000100.0,
        "current_node": "root",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
        },
    }


# ---------------------------------------------------------------------------
# ZIP-level errors
# ---------------------------------------------------------------------------


def test_missing_zip_raises(tmp_path):
    with pytest.raises(ExportReaderError):
        ChatGPTExportReader(tmp_path / "does-not-exist.zip")


def test_invalid_zip_raises(tmp_path):
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"this is not a zip file at all")
    with pytest.raises(ExportReaderError):
        ChatGPTExportReader(bad_zip)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def test_missing_manifest_raises_on_access(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"conversations-000.json": [_minimal_conversation()]})
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            reader.manifest()


def test_invalid_manifest_json_raises(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("export_manifest.json", "{not valid json")
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            reader.manifest()


def test_manifest_must_be_json_object(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"export_manifest.json": ["not", "an", "object"]})
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            reader.manifest()


def test_valid_manifest_parsed(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"export_manifest.json": {"version": 1, "export_files": []}})
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.manifest() == {"version": 1, "export_files": []}


# ---------------------------------------------------------------------------
# Shard discovery
# ---------------------------------------------------------------------------


def test_shard_discovery_via_manifest(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "export_manifest.json": {"export_files": ["conversations-000.json", "conversations-001.json"]},
            "conversations-000.json": [_minimal_conversation("a")],
            "conversations-001.json": [_minimal_conversation("b")],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        shards = reader.discover_conversation_shards()
        assert shards == ["conversations-000.json", "conversations-001.json"]


def test_shard_discovery_fallback_without_manifest_reference(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "export_manifest.json": {"version": 1},  # no shard names listed
            "conversations-000.json": [_minimal_conversation("a")],
            "conversations-001.json": [_minimal_conversation("b")],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        shards = reader.discover_conversation_shards()
        assert shards == ["conversations-000.json", "conversations-001.json"]


def test_shard_discovery_without_manifest_at_all(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation("a")],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        shards = reader.discover_conversation_shards()
        assert shards == ["conversations-000.json"]


def test_shard_discovery_numeric_not_lexicographic_ordering(tmp_path):
    zip_path = tmp_path / "export.zip"
    # Non-zero-padded indices: lexicographic sort would put "10" before "2".
    _write_zip(
        zip_path,
        {
            "conversations-10.json": [_minimal_conversation("j")],
            "conversations-2.json": [_minimal_conversation("c")],
            "conversations-1.json": [_minimal_conversation("b")],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        shards = reader.discover_conversation_shards()
        assert shards == ["conversations-1.json", "conversations-2.json", "conversations-10.json"]


def test_no_shards_found_raises(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"export_manifest.json": {"version": 1}})
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            reader.discover_conversation_shards()


# ---------------------------------------------------------------------------
# Conversation iteration
# ---------------------------------------------------------------------------


def test_iter_conversations_shard_and_array_order(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation("a1"), _minimal_conversation("a2")],
            "conversations-001.json": [_minimal_conversation("b1")],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        ids = [c["id"] for c in reader.iter_conversations()]
        assert ids == ["a1", "a2", "b1"]


def test_iter_conversations_shard_not_a_list_raises(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations-000.json", json.dumps({"not": "a list"}))
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            list(reader.iter_conversations())


def test_iter_conversations_non_object_entry_raises(tmp_path):
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations-000.json", json.dumps(["not-an-object"]))
    with ChatGPTExportReader(zip_path) as reader:
        with pytest.raises(ExportReaderError):
            list(reader.iter_conversations())


# ---------------------------------------------------------------------------
# Asset filename mapping / library files
# ---------------------------------------------------------------------------


def test_conversation_asset_file_names_present(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation()],
            "conversation_asset_file_names.json": {"file-ABC123.dat": "image.png"},
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.conversation_asset_file_names() == {"file-ABC123.dat": "image.png"}


def test_conversation_asset_file_names_absent_returns_empty_dict(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"conversations-000.json": [_minimal_conversation()]})
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.conversation_asset_file_names() == {}


def test_library_files_present_and_absent(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation()],
            "library_files.json": [{"id": "lib-1", "name": "doc.pdf"}],
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.library_files() == [{"id": "lib-1", "name": "doc.pdf"}]

    zip_path2 = tmp_path / "export2.zip"
    _write_zip(zip_path2, {"conversations-000.json": [_minimal_conversation()]})
    with ChatGPTExportReader(zip_path2) as reader:
        assert reader.library_files() is None


def test_physical_dat_filenames_lists_all_dat_members_sorted(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation()],
            "file-B.dat": b"b",
            "file-A.dat": b"a",
            "not-an-asset.json": {"x": 1},
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.physical_dat_filenames() == ["file-A.dat", "file-B.dat"]


def test_hash_asset_sha256_streaming_matches_full_read(tmp_path):
    import hashlib

    zip_path = tmp_path / "export.zip"
    payload = b"x" * 200000
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation()],
            "file-BIG.dat": payload,
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.hash_asset_sha256("file-BIG.dat") == hashlib.sha256(payload).hexdigest()
        assert reader.hash_asset_sha256("file-MISSING.dat") is None


def test_has_asset_and_read_asset_bytes(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(
        zip_path,
        {
            "conversations-000.json": [_minimal_conversation()],
            "file-ABC123.dat": b"\x89PNGfakepixels",
        },
    )
    with ChatGPTExportReader(zip_path) as reader:
        assert reader.has_asset("file-ABC123.dat") is True
        assert reader.has_asset("file-NOPE.dat") is False
        assert reader.read_asset_bytes("file-ABC123.dat") == b"\x89PNGfakepixels"
        assert reader.read_asset_bytes("file-NOPE.dat") is None


# ---------------------------------------------------------------------------
# Source identity
# ---------------------------------------------------------------------------


def test_source_sha256_deterministic(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_zip(zip_path, {"conversations-000.json": [_minimal_conversation()]})
    with ChatGPTExportReader(zip_path) as reader:
        h1 = reader.source_sha256()
        h2 = reader.source_sha256()
        assert h1 == h2
        assert len(h1) == 64


def test_source_sha256_differs_for_different_content(tmp_path):
    zip_a = tmp_path / "a.zip"
    zip_b = tmp_path / "b.zip"
    _write_zip(zip_a, {"conversations-000.json": [_minimal_conversation("a")]})
    _write_zip(zip_b, {"conversations-000.json": [_minimal_conversation("b")]})
    with ChatGPTExportReader(zip_a) as reader_a, ChatGPTExportReader(zip_b) as reader_b:
        assert reader_a.source_sha256() != reader_b.source_sha256()
