"""
F5 — gate_verdict semantics + operator-facing output labels

Tests verify:
  F5a: _compute_gate_verdict() returns the correct verdict tier for each
       combination of ok / gate_blocked / warnings / errors.
  F5a: run_session_end_hook() result dict carries a 'gate_verdict' key.
  F5a: format_human_result() shows gate_verdict as a prominent top-level line.
  F5a: format_human_result() emits a reading guide when verdict=NON-GATE-FAILURE.
  F5b: _semantic_warning_label() maps advisory prefixes → 'ADVISORY'.
  F5b: _semantic_error_label() maps gate error prefixes → 'BLOCKED'.
  F5b: format_human_result() output uses [ADVISORY]/[BLOCKED] labels, not
       the old plain "warning: " / "error: " prefix.
"""

import pytest

from governance_tools.session_end_hook import (
    _compute_gate_verdict,
    _semantic_error_label,
    _semantic_warning_label,
    format_human_result,
    GATE_VERDICT_BLOCKED,
    GATE_VERDICT_NON_GATE_FAILURE,
    GATE_VERDICT_OK,
    GATE_VERDICT_OK_WITH_ADVISORIES,
)


# ── F5a: _compute_gate_verdict() classification ────────────────────────────

class TestComputeGateVerdict:
    def test_blocked_when_gate_blocked(self):
        v = _compute_gate_verdict(ok=False, gate_blocked=True, warnings=[], errors=[])
        assert v == GATE_VERDICT_BLOCKED

    def test_blocked_when_errors_present(self):
        v = _compute_gate_verdict(ok=False, gate_blocked=False, warnings=[], errors=["[GATE:production_fix_required] ..."])
        assert v == GATE_VERDICT_BLOCKED

    def test_blocked_when_gate_blocked_takes_priority_over_ok_true(self):
        # Logically ok=True with gate_blocked=True should not happen in practice,
        # but _compute_gate_verdict must handle it defensively.
        v = _compute_gate_verdict(ok=True, gate_blocked=True, warnings=[], errors=[])
        assert v == GATE_VERDICT_BLOCKED

    def test_non_gate_failure_tier_b_no_closeout(self):
        # Tier B: ok=False because closeout is missing, gate is not blocked.
        v = _compute_gate_verdict(ok=False, gate_blocked=False, warnings=["[closeout_evaluation:closeout_missing_tier_b] ..."], errors=[])
        assert v == GATE_VERDICT_NON_GATE_FAILURE

    def test_non_gate_failure_with_no_warnings(self):
        v = _compute_gate_verdict(ok=False, gate_blocked=False, warnings=[], errors=[])
        assert v == GATE_VERDICT_NON_GATE_FAILURE

    def test_ok_with_advisories_when_clean_ok_has_warnings(self):
        v = _compute_gate_verdict(ok=True, gate_blocked=False, warnings=["[gate_policy:signal] taxonomy..."], errors=[])
        assert v == GATE_VERDICT_OK_WITH_ADVISORIES

    def test_ok_when_fully_clean(self):
        v = _compute_gate_verdict(ok=True, gate_blocked=False, warnings=[], errors=[])
        assert v == GATE_VERDICT_OK


# ── F5a: format_human_result() gate_verdict display ───────────────────────

def _make_minimal_result(**overrides):
    base = {
        "ok": True,
        "gate_verdict": GATE_VERDICT_OK,
        "session_id": "test-session",
        "closeout_status": "present",
        "memory_tier": "A",
        "hook_coverage_tier": "A",
        "closeout_evaluation": {},
        "repo_readiness_level": "full",
        "repo_readiness_limiting_factor": None,
        "repo_closeout_activation_state": "active",
        "repo_activation_recency": None,
        "repo_activation_gap": None,
        "closeout_classification": {},
        "per_layer_results": {},
        "failure_signals": [],
        "failure_disposition": None,
        "gate_policy": {"blocked": False, "fail_mode": "advisory", "artifact_state": "absent",
                        "policy_source": "default", "policy_path": None,
                        "fallback_used": True, "repo_policy_present": False},
        "closeout_file": "/tmp/CLOSEOUT.md",
        "decision": "proceed",
        "snapshot_created": False,
        "promoted": False,
        "memory_closeout": None,
        "verdict_artifact": None,
        "trace_artifact": None,
        "canonical_path_audit": None,
        "canonical_audit_trend": None,
        "canonical_usage_audit": None,
        "taxonomy_expansion_log_entry": None,
        "warnings": [],
        "errors": [],
    }
    base.update(overrides)
    return base


class TestFormatHumanResultGateVerdict:
    def test_gate_verdict_appears_prominently(self):
        result = _make_minimal_result(gate_verdict=GATE_VERDICT_OK)
        output = format_human_result(result)
        assert "gate_verdict=OK" in output

    def test_gate_verdict_appears_before_session_id(self):
        result = _make_minimal_result(gate_verdict=GATE_VERDICT_OK)
        output = format_human_result(result)
        lines = output.splitlines()
        gv_idx = next(i for i, l in enumerate(lines) if "gate_verdict=" in l)
        sid_idx = next(i for i, l in enumerate(lines) if "session_id=" in l)
        assert gv_idx < sid_idx, "gate_verdict must appear before session_id"

    def test_non_gate_failure_shows_reading_guide(self):
        result = _make_minimal_result(
            ok=False,
            gate_verdict=GATE_VERDICT_NON_GATE_FAILURE,
        )
        output = format_human_result(result)
        assert "gate_verdict=NON-GATE-FAILURE" in output
        assert "non-gate issue" in output
        assert "gate_policy.blocked=False" in output

    def test_blocked_does_not_show_non_gate_reading_guide(self):
        result = _make_minimal_result(
            ok=False,
            gate_verdict=GATE_VERDICT_BLOCKED,
            gate_policy={"blocked": True, "fail_mode": "strict", "artifact_state": "absent",
                         "policy_source": "default", "policy_path": None,
                         "fallback_used": False, "repo_policy_present": True},
        )
        output = format_human_result(result)
        assert "gate_verdict=BLOCKED" in output
        assert "non-gate issue" not in output

    def test_gate_verdict_computed_inline_when_missing_from_dict(self):
        # result without gate_verdict key — format_human_result should compute it.
        result = _make_minimal_result()
        del result["gate_verdict"]
        output = format_human_result(result)
        assert "gate_verdict=OK" in output


# ── F5b: semantic label helpers ────────────────────────────────────────────

class TestSemanticWarningLabel:
    @pytest.mark.parametrize("prefix", [
        "[gate_policy:signal]",
        "[gate_policy:audit]",
        "[gate_policy]",
        "[closeout_evaluation:closeout_missing_tier_b]",
        "[canonical_path_audit]",
        "[canonical_audit_trend]",
        "[taxonomy_expansion_log]",
    ])
    def test_known_advisory_prefixes_return_advisory(self, prefix):
        label = _semantic_warning_label(f"{prefix} some detail")
        assert label == "ADVISORY"

    def test_unknown_prefix_returns_warning(self):
        label = _semantic_warning_label("unexpected format: something happened")
        assert label == "WARNING"


class TestSemanticErrorLabel:
    @pytest.mark.parametrize("prefix", [
        "[GATE:production_fix_required]",
        "[GATE:unknown]",
        "[gate_policy:strict]",
    ])
    def test_gate_prefixes_return_blocked(self, prefix):
        label = _semantic_error_label(f"{prefix} some detail")
        assert label == "BLOCKED"

    def test_unknown_error_prefix_returns_error(self):
        label = _semantic_error_label("unexpected error message")
        assert label == "ERROR"


# ── F5b: format_human_result() semantic output labels ─────────────────────

class TestFormatHumanResultSemanticLabels:
    def test_advisory_warning_uses_advisory_label(self):
        result = _make_minimal_result(
            ok=True,
            gate_verdict=GATE_VERDICT_OK_WITH_ADVISORIES,
            warnings=["[gate_policy:signal] taxonomy_expansion_signal exceeded threshold"],
        )
        output = format_human_result(result)
        assert "[ADVISORY] [gate_policy:signal]" in output
        # Must NOT use the old raw prefix
        assert "warning: [gate_policy:signal]" not in output

    def test_unknown_warning_uses_warning_label(self):
        result = _make_minimal_result(
            ok=True,
            gate_verdict=GATE_VERDICT_OK_WITH_ADVISORIES,
            warnings=["something unexpected happened"],
        )
        output = format_human_result(result)
        assert "[WARNING] something unexpected happened" in output

    def test_gate_error_uses_blocked_label(self):
        result = _make_minimal_result(
            ok=False,
            gate_verdict=GATE_VERDICT_BLOCKED,
            errors=["[GATE:production_fix_required] test artifact missing"],
            gate_policy={"blocked": True, "fail_mode": "strict", "artifact_state": "absent",
                         "policy_source": "default", "policy_path": None,
                         "fallback_used": False, "repo_policy_present": True},
        )
        output = format_human_result(result)
        assert "[BLOCKED] [GATE:production_fix_required]" in output
        # Must NOT use the old raw prefix
        assert "error: [GATE:" not in output

    def test_no_old_warning_prefix_in_output(self):
        result = _make_minimal_result(
            warnings=["[gate_policy] repo_local_policy_missing"],
        )
        output = format_human_result(result)
        assert "warning: " not in output
        assert "error: " not in output
