"""
Tests for governance_tools/task_level_detector.py

Coverage:
- detect_task_level: explicit priority, L0 keywords, veto keywords, L2 keywords, defaults
- destructive_data_veto: data-destruction escalation, and the UI words it must not catch
- get_l0_context_limits: structure, required entries
- apply_upgrade_triggers: L0 upgrade, L1/L2 passthrough, deduplication
- Keyword list integrity: non-empty, no overlap, lowercase
"""

from __future__ import annotations

import pytest

from governance_tools.task_level_detector import (
    AMBIGUOUS_REMOVAL_KEYWORDS,
    DATA_OBJECT_KEYWORDS,
    DESTRUCTIVE_OPERATION_KEYWORDS,
    UI_ELEMENT_NOUNS,
    L0_KEYWORDS,
    L0_VETO_KEYWORDS,
    L2_KEYWORDS,
    apply_upgrade_triggers,
    destructive_data_veto,
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
# destructive_data_veto — 資料破壞升級
# ---------------------------------------------------------------------------

class TestDestructiveDataVeto:
    """破壞資料的任務不能走 L0 快速路徑。

    缺口的形狀：L0_VETO_KEYWORDS 收了 schema、auth、kernel、secret，
    卻完全沒有收刪除類動詞，所以一個帶 UI 字眼的刪檔任務會被判成 L0。
    """

    @pytest.mark.parametrize("description", [
        "add UI button to delete saved game files",
        "rm -rf user data directory",
        "wipe the user profile",
        "purge old backups",
        "shred the credential file",
        "overwrite the save file",
        "mkfs the partition",
        "destroy the snapshot",
        "clear all records in the ui table view",
    ])
    def test_data_destruction_is_not_l0(self, description):
        assert detect_task_level(description) != "L0", description

    @pytest.mark.parametrize("description", [
        "刪除 UI button 的存檔",
        "砍掉備份",
        "清空資料",
        "抹除磁碟",
        "移除使用者帳號",
    ])
    def test_cjk_data_destruction_is_not_l0(self, description):
        """CJK 沒有詞界，所以走子字串比對；UI 字眼不得讓它降級。"""
        assert detect_task_level(description) != "L0", description

    # (純 UI 的句子, 同一句加上破壞性子句, 預期的動詞訊號)
    @pytest.mark.parametrize("ui_only,with_destruction,verb", [
        ("restyle the ui button",
         "restyle the ui button that deletes the save files", "delete"),
        ("update the icon",
         "update the icon for deleting the backup folder", "delete"),
        ("fix the dialog layout",
         "fix the dialog layout before it purges the user profile", "purge"),
        ("adjust padding on the button",
         "adjust padding on the button that drops saved game files", "drop"),
        ("restyle the ui control",
         "restyle the ui control that is resetting the user profile", "reset"),
        ("tweak css for the panel",
         "tweak css for the panel that wiped the user profile", "wipe"),
        ("update the ui copy",
         "update the ui copy after removing the artifact files", "remove"),
    ])
    def test_inflected_forms_are_caught(self, ui_only, with_destruction, verb):
        """詞形辨識要能被證明有作用，而不是靠預設值蒙對。

        斷言「結果不是 L0」證明不了任何事：一句沒有命中 L0 關鍵字的描述
        本來就會落到預設的 L1。所以每個案例都成對出現——先確認純 UI 的
        版本真的走 L0，再確認加上破壞性子句之後變成 L1，而且訊號裡真的
        有那個動詞。拿掉 _inflections 的任何一條規則，這組測試就會紅。
        """
        assert detect_task_level(ui_only) == "L0", (
            f"baseline must be L0, otherwise this case proves nothing: {ui_only!r}")
        signals = destructive_data_veto(with_destruction)
        assert verb in signals, (
            f"{with_destruction!r} -> expected {verb!r} in signals, got {signals}")
        assert detect_task_level(with_destruction) == "L1", with_destruction

    @pytest.mark.parametrize("description,verb", [
        ("add UI button for dropping saved game files", "drop"),
        ("add UI button for resetting saved game files", "reset"),
        ("add UI button for shredding the backup files", "shred"),
    ])
    def test_doubled_consonant_forms_are_caught(self, description, verb):
        """drop -> dropping、reset -> resetting：子音疊字的詞形。

        這三句原本都判成 L0，因為 _inflections 只做了加 s/ed/ing 和去 e。
        """
        assert verb in destructive_data_veto(description), description
        assert detect_task_level(description) == "L1", description

    @pytest.mark.parametrize("description,verb", [
        ("新增 UI 按鈕delete存檔", "delete"),
        ("修改ui的delete存檔流程", "delete"),
    ])
    def test_english_verb_adjacent_to_cjk_is_caught(self, description, verb):
        """中英相接處沒有空白時也要認得。

        `\b` 用的是 Unicode 的 word character，中日韓文字也算，所以
        「按鈕delete存檔」裡的 delete 兩側都不是詞界，整句會漏判。
        """
        assert verb in destructive_data_veto(description), description
        assert detect_task_level(description) == "L1", description

    @pytest.mark.parametrize("description", [
        "fix typo in wipe button label",
        "fix the destroy dialog wording",
        "translate the erase button label",
        "restyle the purge menu button",
    ])
    def test_a_destructive_word_naming_a_ui_element_stays_l0(self, description):
        """提到一個破壞性動作，不等於正在執行它。

        `fix typo in wipe button label` 只是在改一行文字。把它升級成 L1
        是用真實的開發成本換一個不存在的風險，和漏判一樣是判錯。
        """
        assert destructive_data_veto(description) == [], description
        assert detect_task_level(description) == "L0", description

    def test_the_ui_element_guard_does_not_apply_once_data_is_named(self):
        """守衛只處理「這個詞是元件名稱」，不是給破壞性任務的通行證。"""
        description = "add a wipe button that erases the save files"
        assert "erase" in destructive_data_veto(description)
        assert detect_task_level(description) == "L1"

    def test_a_bare_log_is_not_a_data_object(self):
        """`remove the console log` 是例行清理，不該因此升級。

        審計用的日誌要指名（audit log），刪日誌檔由 file 接住。這是刻意
        放棄「clear the logs」這類描述的覆蓋，換掉一個每天都會踩到的
        誤升級。
        """
        assert destructive_data_veto("remove the console log from the ui component") == []
        assert "audit log" in destructive_data_veto("clear the audit log")

    def test_detect_task_level_does_not_surface_the_reason(self):
        """訊號可以被查詢，但 runtime 還沒有把升級理由呈現出來。

        這條測試釘住的是說法的邊界：destructive_data_veto() 回傳訊號，
        detect_task_level() 卻只把它當真假值用，對外只有一個 "L1"。哪天
        runtime 真的開始呈現理由，這條會失敗，提醒同時修正說明。
        """
        description = "restyle the ui button that deletes the save files"
        assert destructive_data_veto(description) != []
        assert detect_task_level(description) == "L1"

    @pytest.mark.parametrize("description", [
        "remove the button from the toolbar",
        "add a dropdown to the UI",
        "add swipe gesture to the component",
        "transform the css color",
        "confirm button style update",
        "fix form layout alignment",
        "format the date in the ui label",
        "truncate the label string in the ui",
        "reset the theme color",
        "clear the padding on the icon",
        "remove the row spacing in the css grid",
        "reset the volume slider style",
    ])
    def test_ui_words_that_merely_look_destructive_stay_l0(self, description):
        """這個類別存在的理由就是不要重犯 key ⊂ keyboard 那種子字串誤判。

        rm ⊂ form/confirm/transform、drop ⊂ dropdown、wipe ⊂ swipe；
        而 remove/clear/reset/format/truncate 單獨出現時是 UI 動詞，
        必須等到資料受詞出現才升級。
        """
        assert detect_task_level(description) == "L0", description

    def test_veto_reports_the_signals_not_just_a_boolean(self):
        """升級理由要在現場看得見，否則判級結果無從檢視。"""
        signals = destructive_data_veto("delete the save files")
        assert "delete" in signals
        assert {"save", "file"} & set(signals)

    def test_no_signals_for_a_pure_ui_removal(self):
        assert destructive_data_veto("remove the button from the toolbar") == []

    def test_ambiguous_verb_alone_does_not_veto(self):
        """只有動詞、沒有資料受詞 → 不升級。這是偽陽性的主要防線。"""
        assert destructive_data_veto("remove the icon") == []
        assert destructive_data_veto("clear the margin") == []

    def test_data_object_alone_does_not_veto(self):
        """只有受詞、沒有破壞動詞 → 不升級。"""
        assert destructive_data_veto("show the save file name in the ui") == []

    def test_explicit_level_still_wins(self):
        """人類明確指定的 level 仍然優先，與既有的 veto 行為一致。"""
        assert detect_task_level("delete all user files", explicit_level="L0") == "L0"

    def test_sql_shaped_destruction_is_already_covered(self):
        """drop table / truncate table 由既有的 table、database veto 接住。

        這一條記錄的是分工，不是這個類別的功勞：新類別補的是檔案與
        使用者資料的破壞，不是 SQL。
        """
        assert detect_task_level("drop the table in the ui view") != "L0"
        assert detect_task_level("truncate the database for the ui demo") != "L0"


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

    def test_destruction_lists_not_empty(self):
        assert len(DESTRUCTIVE_OPERATION_KEYWORDS) > 0
        assert len(AMBIGUOUS_REMOVAL_KEYWORDS) > 0
        assert len(DATA_OBJECT_KEYWORDS) > 0

    def test_destruction_keywords_lowercase_and_non_empty(self):
        for kw in (DESTRUCTIVE_OPERATION_KEYWORDS + AMBIGUOUS_REMOVAL_KEYWORDS
                   + DATA_OBJECT_KEYWORDS):
            assert kw == kw.lower(), f"Non-lowercase destruction keyword: '{kw}'"
            assert kw.strip(), "Found empty or whitespace-only keyword"

    def test_ui_element_nouns_usable(self):
        assert len(UI_ELEMENT_NOUNS) > 0
        for noun in UI_ELEMENT_NOUNS:
            assert noun == noun.lower(), f"Non-lowercase UI noun: '{noun}'"
            assert noun.strip(), "Found empty or whitespace-only UI noun"

    def test_destruction_tiers_do_not_overlap(self):
        """一個詞不能同時是『單獨即否決』和『需要受詞才否決』。"""
        overlap = set(DESTRUCTIVE_OPERATION_KEYWORDS) & set(AMBIGUOUS_REMOVAL_KEYWORDS)
        assert overlap == set(), f"A keyword is in both destruction tiers: {overlap}"

    def test_destruction_keywords_do_not_collide_with_l0(self):
        """否則同一個詞會同時要求降級和升級。"""
        for name, lst in [
            ("destructive", DESTRUCTIVE_OPERATION_KEYWORDS),
            ("ambiguous", AMBIGUOUS_REMOVAL_KEYWORDS),
            ("data object", DATA_OBJECT_KEYWORDS),
        ]:
            overlap = set(L0_KEYWORDS) & set(lst)
            assert overlap == set(), f"L0 keywords overlap {name}: {overlap}"
