#!/usr/bin/env python3
"""
Atlas Knowledge Importer

M2.1.1 — Baseline scanner: discovers Markdown documents in knowledge/<PROJECT>/
          and reports their metadata.

M2.1.2 — Change detection: SHA256-based comparison against a persistent
          index. Classifies documents as NEW, MODIFIED, UNCHANGED, DELETED.

M2.3   — Sync: uploads NEW (and retries PENDING/FAILED) documents to an
          Open WebUI Knowledge Collection. MODIFIED and DELETED remote
          handling deferred to future milestones.

M2.4   — Multi-project: each project has its own knowledge/<PROJECT>/
          subdirectory and .state/<PROJECT>.json index. The Knowledge
          Collection is auto-created if not found.
          Usage: atlas-import.py {scan,sync,dry-run} <PROJECT>

M2.4.1 — Hardening: PROJECT name validated against ^[A-Z0-9][A-Z0-9_-]{0,63}$;
          fatal errors (auth, network, collection lookup/create) set
          SyncStats.aborted=True and produce exit code 1.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWLEDGE_DIR = "knowledge"
STATE_DIR = ".state"
INDEX_VERSION = 2
PROJECT_NAME_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,63}\Z")
SEPARATOR = "-" * 50
HTTP_TIMEOUT = 30       # seconds per individual HTTP call
POLL_INTERVAL = 2       # seconds between processing status polls

# Local change status
STATUS_NEW = "NEW"
STATUS_MODIFIED = "MODIFIED"
STATUS_UNCHANGED = "UNCHANGED"
STATUS_DELETED = "DELETED"
STATUS_UNKNOWN = "UNKNOWN"

# Remote sync status
SYNC_PENDING = "PENDING"
SYNC_SYNCED = "SYNCED"
SYNC_FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DocumentInfo:
    """Metadata for a single Markdown document, including sync state."""

    path: Path
    relative_path: Path
    filename: str
    title: Optional[str]
    size_bytes: int
    modified: datetime
    read_error: Optional[str] = None
    sha256: Optional[str] = None
    status: str = STATUS_UNKNOWN
    # Sync fields — loaded from index for known documents
    sync_status: str = SYNC_PENDING
    remote_file_id: Optional[str] = None
    remote_knowledge_id: Optional[str] = None
    synced_sha256: Optional[str] = None
    synced_at: Optional[str] = None


@dataclass
class ScanResult:
    """Aggregate result of a knowledge directory scan."""

    documents: list[DocumentInfo] = field(default_factory=list)
    folder_count: int = 0
    error_count: int = 0
    deleted_paths: list[str] = field(default_factory=list)
    new_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0
    deleted_count: int = 0


@dataclass
class SyncConfig:
    """Runtime configuration for Open WebUI synchronization."""

    url: str
    email: str
    password: str
    knowledge_name: str = ""   # set from CLI <project> arg after load_sync_config()
    process_timeout: int = 300


@dataclass
class SyncStats:
    """Counters accumulated during a sync run."""

    uploaded: int = 0
    failed: int = 0
    skipped: int = 0
    aborted: bool = False   # True when a fatal error stopped the run early


# ---------------------------------------------------------------------------
# M2.1.1 — Core scanning
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    """Return the project root directory (parent of the tools/ directory)."""
    return Path(__file__).resolve().parent.parent


def resolve_project_paths(project_root: Path, project: str) -> tuple[Path, Path]:
    """
    Return (knowledge_dir, index_path) for the given project name.

    knowledge_dir = project_root / knowledge / <project>
    index_path    = project_root / .state   / <project>.json
    """
    knowledge_dir = project_root / KNOWLEDGE_DIR / project
    index_path = project_root / STATE_DIR / f"{project}.json"
    return knowledge_dir, index_path


def validate_project_name(project: str) -> Optional[str]:
    """
    Return None if the project name is valid, or an error message if not.

    Accepted pattern: ^[A-Z0-9][A-Z0-9_-]{0,63}\Z
    Rejects empty strings, path separators, dots, spaces, lowercase, and
    trailing newlines (\Z anchors at the absolute end of the string).
    """
    if not project:
        return "PROJECT must not be empty."
    if not PROJECT_NAME_RE.match(project):
        return (
            f"Invalid PROJECT name '{project}'. "
            "Must match ^[A-Z0-9][A-Z0-9_-]{0,63}$ "
            "(uppercase letters/digits, underscores, hyphens; "
            "no path separators, dots, spaces, or lowercase)."
        )
    return None


def extract_title(file_path: Path) -> Optional[str]:
    """
    Extract the first H1 heading from a Markdown file.

    Returns the text without the leading '# ', or None if not found.
    Never raises: read failures return None.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
        return None
    except OSError:
        return None


def format_size(size_bytes: int) -> str:
    """Return a human-readable file size string (B, KB, or MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def collect_document(file_path: Path, knowledge_dir: Path) -> DocumentInfo:
    """
    Collect metadata for a single Markdown file, including SHA256.

    On OS error, returns a DocumentInfo with zeroed numeric fields
    and read_error set to the exception message.
    """
    try:
        stat = file_path.stat()
        return DocumentInfo(
            path=file_path,
            relative_path=file_path.relative_to(knowledge_dir.parent),
            filename=file_path.name,
            title=extract_title(file_path),
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            sha256=compute_sha256(file_path),
        )
    except OSError as exc:
        return DocumentInfo(
            path=file_path,
            relative_path=file_path.relative_to(knowledge_dir.parent),
            filename=file_path.name,
            title=None,
            size_bytes=0,
            modified=datetime.min,
            read_error=str(exc),
        )


def scan_knowledge_dir(knowledge_dir: Path) -> ScanResult:
    """
    Recursively scan knowledge_dir for Markdown files (.md).

    Files are collected in sorted order (alphabetical, case-sensitive).
    """
    result = ScanResult()
    folders_seen: set[Path] = set()

    for file_path in sorted(knowledge_dir.rglob("*.md")):
        if not file_path.is_file():
            continue
        folders_seen.add(file_path.parent)
        doc = collect_document(file_path, knowledge_dir)
        if doc.read_error:
            result.error_count += 1
        result.documents.append(doc)

    result.folder_count = len(folders_seen)
    return result


def print_document_block(doc: DocumentInfo) -> None:
    """Print the verbose metadata block for a single document."""
    print(doc.filename)
    print()
    if doc.read_error:
        print("Error:")
        print(doc.read_error)
        print()
        return
    print("Path:")
    print(doc.relative_path)
    print()
    print("Title:")
    print(doc.title if doc.title else "(no title found)")
    print()
    print("Size:")
    print(format_size(doc.size_bytes))
    print()
    print("Modified:")
    print(doc.modified.strftime("%Y-%m-%d"))
    print()


# ---------------------------------------------------------------------------
# M2.1.2 — Change detection
# ---------------------------------------------------------------------------


def compute_sha256(file_path: Path) -> Optional[str]:
    """
    Compute the SHA256 digest of a file in 64 KB binary chunks.

    Returns the lowercase hex digest, or None if the file cannot be read.
    """
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def load_index(index_path: Path) -> dict[str, dict]:
    """
    Load the knowledge index from disk.

    Returns a dict keyed by relative_path string.
    Returns {} on missing file, empty file, or JSON parse error.
    """
    if not index_path.exists():
        return {}
    try:
        content = index_path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        data = json.loads(content)
        return data.get("documents", {})
    except (OSError, json.JSONDecodeError):
        return {}


def save_index(index_path: Path, documents: list[DocumentInfo]) -> None:
    """
    Atomically persist the current scan and sync state to disk.

    Writes to a sibling .tmp file first, then replaces the target
    with os.replace() so the index is never left in a partial state.
    Only documents without read errors are written.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)

    entries: dict[str, dict] = {}
    for doc in documents:
        if doc.read_error:
            continue
        key = str(doc.relative_path)
        entries[key] = {
            "relative_path": str(doc.relative_path),
            "sha256": doc.sha256,
            "size_bytes": doc.size_bytes,
            "modified": doc.modified.isoformat(),
            "sync_status": doc.sync_status,
            "remote_file_id": doc.remote_file_id,
            "remote_knowledge_id": doc.remote_knowledge_id,
            "synced_sha256": doc.synced_sha256,
            "synced_at": doc.synced_at,
        }

    payload = {
        "version": INDEX_VERSION,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "documents": entries,
    }
    content = json.dumps(payload, indent=2, ensure_ascii=False)

    tmp_path = index_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, index_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def detect_changes(result: ScanResult, index: dict[str, dict]) -> None:
    """
    Classify each document against the loaded index.

    Sets doc.status (NEW / MODIFIED / UNCHANGED) and loads existing
    sync state from the index for all documents already present.
    Populates result.deleted_paths and increments counters.
    """
    current_keys: set[str] = set()

    for doc in result.documents:
        if doc.read_error:
            continue

        key = str(doc.relative_path)
        current_keys.add(key)

        if key not in index:
            doc.status = STATUS_NEW
            doc.sync_status = SYNC_PENDING
            result.new_count += 1
        else:
            entry = index[key]
            # Load sync state for all known documents
            doc.sync_status = entry.get("sync_status", SYNC_PENDING)
            doc.remote_file_id = entry.get("remote_file_id")
            doc.remote_knowledge_id = entry.get("remote_knowledge_id")
            doc.synced_sha256 = entry.get("synced_sha256")
            doc.synced_at = entry.get("synced_at")

            if doc.sha256 != entry.get("sha256"):
                doc.status = STATUS_MODIFIED
                result.modified_count += 1
            else:
                doc.status = STATUS_UNCHANGED
                result.unchanged_count += 1

    for key in index:
        if key not in current_keys:
            result.deleted_paths.append(key)
            result.deleted_count += 1


def needs_sync(doc: DocumentInfo) -> bool:
    """
    Return True if this document should be uploaded in a sync run.

    A document needs sync when it is NEW, or when a previous sync
    attempt left it in PENDING or FAILED state.
    MODIFIED documents retain their existing sync_status; re-upload
    of modified content is implemented in a future milestone.
    """
    if doc.read_error:
        return False
    if doc.status == STATUS_NEW:
        return True
    return doc.sync_status in (SYNC_PENDING, SYNC_FAILED)


# ---------------------------------------------------------------------------
# M2.3 — Configuration
# ---------------------------------------------------------------------------


def load_sync_config() -> SyncConfig:
    """
    Build SyncConfig from environment variables.

    Required: ATLAS_OPENWEBUI_URL, ATLAS_OPENWEBUI_EMAIL,
              ATLAS_OPENWEBUI_PASSWORD.
    Optional: ATLAS_PROCESS_TIMEOUT (default 300 seconds).

    The knowledge_name field is left empty and must be set by the caller
    from the CLI <project> argument.

    Raises EnvironmentError listing all missing variables.
    """
    required = {
        "ATLAS_OPENWEBUI_URL": "Open WebUI base URL",
        "ATLAS_OPENWEBUI_EMAIL": "authentication email",
        "ATLAS_OPENWEBUI_PASSWORD": "authentication password",
    }
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        lines = "\n".join(f"  {k}: {required[k]}" for k in missing)
        raise EnvironmentError(f"Missing required environment variables:\n{lines}")

    return SyncConfig(
        url=os.environ["ATLAS_OPENWEBUI_URL"].rstrip("/"),
        email=os.environ["ATLAS_OPENWEBUI_EMAIL"],
        password=os.environ["ATLAS_OPENWEBUI_PASSWORD"],
        process_timeout=int(os.environ.get("ATLAS_PROCESS_TIMEOUT", "300")),
    )


# ---------------------------------------------------------------------------
# M2.3 — HTTP utilities
# ---------------------------------------------------------------------------


def http_get(url: str, token: str) -> object:
    """
    Authenticated GET request. Returns parsed JSON.

    Raises urllib.error.HTTPError on 4xx/5xx.
    Raises ValueError on non-JSON response body.
    Raises urllib.error.URLError on network failure.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Non-JSON response from {url}: {raw[:200]!r}") from exc


def http_post_json(url: str, payload: dict, token: Optional[str] = None) -> dict:
    """
    POST a JSON body. Returns parsed JSON response.

    Raises urllib.error.HTTPError on 4xx/5xx.
    Raises ValueError on non-JSON response body.
    Raises urllib.error.URLError on network failure.
    """
    body = json.dumps(payload).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Non-JSON response from {url}: {raw[:200]!r}") from exc


def build_multipart(
    file_path: Path, extra_fields: dict[str, str]
) -> tuple[bytes, str]:
    """
    Build a multipart/form-data body with text fields and one file.

    Returns (body_bytes, Content-Type header value with boundary).
    The boundary is a random UUID hex string; safe for text files.
    """
    boundary = uuid.uuid4().hex
    CRLF = b"\r\n"
    parts: list[bytes] = []

    for name, value in extra_fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n'
                "\r\n"
                f"{value}\r\n"
            ).encode("utf-8")
        )

    with open(file_path, "rb") as f:
        file_data = f.read()

    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            "Content-Type: text/markdown; charset=utf-8\r\n"
            "\r\n"
        ).encode("utf-8")
        + file_data
        + CRLF
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_post_multipart(
    url: str, token: str, file_path: Path, extra_fields: dict[str, str]
) -> dict:
    """
    POST a multipart/form-data request with text fields and a file.

    Raises urllib.error.HTTPError on 4xx/5xx.
    Raises ValueError on non-JSON response.
    Raises urllib.error.URLError on network failure.
    """
    body, content_type = build_multipart(file_path, extra_fields)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Non-JSON response from {url}: {raw[:200]!r}") from exc


# ---------------------------------------------------------------------------
# M2.3 / M2.4 — Open WebUI API
# ---------------------------------------------------------------------------


def authenticate(config: SyncConfig) -> str:
    """
    Authenticate against Open WebUI and return the bearer token.

    The password is sent over the network and then discarded; it is
    never logged or stored to disk.
    Raises RuntimeError if the response contains no token field.
    Raises urllib.error.HTTPError on authentication failure (401 etc.).
    """
    url = f"{config.url}/api/v1/auths/signin"
    data = http_post_json(url, {"email": config.email, "password": config.password})
    token = data.get("token")
    if not token:
        raise RuntimeError(
            "Authentication response contained no 'token' field."
        )
    return token


def _parse_collections_response(url: str, data: object) -> list:
    """
    Extract the list of collections from an API response.

    Accepts both a direct list (legacy) and a paginated dict
    {"items": [...], "total": N} (Open WebUI v0.10.2+).
    Raises RuntimeError on unexpected formats.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get("items")
        if not isinstance(items, list):
            raise RuntimeError(
                f"Unexpected response from {url}: "
                f"'items' is missing or not a list (got {type(items).__name__})."
            )
        return items
    raise RuntimeError(
        f"Unexpected response from {url}: "
        f"expected list or dict, got {type(data).__name__}."
    )


def find_knowledge_collection(
    config: SyncConfig, token: str
) -> tuple[str, str]:
    """
    Find a Knowledge Collection by exact name match.

    Returns (knowledge_id, knowledge_name).
    Raises RuntimeError if no collection matches config.knowledge_name
    or if the API returns an unexpected format.
    """
    url = f"{config.url}/api/v1/knowledge/"
    collections = _parse_collections_response(url, http_get(url, token))
    for col in collections:
        if col.get("name") == config.knowledge_name:
            return col["id"], col["name"]
    available = [c.get("name", "(unnamed)") for c in collections]
    raise RuntimeError(
        f"Knowledge Collection '{config.knowledge_name}' not found.\n"
        f"Available: {available}"
    )


def create_knowledge_collection(
    config: SyncConfig, token: str
) -> tuple[str, str]:
    """
    Create a new Knowledge Collection in Open WebUI.

    Returns (knowledge_id, knowledge_name).
    Raises RuntimeError if the response is missing required fields.
    """
    url = f"{config.url}/api/v1/knowledge/create"
    data = http_post_json(
        url,
        {"name": config.knowledge_name, "description": ""},
        token=token,
    )
    col_id = data.get("id")
    col_name = data.get("name")
    if not col_id or not col_name:
        raise RuntimeError(
            f"Create knowledge collection response missing 'id' or 'name'. "
            f"Response: {data}"
        )
    return col_id, col_name


def find_or_create_knowledge_collection(
    config: SyncConfig, token: str
) -> tuple[str, str]:
    """
    Find a Knowledge Collection by name; create it automatically if absent.

    Returns (knowledge_id, knowledge_name).
    Raises RuntimeError on API format errors or creation failure.
    """
    url = f"{config.url}/api/v1/knowledge/"
    collections = _parse_collections_response(url, http_get(url, token))
    for col in collections:
        if col.get("name") == config.knowledge_name:
            return col["id"], col["name"]
    print(f"  Collection '{config.knowledge_name}' not found — creating ...")
    return create_knowledge_collection(config, token)


def upload_file(config: SyncConfig, token: str, file_path: Path) -> str:
    """
    Upload a file to Open WebUI via multipart POST.

    Returns the file_id from the response.
    Raises RuntimeError if the response contains no 'id' field.
    """
    url = f"{config.url}/api/v1/files/"
    data = http_post_multipart(
        url, token, file_path,
        {"process": "true", "process_in_background": "true"},
    )
    file_id = data.get("id")
    if not file_id:
        raise RuntimeError(
            f"Upload response missing 'id' field. Response: {data}"
        )
    return file_id


def wait_for_processing(
    config: SyncConfig, token: str, file_id: str
) -> None:
    """
    Poll the processing status endpoint until completed, failed, or timeout.

    Polls every POLL_INTERVAL seconds up to config.process_timeout seconds.
    Raises RuntimeError on failure status or timeout.
    """
    url = f"{config.url}/api/v1/files/{file_id}/process/status"
    deadline = time.monotonic() + config.process_timeout

    while time.monotonic() < deadline:
        data = http_get(url, token)
        status = data.get("status", "")

        if status == "completed":
            return
        if status == "failed":
            detail = data.get("detail", "no detail provided")
            raise RuntimeError(
                f"Processing failed for {file_id}: {detail}"
            )
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(
        f"Processing timed out after {config.process_timeout}s for {file_id}."
    )


def add_file_to_knowledge(
    config: SyncConfig, token: str, knowledge_id: str, file_id: str
) -> None:
    """
    Associate an uploaded file with the target Knowledge Collection.

    Raises urllib.error.HTTPError on 4xx/5xx.
    """
    url = f"{config.url}/api/v1/knowledge/{knowledge_id}/file/add"
    http_post_json(url, {"file_id": file_id}, token=token)


# ---------------------------------------------------------------------------
# M2.3 — Sync orchestration
# ---------------------------------------------------------------------------


def sync_document(
    config: SyncConfig,
    token: str,
    knowledge_id: str,
    doc: DocumentInfo,
) -> bool:
    """
    Execute the three-step sync pipeline for a single document:
      1. Upload file  →  obtain file_id
      2. Wait for processing to reach 'completed'
      3. Associate file_id with the Knowledge Collection

    Mutates doc in place: sets sync_status, remote_file_id,
    remote_knowledge_id, synced_sha256, synced_at on success.
    Sets sync_status = SYNC_FAILED on any error.

    sync_status is written as SYNCED only after all three steps
    succeed; a partial failure leaves the document as FAILED so
    the next run can retry.

    Returns True on success, False on failure.
    """
    print(f"  {doc.filename}", end=" ... ", flush=True)

    try:
        file_id = upload_file(config, token, doc.path)
    except Exception as exc:
        doc.sync_status = SYNC_FAILED
        print(f"FAILED (upload: {exc})")
        return False

    print(f"uploaded [{file_id[:8]}]", end=" ", flush=True)

    try:
        wait_for_processing(config, token, file_id)
    except Exception as exc:
        doc.sync_status = SYNC_FAILED
        print(f"FAILED (processing: {exc})")
        return False

    print("processed", end=" ", flush=True)

    try:
        add_file_to_knowledge(config, token, knowledge_id, file_id)
    except Exception as exc:
        doc.sync_status = SYNC_FAILED
        print(f"FAILED (association: {exc})")
        return False

    # All three steps succeeded — only now mark as SYNCED
    doc.sync_status = SYNC_SYNCED
    doc.remote_file_id = file_id
    doc.remote_knowledge_id = knowledge_id
    doc.synced_sha256 = doc.sha256
    doc.synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print("SYNCED")
    return True


def run_sync(
    config: SyncConfig,
    result: ScanResult,
    index_path: Path,
) -> SyncStats:
    """
    Authenticate, locate (or create) the Knowledge Collection, and sync all
    documents returned True by needs_sync().

    Saves the index after each document to preserve progress if the
    process is interrupted mid-run.
    """
    stats = SyncStats()
    candidates = [d for d in result.documents if needs_sync(d)]
    stats.skipped = len(result.documents) - len(candidates)

    if not candidates:
        print("Nothing to synchronize.")
        return stats

    print(f"Authenticating against {config.url} ...")
    try:
        token = authenticate(config)
    except urllib.error.HTTPError as exc:
        print(f"Authentication failed: HTTP {exc.code}", file=sys.stderr)
        stats.aborted = True
        return stats
    except (urllib.error.URLError, RuntimeError, ValueError) as exc:
        print(f"Authentication failed: {exc}", file=sys.stderr)
        stats.aborted = True
        return stats

    print(f"Locating Knowledge Collection '{config.knowledge_name}' ...")
    try:
        knowledge_id, knowledge_name = find_or_create_knowledge_collection(config, token)
    except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        stats.aborted = True
        return stats

    print(f"Ready: {knowledge_name} [{knowledge_id[:8]}...]")
    print(f"Synchronizing {len(candidates)} document(s):\n")

    for doc in candidates:
        success = sync_document(config, token, knowledge_id, doc)
        if success:
            stats.uploaded += 1
        else:
            stats.failed += 1
        # Save after each document — progress is never lost on interruption
        save_index(index_path, result.documents)

    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def print_report(
    result: ScanResult, stats: Optional[SyncStats] = None
) -> None:
    """Print the Knowledge Scan Report with change status and sync state."""
    print()
    print("Knowledge Scan Report")
    print()

    if not result.documents and not result.deleted_paths:
        print("No Markdown documents found in knowledge/.")
        print()
    else:
        for doc in result.documents:
            print(doc.filename)
            print()
            if doc.read_error:
                print("ERROR")
                print(doc.read_error)
            else:
                print(doc.status)
                if doc.sync_status != SYNC_PENDING:
                    print(f"sync: {doc.sync_status}")
            print()

        for path in sorted(result.deleted_paths):
            print(Path(path).name)
            print()
            print(STATUS_DELETED)
            print()

    print(SEPARATOR)
    print()
    print("Summary")
    print()
    print("Documents:")
    print(len(result.documents))
    print()
    print("New:")
    print(result.new_count)
    print()
    print("Modified:")
    print(result.modified_count)
    print()
    print("Unchanged:")
    print(result.unchanged_count)
    print()
    print("Deleted:")
    print(result.deleted_count)
    print()
    print("Errors:")
    print(result.error_count)

    if stats is not None:
        print()
        print(SEPARATOR)
        print()
        print("Sync")
        print()
        print("Uploaded:")
        print(stats.uploaded)
        print()
        print("Failed:")
        print(stats.failed)
        print()
        print("Skipped:")
        print(stats.skipped)

    print()
    print(SEPARATOR)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="atlas-import",
        description=(
            "Atlas Knowledge Importer — "
            "scan knowledge/<PROJECT>/, detect changes, sync to Open WebUI."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    _project_arg = dict(metavar="PROJECT", help="Project name (e.g. ABRAZO, NOEMA, ATLAS).")

    p_scan = sub.add_parser(
        "scan",
        help="Scan and detect changes. No HTTP calls. Updates the local state.",
    )
    p_scan.add_argument("project", **_project_arg)

    p_sync = sub.add_parser(
        "sync",
        help=(
            "Scan then upload NEW, PENDING, and FAILED documents "
            "to the Open WebUI Knowledge Collection."
        ),
    )
    p_sync.add_argument("project", **_project_arg)

    p_dry = sub.add_parser(
        "dry-run",
        help=(
            "Show which documents would be synchronized. "
            "No HTTP calls, no state update."
        ),
    )
    p_dry.add_argument("project", **_project_arg)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Entry point for the Atlas Knowledge Importer.

    scan   <PROJECT>: scan, detect changes, update state. No HTTP.
    dry-run <PROJECT>: scan, show sync candidates. No HTTP, no state update.
    sync   <PROJECT>: scan, detect, sync NEW/PENDING/FAILED, update state.
    """
    parser = build_parser()
    args = parser.parse_args()

    project = args.project
    name_error = validate_project_name(project)
    if name_error:
        print(f"Error: {name_error}", file=sys.stderr)
        return 1
    project_root = find_project_root()
    knowledge_dir, index_path = resolve_project_paths(project_root, project)

    if not knowledge_dir.exists():
        print(
            f"Error: project '{project}' not found at {knowledge_dir}",
            file=sys.stderr,
        )
        return 1
    if not knowledge_dir.is_dir():
        print(
            f"Error: '{knowledge_dir}' exists but is not a directory.",
            file=sys.stderr,
        )
        return 1

    index = load_index(index_path)
    result = scan_knowledge_dir(knowledge_dir)
    detect_changes(result, index)

    # --- dry-run ---
    if args.command == "dry-run":
        candidates = [d for d in result.documents if needs_sync(d)]
        print()
        print(f"Dry Run [{project}] — documents that would be synchronized:")
        print()
        if not candidates:
            print("  Nothing to synchronize.")
        else:
            for doc in candidates:
                print(f"  {doc.filename}  [{doc.status} / sync:{doc.sync_status}]")
        print()
        print_report(result)
        # Intentionally: no save_index in dry-run
        return 0

    # --- sync ---
    if args.command == "sync":
        try:
            config = load_sync_config()
        except EnvironmentError as exc:
            print(f"Configuration error:\n{exc}", file=sys.stderr)
            return 1
        config.knowledge_name = project
        print()
        stats = run_sync(config, result, index_path)
        # Final save captures scan state even when nothing was synced
        save_index(index_path, result.documents)
        print_report(result, stats)
        return 0 if (not stats.aborted and stats.failed == 0 and result.error_count == 0) else 1

    # --- scan (default) ---
    print_report(result)
    save_index(index_path, result.documents)
    return 1 if result.error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
