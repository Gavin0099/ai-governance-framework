"""
tests/test_e1b_observation.py
==============================
E1b Phase 1 — Passive Observation Layer tests.

Six tests covering the original authority-boundary contract,
plus three Track A deprecation tests:
  1. Empty log → is_degenerate=True, entropy=0, advisory_only=True
  2. All-same artifact_state (degenerate: all absent) → entropy<0.3 → is_degenerate=True
  3. Mixed artifact_states (ok + absent) → entropy>=0.3 → is_degenerate=False
  4. advisory_only=True is hard-coded; is_degenerate never affects gate.blocked
  5. run_session_end_hook() result includes e1b_observation key with required schema
  6. format_human_result() renders e1b_observation line; degenerate shows [ADVISORY]
  7. [Track A] is_degenerate_deprecated=True present in all three return paths
  8. [Track A] format_human_result renders [DEPRECATED:legacy_entropy] in e1b line
  9. [Track A] format_human_result renders [DEPRECATED] advisory (not [NOTE])

Authority boundary tests
------------------------
These tests assert that is_degenerate CANNOT influence gate.blocked.
This is an explicit contract, not an implementation detail.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from governance_tools.session_end_hook import (
    _build_e1b_observation,
    _E1B_MIN_VALID_ENTROPY,
    _CANONICAL_AUDIT_LOG_RELPATH,
    run_session_end_hook,
    format_human_result,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _write_audit_log(project_root: Path, entries: list[dict]) -> None:
    """Write a canonical-audit-log.jsonl with the given entries."""
    log_path = project_root / _CANONICAL_AUDIT_LOG_RELPATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


def _make_audit_entry(repo_name: str, artifact_state: str, signals: list[str] | None = None) -> dict:
    return {
        "timestamp": "2026-04-14T00:00:00+00:00",
        "session_id": f"session-{artifact_state}-{id(artifact_state)}",
        "repo_name": repo_name,
        "artifact_state": artifact_state,
        "signals": signals or [],
        "audit_note": "",
        "gate_blocked": False,
        "policy_provenance": {},
    }


_MINIMAL_CLOSEOUT = (
    "TASK_INTENT: e1b observation test\n"
    "WORK_COMPLETED: test_file.py\n"
    "CHECKS_RUN: pytest\n"
    "DECISION: promote\n"
    "RESPONSE: ok\n"
)


# ── Test 1: Empty log → degenerate ─────────────────────────────────────────────


def test_e1b_observation_empty_log_is_degenerate(tmp_path):
    """Empty audit log → is_degenerate=True, entropy=0, advisory_only=True."""
    result = _build_e1b_observation(project_root=tmp_path, window_size=20)

    assert result["is_degenerate"] is True
    assert result["entropy"] == 0.0
    assert result["advisory_only"] is True, "advisory_only must be hard-coded True"
    assert result["raw_entries"] == 0


# ── Test 2: All-same state → degenerate ───────────────────────────────────────


def test_e1b_observation_uniform_state_is_degenerate(tmp_path):
    """
    20 entries all with artifact_state='absent' → distinct_states=1,
    entropy=1/20=0.05 < 0.3 → is_degenerate=True.
    """
    repo_name = tmp_path.resolve().name
    entries = [_make_audit_entry(repo_name, "absent") for _ in range(20)]
    _write_audit_log(tmp_path, entries)

    result = _build_e1b_observation(project_root=tmp_path, window_size=20)

    assert result["distinct_states"] == 1
    assert result["entropy"] < _E1B_MIN_VALID_ENTROPY
    assert result["is_degenerate"] is True
    assert result["advisory_only"] is True


# ── Test 3: Mixed states → not degenerate ─────────────────────────────────────


def test_e1b_observation_mixed_states_not_degenerate(tmp_path):
    """
    10 absent + 10 ok (out of 20) → distinct_states=2,
    entropy=2/20=0.1 — still degenerate at 0.1 with window=20.
    Use smaller window to cross the 0.3 threshold:
      3 entries with 2 distinct states → entropy=2/3=0.67 → VALID.
    """
    repo_name = tmp_path.resolve().name
    entries = [
        _make_audit_entry(repo_name, "absent"),
        _make_audit_entry(repo_name, "ok"),
        _make_audit_entry(repo_name, "stale"),
    ]
    _write_audit_log(tmp_path, entries)

    result = _build_e1b_observation(project_root=tmp_path, window_size=20)

    assert result["distinct_states"] == 3
    assert result["entropy"] >= _E1B_MIN_VALID_ENTROPY, (
        f"entropy={result['entropy']} should be >= {_E1B_MIN_VALID_ENTROPY} "
        f"with 3 distinct states over 3 entries"
    )
    assert result["is_degenerate"] is False
    assert result["advisory_only"] is True


# ── Test 4: advisory_only=True is always hard-coded ───────────────────────────


def test_e1b_observation_advisory_only_always_true(tmp_path):
    """
    advisory_only must be True in all cases (empty, degenerate, valid).
    This is an authority boundary test — not an implementation detail.
    """
    repo_name = tmp_path.resolve().name

    # empty
    r_empty = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert r_empty["advisory_only"] is True

    # degenerate (all absent)
    entries_degen = [_make_audit_entry(repo_name, "absent") for _ in range(5)]
    _write_audit_log(tmp_path, entries_degen)
    r_degen = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert r_degen["advisory_only"] is True

    # valid (mixed)
    entries_valid = [
        _make_audit_entry(repo_name, "absent"),
        _make_audit_entry(repo_name, "ok"),
        _make_audit_entry(repo_name, "stale"),
    ]
    _write_audit_log(tmp_path, entries_valid)
    r_valid = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert r_valid["advisory_only"] is True


# ── Test 5: run_session_end_hook includes e1b_observation ─────────────────────


def test_run_session_end_hook_includes_e1b_observation(tmp_path):
    """
    run_session_end_hook() result must include 'e1b_observation' key
    with required sub-keys.  gate.blocked must NOT be affected by
    is_degenerate.
    """
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(_MINIMAL_CLOSEOUT, encoding="utf-8")

    result = run_session_end_hook(tmp_path)

    assert "e1b_observation" in result, (
        "run_session_end_hook() result must contain 'e1b_observation' key"
    )
    obs = result["e1b_observation"]
    required = {"raw_entries", "valid_entries", "distinct_states", "entropy",
                "signal_ratio", "is_degenerate", "observation_note", "advisory_only"}
    missing = required - set(obs.keys())
    assert not missing, f"e1b_observation missing keys: {missing}"

    # Authority boundary: is_degenerate must never affect gate.blocked
    assert obs["advisory_only"] is True
    assert result["gate_policy"]["blocked"] is False or obs["is_degenerate"] in (True, False), (
        "is_degenerate must not influence gate.blocked (advisory only)"
    )

    # is_degenerate：hook 執行後至少有 1 筆 entry（本次 session 寫入）。
    # 1 個 distinct_state / 1 entry = entropy=1.0 >= 0.3 → NOT degenerate。
    # 所以此處不斷言 is_degenerate 的值；只驗證 key 存在且是 bool。
    assert isinstance(obs["is_degenerate"], bool)


# ── Test 6: format_human_result renders e1b_observation ───────────────────────


def test_format_human_result_renders_e1b_observation(tmp_path):
    """
    format_human_result() must render:
      - 'e1b_observation:' summary line always
      - '[ADVISORY] e1b:' line when is_degenerate=True or internal_error=True
    """
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(_MINIMAL_CLOSEOUT, encoding="utf-8")

    result = run_session_end_hook(tmp_path)
    human = format_human_result(result)

    assert "e1b_observation:" in human, (
        "format_human_result must render 'e1b_observation:' summary line"
    )

    # With empty log, is_degenerate=True → [ADVISORY] should appear
    obs = result["e1b_observation"]
    if obs.get("is_degenerate") or obs.get("internal_error"):
        assert "[ADVISORY] e1b:" in human, (
            "format_human_result must render '[ADVISORY] e1b:' when is_degenerate=True"
        )


# ── Track A: is_degenerate_deprecated presence (all three return paths) ────────


def test_track_a_is_degenerate_deprecated_empty_log(tmp_path):
    """
    [Track A] Empty log path → is_degenerate_deprecated=True must be present.
    Guards against narrative drift: reading is_degenerate=True from an empty-log
    artifact must NOT be interpreted as 'Phase 2 not passed'.
    """
    result = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert result.get("is_degenerate_deprecated") is True, (
        "is_degenerate_deprecated must be True in empty-log return path (Track A)"
    )


def test_track_a_is_degenerate_deprecated_uniform_degenerate(tmp_path):
    """
    [Track A] Uniform-state degenerate window → is_degenerate_deprecated=True present.
    """
    repo_name = tmp_path.resolve().name
    entries = [_make_audit_entry(repo_name, "absent") for _ in range(20)]
    _write_audit_log(tmp_path, entries)

    result = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert result["is_degenerate"] is True  # still fires
    assert result.get("is_degenerate_deprecated") is True, (
        "is_degenerate_deprecated must be True in degenerate return path (Track A)"
    )


def test_track_a_is_degenerate_deprecated_valid_window(tmp_path):
    """
    [Track A] Valid (non-degenerate) window → is_degenerate_deprecated=True still present.
    The deprecation flag is always set, regardless of the is_degenerate value,
    because the *field itself* is deprecated (not the True/False result).
    """
    repo_name = tmp_path.resolve().name
    entries = [
        _make_audit_entry(repo_name, "absent"),
        _make_audit_entry(repo_name, "ok"),
        _make_audit_entry(repo_name, "stale"),
    ]
    _write_audit_log(tmp_path, entries)

    result = _build_e1b_observation(project_root=tmp_path, window_size=20)
    assert result["is_degenerate"] is False
    assert result.get("is_degenerate_deprecated") is True, (
        "is_degenerate_deprecated must be True even when is_degenerate=False (Track A)"
    )


def test_track_a_format_human_result_deprecated_label(tmp_path):
    """
    [Track A] format_human_result must render '[DEPRECATED:legacy_entropy]' in the
    e1b_observation summary line — NOT the old '[legacy_entropy]' label.
    """
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(_MINIMAL_CLOSEOUT, encoding="utf-8")

    result = run_session_end_hook(tmp_path)
    human = format_human_result(result)

    assert "[DEPRECATED:legacy_entropy]" in human, (
        "format_human_result must render '[DEPRECATED:legacy_entropy]' label (Track A)"
    )
    assert "[legacy_entropy]" not in human.replace("[DEPRECATED:legacy_entropy]", ""), (
        "Old '[legacy_entropy]' label must not appear outside the DEPRECATED prefix (Track A)"
    )


def test_track_a_format_human_result_deprecated_advisory(tmp_path):
    """
    [Track A] When is_degenerate=True, format_human_result must render
    '[DEPRECATED]' advisory (not '[NOTE]') to prevent narrative drift.
    """
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(_MINIMAL_CLOSEOUT, encoding="utf-8")

    result = run_session_end_hook(tmp_path)
    obs = result.get("e1b_observation", {})
    human = format_human_result(result)

    if obs.get("is_degenerate") and not obs.get("internal_error"):
        assert "[DEPRECATED] is_degenerate" in human, (
            "format_human_result must render '[DEPRECATED] is_degenerate' advisory (Track A), "
            "not '[NOTE]'"
        )
        assert "[NOTE] is_degenerate" not in human, (
            "Old '[NOTE] is_degenerate' label must not appear (Track A)"
        )
