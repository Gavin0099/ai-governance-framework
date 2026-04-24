from __future__ import annotations

from governance_tools.agents_rule_evidence_aggregation import (
    AgentsRuleEvidenceEvent,
    aggregate_candidate_evidence,
    build_rejection_suppression_window,
)
from governance_tools.agents_rule_promotion_schema import (
    AgentsRulePromotionLedgerEntry,
    make_candidate,
)


def _candidate() -> object:
    return make_candidate(
        candidate_type="must_test_path",
        human_candidate="runtime_hooks/core/pre_task_check.py",
        evidence_count=1,
        evidence_window_days=14,
        observed_from=["post_task_check"],
        repo_specificity="high",
        repo_specificity_basis=["real_path"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T12:00:00Z",
        evidence_refs=["session:end:2026-04-24:abc123"],
    )


def test_duplicate_evidence_ref_counts_once() -> None:
    candidate = _candidate()
    events = [
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="session:end:2026-04-24:abc123",
            observed_at="2026-04-24T10:30:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
            source="post_task_check",
        ),
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="session:end:2026-04-24:abc123",
            observed_at="2026-04-24T10:31:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
            source="post_task_check",
        ),
    ]

    result = aggregate_candidate_evidence(candidate, events)

    assert result.evidence_count == 1
    assert result.duplicate_evidence_refs == ["session:end:2026-04-24:abc123"]


def test_aggregation_key_is_candidate_id() -> None:
    candidate = _candidate()
    result = aggregate_candidate_evidence(candidate, [])
    assert result.aggregation_key == candidate.candidate_id


def test_only_windowed_evidence_is_counted() -> None:
    candidate = _candidate()
    events = [
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="before-window",
            observed_at="2026-04-24T09:59:59Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
        ),
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="in-window",
            observed_at="2026-04-24T11:00:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
        ),
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="after-window",
            observed_at="2026-04-24T12:00:01Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
        ),
    ]

    result = aggregate_candidate_evidence(candidate, events)

    assert result.counted_evidence_refs == ["in-window"]
    assert result.evidence_count == 1


def test_rejected_candidate_is_suppressed_before_suppression_until() -> None:
    candidate = _candidate()
    ledger = AgentsRulePromotionLedgerEntry(
        candidate_id=candidate.candidate_id,
        promotion_decision="rejected",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=["session:end:2026-04-24:abc123"],
        review_note="Too weak for promotion.",
        agents_patch_status="not_proposed",
        suppress_resurfacing_days=14,
        suppression_until="2026-05-08T13:00:00Z",
        resurfacing_condition="material_evidence_increase",
    )

    result = aggregate_candidate_evidence(
        candidate,
        [],
        ledger_entries=[ledger],
        now_utc="2026-04-30T00:00:00Z",
    )

    assert result.resurfacing_allowed is False
    assert result.resurfacing_reason == "suppressed_until_not_reached"
    assert result.suppressed_by_ledger is True


def test_rejected_candidate_only_resurfaces_after_material_evidence_increase() -> None:
    candidate = _candidate()
    ledger = AgentsRulePromotionLedgerEntry(
        candidate_id=candidate.candidate_id,
        promotion_decision="rejected",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=["session:end:2026-04-24:abc123", "review:thread:42"],
        review_note="Still too weak.",
        agents_patch_status="not_proposed",
        suppress_resurfacing_days=7,
        suppression_until="2026-05-01T13:00:00Z",
        resurfacing_condition="material_evidence_increase",
    )
    events = [
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="session:end:2026-04-24:abc123",
            observed_at="2026-04-24T10:30:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
        ),
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="review:thread:42",
            observed_at="2026-04-24T10:35:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_path"],
        ),
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="new-evidence",
            observed_at="2026-04-24T11:00:00Z",
            repo_specificity="high",
            repo_specificity_basis=["real_command"],
        ),
    ]

    blocked = aggregate_candidate_evidence(
        candidate,
        events[:2],
        ledger_entries=[ledger],
        now_utc="2026-05-02T00:00:00Z",
    )
    allowed = aggregate_candidate_evidence(
        candidate,
        events,
        ledger_entries=[ledger],
        now_utc="2026-05-02T00:00:00Z",
    )

    assert blocked.resurfacing_allowed is False
    assert blocked.resurfacing_reason == "material_evidence_increase_not_met"
    assert allowed.resurfacing_allowed is True
    assert allowed.resurfacing_reason == "material_evidence_increase_met"


def test_generic_only_evidence_cannot_raise_repo_specificity() -> None:
    candidate = make_candidate(
        candidate_type="forbidden_behavior",
        human_candidate="do not break production",
        evidence_count=1,
        evidence_window_days=14,
        observed_from=["reviewer_escalation"],
        repo_specificity="medium",
        repo_specificity_basis=["generic_only"],
        first_seen_at="2026-04-24T10:00:00Z",
        last_seen_at="2026-04-24T12:00:00Z",
    )
    events = [
        AgentsRuleEvidenceEvent(
            candidate_id=candidate.candidate_id,
            evidence_ref="review:thread:generic",
            observed_at="2026-04-24T10:30:00Z",
            repo_specificity="high",
            repo_specificity_basis=["generic_only"],
        )
    ]

    result = aggregate_candidate_evidence(candidate, events)

    assert result.repo_specificity == "low"


def test_build_rejection_suppression_window_adds_days() -> None:
    until = build_rejection_suppression_window("2026-04-24T13:00:00Z", 14)
    assert until == "2026-05-08T13:00:00Z"
