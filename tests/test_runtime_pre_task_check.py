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
    assert result["active_rules"]["valid"] is True
    assert result["active_rules"]["active_rules"][0]["files"]


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


def test_pre_task_check_exposes_cpp_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,cpp",
        risk="medium",
        oversight="auto",
        memory_mode="candidate",
    )
    assert result["ok"] is True
    cpp_pack = [pack for pack in result["active_rules"]["active_rules"] if pack["name"] == "cpp"][0]
    assert "AdditionalIncludeDirectories" in cpp_pack["files"][0]["content"]


def test_pre_task_check_exposes_refactor_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common,refactor",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )
    assert result["ok"] is True
    refactor_pack = [pack for pack in result["active_rules"]["active_rules"] if pack["name"] == "refactor"][0]
    contents = "\n".join(file["content"] for file in refactor_pack["files"])
    assert "observable behavior remains unchanged" in contents


def test_pre_task_check_exposes_csharp_avalonia_swift_active_rules(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="csharp,avalonia,swift",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
    )
    assert result["ok"] is True
    contents = "\n".join(
        file["content"]
        for pack in result["active_rules"]["active_rules"]
        for file in pack["files"]
    )
    assert "async void" in contents
    assert "Dispatcher.UIThread" in contents
    assert "structured concurrency" in contents


def test_pre_task_check_exposes_advisory_rule_pack_suggestions(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    assert result["ok"] is True
    assert result["runtime_contract"]["rules"] == ["common"]
    assert "rule_pack_suggestions" in result
    assert "csharp" in result["rule_pack_suggestions"]["suggested_rules"]
    assert "avalonia" in result["rule_pack_suggestions"]["suggested_rules"]
    assert result["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert any(
        item["name"] == "refactor" and item["advisory_only"] is True
        for item in result["rule_pack_suggestions"]["scope_packs"]
    )


def test_pre_task_check_warns_when_high_confidence_suggestions_are_missing(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    assert result["ok"] is True
    assert any("Suggested language pack 'csharp' is not active" in warning for warning in result["warnings"])
    assert any("Suggested framework pack 'avalonia' is not active" in warning for warning in result["warnings"])
    assert any("Advisory scope pack 'refactor' is suggested by task text but not active" in warning for warning in result["warnings"])


def test_pre_task_check_human_output_includes_suggested_rules_preview(local_tmp_dir, monkeypatch):
    monkeypatch.setattr(pre_task_check, "check_freshness", lambda _: _FreshnessStub())
    (local_tmp_dir / "PLAN.md").write_text("> **Owner**: Tester\n", encoding="utf-8")
    (local_tmp_dir / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_tmp_dir / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    result = pre_task_check.run_pre_task_check(
        local_tmp_dir,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Refactor Avalonia boundary",
    )

    output = pre_task_check.format_human_result(result)
    assert "suggested_rules_preview=common,csharp,avalonia,refactor" in output
