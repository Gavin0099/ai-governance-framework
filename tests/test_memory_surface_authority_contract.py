from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from governance_tools.authority_loader import parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = REPO_ROOT / "governance" / "AUTHORITY.md"
AGENT = REPO_ROOT / "governance" / "AGENT.md"
MEMORY_PROTOCOL = REPO_ROOT / "governance" / "MEMORY_PROTOCOL.md"
MEMORY_AUTHORITY = REPO_ROOT / "governance" / "MEMORY_AUTHORITY_CONTRACT.md"
SURFACE_CONTRACT = REPO_ROOT / "governance" / "MEMORY_SURFACE_AUTHORITY_CONTRACT.md"


def _json_block(marker: str) -> Any:
    text = SURFACE_CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(marker)}:begin -->\s*```json\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(marker)}:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _reader_vocabulary() -> dict[str, list[str]]:
    return _json_block("mrcsp-reader-vocabulary")


def _resolution_cases() -> list[dict[str, object]]:
    return _json_block("mrcsp-resolution-cases")


def _activation_id(path: Path) -> str:
    match = re.search(
        r"<!-- mrcsp_activation_id: ([a-z0-9-]+) -->",
        path.read_text(encoding="utf-8"),
    )
    assert match is not None
    return match.group(1)


def _override_chain(start: Path) -> list[str]:
    chain: list[str] = []
    current = start
    seen: set[Path] = set()
    while True:
        assert current not in seen, f"authority override cycle at {current.name}"
        seen.add(current)
        chain.append(current.name)
        target = parse_frontmatter(current).get("overridden_by")
        if not target:
            return chain
        current = current.parent / str(target)
        assert current.is_file(), f"missing override target {target}"


def _case_errors(case: dict[str, object], vocabulary: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    query_class = case.get("query_class")
    resolution = case.get("expected_resolution")
    projection_status = case.get("projection_status")
    review_status = case.get("review_status")
    reviewer_authority_state = case.get("reviewer_authority_state")
    anchor_state = case.get("anchor_state")
    state_transition_coverage = case.get("state_transition_coverage")
    later_change_state = case.get("later_change_state")
    coverage_boundary_state = case.get("coverage_boundary_state")
    knowledge_promotion_state = case.get("knowledge_promotion_state", "not_applicable")
    supersession_state = case.get("supersession_state", "not_applicable")
    review_validity_state = case.get("review_validity_state", "not_applicable")
    review_recency_state = case.get("review_recency_state", "not_applicable")

    if query_class not in vocabulary["query_classes"]:
        errors.append("unknown_query_class")
    if resolution not in vocabulary["resolution_states"]:
        errors.append("unknown_resolution_state")
    if projection_status not in vocabulary["projection_statuses"]:
        errors.append("unknown_projection_status")
    if review_status not in vocabulary["review_statuses"]:
        errors.append("unknown_review_status")
    if reviewer_authority_state not in vocabulary["reviewer_authority_states"]:
        errors.append("unknown_reviewer_authority_state")
    if anchor_state not in vocabulary["anchor_states"]:
        errors.append("unknown_anchor_state")
    if state_transition_coverage not in vocabulary["state_transition_coverage_states"]:
        errors.append("unknown_state_transition_coverage")
    if later_change_state not in vocabulary["later_change_states"]:
        errors.append("unknown_later_change_state")
    if coverage_boundary_state not in vocabulary["coverage_boundary_states"]:
        errors.append("unknown_coverage_boundary_state")
    if knowledge_promotion_state not in vocabulary["knowledge_promotion_states"]:
        errors.append("unknown_knowledge_promotion_state")
    if supersession_state not in vocabulary["supersession_states"]:
        errors.append("unknown_supersession_state")
    if review_validity_state not in vocabulary["review_validity_states"]:
        errors.append("unknown_review_validity_state")
    if review_recency_state not in vocabulary["review_recency_states"]:
        errors.append("unknown_review_recency_state")

    current_projection_query = query_class in {"current_progress", "current_operations"}
    if current_projection_query and resolution == "resolved":
        if projection_status != "current":
            errors.append("resolved_projection_not_current")
        if review_status != "reviewed":
            errors.append("resolved_projection_not_reviewed")
        if reviewer_authority_state != "authority_qualified":
            errors.append("resolved_projection_reviewer_not_authority_qualified")
        if anchor_state != "covers_latest_qualified_evidence":
            errors.append("resolved_projection_coverage_incomplete")
        if state_transition_coverage != "covers_latest_substantive_transition":
            errors.append("resolved_projection_latest_transition_missing")
        if later_change_state != "none_unreconciled":
            errors.append("resolved_projection_has_later_unreconciled_change")
        if coverage_boundary_state != "determinable_without_semantic_guessing":
            errors.append("resolved_projection_boundary_indeterminable")

    if query_class == "reusable_knowledge" and resolution == "resolved":
        if knowledge_promotion_state != "promoted":
            errors.append("resolved_knowledge_not_promoted")
        if review_status != "reviewed":
            errors.append("resolved_knowledge_not_reviewed")
        if reviewer_authority_state != "authority_qualified":
            errors.append("resolved_knowledge_reviewer_not_authority_qualified")
        if supersession_state != "current_non_superseded":
            errors.append("resolved_knowledge_superseded_or_unknown")

    if query_class == "current_review_verdict" and resolution == "resolved":
        if review_status != "reviewed":
            errors.append("resolved_review_not_reviewed")
        if reviewer_authority_state != "authority_qualified":
            errors.append("resolved_review_reviewer_not_authority_qualified")
        if supersession_state != "current_non_superseded":
            errors.append("resolved_review_superseded_or_unknown")
        if review_validity_state != "valid":
            errors.append("resolved_review_invalid_or_unknown")
        if review_recency_state != "latest_valid":
            errors.append("resolved_review_not_latest_valid")

    if resolution != "resolved" and case.get("expected_current_source") is not None:
        errors.append("unresolved_case_has_current_source")
    if anchor_state == "later_qualified_evidence_unreconciled" and resolution != "reviewer_required":
        errors.append("later_evidence_not_escalated")
    if review_status == "unreviewed" and current_projection_query and resolution == "resolved":
        errors.append("unreviewed_projection_resolved")
    if review_status == "disputed" and resolution != "disputed":
        errors.append("disputed_projection_not_preserved")
    return errors


def test_surface_contract_activation_is_atomic_and_non_circular() -> None:
    metadata = parse_frontmatter(SURFACE_CONTRACT)
    assert metadata == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }

    authority = AUTHORITY.read_text(encoding="utf-8")
    protocol = MEMORY_PROTOCOL.read_text(encoding="utf-8")
    authority_contract = MEMORY_AUTHORITY.read_text(encoding="utf-8")
    surface_contract = SURFACE_CONTRACT.read_text(encoding="utf-8")

    assert (
        "| `governance/MEMORY_SURFACE_AUTHORITY_CONTRACT.md` | agent-on-demand | "
        "canonical | false | AGENT.md | on-demand |"
    ) in authority
    assert "Status: ACTIVE WHEN MERGED AFTER AUTHORIZED REVIEW" in surface_contract
    assert "No single file activates it" in protocol
    assert "M-1 activation does not authorize M0" in protocol
    assert "A branch or partial document\nupdate is candidate evidence only" in authority_contract
    assert "PROPOSED - reviewer approval required" not in surface_contract

    activation_paths = (AUTHORITY, MEMORY_PROTOCOL, MEMORY_AUTHORITY, SURFACE_CONTRACT)
    assert {_activation_id(path) for path in activation_paths} == {
        "mrcsp-m1-authority-reader-v1"
    }
    assert _override_chain(SURFACE_CONTRACT) == [
        "MEMORY_SURFACE_AUTHORITY_CONTRACT.md",
        "AGENT.md",
    ]
    assert _override_chain(MEMORY_PROTOCOL) == ["MEMORY_PROTOCOL.md", "AGENT.md"]
    assert parse_frontmatter(AGENT).get("overridden_by") is None


def test_contract_cases_use_declared_vocabulary_and_valid_failure_semantics() -> None:
    vocabulary = _reader_vocabulary()
    cases = _resolution_cases()

    assert len(cases) == 21
    assert all(_case_errors(case, vocabulary) == [] for case in cases)
    assert all(case["history_preserved"] is True for case in cases)


def test_required_resolution_and_negative_cases_are_frozen() -> None:
    cases = {case["id"]: case for case in _resolution_cases()}
    assert set(cases) == {
        "daily_vs_plan",
        "daily_vs_reviewed_01",
        "old_review_vs_newer_authority_qualified_review",
        "candidate_kb_vs_promoted_kb",
        "superseded_vs_current",
        "qualified_source_conflict",
        "unreviewed_current_projection",
        "disputed_current_projection",
        "missing_projection_anchors",
        "legacy_projection_unassessable",
        "self_attested_reviewer_projection",
        "unqualified_reviewer_projection",
        "unknown_reviewer_authority_projection",
        "missing_latest_state_transition",
        "indeterminable_coverage_boundary",
        "candidate_only_knowledge",
        "superseded_promoted_knowledge",
        "invalid_current_review_verdict",
        "non_latest_valid_review_verdict",
        "superseded_current_review_verdict",
        "unqualified_current_review_verdict",
    }

    assert cases["daily_vs_reviewed_01"]["anchor_state"] == "covers_latest_qualified_evidence"
    assert cases["daily_vs_reviewed_01"]["expected_resolution"] == "resolved"
    assert cases["superseded_vs_current"]["query_class"] == "current_progress"

    expected_negative_resolutions = {
        "qualified_source_conflict": "reviewer_required",
        "unreviewed_current_projection": "reviewer_required",
        "disputed_current_projection": "disputed",
        "missing_projection_anchors": "insufficient_authority",
        "legacy_projection_unassessable": "unassessable",
        "self_attested_reviewer_projection": "insufficient_authority",
        "unqualified_reviewer_projection": "insufficient_authority",
        "unknown_reviewer_authority_projection": "insufficient_authority",
        "missing_latest_state_transition": "reviewer_required",
        "indeterminable_coverage_boundary": "unassessable",
        "candidate_only_knowledge": "insufficient_authority",
        "superseded_promoted_knowledge": "insufficient_authority",
        "invalid_current_review_verdict": "insufficient_authority",
        "non_latest_valid_review_verdict": "reviewer_required",
        "superseded_current_review_verdict": "reviewer_required",
        "unqualified_current_review_verdict": "insufficient_authority",
    }
    for case_id, expected in expected_negative_resolutions.items():
        assert cases[case_id]["expected_current_source"] is None
        assert cases[case_id]["expected_resolution"] == expected


def test_contract_validator_rejects_unknown_or_false_authority_cases() -> None:
    vocabulary = _reader_vocabulary()
    valid = next(case for case in _resolution_cases() if case["id"] == "daily_vs_reviewed_01")

    unknown_query = deepcopy(valid)
    unknown_query["query_class"] = "current_state"
    assert "unknown_query_class" in _case_errors(unknown_query, vocabulary)

    missing_anchor = deepcopy(valid)
    missing_anchor["anchor_state"] = "missing_or_untraceable"
    assert "resolved_projection_coverage_incomplete" in _case_errors(missing_anchor, vocabulary)

    later_evidence = deepcopy(valid)
    later_evidence["anchor_state"] = "later_qualified_evidence_unreconciled"
    assert "later_evidence_not_escalated" in _case_errors(later_evidence, vocabulary)

    unreviewed = deepcopy(valid)
    unreviewed["review_status"] = "unreviewed"
    assert "resolved_projection_not_reviewed" in _case_errors(unreviewed, vocabulary)

    self_attested = deepcopy(valid)
    self_attested["reviewer_authority_state"] = "self_attested_only"
    assert "resolved_projection_reviewer_not_authority_qualified" in _case_errors(
        self_attested, vocabulary
    )

    missing_transition = deepcopy(valid)
    missing_transition["state_transition_coverage"] = "missing_latest_substantive_transition"
    assert "resolved_projection_latest_transition_missing" in _case_errors(
        missing_transition, vocabulary
    )

    later_change = deepcopy(valid)
    later_change["later_change_state"] = "unreconciled_qualified_change"
    assert "resolved_projection_has_later_unreconciled_change" in _case_errors(
        later_change, vocabulary
    )

    indeterminable = deepcopy(valid)
    indeterminable["coverage_boundary_state"] = "indeterminable"
    assert "resolved_projection_boundary_indeterminable" in _case_errors(
        indeterminable, vocabulary
    )

    valid_knowledge = next(
        case for case in _resolution_cases() if case["id"] == "candidate_kb_vs_promoted_kb"
    )
    candidate_knowledge = deepcopy(valid_knowledge)
    candidate_knowledge["knowledge_promotion_state"] = "candidate"
    assert "resolved_knowledge_not_promoted" in _case_errors(candidate_knowledge, vocabulary)

    superseded_knowledge = deepcopy(valid_knowledge)
    superseded_knowledge["supersession_state"] = "superseded"
    assert "resolved_knowledge_superseded_or_unknown" in _case_errors(
        superseded_knowledge, vocabulary
    )

    unqualified_knowledge = deepcopy(valid_knowledge)
    unqualified_knowledge["reviewer_authority_state"] = "unqualified"
    assert "resolved_knowledge_reviewer_not_authority_qualified" in _case_errors(
        unqualified_knowledge, vocabulary
    )

    valid_review = next(
        case
        for case in _resolution_cases()
        if case["id"] == "old_review_vs_newer_authority_qualified_review"
    )
    invalid_review = deepcopy(valid_review)
    invalid_review["review_validity_state"] = "invalid"
    assert "resolved_review_invalid_or_unknown" in _case_errors(invalid_review, vocabulary)

    stale_review = deepcopy(valid_review)
    stale_review["review_recency_state"] = "not_latest"
    assert "resolved_review_not_latest_valid" in _case_errors(stale_review, vocabulary)

    superseded_review = deepcopy(valid_review)
    superseded_review["supersession_state"] = "superseded"
    assert "resolved_review_superseded_or_unknown" in _case_errors(
        superseded_review, vocabulary
    )

    unqualified_review = deepcopy(valid_review)
    unqualified_review["reviewer_authority_state"] = "unqualified"
    assert "resolved_review_reviewer_not_authority_qualified" in _case_errors(
        unqualified_review, vocabulary
    )


def test_canonical_contracts_keep_record_and_authority_claims_separate() -> None:
    protocol = MEMORY_PROTOCOL.read_text(encoding="utf-8")
    authority_contract = MEMORY_AUTHORITY.read_text(encoding="utf-8")

    for token in (
        "canonical_record",
        "authority_class",
        "projection_status",
        "review_status",
        "MEMORY_SURFACE_AUTHORITY_CONTRACT.md",
    ):
        assert token in protocol
        assert token in authority_contract

    assert "There is no global memory precedence" in protocol
    assert "do not\nguess" in protocol


def test_m1_contract_does_not_admit_runtime_m0_or_unmerged_pr88_behavior() -> None:
    contract = SURFACE_CONTRACT.read_text(encoding="utf-8")
    assert "no M0 consumer fixture" in contract
    assert "no reader, detector, schema" in contract
    assert "no dependency on unmerged PR #88 behavior" in contract
    assert "M0 still requires a\nseparate owner-authorized" in contract
    assert "terminal_closeout_not_observed" not in contract
