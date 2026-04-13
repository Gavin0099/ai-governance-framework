"""
tests/test_e9a_skip_test_result_check.py — E9a structural absence opt-out tests.

Five tests covering:
  1. skip=False + artifact absent  → test_result_artifact_absent signal present
  2. skip=True  + artifact absent  → signals=[], audit_note records structural declaration
  3. skip=True  + artifact present + failure_disposition_key absent
                                   → canonical_interpretation_missing still fires
  4. skip=True  + artifact present + failure_disposition_key present  → signals=[]
  5. run_session_end_hook with skip_test_result_check=True in gate_policy.yaml
     → canonical_path_audit.signals=[], gate.blocked unaffected

Scope note
----------
skip_test_result_check is an advisory surface opt-out.  It suppresses
test_result_artifact_absent when a repo structurally cannot produce test
artifacts (e.g. C++ firmware, documentation-only repos).  It never affects
gate.blocked — that boundary must remain intact across all five tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools.gate_policy import (
    ArtifactResult,
    ARTIFACT_STATE_ABSENT,
    ARTIFACT_STATE_OK,
)
from governance_tools.session_end_hook import _build_canonical_path_audit


# ── Helpers ───────────────────────────────────────────────────────────────────


def _absent_result() -> ArtifactResult:
    """Minimal ArtifactResult with state=absent (no artifact on disk)."""
    return ArtifactResult(
        state=ARTIFACT_STATE_ABSENT,
        failure_disposition=None,
        failure_disposition_key_present=False,
    )


def _present_result(*, key_present: bool) -> ArtifactResult:
    """ArtifactResult with state=ok; key_present controls canonical footprint."""
    return ArtifactResult(
        state=ARTIFACT_STATE_OK,
        failure_disposition=None,
        failure_disposition_key_present=key_present,
    )


# ── Test 1: skip=False + absent → signal emitted ─────────────────────────────


def test_skip_false_absent_emits_signal():
    """
    When skip_test_result_check=False (default) and the artifact is absent,
    test_result_artifact_absent must appear in signals.
    """
    result = _build_canonical_path_audit(_absent_result(), skip_test_result_check=False)

    assert "test_result_artifact_absent" in result["signals"], (
        "Expected test_result_artifact_absent when skip=False and artifact absent"
    )
    assert result["artifact_present"] is False
    assert result["skip_test_result_check"] is False


# ── Test 2: skip=True + absent → no signal, audit_note records declaration ───


def test_skip_true_absent_suppresses_signal_and_records_note():
    """
    When skip_test_result_check=True and the artifact is absent, signals must
    be empty and audit_note must record the structural absence declaration.
    The skip_test_result_check key in the return dict must be True.
    """
    result = _build_canonical_path_audit(_absent_result(), skip_test_result_check=True)

    assert result["signals"] == [], (
        f"Expected no signals when skip=True and artifact absent; got {result['signals']}"
    )
    assert "skipped" in result["audit_note"].lower(), (
        f"Expected audit_note to mention 'skipped'; got: {result['audit_note']!r}"
    )
    assert result["artifact_present"] is False
    assert result["skip_test_result_check"] is True


# ── Test 3: skip=True + present + key absent → canonical_interpretation_missing ─


def test_skip_true_present_key_absent_still_fires_canonical_signal():
    """
    skip_test_result_check only suppresses the *absent-artifact* path.
    When the artifact is present but lacks the failure_disposition key,
    canonical_interpretation_missing must still be emitted regardless of skip.
    """
    result = _build_canonical_path_audit(
        _present_result(key_present=False), skip_test_result_check=True
    )

    assert "canonical_interpretation_missing" in result["signals"], (
        "Expected canonical_interpretation_missing when artifact present but key absent"
    )
    assert result["artifact_present"] is True
    assert result["skip_test_result_check"] is True


# ── Test 4: skip=True + present + key present → clean (no signals) ───────────


def test_skip_true_present_key_present_no_signals():
    """
    When skip=True but the artifact is present and the failure_disposition key
    exists, the canonical path footprint is confirmed — signals must be empty.
    """
    result = _build_canonical_path_audit(
        _present_result(key_present=True), skip_test_result_check=True
    )

    assert result["signals"] == [], (
        f"Expected no signals when artifact present with canonical key; got {result['signals']}"
    )
    assert result["artifact_present"] is True
    assert result["failure_disposition_key_present"] is True
    assert result["skip_test_result_check"] is True


# ── Test 5: run_session_end_hook with skip=True in gate_policy ───────────────


def test_run_session_end_hook_with_skip_policy_suppresses_signal_and_does_not_affect_gate(
    tmp_path: Path,
):
    """
    With skip_test_result_check=true in gate_policy.yaml and no test artifact:
    - canonical_path_audit.signals must be []
    - canonical_path_audit.skip_test_result_check must be True
    - gate.blocked must remain False (skip never contributes to gate)
    - canonical_path_audit.audit_note must record structural declaration

    Advisory boundary: the absence of a test_result_artifact_absent signal
    here is intentional and declared.  gate.blocked is independent of this flag.
    """
    from governance_tools.session_end_hook import run_session_end_hook

    # Write a minimal valid closeout.
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

    # Write a gate_policy.yaml with skip_test_result_check=true.
    gov = tmp_path / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "gate_policy.yaml").write_text(
        "fail_mode: warn\nskip_test_result_check: true\n", encoding="utf-8"
    )

    result = run_session_end_hook(tmp_path)

    # canonical_path_audit must be present.
    assert "canonical_path_audit" in result, (
        "run_session_end_hook result must contain canonical_path_audit"
    )
    cpa = result["canonical_path_audit"]

    # Signal suppressed by structural declaration.
    assert cpa["signals"] == [], (
        f"Expected no signals with skip=True; got {cpa['signals']}"
    )
    assert cpa.get("skip_test_result_check") is True, (
        "canonical_path_audit must carry skip_test_result_check=True for format_human_result"
    )
    assert "skipped" in cpa.get("audit_note", "").lower(), (
        f"Expected audit_note to record structural declaration; got: {cpa.get('audit_note')!r}"
    )

    # Gate boundary: skip never contributes to gate.blocked.
    gp = result.get("gate_policy") or {}
    assert gp.get("blocked") is False, (
        f"gate.blocked must be False — skip_test_result_check must never affect gate; "
        f"got blocked={gp.get('blocked')}"
    )
