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
    assert "rule_pack_suggestions" in state
    assert state["suggested_skills"] == ["code-style", "governance-runtime"]
    assert state["suggested_agent"] == "advanced-agent"


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


def test_generate_state_can_include_refactor_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Refactor service boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    refactor_pack = [pack for pack in state["active_rules"]["active_rules"] if pack["name"] == "refactor"][0]
    contents = "\n".join(file["content"] for file in refactor_pack["files"])
    assert "must not introduce new boundary crossings" in contents


def test_generate_state_can_include_csharp_avalonia_swift_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Expand UI and concurrency governance\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="csharp,avalonia,swift",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    contents = "\n".join(
        file["content"]
        for pack in state["active_rules"]["active_rules"]
        for file in pack["files"]
    )
    assert "async void" in contents
    assert "Dispatcher.UIThread" in contents
    assert "structured concurrency" in contents


def test_generate_state_includes_advisory_rule_pack_suggestions_without_mutating_contract(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor Avalonia boundary\n"
        "\n"
        "## Current Sprint\n"
        "- [ ] Refactor UI boundary\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )

    assert state["runtime_contract"]["rules"] == ["common"]
    suggested = state["rule_pack_suggestions"]["suggested_rules"]
    assert "common" in suggested
    assert "csharp" in suggested
    assert "avalonia" in suggested
    assert state["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert state["suggested_skills"] == ["code-style", "governance-runtime"]
    assert state["suggested_agent"] == "advanced-agent"
    scope_suggestions = state["rule_pack_suggestions"]["scope_packs"]
    assert any(item["name"] == "refactor" and item["advisory_only"] is True for item in scope_suggestions)


def test_generate_state_can_include_architecture_impact_preview(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(state_generator, "check_freshness", lambda _: _FreshnessStub())

    plan = local_tmp_dir / "PLAN.md"
    plan.write_text(
        "> **Owner**: Tester\n"
        "> **Freshness**: Sprint (7d)\n"
        "\n"
        "[>] Phase A : Refactor service boundary\n",
        encoding="utf-8",
    )

    before_file = local_tmp_dir / "application" / "before.cs"
    after_file = local_tmp_dir / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    state = state_generator.generate_state(
        plan,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        impact_before_files=[before_file],
        impact_after_files=[after_file],
    )

    preview = state["architecture_impact_preview"]
    assert preview["recommended_risk"] == "medium"
    assert preview["recommended_oversight"] == "review-required"
    assert "public-api-review" in preview["required_evidence"]
    assert "application" in preview["touched_layers"]
    guidance = state["proposal_guidance"]
    assert guidance["recommended_risk"] == "medium"
    assert "public_api_diff_checker" in guidance["expected_validators"]
    assert "public-api-review" in guidance["required_evidence"]
