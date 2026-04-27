"""
tests/test_canonical_audit_log.py — E8a canonical audit signal persistence tests.

Five tests covering:
  1. log entry is created when hook runs (file created, entry parseable)
  2. log is append-only: second run appends without overwriting first entry
  3. log schema: each entry has all required keys with correct types
  4. log entries with advisory signals are persisted with correct signal codes
  5. rotation: entries beyond _CANONICAL_AUDIT_LOG_MAX_ENTRIES are trimmed (oldest removed)

Authority boundary note
-----------------------
These tests verify observability behaviour only.
They do NOT assert that the log is authoritative — the authority of truth
for session outcomes remains the run_session_end_hook() result dict.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from governance_tools.session_end_hook import (
    _append_canonical_audit_log,
    _CANONICAL_AUDIT_LOG_RELPATH,
    _CANONICAL_AUDIT_LOG_MAX_ENTRIES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_audit(
    project_root: Path,
    *,
    signals: list[str] | None = None,
    artifact_state: str = "ok",
    gate_blocked: bool = False,
    session_id: str = "session-test-000000",
) -> None:
    """Call _append_canonical_audit_log with minimal valid arguments."""
    audit = {
        "signals": signals or [],
        "audit_note": "test audit note",
    }
    _append_canonical_audit_log(
        project_root=project_root,
        session_id=session_id,
        artifact_state=artifact_state,
        canonical_path_audit=audit,
        gate_blocked=gate_blocked,
        policy_source="framework_default",
        policy_path="governance/gate_policy.yaml",
        fallback_used=False,
        repo_policy_present=False,
    )


def _read_log(project_root: Path) -> list[dict]:
    """Read and parse all JSONL entries from the canonical audit log."""
    log_path = project_root / _CANONICAL_AUDIT_LOG_RELPATH
    if not log_path.exists():
        return []
    lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


# ── Test 1: log entry created on first run ────────────────────────────────────


def test_canonical_audit_log_entry_created_on_first_run(tmp_path):
    """After _append_canonical_audit_log, log file must exist with one parseable entry."""
    _clean_audit(tmp_path)

    log_path = tmp_path / _CANONICAL_AUDIT_LOG_RELPATH
    assert log_path.exists(), f"Expected log file at {log_path}"

    entries = _read_log(tmp_path)
    assert len(entries) == 1, f"Expected exactly 1 entry, got {len(entries)}"
    assert isinstance(entries[0], dict), "Entry must be a JSON object"


# ── Test 2: log is append-only ────────────────────────────────────────────────


def test_canonical_audit_log_is_append_only(tmp_path):
    """Second run must append a new entry without overwriting the first."""
    _clean_audit(tmp_path, session_id="session-first-aaaaaa")
    _clean_audit(tmp_path, session_id="session-second-bbbbbb")

    entries = _read_log(tmp_path)
    assert len(entries) == 2, f"Expected 2 entries after 2 appends, got {len(entries)}"

    session_ids = [e["session_id"] for e in entries]
    assert "session-first-aaaaaa" in session_ids
    assert "session-second-bbbbbb" in session_ids

    # Ordering: first appended entry must come before second.
    assert session_ids.index("session-first-aaaaaa") < session_ids.index("session-second-bbbbbb"), (
        "Entries must be in append order (oldest first)"
    )


# ── Test 3: log entry schema is complete ─────────────────────────────────────


def test_canonical_audit_log_entry_schema_is_complete(tmp_path):
    """Each log entry must contain all required keys with correct types."""
    _clean_audit(
        tmp_path,
        signals=["test_result_artifact_absent"],
        artifact_state="absent",
        gate_blocked=False,
        session_id="session-schema-cccccc",
    )

    entries = _read_log(tmp_path)
    assert len(entries) == 1
    e = entries[0]

    required_str_keys = {"timestamp", "session_id", "repo_name", "artifact_state", "audit_note"}
    for k in required_str_keys:
        assert k in e, f"Missing key: {k}"
        assert isinstance(e[k], str), f"Key {k!r} must be str, got {type(e[k])}"

    assert "signals" in e
    assert isinstance(e["signals"], list), "signals must be a list"

    assert "gate_blocked" in e
    assert isinstance(e["gate_blocked"], bool), "gate_blocked must be bool"

    assert "policy_provenance" in e
    pp = e["policy_provenance"]
    for k in ("policy_source", "policy_path"):
        assert k in pp, f"policy_provenance missing key: {k}"
    assert "fallback_used" in pp and isinstance(pp["fallback_used"], bool)
    assert "repo_policy_present" in pp and isinstance(pp["repo_policy_present"], bool)

    # Timestamp must be ISO-8601 parseable
    from datetime import datetime
    datetime.fromisoformat(e["timestamp"])  # raises ValueError if malformed


# ── Test 4: advisory signals are persisted correctly ─────────────────────────


def test_canonical_audit_log_persists_advisory_signals_correctly(tmp_path):
    """
    When signals are present, they must appear verbatim in the log entry.
    This covers both known signal codes.
    """
    # Run 1: test_result_artifact_absent
    _clean_audit(tmp_path, signals=["test_result_artifact_absent"], artifact_state="absent",
                 session_id="session-sig-absent")

    # Run 2: canonical_interpretation_missing
    _clean_audit(tmp_path, signals=["canonical_interpretation_missing"], artifact_state="ok",
                 session_id="session-sig-missing")

    # Run 3: clean (no signals)
    _clean_audit(tmp_path, signals=[], artifact_state="ok", session_id="session-sig-clean")

    entries = _read_log(tmp_path)
    assert len(entries) == 3

    by_session = {e["session_id"]: e for e in entries}

    assert by_session["session-sig-absent"]["signals"] == ["test_result_artifact_absent"]
    assert by_session["session-sig-absent"]["artifact_state"] == "absent"

    assert by_session["session-sig-missing"]["signals"] == ["canonical_interpretation_missing"]
    assert by_session["session-sig-missing"]["artifact_state"] == "ok"

    assert by_session["session-sig-clean"]["signals"] == []


# ── Test 5: rotation removes oldest entries when limit exceeded ───────────────


def test_canonical_audit_log_rotation_trims_oldest_entries(tmp_path):
    """
    When entries exceed _CANONICAL_AUDIT_LOG_MAX_ENTRIES, oldest must be removed.
    After rotation, the log must contain exactly _CANONICAL_AUDIT_LOG_MAX_ENTRIES entries
    and the most recent entries must be present.
    """
    limit = _CANONICAL_AUDIT_LOG_MAX_ENTRIES

    # Write limit + 10 entries.
    total = limit + 10
    for i in range(total):
        _clean_audit(tmp_path, session_id=f"session-rot-{i:06d}")

    entries = _read_log(tmp_path)
    assert len(entries) == limit, (
        f"After {total} appends, expected exactly {limit} entries, got {len(entries)}"
    )

    # The last entry must be the most recently written.
    last_session = f"session-rot-{total - 1:06d}"
    assert entries[-1]["session_id"] == last_session, (
        f"Last entry must be most recent: expected {last_session}, "
        f"got {entries[-1]['session_id']}"
    )

    # The first 10 entries (session-rot-000000..000009) must have been rotated out.
    surviving_ids = {e["session_id"] for e in entries}
    for i in range(10):
        old_id = f"session-rot-{i:06d}"
        assert old_id not in surviving_ids, (
            f"Old entry {old_id!r} should have been rotated out"
        )


# ── Test 6: policy_load_error is persisted in policy_provenance ───────────────


def test_canonical_audit_log_policy_load_error_persisted_in_provenance(tmp_path):
    """
    When policy_load_error is set (YAML parse failure), it must appear inside
    policy_provenance of the JSONL entry so the parse failure is observable
    in the E8a substrate without requiring a live session re-run.
    """
    error_msg = "yaml.scanner.ScannerError: mapping values are not allowed here"
    audit = {"signals": [], "audit_note": "test"}
    _append_canonical_audit_log(
        project_root=tmp_path,
        session_id="session-parse-err-dddddd",
        artifact_state="ok",
        canonical_path_audit=audit,
        gate_blocked=False,
        policy_source="builtin_default",
        policy_path="governance/gate_policy.yaml",
        fallback_used=True,
        repo_policy_present=True,
        policy_load_error=error_msg,
    )

    entries = _read_log(tmp_path)
    assert len(entries) == 1
    pp = entries[0]["policy_provenance"]
    assert "policy_load_error" in pp, (
        "policy_load_error must be present in policy_provenance when a YAML parse error occurred"
    )
    assert pp["policy_load_error"] == error_msg


def test_canonical_audit_log_policy_load_error_absent_when_clean(tmp_path):
    """
    When policy_load_error is None (clean load), the key must NOT appear in
    policy_provenance — entries must stay minimal when there is no error.
    """
    _clean_audit(tmp_path, session_id="session-clean-eeeeee")

    entries = _read_log(tmp_path)
    assert len(entries) == 1
    pp = entries[0]["policy_provenance"]
    assert "policy_load_error" not in pp, (
        "policy_load_error must be absent from policy_provenance on a clean policy load"
    )
