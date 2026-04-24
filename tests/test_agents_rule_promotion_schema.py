from __future__ import annotations

import pytest

from governance_tools.agents_rule_promotion_schema import (
    build_candidate_id,
    make_candidate,
    normalize_candidate_text,
    section_key_for_candidate_type,
    AgentsRulePromotionLedgerEntry,
)


def test_section_key_mapping_is_fixed() -> None:
    assert section_key_for_candidate_type("must_test_path") == "must_test_paths"
    assert section_key_for_candidate_type("forbidden_behavior") == "forbidden_behaviors"
    assert section_key_for_candidate_type("escalation_trigger") == "escalation_triggers"
    assert section_key_for_candidate_type("risk_level_boundary") == "risk_levels"


def test_normalize_candidate_text_stabilizes_whitespace_and_case() -> None:
    normalized = normalize_candidate_text("must_test_path", "  Runtime_Hooks/Core/Pre_Task_Check.py  ")
    assert normalized == "runtime_hooks/core/pre_task_check.py"


def test_build_candidate_id_is_stable_for_same_normalized_candidate() -> None:
    normalized = "runtime_hooks/core/pre_task_check.py"
    first = build_candidate_id("must_test_path", normalized)
    second = build_candidate_id("must_test_path", normalized)
    assert first == second


def test_make_candidate_builds_valid_contract() -> None:
    candidate = make_candidate(
        candidate_type="must_test_path",
        human_candidate="runtime_hooks/core/pre_task_check.py",
        evidence_count=5,
        evidence_window_days=14,
        observed_from=["post_task_check", "reviewer_escalation"],
        repo_specificity="high",
        repo_specificity_basis=["real_path", "real_command"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T12:00:00Z",
        evidence_refs=["session:end:2026-04-24:abc123"],
    )

    payload = candidate.to_dict()

    assert payload["candidate_type"] == "must_test_path"
    assert payload["section_key"] == "must_test_paths"
    assert payload["candidate_id"].startswith("must_test_path:")


def test_candidate_validation_rejects_section_key_mismatch() -> None:
    candidate = make_candidate(
        candidate_type="must_test_path",
        human_candidate="runtime_hooks/core/pre_task_check.py",
        evidence_count=2,
        evidence_window_days=7,
        observed_from=["post_task_check"],
        repo_specificity="high",
        repo_specificity_basis=["real_path"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T10:10:00Z",
    )
    candidate.section_key = "risk_levels"

    with pytest.raises(ValueError, match="section_key mismatch"):
        candidate.to_dict()


def test_approved_promotion_requires_evidence_refs() -> None:
    entry = AgentsRulePromotionLedgerEntry(
        candidate_id="must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
        promotion_decision="approved",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=[],
        agents_patch_status="proposed",
    )

    with pytest.raises(ValueError, match="approved promotion requires evidence_refs"):
        entry.to_dict()


def test_rejected_promotion_requires_review_note() -> None:
    entry = AgentsRulePromotionLedgerEntry(
        candidate_id="must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
        promotion_decision="rejected",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=["session:end:2026-04-24:abc123"],
        agents_patch_status="not_proposed",
        suppress_resurfacing_days=14,
        suppression_until="2026-05-08T13:00:00Z",
        resurfacing_condition="material_evidence_increase",
    )

    with pytest.raises(ValueError, match="rejected promotion requires review_note"):
        entry.to_dict()


def test_valid_promotion_ledger_entry_serializes() -> None:
    entry = AgentsRulePromotionLedgerEntry(
        candidate_id="must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
        promotion_decision="approved",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=["session:end:2026-04-24:abc123", "review:thread:42"],
        review_note="Repeated repo-local evidence is sufficient.",
        agents_patch_status="proposed",
    )

    payload = entry.to_dict()

    assert payload["promotion_decision"] == "approved"
    assert payload["target_section"] == "must_test_paths"
    assert payload["agents_patch_status"] == "proposed"


def test_must_test_path_requires_concrete_path_like_candidate() -> None:
    with pytest.raises(ValueError, match="path-like"):
        normalize_candidate_text("must_test_path", "pre task decision path")


def test_high_repo_specificity_requires_concrete_basis() -> None:
    candidate = make_candidate(
        candidate_type="forbidden_behavior",
        human_candidate="do not break production",
        evidence_count=3,
        evidence_window_days=14,
        observed_from=["reviewer_escalation"],
        repo_specificity="high",
        repo_specificity_basis=["generic_only"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T11:00:00Z",
    )

    with pytest.raises(ValueError, match="repo_specificity=high requires"):
        candidate.to_dict()


def test_rejected_promotion_requires_suppression_contract() -> None:
    entry = AgentsRulePromotionLedgerEntry(
        candidate_id="forbidden_behavior:do_not_break_production:aaaaaaaaaaaa",
        promotion_decision="rejected",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:99",
        approved_at="2026-04-24T13:00:00Z",
        target_section="forbidden_behaviors",
        evidence_refs=["review:thread:99"],
        review_note="Too generic to promote.",
        agents_patch_status="not_proposed",
    )

    with pytest.raises(ValueError, match="suppress_resurfacing_days"):
        entry.to_dict()
