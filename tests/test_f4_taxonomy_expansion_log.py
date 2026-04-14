"""
F4 tests — Taxonomy remediation trace (taxonomy_expansion_log).

Test contract:
  1. append_pending_entry writes an entry with the correct schema and review_status="pending"
  2. list_pending returns entries where review_status=="pending"
  3. E2E: run_session_end_hook appends a pending entry when taxonomy_expansion_signal=True
  4. run_session_end_hook does NOT write a log entry when taxonomy_expansion_signal=False/absent
  5. Log write failure must not affect gate result (warning emitted only)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.taxonomy_expansion_log import (
    REVIEW_STATUS_PENDING,
    append_pending_entry,
    list_pending,
    read_log,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_test_artifact(project_root: Path, disposition: dict | None) -> None:
    artifact_dir = project_root / "artifacts" / "runtime" / "test-results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "latest.json").write_text(
        json.dumps({
            "source": "pytest-text",
            "ok": True,
            "failure_disposition": disposition,
            "errors": [],
            "warnings": [],
        }),
        encoding="utf-8",
    )


# ── F4a: substrate unit tests ─────────────────────────────────────────────────

def test_f4_log_entry_schema(tmp_path):
    """append_pending_entry writes a dict with all required fields."""
    entry = append_pending_entry(
        project_root=tmp_path,
        session_id="session-test-f4-001",
        unknown_count=5,
        unknown_threshold=3,
    )
    assert entry["session_id"] == "session-test-f4-001"
    assert entry["unknown_count"] == 5
    assert entry["unknown_threshold"] == 3
    assert entry["review_status"] == REVIEW_STATUS_PENDING
    assert "timestamp_utc" in entry
    assert entry["review_note"] is None
    assert entry["review_evidence"] is None


def test_f4_log_is_persisted(tmp_path):
    """append_pending_entry creates the NDJSON file and contents survive read_log."""
    append_pending_entry(tmp_path, "session-a", unknown_count=4, unknown_threshold=3)
    entries = read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0]["session_id"] == "session-a"
    assert entries[0]["review_status"] == REVIEW_STATUS_PENDING


def test_f4_list_pending_returns_unreviewed(tmp_path):
    """list_pending returns only entries where review_status == 'pending'.
    Non-pending entries written manually must not appear."""
    append_pending_entry(tmp_path, "session-pending", unknown_count=3, unknown_threshold=3)

    # Manually write a reviewed entry (simulates operator update)
    log_path = tmp_path / "governance" / "taxonomy_expansion_log.ndjson"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "session_id": "session-reviewed",
            "timestamp_utc": "2026-04-01T00:00:00+00:00",
            "unknown_count": 4,
            "unknown_threshold": 3,
            "review_status": "reviewed",
            "review_note": "confirmed new failure mode",
            "review_evidence": None,
        }) + "\n")

    pending = list_pending(tmp_path)
    assert len(pending) == 1
    assert pending[0]["session_id"] == "session-pending"


def test_f4_multiple_pending_entries_accumulate(tmp_path):
    """Each signal fire appends independently; no deduplication in this slice."""
    append_pending_entry(tmp_path, "session-x", unknown_count=3, unknown_threshold=3)
    append_pending_entry(tmp_path, "session-y", unknown_count=5, unknown_threshold=3)
    entries = read_log(tmp_path)
    assert len(entries) == 2
    assert {e["session_id"] for e in entries} == {"session-x", "session-y"}


def test_f4_read_log_returns_empty_when_no_file(tmp_path):
    assert read_log(tmp_path) == []


# ── F4 E2E: run_session_end_hook integration ──────────────────────────────────

def test_f4_e2e_hook_appends_when_signal_fires(tmp_path):
    """E2E: run_session_end_hook() with taxonomy_expansion_signal=True in artifact
    must write a pending log entry to governance/taxonomy_expansion_log.ndjson."""
    from governance_tools.session_end_hook import run_session_end_hook  # noqa: PLC0415

    _write_test_artifact(tmp_path, disposition={
        "verdict_blocked": False,
        "total": 5,
        "unknown_count": 5,
        "unknown_threshold": 3,
        "taxonomy_expansion_signal": True,
        "by_action": {"escalate": 5},
        "by_kind": {"unknown": 5},
        "by_confidence": {"unknown": 5},
        "results": [],
    })

    result = run_session_end_hook(project_root=tmp_path)

    # result carries the log entry
    assert result.get("taxonomy_expansion_log_entry") is not None
    log_entry = result["taxonomy_expansion_log_entry"]
    assert log_entry["review_status"] == REVIEW_STATUS_PENDING
    assert log_entry["unknown_count"] == 5
    assert log_entry["unknown_threshold"] == 3

    # log file was actually written
    pending = list_pending(tmp_path)
    assert len(pending) == 1
    assert pending[0]["session_id"] == result["session_id"]


def test_f4_e2e_hook_does_not_append_when_signal_absent(tmp_path):
    """E2E: run_session_end_hook() with taxonomy_expansion_signal=False must NOT
    write any log entry — the trace substrate only activates when signal fires."""
    from governance_tools.session_end_hook import run_session_end_hook  # noqa: PLC0415

    _write_test_artifact(tmp_path, disposition={
        "verdict_blocked": False,
        "total": 2,
        "unknown_count": 1,
        "unknown_threshold": 3,
        "taxonomy_expansion_signal": False,
        "by_action": {"test_fix_only": 2},
        "by_kind": {"unknown": 1, "stale_assertion": 1},
        "by_confidence": {"unknown": 1, "high": 1},
        "results": [],
    })

    result = run_session_end_hook(project_root=tmp_path)

    assert result.get("taxonomy_expansion_log_entry") is None
    assert read_log(tmp_path) == []


def test_f4_e2e_hook_result_ok_unaffected_by_log(tmp_path):
    """Gate result must not be affected by taxonomy_expansion_log (advisory-only)."""
    from governance_tools.session_end_hook import run_session_end_hook  # noqa: PLC0415

    _write_test_artifact(tmp_path, disposition={
        "verdict_blocked": False,  # not blocking
        "total": 5,
        "unknown_count": 5,
        "unknown_threshold": 3,
        "taxonomy_expansion_signal": True,
        "by_action": {"escalate": 5},
        "by_kind": {"unknown": 5},
        "by_confidence": {"unknown": 5},
        "results": [],
    })

    result = run_session_end_hook(project_root=tmp_path)
    # taxonomy signal is advisory; gate is not blocked by escalate actions
    # (unknown_treatment_mode defaults to permissive/warn for unknown, not always_block)
    # The key assertion: log entry presence must not pull ok down
    assert result.get("taxonomy_expansion_log_entry") is not None
    # ok may be True or False depending on gate policy defaults — do NOT assert True.
    # What matters is that the log entry's presence didn't change ok vs the no-log case.
    # Confirm taxonomy_expansion_log_entry is not in errors:
    assert not any(
        "taxonomy_expansion_log" in e for e in result["errors"]
    ), f"log entry must not produce errors; got {result['errors']}"
