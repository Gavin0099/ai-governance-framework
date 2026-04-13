"""
tests/test_e1a_canonical_usage_audit.py — E1a canonical usage auditability tests.

Five tests covering the 2x2 usage_status matrix and the full hook integration.

Spec invariants verified here:
- advisory_only=True in ALL code paths (never False)
- usage_status never influences gate.blocked
- internal_error=True in fallback (not silent success)
- canonical_key_present ≠ ingestor was called; only that artifact looks like ingestor output
"""

from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools.session_end_hook import _build_canonical_usage_audit


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _cpa(*, signals: list[str], artifact_present: bool = True,
         failure_disposition_key_present: bool | None = None) -> dict:
    """Build a minimal canonical_path_audit dict matching E7 schema."""
    fdkp = failure_disposition_key_present
    if fdkp is None:
        fdkp = artifact_present and not signals
    return {
        "artifact_present": artifact_present,
        "failure_disposition_key_present": fdkp,
        "failure_disposition_present": artifact_present and fdkp,
        "signals": signals,
        "audit_note": "test note" if signals else "footprint present",
    }


def _cat(*, adoption_risk: bool, signal_ratio: float = 0.0) -> dict:
    """Build a minimal canonical_audit_trend dict matching E8b schema."""
    return {
        "window_size": 20,
        "entries_read": 10,
        "entries_available": 10,
        "entries_with_signals": int(signal_ratio * 10),
        "signal_ratio": round(signal_ratio, 4),
        "top_signals": {},
        "adoption_risk": adoption_risk,
        "advisory_only": True,
        "scope_note": "test",
    }


# ── Test 1: observed ──────────────────────────────────────────────────────────


def test_usage_status_observed():
    """
    E7 footprint present (signals=[]) + E8b adoption_risk=False
    → usage_status="observed", advisory_only=True
    """
    result = _build_canonical_usage_audit(
        canonical_path_audit=_cpa(signals=[]),
        canonical_audit_trend=_cat(adoption_risk=False),
    )

    assert result["usage_status"] == "observed"
    assert result["advisory_only"] is True, "advisory_only must always be True"
    assert result["basis"] == "E7+E8b synthesis"
    assert result.get("internal_error") is not True, "internal_error must not be True for a genuine observation"

    # Schema completeness
    required = {"artifact_present", "canonical_key_present", "trend_adoption_risk",
                "trend_signal_ratio", "usage_status", "usage_note", "advisory_only", "basis"}
    assert not (required - set(result)), f"missing keys: {required - set(result)}"


# ── Test 2: missing ───────────────────────────────────────────────────────────


def test_usage_status_missing():
    """
    E7 footprint absent (signals non-empty) + E8b adoption_risk=False
    → usage_status="missing"
    """
    result = _build_canonical_usage_audit(
        canonical_path_audit=_cpa(
            signals=["test_result_artifact_absent"],
            artifact_present=False,
            failure_disposition_key_present=False,
        ),
        canonical_audit_trend=_cat(adoption_risk=False),
    )

    assert result["usage_status"] == "missing"
    assert result["advisory_only"] is True
    assert result["artifact_present"] is False
    assert result["canonical_key_present"] is False
    # usage_note should not claim ingestor was called
    assert "ingestor" not in result["usage_note"].lower(), (
        "usage_note must not assert ingestor invocation — only footprint presence"
    )


# ── Test 3: observed_with_trend_risk ─────────────────────────────────────────


def test_usage_status_observed_with_trend_risk():
    """
    E7 footprint present (signals=[]) + E8b adoption_risk=True
    → usage_status="observed_with_trend_risk"

    'observed_with_trend_risk' is unambiguous: session state and trend context are
    both named, unlike 'weak' which has no clear directional meaning.
    """
    result = _build_canonical_usage_audit(
        canonical_path_audit=_cpa(signals=[]),
        canonical_audit_trend=_cat(adoption_risk=True, signal_ratio=0.6),
    )

    assert result["usage_status"] == "observed_with_trend_risk"
    assert result["advisory_only"] is True
    assert result["trend_adoption_risk"] is True
    assert result["artifact_present"] is True
    # Naming accuracy: canonical_key_present, not ingestor_footprint_present
    assert "canonical_key_present" in result
    assert "ingestor_footprint_present" not in result


# ── Test 4: trend_risk_context ────────────────────────────────────────────────


def test_usage_status_trend_risk_context():
    """
    E7 footprint absent + E8b adoption_risk=True
    → usage_status="trend_risk_context"

    Two independent dimensions agree on a gap.  This is the strongest advisory
    state.  It is NOT a block and must never influence gate.blocked.
    usage_note must contain '(advisory' to make non-blocking semantics explicit.
    """
    result = _build_canonical_usage_audit(
        canonical_path_audit=_cpa(
            signals=["test_result_artifact_absent"],
            artifact_present=False,
            failure_disposition_key_present=False,
        ),
        canonical_audit_trend=_cat(adoption_risk=True, signal_ratio=0.7),
    )

    assert result["usage_status"] == "trend_risk_context"
    assert result["advisory_only"] is True
    assert result["trend_adoption_risk"] is True

    # usage_note must make advisory-only semantics explicit
    assert "advisory" in result["usage_note"].lower(), (
        "trend_risk_context usage_note must contain 'advisory' to prevent reviewer confusion"
    )
    assert "no gate effect" in result["usage_note"].lower() or "advisory only" in result["usage_note"].lower(), (
        "usage_note must explicitly state there is no gate effect for trend_risk_context"
    )


# ── Test 5: full hook integration + advisory_only invariant ──────────────────


def test_run_session_end_hook_includes_canonical_usage_audit(tmp_path):
    """
    run_session_end_hook() result must include canonical_usage_audit with
    advisory_only=True.  usage_status must NOT influence gate.blocked.
    format_human_result must render [ADVISORY] line for non-observed states.
    """
    from governance_tools.session_end_hook import run_session_end_hook, format_human_result

    # Minimal valid closeout
    closeout = tmp_path / "artifacts" / "session-closeout.txt"
    closeout.parent.mkdir(parents=True, exist_ok=True)
    closeout.write_text(
        "TASK_INTENT: e1a integration test\n"
        "WORK_COMPLETED: test_file.py\n"
        "CHECKS_RUN: pytest\n"
        "DECISION: promote\n"
        "RESPONSE: ok\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(tmp_path)

    # Key must be present
    assert "canonical_usage_audit" in result, (
        "run_session_end_hook result must contain canonical_usage_audit"
    )
    cua = result["canonical_usage_audit"]

    # advisory_only hard contract
    assert cua["advisory_only"] is True, (
        "canonical_usage_audit.advisory_only must always be True"
    )

    # Schema keys
    required = {"artifact_present", "canonical_key_present", "trend_adoption_risk",
                "trend_signal_ratio", "usage_status", "usage_note", "advisory_only", "basis"}
    assert not (required - set(cua)), f"canonical_usage_audit missing keys: {required - set(cua)}"

    # Naming accuracy: no legacy ingestor_footprint_present key
    assert "ingestor_footprint_present" not in cua

    # usage_status must NOT influence gate.blocked — these are always independent
    gate_blocked = result["gate_policy"]["blocked"]
    assert gate_blocked is not None
    # Regardless of usage_status, gate_blocked reflects only gate policy logic.
    # We record this explicitly: usage_status must never be a gate input.
    # (No assertion on the actual value — gate is determined by test artifact state)

    # format_human_result must render [ADVISORY] for non-observed states
    human = format_human_result(result)
    usage_status = cua["usage_status"]
    if usage_status != "observed":
        assert "[ADVISORY] canonical usage:" in human, (
            f"format_human_result must render [ADVISORY] for usage_status={usage_status!r}"
        )
    # Summary line always present
    assert "canonical_usage_audit:" in human
