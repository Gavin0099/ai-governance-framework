from __future__ import annotations

import shutil
from pathlib import Path

from governance_tools.rule_pack_suggester import suggest_rule_packs


FIXTURE_ROOT = Path("tests/_tmp_rule_pack_suggester")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_rule_pack_suggester_detects_csharp_and_avalonia():
    root = _reset_fixture("csharp_avalonia")
    _write(root / "App.sln", "")
    _write(root / "App" / "App.csproj", "<Project><PackageReference Include=\"Avalonia\" /></Project>")
    _write(root / "App" / "MainWindowViewModel.cs", "Dispatcher.UIThread.Post(() => {});")

    result = suggest_rule_packs(root)

    assert "common" in result["suggested_rules"]
    assert any(item["name"] == "csharp" for item in result["language_packs"])
    assert any(item["name"] == "avalonia" for item in result["framework_packs"])
    assert result["suggested_rules_preview"] == ["common", "csharp", "avalonia"]
    assert result["suggested_skills"] == ["code-style", "governance-runtime"]
    assert result["suggested_agent"] == "advanced-agent"


def test_rule_pack_suggester_detects_swift():
    root = _reset_fixture("swift")
    _write(root / "Package.swift", "// swift package")
    _write(root / "Sources" / "Feature.swift", "import Foundation")

    result = suggest_rule_packs(root)

    assert any(item["name"] == "swift" for item in result["language_packs"])


def test_rule_pack_suggester_recommends_python_agent_and_cli_skill():
    root = _reset_fixture("python_cli")
    _write(root / "tool.py", "print('ok')")

    result = suggest_rule_packs(root, task_text="Improve CLI human output for governance command")

    assert any(item["name"] == "python" for item in result["language_packs"])
    assert "python" in result["suggested_skills"]
    assert "human-readable-cli" in result["suggested_skills"]
    assert result["suggested_agent"] == "cli-agent"


def test_rule_pack_suggester_scope_is_advisory_only():
    root = _reset_fixture("scope")
    _write(root / "module.py", "print('ok')")

    result = suggest_rule_packs(root, task_text="Refactor service boundary and extract helper")

    assert any(item["name"] == "refactor" for item in result["scope_packs"])
    assert all(item.get("advisory_only") is True for item in result["scope_packs"])
    assert "refactor" in result["suggested_rules_preview"]


def test_rule_pack_suggester_ignores_contract_scaffolding_language_noise():
    root = _reset_fixture("contract_scaffolding")
    _write(root / "contract.yaml", "name: sample-contract\n")
    _write(root / "validators" / "sample_validator.py", "print('validator')\n")
    _write(root / "fixtures" / "src" / "driver.c", "void DriverEntry(void) {}\n")
    _write(root / "README.md", "# sample\n")

    result = suggest_rule_packs(root)

    assert result["language_packs"] == []
    assert result["suggested_rules"] == ["common"]
    assert result["suggested_agent"] == "advanced-agent"
