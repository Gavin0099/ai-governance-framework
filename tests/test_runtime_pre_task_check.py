import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import runtime_hooks.core.pre_task_check as pre_task_check


class _FreshnessStub:
    def __init__(self, status="FRESH", days_since_update=0, threshold_days=7):
        self.status = status
        self.days_since_update = days_since_update
        self.threshold_days = threshold_days


@pytest.fixture
def local_tmp_dir():
    path = Path("tests") / "_tmp_runtime_hooks"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_pre_task_check_passes_for_valid_inputs(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,python",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is True
    assert result["rule_packs"]["valid"] is True


def test_pre_task_check_blocks_high_risk_auto_oversight(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="high",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is False
    assert any("High-risk" in error for error in result["errors"])


def test_pre_task_check_blocks_unknown_rule_pack(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,unknown-pack",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is False
    assert result["rule_packs"]["missing"] == ["unknown-pack"]
