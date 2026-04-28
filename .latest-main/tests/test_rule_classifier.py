"""
Tests for governance_tools/rule_classifier.py

Coverage:
- load_rule_registry: parse RULE_REGISTRY.md, edge cases (empty, missing)
- detect_repo_type: firmware / product / service / tooling signals
- _matches_trigger: individual condition evaluation
- filter_rule_packs: integration with registry, repo_type/task_type combinations
"""

from __future__ import annotations

import pytest
from pathlib import Path

from governance_tools.rule_classifier import (
    _matches_trigger,
    _parse_yaml_block,
    detect_repo_type,
    filter_rule_packs,
    load_rule_registry,
)


# ---------------------------------------------------------------------------
# _parse_yaml_block
# ---------------------------------------------------------------------------

class TestParseYamlBlock:

    def test_simple_scalar(self):
        block = "name: common\nload_mode: always\n"
        result = _parse_yaml_block(block)
        assert result["name"] == "common"
        assert result["load_mode"] == "always"

    def test_inline_list(self):
        block = "repo_type: [firmware, product]\n"
        result = _parse_yaml_block(block)
        assert result["repo_type"] == ["firmware", "product"]

    def test_single_element_list(self):
        block = "repo_type: [all]\n"
        result = _parse_yaml_block(block)
        assert result["repo_type"] == ["all"]

    def test_quoted_scalar(self):
        block = 'description: "Core coding standards"\n'
        result = _parse_yaml_block(block)
        assert result["description"] == "Core coding standards"

    def test_comment_lines_ignored(self):
        block = "# This is a comment\nname: test\n"
        result = _parse_yaml_block(block)
        assert "name" in result
        assert len(result) == 1

    def test_empty_block(self):
        assert _parse_yaml_block("") == {}


# ---------------------------------------------------------------------------
# load_rule_registry
# ---------------------------------------------------------------------------

class TestLoadRuleRegistry:

    def test_loads_from_default_path(self):
        registry = load_rule_registry()
        assert len(registry) >= 14

    def test_all_packs_have_name(self):
        registry = load_rule_registry()
        for pack in registry:
            assert "name" in pack
            assert pack["name"]

    def test_all_packs_have_required_keys(self):
        registry = load_rule_registry()
        required = {"name", "load_mode", "repo_type", "task_type"}
        for pack in registry:
            missing = required - set(pack.keys())
            assert not missing, f"{pack['name']}: missing keys {missing}"

    def test_repo_type_and_task_type_are_lists(self):
        registry = load_rule_registry()
        for pack in registry:
            assert isinstance(pack["repo_type"], list), f"{pack['name']}.repo_type must be list"
            assert isinstance(pack["task_type"], list), f"{pack['name']}.task_type must be list"

    def test_common_has_load_mode_always(self):
        registry = load_rule_registry()
        common = next((p for p in registry if p["name"] == "common"), None)
        assert common is not None, "common pack must exist"
        assert common["load_mode"] == "always"

    def test_firmware_isr_has_firmware_repo_type(self):
        registry = load_rule_registry()
        pack = next((p for p in registry if p["name"] == "firmware_isr"), None)
        assert pack is not None, "firmware_isr pack must exist"
        assert "firmware" in pack["repo_type"]

    def test_refactor_has_refactor_task_type(self):
        registry = load_rule_registry()
        pack = next((p for p in registry if p["name"] == "refactor"), None)
        assert pack is not None, "refactor pack must exist"
        assert "refactor" in pack["task_type"]

    def test_python_has_service_and_tooling_repo_type(self):
        registry = load_rule_registry()
        pack = next((p for p in registry if p["name"] == "python"), None)
        assert pack is not None, "python pack must exist"
        assert "service" in pack["repo_type"]
        assert "tooling" in pack["repo_type"]

    def test_cpp_has_firmware_and_product_repo_type(self):
        registry = load_rule_registry()
        pack = next((p for p in registry if p["name"] == "cpp"), None)
        assert pack is not None, "cpp pack must exist"
        assert "firmware" in pack["repo_type"]
        assert "product" in pack["repo_type"]

    def test_review_gate_has_review_task_type(self):
        registry = load_rule_registry()
        pack = next((p for p in registry if p["name"] == "review_gate"), None)
        assert pack is not None, "review_gate pack must exist"
        assert "review" in pack["task_type"]

    def test_nonexistent_path_returns_empty(self, tmp_path):
        result = load_rule_registry(tmp_path / "NONEXISTENT.md")
        assert result == []

    def test_empty_registry_returns_empty(self, tmp_path):
        empty = tmp_path / "RULE_REGISTRY.md"
        empty.write_text("# Empty\nNo packs here.\n", encoding="utf-8")
        result = load_rule_registry(empty)
        assert result == []

    def test_custom_registry_file(self, tmp_path):
        content = (
            "# Custom Registry\n\n"
            "### custom_pack\n\n"
            "```yaml\n"
            "name: custom_pack\n"
            "load_mode: always\n"
            "repo_type: [all]\n"
            "task_type: [all]\n"
            "description: \"A custom pack\"\n"
            "```\n"
        )
        registry_file = tmp_path / "RULE_REGISTRY.md"
        registry_file.write_text(content, encoding="utf-8")
        result = load_rule_registry(registry_file)
        assert len(result) == 1
        assert result[0]["name"] == "custom_pack"
        assert result[0]["load_mode"] == "always"


# ---------------------------------------------------------------------------
# detect_repo_type
# ---------------------------------------------------------------------------

class TestDetectRepoType:

    def test_firmware_cmake_and_c_files(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.c").write_text("int main() { return 0; }\n")
        assert detect_repo_type(tmp_path) == "firmware"

    def test_firmware_c_only_no_cmake_no_package_json(self, tmp_path):
        (tmp_path / "hal.c").write_text("")
        assert detect_repo_type(tmp_path) == "firmware"

    def test_firmware_cmake_only_no_c_files(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("")
        assert detect_repo_type(tmp_path) == "firmware"

    def test_product_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert detect_repo_type(tmp_path) == "product"

    def test_product_csproj(self, tmp_path):
        (tmp_path / "App.csproj").write_text("<Project/>")
        assert detect_repo_type(tmp_path) == "product"

    def test_product_swift_file(self, tmp_path):
        (tmp_path / "App.swift").write_text("import SwiftUI\n")
        assert detect_repo_type(tmp_path) == "product"

    def test_service_requirements_and_py(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest\n")
        (tmp_path / "app.py").write_text("pass\n")
        assert detect_repo_type(tmp_path) == "service"

    def test_service_pyproject_and_py(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[build-system]\n")
        (tmp_path / "main.py").write_text("pass\n")
        assert detect_repo_type(tmp_path) == "service"

    def test_tooling_fallback_empty(self, tmp_path):
        assert detect_repo_type(tmp_path) == "tooling"

    def test_tooling_unknown_files(self, tmp_path):
        (tmp_path / "README.md").write_text("# Hello\n")
        assert detect_repo_type(tmp_path) == "tooling"

    def test_firmware_wins_when_cmake_but_no_package_json(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("")
        (tmp_path / "src.c").write_text("")
        # No package.json — should be firmware
        assert detect_repo_type(tmp_path) == "firmware"

    def test_product_wins_when_package_json_present_with_c_files(self, tmp_path):
        # package.json overrides c files because c files alone trigger firmware
        # but package.json check runs after firmware check with !has_package_json
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "native.c").write_text("")
        # firmware check: has_c_files=True AND NOT has_package_json=False → not firmware
        # product check: has_package_json=True → product
        assert detect_repo_type(tmp_path) == "product"

    def test_nonexistent_root_returns_tooling(self, tmp_path):
        assert detect_repo_type(tmp_path / "nonexistent") == "tooling"


# ---------------------------------------------------------------------------
# _matches_trigger
# ---------------------------------------------------------------------------

class TestMatchesTrigger:

    def _pack(self, **kwargs) -> dict:
        defaults = {"name": "test", "load_mode": "context_aware", "repo_type": ["all"], "task_type": ["all"], "risk_level": ["all"]}
        defaults.update(kwargs)
        return defaults

    def test_all_wildcards_always_match(self):
        pack = self._pack()
        assert _matches_trigger(pack, "firmware", "general", "low")
        assert _matches_trigger(pack, "product", "refactor", "high")

    def test_repo_type_specific_matches(self):
        pack = self._pack(repo_type=["firmware"])
        assert _matches_trigger(pack, "firmware", "general", "medium")
        assert not _matches_trigger(pack, "product", "general", "medium")

    def test_task_type_specific_matches(self):
        pack = self._pack(task_type=["refactor"])
        assert _matches_trigger(pack, "tooling", "refactor", "medium")
        assert not _matches_trigger(pack, "tooling", "general", "medium")

    def test_both_conditions_must_match(self):
        pack = self._pack(repo_type=["firmware"], task_type=["refactor"])
        assert _matches_trigger(pack, "firmware", "refactor", "medium")
        assert not _matches_trigger(pack, "product", "refactor", "medium")
        assert not _matches_trigger(pack, "firmware", "general", "medium")

    def test_multi_value_repo_type(self):
        pack = self._pack(repo_type=["firmware", "product"])
        assert _matches_trigger(pack, "firmware", "general", "medium")
        assert _matches_trigger(pack, "product", "general", "medium")
        assert not _matches_trigger(pack, "service", "general", "medium")


# ---------------------------------------------------------------------------
# filter_rule_packs
# ---------------------------------------------------------------------------

class TestFilterRulePacks:

    @pytest.fixture
    def registry(self):
        return load_rule_registry()

    def test_common_always_included_for_any_repo_type(self, registry):
        for rtype in ["firmware", "product", "service", "tooling"]:
            result = filter_rule_packs(registry, repo_type=rtype)
            assert "common" in result, f"common missing for repo_type={rtype}"

    def test_firmware_isr_only_for_firmware(self, registry):
        assert "firmware_isr" in filter_rule_packs(registry, repo_type="firmware")
        assert "firmware_isr" not in filter_rule_packs(registry, repo_type="product")
        assert "firmware_isr" not in filter_rule_packs(registry, repo_type="service")
        assert "firmware_isr" not in filter_rule_packs(registry, repo_type="tooling")

    def test_cpp_for_firmware_and_product(self, registry):
        assert "cpp" in filter_rule_packs(registry, repo_type="firmware")
        assert "cpp" in filter_rule_packs(registry, repo_type="product")
        assert "cpp" not in filter_rule_packs(registry, repo_type="service")
        assert "cpp" not in filter_rule_packs(registry, repo_type="tooling")

    def test_python_for_service_and_tooling(self, registry):
        assert "python" in filter_rule_packs(registry, repo_type="service")
        assert "python" in filter_rule_packs(registry, repo_type="tooling")
        assert "python" not in filter_rule_packs(registry, repo_type="firmware")
        assert "python" not in filter_rule_packs(registry, repo_type="product")

    def test_refactor_activated_by_task_type(self, registry):
        assert "refactor" in filter_rule_packs(registry, repo_type="tooling", task_type="refactor")
        assert "refactor" not in filter_rule_packs(registry, repo_type="tooling", task_type="general")

    def test_release_activated_by_task_type(self, registry):
        assert "release" in filter_rule_packs(registry, repo_type="tooling", task_type="release")
        assert "release" not in filter_rule_packs(registry, repo_type="tooling", task_type="general")

    def test_review_gate_activated_by_review_task_type(self, registry):
        assert "review_gate" in filter_rule_packs(registry, repo_type="tooling", task_type="review")
        assert "review_gate" not in filter_rule_packs(registry, repo_type="tooling", task_type="general")

    def test_product_language_packs_not_for_service(self, registry):
        service_packs = filter_rule_packs(registry, repo_type="service")
        for pack_name in ["typescript", "nextjs", "avalonia", "electron", "supabase", "csharp", "swift"]:
            assert pack_name not in service_packs, f"{pack_name} should not activate for service repo"

    def test_product_language_packs_not_for_firmware(self, registry):
        fw_packs = filter_rule_packs(registry, repo_type="firmware")
        for pack_name in ["typescript", "nextjs", "avalonia", "electron", "supabase"]:
            assert pack_name not in fw_packs, f"{pack_name} should not activate for firmware repo"

    def test_firmware_has_cpp(self, registry):
        fw_packs = filter_rule_packs(registry, repo_type="firmware")
        assert "cpp" in fw_packs

    def test_firmware_refactor_task(self, registry):
        packs = filter_rule_packs(registry, repo_type="firmware", task_type="refactor")
        assert "common" in packs
        assert "refactor" in packs
        assert "firmware_isr" in packs
        assert "cpp" in packs

    def test_empty_registry_returns_empty(self):
        result = filter_rule_packs([], repo_type="firmware")
        assert result == []

    def test_returns_list_of_strings(self, registry):
        result = filter_rule_packs(registry, repo_type="product")
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_default_task_type_general(self, registry):
        # Without specifying task_type, refactor/release/review_gate should not appear
        packs = filter_rule_packs(registry, repo_type="tooling")
        assert "refactor" not in packs
        assert "release" not in packs
        assert "review_gate" not in packs

    def test_advisory_load_mode_not_included(self):
        """Packs with load_mode=advisory should be skipped."""
        fake_registry = [
            {"name": "advisory_pack", "load_mode": "advisory", "repo_type": ["all"], "task_type": ["all"], "risk_level": ["all"]},
            {"name": "always_pack", "load_mode": "always", "repo_type": ["all"], "task_type": ["all"], "risk_level": ["all"]},
        ]
        result = filter_rule_packs(fake_registry, repo_type="tooling")
        assert "advisory_pack" not in result
        assert "always_pack" in result
