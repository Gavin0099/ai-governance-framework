#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

WRITER_ID = "governance_tools.memory_record"
RECORD_FORMAT_VERSION = "1.0"
MEMORY_TYPE_SESSION_DERIVED = "session-derived"


def _current_local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def build_session_derived_record(
    *,
    what_changed: str,
    commit: str,
    session_id: str,
    memory_binding: str,
    test_evidence: str,
    next_step: str,
) -> dict[str, str]:
    return {
        "memory_type": MEMORY_TYPE_SESSION_DERIVED,
        "record_format_version": RECORD_FORMAT_VERSION,
        "writer": WRITER_ID,
        "what_changed": what_changed,
        "commit": commit,
        "commit_hash": commit,
        "session_id": session_id,
        "memory_binding": memory_binding,
        "test_evidence": test_evidence,
        "next_step": next_step,
    }


def render_session_derived_entry(record: dict[str, str]) -> str:
    return (
        f"- memory_type: {record['memory_type']}\n"
        f"  record_format_version: {record['record_format_version']}\n"
        f"  writer: {record['writer']}\n"
        f"  what_changed: {record['what_changed']}\n"
        f"  commit: {record['commit']}\n"
        f"  commit_hash: {record['commit_hash']}\n"
        f"  session_id: {record['session_id']}\n"
        f"  memory_binding: {record['memory_binding']}\n"
        f"  test_evidence: {record['test_evidence']}\n"
        f"  next_step: {record['next_step']}\n"
    )


def append_session_derived_entry(*, project_root: Path, record: dict[str, str]) -> Path:
    memory_root = project_root / "memory"
    memory_root.mkdir(parents=True, exist_ok=True)
    daily_path = memory_root / f"{_current_local_date()}.md"
    if not daily_path.exists():
        daily_path.write_text(f"# {_current_local_date()}\n\n", encoding="utf-8")

    entry = render_session_derived_entry(record)
    with daily_path.open("a", encoding="utf-8") as fh:
        if daily_path.stat().st_size > 0:
            fh.write("\n")
        fh.write(entry)
    return daily_path
