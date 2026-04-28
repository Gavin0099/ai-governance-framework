#!/usr/bin/env python3
"""
Tests for governance_tools/reasoning_compressor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reasoning_compressor import (
    _PROSE_TRUNCATE_LEN,
    classify_violation_type,
    compress_fragment,
    compress_fragments,
    estimate_compression_ratio,
    extract_policy_refs,
    extract_rule_ids,
)


# ── classify_violation_type ──────────────────────────────────────────────────

class TestClassifyViolationType:

    def test_missing_evidence(self):
        assert classify_violation_type("missing evidence for rule") == "missing_evidence"

    def test_evidence_not_provided(self):
        assert classify_violation_type("evidence was not provided") == "missing_evidence"

    def test_staleness(self):
        assert classify_violation_type("PLAN.md is stale and outdated") == "staleness_violation"

    def test_freshness(self):
        assert classify_violation_type("freshness check failed") == "staleness_violation"

    def test_invalid_rule_pack(self):
        assert classify_violation_type("unknown rule pack detected") == "invalid_rule_pack"

    def test_contract_violation(self):
        assert classify_violation_type("contract violation detected") == "contract_violation"

    def test_hard_stop(self):
        assert classify_violation_type("hard-stop condition triggered") == "hard_stop"

    def test_blocked(self):
        assert classify_violation_type("operation is blocked") == "hard_stop"

    def test_permission_violation(self):
        assert classify_violation_type("permission denied for action") == "permission_violation"

    def test_schema_violation(self):
        assert classify_violation_type("schema is invalid") == "schema_violation"

    def test_placeholder(self):
        assert classify_violation_type("placeholder not filled in") == "incomplete_artifact"

    def test_unknown_defaults_to_generic(self):
        assert classify_violation_type("something unexpected happened") == "generic_violation"

    def test_case_insensitive(self):
        assert classify_violation_type("MISSING EVIDENCE") == "missing_evidence"
        assert classify_violation_type("STALE PLAN") == "staleness_violation"

    def test_empty_string(self):
        assert classify_violation_type("") == "generic_violation"


# ── extract_policy_refs ───────────────────────────────────────────────────────

class TestExtractPolicyRefs:

    def test_extracts_runtime_policy(self):
        refs = extract_policy_refs("Violates RUNTIME_POLICY_023 section 3")
        assert "RUNTIME_POLICY_023" in refs

    def test_extracts_kdc_ref(self):
        refs = extract_policy_refs("See KDC-3.2 for details")
        assert "KDC-3.2" in refs

    def test_extracts_usb_hub_ref(self):
        refs = extract_policy_refs("USB-HUB-1.0 compliance required")
        assert "USB-HUB-1.0" in refs

    def test_extracts_p_ref(self):
        refs = extract_policy_refs("per P-023 requirements")
        assert "P-023" in refs

    def test_no_refs_returns_empty(self):
        refs = extract_policy_refs("no policy references here")
        assert refs == []

    def test_deduplicates(self):
        refs = extract_policy_refs("RUNTIME_POLICY_023 and RUNTIME_POLICY_023 again")
        assert refs.count("RUNTIME_POLICY_023") == 1

    def test_multiple_refs(self):
        refs = extract_policy_refs("See RUNTIME_POLICY_023 and KDC-3.2")
        assert "RUNTIME_POLICY_023" in refs
        assert "KDC-3.2" in refs

    def test_empty_string_returns_empty(self):
        assert extract_policy_refs("") == []


# ── extract_rule_ids ──────────────────────────────────────────────────────────

class TestExtractRuleIds:

    def test_extracts_rule_suffix_pattern(self):
        ids = extract_rule_ids("violates SAFETY_RULE_001 constraint")
        assert "SAFETY_RULE_001" in ids

    def test_extracts_rule_prefix_pattern(self):
        ids = extract_rule_ids("see RULE_ALPHA for context")
        assert "RULE_ALPHA" in ids

    def test_runtime_policy_not_a_rule_id(self):
        # RUNTIME_POLICY_023 is a policy ref, not a rule ID per RULE_ID_PATTERN
        # It should be extracted by extract_policy_refs() instead
        ids = extract_rule_ids("RUNTIME_POLICY_023 must be followed")
        assert "RUNTIME_POLICY_023" not in ids

    def test_empty_string_returns_empty(self):
        assert extract_rule_ids("") == []

    def test_deduplicates(self):
        ids = extract_rule_ids("SAFETY_RULE_001 and SAFETY_RULE_001 again")
        assert ids.count("SAFETY_RULE_001") == 1


# ── compress_fragment ─────────────────────────────────────────────────────────

class TestCompressFragment:

    def test_returns_rule_id(self):
        result = compress_fragment("missing evidence for ISR rule")
        assert "rule_id" in result

    def test_returns_violation_type(self):
        result = compress_fragment("missing evidence for ISR rule")
        assert "violation_type" in result

    def test_returns_policy_refs(self):
        result = compress_fragment("missing evidence per RUNTIME_POLICY_023")
        assert "policy_refs" in result

    def test_returns_severity(self):
        result = compress_fragment("some reasoning text")
        assert "severity" in result

    def test_keeps_prose_by_default(self):
        result = compress_fragment("some reasoning text")
        assert "prose" in result

    def test_prose_matches_input_when_short(self):
        result = compress_fragment("short text")
        assert result["prose"] == "short text"

    def test_excludes_prose_when_flag_false(self):
        result = compress_fragment("some reasoning text", keep_prose=False)
        assert "prose" not in result

    def test_truncates_long_prose(self):
        long_prose = "x" * 300
        result = compress_fragment(long_prose, keep_prose=True)
        assert result["prose"].endswith("...")
        # Content portion should be _PROSE_TRUNCATE_LEN chars + "..."
        assert len(result["prose"]) == _PROSE_TRUNCATE_LEN + 3

    def test_does_not_truncate_exact_limit(self):
        prose = "x" * _PROSE_TRUNCATE_LEN
        result = compress_fragment(prose, keep_prose=True)
        assert not result["prose"].endswith("...")
        assert len(result["prose"]) == _PROSE_TRUNCATE_LEN

    def test_uses_provided_rule_id(self):
        result = compress_fragment("some text", rule_id="CUSTOM_RULE_001")
        assert result["rule_id"] == "CUSTOM_RULE_001"

    def test_extracts_rule_id_from_prose(self):
        result = compress_fragment("violates SAFETY_RULE_001 constraint")
        assert result["rule_id"] == "SAFETY_RULE_001"

    def test_unknown_rule_id_when_no_match(self):
        result = compress_fragment("some text with no ids")
        assert result["rule_id"] == "UNKNOWN"

    def test_default_severity_is_medium(self):
        result = compress_fragment("some text")
        assert result["severity"] == "medium"

    def test_custom_severity(self):
        result = compress_fragment("some text", severity="high")
        assert result["severity"] == "high"

    def test_policy_refs_extracted_from_prose(self):
        result = compress_fragment("see RUNTIME_POLICY_023 for details")
        assert "RUNTIME_POLICY_023" in result["policy_refs"]

    def test_missing_evidence_classification(self):
        result = compress_fragment("missing evidence for the rule")
        assert result["violation_type"] == "missing_evidence"


# ── compress_fragments ────────────────────────────────────────────────────────

class TestCompressFragments:

    def test_handles_empty_list(self):
        result = compress_fragments([])
        assert result == []

    def test_handles_string_list(self):
        fragments = ["missing evidence", "stale PLAN.md"]
        result = compress_fragments(fragments)
        assert len(result) == 2
        assert all("rule_id" in r for r in result)

    def test_handles_dict_list(self):
        fragments = [{"rule_id": "R001", "prose": "missing evidence"}]
        result = compress_fragments(fragments)
        assert len(result) == 1
        assert result[0]["rule_id"] == "R001"

    def test_handles_mixed_list(self):
        fragments = [
            "plain text fragment",
            {"rule_id": "R002", "prose": "dict fragment"},
        ]
        result = compress_fragments(fragments)
        assert len(result) == 2

    def test_dict_preserves_existing_rule_id(self):
        fragments = [{"rule_id": "MY_RULE", "prose": "some text"}]
        result = compress_fragments(fragments)
        assert result[0]["rule_id"] == "MY_RULE"

    def test_dict_extracts_text_field(self):
        fragments = [{"text": "some reasoning here"}]
        result = compress_fragments(fragments)
        assert len(result) == 1
        assert "rule_id" in result[0]

    def test_dict_preserves_extra_fields(self):
        fragments = [{"prose": "some text", "custom_field": "custom_value"}]
        result = compress_fragments(fragments)
        assert result[0].get("custom_field") == "custom_value"

    def test_keep_prose_false_for_all(self):
        fragments = ["text one", "text two"]
        result = compress_fragments(fragments, keep_prose=False)
        assert all("prose" not in r for r in result)

    def test_keep_prose_true_for_all(self):
        fragments = ["text one", "text two"]
        result = compress_fragments(fragments, keep_prose=True)
        assert all("prose" in r for r in result)


# ── estimate_compression_ratio ────────────────────────────────────────────────

class TestEstimateCompressionRatio:

    def test_returns_required_keys(self):
        fragments = ["This is a long reasoning fragment"]
        result = estimate_compression_ratio(fragments)
        assert "original_tokens" in result
        assert "compressed_tokens" in result
        assert "reduction" in result
        assert "reduction_pct" in result

    def test_compression_reduces_tokens_on_verbose_input(self):
        """壓縮後 token 應該比原始少（verbose prose 壓縮效果）。"""
        fragments = [
            "Detected missing evidence because rule RUNTIME_POLICY_023 requires ISR evidence "
            "but none was provided in the task context. This violates the kernel driver contract "
            "section 3.2 which clearly states that all interrupt service routine modifications "
            "must be accompanied by proper evidence documentation. The rule was introduced in "
            "version 1.2 of the governance framework to prevent undocumented ISR changes."
        ] * 5
        result = estimate_compression_ratio(fragments)
        assert result["reduction"] > 0

    def test_handles_empty_list(self):
        result = estimate_compression_ratio([])
        assert result["original_tokens"] == 1  # max(0//4, 1) = 1
        assert result["compressed_tokens"] >= 0

    def test_reduction_pct_type_is_float(self):
        fragments = ["some text to compress"] * 3
        result = estimate_compression_ratio(fragments)
        assert isinstance(result["reduction_pct"], float)

    def test_original_tokens_positive_for_nonempty_input(self):
        fragments = ["x" * 100]
        result = estimate_compression_ratio(fragments)
        assert result["original_tokens"] > 0
