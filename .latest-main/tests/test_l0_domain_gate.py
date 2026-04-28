import pytest
from governance_tools.l0_domain_gate import (
    should_load_domain_contract,
    get_l0_domain_skip_reason,
    DOMAIN_UPGRADE_KEYWORDS,
    L0_DOMAIN_POLICY,
)


class TestShouldLoadDomainContract:

    def test_l1_always_loads(self):
        load, mode = should_load_domain_contract("L1")
        assert load is True
        assert mode == "summary"

    def test_l2_always_loads(self):
        load, mode = should_load_domain_contract("L2")
        assert load is True
        assert mode == "summary"

    def test_l0_default_skips(self):
        load, mode = should_load_domain_contract("L0")
        assert load is False
        assert mode == "skip"

    def test_l0_force_domain_loads_summary(self):
        load, mode = should_load_domain_contract("L0", force_domain=True)
        assert load is True
        assert mode == "summary"

    def test_l0_force_domain_never_full(self):
        """force-domain 只允許 summary，不允許 full。"""
        load, mode = should_load_domain_contract("L0", force_domain=True)
        assert mode != "full"

    def test_l0_with_domain_keywords_loads_summary(self):
        """domain 關鍵字作為雙重保護，允許 summary。"""
        load, mode = should_load_domain_contract(
            "L0", task_description="fix ISR timing in KDC"
        )
        assert load is True
        assert mode == "summary"

    def test_l0_pure_ui_skips(self):
        load, mode = should_load_domain_contract(
            "L0", task_description="update button color"
        )
        assert load is False
        assert mode == "skip"

    def test_unknown_level_conservative(self):
        """未知 level 保守允許。"""
        load, mode = should_load_domain_contract("L3")
        assert load is True

    def test_l0_empty_description_skips(self):
        load, mode = should_load_domain_contract("L0", task_description="")
        assert load is False
        assert mode == "skip"

    def test_l0_case_insensitive_keyword(self):
        load, mode = should_load_domain_contract("L0", task_description="Fix KDC driver")
        assert load is True

    def test_l1_with_force_domain_still_loads(self):
        load, mode = should_load_domain_contract("L1", force_domain=True)
        assert load is True


class TestGetL0DomainSkipReason:

    def test_returns_string(self):
        reason = get_l0_domain_skip_reason()
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_domain_keyword_reason(self):
        reason = get_l0_domain_skip_reason("fix ISR handler")
        assert "summary" in reason.lower() or "domain" in reason.lower()

    def test_default_reason(self):
        reason = get_l0_domain_skip_reason("update button color")
        assert "L0" in reason or "skip" in reason.lower()

    def test_kdc_keyword_reason(self):
        reason = get_l0_domain_skip_reason("kdc timing fix")
        assert "summary" in reason.lower() or "domain" in reason.lower()


class TestDomainUpgradeKeywords:

    def test_keywords_not_empty(self):
        assert len(DOMAIN_UPGRADE_KEYWORDS) > 0

    def test_all_lowercase(self):
        for kw in DOMAIN_UPGRADE_KEYWORDS:
            assert kw == kw.lower(), f"Non-lowercase: {kw}"

    def test_critical_keywords_present(self):
        assert "isr" in DOMAIN_UPGRADE_KEYWORDS
        assert "kdc" in DOMAIN_UPGRADE_KEYWORDS


class TestL0DomainPolicy:

    def test_policy_has_required_keys(self):
        assert "default" in L0_DOMAIN_POLICY
        assert "force_flag" in L0_DOMAIN_POLICY
        assert "force_mode" in L0_DOMAIN_POLICY

    def test_default_is_skip(self):
        assert L0_DOMAIN_POLICY["default"] == "skip"

    def test_force_mode_not_full(self):
        assert L0_DOMAIN_POLICY["force_mode"] != "full"


class TestL0TokenImpact:

    def test_l0_skip_removes_domain_tokens(self):
        """
        概念測試：L0 跳過 domain_contract 應讓 token 從 ~10,264 降至 ~6,742。
        這個測試驗證的是邏輯行為，不是實際 token 數。
        """
        load, _ = should_load_domain_contract("L0", task_description="update button color")
        assert load is False, "Pure UI L0 task should skip domain contract"

    def test_l0_never_loads_full_contract(self):
        """L0 無論如何都不應載入 full contract。"""
        for desc in ["", "update button", "kdc driver fix"]:
            _, mode = should_load_domain_contract("L0", task_description=desc)
            assert mode != "full", f"L0 loaded full contract for: {desc!r}"

    def test_l0_force_domain_still_no_full(self):
        _, mode = should_load_domain_contract("L0", force_domain=True)
        assert mode != "full"
