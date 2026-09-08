---
name: pr-review-merge-gate
description: Open or review a tightly scoped pull request, disposition findings against a frozen owner decision, and merge only when the exact current HEAD has no unresolved finding that blocks that decision and the appropriate engineering or qualification gate passes. Use when the user explicitly authorizes PR review followed by conditional merge; do not use for review-only requests or when merge authorization is absent.
---

# PR Review Merge Gate

Use this workflow only within the user's explicit authority for branch creation,
commit, push, PR creation, Ready transition, and merge. The skill does not supply
any missing authorization.

When the repository provides `governance/REVIEW_CRITERIA.md`, read it and treat
it as the canonical review semantics. This skill is the operational procedure,
not an independent policy source.

## Freeze the Decision

Before review, record:

- the current owner decision;
- the exact DONE condition;
- the claim ceiling;
- the review boundary: changed surface plus necessary semantic blast radius;
- whether this is an Engineering Merge Gate or Qualification Gate.

Do not turn an ordinary merge decision into subsystem qualification.

## Prepare the Pull Request

1. Inspect base, remote, status, requested files, and repository instructions.
   Preserve unrelated modified and untracked files and stage explicit paths only.
2. Keep one independently reviewable capability per PR. Separate unrelated
   outcomes instead of expanding the current decision.
3. Run risk-proportional, scope-matched checks. Expected results must come from
   an independent specification, invariant, fixture, or source of truth.
4. Bind the PR body to its exact scope, evidence, claim ceiling, and current HEAD.
   Do not add artifacts or gates solely to support this workflow.

## Review and Triage Findings

Bind every review to the exact current PR HEAD. Inspect the live body, combined
diff, checks, mergeability, and unresolved threads. A clean diff or passing test
alone is not a review.

For every real finding, report these dimensions separately:

- finding label / severity: preserve the original value and source convention;
- `attribution`: introduced | worsened | exposed | pre-existing;
- current-decision impact: yes | no, with an evidence-backed reason;
- disposition: fix now | workaround | carried-forward | separate work.

Do not migrate severity vocabulary. Existing `BLOCKING`, `WARNING`, and
`SUGGESTION` finding labels remain valid, as do external `P0`-`P3` labels when
already in use. Neither a source label nor attribution determines impact.
A pre-existing problem still blocks when the PR relies on the unsafe path,
increases exposure, interacts with it materially, or relies on evidence it
invalidates. Never downgrade the original label to justify proceeding.

Impact `yes` means the frozen decision cannot proceed while the finding remains
unresolved. Impact `no` requires evidence and a disclosed disposition; it does
not mean the finding is fixed or harmless at another boundary. Escalate unknown
impact instead of treating it as `no`.

Set current-decision impact to `yes` when the finding:

1. is a concrete defect introduced or materially worsened by the PR affecting
   correctness, safety, governance, or the stated claim boundary;
2. invalidates the frozen DONE or claim ceiling;
3. affects an unsafe path the PR enters, relies on, or materially exposes;
4. invalidates merge safety, relied-upon evidence or identity, or an irreversible
   state transition's safety.

A workaround removes blocking applicability only when the applicable owner or
governing authority accepts it and it is deterministic, bounded, replayable,
fail-closed, claim-preserving, and already available as reviewable evidence. An
operator's future intention is not a workaround. Record the accepted evidence
and why impact is now `no`; preserve the finding label and workaround
disposition. `carried-forward` or `separate work` alone cannot clear `yes`.

## Remediate and Re-Review

Fix findings with current-decision impact `yes` within scope, normally batching one
review round before pushing. Require proportionate replayable regression
evidence. Stop for owner direction when remediation changes architecture,
expands the capability, crosses repositories, changes authority, or creates an
irreversible risk.

After a fix, prior approval is stale. Review the new exact HEAD, prioritizing:

1. whether prior blockers are resolved;
2. whether the correction delta introduces or worsens a blocker;
3. necessary adjacent paths affected by the correction's semantic blast radius.

Do not reopen unrelated subsystem qualification unless the claim ceiling
expanded, a shared semantic choke point changed, or new evidence proves that the
prior boundary was incomplete.

For specification PRs, defer concerns about nonexistent future paths unless they
contradict the current DONE, make the next authorized implementation unsafe or
unimplementable, or freeze an incorrect public contract.

## Select the Gate

Use the Engineering Merge Gate for ordinary capability PRs. The exact current
HEAD is merge-ready only when:

1. no unresolved finding has current-decision impact `yes`, and no impact
   assessment remains unknown for the frozen merge decision;
2. required scope-matched checks pass and mergeability is acceptable;
3. the PR body matches current evidence, scope, and claims;
4. no unrelated files are included;
5. remaining real findings have evidence-supported owner-visible dispositions;
6. merge authorization still applies to the exact head and base;
7. every predicate of the applicable repository merge-authority contract is
   satisfied. Load that contract before assessing merge readiness; this list
   cannot replace or weaken its requirements.

When the repository operates under its
`governance/SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md`, verify all four predicates
for the same exact candidate HEAD:

- `owner_merge_attestation=recorded_for_exact_head`;
- `independent_technical_review=independent_approved_for_exact_head`;
- `required_checks=green_for_exact_head`;
- `head_state=matches_reviewed_head`.

Any missing, unknown, stale, failing, or non-independent required predicate
makes the candidate ineligible. A review performed by the implementation
authoring process cannot satisfy the independent-review predicate, even when
it finds no current-decision blocker and CI is green. Record the independent
reviewer's identity, exact target, evidence, and verdict. A GitHub `APPROVED`
review is optional additional evidence under this contract, not a substitute
for any missing predicate.

Use the Qualification Gate only for a formal POC pass, qualification, GO, or
equivalent admission claim. Add the applicable golden set, threshold,
independent review, environment identities, durable receipt, and replay evidence.
Never promote an Engineering Merge Gate result into qualification.

## Gate 3 Boundaries

For Gate 3, freeze and review four decisions independently:

1. Engineering Merge;
2. Bootstrap Readiness;
3. Execution Authorization;
4. Evidence / Result Acceptance.

Assess current-decision impact separately at each boundary. Impact `no` at
Engineering Merge does not grant execution authority or result acceptance.
Gate 3 workarounds must also be precommitted, arm-symmetric,
secret-independent, outcome-independent, Attempt-accounting preserving, and
replayable. Never weaken an existing preregistered or frozen requirement through
this workflow.

Unrelated ancestry movement alone need not invalidate qualification when bound
implementation bytes, relevant transitive dependencies, shared semantic helpers,
qualification assumptions, and explicit head/ancestry bindings remain satisfied.
Revalidate affected evidence when any of those changes. Never discard a frozen
binding to preserve a prior qualification result.

## Complete the Gate

Merge only through the repository's normal method and only under current owner
authorization. Then verify the resulting main state or required post-merge
checks. Keep commit, push, PR, review, merge, qualification, deployment, and
cross-machine skill installation as separate evidence claims.

Report the PR URL, reviewed head, checks, gate type, merge result, post-merge
verification, and every carried-forward finding. One passing PR never authorizes
another repository's PR.
