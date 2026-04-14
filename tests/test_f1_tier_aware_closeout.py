"""
test_f1_tier_aware_closeout.py — F1 Tier-Aware Closeout Contract

Tests:
  1. Policy parsing: valid A/B/C tiers parsed correctly
  2. Policy parsing: invalid tier value → ValueError (config error, not silent)
  3. Policy parsing: missing tier → None
  4. Closeout eval: Tier A + missing closeout → ok=False, signal=closeout_file_missing
  5. Closeout eval: Tier B + missing closeout → ok unchanged, signal=closeout_missing_tier_b
  6. Closeout eval: Tier C + missing closeout → ok unchanged, no signal
  7. Closeout eval: undeclared tier + missing closeout → ok=False, two signals
  8. Closeout eval: Tier B + closeout present+valid → ok=True, clean pass
  9. Artifact visibility: result contains hook_coverage_tier + closeout_evaluation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.gate_policy import load_policy
from governance_tools.session_end_hook import (
    run_session_end_hook,
    _evaluate_closeout_by_tier,
    STATUS_MISSING,
    STATUS_VALID,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_policy(tmp_path: Path, **fields) -> Path:
    policy_dir = tmp_path / "governance"
    policy_dir.mkdir(parents=True, exist_ok=True)
    p = policy_dir / "gate_policy.yaml"
    lines = ["version: '1'\n", "fail_mode: audit\n"]  # audit so gate never blocks
    for k, v in fields.items():
        lines.append(f"{k}: {v}\n")
    p.write_text("".join(lines), encoding="utf-8")
    return p


def _write_closeout(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "session-closeout.txt").write_text(
        "TASK_INTENT: run f1 tests for governance_tools\n"
        "WORK_COMPLETED: test_f1_tier_aware_closeout.py added\n"
        "FILES_TOUCHED: tests/test_f1_tier_aware_closeout.py\n"
        "CHECKS_RUN: pytest tests/test_f1_tier_aware_closeout.py\n"
        "OPEN_RISKS: none\n"
        "NOT_DONE: none\n"
        "RECOMMENDED_MEMORY_UPDATE: none\n",
        encoding="utf-8",
    )


def _write_test_artifact(tmp_path: Path) -> None:
    """Write a minimal canonical test-result artifact (no failures)."""
    art_dir = tmp_path / "artifacts" / "runtime" / "test-results"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "latest.json").write_text(
        json.dumps({"source": "pytest", "failure_disposition": None}),
        encoding="utf-8",
    )


# ── 1. Policy parsing: valid tiers ───────────────────────────────────────────

@pytest.mark.parametrize("tier", ["A", "B", "C"])
def test_policy_parses_valid_tier(tmp_path, tier):
    _write_policy(tmp_path, hook_coverage_tier=tier)
    policy = load_policy(project_root=tmp_path)
    assert policy.hook_coverage_tier == tier


# ── 2. Policy parsing: invalid tier → ValueError ─────────────────────────────

@pytest.mark.parametrize("bad_tier", ["D", "0", "tier-b", ""])
def test_policy_invalid_tier_raises(tmp_path, bad_tier):
    _write_policy(tmp_path, hook_coverage_tier=bad_tier if bad_tier else "''")
    with pytest.raises(ValueError, match="invalid hook_coverage_tier"):
        load_policy(project_root=tmp_path)


# ── 3. Policy parsing: absent tier → None ────────────────────────────────────

def test_policy_absent_tier_is_none(tmp_path):
    _write_policy(tmp_path)  # no hook_coverage_tier
    policy = load_policy(project_root=tmp_path)
    assert policy.hook_coverage_tier is None


# ── 4. Closeout eval unit: Tier A + missing ───────────────────────────────────

def test_evaluate_closeout_tier_a_missing():
    result = _evaluate_closeout_by_tier(STATUS_MISSING, "A")
    assert result["hook_coverage_tier"] == "A"
    assert result["enforcement"] == "fail"
    assert result["ok_effect"] == "fail"
    assert result["classification"] == "violation"
    assert "closeout_file_missing" in result["signals"]
    assert "hook_coverage_tier_undeclared" not in result["signals"]


# ── 5. Closeout eval unit: Tier B + missing ───────────────────────────────────

def test_evaluate_closeout_tier_b_missing():
    result = _evaluate_closeout_by_tier(STATUS_MISSING, "B")
    assert result["hook_coverage_tier"] == "B"
    assert result["enforcement"] == "advisory"
    assert result["ok_effect"] == "pass"
    assert result["classification"] == "incomplete_observation"
    assert "closeout_missing_tier_b" in result["signals"]
    assert "closeout_file_missing" not in result["signals"]


# ── 6. Closeout eval unit: Tier C + missing ───────────────────────────────────

def test_evaluate_closeout_tier_c_missing():
    result = _evaluate_closeout_by_tier(STATUS_MISSING, "C")
    assert result["hook_coverage_tier"] == "C"
    assert result["enforcement"] == "none"
    assert result["ok_effect"] == "pass"
    assert result["classification"] == "not_applicable"
    assert result["signals"] == []


# ── 7. Closeout eval unit: undeclared + missing ───────────────────────────────

def test_evaluate_closeout_undeclared_missing():
    result = _evaluate_closeout_by_tier(STATUS_MISSING, None)
    assert result["hook_coverage_tier"] == "undeclared"
    assert result["enforcement"] == "fail"
    assert result["ok_effect"] == "fail"
    assert "closeout_file_missing" in result["signals"]
    assert "hook_coverage_tier_undeclared" in result["signals"]


# ── 8. Closeout eval unit: Tier B + valid closeout ───────────────────────────

def test_evaluate_closeout_tier_b_valid():
    result = _evaluate_closeout_by_tier(STATUS_VALID, "B")
    assert result["hook_coverage_tier"] == "B"
    assert result["ok_effect"] == "pass"
    assert result["classification"] == "ok"
    assert result["signals"] == []


# ── 9. Integration: Tier B + missing closeout → ok not pulled down ───────────

def test_integration_tier_b_missing_closeout_ok_not_false(tmp_path):
    """Tier B repo with no closeout file: ok should not be forced False."""
    _write_policy(tmp_path, hook_coverage_tier="B")
    _write_test_artifact(tmp_path)
    # No closeout file written — STATUS_MISSING expected

    result = run_session_end_hook(tmp_path)

    assert result["closeout_status"] == "closeout_missing"
    assert result["hook_coverage_tier"] == "B"
    ce = result["closeout_evaluation"]
    assert ce["enforcement"] == "advisory"
    assert ce["ok_effect"] == "pass"
    assert "closeout_missing_tier_b" in ce["signals"]
    # ok should NOT be False solely due to closeout missing
    # (it may be False for other reasons, but closeout alone must not block)
    assert result["closeout_evaluation"]["ok_effect"] == "pass"


# ── 10. Integration: Tier A + missing closeout → ok=False ─────────────────────

def test_integration_tier_a_missing_closeout_ok_false(tmp_path):
    """Tier A repo with no closeout file: ok must be False."""
    _write_policy(tmp_path, hook_coverage_tier="A")
    _write_test_artifact(tmp_path)

    result = run_session_end_hook(tmp_path)

    assert result["closeout_status"] == "closeout_missing"
    assert result["hook_coverage_tier"] == "A"
    assert result["closeout_evaluation"]["enforcement"] == "fail"
    assert result["ok"] is False


# ── 11. Integration: artifact visibility ──────────────────────────────────────

def test_integration_artifact_visibility(tmp_path):
    """Result dict always contains hook_coverage_tier and closeout_evaluation."""
    _write_policy(tmp_path, hook_coverage_tier="C")
    _write_test_artifact(tmp_path)

    result = run_session_end_hook(tmp_path)

    assert "hook_coverage_tier" in result
    assert "closeout_evaluation" in result
    ce = result["closeout_evaluation"]
    assert "hook_coverage_tier" in ce
    assert "enforcement" in ce
    assert "ok_effect" in ce
    assert "classification" in ce
    assert "signals" in ce
