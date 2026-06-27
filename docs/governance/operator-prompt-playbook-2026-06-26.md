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

## Sub-Agent Review Receipt Workflow

Use this workflow when the main thread wants skeptical read-only review without
handing over action authority.

Boundary:

```text
Main owns action.
Sub-agent owns skepticism.
Receipt returns evidence.
Main spot-checks key evidence.
Push, commit, memory writes, and authority changes still require main-thread
decision plus user authorization where applicable.
```

Mechanism:

- spawn the review sub-agent with `multi_agent_v1.spawn_agent`;
- wait for its receipt with `multi_agent_v1.wait_agent`;
- continue or correct the same sub-agent with `multi_agent_v1.send_input`;
- close the sub-agent with `multi_agent_v1.close_agent` when done;
- use sidebar thread tools only when a user-visible separate thread is desired,
  not as the default receipt-callback mechanism.

Decision rule:

- Do not open an ordinary separate ChatGPT conversation and ask the user to
  copy the result back. That loses context, invites copy errors, and breaks the
  claim chain.
- Prefer a right-side Codex sub-thread / sub-agent when the user wants visible
  parallel review. The main thread sends the bounded task, reads or awaits the
  receipt, integrates the result, and decides the next step.
- Treat polling as tool-level waiting/reading by the main thread, not as manual
  user polling. The user should not have to shuttle reviewer text back into the
  main thread during normal operation.
- The sub-thread may run checks and return `REVIEW_RECEIPT`, but it must not
  own final action authority. It can say `APPROVED_FOR_PUSH_GATE`; the main
  thread still waits for explicit user authorization before push.

When the user explicitly asks for a separate Codex thread:

- main thread creates the bounded reviewer thread;
- reviewer thread returns `REVIEW_RECEIPT` only;
- main thread reads the reviewer result with `codex_app.read_thread`;
- main thread sends follow-up fixes back with `codex_app.send_message_to_thread`
  when a second review pass is needed;
- user copy/paste of the reviewer result is a fallback only, not the normal
  workflow;
- main thread must not commit, push, write memory, or upgrade claims until it
  has pulled the receipt itself and made the final gate decision.

Use this prompt shape for a read-only sub-agent:

```text
Read-only sub-agent task. Do not modify files, stage, commit, or push.

Task: review <artifact/diff/commit pair/state>.
Return ONLY this receipt:

REVIEW_RECEIPT
verdict: APPROVED | CHANGES_REQUESTED | ESCALATED
blocking_findings:
warnings:
suggestions:
evidence_checked:
claim_ceiling:
cannot_claim:
push_gate: allowed | not_allowed | not_applicable
next_recommended_action:
```

`evidence_checked` must contain actual commands with results, file/line
references, or artifact paths. It must not be a bare `checked=yes` or a list of
intentions. The main thread re-checks load-bearing evidence before any sensitive
action.

Treat a sub-agent `APPROVED` verdict as evidence to inspect, not as authority.
The main thread decides whether to fix, commit, write memory, request push
authorization, or stop.

## Cross-Repo Write Boundary

Use this boundary when a task runs in a workspace that exposes more than one
repository or writable root.

Rule:

```text
Writable root is capability, not authorization.
Active repo owns the write scope.
All other repos are read-only unless explicitly authorized by path.
```

Implementation slices must name `active_repo` before file edits begin. If the
user says `continue`, `keep going`, Chinese continuation equivalents, or
similar continuation wording, that authority applies only inside the already
approved active repo and scope.
It does not authorize writing to another repo, even if that repo is visible,
related to the subject matter, or writable by the tool.

Portable patches, design notes, and implementation packages default to staying
in the source repo that produced them. Applying a portable patch to a target
repo is a separate cross-repo write and requires explicit user wording naming
the target path.

Before any cross-repo write, stop and ask unless the user already gave an
explicit path-level instruction such as:

```text
Apply this patch to D:\ai-governance-framework.
Modify D:\Enumd-private-vault only.
Do not touch any other repo.
```

If an unintended cross-repo write is discovered:

- stop immediately;
- report the active repo, touched repo, and touched paths;
- do not inspect, stage, commit, delete, or repair the out-of-scope files
  unless the user explicitly authorizes that cleanup scope;
- resume only inside the user-approved repo boundary.

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
- If a sub-agent receipt is treated as authority, the workflow only moves
  overclaim risk from the main thread to the sub-agent.
- If `evidence_checked` lacks concrete commands or file references, the main
  thread has nothing meaningful to spot-check.
- If writable roots are treated as user intent, an agent can silently turn a
  source-repo design package into an unauthorized target-repo write.

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
