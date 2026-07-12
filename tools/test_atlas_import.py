#!/usr/bin/env python3
"""
Test suite for atlas-import.py — M2.3

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

    env_backup = {k: os.environ.pop(k, None) for k in [
        "ATLAS_OPENWEBUI_URL", "ATLAS_OPENWEBUI_EMAIL",
        "ATLAS_OPENWEBUI_PASSWORD", "ATLAS_KNOWLEDGE_NAME",
    ]}
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
        os.environ["ATLAS_OPENWEBUI_PASSWORD"] = "secret"
        # ATLAS_KNOWLEDGE_NAME still missing
        try:
            ai.load_sync_config()
            raised = False
        except EnvironmentError as exc:
            raised = True
            msg = str(exc)
        check("raises EnvironmentError for single missing var", raised)
        check("message names the missing var", "ATLAS_KNOWLEDGE_NAME" in msg)

        # All present
        os.environ["ATLAS_KNOWLEDGE_NAME"] = "Foundation"
        cfg = ai.load_sync_config()
        check("returns SyncConfig when all vars present", cfg.url == "http://example.com")
        check("strips trailing slash from URL", not cfg.url.endswith("/"))
        check("default process_timeout is 300", cfg.process_timeout == 300)

    finally:
        # Restore
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        for k in ["ATLAS_OPENWEBUI_URL", "ATLAS_OPENWEBUI_EMAIL",
                   "ATLAS_OPENWEBUI_PASSWORD", "ATLAS_KNOWLEDGE_NAME"]:
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
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("Atlas Import — Test Suite (M2.3)")
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
