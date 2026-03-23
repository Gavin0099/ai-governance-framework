import pytest
import yaml
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
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert "payload_layering" in config

    def test_config_repo_type_matches(self, tmp_path):
        _write_payload_layering_config(tmp_path, "firmware")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert config["payload_layering"]["repo_type"] == "firmware"

    def test_l0_domain_policy_is_skip(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert config["payload_layering"]["l0_context"]["domain_contract_policy"] == "skip"

    def test_memory_policy_is_incremental(self, tmp_path):
        _write_payload_layering_config(tmp_path, "service")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert config["payload_layering"]["memory_policy"] == "incremental"

    def test_config_has_authority_path(self, tmp_path):
        _write_payload_layering_config(tmp_path, "generic")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert "authority_table_path" in config["payload_layering"]

    def test_config_version_present(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert "version" in config["payload_layering"]

    def test_l0_always_load_list_nonempty(self, tmp_path):
        _write_payload_layering_config(tmp_path, "product")
        config = yaml.safe_load(
            (tmp_path / ".governance-payload-config.yaml").read_text()
        )
        assert len(config["payload_layering"]["l0_context"]["always_load"]) > 0


class TestWriteSessionDefaults:

    def test_session_defaults_added(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "product")

        state = yaml.safe_load(state_file.read_text())
        assert "session_defaults" in state

    def test_repo_type_stored(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "firmware")

        state = yaml.safe_load(state_file.read_text())
        assert state["session_defaults"]["repo_type"] == "firmware"

    def test_domain_summary_first_true(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "product")

        state = yaml.safe_load(state_file.read_text())
        assert state["session_defaults"]["domain_summary_first"] is True

    def test_memory_mode_incremental(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\n")

        _write_session_defaults(tmp_path, "service")

        state = yaml.safe_load(state_file.read_text())
        assert state["session_defaults"]["memory_mode"] == "incremental"

    def test_no_crash_when_state_missing(self, tmp_path):
        """state.yaml 不存在時不應 crash。"""
        _write_session_defaults(tmp_path, "service")  # should not raise

    def test_existing_state_keys_preserved(self, tmp_path):
        state_file = tmp_path / ".governance-state.yaml"
        state_file.write_text("authority_version: '1.0.0'\nexisting_key: preserved\n")

        _write_session_defaults(tmp_path, "product")

        state = yaml.safe_load(state_file.read_text())
        assert state.get("existing_key") == "preserved"
