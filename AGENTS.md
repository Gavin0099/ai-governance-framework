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

Final reports should be result-first, not process-first.

Event-driven response envelope:
- When using a `mode` field, follow `governance/RESPONSE_ENVELOPE_CONTRACT.md`.
- `mode` must be event-derived, not agent-selected.
- `mode_source`, `task_authority`, `scope`, `done`, `not_claimed`, `evidence_refs`, and `risk` must remain separate fields.
- `task_authority` distinguishes authorized work from autonomous expansion.
- `evidence_refs` records commands, artifacts, or reviewer sources supporting the DONE claim; it does not upgrade semantic authority.
- Do not replace claim ceiling or risk disclosure with confidence scores, effort estimates, or broad impact analysis.

Vocabulary:
- `NOT PRESENT` = the mechanism, artifact, or enforcement does not exist
- `NOT CLAIMED` = the capability or conclusion is not being asserted this session
- `PASS` = must always include `— <command or source>`; bare `PASS` is not valid

**Language rule:** Content language must match the session language. Sub-field labels (`structural`, `build`, `semantic`, `behavioral`, `ext evidence`, `scope drift`, `claim inflation`, `evidence maturity`) and fixed vocabulary tokens (`PASS`, `FAIL`, `NOT RUN`, `NOT CLAIMED`, `NOT PRESENT`) remain in English. Section headers (Result / Validation / Risk / Cannot claim) may be translated.

Use this format (English session):

1. Result: Done / Not done
2. Capability increased:
3. Changed files:
4. Validation:
   - structural:    PASS — <command> | FAIL — <command> | NOT RUN
   - build:         PASS — <command> | FAIL — <command> | NOT RUN
   - semantic:      NOT CLAIMED | PASS — human review: [reviewer/date]
   - behavioral:    NOT PRESENT | verified — [how]
   - ext evidence:  NOT PRESENT | [source and scope]
5. Risk:
   - scope drift:        none | [description]
   - claim inflation:    none | [description]
   - evidence maturity:  [one line]
6. Incidental cleanup:   none | file=[path] reason=[why] semantic_change=no
7. Governance surface change: none / list
8. Remaining blocker:
9. Cannot claim this session:
   - [list what was NOT validated, NOT verified, NOT proven — required, never omit]

Chinese session format:

1. 結果：完成 / 未完成
2. 能力提升：
3. 變更檔案：
4. 驗證：
   - structural:    PASS — <指令> | FAIL — <指令> | NOT RUN
   - build:         PASS — <指令> | FAIL — <指令> | NOT RUN
   - semantic:      NOT CLAIMED | PASS — 人工審查：[審查者/日期]
   - behavioral:    NOT PRESENT | 已驗證 — [如何]
   - ext evidence:  NOT PRESENT | [來源與範圍]
5. 風險：
   - scope drift:        none | [說明]
   - claim inflation:    none | [說明]
   - evidence maturity:  [一行說明]
6. 附帶清理：   none | file=[路徑] reason=[原因] semantic_change=no
7. Governance surface 變更：none / 列舉
8. 剩餘阻擋：
9. 本次無法宣告：
   - [列出未驗證、未確認、未證明的項目 — 必填，不得省略]

Golden examples:

**Schema-only change (markdown, no runtime):**
```
1. Result: Done
2. Capability increased: section_refs schema extended
3. Changed files: wiki/port-status.md
4. Validation:
   - structural:    PASS — grep section_refs wiki/port-status.md
   - build:         NOT RUN — markdown-only change
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none
   - claim inflation:    none
   - evidence maturity:  structural layer only; no semantic verification
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     none
9. Cannot claim this session:
   - semantic correctness of section references
   - PDF-level content verification
```

**Pilot attachment change (build pass, no semantic verification):**
```
1. Result: Done
2. Capability increased: 4 port entries have section_refs attached
3. Changed files: wiki/port-status.md, wiki/zh/port-status.md
4. Validation:
   - structural:    PASS — validate_wiki_frontmatter (exit 0)
   - build:         PASS — npm run build (exit 0)
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none — pilot limited to 4 existing entries
   - claim inflation:    none — claim_level unchanged (inferred)
   - evidence maturity:  build-verified only; high-risk coverage below original plan
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     PORT_OVER_CURRENT not in pilot — high-risk coverage gap
9. Cannot claim this session:
   - bit-level semantic verification of attached spec sections
   - high-risk boundary condition coverage (PORT_OVER_CURRENT not in pilot)
   - verified status upgrade
```

**Failed / partial validation:**
```
1. Result: Not done — build failed
2. Capability increased: none
3. Changed files: wiki/port-status.md (uncommitted)
4. Validation:
   - structural:    PASS — validate_wiki_frontmatter (exit 0)
   - build:         FAIL — npm run build (exit 1, error above)
   - semantic:      NOT CLAIMED
   - behavioral:    NOT PRESENT
   - ext evidence:  NOT PRESENT
5. Risk:
   - scope drift:        none
   - claim inflation:    none — task not complete
   - evidence maturity:  build failure; no completion evidence
6. Incidental cleanup:   none
7. Governance surface change: none
8. Remaining blocker:     build error must be resolved before commit
9. Cannot claim this session:
   - task complete
   - any validation above build layer
```

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

### AI Governance Update Intent Rule

When the user asks to "Update AI Governance to latest" or 「把 AI Governance
更新到最新」, do not interpret this as checking whether `AGENTS.md`,
`AGENTS.base.md`, or local governance instruction files are clean.

First determine whether the repository consumes AI Governance through a
submodule path such as:
- `ai-governance-framework`
- `.ai-governance-framework`

If a governance submodule exists, the request maps to the governed submodule
update workflow. The agent must compare the nested governance HEAD with the
approved target upstream HEAD, preferably through the governed submodule updater
dry-run path.

The agent must not claim AI Governance is already current based only on:
- `AGENTS.md` unchanged
- `AGENTS.base.md` unchanged
- parent repository `HEAD == origin/main`
- `git pull --ff-only` reporting already up to date
- clean parent repository working tree

A valid `already_current` conclusion for a submodule consumer must include:
- governance submodule path
- nested governance HEAD
- target upstream framework HEAD
- dry-run update result

Required response shape:

```text
AI Governance update check: <already_current | update_available | updated | not_submodule_consumer | not_verified>
governance submodule path: <path | NOT FOUND | NOT CHECKED>
nested governance HEAD: <sha | NOT CHECKED>
target framework HEAD: <sha | NOT CHECKED>
dry-run: PASS | FAIL | NOT RUN
update mode: already_current | fast_forward | detached_target_checkout | NOT CLAIMED
parent repo commit: <hash | NOT NEEDED | NOT CREATED>
```

If the session only updates `AGENTS.md` or other local instruction files, report
that as an instruction-file update and mark the AI Governance Framework update
as `not_verified`. Do not collapse instruction-file sync into framework update
status.

Invalid conclusion:

```text
AGENTS.md was updated and the parent repo is up to date, so AI Governance is current.
```

Valid partial conclusion:

```text
AGENTS.md was updated, but the AI Governance Framework submodule was not checked.
AI Governance update check: not_verified
governance submodule path: NOT CHECKED
nested governance HEAD: NOT CHECKED
target framework HEAD: NOT CHECKED
dry-run: NOT RUN
update mode: NOT CLAIMED
parent repo commit: NOT CREATED
```

### AI Governance Check Vs Update Intent

Classify the user's wording before acting:

`check` intent examples:
- "檢查 AI Governance 是否最新"
- "確認 AI Governance 有沒有更新"
- "verify AI Governance version"
- "check whether AI Governance is up to date"

Action: verify-only. Do not update the submodule pointer.

`update` intent examples:
- "幫我更新最新版 AI Governance"
- "把 AI Governance 更新到最新"
- "更新 AI Governance 到最新版"
- "Update AI Governance to latest"

Action: perform the governed update flow for a submodule consumer: detect the
governance submodule path, run dry-run, then apply the scoped submodule pointer
update if dry-run is safe and no blocker exists.

For `update` intent, do not stop after direct HEAD comparison when nested
governance HEAD differs from target framework HEAD. A direct HEAD comparison may
establish `update_available`, but it is not a completed update.

If the repository is a submodule consumer and no blocker exists, the agent must
continue from `update_available` to the governed update step.

The agent must not ask "要不要我幫你更新？" after the user has already used
update wording. Ask only when the user intent is ambiguous or when a blocker
requires user decision.

AI Governance update status must use one of these fixed values only:

- `already_current`: nested governance HEAD already matches the target framework HEAD.
- `update_available`: nested governance HEAD differs from the target framework HEAD, but update has not yet been applied.
- `updated`: governed update flow completed and nested governance HEAD now matches the target framework HEAD.
- `blocked`: update could not proceed due to dirty worktree, staged changes, dirty nested submodule, dry-run failure, missing path, or other explicit blocker.
- `not_submodule_consumer`: repository does not consume AI Governance through a submodule.
- `not_verified`: the agent could not safely determine current or target governance state.

For update intent, `update_available` is an intermediate state, not a final
successful outcome. Final response must be one of:
`already_current | updated | blocked | not_submodule_consumer | not_verified`.

Updating the governance submodule pointer does not automatically authorize a
parent repository commit or push unless the user explicitly requested commit/push
or the active workflow already defines commit/push as part of the governed
update task.

If no parent repo commit is created, report:
`parent repo commit: NOT CREATED`.

### F-7 Full Update Semantics

F-7 is the AI Governance Full Update workflow. The governed submodule update is
Stage 1 of F-7, not the whole workflow.

When the user asks to update or adopt the latest AI Governance through F-7, F-7
must execute the full adoption/update workflow or explicitly report a blocker.
A submodule pointer update alone is insufficient and must be reported as
`partially_updated`, not completed.

Required stages:

1. framework pointer update
2. repo-local instruction refresh
3. memory writer coverage check
4. hook / validator coverage check
5. existing memory normalization status check
6. final adoption status report

Layered status fields:

```text
framework_pointer: updated | already_current | blocked | not_present | not_verified
repo_local_instruction: updated | already_current | blocked | missing | not_verified
memory_writer_coverage: verified | updated | blocked | missing | not_applicable | not_verified
hook_validator_enforcement: verified | updated | blocked | missing | not_applicable | not_verified
existing_memory_normalization: completed | needed | blocked | not_applicable | not_verified
final_status: full_update_completed | already_current | partially_updated | blocked | not_submodule_consumer | not_verified
```

`full_update_completed` may be used only when every required stage is
`updated`, `already_current`, `verified`, `completed`, or `not_applicable`.
If any required surface is `missing`, `needed`, `blocked`, or `not_verified`,
the final status must not be `full_update_completed`.

This semantic update defines the required F-7 contract. It does not by itself
implement updater automation for all stages.

NOT CLAIMED unless separately implemented and validated:
- updater automation performs all F-7 stages
- hooks changed
- validators changed
- artifact schema changed
- existing memory was normalized

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
- **All new memory entries MUST use the canonical writer CLI.** Direct markdown append (`- what changed:` or `- what_changed:` format) is PROHIBITED for new entries. The guard flags direct-format entries in files dated >= 2026-05-01 as `old_format_entry_after_canonical_writer_cutoff`.
- `session_id` = the Claude Code session UUID (visible in receipt artifacts under `artifacts/runtime/closeout-receipts/`).
- Violation: `non_canonical_writer` warning in `memory_authority_guard`. 76 historical violations exist pre-2026-05-30; do not backfill. Prevent new ones going forward.

### Post-Push Memory Protocol (Cross-Repo)
- After every push in a main session, append one short entry to `memory/YYYY-MM-DD.md`
- Keep the entry compact and structured: `what changed`, `commit hash`, `test evidence`, `next step`
- Use the canonical writer CLI for all new entries. **Never write `- what changed:` or `- what_changed:` format directly** — this generates `non_canonical_writer` violations in the guard.
- If the push introduced a durable workflow preference, also update `memory/00_long_term.md`
- This protocol is portable: apply the same pattern in other repos with a local `memory/` directory

#### Memory State Trace Consistency

Memory entries must not mix completed and pending state.

`next_step` must describe the next unfinished action, not repeat an action already recorded as completed in the same memory entry.

If a `commit` or `commit_hash` is recorded, commit state for that scope must be treated as completed unless the entry explicitly marks the commit as failed, local-only, or not pushed.

If push status is unknown, write `verify remote push state` instead of `commit and push`.

If push is confirmed, `next_step` must name the next unfinished slice rather than repeat commit or push for the completed scope.

When correcting ambiguous historical memory state, prefer adding a new canonical corrective memory entry over rewriting historical entries.

#### Memory State Interpretation Rule

Memory entries are state evidence of prior work, not authorization for current action.

A retrieved `memory.next_step` is a candidate continuation signal only. It does not grant permission to modify files, commit, push, close issues, upgrade claims, or bypass current workspace checks.

Current user instruction, current workspace state, dirty-tree status, and applicable governance rules always supersede memory content. Before acting on any memory-derived next step, the agent must revalidate the current repo state and authority boundary.

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

