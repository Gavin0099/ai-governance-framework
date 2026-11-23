---
audience: agent-on-demand
authority: canonical
can_override: false
overridden_by: AGENT.md
default_load: on-demand
---

# Solo-Owner Merge Authority Contract

Status: ACTIVE WHEN MERGED AFTER OWNER ATTESTATION, AUTHORIZED INDEPENDENT
TECHNICAL REVIEW, GREEN REQUIRED CHECKS, AND CURRENT-BASE INTEGRATION EVIDENCE

## Observed Failure And Applicability

PR #103's final reviewer-facing body required a human GitHub `APPROVED` review,
but its GitHub review list was empty when the PR was merged. The stated prose
gate and the recorded merge evidence therefore disagreed. A PR body must not
invent a merge authority requirement that is absent from the canonical
governance model.

In consumer story2video PR #3, required checks were green for the exact PR head
but had tested its merge with an old target tip. After the target branch
advanced, the current merge candidate had no CI result. The head's check
results did not establish integration coverage for the current target tip.

This contract applies when the repository owner explicitly operates the
repository under a solo-owner authority model. It replaces a mandatory GitHub
`APPROVED` review with a conjunctive, evidence-bound merge decision. A GitHub
`APPROVED` review remains valid additional evidence when available, but it is
not a required predicate and cannot substitute for a missing predicate below.

## Normative Merge Decision

<!-- solo-owner-merge-vocabulary:begin -->
```json
{
  "attestation_states": [
    "recorded_for_exact_head",
    "missing",
    "stale",
    "inferred_or_agent_generated"
  ],
  "check_states": [
    "green_for_exact_head",
    "pending",
    "failing",
    "missing_or_unknown"
  ],
  "integration_check_states": [
    "head_contains_current_base",
    "merge_candidate_green_for_current_base",
    "base_advanced_without_integration_evidence",
    "required_check_set_changed",
    "pending",
    "failing",
    "missing_or_unknown"
  ],
  "github_approval_states": [
    "present",
    "absent"
  ],
  "head_states": [
    "matches_reviewed_head",
    "substantive_change_after_review",
    "unknown"
  ],
  "merge_decisions": [
    "eligible",
    "ineligible"
  ],
  "technical_review_states": [
    "independent_approved_for_exact_head",
    "missing",
    "changes_requested",
    "stale",
    "not_independent"
  ]
}
```
<!-- solo-owner-merge-vocabulary:end -->

The merge decision is `eligible` if and only if all five predicates hold for the
same exact candidate head, with integration evidence for the current target
branch tip and required-check set:

1. `owner_merge_attestation=recorded_for_exact_head`;
2. `independent_technical_review=independent_approved_for_exact_head`;
3. `required_checks=green_for_exact_head`;
4. `head_state=matches_reviewed_head`; and
5. `integration_checks` is either `head_contains_current_base` or
   `merge_candidate_green_for_current_base`.

Any missing, unknown, stale, failing, or non-independent required predicate
makes the decision `ineligible`. The decision fails closed; it must not be
rounded up from partial evidence.

## Predicate Meanings

### Owner merge attestation

The repository owner must make a current, explicit human statement authorizing
merge of the exact candidate head or immutable range. It may be recorded in an
authenticated PR comment, an authoring session, or another durable handoff
surface that identifies the target bytes.

An agent must not infer this attestation from a PLAN item, memory `next_step`, a
general continuation instruction, its own recommendation, or the later fact
that a merge occurred. An authenticated owner merge action can prove who
performed the merge during a post-merge audit, but it does not retroactively
prove that the pre-merge attestation predicate was satisfied.

### Independent technical review

The review must be performed by a reviewer distinct from the implementation
authoring process, identify the exact head or immutable range reviewed, apply
the applicable `REVIEW_CRITERIA.md` evidence rules, and finish with no blocking
findings. A GitHub review object is one possible transport, not the authority
source. A bounded independent sub-agent or human review can satisfy this
predicate when its identity, target, evidence, and verdict are recorded.

### Green required checks

Every check configured as required for the target branch must report success
for the exact candidate head. Pending, failing, absent, or indeterminate
required contexts fail closed. Event-inapplicable jobs that are not configured
as required do not become required merely because they exist in a workflow.

This predicate reports checks for the exact PR head. Advancing the target
branch does not make those head check results stale, failing, or missing;
current integration coverage is a separate predicate below.

### Reviewed-head preservation

The merge candidate must match the exact head approved by the independent
technical review. Any substantive change after that review invalidates the
review predicate and requires a new review of the changed head. Metadata-only
PR edits do not change the Git head and therefore do not invalidate a
commit-bound review.

### Integration checks for the current target tip

Integration evidence is identified by the tuple (target tip SHA, head SHA,
required-check set). It applies only when all three match the current merge
decision; any mismatch means the evidence does not apply.

An accepted `integration_checks` state holds only while the tuple (target tip
SHA, head SHA, required-check set) is unchanged up to the merge; if any element
changes before merge, the predicate reverts to the matching non-accepted state
and eligibility lapses.

`integration_checks` cannot be satisfied by an empty or undeterminable
required-check set or by absent CI evidence; such cases are `missing_or_unknown`.

Only these two states satisfy `integration_checks`:

- `head_contains_current_base`: the exact head already contains the target
  branch's current tip, and the required checks green for that head ran against
  the current required set. The integration is the head itself.
- `merge_candidate_green_for_current_base`: every currently required check
  succeeded on the exact merge candidate of the current target tip and exact
  head. Evidence may be a pull_request merge-ref run whose recorded base equals
  the current target tip, or equivalent merge-queue evidence for that same tip
  and head.

Integration evidence must identify the revision actually tested and bind it to
both the target tip and the exact head (for example, a merge commit whose parents
are that tip and head, or run metadata recording both SHAs and the tested ref).
Event type alone is insufficient: a `pull_request`-triggered job that explicitly
checks out only the head is head evidence, not merge-candidate evidence.

For GitHub Actions, re-running an existing workflow run or attempt reuses the
original event's `GITHUB_SHA`. The framework's `governance.yml` checks out
`${{ github.sha }}`; for `pull_request`, this is the merge commit computed at
event time.

After the target tip advances, evidence must come from a fresh run whose tested
revision is verified to bind the current target tip and exact head. A new
`pull_request` event such as `synchronize` or `reopened` may trigger a fresh run,
but the event type alone is insufficient. A test-merge run or merge-queue
evidence may also qualify under the same tested-revision binding requirement.
Re-running an earlier workflow run or attempt is not an evidence refresh,
because it tests the earlier merge candidate.

If fresh evidence cannot be produced or the tested revision cannot be shown to
bind the current target tip and exact head, `integration_checks` fails closed
(for base drift, `base_advanced_without_integration_evidence`), and eligibility
is `ineligible`.

Every other state fails closed:

- `base_advanced_without_integration_evidence`: the target tip moved after the
  evidence ran, and no evidence exists for the current tip.
- `required_check_set_changed`: the set of checks required for the target branch
  changed after the evidence ran, and the new set is not covered.
- `pending`: the required integration checks have not all completed.
- `failing`: a required integration check failed.
- `missing_or_unknown`: applicable integration evidence is absent or cannot be
  established.

Base drift invalidates only integration evidence, never the head's own check
results, independent review, or owner attestation. With an unchanged head,
re-verification requires only fresh integration evidence for the current target
tip and exact head; no re-review is required. If the head itself changes, the
existing exact-head and reviewed-head predicates still apply.

GitHub's "strict" required-status mode or a merge queue are ways to produce
such evidence. This contract does not require or configure either mechanism.

## Normative Cases

<!-- solo-owner-merge-cases:begin -->
```json
[
  {
    "case_id": "all_required_predicates_without_github_approval",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "absent",
    "expected_decision": "eligible"
  },
  {
    "case_id": "github_approval_is_additional_evidence",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "eligible"
  },
  {
    "case_id": "missing_owner_attestation",
    "owner_merge_attestation": "missing",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "missing_independent_review",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "missing",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "changes_requested",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "changes_requested",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "required_checks_pending",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "pending",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "required_checks_failing",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "failing",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "substantive_change_after_review",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "stale",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "substantive_change_after_review",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "post_merge_action_is_not_pre_merge_attestation",
    "owner_merge_attestation": "inferred_or_agent_generated",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "absent",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "base_advanced_head_checks_still_green",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "base_advanced_without_integration_evidence",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "rerun_of_stale_attempt_is_not_integration_evidence",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "base_advanced_without_integration_evidence",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "merge_candidate_green_for_current_base",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "merge_candidate_green_for_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "absent",
    "expected_decision": "eligible"
  },
  {
    "case_id": "head_contains_current_base",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "head_contains_current_base",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "absent",
    "expected_decision": "eligible"
  },
  {
    "case_id": "integration_checks_failing",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "failing",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "required_check_set_changed",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "required_check_set_changed",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "integration_missing_or_unknown",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "missing_or_unknown",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  },
  {
    "case_id": "empty_required_check_set_is_not_integration_evidence",
    "owner_merge_attestation": "recorded_for_exact_head",
    "independent_technical_review": "independent_approved_for_exact_head",
    "required_checks": "green_for_exact_head",
    "integration_checks": "missing_or_unknown",
    "head_state": "matches_reviewed_head",
    "github_approved_review": "present",
    "expected_decision": "ineligible"
  }
]
```
<!-- solo-owner-merge-cases:end -->

## Reviewer-Facing Language

For a solo-owner repository, use this merge condition:

> Merge requires an owner merge attestation for the exact head, an independent
> technical review approving that same head, green required checks for that
> head, integration evidence for the current target tip and required-check set,
> and no substantive change after review. A GitHub `APPROVED` review is
> optional additional evidence, not a mandatory authority predicate.

Do not write "human APPROVED review required" or "GitHub APPROVED required"
unless a separate owner decision has deliberately adopted that stronger model
and the repository's enforcement and reviewer workflow are aligned with it.

## Activation and compatibility

The added `integration_checks` predicate applies to merge decisions made after
this amendment is merged. It does not reclassify earlier merges. Consumers
pinned to an older framework copy keep the old four-predicate text until they
update.

Before adopting the five-predicate text, a consumer must have a non-empty,
explicitly declared, verifiable required-check set from repository configuration
or a separately authorized governance declaration. Classic branch protection
and repository rulesets both count as repository configuration; the required
set must cover all applicable requirements from either or both sources. A 404
from the classic branch-protection API alone is not evidence that the
required-check set is empty.

An agent must not choose a subset of green checks and treat it as the required
set. A consumer without such a set will find every merge ineligible under this
text; this is the disclosed adoption cost, not a reason to relax the
empty-required-check-set rule.

## Claim Ceiling And Non-Goals

This contract defines decision authority and reporting semantics only. It does
not change GitHub branch protection, rulesets, required checks, reviewer
permissions, CI, runtime, hooks, schemas, gates, blockers, or enforcement.

It does not make PR #103 retroactively compliant with the prose gate its final
PR body stated. Its fixed-head technical evidence remains evidence; the missing
pre-merge GitHub approval remains a historical process discrepancy. This
contract governs future solo-owner merge decisions after activation.

M1b and every reader, writer, reconciliation, mutation, or enforcement tranche
remain outside this correction and require separate owner authorization.
