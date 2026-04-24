from __future__ import annotations

import pytest

from governance_tools.agents_rule_aggregation_artifact import (
    AGENTS_RULE_AGGREGATION_ARTIFACT_SCHEMA_VERSION,
    DEFAULT_ARTIFACT_PATH,
    AgentsRuleAggregationArtifact,
    make_aggregation_artifact,
)
from governance_tools.agents_rule_evidence_aggregation import aggregate_candidate_evidence
from governance_tools.agents_rule_promotion_schema import (
    AgentsRulePromotionLedgerEntry,
    make_candidate,
)


def _candidate():
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


def test_default_artifact_contract_values_are_exposed() -> None:
    assert AGENTS_RULE_AGGREGATION_ARTIFACT_SCHEMA_VERSION == "0.1"
    assert DEFAULT_ARTIFACT_PATH == "artifacts/governance/agents_rule_candidates.json"


def test_make_aggregation_artifact_serializes_minimal_payload() -> None:
    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
    )

    payload = artifact.to_dict()

    assert payload["schema_version"] == "0.1"
    assert payload["source"] == "manual_or_test_fixture"
    assert payload["candidates"] == []
    assert payload["suppressed_candidates"] == []
    assert payload["ledger_refs"] == []


def test_artifact_keeps_suppressed_candidates_visible() -> None:
    candidate = _candidate()
    suppressed = aggregate_candidate_evidence(candidate, [])
    suppressed.resurfacing_allowed = False
    suppressed.suppressed_by_ledger = True
    suppressed.resurfacing_reason = "suppressed_until_not_reached"

    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
        suppressed_candidates=[suppressed],
    )
    payload = artifact.to_dict()

    assert payload["candidates"] == []
    assert len(payload["suppressed_candidates"]) == 1
    assert payload["suppressed_candidates"][0]["candidate_id"] == candidate.candidate_id


def test_artifact_rejects_suppressed_entry_marked_as_resurfacing_allowed() -> None:
    candidate = _candidate()
    suppressed = aggregate_candidate_evidence(candidate, [])
    suppressed.resurfacing_allowed = True
    suppressed.suppressed_by_ledger = True

    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
        suppressed_candidates=[suppressed],
    )

    with pytest.raises(ValueError, match="suppressed candidate entry must have resurfacing_allowed=false"):
        artifact.to_dict()


def test_artifact_rejects_active_candidate_marked_as_suppressed() -> None:
    candidate = _candidate()
    active = aggregate_candidate_evidence(candidate, [])
    active.suppressed_by_ledger = True

    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
        candidates=[active],
    )

    with pytest.raises(ValueError, match="active candidate entry must not be suppressed_by_ledger=true"):
        artifact.to_dict()


def test_artifact_collects_ledger_refs_for_traceability_only() -> None:
    ledger = AgentsRulePromotionLedgerEntry(
        candidate_id="must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
        promotion_decision="approved",
        approved_by="reviewer",
        review_source="pr_review",
        review_ref="review:thread:42",
        approved_at="2026-04-24T13:00:00Z",
        target_section="must_test_paths",
        evidence_refs=["session:end:2026-04-24:abc123"],
        review_note="Approved after review.",
        agents_patch_status="proposed",
    )

    artifact = make_aggregation_artifact(
        generated_at="2026-04-24T00:00:00Z",
        ledger_entries=[ledger],
    )

    payload = artifact.to_dict()

    assert payload["ledger_refs"] == ["review:thread:42"]


def test_artifact_rejects_unknown_source() -> None:
    artifact = AgentsRuleAggregationArtifact(
        schema_version="0.1",
        generated_at="2026-04-24T00:00:00Z",
        source="runtime_extraction",
    )

    with pytest.raises(ValueError, match="unsupported source"):
        artifact.to_dict()
