"""
Unit tests for governance_tools.framework_risk_signal.

Exercises write/read/clear/compute_overrides in isolation using a tmp directory.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from governance_tools.framework_risk_signal import (
    KNOWN_COMPONENTS,
    clear_risk_signal,
    compute_overrides,
    read_risk_signal,
    write_risk_signal,
)


@pytest.fixture()
def fw_root(tmp_path: Path) -> Path:
    return tmp_path


# ── write / read ──────────────────────────────────────────────────────────────

def test_write_creates_signal_file(fw_root: Path) -> None:
    path = write_risk_signal(
        fw_root,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test",
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["severity"] == "critical"
    assert data["repo_scope"] == "framework"
    assert data["version"] == 1
    assert "task_level_detection" in data["affected_components"]


def test_read_returns_signal_when_fresh(fw_root: Path) -> None:
    write_risk_signal(
        fw_root,
        affected_components=["rule_selection"],
        severity="critical",
        source="test",
    )
    signal = read_risk_signal(fw_root)
    assert signal is not None
    assert signal["severity"] == "critical"
    assert "rule_selection" in signal["affected_components"]


def test_read_returns_none_when_no_file(fw_root: Path) -> None:
    assert read_risk_signal(fw_root) is None


def test_read_returns_none_on_corrupt_file(fw_root: Path) -> None:
    path = fw_root / "artifacts" / "runtime" / "framework_risk_signal.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert read_risk_signal(fw_root) is None


def test_read_returns_none_for_wrong_scope(fw_root: Path) -> None:
    path = fw_root / "artifacts" / "runtime" / "framework_risk_signal.json"
    path.parent.mkdir(parents=True)
    data = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "severity": "critical",
        "affected_components": ["rule_selection"],
        "source": "test",
        "repo_scope": "external",          # wrong scope
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert read_risk_signal(fw_root) is None


def test_read_returns_none_for_wrong_version(fw_root: Path) -> None:
    path = fw_root / "artifacts" / "runtime" / "framework_risk_signal.json"
    path.parent.mkdir(parents=True)
    data = {
        "version": 99,                    # unknown future version
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "severity": "critical",
        "affected_components": ["rule_selection"],
        "source": "test",
        "repo_scope": "framework",
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert read_risk_signal(fw_root) is None


def test_read_returns_none_when_expired(fw_root: Path) -> None:
    path = write_risk_signal(
        fw_root,
        affected_components=["drift_baseline_integrity"],
        severity="critical",
        source="test",
    )
    # Back-date the generated_at to 49 hours ago
    data = json.loads(path.read_text(encoding="utf-8"))
    old_time = datetime.now(timezone.utc) - timedelta(hours=49)
    data["generated_at"] = old_time.isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")

    assert read_risk_signal(fw_root, max_age_hours=48) is None


def test_read_returns_signal_just_within_expiry(fw_root: Path) -> None:
    path = write_risk_signal(
        fw_root,
        affected_components=["drift_baseline_integrity"],
        severity="critical",
        source="test",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    almost_old = datetime.now(timezone.utc) - timedelta(hours=47, minutes=59)
    data["generated_at"] = almost_old.isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")

    assert read_risk_signal(fw_root, max_age_hours=48) is not None


# ── unknown component filtering ───────────────────────────────────────────────

def test_unknown_components_are_filtered_on_write(fw_root: Path) -> None:
    path = write_risk_signal(
        fw_root,
        affected_components=["task_level_detection", "totally_fake_component"],
        severity="critical",
        source="test",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "totally_fake_component" not in data["affected_components"]
    assert "task_level_detection" in data["affected_components"]


def test_all_known_components_accepted(fw_root: Path) -> None:
    path = write_risk_signal(
        fw_root,
        affected_components=list(KNOWN_COMPONENTS),
        severity="critical",
        source="test",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data["affected_components"]) == KNOWN_COMPONENTS


# ── clear ─────────────────────────────────────────────────────────────────────

def test_clear_returns_true_when_file_exists(fw_root: Path) -> None:
    write_risk_signal(fw_root, affected_components=["rule_selection"], severity="critical", source="test")
    assert clear_risk_signal(fw_root) is True


def test_clear_removes_file(fw_root: Path) -> None:
    write_risk_signal(fw_root, affected_components=["rule_selection"], severity="critical", source="test")
    clear_risk_signal(fw_root)
    assert read_risk_signal(fw_root) is None


def test_clear_returns_false_when_no_file(fw_root: Path) -> None:
    assert clear_risk_signal(fw_root) is False


# ── compute_overrides ────────────────────────────────────────────────────────

def test_compute_overrides_empty_when_no_signal() -> None:
    assert compute_overrides(None) == {}


def test_compute_overrides_returns_min_task_level_for_known_components(fw_root: Path) -> None:
    write_risk_signal(
        fw_root,
        affected_components=["task_level_detection"],
        severity="critical",
        source="test",
    )
    signal = read_risk_signal(fw_root)
    overrides = compute_overrides(signal)
    assert overrides.get("min_task_level") == "L1"


def test_compute_overrides_conservative_merge_takes_highest_protection(fw_root: Path) -> None:
    # All current components map to L1; ensure the merge picks L1 (not lower).
    write_risk_signal(
        fw_root,
        affected_components=["task_level_detection", "domain_contract_loading", "drift_baseline_integrity"],
        severity="critical",
        source="test",
    )
    signal = read_risk_signal(fw_root)
    overrides = compute_overrides(signal)
    assert overrides["min_task_level"] == "L1"


def test_compute_overrides_empty_components_gives_empty_result() -> None:
    signal = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "severity": "critical",
        "affected_components": [],
        "source": "test",
        "repo_scope": "framework",
    }
    assert compute_overrides(signal) == {}


def test_compute_overrides_summary_first_gate_sets_disable_flag() -> None:
    write_risk_signal(
        fw_root := Path(__file__).parent / "_tmp_signal_test",
        affected_components=["summary_first_gate"],
        severity="critical",
        source="test",
    )
    sig = read_risk_signal(fw_root)
    overrides = compute_overrides(sig)
    assert overrides.get("disable_summary_first") is True
    import shutil; shutil.rmtree(fw_root, ignore_errors=True)


def test_compute_overrides_domain_contract_loading_sets_disable_flag(fw_root: Path) -> None:
    write_risk_signal(
        fw_root,
        affected_components=["domain_contract_loading"],
        severity="critical",
        source="test",
    )
    sig = read_risk_signal(fw_root)
    overrides = compute_overrides(sig)
    assert overrides.get("disable_summary_first") is True


def test_compute_overrides_rule_selection_does_not_set_disable_flag(fw_root: Path) -> None:
    write_risk_signal(
        fw_root,
        affected_components=["rule_selection"],
        severity="critical",
        source="test",
    )
    sig = read_risk_signal(fw_root)
    overrides = compute_overrides(sig)
    assert "disable_summary_first" not in overrides
