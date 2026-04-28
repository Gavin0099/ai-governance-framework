"""
L0 整合測試：驗證 L0 session 的 payload 確實被限制。

Tests the L0-specific logic in task_level_detector without exercising
the full session_start pipeline (which has expensive I/O).
"""

from __future__ import annotations

import pytest

from governance_tools.task_level_detector import (
    apply_upgrade_triggers,
    detect_task_level,
    get_l0_context_limits,
)


# ---------------------------------------------------------------------------
# L0 payload restriction invariants
# ---------------------------------------------------------------------------

class TestL0PayloadRestriction:

    def test_forbidden_files_not_in_l0_always_load(self):
        """forbidden_load 和 always_load 不應有交集。"""
        limits = get_l0_context_limits()
        always = set(limits["always_load"])
        forbidden = set(limits["forbidden_load"])
        overlap = always & forbidden
        assert len(overlap) == 0, f"Conflict: {overlap}"

    def test_human_only_files_in_forbidden(self):
        """human-only governance files must be in forbidden_load for L0."""
        limits = get_l0_context_limits()
        human_only = {"REVIEW_CRITERIA.md", "HUMAN-OVERSIGHT.md"}
        for f in human_only:
            assert any(f in path for path in limits["forbidden_load"]), \
                f"{f} must appear in L0 forbidden_load"

    def test_on_demand_files_in_forbidden(self):
        """on-demand governance files must be in forbidden_load for L0."""
        limits = get_l0_context_limits()
        on_demand = {"ARCHITECTURE.md", "NATIVE-INTEROP.md"}
        for f in on_demand:
            assert any(f in path for path in limits["forbidden_load"]), \
                f"{f} must appear in L0 forbidden_load"


# ---------------------------------------------------------------------------
# L0 detection consistency
# ---------------------------------------------------------------------------

class TestL0DetectionConsistency:

    def test_l0_cases_detected_correctly(self):
        """Pure UI/doc tasks should auto-detect as L0."""
        l0_cases = [
            "change button color to blue",
            "fix typo in sidebar label",
            "update README with new screenshot",
            "adjust padding in card component",
            "rename CSS class from old-style to new-style",
        ]
        for desc in l0_cases:
            level = detect_task_level(desc)
            assert level == "L0", f"Expected L0 for: '{desc}', got {level}"

    def test_veto_cases_never_l0(self):
        """High-risk task descriptions must not be downgraded to L0."""
        non_l0_cases = [
            "update database schema for new feature",
            "fix authentication middleware",
            "add ISR handler for USB interrupt",
            "deploy release v2.0",
            "add new API endpoint for user profile",
            "breaking change to auth token format",
        ]
        for desc in non_l0_cases:
            level = detect_task_level(desc)
            assert level != "L0", f"Expected non-L0 for: '{desc}', got {level}"

    def test_l2_cases_above_l1(self):
        """Breaking-change and cross-repo tasks must return L2."""
        l2_cases = [
            "breaking change to the auth API",
            "cross-repo dependency refactor",
            "major refactor of authentication module",
        ]
        for desc in l2_cases:
            level = detect_task_level(desc)
            assert level == "L2", f"Expected L2 for: '{desc}', got {level}"


# ---------------------------------------------------------------------------
# Upgrade trigger escalation
# ---------------------------------------------------------------------------

class TestUpgradeTriggerEscalation:

    def test_schema_keyword_escalates_l0_to_l1(self):
        """A task that looks like UI but contains schema keyword → L1."""
        level, additions = apply_upgrade_triggers(
            "L0",
            "update UI layout and add new schema column",
        )
        assert level == "L1"

    def test_pure_ui_stays_l0_at_low_risk(self):
        """Pure UI task at low risk should not be escalated."""
        level, additions = apply_upgrade_triggers(
            "L0",
            "update button color from red to blue",
            risk_level="low",
        )
        assert level == "L0"
        assert additions == []

    def test_high_risk_escalates_l0_regardless_of_content(self):
        """High risk must escalate L0 → L1 even if task is trivial."""
        level, additions = apply_upgrade_triggers(
            "L0",
            "fix icon alignment",
            risk_level="high",
        )
        assert level == "L1"

    def test_l1_not_escalated_further(self):
        """L1 with schema keyword stays L1, not escalated to L2."""
        level, additions = apply_upgrade_triggers(
            "L1",
            "update database schema and table columns",
        )
        assert level == "L1"
        assert additions == []

    def test_upgrade_adds_architecture_doc_for_schema(self):
        """Schema trigger should request ARCHITECTURE.md to be loaded."""
        _, additions = apply_upgrade_triggers(
            "L0",
            "migrate schema for user table",
        )
        assert any("ARCHITECTURE" in a for a in additions)

    def test_upgrade_adds_domain_summary_for_kernel(self):
        """Kernel/ISR trigger should request domain_summary to be loaded."""
        _, additions = apply_upgrade_triggers(
            "L0",
            "fix kernel ISR handler timing",
        )
        assert any("domain_summary" in a for a in additions)


# ---------------------------------------------------------------------------
# Explicit level override in L0 context
# ---------------------------------------------------------------------------

class TestExplicitLevelForL0:

    def test_explicit_l0_overrides_veto_keyword(self):
        """If user explicitly passes L0, it should be respected."""
        result = detect_task_level("deploy to production", explicit_level="L0")
        assert result == "L0"

    def test_explicit_l1_overrides_l0_keyword(self):
        """If user explicitly passes L1, UI keywords should not downgrade it."""
        result = detect_task_level("change button color", explicit_level="L1")
        assert result == "L1"

    def test_explicit_l0_still_subject_to_upgrade_triggers(self):
        """Upgrade triggers apply after level detection, so explicit L0 can be escalated."""
        # detect_task_level returns L0 when explicit_level="L0"
        detected = detect_task_level("deploy button color", explicit_level="L0")
        assert detected == "L0"
        # But apply_upgrade_triggers can still escalate it
        final_level, _ = apply_upgrade_triggers(detected, "deploy button color", risk_level="high")
        assert final_level == "L1"
