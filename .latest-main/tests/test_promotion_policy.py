"""
Tests for memory_pipeline/promotion_policy.py

Coverage:
- Step 3 新增：get_source_authority, get_promotion_behavior
- Step 3 新增：classify_promotion_policy with source_file parameter
- 現有邏輯：classify_promotion_policy without source_file（regression guard）
- 常數一致性：MEMORY_SOURCE_AUTHORITY, PROMOTION_BEHAVIOR
"""

from __future__ import annotations

import pytest

from memory_pipeline.promotion_policy import (
    MEMORY_SOURCE_AUTHORITY,
    PROMOTION_BEHAVIOR,
    classify_promotion_policy,
    get_promotion_behavior,
    get_source_authority,
)


# ---------------------------------------------------------------------------
# get_source_authority
# ---------------------------------------------------------------------------

class TestGetSourceAuthority:

    def test_canonical_exact_match_project_facts(self):
        assert get_source_authority("02_project_facts.md") == "canonical"

    def test_canonical_exact_match_decisions(self):
        assert get_source_authority("03_decisions.md") == "canonical"

    def test_reference_exact_match_patterns(self):
        assert get_source_authority("04_patterns.md") == "reference"

    def test_reference_exact_match_aliases(self):
        assert get_source_authority("external_repo_aliases") == "reference"

    def test_derived_exact_match_reviewer_handoff(self):
        assert get_source_authority("reviewer_handoff") == "derived"

    def test_derived_exact_match_framework_artifact(self):
        assert get_source_authority("framework_artifact") == "derived"

    def test_derived_exact_match_session_summary(self):
        assert get_source_authority("session_summary") == "derived"

    def test_derived_prefix_match_reviewer_handoff_dated(self):
        """reviewer_handoff_2026-03-18.md → derived (prefix match)"""
        assert get_source_authority("reviewer_handoff_2026-03-18.md") == "derived"

    def test_derived_prefix_match_framework_artifact_versioned(self):
        assert get_source_authority("framework_artifact_cache_v2.md") == "derived"

    def test_derived_prefix_match_session_summary_with_suffix(self):
        assert get_source_authority("session_summary_20260318.json") == "derived"

    def test_unknown_source_defaults_to_reference(self):
        assert get_source_authority("unknown_file.md") == "reference"
        assert get_source_authority("some_random_source") == "reference"
        assert get_source_authority("my_notes.txt") == "reference"

    def test_path_with_forward_slashes(self):
        assert get_source_authority("memory/02_project_facts.md") == "canonical"
        assert get_source_authority("memory/reviewer_handoff.md") == "derived"

    def test_path_with_backslashes(self):
        assert get_source_authority("memory\\03_decisions.md") == "canonical"

    def test_absolute_path(self):
        assert get_source_authority("/full/path/to/03_decisions.md") == "canonical"

    def test_empty_string_defaults_to_reference(self):
        assert get_source_authority("") == "reference"

    def test_none_not_passed_directly(self):
        # None is not a valid type, but empty string is the sentinel
        assert get_source_authority("") == "reference"


# ---------------------------------------------------------------------------
# get_promotion_behavior
# ---------------------------------------------------------------------------

class TestGetPromotionBehavior:

    def test_canonical_promotes(self):
        assert get_promotion_behavior("02_project_facts.md") == "promote"
        assert get_promotion_behavior("03_decisions.md") == "promote"

    def test_derived_cache_only(self):
        assert get_promotion_behavior("reviewer_handoff") == "cache_only"
        assert get_promotion_behavior("framework_artifact") == "cache_only"
        assert get_promotion_behavior("session_summary") == "cache_only"

    def test_reference_evaluates(self):
        assert get_promotion_behavior("04_patterns.md") == "evaluate"
        assert get_promotion_behavior("external_repo_aliases") == "evaluate"

    def test_unknown_evaluates(self):
        assert get_promotion_behavior("mystery_source.md") == "evaluate"

    def test_derived_prefix_cache_only(self):
        assert get_promotion_behavior("reviewer_handoff_2026-03-18.md") == "cache_only"


# ---------------------------------------------------------------------------
# classify_promotion_policy — source_file 前置過濾（Step 3 新增）
# ---------------------------------------------------------------------------

class TestClassifyWithSourceAuthority:

    _low_risk_contract = {"risk": "low", "oversight": "auto", "memory_mode": "candidate", "rules": []}
    _high_risk_contract = {"risk": "high", "oversight": "auto", "memory_mode": "candidate", "rules": []}

    def test_derived_source_always_do_not_promote(self):
        """derived source → DO_NOT_PROMOTE，無論 runtime_contract 如何"""
        result = classify_promotion_policy(
            self._low_risk_contract,
            source_file="reviewer_handoff",
        )
        assert result["decision"] == "DO_NOT_PROMOTE"
        assert "derived" in result["reasons"][0].lower()

    def test_derived_source_overrides_low_risk(self):
        """low-risk + derived source → 仍然 DO_NOT_PROMOTE"""
        result = classify_promotion_policy(
            self._low_risk_contract,
            source_file="session_summary",
        )
        assert result["decision"] == "DO_NOT_PROMOTE"

    def test_derived_prefix_source_do_not_promote(self):
        result = classify_promotion_policy(
            self._low_risk_contract,
            source_file="reviewer_handoff_2026-03-18.md",
        )
        assert result["decision"] == "DO_NOT_PROMOTE"

    def test_canonical_source_auto_promotes(self):
        """canonical source → AUTO_PROMOTE，跳過後續評估"""
        result = classify_promotion_policy(
            self._high_risk_contract,  # high-risk normally → REVIEW_REQUIRED
            source_file="03_decisions.md",
        )
        assert result["decision"] == "AUTO_PROMOTE"
        assert "canonical" in result["reasons"][0].lower()

    def test_canonical_source_overrides_high_risk(self):
        """canonical source 即使 high risk 也直接 promote"""
        contract = {"risk": "high", "oversight": "human-approval", "memory_mode": "durable", "rules": []}
        result = classify_promotion_policy(contract, source_file="02_project_facts.md")
        assert result["decision"] == "AUTO_PROMOTE"

    def test_reference_source_uses_existing_logic_low_risk(self):
        """reference source + low-risk → 走現有邏輯 → AUTO_PROMOTE"""
        result = classify_promotion_policy(
            self._low_risk_contract,
            source_file="04_patterns.md",
        )
        assert result["decision"] == "AUTO_PROMOTE"

    def test_reference_source_uses_existing_logic_high_risk(self):
        """reference source + high-risk → 走現有邏輯 → REVIEW_REQUIRED"""
        result = classify_promotion_policy(
            self._high_risk_contract,
            source_file="04_patterns.md",
        )
        assert result["decision"] == "REVIEW_REQUIRED"

    def test_no_source_file_uses_existing_logic(self):
        """source_file 未傳 → 完全走現有邏輯（backward compat）"""
        result = classify_promotion_policy(self._low_risk_contract)
        assert result["decision"] == "AUTO_PROMOTE"

    def test_empty_source_file_uses_existing_logic(self):
        """source_file="" → 視為未傳，走現有邏輯"""
        result = classify_promotion_policy(self._low_risk_contract, source_file="")
        assert result["decision"] == "AUTO_PROMOTE"


# ---------------------------------------------------------------------------
# classify_promotion_policy — 現有邏輯 regression guard
# ---------------------------------------------------------------------------

class TestClassifyExistingLogicRegression:
    """確保 Step 3 修改沒有 break 原有的 classify_promotion_policy 行為"""

    def test_errors_cause_do_not_promote(self):
        contract = {"risk": "low", "oversight": "auto", "memory_mode": "candidate", "rules": []}
        result = classify_promotion_policy(contract, check_result={"errors": ["fatal error"]})
        assert result["decision"] == "DO_NOT_PROMOTE"

    def test_stateless_mode_do_not_promote(self):
        contract = {"risk": "low", "oversight": "auto", "memory_mode": "stateless", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "DO_NOT_PROMOTE"

    def test_high_risk_review_required(self):
        contract = {"risk": "high", "oversight": "auto", "memory_mode": "candidate", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "REVIEW_REQUIRED"

    def test_human_approval_oversight_review_required(self):
        contract = {"risk": "low", "oversight": "human-approval", "memory_mode": "candidate", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "REVIEW_REQUIRED"

    def test_durable_mode_review_required(self):
        contract = {"risk": "low", "oversight": "auto", "memory_mode": "durable", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "REVIEW_REQUIRED"

    def test_architecture_sensitive_rules_review_required(self):
        contract = {"risk": "low", "oversight": "auto", "memory_mode": "candidate", "rules": ["refactor"]}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "REVIEW_REQUIRED"

    def test_low_risk_auto_promote(self):
        contract = {"risk": "low", "oversight": "auto", "memory_mode": "candidate", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "AUTO_PROMOTE"

    def test_default_medium_risk_review_required(self):
        contract = {"risk": "medium", "oversight": "auto", "memory_mode": "candidate", "rules": []}
        result = classify_promotion_policy(contract)
        assert result["decision"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# 常數一致性
# ---------------------------------------------------------------------------

class TestConstantsConsistency:

    def test_all_authority_values_valid(self):
        valid = {"canonical", "reference", "derived"}
        for source, authority in MEMORY_SOURCE_AUTHORITY.items():
            assert authority in valid, f"{source}: invalid authority '{authority}'"

    def test_all_behavior_keys_valid(self):
        valid = {"canonical", "reference", "derived"}
        for key in PROMOTION_BEHAVIOR:
            assert key in valid, f"Invalid key in PROMOTION_BEHAVIOR: '{key}'"

    def test_all_behavior_values_valid(self):
        valid = {"promote", "evaluate", "cache_only"}
        for authority, behavior in PROMOTION_BEHAVIOR.items():
            assert behavior in valid, f"{authority}: invalid behavior '{behavior}'"

    def test_canonical_maps_to_promote(self):
        assert PROMOTION_BEHAVIOR["canonical"] == "promote"

    def test_derived_maps_to_cache_only(self):
        assert PROMOTION_BEHAVIOR["derived"] == "cache_only"

    def test_reference_maps_to_evaluate(self):
        assert PROMOTION_BEHAVIOR["reference"] == "evaluate"

    def test_all_three_authority_levels_covered(self):
        authorities_in_map = set(MEMORY_SOURCE_AUTHORITY.values())
        assert "canonical" in authorities_in_map
        assert "reference" in authorities_in_map
        assert "derived" in authorities_in_map
