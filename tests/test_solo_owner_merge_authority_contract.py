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
MERGE_GATE_SKILL = REPO_ROOT / ".agents" / "skills" / "pr-review-merge-gate" / "SKILL.md"


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
    integration_checks = case.get("integration_checks")
    head_state = case.get("head_state")
    github_approval = case.get("github_approved_review")
    decision = case.get("expected_decision")

    if attestation not in vocabulary["attestation_states"]:
        errors.append("unknown_attestation_state")
    if review not in vocabulary["technical_review_states"]:
        errors.append("unknown_technical_review_state")
    if checks not in vocabulary["check_states"]:
        errors.append("unknown_check_state")
    if integration_checks not in vocabulary["integration_check_states"]:
        errors.append("unknown_integration_check_state")
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
        and integration_checks in {
            "head_contains_current_base",
            "merge_candidate_green_for_current_base",
        }
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
    predicate_summary = (
        "exact-head owner attestation, independent technical review, green required "
        "checks, reviewed-head preservation, and current-base integration evidence"
    )
    assert f"five merge predicates: {predicate_summary}." in " ".join(agent.split())
    assert (
        "| `governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md` | canonical solo-owner "
        f"merge decision contract | five predicates: {predicate_summary} |"
    ) in " ".join(authority.split())


def test_merge_gate_skill_summaries_preserve_five_predicate_requirements() -> None:
    skill = MERGE_GATE_SKILL.read_text(encoding="utf-8")
    check_only = " ".join(
        skill.split("## Check-Only Mode\n", 1)[1].split("\n## ", 1)[0].split()
    )
    merge_gate = " ".join(
        skill.split("## Select the Gate\n", 1)[1].split("\n## ", 1)[0].split()
    )
    required_check_only_text = (
        "report each of its five predicates",
        "For `integration_checks`, report its state and evidence tuple "
        "(target tip SHA, head SHA, required-check set).",
        "Derive the set from all applicable repository configuration "
        "(classic branch protection and rulesets); the agent must not choose the set.",
        "Re-running an earlier workflow run or attempt is not fresh integration "
        "evidence; see the contract.",
    )
    for text in required_check_only_text:
        assert text in check_only

    assert "verify all five predicates" in merge_gate
    for predicate in (
        "owner_merge_attestation=recorded_for_exact_head",
        "independent_technical_review=independent_approved_for_exact_head",
        "required_checks=green_for_exact_head",
        "head_state=matches_reviewed_head",
        "integration_checks=head_contains_current_base",
        "integration_checks=merge_candidate_green_for_current_base",
    ):
        assert f"`{predicate}`" in merge_gate


def test_integration_check_vocabulary_covers_current_base_evidence_states() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")

    assert vocabulary["integration_check_states"] == [
        "head_contains_current_base",
        "merge_candidate_green_for_current_base",
        "base_advanced_without_integration_evidence",
        "required_check_set_changed",
        "pending",
        "failing",
        "missing_or_unknown",
    ]


def test_normative_cases_are_semantically_consistent() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = _json_block("solo-owner-merge-cases")

    assert len(cases) == 17
    assert all(_case_errors(case, vocabulary) == [] for case in cases)


def test_integration_evidence_prose_preserves_required_semantics() -> None:
    text = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    required_sentences = (
        "Advancing the target branch does not make those head check results stale, "
        "failing, or missing; current integration coverage is a separate predicate below.",
        "Integration evidence is identified by the tuple (target tip SHA, head SHA, "
        "required-check set). It applies only when all three match the current merge "
        "decision; any mismatch means the evidence does not apply.",
        "`integration_checks` cannot be satisfied by an empty or undeterminable "
        "required-check set or by absent CI evidence; such cases are `missing_or_unknown`.",
        "An accepted `integration_checks` state holds only while the tuple (target tip SHA, "
        "head SHA, required-check set) is unchanged up to the merge; if any element changes "
        "before merge, the predicate reverts to the matching non-accepted state and "
        "eligibility lapses.",
        "Integration evidence must identify the revision actually tested and bind it to "
        "both the target tip and the exact head (for example, a merge commit whose parents "
        "are that tip and head, or run metadata recording both SHAs and the tested ref).",
        "Event type alone is insufficient: a `pull_request`-triggered job that explicitly "
        "checks out only the head is head evidence, not merge-candidate evidence.",
    )

    for sentence in required_sentences:
        assert " ".join(sentence.split()) in text


def test_fresh_run_prose_excludes_rerunning_stale_workflow_attempts() -> None:
    text = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    required_sentences = (
        "For GitHub Actions, re-running an existing workflow run or attempt reuses the "
        "original event's `GITHUB_SHA`.",
        "The framework's `governance.yml` checks out `${{ github.sha }}`; for "
        "`pull_request`, this is the merge commit computed at event time.",
        "After the target tip advances, evidence must come from a fresh run whose tested "
        "revision is verified to bind the current target tip and exact head.",
        "A new `pull_request` event such as `synchronize` or `reopened` may trigger a "
        "fresh run, but the event type alone is insufficient.",
        "A test-merge run or merge-queue evidence may also qualify under the same "
        "tested-revision binding requirement.",
        "Re-running an earlier workflow run or attempt is not an evidence refresh, "
        "because it tests the earlier merge candidate.",
        "If fresh evidence cannot be produced or the tested revision cannot be shown to "
        "bind the current target tip and exact head, `integration_checks` fails closed "
        "(for base drift, `base_advanced_without_integration_evidence`), and eligibility "
        "is `ineligible`.",
        "With an unchanged head, re-verification requires only fresh integration evidence "
        "for the current target tip and exact head; no re-review is required.",
    )

    for sentence in required_sentences:
        assert " ".join(sentence.split()) in text


def test_consumer_adoption_prose_requires_a_declared_verifiable_check_set() -> None:
    text = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    required_sentences = (
        "Before adopting the five-predicate text, a consumer must have a non-empty, "
        "explicitly declared, verifiable required-check set from repository configuration "
        "or a separately authorized governance declaration.",
        "Classic branch protection and repository rulesets both count as repository "
        "configuration; the required set must cover all applicable requirements from "
        "either or both sources.",
        "A 404 from the classic branch-protection API alone is not evidence that the "
        "required-check set is empty.",
        "An agent must not choose a subset of green checks and treat it as the required set.",
        "A consumer without such a set will find every merge ineligible under this "
        "text; this is the disclosed adoption cost, not a reason to relax the "
        "empty-required-check-set rule.",
    )

    for sentence in required_sentences:
        assert " ".join(sentence.split()) in text


def test_rerun_of_stale_attempt_is_not_integration_evidence() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}
    rerun_case = cases["rerun_of_stale_attempt_is_not_integration_evidence"]

    assert rerun_case["required_checks"] == "green_for_exact_head"
    assert rerun_case["integration_checks"] == "base_advanced_without_integration_evidence"
    assert rerun_case["expected_decision"] == "ineligible"
    assert _case_errors(rerun_case, vocabulary) == []


def test_empty_required_check_set_is_not_integration_evidence() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}
    empty_set_case = cases["empty_required_check_set_is_not_integration_evidence"]

    assert empty_set_case["integration_checks"] == "missing_or_unknown"
    assert empty_set_case["expected_decision"] == "ineligible"
    assert _case_errors(empty_set_case, vocabulary) == []


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
    predicate_states = {
        "owner_merge_attestation": (
            vocabulary["attestation_states"],
            {"recorded_for_exact_head"},
        ),
        "independent_technical_review": (
            vocabulary["technical_review_states"],
            {"independent_approved_for_exact_head"},
        ),
        "required_checks": (vocabulary["check_states"], {"green_for_exact_head"}),
        "head_state": (vocabulary["head_states"], {"matches_reviewed_head"}),
        "integration_checks": (
            vocabulary["integration_check_states"],
            {"head_contains_current_base", "merge_candidate_green_for_current_base"},
        ),
    }

    for field, (states, valid_states) in predicate_states.items():
        for state in states:
            mutant = deepcopy(baseline)
            mutant[field] = state
            if state in valid_states:
                assert _case_errors(mutant, vocabulary) == []
                continue
            assert "decision_does_not_match_required_predicates" in _case_errors(
                mutant, vocabulary
            )
            mutant["expected_decision"] = "ineligible"
            assert _case_errors(mutant, vocabulary) == []


def test_base_drift_does_not_alter_required_checks() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}
    drift_case = cases["base_advanced_head_checks_still_green"]

    assert drift_case["required_checks"] == "green_for_exact_head"
    assert drift_case["integration_checks"] == "base_advanced_without_integration_evidence"
    assert drift_case["expected_decision"] == "ineligible"
    assert _case_errors(drift_case, vocabulary) == []

    refreshed_case = deepcopy(drift_case)
    refreshed_case["integration_checks"] = "merge_candidate_green_for_current_base"
    refreshed_case["expected_decision"] = "eligible"
    assert _case_errors(refreshed_case, vocabulary) == []


def test_both_accepted_integration_states_are_eligible_with_other_predicates() -> None:
    vocabulary = _json_block("solo-owner-merge-vocabulary")
    cases = {case["case_id"]: case for case in _json_block("solo-owner-merge-cases")}

    for state in ("head_contains_current_base", "merge_candidate_green_for_current_base"):
        case = cases[state]
        assert case["integration_checks"] == state
        assert case["expected_decision"] == "eligible"
        assert _case_errors(case, vocabulary) == []


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
    assert "does not make PR #103 retroactively compliant" in text
