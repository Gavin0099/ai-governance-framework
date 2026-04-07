import pytest
from pathlib import Path

from governance_tools.adopt_governance import (
    _detect_repo_type,
    _get_default_rule_packs,
    _write_payload_layering_config,
    _write_session_defaults,
)


class TestDetectRepoType:

    def test_firmware_by_cmake(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("")
        assert _detect_repo_type(tmp_path) == "firmware"

    def test_firmware_by_inf(self, tmp_path):
        (tmp_path / "driver.inf").write_text("")
        assert _detect_repo_type(tmp_path) == "firmware"

    def test_product_by_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        assert _detect_repo_type(tmp_path) == "product"

    def test_service_by_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")
        assert _detect_repo_type(tmp_path) == "service"

    def test_service_by_setup_py(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup")
        assert _detect_repo_type(tmp_path) == "service"

    def test_generic_empty(self, tmp_path):
        assert _detect_repo_type(tmp_path) == "generic"


class TestGetDefaultRulePacks:

    def test_no_onboarding_in_product(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        packs = _get_default_rule_packs(tmp_path)
        assert "onboarding" not in packs

    def test_includes_common_for_product(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        packs = _get_default_rule_packs(tmp_path)
        assert "common" in packs

    def test_firmware_gets_cpp(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("")
        packs = _get_default_rule_packs(tmp_path)
        assert "cpp" in packs
        assert "onboarding" not in packs

    def test_firmware_no_onboarding(self, tmp_path):
        (tmp_path / "driver.inf").write_text("")
        packs = _get_default_rule_packs(tmp_path)
        assert "onboarding" not in packs

    def test_generic_only_common(self, tmp_path):
        packs = _get_default_rule_packs(tmp_path)
        assert "common" in packs
        assert "onboarding" not in packs

    def test_returns_list(self, tmp_path):
        packs = _get_default_rule_packs(tmp_path)
        assert isinstance(packs, list)


class TestWritePayloadLayeringConfig:

    def test_config_file_created(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        assert (tmp_path / ".governance-payload-config.yaml").exists()

    def test_config_has_payload_layering_key(self, tmp_path):
        _write_payload_layering_config(tmp_path, "firmware")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "payload_layering:" in text

    def test_config_repo_type_matches(self, tmp_path):
        _write_payload_layering_config(tmp_path, "firmware")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "repo_type: firmware" in text

    def test_l0_domain_policy_is_skip(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "domain_contract_policy: skip" in text

    def test_memory_policy_is_incremental(self, tmp_path):
        _write_payload_layering_config(tmp_path, "service")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "memory_policy: incremental" in text

    def test_config_has_authority_path(self, tmp_path):
        _write_payload_layering_config(tmp_path, "generic")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "authority_table_path:" in text

    def test_config_version_present(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "version:" in text

    def test_l0_always_load_list_nonempty(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        text = (tmp_path / ".governance-payload-config.yaml").read_text()
        assert "always_load:" in text
        # At least one item follows always_load
        assert "- governance/" in text or "- " in text.split("always_load:")[1].split("\n")[1]


class TestWriteSessionDefaults:

    def test_session_defaults_added(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "product")

        text = state_file.read_text()
        assert "session_defaults:" in text

    def test_repo_type_stored(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "firmware")

        text = state_file.read_text()
        assert "repo_type: firmware" in text

    def test_domain_summary_first_true(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "product")

        text = state_file.read_text()
        assert "domain_summary_first: true" in text

    def test_memory_mode_incremental(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "service")

        text = state_file.read_text()
        assert "memory_mode: incremental" in text

    def test_no_crash_when_state_missing(self, tmp_path):
        """state.yaml 不存在時不應 crash。"""
        _write_session_defaults(tmp_path, "service")  # should not raise

    def test_existing_state_keys_preserved(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\nexisting_key: preserved\n")

        _write_session_defaults(tmp_path, "product")

        text = state_file.read_text()
        assert "existing_key: preserved" in text
