"""
taxonomy_expansion_log.py — Remediation trace substrate for taxonomy_expansion_signal.

When `taxonomy_expansion_signal=True` fires in a session, the session_end_hook
writes one entry here with review_status="pending".  Operators update the entry
fields manually (or via a future write-back tool) to leave a closure trace.

Authority:
  - This log is advisory-only.  Its contents do not affect gate decisions.
  - A "pending" entry does NOT block anything — it is a visibility record.
  - The log exists so that repeated unreviewed signals accumulate visibly
    instead of silently disappearing each session.

Storage: <project_root>/governance/taxonomy_expansion_log.ndjson
  One JSON object per line.  Appended; never overwritten.

Entry schema:
  session_id:       str   — matches session_end_hook session_id
  timestamp_utc:    str   — ISO 8601 UTC
  unknown_count:    int   — unknown failures in the session that triggered signal
  unknown_threshold: int  — threshold value that classified the count as expansion signal
  review_status:    str   — "pending" | "reviewed" | "updated" | "dismissed"
                            default = "pending" on write
  review_note:      str | None  — free-form operator annotation
  review_evidence:  str | None  — path or URL to supporting evidence
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_LOG_RELPATH = Path("governance") / "taxonomy_expansion_log.ndjson"

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_REVIEWED = "reviewed"
REVIEW_STATUS_UPDATED = "updated"
REVIEW_STATUS_DISMISSED = "dismissed"

VALID_REVIEW_STATUSES = frozenset({
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_REVIEWED,
    REVIEW_STATUS_UPDATED,
    REVIEW_STATUS_DISMISSED,
})


def _log_path(project_root: Path) -> Path:
    return project_root / _LOG_RELPATH


def append_pending_entry(
    project_root: Path,
    session_id: str,
    unknown_count: int,
    unknown_threshold: int,
) -> dict:
    """
    Append one 'pending' remediation trace entry to the log file.

    Returns the dict that was written (so callers can include it in result output).
    The log directory is created if absent.  Raises on write error (caller decides
    how to handle — session_end_hook wraps in try/except to stay non-blocking).
    """
    entry = {
        "session_id": session_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "unknown_count": unknown_count,
        "unknown_threshold": unknown_threshold,
        "review_status": REVIEW_STATUS_PENDING,
        "review_note": None,
        "review_evidence": None,
    }
    log_file = _log_path(project_root)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_log(project_root: Path) -> list[dict]:
    """
    Read all entries from the log.  Returns an empty list if the file does not
    exist or is empty.  Malformed lines are skipped silently.
    """
    log_file = _log_path(project_root)
    if not log_file.exists():
        return []
    entries = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def list_pending(project_root: Path) -> list[dict]:
    """Return only entries where review_status == 'pending'."""
    return [e for e in read_log(project_root) if e.get("review_status") == REVIEW_STATUS_PENDING]
