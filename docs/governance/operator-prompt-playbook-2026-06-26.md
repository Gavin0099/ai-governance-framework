# Operator Prompt Playbook - 2026-06-26

Status: proposal/design-only
Scope: user/operator quick-reference
Runtime behavior change: no
Tooling behavior change: no
Governance authority change: no
Enforcement change: no

## Problem

The most reliable recent workflow in this repository has not been a larger
governance surface. It has been a smaller operator habit:

1. name the task mode;
2. define one measurable `DONE`;
3. keep scope and non-goals explicit;
4. validate only the changed surface;
5. review separately;
6. push only after explicit authorization.

When those fields are missing, ambiguous continuation phrases such as
`continue`, `proceed`, `keep going`, `go next`, or equivalent short
continuation commands can cause the agent to infer the next slice too broadly.
This playbook records prompt snippets that keep the operator and agent aligned
before work starts.

This is not a new governance rule. It is a lightweight way to trigger the rules
that already exist.

## Current Repository Truth

Observed repository rules and surfaces relevant to this playbook:

- `AGENTS.md` requires ambiguous continuation to be audit-first unless a narrow
  next-slice boundary was already approved.
- `AGENTS.md` requires a concrete `DONE = <one measurable product outcome>`
  before implementation edits begin unless the user has already provided one.
- `governance/REVIEW_CRITERIA.md` defines review as skeptical verification with
  evidence-bound findings.
- `governance/RESPONSE_ENVELOPE_CONTRACT.md` keeps result, claim ceiling,
  non-claims, evidence, risk, and next action separate in final reports.
- `governance/MEMORY_PROTOCOL.md` requires canonical writer use for
  session-derived repository memory.
- Recent adoption work showed that documentation-only reminders are weak when
  they are not in the active execution path. Therefore this playbook is most
  useful as text pasted into the prompt, not as an authority layer.

## Target Outcome

Provide short, reusable prompt templates for this repository's common task
modes:

- implementation;
- read-only review;
- diagnosis only;
- proposal/design-only;
- push/verify.

The target outcome is less scope ambiguity, not more enforcement.

## Scope

This playbook covers:

- task-mode labels;
- a reusable task header;
- per-mode prompt snippets;
- repository startup checklist prompts;
- claim-ceiling snippets;
- sequencing reminders for review, memory, commit, and push.

## Non-Goals

This playbook does not:

- change `AGENTS.md`;
- change governance routers;
- change memory protocol;
- change runtime hooks;
- change tooling behavior;
- add CI, pre-push, gate, or enforcement behavior;
- require agents to read this file automatically;
- make any prompt template authoritative by itself;
- prove that future agents will follow the snippets.

## Affected Surfaces

Directly affected by this proposal:

- `docs/governance/operator-prompt-playbook-2026-06-26.md`

Not affected:

- `AGENTS.md`
- `governance/*.md` routers
- `governance_tools/**`
- `runtime_hooks/**`
- schemas
- hooks
- CI
- memory writer behavior

## Boundary And API Considerations

This file is an operator aid. It should not be imported by runtime code,
referenced as a canonical governance router, or treated as an enforcement
contract.

If a future slice wants this content to influence execution, that must be a
separate design and review. This document only records prompt-side usage.

## Standard Task Header

Use this header when starting a non-trivial task:

```text
DONE = <one measurable outcome>
mode = implementation | read-only review | diagnosis only | proposal/design-only | push/verify
scope = <allowed files/repos/surfaces>
non-goals = <what must not change or be claimed>
validation = <focused checks only>
claim ceiling = <what this can safely prove>
commit/push intent = <no commit | commit after review | push only after explicit authorization>
```

For implementation tasks, echo the approved slice before editing:

```text
Executing approved slice:
DONE = <copied DONE>
scope = <copied scope>
non-goals = <copied non-goals>
```

## Mode Templates

### Implementation

Use when the agent should edit files.

```text
DONE = <specific change>; mode = implementation.
scope = <exact files or directory>.
non-goals = no unrelated cleanup, no enforcement change, no runtime behavior
change outside the stated scope, no push.
validation = <focused tests/checks>.
commit intent = do not commit until review | commit source/test after approval.
```

### Read-Only Review

Use when the agent must verify an artifact, diff, commit, or repo state without
changing files.

```text
DONE = review <artifact/commit pair/diff>; mode = read-only review.
Do not modify files, stage, commit, or push.
Verify repo state, scope, diff, memory binding, evidence, claim ceiling, and
non-claims.
Return findings first, then verdict, risk, evidence, cannot-claim, and next-step
judgment.
```

### Diagnosis Only

Use when the agent should inspect state and identify causes, but not repair.

```text
DONE = diagnose <repo/system/state>; mode = diagnosis only.
scope = read-only inspection of <paths/repos>.
non-goals = no repair, no fetch unless explicitly allowed, no commit, no push,
no rewriting local state.
validation = commands or artifacts that support the diagnosis.
claim ceiling = findings and recommended next slice only.
```

### Proposal / Design-Only

Use when the agent should write or review a proposal without implementing it.

```text
DONE = write a design-only proposal for <problem>; mode = proposal/design-only.
scope = one docs file.
non-goals = no code behavior change, no tooling/runtime/hook/CI/enforcement
change, no implementation commitment.
validation = scope check, ASCII/trailing-whitespace check, and review.
claim ceiling = proposed scope and evidence plan only.
```

### Push / Verify

Use only after a commit pair has been reviewed and approved.

```text
DONE = push <commit(s)> to origin/main and gitlab/main, then verify both
remote-tracking heads match <expected head>.
mode = push/verify.
scope = git push/fetch/rev-parse only.
non-goals = no new edits, no commit, no repair.
validation = HEAD, origin/main, and gitlab/main all equal <expected head>.
```

## Repository Startup Checklist Prompts

For governance refresh, pull, or adoption questions, start with diagnosis before
repair:

```text
mode = diagnosis only.
Check repo state before recommending repair:
- git status and branch ahead/behind;
- dirty/conflict state;
- submodule/gitlink state;
- framework lock or framework pin state;
- readiness/onboarding validator relevant to this repo;
- repo-specific validator or smoke path;
- memory or push gate state when memory/push is in scope.
Do not repair, commit, or push until the next slice is explicit.
```

This avoids conflating:

- governance refresh success with parent pull completion;
- framework lock currentness with readiness cleanliness;
- static self-contained evidence with runtime hook execution;
- memory bound status with truth, review, commit, or push.

## Claim-Ceiling Snippets

Use the shortest accurate non-claim phrase.

```text
proposal-only; no behavior changed
docs-only; no runtime/tooling/enforcement change
diagnosis-only; no repair performed
refresh completed; parent pull still not claimed
observation-only; not source commit evidence
memory bound; not truth/review/push proof
static self_contained; runtime_capable not checked
current_vs_local_tracking; true remote currentness not claimed
preview shows candidates only; no delete/apply unless explicitly authorized
LTSSM/link-training only; non-LTSSM remains advisory
no verified uplift; claim ceiling unchanged
```

## Sequencing Pattern

Preferred sequence for governance-sensitive work:

```text
small slice -> focused validation -> read-only review thread -> commit pair
-> review commit pair -> explicit push/verify -> stop
```

Do not continue into the next slice automatically after push. Recommend one
next action, then wait for a new `DONE` unless the next slice was already
explicitly approved.

## Failure Paths Or Risk Points

- If this file is treated as authority, it becomes a new governance surface
  without a real enforcement path.
- If snippets are copied without concrete `scope` and `non-goals`, they become
  decorative text rather than useful task boundaries.
- If `proposal/design-only` is mixed with implementation, review cannot tell
  whether behavior changed.
- If push is bundled with implementation, remote delivery can happen before
  review has verified memory binding and claim ceiling.
- If diagnosis turns into repair, dirty parent repos and submodule pins can be
  changed before ownership is clear.

## Evidence Plan

For this docs-only playbook:

- confirm only this file is added;
- confirm ASCII-only content;
- confirm no trailing whitespace;
- confirm no changes to `AGENTS.md`, governance routers, tooling, hooks, CI, or
  memory protocol.

## Implementation Tranche Recommendation

This file is the full intended tranche.

Next possible action after review is commit plus canonical memory, but only if
the reviewer accepts the claim ceiling:

```text
operator quick-reference only; no governance authority or enforcement change
```
