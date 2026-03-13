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


def test_rule_pack_suggester_detects_swift():
    root = _reset_fixture("swift")
    _write(root / "Package.swift", "// swift package")
    _write(root / "Sources" / "Feature.swift", "import Foundation")

    result = suggest_rule_packs(root)

    assert any(item["name"] == "swift" for item in result["language_packs"])


def test_rule_pack_suggester_scope_is_advisory_only():
    root = _reset_fixture("scope")
    _write(root / "module.py", "print('ok')")

    result = suggest_rule_packs(root, task_text="Refactor service boundary and extract helper")

    assert any(item["name"] == "refactor" for item in result["scope_packs"])
    assert all(item.get("advisory_only") is True for item in result["scope_packs"])
