"""
M4.1 — OpenAI ChatGPT export reader.

Reads a ChatGPT Data Export ZIP directly, without prior extraction and
without ever modifying the RAW archive. Responsible only for RAW access:
manifest discovery, conversation shard discovery, conversation iteration,
and asset/library metadata access.

Semantic interpretation and ACNF normalization happen downstream in
normalizer.py — this module never reinterprets content, only exposes it.
"""

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

MANIFEST_FILENAME = "export_manifest.json"
ASSET_FILENAME_MAP_FILENAME = "conversation_asset_file_names.json"
LIBRARY_FILES_FILENAME = "library_files.json"

_SHARD_RE = re.compile(r"conversations-(\d+)\.json\Z")
_READ_CHUNK_SIZE = 65536


class ExportReaderError(Exception):
    """Raised for structural problems reading a ChatGPT export ZIP."""


class ChatGPTExportReader:
    """
    Read-only accessor over a ChatGPT export ZIP.

    Usage:
        with ChatGPTExportReader(zip_path) as reader:
            for conversation in reader.iter_conversations():
                ...
    """

    def __init__(self, zip_path: Path) -> None:
        self.zip_path = Path(zip_path)
        if not self.zip_path.exists():
            raise ExportReaderError(f"Export ZIP not found: {self.zip_path}")
        try:
            self._zf = zipfile.ZipFile(self.zip_path, "r")
        except zipfile.BadZipFile as exc:
            raise ExportReaderError(f"Invalid ZIP file: {self.zip_path} ({exc})") from exc
        self._namelist = set(self._zf.namelist())
        self._manifest_cache: Optional[Dict[str, Any]] = None
        self._shard_cache: Optional[List[str]] = None
        self._source_sha256_cache: Optional[str] = None

    def __enter__(self) -> "ChatGPTExportReader":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self._zf.close()

    # -- raw file access -----------------------------------------------------

    def has_file(self, name: str) -> bool:
        return name in self._namelist

    def read_json(self, name: str) -> Any:
        """Read and parse a JSON member of the ZIP. Raises ExportReaderError on failure."""
        try:
            raw = self._zf.read(name)
        except KeyError as exc:
            raise ExportReaderError(f"Missing file in export: {name}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ExportReaderError(f"Invalid JSON in {name}: {exc}") from exc

    def read_bytes(self, name: str) -> bytes:
        try:
            return self._zf.read(name)
        except KeyError as exc:
            raise ExportReaderError(f"Missing file in export: {name}") from exc

    def file_size(self, name: str) -> Optional[int]:
        try:
            return self._zf.getinfo(name).file_size
        except KeyError:
            return None

    # -- source identity -------------------------------------------------------

    def source_sha256(self) -> str:
        """SHA-256 of the raw ZIP file's bytes, computed in fixed-size chunks."""
        if self._source_sha256_cache is None:
            h = hashlib.sha256()
            with open(self.zip_path, "rb") as f:
                while True:
                    chunk = f.read(_READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    h.update(chunk)
            self._source_sha256_cache = h.hexdigest()
        return self._source_sha256_cache

    # -- manifest ---------------------------------------------------------------

    def manifest(self) -> Dict[str, Any]:
        """Return the parsed export_manifest.json. Raises ExportReaderError if missing/invalid."""
        if self._manifest_cache is None:
            if not self.has_file(MANIFEST_FILENAME):
                raise ExportReaderError(f"Missing {MANIFEST_FILENAME} in export")
            data = self.read_json(MANIFEST_FILENAME)
            if not isinstance(data, dict):
                raise ExportReaderError(f"{MANIFEST_FILENAME} does not contain a JSON object")
            self._manifest_cache = data
        return self._manifest_cache

    # -- conversation shard discovery -------------------------------------------

    def discover_conversation_shards(self) -> List[str]:
        """
        Return conversation shard filenames (e.g. conversations-000.json),
        sorted numerically by shard index. Discovery tries the manifest
        first (any string found anywhere within it matching the shard
        filename pattern), then falls back to scanning the ZIP's own file
        list. The shard count is never hardcoded.
        """
        if self._shard_cache is not None:
            return self._shard_cache

        found: Dict[int, str] = {}

        try:
            manifest = self.manifest()
            for name in _iter_strings(manifest):
                m = _SHARD_RE.search(name)
                if m and name in self._namelist:
                    found[int(m.group(1))] = name
        except ExportReaderError:
            pass  # fall back to scanning the ZIP directly

        if not found:
            for name in self._namelist:
                m = _SHARD_RE.search(name)
                if m:
                    found[int(m.group(1))] = name

        if not found:
            raise ExportReaderError(
                "No conversation shard files (conversations-*.json) found in export"
            )

        self._shard_cache = [found[idx] for idx in sorted(found)]
        return self._shard_cache

    def iter_conversations(self) -> Iterator[Dict[str, Any]]:
        """
        Yield raw conversation dicts across all shards, in numeric shard
        order and then in-file array order.
        """
        for shard_name in self.discover_conversation_shards():
            data = self.read_json(shard_name)
            if not isinstance(data, list):
                raise ExportReaderError(f"Conversation shard {shard_name} does not contain a JSON array")
            for entry in data:
                if not isinstance(entry, dict):
                    raise ExportReaderError(f"Non-object conversation entry found in {shard_name}")
                yield entry

    # -- asset / library metadata ------------------------------------------------

    def conversation_asset_file_names(self) -> Dict[str, Any]:
        """
        Raw parsed contents of conversation_asset_file_names.json.

        Returns {} if the file is absent from the export; callers should
        treat that as "no known original filenames", not a fatal error.
        """
        if not self.has_file(ASSET_FILENAME_MAP_FILENAME):
            return {}
        data = self.read_json(ASSET_FILENAME_MAP_FILENAME)
        return data if isinstance(data, dict) else {}

    def library_files(self) -> Any:
        """Raw parsed contents of library_files.json, or None if absent."""
        if not self.has_file(LIBRARY_FILES_FILENAME):
            return None
        return self.read_json(LIBRARY_FILES_FILENAME)

    def has_asset(self, physical_filename: str) -> bool:
        return physical_filename in self._namelist

    def read_asset_bytes(self, physical_filename: str) -> Optional[bytes]:
        if not self.has_asset(physical_filename):
            return None
        return self.read_bytes(physical_filename)

    def physical_dat_filenames(self) -> List[str]:
        """
        Return every *.dat member in the ZIP, sorted, regardless of
        whether any conversation message references it. This is a
        generic physical-asset inventory independent of the
        conversation_asset_file_names.json mapping or any message
        content — used so no physical asset silently disappears from the
        normalized inventory.
        """
        return sorted(name for name in self._namelist if name.endswith(".dat"))

    def hash_asset_sha256(self, physical_filename: str) -> Optional[str]:
        """
        SHA-256 of one ZIP member's decompressed bytes, computed in
        fixed-size chunks via a streaming read so the full asset is never
        held in memory solely for hashing. Returns None if the member is
        absent.
        """
        if not self.has_asset(physical_filename):
            return None
        h = hashlib.sha256()
        with self._zf.open(physical_filename) as f:
            while True:
                chunk = f.read(_READ_CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()


def _iter_strings(obj: Any) -> Iterator[str]:
    """Recursively yield every string key/value found anywhere within obj."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _iter_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_strings(item)
