#!/usr/bin/env python3
"""
Test suite for atlas-import.py — M2.3 / M2.4 / M2.4.1

Tests all logic functions in isolation without network calls or a live
Open WebUI instance. HTTP functions are replaced by local stubs.
"""

import json
import os
import sys
import tempfile
import urllib.error
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make tools/ importable from any working directory
sys.path.insert(0, str(Path(__file__).parent))

import atlas_import as ai

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    label = PASS if condition else FAIL
    _results.append((name, condition, detail))
    suffix = f"  ({detail})" if detail and not condition else ""
    print(f"  [{label}] {name}{suffix}")


# ---------------------------------------------------------------------------
# 1. Missing environment variables
# ---------------------------------------------------------------------------

def test_missing_env_vars() -> None:
    print("\n1. Missing environment variables")

    _required = ["ATLAS_OPENWEBUI_URL", "ATLAS_OPENWEBUI_EMAIL", "ATLAS_OPENWEBUI_PASSWORD"]
    env_backup = {k: os.environ.pop(k, None) for k in _required}
    try:
        raised = False
        msg = ""
        try:
            ai.load_sync_config()
        except EnvironmentError as exc:
            raised = True
            msg = str(exc)
        check("raises EnvironmentError when all vars missing", raised)
        check("message lists missing vars", "ATLAS_OPENWEBUI_URL" in msg)

        # Only one missing
        os.environ["ATLAS_OPENWEBUI_URL"] = "http://example.com"
        os.environ["ATLAS_OPENWEBUI_EMAIL"] = "user@example.com"
        # ATLAS_OPENWEBUI_PASSWORD still missing
        try:
            ai.load_sync_config()
            raised = False
        except EnvironmentError as exc:
            raised = True
            msg = str(exc)
        check("raises EnvironmentError for single missing var", raised)
        check("message names the missing var", "ATLAS_OPENWEBUI_PASSWORD" in msg)

        # All present (knowledge_name set separately from CLI arg)
        os.environ["ATLAS_OPENWEBUI_PASSWORD"] = "secret"
        cfg = ai.load_sync_config()
        check("returns SyncConfig when all vars present", cfg.url == "http://example.com")
        check("strips trailing slash from URL", not cfg.url.endswith("/"))
        check("default process_timeout is 300", cfg.process_timeout == 300)
        check("knowledge_name is empty (set from CLI)", cfg.knowledge_name == "")

    finally:
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        for k in _required:
            os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# 2. Knowledge collection not found
# ---------------------------------------------------------------------------

def test_knowledge_not_found() -> None:
    print("\n2. Knowledge Collection not found")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="NonExistent",
    )
    collections = [
        {"id": "abc", "name": "Foundation"},
        {"id": "def", "name": "Networking"},
    ]

    raised = False
    msg = ""
    try:
        with patch.object(ai, "http_get", return_value=collections):
            ai.find_knowledge_collection(cfg, "token")
    except RuntimeError as exc:
        raised = True
        msg = str(exc)

    check("raises RuntimeError when name not found", raised)
    check("message mentions the searched name", "NonExistent" in msg)
    check("message lists available names", "Foundation" in msg)


def test_knowledge_found() -> None:
    print("\n   Knowledge Collection found")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )
    collections = [
        {"id": "abc123", "name": "Foundation"},
        {"id": "def456", "name": "Networking"},
    ]
    with patch.object(ai, "http_get", return_value=collections):
        kid, kname = ai.find_knowledge_collection(cfg, "token")

    check("returns correct id", kid == "abc123")
    check("returns correct name", kname == "Foundation")


# ---------------------------------------------------------------------------
# 3. Authentication failure
# ---------------------------------------------------------------------------

def test_auth_failed() -> None:
    print("\n3. Authentication failure")

    cfg = ai.SyncConfig(
        url="http://example.com", email="bad@example.com",
        password="wrong", knowledge_name="Foundation",
    )

    def raise_401(*a, **kw):
        raise urllib.error.HTTPError(
            cfg.url, 401, "Unauthorized", {}, None
        )

    with patch.object(ai, "http_post_json", side_effect=raise_401):
        raised = False
        try:
            ai.authenticate(cfg)
        except urllib.error.HTTPError as exc:
            raised = True
            code = exc.code
    check("HTTPError propagates from authenticate()", raised)
    check("error code is 401", code == 401)


def test_auth_no_token() -> None:
    print("\n   Auth response with no token field")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )
    with patch.object(ai, "http_post_json", return_value={"user": "andrea"}):
        raised = False
        try:
            ai.authenticate(cfg)
        except RuntimeError:
            raised = True
    check("raises RuntimeError when response has no 'token'", raised)


# ---------------------------------------------------------------------------
# 4. Upload failure
# ---------------------------------------------------------------------------

def test_upload_failed() -> None:
    print("\n4. Upload failure")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        f.write(b"# Test\n\nContent.")
        tmp = Path(f.name)

    def raise_500(*a, **kw):
        raise urllib.error.HTTPError(
            cfg.url, 500, "Internal Server Error", {}, None
        )

    doc = ai.DocumentInfo(
        path=tmp, relative_path=Path("knowledge/test.md"),
        filename="test.md", title="Test", size_bytes=0,
        modified=datetime.min, sha256="abc",
    )

    with patch.object(ai, "http_post_multipart", side_effect=raise_500):
        result = ai.sync_document(cfg, "token", "kid", doc)

    check("sync_document returns False on upload failure", not result)
    check("doc.sync_status is FAILED after upload failure", doc.sync_status == ai.SYNC_FAILED)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 5. Processing failed
# ---------------------------------------------------------------------------

def test_processing_failed() -> None:
    print("\n5. Processing failed")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation", process_timeout=10,
    )

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        f.write(b"# Test\n")
        tmp = Path(f.name)

    doc = ai.DocumentInfo(
        path=tmp, relative_path=Path("knowledge/test.md"),
        filename="test.md", title="Test", size_bytes=0,
        modified=datetime.min, sha256="abc",
    )

    with (
        patch.object(ai, "http_post_multipart", return_value={"id": "file-xyz"}),
        patch.object(ai, "http_get", return_value={"status": "failed", "detail": "parse error"}),
    ):
        result = ai.sync_document(cfg, "token", "kid", doc)

    check("sync_document returns False when processing fails", not result)
    check("doc.sync_status is FAILED", doc.sync_status == ai.SYNC_FAILED)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 6. Processing timeout
# ---------------------------------------------------------------------------

def test_processing_timeout() -> None:
    print("\n6. Processing timeout")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation", process_timeout=1,
    )

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        f.write(b"# Test\n")
        tmp = Path(f.name)

    doc = ai.DocumentInfo(
        path=tmp, relative_path=Path("knowledge/test.md"),
        filename="test.md", title="Test", size_bytes=0,
        modified=datetime.min, sha256="abc",
    )

    call_count = 0

    def slow_status(*a, **kw):
        nonlocal call_count
        call_count += 1
        return {"status": "processing"}

    with (
        patch.object(ai, "http_post_multipart", return_value={"id": "file-xyz"}),
        patch.object(ai, "http_get", side_effect=slow_status),
        patch.object(ai, "time") as mock_time,
    ):
        # Simulate time advancing past deadline after first poll
        mock_time.monotonic.side_effect = [0, 0, 999]
        mock_time.sleep = MagicMock()
        result = ai.sync_document(cfg, "token", "kid", doc)

    check("sync_document returns False on timeout", not result)
    check("doc.sync_status is FAILED on timeout", doc.sync_status == ai.SYNC_FAILED)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 7. Association failure
# ---------------------------------------------------------------------------

def test_association_failed() -> None:
    print("\n7. Association failure")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        f.write(b"# Test\n")
        tmp = Path(f.name)

    doc = ai.DocumentInfo(
        path=tmp, relative_path=Path("knowledge/test.md"),
        filename="test.md", title="Test", size_bytes=0,
        modified=datetime.min, sha256="abc",
    )

    def add_raises(*a, **kw):
        raise urllib.error.HTTPError(cfg.url, 404, "Not Found", {}, None)

    with (
        patch.object(ai, "http_post_multipart", return_value={"id": "file-xyz"}),
        patch.object(ai, "http_get", return_value={"status": "completed"}),
        patch.object(ai, "http_post_json", side_effect=add_raises),
    ):
        result = ai.sync_document(cfg, "token", "kid", doc)

    check("sync_document returns False on association failure", not result)
    check("doc.sync_status is FAILED", doc.sync_status == ai.SYNC_FAILED)
    check("doc.synced_sha256 is NOT set after partial failure", doc.synced_sha256 is None)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 8. Full success
# ---------------------------------------------------------------------------

def test_full_success() -> None:
    print("\n8. Full success")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        f.write(b"# Foundation-001\n\nContent.")
        tmp = Path(f.name)

    doc = ai.DocumentInfo(
        path=tmp, relative_path=Path("knowledge/FOUNDATION-001.md"),
        filename="FOUNDATION-001.md", title="Foundation-001", size_bytes=42,
        modified=datetime.min, sha256="deadbeef",
    )

    with (
        patch.object(ai, "http_post_multipart", return_value={"id": "file-abc123"}),
        patch.object(ai, "http_get", return_value={"status": "completed"}),
        patch.object(ai, "http_post_json", return_value={}),
    ):
        result = ai.sync_document(cfg, "token", "knowledge-001", doc)

    check("sync_document returns True on full success", result)
    check("doc.sync_status is SYNCED", doc.sync_status == ai.SYNC_SYNCED)
    check("doc.remote_file_id is set", doc.remote_file_id == "file-abc123")
    check("doc.remote_knowledge_id is set", doc.remote_knowledge_id == "knowledge-001")
    check("doc.synced_sha256 matches doc.sha256", doc.synced_sha256 == "deadbeef")
    check("doc.synced_at is set", doc.synced_at is not None)
    tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 9. Retry of FAILED / PENDING documents
# ---------------------------------------------------------------------------

def test_retry_failed_pending() -> None:
    print("\n9. Retry of FAILED and PENDING documents")

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "knowledge-index.json"
        knowledge_dir = Path(tmpdir) / "knowledge"
        knowledge_dir.mkdir()

        # Create a document
        doc_path = knowledge_dir / "test.md"
        doc_path.write_text("# Test\n\nContent.", encoding="utf-8")

        # Simulate an index with a FAILED entry for this document
        sha = ai.compute_sha256(doc_path)
        index_data = {
            "version": 2,
            "last_updated": datetime.now().isoformat(),
            "documents": {
                "knowledge/test.md": {
                    "relative_path": "knowledge/test.md",
                    "sha256": sha,
                    "size_bytes": doc_path.stat().st_size,
                    "modified": datetime.now().isoformat(),
                    "sync_status": ai.SYNC_FAILED,
                    "remote_file_id": None,
                    "remote_knowledge_id": None,
                    "synced_sha256": None,
                    "synced_at": None,
                }
            },
        }
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        # The knowledge_dir parent is tmpdir, so relative_to(knowledge_dir.parent) = relative_to(tmpdir)
        # We need to fake the project structure slightly
        index = ai.load_index(index_path)

        result = ai.ScanResult()
        doc = ai.collect_document(doc_path, knowledge_dir)
        result.documents.append(doc)
        ai.detect_changes(result, index)

        check(
            "UNCHANGED locally (sha256 unchanged)",
            doc.status == ai.STATUS_UNCHANGED,
            f"got {doc.status}",
        )
        check(
            "sync_status loaded as FAILED from index",
            doc.sync_status == ai.SYNC_FAILED,
            f"got {doc.sync_status}",
        )
        check(
            "needs_sync() returns True for FAILED document",
            ai.needs_sync(doc),
        )

        # Now test PENDING
        doc.sync_status = ai.SYNC_PENDING
        check("needs_sync() returns True for PENDING document", ai.needs_sync(doc))

        # And a SYNCED + UNCHANGED document should NOT need sync
        doc.sync_status = ai.SYNC_SYNCED
        check(
            "needs_sync() returns False for UNCHANGED+SYNCED document",
            not ai.needs_sync(doc),
        )


# ---------------------------------------------------------------------------
# 10. No upload for UNCHANGED + SYNCED
# ---------------------------------------------------------------------------

def test_no_upload_for_synced() -> None:
    print("\n10. No upload for UNCHANGED + SYNCED")

    with tempfile.TemporaryDirectory() as tmpdir:
        knowledge_dir = Path(tmpdir) / "knowledge"
        knowledge_dir.mkdir()
        doc_path = knowledge_dir / "synced.md"
        doc_path.write_text("# Synced\n\nContent.", encoding="utf-8")

        sha = ai.compute_sha256(doc_path)
        index = {
            "knowledge/synced.md": {
                "relative_path": "knowledge/synced.md",
                "sha256": sha,
                "size_bytes": doc_path.stat().st_size,
                "modified": datetime.now().isoformat(),
                "sync_status": ai.SYNC_SYNCED,
                "remote_file_id": "file-existing",
                "remote_knowledge_id": "knowledge-001",
                "synced_sha256": sha,
                "synced_at": "2026-07-12T08:00:00+00:00",
            }
        }

        result = ai.ScanResult()
        doc = ai.collect_document(doc_path, knowledge_dir)
        result.documents.append(doc)
        ai.detect_changes(result, index)

        check("status is UNCHANGED", doc.status == ai.STATUS_UNCHANGED)
        check("sync_status is SYNCED (loaded from index)", doc.sync_status == ai.SYNC_SYNCED)
        check("remote_file_id preserved from index", doc.remote_file_id == "file-existing")
        check("needs_sync() is False", not ai.needs_sync(doc))
        check("new_count is 0", result.new_count == 0)
        check("unchanged_count is 1", result.unchanged_count == 1)


# ---------------------------------------------------------------------------
# 11. Atomic index write
# ---------------------------------------------------------------------------

def test_atomic_index_write() -> None:
    print("\n11. Atomic index write")

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / ".state" / "knowledge-index.json"
        doc = ai.DocumentInfo(
            path=Path(tmpdir) / "knowledge" / "test.md",
            relative_path=Path("knowledge/test.md"),
            filename="test.md", title="Test",
            size_bytes=100, modified=datetime.min,
            sha256="abc123",
            sync_status=ai.SYNC_SYNCED,
            synced_sha256="abc123",
            synced_at="2026-07-12T08:00:00+00:00",
            remote_file_id="file-abc",
            remote_knowledge_id="knowledge-001",
        )

        ai.save_index(index_path, [doc])

        check("index file created", index_path.exists())
        check("tmp file not left behind", not index_path.with_suffix(".tmp").exists())

        data = json.loads(index_path.read_text())
        check("version field is present", data.get("version") == ai.INDEX_VERSION)
        check("last_updated is present", "last_updated" in data)

        entry = data["documents"].get("knowledge/test.md")
        check("document entry written", entry is not None)
        check("sync_status persisted", entry.get("sync_status") == ai.SYNC_SYNCED)
        check("synced_sha256 persisted", entry.get("synced_sha256") == "abc123")
        check("remote_file_id persisted", entry.get("remote_file_id") == "file-abc")
        check("synced_at persisted", entry.get("synced_at") is not None)

        # Round-trip: load and verify
        reloaded = ai.load_index(index_path)
        check("round-trip: sync_status survives", reloaded["knowledge/test.md"]["sync_status"] == ai.SYNC_SYNCED)


# ---------------------------------------------------------------------------
# 12. needs_sync edge cases
# ---------------------------------------------------------------------------

def test_needs_sync_rules() -> None:
    print("\n12. needs_sync() rules")

    def make_doc(**kwargs) -> ai.DocumentInfo:
        defaults = dict(
            path=Path("/tmp/x.md"), relative_path=Path("knowledge/x.md"),
            filename="x.md", title=None, size_bytes=0, modified=datetime.min,
        )
        defaults.update(kwargs)
        return ai.DocumentInfo(**defaults)

    d = make_doc(status=ai.STATUS_NEW, sync_status=ai.SYNC_PENDING)
    check("NEW → needs_sync", ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_UNCHANGED, sync_status=ai.SYNC_SYNCED)
    check("UNCHANGED + SYNCED → no sync", not ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_UNCHANGED, sync_status=ai.SYNC_PENDING)
    check("UNCHANGED + PENDING → needs_sync", ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_UNCHANGED, sync_status=ai.SYNC_FAILED)
    check("UNCHANGED + FAILED → needs_sync (retry)", ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_MODIFIED, sync_status=ai.SYNC_SYNCED)
    check("MODIFIED + SYNCED → no sync (M2.3 scope)", not ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_MODIFIED, sync_status=ai.SYNC_PENDING)
    check("MODIFIED + PENDING → needs_sync", ai.needs_sync(d))

    d = make_doc(status=ai.STATUS_NEW, sync_status=ai.SYNC_PENDING, read_error="oops")
    check("read_error → no sync regardless of status", not ai.needs_sync(d))


# ---------------------------------------------------------------------------
# 13. find_knowledge_collection — response parsing
# ---------------------------------------------------------------------------

def test_knowledge_response_parsing() -> None:
    print("\n13. find_knowledge_collection() response parsing")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="Foundation",
    )
    collections = [
        {"id": "abc123", "name": "Foundation"},
        {"id": "def456", "name": "Networking"},
    ]

    # Paginated response (Open WebUI v0.10.2+)
    paginated = {"items": collections, "total": 2}
    with patch.object(ai, "http_get", return_value=paginated):
        kid, kname = ai.find_knowledge_collection(cfg, "token")
    check("paginated: returns correct id", kid == "abc123")
    check("paginated: returns correct name", kname == "Foundation")

    # Legacy direct list
    with patch.object(ai, "http_get", return_value=collections):
        kid, kname = ai.find_knowledge_collection(cfg, "token")
    check("legacy list: returns correct id", kid == "abc123")
    check("legacy list: returns correct name", kname == "Foundation")

    # Dict without 'items' key
    raised = False
    msg = ""
    with patch.object(ai, "http_get", return_value={"total": 0}):
        try:
            ai.find_knowledge_collection(cfg, "token")
        except RuntimeError as exc:
            raised = True
            msg = str(exc)
    check("dict without 'items': raises RuntimeError", raised)
    check("dict without 'items': message mentions 'items'", "items" in msg)

    # 'items' present but not a list
    raised = False
    msg = ""
    with patch.object(ai, "http_get", return_value={"items": "not-a-list", "total": 0}):
        try:
            ai.find_knowledge_collection(cfg, "token")
        except RuntimeError as exc:
            raised = True
            msg = str(exc)
    check("items not list: raises RuntimeError", raised)
    check("items not list: message mentions type", "str" in msg)


# ---------------------------------------------------------------------------
# 14. M2.4 — Multi-project
# ---------------------------------------------------------------------------

def test_project_not_found() -> None:
    print("\n14. Multi-project: progetto inesistente")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # knowledge/ABRAZO/ does not exist

        with (
            patch.object(ai, "find_project_root", return_value=root),
            patch("sys.argv", ["atlas-import", "scan", "ABRAZO"]),
        ):
            rc = ai.main()

        check("returns exit code 1 for non-existent project", rc == 1)


def test_collection_already_exists() -> None:
    print("\n   Collection già esistente (find_or_create non chiama create)")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="ABRAZO",
    )
    collections = [{"id": "id-abrazo", "name": "ABRAZO"}]
    create_called = []

    with (
        patch.object(ai, "http_get", return_value=collections),
        patch.object(
            ai, "create_knowledge_collection",
            side_effect=lambda *a, **kw: create_called.append(1) or ("new-id", "ABRAZO"),
        ),
    ):
        kid, kname = ai.find_or_create_knowledge_collection(cfg, "token")

    check("returns existing id", kid == "id-abrazo")
    check("returns existing name", kname == "ABRAZO")
    check("create_knowledge_collection not called", not create_called)


def test_collection_auto_created() -> None:
    print("\n   Collection da creare (find_or_create chiama create)")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x",
        knowledge_name="NOEMA",
    )
    existing = [{"id": "other-id", "name": "OTHER"}]

    with (
        patch.object(ai, "http_get", return_value=existing),
        patch.object(ai, "http_post_json", return_value={"id": "noema-new-id", "name": "NOEMA"}),
    ):
        kid, kname = ai.find_or_create_knowledge_collection(cfg, "token")

    check("auto-created: id returned", kid == "noema-new-id")
    check("auto-created: name returned", kname == "NOEMA")


def test_independent_state() -> None:
    print("\n   Stato indipendente per progetto")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        abrazo_dir, abrazo_idx = ai.resolve_project_paths(root, "ABRAZO")
        noema_dir, noema_idx = ai.resolve_project_paths(root, "NOEMA")

        check("ABRAZO knowledge dir ends with knowledge/ABRAZO",
              str(abrazo_dir).endswith("knowledge/ABRAZO"))
        check("NOEMA knowledge dir ends with knowledge/NOEMA",
              str(noema_dir).endswith("knowledge/NOEMA"))
        check("ABRAZO index ends with .state/ABRAZO.json",
              str(abrazo_idx).endswith(".state/ABRAZO.json"))
        check("NOEMA index ends with .state/NOEMA.json",
              str(noema_idx).endswith(".state/NOEMA.json"))
        check("index paths are different", abrazo_idx != noema_idx)

        # Write state only for ABRAZO
        abrazo_dir.mkdir(parents=True)
        doc_path = abrazo_dir / "test.md"
        doc_path.write_text("# Test\n\nContent.", encoding="utf-8")
        doc = ai.DocumentInfo(
            path=doc_path,
            relative_path=Path("ABRAZO/test.md"),
            filename="test.md", title="Test",
            size_bytes=doc_path.stat().st_size,
            modified=datetime.min, sha256="abc",
            sync_status=ai.SYNC_SYNCED,
        )
        ai.save_index(abrazo_idx, [doc])

        check("ABRAZO index created", abrazo_idx.exists())
        check("NOEMA index not created", not noema_idx.exists())
        check("NOEMA state loads as empty dict", ai.load_index(noema_idx) == {})


def test_two_consecutive_projects() -> None:
    print("\n   Sincronizzazione di due progetti consecutivi")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Set up independent project dirs
        for proj, fname in [("ABRAZO", "abrazo-doc.md"), ("NOEMA", "noema-doc.md")]:
            proj_dir = root / "knowledge" / proj
            proj_dir.mkdir(parents=True)
            (proj_dir / fname).write_text(f"# {proj}\n\nContent.", encoding="utf-8")

        # Scan + save state for each project independently
        for proj in ("ABRAZO", "NOEMA"):
            knowledge_dir, index_path = ai.resolve_project_paths(root, proj)
            result = ai.scan_knowledge_dir(knowledge_dir)
            ai.detect_changes(result, ai.load_index(index_path))
            ai.save_index(index_path, result.documents)

        _, abrazo_idx = ai.resolve_project_paths(root, "ABRAZO")
        _, noema_idx = ai.resolve_project_paths(root, "NOEMA")

        abrazo_state = ai.load_index(abrazo_idx)
        noema_state = ai.load_index(noema_idx)

        check("ABRAZO state has exactly 1 document", len(abrazo_state) == 1)
        check("NOEMA state has exactly 1 document", len(noema_state) == 1)
        check("ABRAZO state contains ABRAZO doc",
              any("abrazo-doc" in k for k in abrazo_state))
        check("NOEMA state contains NOEMA doc",
              any("noema-doc" in k for k in noema_state))
        check("ABRAZO state does not contain NOEMA doc",
              not any("noema-doc" in k for k in abrazo_state))
        check("NOEMA state does not contain ABRAZO doc",
              not any("abrazo-doc" in k for k in noema_state))


# ---------------------------------------------------------------------------
# 15. M2.4.1 — Hardening: abort su errori fatali + validazione PROJECT
# ---------------------------------------------------------------------------

def _make_new_doc(tmp_path: Path) -> ai.DocumentInfo:
    """Helper: DocumentInfo with STATUS_NEW backed by a real temp file."""
    tmp_path.write_text("# Test\n\nContent.", encoding="utf-8")
    return ai.DocumentInfo(
        path=tmp_path,
        relative_path=Path("ABRAZO") / tmp_path.name,
        filename=tmp_path.name,
        title="Test",
        size_bytes=tmp_path.stat().st_size,
        modified=datetime.min,
        sha256="abc",
        status=ai.STATUS_NEW,
    )


def test_abort_on_auth_failure() -> None:
    print("\n15. M2.4.1 — Abort su errori fatali")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x", knowledge_name="ABRAZO"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "ABRAZO.json"
        doc = _make_new_doc(Path(tmpdir) / "doc.md")
        result = ai.ScanResult(documents=[doc], new_count=1)

        # HTTPError 401
        def raise_401(*a, **kw):
            raise urllib.error.HTTPError(cfg.url, 401, "Unauthorized", {}, None)

        with patch.object(ai, "http_post_json", side_effect=raise_401):
            stats = ai.run_sync(cfg, result, index_path)

        check("auth HTTPError → stats.aborted", stats.aborted)
        check("auth HTTPError → uploaded == 0", stats.uploaded == 0)

        # URLError (rete irraggiungibile)
        doc.sync_status = ai.SYNC_PENDING
        doc.status = ai.STATUS_NEW

        def raise_url(*a, **kw):
            raise urllib.error.URLError("unreachable")

        with patch.object(ai, "http_post_json", side_effect=raise_url):
            stats2 = ai.run_sync(cfg, result, index_path)

        check("auth URLError → stats.aborted", stats2.aborted)

        # RuntimeError (no token in response)
        doc.sync_status = ai.SYNC_PENDING
        doc.status = ai.STATUS_NEW

        with patch.object(ai, "http_post_json", return_value={"user": "x"}):
            stats3 = ai.run_sync(cfg, result, index_path)

        check("auth RuntimeError (no token) → stats.aborted", stats3.aborted)


def test_abort_on_collection_lookup_failure() -> None:
    print("\n   Abort: collection lookup fallito")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x", knowledge_name="ABRAZO"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "ABRAZO.json"
        doc = _make_new_doc(Path(tmpdir) / "doc.md")
        result = ai.ScanResult(documents=[doc], new_count=1)

        # auth OK, GET /knowledge/ → URLError
        with (
            patch.object(ai, "http_post_json", return_value={"token": "tok"}),
            patch.object(ai, "http_get",
                         side_effect=urllib.error.URLError("connection refused")),
        ):
            stats = ai.run_sync(cfg, result, index_path)

        check("collection URLError → stats.aborted", stats.aborted)
        check("collection URLError → uploaded == 0", stats.uploaded == 0)

        # auth OK, GET /knowledge/ → malformed dict (no items)
        doc.sync_status = ai.SYNC_PENDING
        doc.status = ai.STATUS_NEW

        with (
            patch.object(ai, "http_post_json", return_value={"token": "tok"}),
            patch.object(ai, "http_get", return_value={"total": 0}),
        ):
            stats2 = ai.run_sync(cfg, result, index_path)

        check("collection bad format → stats.aborted", stats2.aborted)


def test_abort_on_collection_create_failure() -> None:
    print("\n   Abort: collection creation fallita")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x", knowledge_name="NOEMA"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "NOEMA.json"
        doc = _make_new_doc(Path(tmpdir) / "doc.md")
        result = ai.ScanResult(documents=[doc], new_count=1)

        # auth OK → find returns empty list → create → 500
        create_error = urllib.error.HTTPError(
            cfg.url, 500, "Internal Server Error", {}, None
        )

        with (
            patch.object(ai, "http_post_json",
                         side_effect=[{"token": "tok"}, create_error]),
            patch.object(ai, "http_get", return_value=[]),
        ):
            stats = ai.run_sync(cfg, result, index_path)

        check("create HTTPError 500 → stats.aborted", stats.aborted)
        check("create HTTPError 500 → uploaded == 0", stats.uploaded == 0)

        # auth OK → find returns empty → create returns no id
        doc.sync_status = ai.SYNC_PENDING
        doc.status = ai.STATUS_NEW

        with (
            patch.object(ai, "http_post_json",
                         side_effect=[{"token": "tok"}, {"name": "NOEMA"}]),
            patch.object(ai, "http_get", return_value=[]),
        ):
            stats2 = ai.run_sync(cfg, result, index_path)

        check("create missing id → stats.aborted", stats2.aborted)


def test_project_name_validation() -> None:
    print("\n   Validazione nome PROJECT")

    valid = ["ABRAZO", "NOEMA", "ATLAS", "A", "Z9", "MY-PROJECT", "MY_PROJECT", "A1B"]
    for name in valid:
        check(f"valido: '{name}'", ai.validate_project_name(name) is None)

    invalid = [
        ("",              "vuoto"),
        ("../SECRETS",    "path traversal con ../"),
        ("ABRAZO/sub",    "slash"),
        ("MY PROJECT",    "spazio"),
        ("abrazo",        "lowercase"),
        ("_ABRAZO",       "inizia con underscore"),
        ("-ABRAZO",       "inizia con trattino"),
        ("A" * 65,        "troppo lungo (65 car.)"),
        ("ABRAZO.",       "punto"),
        ("ABRAZO\n",      "newline"),
    ]
    for name, desc in invalid:
        check(
            f"non valido: {desc!r}",
            ai.validate_project_name(name) is not None,
        )


def test_main_rejects_invalid_project() -> None:
    print("\n   main() rifiuta PROJECT non valido → exit 1")

    for bad in ("../secrets", "abrazo", "MY PROJECT", ""):
        with patch("sys.argv", ["atlas-import", "scan", bad] if bad else ["atlas-import", "scan", bad]):
            # argparse requires a non-empty positional; empty string is tricky
            if not bad:
                # argparse would print usage and exit(2) for truly missing arg
                # test validate_project_name directly instead
                check("vuoto: validate_project_name restituisce errore",
                      ai.validate_project_name(bad) is not None)
                continue
            rc = ai.main()
        check(f"main() → 1 per PROJECT='{bad}'", rc == 1)


# ---------------------------------------------------------------------------
# 16. M2.4.1 — ValueError da risposta non JSON
# ---------------------------------------------------------------------------

def test_abort_on_auth_non_json() -> None:
    print("\n16. M2.4.1 — ValueError: risposta non JSON")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x", knowledge_name="ABRAZO"
    )
    collection_called = []

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "ABRAZO.json"
        doc = _make_new_doc(Path(tmpdir) / "doc.md")
        result = ai.ScanResult(documents=[doc], new_count=1)

        def fake_http_get_spy(url, token):
            collection_called.append(url)
            return []

        with (
            patch.object(ai, "http_post_json",
                         side_effect=ValueError("Non-JSON response from signin: b'<html>'")),
            patch.object(ai, "http_get", side_effect=fake_http_get_spy),
        ):
            stats = ai.run_sync(cfg, result, index_path)

        check("auth ValueError → stats.aborted", stats.aborted)
        check("auth ValueError → uploaded == 0", stats.uploaded == 0)
        check("auth ValueError → collection lookup non eseguito", not collection_called)


def test_abort_on_collection_non_json() -> None:
    print("\n   ValueError durante lookup collection")

    cfg = ai.SyncConfig(
        url="http://example.com", email="x", password="x", knowledge_name="ABRAZO"
    )
    upload_called = []

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "ABRAZO.json"
        doc = _make_new_doc(Path(tmpdir) / "doc.md")
        result = ai.ScanResult(documents=[doc], new_count=1)

        def fake_upload_spy(*a, **kw):
            upload_called.append(1)
            return {"id": "file-xyz"}

        with (
            patch.object(ai, "http_post_json", return_value={"token": "tok"}),
            patch.object(ai, "http_get",
                         side_effect=ValueError("Non-JSON response from /knowledge/: b'<html>'")),
            patch.object(ai, "http_post_multipart", side_effect=fake_upload_spy),
        ):
            stats = ai.run_sync(cfg, result, index_path)

        check("collection ValueError → stats.aborted", stats.aborted)
        check("collection ValueError → uploaded == 0", stats.uploaded == 0)
        check("collection ValueError → nessun upload documento", not upload_called)


def test_main_exit1_on_non_json() -> None:
    print("\n   main() → exit 1 su ValueError")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        proj_dir = root / "knowledge" / "ABRAZO"
        proj_dir.mkdir(parents=True)
        (proj_dir / "doc.md").write_text("# Doc\n\nContent.", encoding="utf-8")

        env = {
            "ATLAS_OPENWEBUI_URL": "http://example.com",
            "ATLAS_OPENWEBUI_EMAIL": "x@x.com",
            "ATLAS_OPENWEBUI_PASSWORD": "secret",
        }

        # ValueError su autenticazione
        with (
            patch.object(ai, "find_project_root", return_value=root),
            patch("sys.argv", ["atlas-import", "sync", "ABRAZO"]),
            patch.dict(os.environ, env),
            patch.object(ai, "http_post_json",
                         side_effect=ValueError("Non-JSON response: b'<html>'")),
        ):
            rc = ai.main()
        check("main() → 1 su auth ValueError", rc == 1)

        # ValueError su collection lookup
        with (
            patch.object(ai, "find_project_root", return_value=root),
            patch("sys.argv", ["atlas-import", "sync", "ABRAZO"]),
            patch.dict(os.environ, env),
            patch.object(ai, "http_post_json", return_value={"token": "tok"}),
            patch.object(ai, "http_get",
                         side_effect=ValueError("Non-JSON response: b'<html>'")),
        ):
            rc2 = ai.main()
        check("main() → 1 su collection ValueError", rc2 == 1)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("Atlas Import — Test Suite (M2.3 / M2.4 / M2.4.1)")
    print("=" * 60)

    test_missing_env_vars()
    test_knowledge_not_found()
    test_knowledge_found()
    test_auth_failed()
    test_auth_no_token()
    test_upload_failed()
    test_processing_failed()
    test_processing_timeout()
    test_association_failed()
    test_full_success()
    test_retry_failed_pending()
    test_no_upload_for_synced()
    test_atomic_index_write()
    test_needs_sync_rules()
    test_knowledge_response_parsing()
    test_project_not_found()
    test_collection_already_exists()
    test_collection_auto_created()
    test_independent_state()
    test_two_consecutive_projects()
    test_abort_on_auth_failure()
    test_abort_on_collection_lookup_failure()
    test_abort_on_collection_create_failure()
    test_project_name_validation()
    test_main_rejects_invalid_project()
    test_abort_on_auth_non_json()
    test_abort_on_collection_non_json()
    test_main_exit1_on_non_json()

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total = len(_results)

    print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  —  {FAIL}: {failed} failed")
        for name, ok, detail in _results:
            if not ok:
                print(f"    • {name}" + (f": {detail}" if detail else ""))
    else:
        print(f"  —  all {PASS}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
