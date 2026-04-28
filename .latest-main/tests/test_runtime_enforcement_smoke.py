"""
Tests for governance_tools.runtime_enforcement_smoke.

Validates:
  1. All three enforcement checks pass on the real framework root (integration)
  2. Failure injection: monkeypatching a broken entrypoint causes ok=False
     and, with emit_risk_signal=True, writes to the risk signal
  3. Clean run with emit_risk_signal=True clears a pre-existing signal
  4. Signal uses the same framework_risk_signal mechanism (not a new file)
  5. Shared mechanism proof: signal written by enforcement smoke is readable
     by read_risk_signal and has correct component/source metadata

These tests are the "substrate extensibility proof":
  - two independent sources (governance_drift_checker + runtime_enforcement_smoke)
  - one shared signal mechanism (framework_risk_signal.py)
  - identical read/compute/clear consumer in session_start
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from governance_tools.framework_risk_signal import (
    clear_risk_signal,
    compute_overrides,
    read_risk_signal,
    write_risk_signal,
)
from governance_tools.framework_versioning import repo_root_from_tooling
from governance_tools.runtime_enforcement_smoke import (
    EnforcementSmokeResult,
    check_enforcement_boundary,
    format_human,
)

_FW_ROOT = repo_root_from_tooling()


@pytest.fixture(autouse=True)
def _clean_signal():
    clear_risk_signal(_FW_ROOT)
    yield
    clear_risk_signal(_FW_ROOT)


# ── Happy path: all checks pass on real framework ────────────────────────────

def test_all_checks_pass_on_framework_root() -> None:
    result = check_enforcement_boundary(_FW_ROOT)
    assert result.ok is True
    assert result.checks["pre_task_ok"] is True
    assert result.checks["session_start_ok"] is True
    assert result.checks["dispatch_ok"] is True
    assert result.errors == []


def test_no_signal_written_when_emit_false() -> None:
    result = check_enforcement_boundary(_FW_ROOT, emit_risk_signal=False)
    assert result.ok is True
    assert result.signal_written is False
    assert read_risk_signal(_FW_ROOT) is None


def test_all_pass_with_emit_clears_existing_signal() -> None:
    # Pre-write a stale signal
    write_risk_signal(_FW_ROOT, ["runtime_enforcement_entrypoint"], "critical", "prev")
    assert read_risk_signal(_FW_ROOT) is not None

    result = check_enforcement_boundary(_FW_ROOT, emit_risk_signal=True)
    assert result.ok is True
    assert result.signal_cleared is True
    assert read_risk_signal(_FW_ROOT) is None


# ── Format human output ───────────────────────────────────────────────────────

def test_format_human_shows_pass_checks() -> None:
    result = check_enforcement_boundary(_FW_ROOT)
    rendered = format_human(result)
    assert "[runtime_enforcement_smoke]" in rendered
    assert "ok=True" in rendered
    assert "pre_task_ok" in rendered
    assert "PASS" in rendered


# ── Failure injection: broken pre_task entrypoint ────────────────────────────

def test_pre_task_failure_sets_check_false(tmp_path: Path) -> None:
    def _bad_pre_task(**_kwargs):
        return {"ok": False, "errors": ["injected pre_task failure"]}

    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_pre_task_smoke",
        return_value=(False, "injected pre_task failure"),
    ):
        result = check_enforcement_boundary(_FW_ROOT)

    assert result.ok is False
    assert result.checks["pre_task_ok"] is False
    assert any("pre_task" in e for e in result.errors)


def test_session_start_failure_sets_check_false() -> None:
    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_session_start_smoke",
        return_value=(False, "injected session_start failure"),
    ):
        result = check_enforcement_boundary(_FW_ROOT)

    assert result.ok is False
    assert result.checks["session_start_ok"] is False


def test_dispatch_failure_sets_check_false() -> None:
    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_dispatch_smoke",
        return_value=(False, "injected dispatch failure"),
    ):
        result = check_enforcement_boundary(_FW_ROOT)

    assert result.ok is False
    assert result.checks["dispatch_ok"] is False


# ── Signal emission on failure ────────────────────────────────────────────────

def test_emit_writes_signal_on_pre_task_failure() -> None:
    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_pre_task_smoke",
        return_value=(False, "injected failure"),
    ):
        result = check_enforcement_boundary(_FW_ROOT, emit_risk_signal=True)

    assert result.signal_written is True
    signal = read_risk_signal(_FW_ROOT)
    assert signal is not None
    assert signal["source"] == "runtime_enforcement_smoke"
    assert "runtime_enforcement_entrypoint" in signal["affected_components"]


def test_emitted_signal_compute_overrides_returns_min_task_level() -> None:
    """Proof: enforcement-sourced signal produces same overrides as drift-sourced."""
    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_dispatch_smoke",
        return_value=(False, "injected failure"),
    ):
        check_enforcement_boundary(_FW_ROOT, emit_risk_signal=True)

    signal = read_risk_signal(_FW_ROOT)
    overrides = compute_overrides(signal)
    assert overrides.get("min_task_level") == "L1"


# ── Substrate extensibility proof ─────────────────────────────────────────────

def test_enforcement_and_drift_signals_share_mechanism() -> None:
    """
    Two sources write to the same signal file via framework_risk_signal.
    The last writer wins; the consumer (session_start) reads whoever wrote last.
    This proves the mechanism is source-agnostic.
    """
    # Source 1: drift checker (simulated)
    write_risk_signal(
        _FW_ROOT,
        affected_components=["drift_baseline_integrity"],
        severity="critical",
        source="governance_drift_checker",
    )
    sig_drift = read_risk_signal(_FW_ROOT)
    assert sig_drift["source"] == "governance_drift_checker"

    # Source 2: enforcement smoke (injected failure)
    with mock.patch(
        "governance_tools.runtime_enforcement_smoke._run_pre_task_smoke",
        return_value=(False, "injected"),
    ):
        check_enforcement_boundary(_FW_ROOT, emit_risk_signal=True)

    sig_enforcement = read_risk_signal(_FW_ROOT)
    assert sig_enforcement is not None
    assert sig_enforcement["source"] == "runtime_enforcement_smoke"
    assert "runtime_enforcement_entrypoint" in sig_enforcement["affected_components"]

    # Both produce actionable overrides via the same compute_overrides path
    overrides = compute_overrides(sig_enforcement)
    assert overrides.get("min_task_level") == "L1"
