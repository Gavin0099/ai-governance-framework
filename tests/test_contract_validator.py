"""
Unit tests for governance_tools/contract_validator.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.contract_validator import (
    DISPLAY_CONTRACT_FIELDS,
    RUNTIME_CONTRACT_FIELDS,
    extract_contract_block,
    normalize_loaded_identifier,
    validate_display_contract,
    validate_runtime_contract,
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
        result = validate_contract(_make_contract(LANG="Rust"))
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
    @pytest.mark.parametrize("lang", ["C", "C++", "C#", "ObjC", "Swift", "JS", "Python", "Verilog", "SystemVerilog"])
    def test_all_valid_langs(self, lang):
        assert validate_contract(_make_contract(LANG=lang)).compliant

    @pytest.mark.parametrize("level", ["L0", "L1", "L2"])
    def test_all_valid_levels(self, level):
        assert validate_contract(_make_contract(LEVEL=level)).compliant

    @pytest.mark.parametrize("scope", ["feature", "refactor", "bugfix", "I/O", "tooling", "review", "governance", "kernel-driver"])
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

    def test_pressure_without_line_count_is_an_error(self):
        """This used to be a warning, which is what let filler counts through.

        §2.8 requires a label *and* a line count, and calls a malformed block a
        governance failure; tolerating a missing count contradicted both.
        """
        result = validate_contract(_make_contract(PRESSURE="SAFE"))

        assert result.compliant is False
        assert any("PRESSURE invalid" in e for e in result.errors)

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


def test_loaded_without_human_oversight_is_valid():
    """SYSTEM_PROMPT.md §2.8 forbids listing HUMAN-OVERSIGHT unless a human
    supplied it, so requiring it here made the canonical rule unsatisfiable."""
    result = validate_contract(_make_contract(LOADED="SYSTEM_PROMPT, AGENT, TESTING"))

    assert result.compliant is True, result.errors
    assert not any("HUMAN-OVERSIGHT" in error for error in result.errors)


def test_loaded_still_requires_system_prompt():
    result = validate_contract(_make_contract(LOADED="AGENT, TESTING"))

    assert result.compliant is False
    assert any("SYSTEM_PROMPT" in error for error in result.errors)


class TestLangCardinality:
    """SYSTEM_PROMPT.md §2.8 allows a comma-separated LANG list (decision 2B)."""

    def test_single_language_still_valid(self):
        assert validate_contract(_make_contract(LANG="C++")).compliant is True

    def test_comma_separated_languages_are_valid(self):
        assert validate_contract(_make_contract(LANG="C, C++")).compliant is True

    def test_separator_tolerates_missing_whitespace(self):
        assert validate_contract(_make_contract(LANG="C,C++")).compliant is True

    def test_slash_form_is_rejected_with_a_migration_hint(self):
        """`/` cannot separate a list: `I/O` is already a SCOPE value."""
        result = validate_contract(_make_contract(LANG="C/C++"))

        assert result.compliant is False
        error = next(e for e in result.errors if e.startswith("LANG"))
        assert "C/C++" in error
        assert "'C, C++'" in error

    def test_unknown_language_in_a_list_is_rejected(self):
        result = validate_contract(_make_contract(LANG="C, Rust"))

        assert result.compliant is False
        assert any("Rust" in e for e in result.errors)

    def test_duplicate_languages_are_rejected(self):
        result = validate_contract(_make_contract(LANG="C, C"))

        assert result.compliant is False
        assert any("duplicate" in e for e in result.errors)

    def test_empty_lang_is_still_required(self):
        result = validate_contract(_make_contract(LANG=""))

        assert result.compliant is False
        assert any("LANG field is required" in e for e in result.errors)


class TestScopeCardinality:
    """SCOPE stays single-valued (decision 3): it drives routing, LANG does not."""

    def test_single_scope_is_valid(self):
        assert validate_contract(_make_contract(SCOPE="tooling")).compliant is True

    def test_io_scope_containing_a_slash_is_still_valid(self):
        """Guards the reason `/` was rejected as a LANG separator."""
        assert validate_contract(_make_contract(SCOPE="I/O")).compliant is True

    def test_comma_separated_scope_is_rejected_with_reason(self):
        result = validate_contract(_make_contract(SCOPE="tooling, review"))

        assert result.compliant is False
        error = next(e for e in result.errors if e.startswith("SCOPE"))
        assert "single-valued" in error

    def test_slash_separated_scope_is_rejected(self):
        result = validate_contract(_make_contract(SCOPE="tooling / review"))

        assert result.compliant is False
        assert any(e.startswith("SCOPE invalid") for e in result.errors)


class TestContractAuthoritySplit:
    """Decision 1B: display and runtime contracts validate separately."""

    DISPLAY_ONLY = {
        "LANG": "C, C++", "LEVEL": "L2", "SCOPE": "kernel-driver", "PLAN": "PLAN.md",
        "LOADED": "SYSTEM_PROMPT", "CONTEXT": "repo -> x; NOT: y",
        "PRESSURE": "SAFE (10/200)",
    }

    def _block(self, fields):
        body = "\n".join(f"{k} = {v}" for k, v in fields.items())
        return f"[Governance Contract]\n{body}\n"

    def test_field_groups_do_not_overlap(self):
        assert not set(DISPLAY_CONTRACT_FIELDS) & set(RUNTIME_CONTRACT_FIELDS)

    def test_display_only_block_passes_display_validation(self):
        result = validate_display_contract(self._block(self.DISPLAY_ONLY))

        assert result.compliant is True

    def test_display_only_block_fails_runtime_validation(self):
        """A display pass says nothing about whether a task may execute."""
        result = validate_runtime_contract(self._block(self.DISPLAY_ONLY))

        assert result.compliant is False
        assert any("RULES" in e for e in result.errors)

    def test_validate_contract_still_requires_runtime_fields_by_default(self):
        """The migration must not silently stop checking the runtime fields.

        Relaxing this default would leave resolved_rules empty and MEMORY_MODE
        falling back to candidate, disabling rule routing and the durable-memory
        oversight gate with nothing reported.
        """
        result = validate_contract(self._block(self.DISPLAY_ONLY))

        assert result.compliant is False

    def test_opting_out_of_runtime_validation_is_explicit(self):
        assert validate_contract(
            self._block(self.DISPLAY_ONLY), include_runtime=False
        ).compliant is True

    def test_full_block_passes_all_three_entry_points(self):
        result = validate_contract(_make_contract())

        assert result.compliant is True
        assert validate_display_contract(_make_contract()).compliant is True
        assert validate_runtime_contract(_make_contract()).compliant is True

    def test_runtime_validation_ignores_display_field_errors(self):
        """Each validator answers to its own authority."""
        broken_display = dict(self.DISPLAY_ONLY)
        broken_display["LANG"] = "Rust"
        broken_display.update(
            {"RULES": "common", "RISK": "low", "OVERSIGHT": "auto", "MEMORY_MODE": "candidate"}
        )

        assert validate_runtime_contract(self._block(broken_display)).compliant is True
        assert validate_display_contract(self._block(broken_display)).compliant is False


class TestLoadedIdentifierNormalization:
    """§2.8: last path segment, optional `.md`, case-sensitive.

    Observed in a real Copilot session: the reply that had actually read the file
    wrote the full path and failed this check, while the bare token passed. The
    rule named `SYSTEM_PROMPT` without saying whether that was a token or a path.
    """

    def test_bare_token_is_accepted(self):
        assert validate_contract(_make_contract(LOADED="SYSTEM_PROMPT")).compliant is True

    def test_filename_is_accepted(self):
        assert validate_contract(_make_contract(LOADED="SYSTEM_PROMPT.md")).compliant is True

    def test_relative_path_is_accepted(self):
        assert validate_contract(
            _make_contract(LOADED="governance/SYSTEM_PROMPT.md")
        ).compliant is True

    def test_windows_path_is_accepted(self):
        """The exact form emitted by Copilot in the observed session."""
        assert validate_contract(
            _make_contract(LOADED=r"ai-governance-framework\governance\SYSTEM_PROMPT.md")
        ).compliant is True

    def test_mixed_forms_in_one_list_are_accepted(self):
        assert validate_contract(
            _make_contract(LOADED="governance/SYSTEM_PROMPT.md, AGENT, TESTING.md")
        ).compliant is True

    @pytest.mark.parametrize(
        "loaded",
        [
            "SYSTEM_PROMPT.txt",       # only .md may be omitted
            "SYSTEM_PROMPT.md.bak",
            "MY_SYSTEM_PROMPT.md",     # suffix match must not count
            "SYSTEM_PROMPTS.md",
            "system_prompt",           # matching is case-sensitive
            "governance/AGENT.md",     # a different document
        ],
    )
    def test_similar_names_are_rejected(self, loaded):
        result = validate_contract(_make_contract(LOADED=loaded))

        assert result.compliant is False
        assert any("LOADED missing required documents" in e for e in result.errors)

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("SYSTEM_PROMPT", "SYSTEM_PROMPT"),
            ("SYSTEM_PROMPT.md", "SYSTEM_PROMPT"),
            ("governance/SYSTEM_PROMPT.md", "SYSTEM_PROMPT"),
            (r"a\b\SYSTEM_PROMPT.md", "SYSTEM_PROMPT"),
            ("  SYSTEM_PROMPT.md  ", "SYSTEM_PROMPT"),
            ("SYSTEM_PROMPT.txt", "SYSTEM_PROMPT.txt"),
            ("MY_SYSTEM_PROMPT.md", "MY_SYSTEM_PROMPT"),
        ],
    )
    def test_normalization_is_exact(self, raw, expected):
        assert normalize_loaded_identifier(raw) == expected


class TestPressureLineCount:
    """§2.8 requires a label and a line count; the count has to be a real number.

    Observed passing before this check existed, in real sessions and fixtures:
    an unfilled template, a placeholder phrase, a negative count and a wrong
    denominator. A number that cannot be read is not evidence of memory pressure.
    """

    @pytest.mark.parametrize(
        "pressure",
        [
            "SAFE (0/200)",
            "SAFE (39/200)",
            "WARNING (185/200)",
            "CRITICAL (210/200)",
            "EMERGENCY (260/200)",
            "SAFE(39/200)",
            "SAFE ( 39 / 200 )",
        ],
    )
    def test_real_line_counts_are_accepted(self, pressure):
        assert validate_contract(_make_contract(PRESSURE=pressure)).compliant is True

    @pytest.mark.parametrize(
        "pressure",
        [
            "SAFE (<line count>/200)",              # template never filled in
            "SAFE (pending exact line count/200)",  # observed in a real session
            "SAFE (abc/200)",
            "SAFE (39.5/200)",
            "SAFE (-5/200)",
            "SAFE 39/200",                          # no parentheses
            "SAFE",                                 # was only a warning before
        ],
    )
    def test_unreadable_line_counts_are_rejected(self, pressure):
        result = validate_contract(_make_contract(PRESSURE=pressure))

        assert result.compliant is False
        assert any(e.startswith("PRESSURE invalid") for e in result.errors)

    def test_wrong_denominator_is_rejected_with_its_own_message(self):
        result = validate_contract(_make_contract(PRESSURE="SAFE (39/999)"))

        assert result.compliant is False
        assert any("denominator invalid" in e for e in result.errors)

    def test_unknown_level_is_still_reported_as_a_level_problem(self):
        result = validate_contract(_make_contract(PRESSURE="NOTALEVEL (39/200)"))

        assert result.compliant is False
        assert any("NOTALEVEL" in e and "Allowed" in e for e in result.errors)

    def test_missing_pressure_is_still_required(self):
        result = validate_contract(_make_contract(PRESSURE=""))

        assert result.compliant is False
        assert any("PRESSURE field is required" in e for e in result.errors)


class TestPressureCharCountForm:
    """§7.4 escalates on lines *or* characters; §2.8 now has room to say which.

    Observed: `WARNING (87/200 lines; 9642 chars)` from a real session. 87 lines
    is below the 180-line threshold, so WARNING is correct only because 9642
    characters crossed 8000. The short form cannot show that, and rejecting the
    long form punished the output that best evidenced its own level.
    """

    @pytest.mark.parametrize(
        "pressure",
        [
            "WARNING (87/200 lines; 9642 chars)",
            "WARNING (87/200 lines;9642 chars)",
            "EMERGENCY (260/200 lines; 13000 chars)",
            "SAFE (0/200 lines; 0 chars)",
        ],
    )
    def test_char_count_form_is_accepted(self, pressure):
        assert validate_contract(_make_contract(PRESSURE=pressure)).compliant is True

    def test_short_form_remains_valid(self):
        assert validate_contract(_make_contract(PRESSURE="SAFE (45/200)")).compliant is True

    @pytest.mark.parametrize(
        "pressure",
        [
            "SAFE (87/200 lines; abc chars)",  # char count must be a number too
            "SAFE (87/200 lines)",             # half the suffix
            "SAFE (87/200; 9642 chars)",       # suffix without the `lines` label
            "SAFE (<line count>/200 lines; <char count> chars)",
        ],
    )
    def test_partial_or_filler_suffix_is_rejected(self, pressure):
        result = validate_contract(_make_contract(PRESSURE=pressure))

        assert result.compliant is False
        assert any(e.startswith("PRESSURE invalid") for e in result.errors)

    def test_the_block_observed_in_the_session_validates(self):
        """Regression for the exact form that a real agent emitted."""
        result = validate_contract(
            _make_contract(PRESSURE="WARNING (87/200 lines; 9642 chars)")
        )

        assert result.compliant is True
