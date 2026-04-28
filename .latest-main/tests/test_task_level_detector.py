"""
Tests for governance_tools/task_level_detector.py

Coverage:
- detect_task_level: explicit priority, L0 keywords, veto keywords, L2 keywords, defaults
- get_l0_context_limits: structure, required entries
- apply_upgrade_triggers: L0 upgrade, L1/L2 passthrough, deduplication
- Keyword list integrity: non-empty, no overlap, lowercase
"""

from __future__ import annotations

import pytest

from governance_tools.task_level_detector import (
    L0_KEYWORDS,
    L0_VETO_KEYWORDS,
    L2_KEYWORDS,
    apply_upgrade_triggers,
    detect_task_level,
    get_l0_context_limits,
)


# ---------------------------------------------------------------------------
# detect_task_level — explicit level takes priority
# ---------------------------------------------------------------------------

class TestDetectTaskLevelExplicit:

    def test_explicit_l0_takes_priority_over_veto(self):
        assert detect_task_level("deploy to production", explicit_level="L0") == "L0"

    def test_explicit_l1_takes_priority_over_l0_keyword(self):
        assert detect_task_level("change button color", explicit_level="L1") == "L1"

    def test_explicit_l2_takes_priority(self):
        assert detect_task_level("change button color", explicit_level="L2") == "L2"

    def test_explicit_case_insensitive_l0(self):
        assert detect_task_level("anything", explicit_level="l0") == "L0"

    def test_explicit_case_insensitive_l1(self):
        assert detect_task_level("anything", explicit_level="l1") == "L1"

    def test_explicit_case_insensitive_l2(self):
        assert detect_task_level("anything", explicit_level="l2") == "L2"

    def test_invalid_explicit_falls_through_to_detection(self):
        result = detect_task_level("change button color", explicit_level="L9")
        assert result in ("L0", "L1", "L2")

    def test_none_explicit_triggers_auto_detection(self):
        result = detect_task_level("change button color", explicit_level=None)
        assert result == "L0"

    def test_empty_explicit_triggers_auto_detection(self):
        result = detect_task_level("change button color", explicit_level="")
        assert result == "L0"


# ---------------------------------------------------------------------------
# detect_task_level — L0 auto-detection
# ---------------------------------------------------------------------------

class TestDetectTaskLevelAutoL0:

    def test_ui_keyword_detected(self):
        assert detect_task_level("update button color") == "L0"

    def test_layout_keyword_detected(self):
        assert detect_task_level("fix layout alignment") == "L0"

    def test_css_keyword_detected(self):
        assert detect_task_level("change CSS style") == "L0"

    def test_readme_update_is_l0(self):
        assert detect_task_level("update README documentation") == "L0"

    def test_typo_fix_is_l0(self):
        assert detect_task_level("fix typo in comment") == "L0"

    def test_rename_variable_is_l0(self):
        assert detect_task_level("rename variable userID to userId") == "L0"

    def test_dark_mode_is_l0(self):
        assert detect_task_level("implement dark mode toggle") == "L0"

    def test_icon_update_is_l0(self):
        assert detect_task_level("replace icon with new design") == "L0"

    def test_spacing_is_l0(self):
        assert detect_task_level("adjust spacing between elements") == "L0"

    def test_padding_is_l0(self):
        assert detect_task_level("increase padding in card component") == "L0"

    def test_docstring_update_is_l0(self):
        assert detect_task_level("update docstring for get_user function") == "L0"


# ---------------------------------------------------------------------------
# detect_task_level — veto overrides L0
# ---------------------------------------------------------------------------

class TestDetectTaskLevelVeto:

    def test_schema_vetos_l0(self):
        result = detect_task_level("update UI layout and schema migration")
        assert result == "L1"

    def test_auth_vetos_l0(self):
        assert detect_task_level("update auth button style") == "L1"

    def test_api_vetos_l0(self):
        assert detect_task_level("fix API button display") == "L1"

    def test_security_vetos_l0(self):
        assert detect_task_level("fix security icon color") == "L1"

    def test_migration_vetos_l0(self):
        assert detect_task_level("apply migration for UI") == "L1"

    def test_firmware_vetos_l0(self):
        assert detect_task_level("fix ISR timing comment") == "L1"

    def test_irql_vetos_l0(self):
        assert detect_task_level("update IRQL documentation") == "L1"

    def test_kernel_vetos_l0(self):
        assert detect_task_level("update kernel driver styling") == "L1"

    def test_deploy_vetos_l0(self):
        assert detect_task_level("deploy button to production") == "L1"

    def test_release_vetos_l0(self):
        assert detect_task_level("release UI update") == "L1"

    def test_contract_vetos_l0(self):
        assert detect_task_level("update component contract interface") == "L1"

    def test_permission_vetos_l0(self):
        assert detect_task_level("update display permission settings") == "L1"


# ---------------------------------------------------------------------------
# detect_task_level — L2 takes highest priority
# ---------------------------------------------------------------------------

class TestDetectTaskLevelL2:

    def test_breaking_change_is_l2(self):
        assert detect_task_level("breaking change to auth API") == "L2"

    def test_breaking_change_hyphenated(self):
        assert detect_task_level("breaking-change in component interface") == "L2"

    def test_architectural_change_is_l2(self):
        assert detect_task_level("architectural change to domain contract") == "L2"

    def test_cross_repo_is_l2(self):
        assert detect_task_level("cross-repo dependency update") == "L2"

    def test_multi_repo_is_l2(self):
        assert detect_task_level("multi-repo refactor coordination") == "L2"

    def test_l2_overrides_l0_keywords(self):
        result = detect_task_level("breaking change to button component API")
        assert result == "L2"

    def test_contract_update_is_l2(self):
        assert detect_task_level("domain contract change for new feature") == "L2"

    def test_major_refactor_is_l2(self):
        assert detect_task_level("major refactor of authentication system") == "L2"


# ---------------------------------------------------------------------------
# detect_task_level — defaults
# ---------------------------------------------------------------------------

class TestDetectTaskLevelDefaults:

    def test_empty_description_defaults_to_l1(self):
        assert detect_task_level("") == "L1"

    def test_unknown_description_defaults_to_l1(self):
        assert detect_task_level("do the thing") == "L1"

    def test_no_keywords_defaults_to_l1(self):
        assert detect_task_level("update project dependencies") == "L1"

    def test_generic_feature_defaults_to_l1(self):
        assert detect_task_level("add new user feature") == "L1"


# ---------------------------------------------------------------------------
# get_l0_context_limits
# ---------------------------------------------------------------------------

class TestGetL0ContextLimits:

    def test_returns_required_keys(self):
        limits = get_l0_context_limits()
        assert "always_load" in limits
        assert "forbidden_load" in limits
        assert "upgrade_triggers" in limits

    def test_system_prompt_always_loaded(self):
        limits = get_l0_context_limits()
        assert any("SYSTEM_PROMPT" in f for f in limits["always_load"])

    def test_agent_md_always_loaded(self):
        limits = get_l0_context_limits()
        assert any("AGENT.md" in f for f in limits["always_load"])

    def test_plan_always_loaded(self):
        limits = get_l0_context_limits()
        assert any("PLAN.md" in f for f in limits["always_load"])

    def test_review_criteria_forbidden(self):
        limits = get_l0_context_limits()
        assert any("REVIEW_CRITERIA" in f for f in limits["forbidden_load"])

    def test_human_oversight_forbidden(self):
        limits = get_l0_context_limits()
        assert any("HUMAN-OVERSIGHT" in f for f in limits["forbidden_load"])

    def test_architecture_forbidden_for_l0(self):
        limits = get_l0_context_limits()
        assert any("ARCHITECTURE" in f for f in limits["forbidden_load"])

    def test_native_interop_forbidden_for_l0(self):
        limits = get_l0_context_limits()
        assert any("NATIVE-INTEROP" in f for f in limits["forbidden_load"])

    def test_upgrade_triggers_is_list(self):
        limits = get_l0_context_limits()
        assert isinstance(limits["upgrade_triggers"], list)
        assert len(limits["upgrade_triggers"]) > 0

    def test_upgrade_triggers_have_required_keys(self):
        limits = get_l0_context_limits()
        for trigger in limits["upgrade_triggers"]:
            assert "condition" in trigger
            assert "escalate_to" in trigger

    def test_no_overlap_always_and_forbidden(self):
        limits = get_l0_context_limits()
        always = set(limits["always_load"])
        forbidden = set(limits["forbidden_load"])
        overlap = always & forbidden
        assert len(overlap) == 0, f"always_load and forbidden_load must not overlap: {overlap}"


# ---------------------------------------------------------------------------
# apply_upgrade_triggers
# ---------------------------------------------------------------------------

class TestApplyUpgradeTriggers:

    def test_l1_passthrough_unchanged(self):
        level, additions = apply_upgrade_triggers("L1", "anything")
        assert level == "L1"
        assert additions == []

    def test_l2_passthrough_unchanged(self):
        level, additions = apply_upgrade_triggers("L2", "breaking change")
        assert level == "L2"
        assert additions == []

    def test_l0_schema_keyword_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "update database schema")
        assert level == "L1"
        assert any("ARCHITECTURE" in a for a in additions)

    def test_l0_migration_keyword_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "add migration for table")
        assert level == "L1"

    def test_l0_domain_isr_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "fix ISR interrupt handler")
        assert level == "L1"

    def test_l0_kernel_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "update kernel module")
        assert level == "L1"

    def test_l0_high_risk_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "update button color", risk_level="high")
        assert level == "L1"

    def test_l0_critical_risk_upgrades_to_l1(self):
        level, additions = apply_upgrade_triggers("L0", "rename icon", risk_level="critical")
        assert level == "L1"

    def test_l0_low_risk_pure_ui_stays_l0(self):
        level, additions = apply_upgrade_triggers("L0", "update button color", risk_level="low")
        assert level == "L0"
        assert additions == []

    def test_l0_medium_risk_stays_l0(self):
        level, additions = apply_upgrade_triggers("L0", "fix layout spacing", risk_level="medium")
        assert level == "L0"
        assert additions == []

    def test_additional_loads_deduplicated(self):
        # Multiple triggers hitting the same ARCHITECTURE.md → should appear only once
        level, additions = apply_upgrade_triggers(
            "L0",
            "update schema and migration for database column",
        )
        assert len(additions) == len(set(additions)), "additional_loads should be deduplicated"

    def test_returns_tuple(self):
        result = apply_upgrade_triggers("L0", "any task", risk_level="low")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_additional_loads_is_list(self):
        _, additions = apply_upgrade_triggers("L0", "any task", risk_level="low")
        assert isinstance(additions, list)


# ---------------------------------------------------------------------------
# Keyword list integrity
# ---------------------------------------------------------------------------

class TestKeywordListIntegrity:

    def test_l0_keywords_not_empty(self):
        assert len(L0_KEYWORDS) > 0

    def test_veto_keywords_not_empty(self):
        assert len(L0_VETO_KEYWORDS) > 0

    def test_l2_keywords_not_empty(self):
        assert len(L2_KEYWORDS) > 0

    def test_no_overlap_l0_and_veto(self):
        """L0 關鍵字和 veto 關鍵字不應重疊，否則邏輯永遠矛盾。"""
        overlap = set(L0_KEYWORDS) & set(L0_VETO_KEYWORDS)
        assert len(overlap) == 0, f"Overlapping keywords between L0 and veto: {overlap}"

    def test_all_keywords_lowercase(self):
        """所有關鍵字應為小寫（比對時用 .lower()）。"""
        for kw in L0_KEYWORDS:
            assert kw == kw.lower(), f"Non-lowercase L0 keyword: '{kw}'"
        for kw in L0_VETO_KEYWORDS:
            assert kw == kw.lower(), f"Non-lowercase veto keyword: '{kw}'"
        for kw in L2_KEYWORDS:
            assert kw == kw.lower(), f"Non-lowercase L2 keyword: '{kw}'"

    def test_no_empty_keywords(self):
        for kw in L0_KEYWORDS + L0_VETO_KEYWORDS + L2_KEYWORDS:
            assert kw.strip(), "Found empty or whitespace-only keyword"
