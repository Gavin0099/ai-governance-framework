import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import governance_tools.state_generator as state_generator


class _FreshnessStub:
    def __init__(self, status="FRESH", days_since_update=0, threshold_days=7, last_updated=None):
        self.status = status
        self.days_since_update = days_since_update
        self.threshold_days = threshold_days
        self.last_updated = last_updated


@pytest.fixture
def local_tmp_dir():
    path = Path("tests") / "_tmp_state_generator"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_generate_state_includes_runtime_contract(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Add runtime hooks\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,python",
        risk="high",
        oversight="review-required",
        memory_mode="candidate",
    )

    assert state["runtime_contract"]["rules"] == ["common", "python"]
    assert state["runtime_contract"]["risk"] == "high"
    assert state["runtime_contract"]["oversight"] == "review-required"
    assert state["runtime_contract"]["memory_mode"] == "candidate"
    assert state["rule_packs"]["valid"] is True
    assert state["active_rules"]["valid"] is True
    assert state["active_rules"]["active_rules"][0]["files"]


def test_generate_state_missing_plan_returns_error(local_tmp_dir):
    state = state_generator.generate_state(local_tmp_dir / "PLAN.md")
    assert "error" in state


def test_generate_state_can_include_cpp_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Enforce build boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,cpp",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    cpp_pack = [pack for pack in state["active_rules"]["active_rules"] if pack["name"] == "cpp"][0]
    assert "cross-project private header" in cpp_pack["files"][0]["content"]
