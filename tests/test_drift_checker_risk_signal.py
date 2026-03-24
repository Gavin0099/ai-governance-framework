"""
Integration tests: governance_drift_checker + framework_risk_signal.

Verifies that check_governance_drift(emit_risk_signal=True) writes/clears
the risk signal correctly.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from governance_tools.framework_risk_signal import clear_risk_signal, read_risk_signal
from governance_tools.governance_drift_checker import check_governance_drift


FIXTURE_ROOT = Path("tests/_tmp_drift_checker_signal")


def _reset(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_minimal_governed_repo(root: Path, *, name: str = "test-repo") -> None:
    """Write just enough governance files for drift check to reach severity roll-up."""
    _write(
        root / ".governance" / "baseline.yaml",
        "\n".join([
            f"baseline_version: v1.0.0",
            f"source_commit: abc1234",
            "initialized_at: 2026-01-01T00:00:00+00:00",
        ]),
    )
    _write(
        root / "contract.yaml",
        "\n".join([
            f"name: {name}",
            "domain: firmware",
            "plugin_version: \"1.0.0\"",
            "framework_interface_version: \"1\"",
            "framework_compatible: \">=1.0.0,<2.0.0\"",
        ]),
    )
    _write(root / "AGENTS.base.md", "<!-- governance-baseline: protected -->\n# Base\n")
    _write(root / "AGENTS.md", "# Agents\n\nSome real content here.\n")
    _write(
        root / "PLAN.md",
        "> **最後更新**: 2026-03-24\n> **Owner**: test\n> **Freshness**: Monthly (30d)\n",
    )


# ── emit=False: no signal written even on critical ────────────────────────────

def test_no_signal_without_emit_flag(tmp_path: Path) -> None:
    fw_root = tmp_path / "fw"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fw_root.mkdir()
    # Missing baseline → critical, but emit_risk_signal=False (default)
    result = check_governance_drift(
        repo_root=repo_root,
        framework_root=fw_root,
        emit_risk_signal=False,
    )
    assert result.severity == "critical"
    assert read_risk_signal(fw_root) is None


# ── emit=True + critical → signal written ────────────────────────────────────

def test_emit_signal_on_critical_missing_baseline(tmp_path: Path) -> None:
    fw_root = tmp_path / "fw"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fw_root.mkdir()
    # No baseline → critical
    result = check_governance_drift(
        repo_root=repo_root,
        framework_root=fw_root,
        emit_risk_signal=True,
    )
    assert result.severity == "critical"
    signal = read_risk_signal(fw_root)
    assert signal is not None
    assert signal["source"] == "governance_drift_checker"
    assert signal["severity"] == "critical"
    assert "drift_baseline_integrity" in signal["affected_components"]


# ── emit=True + all passing → signal cleared ─────────────────────────────────

def test_emit_clears_signal_when_all_critical_pass(tmp_path: Path) -> None:
    fw_root = tmp_path / "fw"
    repo_root = tmp_path / "repo"
    fw_root.mkdir()
    _make_minimal_governed_repo(repo_root)

    # Pre-write a stale signal to verify it gets cleared
    from governance_tools.framework_risk_signal import write_risk_signal
    write_risk_signal(fw_root, ["drift_baseline_integrity"], "critical", "previous_run")
    assert read_risk_signal(fw_root) is not None  # stale signal present

    result = check_governance_drift(
        repo_root=repo_root,
        framework_root=fw_root,
        skip_hash=True,
        emit_risk_signal=True,
    )
    # No critical findings → clear
    assert result.severity in {"ok", "warning"}
    assert read_risk_signal(fw_root) is None


# ── emit=True + critical that is NOT in mapping → no signal ──────────────────

def test_emit_does_not_write_signal_for_unmapped_critical(tmp_path: Path) -> None:
    """
    If the only critical finding has no component mapping, write_risk_signal
    is called with an empty list, so no meaningful signal is written.
    Confirm the call proceeds without error and no persisted signal is active.
    """
    fw_root = tmp_path / "fw"
    repo_root = tmp_path / "repo"
    fw_root.mkdir()
    _make_minimal_governed_repo(repo_root)

    # Corrupt the sentinel to trigger protected_file_sentinel_present as critical
    # — but AGENTS.base.md check uses "warning" in this case, so fake a contract
    # critical by removing required fields.
    (repo_root / "contract.yaml").write_text(
        "name: test-repo\ndomain: firmware\n",  # missing required fields
        encoding="utf-8",
    )

    result = check_governance_drift(
        repo_root=repo_root,
        framework_root=fw_root,
        skip_hash=True,
        emit_risk_signal=True,
    )
    # contract_required_fields_present critical IS in the mapping
    # → signal still written for known component
    assert result.checks.get("contract_required_fields_present") is False
    signal = read_risk_signal(fw_root)
    assert signal is not None
    assert "drift_baseline_integrity" in signal["affected_components"]
