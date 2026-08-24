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
CONTRACT = REPO_ROOT / "governance" / "SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md"


def _json_block(marker: str) -> Any:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(marker)}:begin -->\s*```json\s*(.*?)\s*```\s*"
        rf"<!-- {re.escape(marker)}:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _case_errors(case: dict[str, object], vocabulary: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    attestation = case.get("owner_merge_attestation")
    review = case.get("independent_technical_review")
    checks = case.get("required_checks")
    head_state = case.get("head_state")
    github_approval = case.get("github_approved_review")
    decision = case.get("expected_decision")

    if attestation not in vocabulary["attestation_states"]:
        errors.append("unknown_attestation_state")
    if review not in vocabulary["technical_review_states"]:
        errors.append("unknown_technical_review_state")
    if checks not in vocabulary["check_states"]:
        errors.append("unknown_check_state")
    if head_state not in vocabulary["head_states"]:
        errors.append("unknown_head_state")
    if github_approval not in vocabulary["github_approval_states"]:
        errors.append("unknown_github_approval_state")
    if decision not in vocabulary["merge_decisions"]:
        errors.append("unknown_merge_decision")

    predicates_hold = (
        attestation == "recorded_for_exact_head"
        and review == "independent_approved_for_exact_head"
        and checks == "green_for_exact_head"
        and head_state == "matches_reviewed_head"
    )
    expected_from_predicates = "eligible" if predicates_hold else "ineligible"
    if decision != expected_from_predicates:
        errors.append("decision_does_not_match_required_predicates")
    return errors


def test_contract_is_registered_and_routed_as_canonical_on_demand_authority() -> None:
    assert parse_frontmatter(CONTRACT) == {
        "audience": "agent-on-demand",
        "authority": "canonical",
        "can_override": False,
        "overridden_by": "AGENT.md",
        "default_load": "on-demand",
    }

    authority = AUTHORITY.read_text(encoding="utf-8")
    agent = AGENT.read_text(encoding="utf-8")
    assert (
        "| `governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md` | agent-on-demand | "
        "canonical | false | AGENT.md | on-demand |"
    ) in authority
    assert "`SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md`" in agent


def test_normative_cases_are_semantically_consistent() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = _json_block("solo-owner-merge-cases")

    assert len(cases) == 9
    assert all(_case_errors(case, vocabulary) == [] for case in cases)


def test_github_approval_is_optional_and_cannot_substitute_for_required_evidence() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}

    without_github_approval = cases["all_required_predicates_without_github_approval"]
    assert without_github_approval["expected_decision"] == "eligible"
    assert _case_errors(without_github_approval, vocabulary) == []

    missing_review = cases["missing_independent_review"]
    assert missing_review["github_approved_review"] == "present"
    assert missing_review["expected_decision"] == "ineligible"
    assert _case_errors(missing_review, vocabulary) == []


def test_every_required_predicate_fails_closed_when_mutated() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = _json_block("solo-owner-merge-cases")
    baseline = next(
        case for case in cases if case["case_id"] == "all_required_predicates_without_github_approval"
    )
    invalid_states = {
        "owner_merge_attestation": (
            vocabulary["attestation_states"],
            "recorded_for_exact_head",
        ),
        "independent_technical_review": (
            vocabulary["technical_review_states"],
            "independent_approved_for_exact_head",
        ),
        "required_checks": (vocabulary["check_states"], "green_for_exact_head"),
        "head_state": (vocabulary["head_states"], "matches_reviewed_head"),
    }

    for field, (states, valid_state) in invalid_states.items():
        for invalid_state in set(states) - {valid_state}:
            mutant = deepcopy(baseline)
            mutant[field] = invalid_state
            assert "decision_does_not_match_required_predicates" in _case_errors(
                mutant, vocabulary
            )
            mutant["expected_decision"] = "ineligible"
            assert _case_errors(mutant, vocabulary) == []


def test_post_merge_action_is_not_reclassified_as_pre_merge_attestation() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}
    post_merge_case = cases["post_merge_action_is_not_pre_merge_attestation"]

    assert post_merge_case["owner_merge_attestation"] == "inferred_or_agent_generated"
    assert post_merge_case["expected_decision"] == "ineligible"
    assert _case_errors(post_merge_case, vocabulary) == []


def test_contract_does_not_claim_github_or_runtime_enforcement() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "A GitHub `APPROVED` review is\n> optional additional evidence" in text
    assert re.search(r"does\s+not change GitHub branch protection", text)
    assert "does not make PRs #101 or #103 retroactively compliant" in text
