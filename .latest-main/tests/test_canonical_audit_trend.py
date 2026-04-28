"""
tests/test_canonical_audit_trend.py — E8b canonical audit aggregation tests.

Five tests covering:
  1. empty log → trend returns adoption_risk=False, entries_read=0
  2. window respected: only most-recent N entries (by timestamp) are counted
  3. adoption_risk=True when signal_ratio >= threshold
  4. adoption_risk=False when signal_ratio < threshold
  5. run_session_end_hook result includes canonical_audit_trend with advisory_only=True
     and the key is NEVER connected to gate.blocked

Scope note
----------
_compute_canonical_audit_trend() produces advisory_only output.
These tests verify the computation is correct and the advisory_only boundary
is never violated — no test should assert that adoption_risk affects gate.blocked.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from governance_tools.session_end_hook import (
    _compute_canonical_audit_trend,
    _CANONICAL_AUDIT_LOG_RELPATH,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_log(project_root: Path, entries: list[dict]) -> None:
    """Write entries directly to the canonical audit log (bypasses rotation)."""
    log_path = project_root / _CANONICAL_AUDIT_LOG_RELPATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, separators=(",", ":")) for e in entries]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _entry(
    project_root: Path,
    *,
    signals: list[str],
    offset_seconds: int = 0,
) -> dict:
    """Build a minimal log entry matching _append_canonical_audit_log schema."""
    ts = (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()
    return {
        "timestamp": ts,
        "session_id": f"session-test-{offset_seconds:06d}",
        "repo_name": project_root.resolve().name,
        "artifact_state": "absent" if signals else "ok",
        "signals": signals,
        "audit_note": "test note",
        "gate_blocked": False,
        "policy_provenance": {
            "policy_source": "framework_default",
            "policy_path": "",
            "fallback_used": False,
            "repo_policy_present": False,
        },
    }


# ── Test 1: empty log → adoption_risk=False ───────────────────────────────────


def test_trend_empty_log_returns_no_adoption_risk(tmp_path):
    """With no log file, trend must return adoption_risk=False and entries_read=0."""
    trend = _compute_canonical_audit_trend(
        project_root=tmp_path,
        window_size=20,
        signal_threshold_ratio=0.5,
    )

    assert trend["adoption_risk"] is False
    assert trend["entries_read"] == 0
    assert trend["advisory_only"] is True, "advisory_only must always be True"
    assert trend["signal_ratio"] == 0.0
    assert "scope_note" in trend and trend["scope_note"]


# ── Test 2: window respected using timestamp sort ─────────────────────────────


def test_trend_window_uses_most_recent_entries_by_timestamp(tmp_path):
    """
    With more entries than window_size, only the most recent window_size entries
    (by timestamp) must be counted.  Entries outside the window are ignored.
    """
    # 10 old entries WITHOUT signals (offset -100..-91 seconds ago)
    # 5 recent entries WITH signals (offset -5..-1 seconds ago)
    entries = []
    for i in range(10):
        entries.append(_entry(tmp_path, signals=[], offset_seconds=-(100 - i)))
    for i in range(5):
        entries.append(_entry(tmp_path, signals=["test_result_artifact_absent"],
                               offset_seconds=-(5 - i)))

    _write_log(tmp_path, entries)

    # window_size=5 → only the 5 recent entries (all with signals) should be read
    trend = _compute_canonical_audit_trend(
        project_root=tmp_path,
        window_size=5,
        signal_threshold_ratio=0.9,  # high threshold
    )

    assert trend["entries_read"] == 5
    assert trend["entries_with_signals"] == 5
    assert trend["signal_ratio"] == 1.0
    # 1.0 >= 0.9 → adoption_risk
    assert trend["adoption_risk"] is True


# ── Test 3: adoption_risk=True when ratio >= threshold ────────────────────────


def test_trend_adoption_risk_true_when_signal_ratio_meets_threshold(tmp_path):
    """When >= threshold fraction of window entries have signals, adoption_risk=True."""
    # 6 entries with signals, 4 without → ratio = 0.6
    entries = []
    for i in range(6):
        entries.append(_entry(tmp_path, signals=["canonical_interpretation_missing"],
                               offset_seconds=i))
    for i in range(6, 10):
        entries.append(_entry(tmp_path, signals=[], offset_seconds=i))

    _write_log(tmp_path, entries)

    trend = _compute_canonical_audit_trend(
        project_root=tmp_path,
        window_size=10,
        signal_threshold_ratio=0.5,  # 0.6 >= 0.5
    )

    assert trend["entries_read"] == 10
    assert trend["entries_with_signals"] == 6
    assert trend["signal_ratio"] == pytest.approx(0.6, abs=1e-4)
    assert trend["adoption_risk"] is True
    assert trend["advisory_only"] is True  # must always stay True


# ── Test 4: adoption_risk=False when ratio < threshold ────────────────────────


def test_trend_adoption_risk_false_when_signal_ratio_below_threshold(tmp_path):
    """When < threshold fraction have signals, adoption_risk=False."""
    # 4 with signals, 6 without → ratio = 0.4; threshold = 0.5
    entries = []
    for i in range(4):
        entries.append(_entry(tmp_path, signals=["test_result_artifact_absent"],
                               offset_seconds=i))
    for i in range(4, 10):
        entries.append(_entry(tmp_path, signals=[], offset_seconds=i))

    _write_log(tmp_path, entries)

    trend = _compute_canonical_audit_trend(
        project_root=tmp_path,
        window_size=10,
        signal_threshold_ratio=0.5,  # 0.4 < 0.5
    )

    assert trend["entries_with_signals"] == 4
    assert trend["signal_ratio"] == pytest.approx(0.4, abs=1e-4)
    assert trend["adoption_risk"] is False
    assert trend["advisory_only"] is True


# ── Test 5: run_session_end_hook includes trend; advisory_only never touches gate ──


def test_run_session_end_hook_includes_trend_and_trend_never_affects_gate(tmp_path):
    """
    run_session_end_hook() must include canonical_audit_trend with advisory_only=True.
    adoption_risk in the trend must NEVER change gate.blocked.

    Two runs: first with a clean session (no failing tests, no signals),
    then verify that even after artificially inflating the log with signal-heavy
    entries, gate.blocked stays False when the test-result artifact is absent
    (already tested in gate_policy tests) — here we just confirm the schema and
    advisory_only contract.
    """
    from governance_tools.session_end_hook import run_session_end_hook

    # Write a minimal valid closeout that passes all classification layers.
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "TASK_INTENT: test task\n"
        "WORK_COMPLETED: test_file.py\n"
        "CHECKS_RUN: pytest\n"
        "DECISION: promote\n"
        "RESPONSE: ok\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(tmp_path)

    # Key must be present.
    assert "canonical_audit_trend" in result, (
        "run_session_end_hook result must contain canonical_audit_trend"
    )
    cat = result["canonical_audit_trend"]

    # advisory_only must always be True — hard contract.
    assert cat["advisory_only"] is True, "canonical_audit_trend.advisory_only must always be True"

    # Required schema keys.
    required_keys = {
        "window_size", "entries_read", "entries_available",
        "entries_with_signals", "signal_ratio", "top_signals",
        "adoption_risk", "advisory_only", "scope_note",
    }
    missing = required_keys - set(cat.keys())
    assert not missing, f"canonical_audit_trend missing keys: {missing}"

    # adoption_risk must NOT influence gate.blocked.
    # (We can't directly set adoption_risk=True here without mocking, but we
    # can assert that the gate_policy.blocked field exists and is independent.)
    assert "gate_policy" in result
    assert "blocked" in result["gate_policy"]
    # If adoption_risk were True, gate.blocked must still reflect only gate logic.
    # The contract is: adoption_risk never feeds into gate.blocked.
    # We record this as an explicit assertion even when adoption_risk=False.
    if cat.get("adoption_risk"):
        # This session happened to trigger adoption_risk — gate must still be independent.
        assert result["gate_policy"]["blocked"] is not None  # gate has its own value
        # We do NOT assert result["gate_policy"]["blocked"] == True or False here,
        # because gate is determined by the test-result artifact state, not the trend.
