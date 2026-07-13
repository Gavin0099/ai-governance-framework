from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from governance_tools.rule_pack_suggester import suggest_rule_packs


def _reset_fixture(fixture_root: Path, name: str) -> Path:
    path = fixture_root / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet"], cwd=path, check=True, capture_output=True)


def _language_item(result: dict, name: str) -> dict:
    return next(item for item in result["language_packs"] if item["name"] == name)


def _framework_item(result: dict, name: str) -> dict:
    return next(item for item in result["framework_packs"] if item["name"] == name)


def test_rule_pack_suggester_detects_csharp_and_avalonia(tmp_path):
    root = _reset_fixture(tmp_path, "csharp_avalonia")
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


def test_avalonia_structure_signal_is_prioritized_within_fifty_file_sample(tmp_path):
    root = _reset_fixture(tmp_path, "avalonia_structure_priority")
    for index in range(50):
        _write(root / "src" / f"a{index:02d}.cs", "public class Placeholder {}\n")
    _write(
        root / "z-project" / "App.csproj",
        '<Project><PackageReference Include="Avalonia" /></Project>\n',
    )

    result = suggest_rule_packs(root)

    avalonia = _framework_item(result, "avalonia")
    assert avalonia["confidence"] == "medium"
    assert avalonia.get("advisory_only") is not True
    assert "avalonia" in result["suggested_rules"]


def test_avalonia_dispatcher_source_signal_remains_medium(tmp_path):
    root = _reset_fixture(tmp_path, "avalonia_dispatcher_source")
    _write(root / "MainWindow.cs", "Dispatcher.UIThread.Post(() => {});\n")

    result = suggest_rule_packs(root)

    avalonia = _framework_item(result, "avalonia")
    assert avalonia["confidence"] == "medium"
    assert avalonia.get("advisory_only") is not True
    assert "avalonia" in result["suggested_rules"]


def test_avalonia_headless_source_signal_remains_medium(tmp_path):
    root = _reset_fixture(tmp_path, "avalonia_headless_source")
    _write(root / "TestApp.cs", "using Avalonia.Headless;\n")

    result = suggest_rule_packs(root)

    avalonia = _framework_item(result, "avalonia")
    assert avalonia["confidence"] == "medium"
    assert avalonia.get("advisory_only") is not True


def test_avalonia_bare_source_comment_is_low_preview_only(tmp_path):
    root = _reset_fixture(tmp_path, "avalonia_weak_comment")
    _write(root / "Migration.cs", "// Avalonia migration note\n")

    result = suggest_rule_packs(root)

    avalonia = _framework_item(result, "avalonia")
    assert avalonia["confidence"] == "low"
    assert avalonia["advisory_only"] is True
    assert "avalonia" not in result["suggested_rules"]
    assert "avalonia" in result["suggested_rules_preview"]


def test_planned_electron_is_suppressed_from_all_suggestion_surfaces(tmp_path):
    root = _reset_fixture(tmp_path, "electron_planned")
    _write(root / "main.ts", 'import { BrowserWindow } from "electron";\n')

    result = suggest_rule_packs(root)

    assert all(item["name"] != "electron" for item in result["framework_packs"])
    assert "electron" not in result["suggested_rules"]
    assert "electron" not in result["suggested_rules_preview"]
    assert "electron" not in result["unloadable_signals"]
    assert result["suggested_skills"] == ["code-style", "governance-runtime"]
    assert result["suggested_agent"] == "advanced-agent"


def test_planned_release_is_suppressed_from_scope_and_preview(tmp_path):
    root = _reset_fixture(tmp_path, "release_planned")
    _write(root / "tool.py", "print('ok')\n")

    result = suggest_rule_packs(root, task_text="Prepare release package and deploy")

    assert all(item["name"] != "release" for item in result["scope_packs"])
    assert "release" not in result["suggested_rules"]
    assert "release" not in result["suggested_rules_preview"]


def test_language_specific_structure_files_are_high_confidence(tmp_path):
    cases = [
        ("csharp", "App.csproj", "<Project />\n"),
        ("swift", "Package.swift", "// swift-tools-version: 6.0\n"),
        ("cpp", "Native.vcxproj", "<Project />\n"),
        ("python", "pyproject.toml", "[project]\nname = 'sample'\n"),
    ]

    for pack, filename, content in cases:
        root = _reset_fixture(tmp_path, f"strong_{pack}")
        _write(root / filename, content)

        result = suggest_rule_packs(root)

        assert _language_item(result, pack)["confidence"] == "high"
        assert pack in result["suggested_rules"]


def test_sln_referencing_only_vcxproj_is_cpp_high_not_csharp(tmp_path):
    root = _reset_fixture(tmp_path, "vcxproj_solution")
    _write(
        root / "Native.sln",
        'Project("{GUID}") = "Native", "Native\\Native.vcxproj", "{PROJECT-GUID}"\nEndProject\n',
    )

    result = suggest_rule_packs(root)

    assert _language_item(result, "cpp")["confidence"] == "high"
    assert all(item["name"] != "csharp" for item in result["language_packs"])


def test_sln_referencing_only_csproj_is_csharp_high_not_cpp(tmp_path):
    root = _reset_fixture(tmp_path, "csproj_solution")
    _write(
        root / "Managed.sln",
        'Project("{GUID}") = "Managed", "Managed\\Managed.csproj", "{PROJECT-GUID}"\nEndProject\n',
    )

    result = suggest_rule_packs(root)

    assert _language_item(result, "csharp")["confidence"] == "high"
    assert all(item["name"] != "cpp" for item in result["language_packs"])


def test_rule_pack_suggester_detects_swift(tmp_path):
    root = _reset_fixture(tmp_path, "swift")
    _write(root / "Package.swift", "// swift package")
    _write(root / "Sources" / "Feature.swift", "import Foundation")

    result = suggest_rule_packs(root)

    assert any(item["name"] == "swift" for item in result["language_packs"])


def test_rule_pack_suggester_recommends_python_agent_and_cli_skill(tmp_path):
    root = _reset_fixture(tmp_path, "python_cli")
    _write(root / "tool.py", "print('ok')")

    result = suggest_rule_packs(root, task_text="Improve CLI human output for governance command")

    assert any(item["name"] == "python" for item in result["language_packs"])
    assert "python" in result["suggested_skills"]
    assert "human-readable-cli" in result["suggested_skills"]
    assert result["suggested_agent"] == "cli-agent"


def test_rule_pack_suggester_scope_is_advisory_only(tmp_path):
    root = _reset_fixture(tmp_path, "scope")
    _write(root / "module.py", "print('ok')")

    result = suggest_rule_packs(root, task_text="Refactor service boundary and extract helper")

    assert any(item["name"] == "refactor" for item in result["scope_packs"])
    assert all(item.get("advisory_only") is True for item in result["scope_packs"])
    assert "refactor" in result["suggested_rules_preview"]


def test_rule_pack_suggester_ignores_contract_scaffolding_language_noise(tmp_path):
    root = _reset_fixture(tmp_path, "contract_scaffolding")
    _write(root / "contract.yaml", "name: sample-contract\n")
    _write(root / "validators" / "sample_validator.py", "print('validator')\n")
    _write(root / "fixtures" / "src" / "driver.c", "void DriverEntry(void) {}\n")
    _write(root / "README.md", "# sample\n")

    result = suggest_rule_packs(root)

    assert result["language_packs"] == []
    assert result["suggested_rules"] == ["common"]
    assert result["suggested_agent"] == "advanced-agent"


def test_rule_pack_suggester_ignores_local_test_and_artifact_fixture_noise(tmp_path):
    root = _reset_fixture(tmp_path, "non_product_roots")
    _write(root / "tool.py", "print('product')\n")
    _write(root / "tests" / "fixture.cs", "Dispatcher.UIThread.Post(() => {});\n")
    _write(root / "artifacts" / "capture.swift", "import Foundation\n")
    _write(root / "examples" / "fixture.cpp", "int main() { return 0; }\n")
    _write(root / "runtime_hooks" / "examples" / "fixture.cs", "Dispatcher.UIThread.Post(() => {});\n")
    _write(root / ".tmp-pilot" / "fixture.csproj", "<Project />\n")
    _write(root / "docs" / "transcript.json", '{"note": "Avalonia"}\n')

    result = suggest_rule_packs(root)

    assert [item["name"] for item in result["language_packs"]] == ["python"]
    assert result["framework_packs"] == []


def test_rule_pack_suggester_ignores_embedded_framework_fixture_noise(tmp_path):
    root = _reset_fixture(tmp_path, "embedded_framework")
    _write(root / "consumer.py", "print('consumer')\n")
    embedded = root / "ai-governance-framework"
    _write(embedded / "tests" / "fixture.cs", "Dispatcher.UIThread.Post(() => {});\n")
    _write(embedded / "runtime_hooks" / "examples" / "fixture.swift", "import Foundation\n")

    result = suggest_rule_packs(root)

    assert [item["name"] for item in result["language_packs"]] == ["python"]
    assert result["framework_packs"] == []


def test_rule_pack_suggester_git_inventory_uses_tracked_and_untracked_nonignored_files(tmp_path):
    root = tmp_path / "consumer"
    _init_git_repo(root)
    _write(root / ".gitignore", "obj/\nnode_modules/\n")
    _write(root / "src" / "App.cs", "public class App {}\n")
    _write(root / "src" / "NewFeature.cs", "public class NewFeature {}\n")
    _write(root / "obj" / "Generated.py", "print('generated')\n")
    _write(root / "node_modules" / "native.cpp", "int generated = 1;\n")
    subprocess.run(
        ["git", "add", "--", ".gitignore", "src/App.cs"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    result = suggest_rule_packs(root)

    assert [item["name"] for item in result["language_packs"]] == ["csharp"]
    assert result["language_packs"][0]["reasons"] == ["src/App.cs", "src/NewFeature.cs"]
    assert "python" not in result["suggested_rules"]
    assert "cpp" not in result["suggested_rules"]


def test_low_confidence_language_stays_preview_only_and_does_not_select_python_behavior(tmp_path):
    root = _reset_fixture(tmp_path, "incidental_python")
    for index in range(20):
        _write(root / "src" / f"Feature{index}.cs", f"public class Feature{index} {{}}\n")
    _write(root / "tools" / "generate.py", "print('generate')\n")

    result = suggest_rule_packs(root)

    python = _language_item(result, "python")
    assert python["confidence"] == "low"
    assert python["advisory_only"] is True
    assert "python" not in result["suggested_rules"]
    assert "python" in result["suggested_rules_preview"]
    assert "python" not in result["suggested_skills"]
    assert result["suggested_agent"] == "advanced-agent"


def test_language_share_denominator_excludes_headers_and_structure_files(tmp_path):
    root = _reset_fixture(tmp_path, "language_share_denominator")
    for index in range(57):
        _write(root / "managed" / f"Feature{index}.cs", f"public class Feature{index} {{}}\n")
    for index in range(3):
        _write(root / "tools" / f"tool{index}.py", f"print({index})\n")
    for index in range(100):
        _write(root / "include" / f"header{index}.h", f"#define HEADER_{index} {index}\n")
    for index in range(20):
        _write(root / "solutions" / f"Empty{index}.sln", "Microsoft Visual Studio Solution File\n")

    result = suggest_rule_packs(root)

    assert _language_item(result, "python")["confidence"] == "medium"
    assert all(item["name"] != "cpp" for item in result["language_packs"])
    assert all(item["name"] != "objective-c" for item in result["language_packs"])


def test_hpp_only_repo_remains_extension_only_cpp_evidence(tmp_path):
    root = _reset_fixture(tmp_path, "hpp_only")
    _write(root / "include" / "widget.hpp", "class Widget {};\n")

    result = suggest_rule_packs(root)

    cpp = _language_item(result, "cpp")
    assert cpp["confidence"] == "medium"
    assert "cpp" in result["suggested_rules"]


def test_h_header_requires_unambiguous_cpp_or_objective_c_companion(tmp_path):
    header_only = _reset_fixture(tmp_path, "header_only")
    _write(header_only / "include" / "shared.h", "#pragma once\n")
    assert suggest_rule_packs(header_only)["language_packs"] == []

    cpp_root = _reset_fixture(tmp_path, "header_with_cpp")
    _write(cpp_root / "include" / "shared.h", "#pragma once\n")
    _write(cpp_root / "src" / "main.cpp", "int main() { return 0; }\n")
    cpp_result = suggest_rule_packs(cpp_root)
    assert "include/shared.h" in _language_item(cpp_result, "cpp")["reasons"]
    assert all(item["name"] != "objective-c" for item in cpp_result["language_packs"])

    objc_root = _reset_fixture(tmp_path, "header_with_objective_c")
    _write(objc_root / "include" / "shared.h", "#pragma once\n")
    _write(objc_root / "src" / "main.m", "int main(void) { return 0; }\n")
    objc_result = suggest_rule_packs(objc_root)
    assert "include/shared.h" in _language_item(objc_result, "objective-c")["reasons"]
    assert "objective-c" not in objc_result["suggested_rules"]
    assert "objective-c" in objc_result["unloadable_signals"]


def test_h_header_with_mixed_companions_preserves_both_language_signals(tmp_path):
    root = _reset_fixture(tmp_path, "header_with_mixed_companions")
    _write(root / "include" / "shared.h", "#pragma once\n")
    _write(root / "src" / "native.cpp", "int native() { return 0; }\n")
    _write(root / "src" / "bridge.m", "int bridge(void) { return 0; }\n")

    result = suggest_rule_packs(root)

    cpp = _language_item(result, "cpp")
    objective_c = _language_item(result, "objective-c")
    assert "include/shared.h" in cpp["reasons"]
    assert "include/shared.h" in objective_c["reasons"]
    assert "cpp" in result["suggested_rules"]
    assert "objective-c" not in result["suggested_rules"]
    assert "objective-c" in result["unloadable_signals"]


def test_rule_pack_suggester_non_git_fallback_is_deterministic(tmp_path):
    root = _reset_fixture(tmp_path, "deterministic_non_git_fallback")
    _write(root / "zeta.py", "print('zeta')\n")
    _write(root / "alpha.py", "print('alpha')\n")

    result = suggest_rule_packs(root)

    assert [item["name"] for item in result["language_packs"]] == ["python"]
    assert result["language_packs"][0]["reasons"] == ["alpha.py", "zeta.py"]


def test_rule_pack_suggester_nested_parent_repo_uses_filesystem_fallback(tmp_path):
    parent = tmp_path / "parent"
    _init_git_repo(parent)
    _write(parent / ".gitignore", "nested/*.py\n")
    subprocess.run(
        ["git", "add", "--", ".gitignore"],
        cwd=parent,
        check=True,
        capture_output=True,
    )
    root = parent / "nested"
    _write(root / "zeta.py", "print('zeta')\n")
    _write(root / "alpha.py", "print('alpha')\n")

    result = suggest_rule_packs(root)

    assert [item["name"] for item in result["language_packs"]] == ["python"]
    assert result["language_packs"][0]["reasons"] == ["alpha.py", "zeta.py"]


def test_unloadable_domain_moves_to_unloadable_signals(tmp_path):
    """A contract domain with no matching pack directory must not be suggested
    as loadable (regression for the pilot's "Unknown rule packs" error)."""
    root = _reset_fixture(tmp_path, "unloadable_domain")
    _write(root / "contract.yaml", "domain: custom-governance\nrule_roots:\n  - rules\n")
    _write(root / "app.py", "print('hi')\n")
    (root / "rules").mkdir(parents=True, exist_ok=True)

    result = suggest_rule_packs(root)

    assert "custom-governance" not in result["suggested_rules"]
    assert "custom-governance" not in result["suggested_rules_preview"]
    assert "custom-governance" in result["unloadable_signals"]
    # detection metadata is preserved for reviewers
    assert any(item["name"] == "custom-governance" for item in result["domain_packs"])
    # loadable language pack still suggested
    assert "python" in result["suggested_rules"]


def test_loadable_domain_pack_is_still_suggested(tmp_path):
    """A contract domain whose pack directory exists under its rule_roots
    keeps being suggested."""
    root = _reset_fixture(tmp_path, "loadable_domain")
    _write(root / "contract.yaml", "domain: boardsupport\nrule_roots:\n  - rules\n")
    _write(root / "rules" / "boardsupport" / "core.md", "# rule\n")
    _write(root / "app.py", "print('hi')\n")

    result = suggest_rule_packs(root)

    assert "boardsupport" in result["suggested_rules"]
    assert "boardsupport" in result["suggested_rules_preview"]
    assert result["unloadable_signals"] == []
