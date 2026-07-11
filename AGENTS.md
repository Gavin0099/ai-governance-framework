# AGENTS.md - Your Workspace

<!-- governance:memory_authority -->
memory_root: memory/
external_memory_allowed: false
operational_records_must_stay_under_memory_root: true

This folder is home. Treat it that way.

## Every Session

Before doing anything else:
1. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
2. **If in MAIN SESSION** (direct chat with your human): Also read `memory/00_long_term.md`

Don't ask permission. Just do it.

## Conditional Governance Routers

Before acting, load the detailed protocol only when its trigger applies:

1. Memory write / post-push memory / memory correction:
   read `governance/MEMORY_PROTOCOL.md`.
   Run `python -m governance_tools.memory_workflow --check` before claiming
   completion for any task that edits, backfills, analyzes, or reports repo
   memory.
   New session-derived memory must use `governance_tools.memory_record`.
   Direct markdown append is prohibited.

2. Final report / closeout:
   read `governance/RESPONSE_ENVELOPE_CONTRACT.md`.
   Use result-first reporting and do not omit Cannot claim / not_claimed.
   When surfacing machine / guard field tokens, pair each with a one-line
   plain-language meaning; keep the field, add the gloss.

3. Review / assess / audit / recommend next changes:
   read `governance/REVIEW_CRITERIA.md`.

4. AI Governance check/update request:
   read `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`.
   Do not treat instruction-file sync as framework update verification.

5. F-7 full update request:
   read `governance/F7_FULL_UPDATE.md`.
   A submodule pointer update alone is not a full F-7 update.

6. Governance-sensitive file changes:
   if changes touch `contract.yaml`, `governance/RULE_REGISTRY.md`,
   `governance/AGENT.md`, `runtime_hooks/**`, `governance_tools/**`,
   `schemas/**`, `.github/workflows/**`, `fleet/**`, or memory writer /
   closeout / gate policy files, read `governance/GOVERNANCE_SURFACE_RULES.md`.

These routers are trigger rules. The detailed files are the authority for the
corresponding protocol.

## Review Tasks

When asked to **review, assess, audit, or recommend next changes** for this repository,
first read `governance/REVIEW_CRITERIA.md` before producing findings.

`REVIEW_CRITERIA.md` defines which additional governance documents are required
(e.g. `TESTING.md`, `ARCHITECTURE.md`, `memory/03_knowledge_base.md`) and under what conditions.
Do not produce review findings before reading it.

## Delivery Recovery Constraints

These constraints apply to implementation sessions in this repository and in consuming repositories using this governance framework. Their purpose is to prevent governance work from displacing product delivery.

### 1. Vertical Slice First

Before expanding governance surface, complete one usable end-to-end product slice.

Examples:
- `scan -> select -> execute -> result`
- `launch -> interact -> complete -> recover`

No governance expansion before the vertical slice is usable unless triggered by an observed failure.

### 2. Failure-Driven Governance Only

New governance surface is allowed only after an observed failure.

Valid triggers:
- unsafe behavior
- irreversible failure
- false-positive / false-negative
- authority escalation
- replay inconsistency
- production ambiguity

Invalid triggers:
- future extensibility
- theoretical completeness
- semantic elegance
- might be useful later

### 3. Session Done Definition Required

Every implementation session must have a concrete DONE condition before file edits begin.

If the user provides DONE, use it directly.
If the user does not provide DONE, propose one measurable product outcome and wait for confirmation.
If the user gives an explicit bounded execution directive (for example: "proceed", "continue", "do not add features, only converge"), treat that as execution authorization within the stated boundary and do not ask for redundant confirmation.
Ask again only when scope expands, enforcement semantics change, schema/runtime behavior changes, or irreversible/destructive risk is introduced.

#### Ambiguous Continuation Is Audit-First

Ambiguous continuation commands are not bounded execution directives by themselves.

Examples include:

- continue
- proceed
- keep going
- 繼續
- 往下做
- 再做下一步

If no next-slice boundary was already approved, the agent must default to audit-first behavior:

- inspect the current state;
- identify the last committed / validated scope;
- propose the next narrow slice;
- list the intended scope, allowed files, non-goals, validation, commit/push intent, and non-claims;
- do not edit files until the user confirms the proposed slice.

If a next-slice boundary was already explicitly approved, the agent may execute that bounded slice without repeating the proposal.

Format:

`DONE = <one measurable product outcome>`

Do not infer broad project direction as DONE. DONE must be narrow and testable.

### 4. Hard Stop After Done

When DONE is achieved, stop.

Do not add extra telemetry, readiness, qualification, runtime hooks, artifacts, or governance work unless there is an observed failure.

Do not automatically continue into: full regression, broad smoke validation, closeout execution, status/rollup updates, unrelated cleanup, commit, push, or inspection of unrelated dirty/untracked files.

If additional work appears useful, report it as next options only.

### 5. Scope-Matched Validation

Validation must match the changed scope. Run targeted validation first.

Do not upgrade to full regression, broad smoke, or closeout unless the DONE definition explicitly requires it or the user explicitly requests it.

Examples: markdown-only changes do not require runtime tests; a single helper change runs its directly related test file; full regression is a release gate, not a default task gate.

### 6. Dirty Tree Allowlist

When the working tree is dirty, produce a concise `git status` summary only.

Do not inspect, read, explain, stage, or modify unrelated dirty or untracked files.

Stage only the explicit allowlist provided by the user or required by the DONE scope.

#### Dirty Work Must Not Be Reported as Overall DONE

If local workspace changes remain after the claimed work, the agent must not report the overall task as DONE.

The agent may only claim DONE for the committed and validated scope.

Required wording pattern:

```text
Committed scope: DONE
Workspace state: NOT CLEAN
Overall task: NOT DONE until dirty work is audited or explicitly excluded
```

This applies when any of the following remain after the claimed work:

- unstaged changes;
- staged but uncommitted changes;
- untracked files;
- generated local diff without commit checkpoint;
- failed or unavailable commit / push tooling;
- auto-review changes that were not committed.

When dirty work exists, the agent must:

- run `git status --short`;
- identify whether dirty files are in the claimed scope, unrelated, or unknown;
- inspect only files in the claimed scope or user-approved allowlist;
- summarize scoped diff only when inspection is allowed;
- run scoped validation only for in-scope changes;
- provide commit-preflight review only if commit is requested.

The agent must not read, stage, summarize, or validate unrelated dirty files unless the user explicitly approves that scope.

### 7. Result-First Final Report (reporting convention, not a gate)

Final reports and closeout must follow
`governance/RESPONSE_ENVELOPE_CONTRACT.md`.

Result-first reporting is required. Event-driven `mode` must be event-derived,
not agent-selected. `mode_source`, `task_authority`, `scope`, `done`,
`not_claimed`, `evidence_refs`, and `risk` must remain separate.

Do not omit Cannot claim / not_claimed. `PASS` must always include a command,
artifact, or source; bare `PASS` is not valid.

### 8. Commit Checkpoint (reporting convention, not a gate)

After each implementation commit, report the following before continuing.
This is an automatic checkpoint — not a mandatory pause.

```
Commit: <hash + one-line summary>
Tests: <pass / fail count, or "not run">
Previously passing signal regression: <none | list what regressed>
Dirty state: <clean | explained — list unrelated dirty files if any>
Claim ceiling: <what was claimed; confirm it stays within DONE scope>
Next recommended step: <one concrete action>
```

If all signals are clear, continue without waiting.
If any signal is unclear or regressed, surface it before proceeding.

## Repo-Specific Risk Levels
<!-- governance:key=risk_levels -->

- HIGH: any change to `governance_tools/session_end_hook.py` — defines REQUIRED_FIELDS, schema validation, evidence admissibility, and gate_blocked detection; wrong logic silently accepts invalid closeouts
- HIGH: any change to `governance_tools/gate_policy.py` — controls fail_mode, block conditions, and artifact_state transitions; weakening gate logic undermines the entire enforcement model
- HIGH: any change to verified / admissible evidence criteria in matrix logic — changing what counts as evidence directly inflates verified ratio without real governance gain
- MEDIUM: any change to `governance_tools/session_closeout_entry.py` — orchestrates the closeout pipeline; regression here can break evidence chain for all consuming repos
- MEDIUM: any change to evidence_tier or scope tier definitions (`governance/fleet/governance_scope.yaml`, `governance/runtime/`) — scope changes affect which repos are required vs recommended
- LOW: documentation, test fixture updates, memory/session artifacts with no governance_tools changes

## Must-Test Paths
<!-- governance:key=must_test_paths -->

- `governance_tools/session_end_hook.py` — any change to REQUIRED_FIELDS, _parse_fields, _check_schema, or _check_content requires tests covering valid/invalid/missing-field cases
- `governance_tools/gate_policy.py` — any change to block/pass conditions requires tests verifying fail-open and fail-closed paths
- `governance_tools/session_closeout_entry.py` — changes require smoke test confirming receipt generation with correct linked_head_commit
- `governance_tools/framework_versioning.py` — load_framework_lock and assess_framework_version_status changes require tests for lock-missing, version-mismatch, and canonical-source cases
- `tests/test_agent_closeout_receipt.py` — must remain green before any merge touching session_end_hook or session_closeout_entry

## L1 → L2 Escalation Triggers
<!-- governance:key=escalation_triggers -->

- Any change to what constitutes admissible evidence (gate_blocked logic, receipt schema, cross-reference rules) — requires explicit evidence that no currently-verified repo would be retroactively de-verified
- Any change to the `repo_native_verified` classification criteria in the matrix — requires full fleet re-run and comparison against prior snapshot
- Any change to scope tier definitions (required / recommended / exempt) — requires human approval; scope changes can shift the verified ratio denominator without repo changes
- Any change simultaneously touching session_end_hook.py, gate_policy.py, and matrix logic — three-path cross-cut needs explicit sign-off that verified count is not being artificially inflated

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->

- Do NOT relax the `verified` definition or admissibility criteria to improve the verified ratio — verified count must reflect genuine governance adoption, not calibrated thresholds
- Do NOT use a `gate_blocked=true` closeout receipt as admissible evidence — this was an observed failure mode already fixed; reverting is forbidden
- Do NOT treat a closeout receipt as proof of framework correctness — receipts prove evidence chain integrity, not that the governance model is correct
- Do NOT mix schema changes with repo onboarding commits — schema and evidence contract changes must be separate commits with explicit justification
- Do NOT let `self_reference_note` in framework.lock.json be removed — it exists to prevent semantic drift where self-verification is misread as framework correctness proof

## Workspace vs Repo Governance

This file defines workspace behavior, memory habits, safety posture, and how to
operate in this environment.

For repo-local engineering governance such as `L0/L1/L2` classification,
execution rigor, architecture gates, and testing expectations, the canonical
source is `governance/AGENT.md` together with the other files under
`governance/`.

If this file and `governance/AGENT.md` appear to overlap:
- use this file for session/workspace behavior
- use `governance/AGENT.md` for repo engineering governance
- if editor/adapter/workspace instructions conflict with repo-local governance on execution rigor, risk gates, or task classification, `governance/` wins for repo work and the mismatch should be corrected instead of silently improvised

### Persistent User Preference Precedence

Repo-local instructions may define task execution, validation, memory, and
governance behavior for this repository. They must not silently override durable
user preferences or tool-level permanent instructions when those preferences do
not conflict with repo safety or correctness.

If a repo instruction conflicts with a durable user preference, the agent must
surface the conflict and state which instruction is being followed and why.

Repo governance may override a durable user preference only for:
- safety;
- destructive operation prevention;
- validation, evidence, or claim-boundary requirements;
- commit / push discipline;
- repository-specific correctness boundaries.

Repo governance must not override a durable user preference for:
- language preference;
- communication style;
- response verbosity;
- non-conflicting workflow preferences;
- personal naming or formatting preferences.

When uncertain, report:

```text
Instruction conflict detected: <repo instruction> vs <persistent user preference>.
Following <source> because <reason>.
```

## Nested Repo / Submodule Rule

When this repository is opened inside another repository as a nested checkout or
submodule:
- treat this repository root as a separate workspace, not as an extension of the parent repo
- confirm the current repo root before reading or updating `memory/`, `artifacts/`, `PLAN.md`, or `governance/`
- do not mix this repo's `memory/` files with the parent repo's `memory/` files
- do not write review notes, active-task updates, or governance artifacts into the wrong repo just because both repos expose similarly named paths
- when reporting findings, name which repo owns the file and which repo owns the decision

If the parent repo wants to consume this framework through a submodule, treat
submodule pointer updates as parent-repo decisions. Do not silently assume that
advancing the framework checkout also updates the parent repo's intended pinned
version.

### AI Governance Update Trigger

When the user asks to check or update AI Governance, read
`governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` before acting.

Do not treat `AGENTS.md`, `AGENTS.base.md`, local instruction-file sync, parent
repo `git pull`, or a clean parent working tree as proof that the AI Governance
Framework is current.

When updating AI Governance for a consuming repository, prefer the governed
updater/F-7 path. A direct submodule/gitlink checkout, framework checkout bump,
or lock-file edit is a `manual_update` path and must be reported as incomplete
unless the governed updater/F-7 evidence is also produced.

This workspace section is a trigger summary, not the canonical definition of
`manual_update` or `destructive_manual_update`. The canonical reporting
vocabulary and templates live in `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`;
F-7 and consumer AGENTS baselines only project that vocabulary into their active
execution surfaces.

Before discarding local state in a nested framework checkout, first inspect the
modified and untracked paths that would be discarded. If cleanup proceeds, the
final report must list that discarded-path inventory and use
`destructive_manual_update`; do not summarize it only as "cleaned the
submodule".

### F-7 Full Update Trigger

When the user asks for F-7 or full AI Governance update, read
`governance/F7_FULL_UPDATE.md`.

A submodule pointer update alone is not a full F-7 update and must not be
reported as `full_update_completed`.

## Memory

Before writing memory, post-push memory, corrective memory, PLAN sync entries,
or closeout memory, read `governance/MEMORY_PROTOCOL.md`.

All new session-derived memory entries must use `governance_tools.memory_record`.
Direct markdown append in `- what changed:` or `- what_changed:` format is
prohibited.

Memory `next_step` is evidence of a prior candidate continuation, not current
authorization. Current user instruction, workspace state, dirty-tree status, and
applicable governance rules supersede memory content.

`PLAN.md` remains mandatory governance state. Update PLAN and memory after phase
or milestone transitions according to `governance/MEMORY_PROTOCOL.md`.

## Safety

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- `trash` > `rm` (recoverable beats gone forever)
- When in doubt, ask.

## External vs Internal

**Safe to do freely:**
- Read files, explore, organize, learn
- Search the web, check calendars
- Work within this workspace

**Ask first:**
- Sending emails, tweets, public posts
- Anything that leaves the machine
- Anything you're uncertain about

## Companion / Chat Operations

Non-repo companion behavior (group chat etiquette, heartbeat routine, social formatting, voice storytelling) is intentionally moved out of this file to reduce implementation-session noise.

See `TOOLS.md` for companion and chat operation guidance.

## Make It Yours

This is a starting point. Add your own conventions, style, and rules as you figure out what works.

