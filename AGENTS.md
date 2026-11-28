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

## Governance Contract Output (MANDATORY)

The rules below are projected verbatim from the canonical source named in the
projection header, which carries the projection version and the content digest
of that canonical section. Do not edit them here. Edit the canonical section,
then regenerate:

```bash
python -m governance_tools.copilot_instructions_projection --framework-root . --write
```

<!-- ai-governance:checkpoint-projection BEGIN version=1.1 source=governance/SYSTEM_PROMPT.md#2.8 sha256=bde31e2dbdfbb3b07421248db57e202f52cf9f20523094ea390b8913817a80bf -->
### 2.8 Governance Contract Output

在以下時點輸出此 block：
- task 開始
- milestone 完成
- scope 改變
- stop / escalation 事件
- 任何 contract 欄位發生實質變化時

若只是 routine progress commentary 且 state 未變，可省略。

```text
[Governance Contract]
LANG     = <value>
LEVEL    = <value>
SCOPE    = <value>
PLAN     = <current phase> / <sprint> / <task>
LOADED   = <comma-separated list of loaded governance docs>
CONTEXT  = <context name> -> <responsible for X>; NOT: <not responsible for Y>
PRESSURE = <SAFE|WARNING|CRITICAL|EMERGENCY> (<line count>/200)
         # 或 <LEVEL> (<line count>/200 lines; <char count> chars)
AGENT_ID = <agent-id>       # optional; required in multi-agent sessions
SESSION  = <YYYY-MM-DD-NN>  # optional; required when AGENT_ID is present
```

欄位規則：
- `LANG`: 取自 `C | C++ | C# | ObjC | Swift | JS | Python | Verilog | SystemVerilog | GDScript`。
  單一語言直接填該值；跨語言任務以逗號分隔，每個元素都必須是上列值之一（例：`C, C++`）。
  不得把多個語言寫成單一 token（例：`C/C++`）：`/` 已是 `SCOPE` 的 `I/O` 值的一部分，
  在同一個 block 內不能再兼作清單分隔符。分隔符與 `LOADED` 一致。
- `LEVEL`: 單值，取自 `L0 | L1 | L2`
- `SCOPE`: **單值**，取自 `feature | refactor | bugfix | I/O | tooling | review | governance | kernel-driver`。
  `SCOPE` 會決定 review、testing 與 governance routing；多值會引入未定義的優先序與衝突語義，
  因此不接受清單。任務橫跨多個 scope 時，拆成多個 task 或選擇主導的那一個。
- `PLAN`: 取自 `PLAN.md`；若人類明確授權 governance analysis，可標 `Out-of-scope`
- `LOADED`: must name governance docs actually loaded into the agent context. It must include `SYSTEM_PROMPT`; `HUMAN-OVERSIGHT.md` is human-only authority and must not be listed as loaded unless a human explicitly provides it.
  每個項目以逗號分隔。文件識別採**最後一段路徑、可省略 `.md`**，因此下列四種寫法識別為同一份文件：
  `SYSTEM_PROMPT`、`SYSTEM_PROMPT.md`、`governance/SYSTEM_PROMPT.md`、
  `ai-governance-framework\governance\SYSTEM_PROMPT.md`。
  正規化規則：`\` 一律視為 `/`；取最後一段；**只有 `.md` 可省略**，其他副檔名不得省略；
  比對**區分大小寫**。因此 `SYSTEM_PROMPT.txt`、`MY_SYSTEM_PROMPT.md`、`system_prompt`
  都不是 `SYSTEM_PROMPT`。寫出完整路徑比裸 token 攜帶更多可稽核資訊，兩者同等合法。
- `CONTEXT`: 必須同時包含 `->` 與 `NOT:`
- `PRESSURE`: 必須含 label 與**實際的** line count，兩種形式擇一：
  - `<LEVEL> (<line count>/200)`
  - `<LEVEL> (<line count>/200 lines; <char count> chars)`
  第二種形式存在的理由：§7.4 的判級依據是「行數**或**字元數任一達標」，只寫 line count
  時，因字元數達標而升級的判定在 contract 裡無法被檢視。需要說明判級理由時用第二種。
  兩個數字都必須是實際整數；分母固定 200。`(<line count>/200)` 這種未替換的樣板、
  `(pending exact line count/200)` 這類佔位字串、非數字與負數都屬格式錯誤。
- `SESSION`: 當 `AGENT_ID` 存在時必填

格式錯誤的 contract block 屬於 governance failure。
<!-- ai-governance:checkpoint-projection END -->

### When SYSTEM_PROMPT.md is not loaded

`LOADED` must name governance documents actually loaded into this context, and
the canonical rules require `SYSTEM_PROMPT` among them. This file is a projection
of one canonical section — it is not `SYSTEM_PROMPT.md`, and its presence is not
evidence that `SYSTEM_PROMPT.md` was read.

When `governance/SYSTEM_PROMPT.md` has not actually been loaded, no compliant
`[Governance Contract]` block can be produced. Emit this notice at the same
checkpoints instead, and never emit a block whose `LOADED` names documents that
were not read:

```text
[Governance Contract: UNAVAILABLE]
REASON  = governance context incomplete
MISSING = SYSTEM_PROMPT
SOURCE  = AGENTS.md (checkpoint projection)
NEXT    = load governance/SYSTEM_PROMPT.md, or ask the human to provide it
```

Reading `governance/SYSTEM_PROMPT.md` during the session clears the notice, and
that change to `LOADED` is itself a material contract change — emit the full
block at that point.

<!-- ai-governance:agent-core-rules BEGIN version=1 canonical=governance/AGENT_CORE_RULES.md -->
## Agent Core Rules (MANDATORY)

Identical on every agent surface. Repository rules may add duties; they never relax these.

1. **Owner Gate.** Every agent needs explicit owner approval before merging into main, publishing or releasing, deleting branches, closing another person's PR, any irreversible operation, firmware operations, data-integrity operations, and any high-risk operation this repository's own rules name. No directive, slice approval or protocol relaxes this gate.
2. **Commit and push.** Memory and delivery protocols define order, not git authority. Commit and push follow the owner's current authorization and this repository's rules; inside an owner-authorized slice they may continue without re-asking. If either is missing from your context, ask.
3. **Task DONE is not session end.** After task DONE, stop and do no extra work. A confirmed session end still requires the existing session-end closeout. An ordinary Stop event, a final answer, or a subagent finishing is not session end.
4. **Must-record events.** Memory or PLAN updates these events require are part of that delivery, not extra work. A task limited to named files still includes these records unless the owner explicitly excludes them. Honor explicit edit bans covering a record, including bans on changes outside named files or directories or on creating its file, and report that record as unwritten. After DONE, add no unrelated rollups or new PRs; do not record micro-steps or duplicate a record. Repository-specific record duties still apply. An agent's private or tool-provided memory (for example Claude auto-memory or the Copilot memory tool) may help the agent, but never satisfies these records; only the records named here or by this repository, written through their own contracts, do.

| Event | Record in |
|---|---|
| Architecture decision | `memory/02_workflow.md`; `PLAN.md` only when it changes PLAN scope, phase, anti-goal or another existing PLAN obligation |
| Bug fixed with root cause identified (new gotcha / solution) | `memory/03_knowledge_base.md` as a `CANDIDATE / UNREVIEWED` entry (root cause, fix, fix commit, test evidence) paired with a `memory_record` daily record for the same fix commit; never marked approved, reviewed only through promotion |
| Review completed | full record in `memory/04_review_log.md`, one-line summary in `memory/01_active_task.md` |
| Milestone reached | `memory/01_active_task.md`; `PLAN.md` phase/sprint only when it changes PLAN phase, scope, anti-goal or another existing PLAN obligation |
| Risk or incident encountered | `PLAN.md` risk section + `memory/01_active_task.md` |
| Confirmed session end | canonical `memory/YYYY-MM-DD.md` record through the session-end closeout when it is non-stateless |

Use an alias only when this repository has adopted the `SYSTEM_PROMPT.md` section 6.1 alias schema (`02_project_facts.md`, `03_decisions.md`, `04_validation_log.md`); never assume an alias that does not exist.

5. **No fabricated evidence.** Never claim a document was loaded, an authorization was given, or work was completed without evidence in this context. Filling `LOADED` or any other contract field by inference, or reusing a stale `[Governance Contract]` block such as one from an earlier session, is a governance failure. The block is evidence of what was loaded, not a formatting ritual.
6. **Report labels follow the session language:** Chinese `結果：` / `原因：` / `下一步：`; English `Result:` / `Reason:` / `Next step:`. In owner-facing reports, lead with the original goal, what happened, its impact on that goal, and any owner decision actually needed, preserving evidence and authority limits.
7. **Secrets.** Never commit tokens, API keys, credentials, or secrets to the repo; never write tokens or credentials into memory/ files or logs.
8. **Reuse prior evidence.** Before proposing a rerun, revalidation, or next slice, or relying on PR status, check relevant PLAN, memory, and evidence. For each decision, open relevant PRs or issues and their evidence, including Draft PRs at their own ref or commit. Search by topic only without a relevant lead. Distinguish work done, verified evidence, formal eligibility, remaining gaps, and the smallest authorized next step. Reuse qualifying evidence. Refresh live status when it affects the decision. If evidence is unavailable, mark the decision `UNKNOWN`. Do not infer the work was never done or needs a rerun. No table is required for this check.
<!-- ai-governance:agent-core-rules END -->

## Conditional Governance Routers

Before acting, load the detailed protocol only when its trigger applies:

1. Memory write / post-push memory / memory correction:
   read `governance/MEMORY_PROTOCOL.md`.
   Run `python -m governance_tools.memory_workflow --check` before claiming
   completion for any task that edits, backfills, analyzes, or reports repo
   memory.
   New session-derived memory must use `governance_tools.memory_record`.
   Direct markdown append is prohibited.

2. Owner-facing status, diagnosis, review, plain explanation, final report or
   closeout: read `governance/RESPONSE_ENVELOPE_CONTRACT.md`. Preserve the complete
   machine envelope including `not_claimed`; follow its result-first rendering,
   non-claim visibility and plain-language glossing rules. Keep raw fields in
   canonical evidence; display exact tokens only when decision-relevant or requested.
   Give each surfaced machine/guard field token a one-line plain-language meaning.

3. Review / assess / audit / recommend next changes:
   read `governance/REVIEW_CRITERIA.md` before findings; it routes additional
   testing, architecture and knowledge-base inputs.

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

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->

- Do NOT relax the `verified` definition or admissibility criteria to improve the verified ratio — verified count must reflect genuine governance adoption, not calibrated thresholds
- Do NOT use a `gate_blocked=true` closeout receipt as admissible evidence — this was an observed failure mode already fixed; reverting is forbidden
- Do NOT treat a closeout receipt as proof of framework correctness — receipts prove evidence chain integrity, not that the governance model is correct
- Do NOT mix schema changes with repo onboarding commits — schema and evidence contract changes must be separate commits with explicit justification
- Do NOT let `self_reference_note` in framework.lock.json be removed — it exists to prevent semantic drift where self-verification is misread as framework correctness proof

## Workspace vs Repo Governance

This file governs session/workspace behavior, memory habits and safety.
`governance/AGENT.md` and `governance/` own repo engineering classification,
execution rigor, architecture, risk and testing gates. For repo work they prevail
over conflicting workspace/editor/adapter instructions; correct the mismatch
instead of silently inventing policy.

### Persistent User Preference Precedence

Surface conflicts with durable user preferences or permanent tool instructions;
state the chosen source and reason. Repo governance overrides preferences only
for safety, destructive-operation prevention, validation/evidence/claim boundaries,
commit/push discipline or repo correctness. It must not override language, style,
verbosity, non-conflicting workflow, naming or formatting preferences.
When uncertain, report:

```text
Instruction conflict detected: <repo instruction> vs <persistent user preference>.
Following <source> because <reason>.
```

## Nested Repo / Submodule Rule

Treat this root as a separate workspace when nested. Confirm it before accessing
`memory/`, `artifacts/`, `PLAN.md` or `governance/`; never mix parent/child memory,
review notes, active-task updates or governance artifacts. Findings must name
the repo owning the file and the repo owning the decision. Submodule pointer
updates are parent-repo decisions; advancing this checkout does not update the
parent's intended pin.

### AI Governance Update Trigger

Follow Conditional Governance Routers 4–5 before check/update work. Route
"幫我更新最新版 AI Governance" or equivalent wording to
`governance_tools.f7_full_update`, even without the name F-7. Its updater is a
backend, not the final reporting surface.

Instruction sync, parent `git pull` or a clean parent tree do not prove framework
freshness. A submodule pointer alone is incomplete, never `full_update_completed`.
This workspace section is a trigger summary, not the canonical definition.
For consumer updates, prefer the governed F-7 path. A direct pointer, checkout or
lock edit is a `manual_update` path, incomplete without governed evidence.
`governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` owns the definitions, templates,
pre-discard inspection and final discarded-path inventory for `manual_update`
and `destructive_manual_update`; read it before changing nested state.
Before discarding local state in a nested framework checkout, first inspect the modified and untracked paths to be discarded.
If cleanup proceeds, list that inventory in the final report as `destructive_manual_update`.
Do not call discarded state merely "cleaned the submodule".

Every F-7 terminal report relays the complete `[human_readable_adoption_summary]`
table. If unavailable or omitted, report
`human_readable_adoption_summary: NOT REPORTED`, `update_report_complete=false`
and `completion_claim_allowed=false`; do not claim a complete update report.

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

## Delivery Recovery Constraints

These apply to framework and consumer implementation sessions; governance must
not displace product delivery.

### 1. Vertical Slice First

Complete one usable end-to-end product slice before expanding governance
(e.g. `scan -> select -> execute -> result`), unless an observed failure requires it.

### 2. Failure-Driven Governance Only

New governance requires observed unsafe behavior, irreversible failure, a false
positive/negative, authority escalation, replay inconsistency or production
ambiguity. Future extensibility, theoretical completeness, semantic elegance
and "might be useful later" are not triggers.

### 3. Session Done Definition Required

Before edits, use the user's DONE or propose one measurable product outcome and
wait for confirmation: `DONE = <one measurable product outcome>`.
Keep it narrow and testable; broad project direction is not DONE.
An explicit bounded directive ("proceed", "continue", "only converge") authorizes
execution inside its stated boundary without redundant confirmation. Ask again
only for scope expansion, enforcement or schema/runtime behavior changes, or
new irreversible/destructive risk.

#### Ambiguous Continuation Is Audit-First

"Continue", "proceed", "keep going", "繼續", "往下做" or "再做下一步" alone
does not establish a boundary. Without an approved next slice, inspect current
state and the last committed/validated scope; propose a narrow slice with scope,
allowed files, non-goals, validation, commit/push intent and non-claims. Wait for
confirmation before edits. Execute an already approved slice without re-proposing it.

### 4. Hard Stop After Done

At DONE, stop; report additional work as next options only. Add no telemetry,
readiness, qualification, hooks, artifacts or governance without an observed
failure. Do not automatically run full regression, broad smoke, closeout,
status/rollups, unrelated cleanup, commit, push or inspect unrelated dirty files.

### Session-End Closeout (MANDATORY)

The block below is a verbatim copy of the canonical block in `AGENTS.base.md`
(Session Closeout Obligation). Do not edit it here; edit the canonical block and
copy it to every entry file. No generator or drift check covers this block yet.

<!-- ai-governance:session-end-closeout BEGIN version=1 canonical=AGENTS.base.md -->
### Session-End Closeout Responsibility

These rules apply to every agent platform (Codex, Claude, Copilot and others).
They define when closeout is required, who is responsible, and what may be
claimed. They do not define which lifecycle event a platform uses; that is
platform-specific and must be qualified separately for each platform.

1. **Task DONE is not session end.** Finishing a task, a review, or a milestone
   ends that task only. Report DONE, do not expand the work, and leave the
   session open for the next request.
2. **Closeout at a defined session end is a duty, not new work.** A mandatory
   closeout at session end is not scope expansion. Hard Stop After DONE forbids
   closeout after task DONE; it does not forbid closeout at session end.
3. **Session end must come from a defined, observable source.** Only two sources
   count: a platform lifecycle event whose session-end meaning has been
   confirmed for that platform, or the user explicitly asking to end the session
   or to close out. The user may give that request in advance: an owner
   authorization that names a concrete closeout or handover condition counts
   once the agent has met that condition, provided it traces to a verifiable
   original owner source and was recorded before the session started. A plan
   item, a memory `next_step`, or an authorization the agent wrote for itself
   does not count. The agent must not infer that the conversation is over. A
   final answer, a DONE report, or a per-turn `Stop` event is not session end
   unless that meaning has been confirmed.
4. **Governed lifecycle hook present:** the harness is responsible for
   triggering canonical closeout. A governed hook is one wired to the governance
   closeout entry and confirmed to run for this platform.
5. **No usable governed hook:** only when session end is established under
   rule 3, the top-level agent must attempt the existing manual closeout
   (`python -m governance_tools.manage_agent_closeout print-manual --agent <agent>`
   prints the command). If it cannot run or its result cannot be verified,
   report closeout as `NOT PERSISTED` or `UNKNOWN`; never claim it was persisted.
6. **Subagent completion is not project-level session end.** A subagent
   returning to its parent must not run project-level closeout unless it has its
   own governed session identity and was explicitly given closeout
   responsibility.

A closeout, including the manual fallback, does not authorize commit, push,
pull request, or a new task; each still needs its own explicit authorization.

Closeout candidate, canonical record, and memory are verified separately. A
successful closeout on one platform is not evidence for any other platform.
<!-- ai-governance:session-end-closeout END -->

### 5. Scope-Matched Validation

Run targeted checks for the changed scope first. Full regression, broad smoke
or closeout only if the DONE definition explicitly requires it or the user
explicitly requests it. Markdown-only work
needs no runtime tests; a helper change runs its related test file; full
regression is a release gate. This and Hard Stop apply to task DONE; closeout
at an established session end follows the mandatory block above.

### 6. Dirty Tree Allowlist

Run `git status --short` and give a concise summary; classify paths as in scope,
unrelated or unknown. Inspect, explain, summarize and validate only the claimed
scope or an approved allowlist. Never read, stage or modify unrelated dirty or
untracked files without explicit approval. Stage only user-listed or DONE files;
provide commit-preflight review only when commit is requested.

#### Dirty Work Must Not Be Reported as Overall DONE

Only committed, validated scope may be DONE. Any remaining unstaged, staged but
uncommitted, untracked, generated or uncommitted auto-review work, or failed/
unavailable commit/push tooling, prevents overall DONE. Use this wording:

```text
Committed scope: DONE
Workspace state: NOT CLEAN
Overall task: NOT DONE until dirty work is audited or explicitly excluded
```

### 7. Result-First Final Report (reporting convention, not a gate)

Before a final report or closeout, read `governance/RESPONSE_ENVELOPE_CONTRACT.md`
for rendering, triggers, the F-7 exception, language/glossing and report paths.
Even if unavailable: lead with the result; derive `mode` from the event; preserve
`mode_source`, `task_authority`, `scope`, `done`, `claim_ceiling`, `not_claimed`,
`evidence_refs`, `risk` and `next_action` separately in the complete machine record.
Compact text must preserve decision-relevant non-claims, blockers and owner
decisions; expand if needed. Use one `注意：` line for dirty state, material
limitations or high-risk authority surfaces, or report failed/partial. `PASS`
must name a command, artifact or source.

#### Progress Updates

Keep updates concise, in the session language and on demand. Each must add a
discovery, root-cause convergence or plan change; omit routine command/search/
retest narration. No hard maximum applies. Final reports state results rather
than replay progress.

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

## Companion / Chat Operations

See `TOOLS.md` for non-repo companion and chat operation guidance.

