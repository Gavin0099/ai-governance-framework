"""
Integration tests: session_start reads the framework risk signal and applies task-level overrides.

Uses a real tmp framework root and KDC contract to exercise the full session_start pipeline.

Test scope note
───────────────
This file is included in the "filtered" pytest run (1301 tests across the controlled subset)
and excluded from the "full" suite (1337 tests) by the trust_signal / reviewer_handoff /
session_start_can_* / version_audit / governance_auditor / publication_reader exclusions in
the standard pytest invocation.  The difference (≈36) is the set of tests that depend on
external repos being present or involve long CI paths.  That count is documented here to
prevent future confusion between suite scopes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from governance_tools.framework_risk_signal import (
    clear_risk_signal,
    read_risk_signal,
    write_risk_signal,
)
from governance_tools.framework_versioning import repo_root_from_tooling
from runtime_hooks.core.session_start import build_session_start_context

_KDC_CONTRACT = Path("e:/BackUp/Git_EE/Kernel-Driver-Contract/contract.yaml")
_KDC_ROOT = _KDC_CONTRACT.parent

_FW_ROOT = repo_root_from_tooling()
_PLAN = _FW_ROOT / "PLAN.md"


def _base_kwargs(**overrides) -> dict:
    base = dict(
        project_root=_FW_ROOT,
        plan_path=_PLAN,
        rules="common",
        risk="low",
        oversight="auto",
        memory_mode="candidate",
        task_text="update a comment in the grammar file",  # generic; should be L0
        task_level=None,  # let auto-detection run
    )
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _no_lingering_signal():
    """Ensure any risk signal written during a test is cleaned up afterward."""
    clear_risk_signal(_FW_ROOT)
    yield
    clear_risk_signal(_FW_ROOT)


# ── no signal → no override ───────────────────────────────────────────────────

def test_no_signal_result_has_active_false() -> None:
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    assert result["risk_signal"]["active"] is False
    assert result["risk_signal"]["overrides"] == {}


def test_no_signal_task_level_unchanged() -> None:
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    assert result["task_level"] == "L0"


# ── active signal → min_task_level override ───────────────────────────────────

def test_active_signal_upgrades_l0_to_l1() -> None:
    write_risk_signal(
        _FW_ROOT,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    assert result["risk_signal"]["active"] is True
    assert result["task_level"] == "L1"


def test_active_signal_level_decision_shows_upgrade() -> None:
    write_risk_signal(
        _FW_ROOT,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    decision = result["level_decision"]
    assert decision["upgraded"] is True
    assert "risk_signal" in decision.get("upgrade_reason", "")
    assert decision["final"] == "L1"


def test_active_signal_does_not_downgrade_l2() -> None:
    """L2 is already above the L1 minimum — must not be downgraded."""
    write_risk_signal(
        _FW_ROOT,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L2"))
    assert result["task_level"] == "L2"


def test_active_signal_overrides_surfaced_in_result() -> None:
    write_risk_signal(
        _FW_ROOT,
        affected_components=["rule_selection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    overrides = result["risk_signal"]["overrides"]
    assert overrides.get("min_task_level") == "L1"


def test_active_signal_does_not_change_rules() -> None:
    """Risk signal must not alter rule packs — only task_level."""
    write_risk_signal(
        _FW_ROOT,
        affected_components=["rule_selection"],
        severity="critical",
        source="test_suite",
    )
    result_with_signal = build_session_start_context(
        **_base_kwargs(task_level="L1", rules="common")
    )
    clear_risk_signal(_FW_ROOT)
    result_without_signal = build_session_start_context(
        **_base_kwargs(task_level="L1", rules="common")
    )
    # Rule packs must be the same regardless of signal state
    rules_with = result_with_signal["runtime_contract"].get("rules", [])
    rules_without = result_without_signal["runtime_contract"].get("rules", [])
    assert rules_with == rules_without


# ── Observability: format_human_result() banner ───────────────────────────────

def test_format_human_result_has_no_banner_without_signal() -> None:
    from runtime_hooks.core.session_start import format_human_result
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    rendered = format_human_result(result)
    assert "FRAMEWORK RISK SIGNAL" not in rendered


def test_format_human_result_banner_is_first_when_signal_active() -> None:
    from runtime_hooks.core.session_start import format_human_result
    write_risk_signal(
        _FW_ROOT,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    rendered = format_human_result(result)
    first_line = rendered.splitlines()[0]
    assert first_line == "[FRAMEWORK RISK SIGNAL ACTIVE]"


def test_format_human_result_banner_includes_required_fields() -> None:
    from runtime_hooks.core.session_start import format_human_result
    write_risk_signal(
        _FW_ROOT,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(**_base_kwargs(task_level="L0"))
    rendered = format_human_result(result)
    assert "severity=critical" in rendered
    assert "source=test_suite" in rendered
    assert "task_level_detection" in rendered
    assert "min_task_level=L1" in rendered


# ── Protective behavior: suppress summary_first on compromised components ─────

def test_summary_first_gate_signal_disables_summary_first() -> None:
    """When summary_first_gate is affected, pre_task_check must load full document content."""
    _KDC = Path("e:/BackUp/Git_EE/Kernel-Driver-Contract/contract.yaml")
    if not _KDC.exists():
        pytest.skip("KDC contract not available")
    write_risk_signal(
        _FW_ROOT,
        affected_components=["summary_first_gate"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(
        **_base_kwargs(task_level="L1", contract_file=_KDC)
    )
    pre = result.get("pre_task_check", {})
    sf = pre.get("summary_first", {})
    # With the signal active, summary_first must be suppressed
    assert sf.get("active") is False, (
        f"Expected summary_first.active=False when summary_first_gate signal is set, "
        f"got: {sf}"
    )


def test_domain_contract_loading_signal_disables_summary_first() -> None:
    """domain_contract_loading component also triggers disable_summary_first."""
    _KDC = Path("e:/BackUp/Git_EE/Kernel-Driver-Contract/contract.yaml")
    if not _KDC.exists():
        pytest.skip("KDC contract not available")
    write_risk_signal(
        _FW_ROOT,
        affected_components=["domain_contract_loading"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(
        **_base_kwargs(task_level="L1", contract_file=_KDC)
    )
    pre = result.get("pre_task_check", {})
    sf = pre.get("summary_first", {})
    assert sf.get("active") is False


def test_unrelated_signal_component_does_not_disable_summary_first() -> None:
    """rule_selection signal must NOT suppress summary_first."""
    _KDC = Path("e:/BackUp/Git_EE/Kernel-Driver-Contract/contract.yaml")
    if not _KDC.exists():
        pytest.skip("KDC contract not available")
    write_risk_signal(
        _FW_ROOT,
        affected_components=["rule_selection"],
        severity="critical",
        source="test_suite",
    )
    result = build_session_start_context(
        **_base_kwargs(task_level="L1", contract_file=_KDC)
    )
    pre = result.get("pre_task_check", {})
    sf = pre.get("summary_first", {})
    # rule_selection does not include disable_summary_first, so it should remain active
    assert sf.get("active") is True
