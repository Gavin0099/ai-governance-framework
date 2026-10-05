#!/usr/bin/env python3
"""Append one bounded Emergency Event Journal entry to daily memory.

This is not an active-task replacement, cleanup, or pressure-reset mechanism.
"""

from __future__ import annotations

try:
    import fcntl
except ImportError:  # The dedicated event lane is unavailable without POSIX locking.
    fcntl = None
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_tools.memory_janitor import MemoryJanitor
from governance_tools.memory_record import (
    MEMORY_TYPE_SESSION_DERIVED,
    WRITER_ID,
    MemoryWriteOutcome,
    MEMORY_WRITE_STATUS_WRITTEN,
    build_record_identity,
    prepare_projection_record,
    render_session_derived_entry,
)

EVENT_VERSION = "1"
EVENT_MARKER = "EMERGENCY_EVENT"
MAX_EVENT_BYTES = 4096
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
MAX_DAILY_SCAN_BYTES = 10 * 1024 * 1024
MAX_AUTHORIZATION_REF_BYTES = 512
MAX_NOT_DONE_BYTES = 1024
_DAILY_NAME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$")


def _single_line(value: str, field_name: str, max_bytes: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    candidate = value.strip()
    if not candidate or any(char in candidate for char in ("\n", "\r", "\x00")):
        raise ValueError(f"{field_name} must be non-empty single-line text")
    if len(candidate.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field_name} exceeds its {max_bytes}-byte limit")
    return candidate


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _active_snapshot(project_root: Path) -> dict[str, Any]:
    memory_root = project_root / "memory"
    active_path = memory_root / "01_active_task.md"
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("Emergency Event Journal requires no-follow file opening")
    try:
        memory_info = memory_root.lstat()
        active_path_info = active_path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect active-task source: {exc}") from exc
    if stat.S_ISLNK(memory_info.st_mode) or not stat.S_ISDIR(memory_info.st_mode):
        raise ValueError("Emergency Event Journal requires a real memory directory")
    if stat.S_ISLNK(active_path_info.st_mode) or not stat.S_ISREG(active_path_info.st_mode):
        raise ValueError("Emergency Event Journal requires a regular active-task file")

    try:
        active_fd = os.open(active_path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ValueError(f"cannot open active-task source safely: {exc}") from exc
    try:
        opened = os.fstat(active_fd)
        if not stat.S_ISREG(opened.st_mode) or _stat_identity(opened) != _stat_identity(active_path_info):
            raise ValueError("active-task source identity changed before read")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(active_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        finished = os.fstat(active_fd)
        path_after = active_path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot read active-task source safely: {exc}") from exc
    finally:
        os.close(active_fd)
    if _stat_identity(opened) != _stat_identity(finished) or _stat_identity(opened) != _stat_identity(path_after):
        raise ValueError("active-task source changed while measuring pressure")

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("active-task source is not strict UTF-8") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    line_count = len(normalized.splitlines())
    char_count = len(text)
    if line_count >= MemoryJanitor.HOT_MEMORY_CRITICAL or char_count >= MemoryJanitor.HOT_MEMORY_CRITICAL_SIZE_LIMIT:
        pressure = "EMERGENCY"
    elif line_count >= MemoryJanitor.HOT_MEMORY_HARD_LIMIT or char_count >= MemoryJanitor.HOT_MEMORY_HARD_SIZE_LIMIT:
        pressure = "CRITICAL"
    elif line_count >= MemoryJanitor.HOT_MEMORY_SOFT_LIMIT or char_count >= MemoryJanitor.HOT_MEMORY_SOFT_SIZE_LIMIT:
        pressure = "WARNING"
    else:
        pressure = "SAFE"
    if pressure != "EMERGENCY":
        raise ValueError("Emergency Event Journal is only available at measured EMERGENCY pressure")
    return {
        "active_task_sha256": hashlib.sha256(raw).hexdigest(),
        "active_task_lines": line_count,
        "active_task_chars": char_count,
        "pressure": pressure,
    }


def _hash_evidence(project_root: Path, evidence_path: str) -> tuple[str, str]:
    if "\\" in evidence_path:
        raise ValueError("evidence path must use repository-relative '/' separators")
    relative = Path(evidence_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("evidence path must be relative and cannot traverse parents")
    if relative.parts[:2] != ("artifacts", "evidence") or len(relative.parts) < 3:
        raise ValueError("evidence file must be under artifacts/evidence/")

    current = project_root
    try:
        for part in relative.parts:
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError("evidence path must not contain symlinks")
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("evidence path must identify a regular file")
        if info.st_size > MAX_EVIDENCE_BYTES:
            raise ValueError("evidence file exceeds the 10 MiB limit")
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(project_root / "artifacts" / "evidence"):
            raise ValueError("evidence resolves outside artifacts/evidence/")
        digest = hashlib.sha256()
        with current.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _stat_identity(opened) != _stat_identity(info):
                raise ValueError("evidence changed while opening")
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            finished = os.fstat(stream.fileno())
        after = current.lstat()
    except OSError as exc:
        raise ValueError(f"cannot verify evidence file: {exc}") from exc
    if _stat_identity(info) != _stat_identity(finished) or _stat_identity(info) != _stat_identity(after):
        raise ValueError("evidence changed while hashing")
    return relative.as_posix(), digest.hexdigest()


def _reject_existing_source_event(memory_root: Path, active_sha256: str) -> None:
    marker = f"  emergency_active_task_sha256: {active_sha256}\n".encode("ascii")
    for path in sorted(memory_root.iterdir()):
        if not _DAILY_NAME.fullmatch(path.name):
            continue
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise ValueError("cannot safely scan non-regular daily memory files")
            if info.st_size > MAX_DAILY_SCAN_BYTES:
                raise ValueError("daily memory exceeds the 10 MiB emergency scan limit")
            content = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"cannot scan existing daily memory: {exc}") from exc
        if marker in content:
            raise ValueError("one Emergency Event Journal entry already exists for this active source")


def _render_emergency_entry(record: dict[str, str], metadata: dict[str, Any]) -> str:
    entry = render_session_derived_entry(record)
    identity_line = f"  record_identity: {record['record_identity']}\n"
    if entry.count(identity_line) != 1:
        raise ValueError("canonical record identity line is missing or ambiguous")
    fields = (
        ("emergency_event_marker", EVENT_MARKER),
        ("emergency_event_version", EVENT_VERSION),
        ("emergency_event_at_utc", metadata["at_utc"]),
        ("emergency_event_authorization_ref", metadata["authorization_ref"]),
        ("emergency_active_task_sha256", metadata["active_task_sha256"]),
        ("emergency_active_task_lines", metadata["active_task_lines"]),
        ("emergency_active_task_chars", metadata["active_task_chars"]),
        ("emergency_evidence_path", metadata["evidence_path"]),
        ("emergency_evidence_sha256", metadata["evidence_sha256"]),
        ("emergency_not_done", metadata["not_done"]),
        ("emergency_event_identity", metadata["event_identity"]),
    )
    additions = "".join(f"  {key}: {value}\n" for key, value in fields)
    return entry.replace(identity_line, additions + identity_line, 1)


def append_emergency_event_with_outcome(
    *,
    project_root: Path,
    record: dict[str, str],
    authorization_ref: str,
    not_done: str,
    evidence_path: str,
) -> MemoryWriteOutcome:
    """Append at most one bounded daily event for the current active-source digest."""
    if fcntl is None or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("Emergency Event Journal requires POSIX directory locking")
    project_root = project_root.resolve()
    memory_root = project_root / "memory"
    try:
        memory_info = memory_root.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect memory directory: {exc}") from exc
    if stat.S_ISLNK(memory_info.st_mode) or not stat.S_ISDIR(memory_info.st_mode):
        raise ValueError("Emergency Event Journal requires a real memory directory")

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(memory_root, directory_flags)
    try:
        opened_memory = os.fstat(directory_fd)
        if _stat_identity(opened_memory) != _stat_identity(memory_info):
            raise ValueError("memory directory changed before acquiring event lock")
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        snapshot = _active_snapshot(project_root)
        authorization_ref = _single_line(
            authorization_ref, "authorization_ref", MAX_AUTHORIZATION_REF_BYTES
        )
        not_done = _single_line(not_done, "not_done", MAX_NOT_DONE_BYTES)
        if record.get("memory_type") != MEMORY_TYPE_SESSION_DERIVED:
            raise ValueError("Emergency Event Journal requires a canonical session-derived record")
        prepared = prepare_projection_record(record)
        if prepared["plan_reconciliation"] == "updated":
            raise ValueError("Emergency Event Journal must not claim a PLAN update")
        if not prepared["test_evidence"].startswith(("NOT RUN:", "NOT CLAIMED:")):
            raise ValueError("Emergency Event Journal must not make a validation-success claim")

        relative_evidence, evidence_sha256 = _hash_evidence(project_root, evidence_path)
        prepared["test_evidence"] = (
            "NOT CLAIMED: emergency event capture only; "
            f"evidence={relative_evidence}; sha256={evidence_sha256}"
        )
        prepared["record_identity"] = build_record_identity(prepared)
        metadata: dict[str, Any] = {
            "at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "authorization_ref": authorization_ref,
            **snapshot,
            "evidence_path": relative_evidence,
            "evidence_sha256": evidence_sha256,
            "not_done": not_done,
        }
        identity_payload = {
            "record": {key: value for key, value in prepared.items() if key != "record_identity"},
            "metadata": metadata,
        }
        metadata["event_identity"] = hashlib.sha256(
            json.dumps(identity_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        entry = _render_emergency_entry(prepared, metadata)
        entry_bytes = entry.encode("utf-8")
        if len(entry_bytes) > MAX_EVENT_BYTES:
            raise ValueError("Emergency Event Journal entry exceeds the 4 KiB limit")

        if _active_snapshot(project_root) != snapshot:
            raise ValueError("active-task source changed before event append")
        if _hash_evidence(project_root, relative_evidence)[1] != evidence_sha256:
            raise ValueError("evidence changed before event append")
        _reject_existing_source_event(memory_root, snapshot["active_task_sha256"])

        daily_path = memory_root / f"{datetime.now().astimezone().date().isoformat()}.md"
        try:
            existing_info = daily_path.lstat()
        except FileNotFoundError:
            existing_info = None
        if existing_info is not None:
            if stat.S_ISLNK(existing_info.st_mode) or not stat.S_ISREG(existing_info.st_mode):
                raise ValueError("daily event target must be a regular file")
            if existing_info.st_size > MAX_DAILY_SCAN_BYTES:
                raise ValueError("daily event target exceeds the 10 MiB append guard")
            existing = daily_path.read_bytes()
            existing.decode("utf-8", errors="strict")
        else:
            existing = b""

        if not existing:
            prefix = f"# {datetime.now().astimezone().date().isoformat()}\n\n".encode("utf-8")
        else:
            prefix = (b"" if existing.endswith((b"\n", b"\r")) else b"\n") + b"\n"
        append_bytes = prefix + entry_bytes
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        if existing_info is None:
            flags |= os.O_CREAT | os.O_EXCL
        file_fd = os.open(daily_path, flags, 0o666)
        try:
            opened = os.fstat(file_fd)
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError("daily event target is not a regular file")
            if existing_info is None:
                if opened.st_size != 0:
                    raise ValueError("daily event target appeared before exclusive creation")
            else:
                if _stat_identity(opened) != _stat_identity(existing_info) or opened.st_size != len(existing):
                    raise ValueError("daily event target changed before append")
                if daily_path.read_bytes() != existing:
                    raise ValueError("daily event target content changed before append")
            view = memoryview(append_bytes)
            while view:
                written = os.write(file_fd, view)
                if written <= 0:
                    raise OSError("short write while appending emergency event")
                view = view[written:]
            os.fsync(file_fd)
        finally:
            os.close(file_fd)
        if existing_info is None:
            os.fsync(directory_fd)
        return MemoryWriteOutcome(
            path=daily_path,
            status=MEMORY_WRITE_STATUS_WRITTEN,
            record_identity=prepared["record_identity"],
            writer=WRITER_ID,
        )
    finally:
        fcntl.flock(directory_fd, fcntl.LOCK_UN)
        os.close(directory_fd)