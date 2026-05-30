# AGENTS.md - Your Workspace

<!-- governance:memory_authority -->
memory_root: memory/
external_memory_allowed: false
operational_records_must_stay_under_memory_root: true

This folder is home. Treat it that way.

## First Run

If `BOOTSTRAP.md` exists, that's your birth certificate. Follow it, figure out who you are, then delete it. You won't need it again.

## Every Session

Before doing anything else:
1. Read `SOUL.md` ??this is who you are
2. Read `USER.md` ??this is who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
4. **If in MAIN SESSION** (direct chat with your human): Also read `memory/00_long_term.md`

Don't ask permission. Just do it.

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

Format:

`DONE = <one measurable product outcome>`

Do not infer broad project direction as DONE. DONE must be narrow and testable.

### 4. Hard Stop After Done

When DONE is achieved, stop.

Do not add extra telemetry, readiness, qualification, runtime hooks, artifacts, or governance work unless there is an observed failure.

### 5. Result-First Final Report (reporting convention, not a gate)

Final reports should be result-first, not process-first.

Use this format:

1. Result: Done / Not done
2. Capability increased:
3. Changed files:
4. Validation:
5. Governance surface change: none / list
6. Remaining blocker:

### 6. Commit Checkpoint (reporting convention, not a gate)

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

## Memory

You wake up fresh each session. These files are your continuity:
- **Daily notes:** `memory/YYYY-MM-DD.md` (create `memory/` if needed) ??raw logs of what happened
- **Long-term:** `memory/00_long_term.md` ??your curated memories, like a human's long-term memory

Capture what matters. Decisions, context, things to remember. Skip the secrets unless asked to keep them.

### Cross-Agent Memory Channel (Authoritative In-Repo Path)
- Shared memory for all agents in this workspace must live under this repo's `memory/` directory.
- `memory/00_long_term.md` is the canonical long-term cross-agent memory file for main sessions.
- External/private tool memory paths (for example `C:\Users\reiko\.claude\projects\...\memory\MEMORY.md`) are **not** cross-agent authority and must not be cited as repo governance state.
- If important context exists only in an external/private memory file, copy a distilled version into `memory/YYYY-MM-DD.md` and/or `memory/00_long_term.md` before using it for repo decisions.

### ?? memory/00_long_term.md - Your Long-Term Memory
- **ONLY load in main session** (direct chats with your human)
- **DO NOT load in shared contexts** (Discord, group chats, sessions with other people)
- This is for **security** ??contains personal context that shouldn't leak to strangers
- You can **read, edit, and update** memory/00_long_term.md freely in main sessions
- Write significant events, thoughts, decisions, opinions, lessons learned
- This is your curated memory ??the distilled essence, not raw logs
- Over time, review your daily files and update memory/00_long_term.md with what's worth keeping

### ?? Write It Down - No "Mental Notes"!
- **Memory is limited** ??if you want to remember something, WRITE IT TO A FILE
- "Mental notes" don't survive session restarts. Files do.
- When someone says "remember this" ??update `memory/YYYY-MM-DD.md` or relevant file
- When you learn a lesson ??update AGENTS.md, TOOLS.md, or the relevant skill
- When you make a mistake ??document it so future-you doesn't repeat it
- **Text > Brain** ??

### Canonical Memory Writer Rule (MANDATORY)

**Any entry claiming `memory_type: session-derived` MUST be written via `governance_tools.memory_record`, not by direct markdown append.**

- Canonical path (required for session-derived entries):
  ```
  python governance_tools/memory_record.py \
    --what-changed "..." \
    --commit <git-sha> \
    --session-id <claude-session-id> \
    --test-evidence "..." \
    --next-step "..." \
    --project-root .
  ```
- Manual / AI direct markdown append is allowed, but **MUST NOT include `memory_type: session-derived`**. Use plain `- what_changed:` format instead.
- `session_id` = the Claude Code session UUID (visible in receipt artifacts under `artifacts/runtime/closeout-receipts/`).
- Violation: `non_canonical_writer` warning in `memory_authority_guard`. 76 historical violations exist pre-2026-05-30; do not backfill. Prevent new ones going forward.

### Post-Push Memory Protocol (Cross-Repo)
- After every push in a main session, append one short entry to `memory/YYYY-MM-DD.md`
- Keep the entry compact and structured: `what changed`, `commit hash`, `test evidence`, `next step`
- Use plain `- what_changed:` format (not `memory_type: session-derived`) unless writing via `memory_record` CLI.
- If the push introduced a durable workflow preference, also update `memory/00_long_term.md`
- This protocol is portable: apply the same pattern in other repos with a local `memory/` directory

### PLAN Sync Protocol (Cross-Repo)
- `PLAN.md` is mandatory governance state, not optional project notes.
- After each phase completion or milestone transition:
  1. update `PLAN.md` phase status / next milestone
  2. update memory files
  3. commit and push
- `PLAN.md` drift is treated as governance drift.

### Definition Of Done (Implementation Session)
- A change is done when:
  1. session done-condition is met (defined in first 5 messages)
  2. changes are committed and pushed
  3. one compact line is appended to `memory/YYYY-MM-DD.md` (`what changed`, `what's next`)
- `PLAN.md` sync and structured memory refresh are required only when a phase/milestone transition happened.

### Cross-Agent Closeout Rule (Scope-Split)
- Framework repo (`ai-governance-framework`): strict mode. Details live in `governance/AGENT.md`.
- Consuming repos: minimal mode by default (`done-condition met -> commit/push -> one memory line`).
- Strict closeout (receipt/compliance enforcement) is opt-in for consuming repos.
- Canonical tools remain:
  - `python -m governance_tools.session_closeout_entry --project-root .`
  - `python -m governance_tools.manage_agent_closeout`

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

