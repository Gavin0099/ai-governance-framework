"""
tests/test_session_end_canonical_audit.py — E7 canonical path usage audit tests.

Five tests covering two layers:
  - _build_canonical_path_audit() pure function behaviour (tests 1–3)
  - run_session_end_hook() result schema (test 4)
  - format_human_result() advisory rendering (test 5)

Signal semantics under test:

  test_result_artifact_absent
      ArtifactResult.state == "absent"
      → artifact_present=False, failure_disposition_key_present=False

  canonical_interpretation_missing
      ArtifactResult.state == "ok", failure_disposition_key_present=False
      (artifact exists but was not produced by canonical ingestor)

  No signal (clean path)
      ArtifactResult.state == "ok", failure_disposition_key_present=True
      (canonical ingestor ran; value may be null when no failures)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from governance_tools.gate_policy import (
    ARTIFACT_STATE_ABSENT,
    ARTIFACT_STATE_OK,
    ArtifactResult,
)
from governance_tools.session_end_hook import (
    _build_canonical_path_audit,
    format_human_result,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_artifact_result(
    state: str,
    failure_disposition: dict | None = None,
    failure_disposition_key_present: bool = False,
) -> ArtifactResult:
    return ArtifactResult(
        state=state,
        failure_disposition=failure_disposition,
        failure_disposition_key_present=failure_disposition_key_present,
    )


def _minimal_hook_result(*, canonical_path_audit: dict, blocked: bool = False) -> dict:
    """Minimal result dict consumed by format_human_result."""
    return {
        "ok": not blocked,
        "session_id": "session-test-000000",
        "closeout_status": "valid",
        "memory_tier": "working_state_update",
        "repo_readiness_level": "L1",
        "repo_readiness_limiting_factor": None,
        "repo_closeout_activation_state": "active",
        "repo_activation_recency": None,
        "repo_activation_gap": None,
        "closeout_classification": {
            "presence": "ok",
            "schema_validity": "ok",
            "content_sufficiency": "ok",
            "evidence_consistency": "ok",
        },
        "per_layer_results": {},
        "failure_signals": [],
        "failure_disposition": None,
        "gate_policy": {
            "fail_mode": "strict",
            "artifact_state": "ok",
            "blocked": blocked,
            "policy_source": "framework_default",
            "policy_path": "",
            "fallback_used": False,
            "repo_policy_present": False,
        },
        "canonical_path_audit": canonical_path_audit,
        "closeout_file": "artifacts/session-closeout.txt",
        "decision": "promote",
        "snapshot_created": False,
        "promoted": True,
        "memory_closeout": {"decision": "promote", "reason": "test"},
        "verdict_artifact": None,
        "trace_artifact": None,
        "warnings": [],
        "errors": [],
    }


# ── Test 1: artifact absent → signal test_result_artifact_absent ──────────────


def test_canonical_path_audit_emits_artifact_absent_signal_when_artifact_state_absent():
    """When artifact is absent, audit must emit test_result_artifact_absent signal."""
    ar = _make_artifact_result(state=ARTIFACT_STATE_ABSENT)

    audit = _build_canonical_path_audit(ar)

    assert audit["artifact_present"] is False
    assert audit["failure_disposition_key_present"] is False
    assert audit["failure_disposition_present"] is False
    assert "test_result_artifact_absent" in audit["signals"]
    assert "canonical_interpretation_missing" not in audit["signals"]
    assert audit["audit_note"], "audit_note must be non-empty"


# ── Test 2: artifact present + key present → no signal ───────────────────────


def test_canonical_path_audit_has_no_signal_when_failure_disposition_key_present():
    """
    When artifact is present and failure_disposition key exists (value may be
    null — valid canonical output when no failing tests), no signal is emitted.
    """
    # Case A: key present, value non-null (failures classified)
    ar_with_value = _make_artifact_result(
        state=ARTIFACT_STATE_OK,
        failure_disposition={"total": 3, "verdict_blocked": False},
        failure_disposition_key_present=True,
    )
    audit_a = _build_canonical_path_audit(ar_with_value)
    assert audit_a["signals"] == [], f"Expected no signals for non-null disposition: {audit_a['signals']}"
    assert audit_a["artifact_present"] is True
    assert audit_a["failure_disposition_key_present"] is True
    assert audit_a["failure_disposition_present"] is True

    # Case B: key present, value null (no failures — still canonical)
    ar_null_value = _make_artifact_result(
        state=ARTIFACT_STATE_OK,
        failure_disposition=None,
        failure_disposition_key_present=True,
    )
    audit_b = _build_canonical_path_audit(ar_null_value)
    assert audit_b["signals"] == [], (
        "Null failure_disposition with key_present=True must NOT trigger "
        f"canonical_interpretation_missing: {audit_b['signals']}"
    )
    assert audit_b["failure_disposition_key_present"] is True
    assert audit_b["failure_disposition_present"] is True  # key is present even if value is null


# ── Test 3: artifact present, key absent → canonical_interpretation_missing ───


def test_canonical_path_audit_emits_interpretation_missing_when_artifact_present_but_key_absent():
    """
    When artifact file exists (state=ok) but failure_disposition key is absent
    from the JSON, emit canonical_interpretation_missing — artifact was not
    produced by the canonical ingestor.
    """
    ar = _make_artifact_result(
        state=ARTIFACT_STATE_OK,
        failure_disposition=None,
        failure_disposition_key_present=False,  # key absent from JSON
    )

    audit = _build_canonical_path_audit(ar)

    assert audit["artifact_present"] is True
    assert audit["failure_disposition_key_present"] is False
    assert audit["failure_disposition_present"] is False
    assert "canonical_interpretation_missing" in audit["signals"], (
        f"Expected canonical_interpretation_missing signal: {audit['signals']}"
    )
    assert "test_result_artifact_absent" not in audit["signals"]


# ── Test 4: run_session_end_hook result includes canonical_path_audit key ─────


def test_run_session_end_hook_result_includes_canonical_path_audit(tmp_path):
    """
    run_session_end_hook() must include a 'canonical_path_audit' key in the
    result dict with the required sub-keys.
    """
    from governance_tools.session_end_hook import run_session_end_hook

    # Write a minimal valid closeout file so the hook can proceed past presence check.
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

    assert "canonical_path_audit" in result, (
        "run_session_end_hook() result must contain 'canonical_path_audit' key"
    )
    cpa = result["canonical_path_audit"]
    required_keys = {
        "artifact_present",
        "failure_disposition_key_present",
        "failure_disposition_present",
        "signals",
        "audit_note",
    }
    missing = required_keys - set(cpa.keys())
    assert not missing, f"canonical_path_audit missing keys: {missing}"

    # With no test-result artifact, expect test_result_artifact_absent signal.
    assert "test_result_artifact_absent" in cpa["signals"], (
        f"Expected test_result_artifact_absent in signals when no artifact: {cpa['signals']}"
    )


# ── Test 5: format_human_result renders canonical_path_audit advisory ─────────


def test_format_human_result_renders_canonical_path_audit_advisory():
    """
    format_human_result() must include [ADVISORY] lines when
    canonical_path_audit has signals, and must NOT include them when signals is empty.
    """
    # With advisory signal
    audit_with_signal = {
        "artifact_present": False,
        "failure_disposition_key_present": False,
        "failure_disposition_present": False,
        "signals": ["test_result_artifact_absent"],
        "audit_note": "test result artifact absent at session boundary",
    }
    output_with = format_human_result(_minimal_hook_result(canonical_path_audit=audit_with_signal))
    assert "[ADVISORY]" in output_with, (
        "format_human_result must display [ADVISORY] when signals present"
    )
    assert "test_result_artifact_absent" in output_with, (
        "Signal code must appear in human output"
    )
    assert "canonical_path_audit:" in output_with

    # Without advisory signal (clean canonical path)
    audit_clean = {
        "artifact_present": True,
        "failure_disposition_key_present": True,
        "failure_disposition_present": True,
        "signals": [],
        "audit_note": "canonical interpretation footprint present (no failures to classify)",
    }
    output_clean = format_human_result(_minimal_hook_result(canonical_path_audit=audit_clean))
    assert "[ADVISORY]" not in output_clean, (
        "format_human_result must NOT display [ADVISORY] when signals is empty"
    )
    # But the audit summary line should still appear (advisory is suppressed, not the whole section)
    assert "canonical_path_audit:" in output_clean
