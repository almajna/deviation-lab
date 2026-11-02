"""Bounded public downloads and JSON-only archive reading. Never unpickle data."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

from .pipeline import AuditError

MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 12 * 1024 * 1024
MAX_INFLATED_BYTES = 128 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    if path.suffix != ".json":
        raise AuditError("only JSON input is supported; pickle is never deserialized")
    if path.stat().st_size > MAX_MEMBER_BYTES:
        raise AuditError("JSON input exceeds size limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError("expected a JSON object")
    return value


def cached_input(spec: dict, cache: Path, *, download: bool = False,
                 opener=urllib.request.urlopen) -> bytes:
    size = spec["bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_INPUT_BYTES:
        raise AuditError("invalid input byte limit")
    expected = spec["sha256"]
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise AuditError("invalid expected SHA-256")
    path = cache / (expected + ".bin")
    if path.exists():
        if path.stat().st_size != size:
            raise AuditError("cached input byte count mismatch")
        raw = path.read_bytes()
    else:
        if not download:
            raise AuditError("input not cached; use --download for bounded public retrieval")
        if not spec["url"].startswith("https://huggingface.co/datasets/"):
            raise AuditError("download source must be a public Hugging Face dataset URL")
        headers = {"User-Agent": "DEVIATION-data-audit/0.1"}
        if spec.get("range_prefix"):
            headers["Range"] = f"bytes=0-{size - 1}"
        request = urllib.request.Request(spec["url"], headers=headers)
        with opener(request, timeout=60) as response:
            if spec.get("range_prefix"):
                expected_range = f"bytes 0-{size - 1}/{spec['full_file_bytes']}"
                if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                    raise AuditError("server did not honor bounded byte range")
            raw = response.read(size + 1)
    if len(raw) != size or sha256(raw) != expected:
        raise AuditError("input size or SHA-256 mismatch")
    cache.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)
    return raw


def result_members(prefix: bytes, members: list[dict]) -> list[tuple[dict, dict]]:
    """Read four exact whitelisted members in memory; never extract tar paths.

    The gzip prefix is intentionally incomplete. Stop only after every requested
    complete member has been read and checksummed; truncated targets fail closed.
    """
    wanted = {m["path"]: m for m in members}
    if len(wanted) != len(members) or not wanted:
        raise AuditError("duplicate or empty member whitelist")
    for name in wanted:
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or not name.endswith(".json"):
            raise AuditError("unsafe archive member path")
    found, inflated = {}, 0
    try:
        with tarfile.open(fileobj=io.BytesIO(prefix), mode="r|gz") as archive:
            for member in archive:
                inflated += member.size
                if inflated > MAX_INFLATED_BYTES:
                    raise AuditError("archive exceeds uncompressed scan limit")
                if member.name not in wanted:
                    continue
                if member.name in found or not member.isfile() or not 0 < member.size <= MAX_MEMBER_BYTES:
                    raise AuditError("invalid or duplicate selected archive member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AuditError("unreadable archive member")
                raw = stream.read(MAX_MEMBER_BYTES + 1)
                spec = wanted[member.name]
                if len(raw) != member.size or sha256(raw) != spec["sha256"]:
                    raise AuditError("selected archive member checksum mismatch")
                document = json.loads(raw)
                if document.get("model_name") != spec["model_id"] or len(document.get("records", [])) != spec["records"]:
                    raise AuditError("selected member metadata mismatch")
                found[member.name] = (spec, document)
                if len(found) == len(wanted):
                    return [found[m["path"]] for m in members]
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise AuditError("archive prefix ends before all selected members") from exc
    raise AuditError("selected members missing from archive prefix")
