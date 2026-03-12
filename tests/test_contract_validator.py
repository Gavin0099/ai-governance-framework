"""
Unit tests for governance_tools/contract_validator.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.contract_validator import (
    extract_contract_block,
    format_json,
    parse_contract_fields,
    validate_contract,
)


def _make_contract(**overrides) -> str:
    fields = {
        "LANG": "C++",
        "LEVEL": "L2",
        "SCOPE": "feature",
        "PLAN": "PLAN.md",
        "LOADED": "SYSTEM_PROMPT, HUMAN-OVERSIGHT",
        "CONTEXT": "repo -> runtime-governance; NOT: full-platform rewrite",
        "PRESSURE": "SAFE (45/200)",
        "RULES": "common,python",
        "RISK": "medium",
        "OVERSIGHT": "auto",
        "MEMORY_MODE": "candidate",
    }
    fields.update(overrides)
    body = "\n".join(f"{k} = {v}" for k, v in fields.items())
    return f"[Governance Contract]\n{body}\n"


class TestExtractContractBlock:
    def test_plain_text_format(self):
        text = "[Governance Contract]\nLANG = C++\nLEVEL = L2\n"
        assert extract_contract_block(text) is not None

    def test_markdown_code_block_format(self):
        text = "```\n[Governance Contract]\nLANG = C++\n```"
        assert extract_contract_block(text) is not None

    def test_missing_returns_none(self):
        assert extract_contract_block("no contract here") is None


class TestParseContractFields:
    def test_basic_key_value(self):
        fields = parse_contract_fields("[Governance Contract]\nLANG = C++\nLEVEL = L2\n")
        assert fields["LANG"] == "C++"
        assert fields["LEVEL"] == "L2"

    def test_empty_block(self):
        assert parse_contract_fields("") == {}


class TestValidateContractInvalid:
    def test_no_contract_block(self):
        result = validate_contract("no contract here")
        assert not result.contract_found
        assert not result.compliant

    def test_invalid_lang(self):
        result = validate_contract(_make_contract(LANG="Python"))
        assert any("LANG" in e for e in result.errors)

    def test_missing_loaded(self):
        result = validate_contract(_make_contract(LOADED=""))
        assert any("LOADED" in e for e in result.errors)

    def test_missing_not_clause(self):
        result = validate_contract(_make_contract(CONTEXT="repo -> scope"))
        assert any("NOT:" in e for e in result.errors)

    def test_invalid_pressure(self):
        result = validate_contract(_make_contract(PRESSURE="UNKNOWN (10/200)"))
        assert any("PRESSURE" in e for e in result.errors)

    def test_missing_rules(self):
        result = validate_contract(_make_contract(RULES=""))
        assert any("RULES" in e for e in result.errors)

    def test_unknown_rule_pack(self):
        result = validate_contract(_make_contract(RULES="common,missing-pack"))
        assert any("unknown rule pack" in e.lower() for e in result.errors)

    def test_invalid_risk(self):
        result = validate_contract(_make_contract(RISK="critical"))
        assert any("RISK" in e for e in result.errors)

    def test_invalid_oversight(self):
        result = validate_contract(_make_contract(OVERSIGHT="manual"))
        assert any("OVERSIGHT" in e for e in result.errors)

    def test_invalid_memory_mode(self):
        result = validate_contract(_make_contract(MEMORY_MODE="archive"))
        assert any("MEMORY_MODE" in e for e in result.errors)

    def test_agent_id_requires_session(self):
        result = validate_contract(_make_contract(AGENT_ID="coder-01"))
        assert any("SESSION" in e for e in result.errors)


class TestValidateContractCompliant:
    @pytest.mark.parametrize("lang", ["C++", "C#", "ObjC", "Swift", "JS"])
    def test_all_valid_langs(self, lang):
        assert validate_contract(_make_contract(LANG=lang)).compliant

    @pytest.mark.parametrize("level", ["L0", "L1", "L2"])
    def test_all_valid_levels(self, level):
        assert validate_contract(_make_contract(LEVEL=level)).compliant

    @pytest.mark.parametrize("scope", ["feature", "refactor", "bugfix", "I/O", "tooling", "review"])
    def test_all_valid_scopes(self, scope):
        assert validate_contract(_make_contract(SCOPE=scope)).compliant

    @pytest.mark.parametrize("pressure", ["SAFE", "WARNING", "CRITICAL", "EMERGENCY"])
    def test_all_valid_pressure_levels(self, pressure):
        assert validate_contract(_make_contract(PRESSURE=f"{pressure} (50/200)")).compliant

    def test_full_contract(self):
        result = validate_contract(_make_contract())
        assert result.compliant
        assert result.errors == []

    def test_missing_plan_is_warning(self):
        result = validate_contract(_make_contract(PLAN=""))
        assert result.compliant
        assert any("PLAN" in w for w in result.warnings)

    def test_pressure_without_line_count_is_warning(self):
        result = validate_contract(_make_contract(PRESSURE="SAFE"))
        assert result.compliant
        assert any("PRESSURE" in w for w in result.warnings)

    def test_session_without_agent_id_is_warning(self):
        result = validate_contract(_make_contract(SESSION="2026-03-06-01"))
        assert result.compliant
        assert any("SESSION" in w for w in result.warnings)


class TestFormatJson:
    def test_json_output_has_required_keys(self):
        output = json.loads(format_json(validate_contract(_make_contract())))
        for key in ("compliant", "contract_found", "fields", "errors", "warnings"):
            assert key in output

    def test_json_is_valid_json(self):
        assert isinstance(json.loads(format_json(validate_contract("no contract"))), dict)
