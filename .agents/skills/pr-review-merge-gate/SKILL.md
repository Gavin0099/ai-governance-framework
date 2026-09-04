---
name: pr-review-merge-gate
description: Open or review a tightly scoped pull request, disposition findings against a frozen owner decision, and merge only when the exact current HEAD has no unresolved current-decision BLOCKING finding and the appropriate engineering or qualification gate passes. Use when the user explicitly authorizes PR review followed by conditional merge; do not use for review-only requests or when merge authorization is absent.
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

- `severity`: `P0` | `P1` | `P2` | `P3`;
- `attribution`: introduced | worsened | exposed | pre-existing;
- `treatment`: `BLOCKING` | `WARNING` | `SUGGESTION` for the frozen decision;
- `disposition`: fix now | bounded workaround | carried-forward | separate work.

Attribution does not decide treatment. A pre-existing problem is still
`BLOCKING` when the PR executes or relies on the path, increases exposure,
interacts with it materially, or relies on evidence it invalidates.

Severity also does not decide treatment. Preserve a real `P1` as `P1` when it is
non-blocking for this decision; give it an evidence-supported carried-forward or
separate-work disposition instead of silently downgrading or fixing unrelated
scope.

Treat a finding as `BLOCKING` when it:

1. is introduced or worsened by the PR at `P0` or `P1` severity;
2. invalidates the frozen DONE or claim ceiling;
3. affects a path the PR enters, relies on, or materially exposes;
4. invalidates merge safety, relied-upon evidence or identity, or an irreversible
   state transition.

A workaround removes blocking applicability only when the applicable owner or
governing authority accepts it and it is deterministic, bounded, replayable,
fail-closed, claim-preserving, and already available as reviewable evidence. An
operator's future intention is not a workaround.

## Remediate and Re-Review

Fix current-decision `BLOCKING` findings within scope, normally batching one
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

1. no unresolved finding has `BLOCKING` treatment for the frozen merge decision;
2. required scope-matched checks pass and mergeability is acceptable;
3. the PR body matches current evidence, scope, and claims;
4. no unrelated files are included;
5. remaining real findings have evidence-supported owner-visible dispositions;
6. merge authorization still applies to the exact head and base.

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

Do not use a finding's treatment at one boundary as its treatment at another.
Gate 3 workarounds must also be precommitted, arm-symmetric,
secret-independent, outcome-independent, Attempt-accounting preserving, and
replayable. Never weaken an existing preregistered or frozen requirement through
this workflow.

Qualification remains reusable across unrelated ancestry movement only when
bound implementation bytes, relevant transitive dependencies, shared semantic
helpers, and qualification assumptions remain unchanged.

## Complete the Gate

Merge only through the repository's normal method and only under current owner
authorization. Then verify the resulting main state or required post-merge
checks. Keep commit, push, PR, review, merge, qualification, deployment, and
cross-machine skill installation as separate evidence claims.

Report the PR URL, reviewed head, checks, gate type, merge result, post-merge
verification, and every carried-forward finding. One passing PR never authorizes
another repository's PR.
