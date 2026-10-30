# I2 Agent Core Rules — S2-A / S2-B delivery record (2026-10-30)

Branch `feat/i2-core-rules` from `main@48f0ce76`. Push, PR and merge are not
part of this slice. Line numbers below are "before" = `48f0ce76`,
"after" = this branch.

## Owner ruling adopted 2026-10-30 (summary, implemented as stated)

- **C1** Task DONE is not session end. Hard Stop forbids extra work after task
  DONE; a confirmed session end still requires the existing session-end
  closeout. An ordinary Stop event, a final answer or a subagent finishing is
  not session end.
- **C2** PLAN/memory updates required by defined must-record events are part of
  that delivery; after DONE, no extra unrelated rollups or new PRs.
- **C3** Memory routing: (1) architecture decision → `memory/02_workflow.md` or
  the adopted alias `02_project_facts.md` per `SYSTEM_PROMPT.md` §6.1; PLAN only
  when the decision changes PLAN scope, phase, anti-goal or another existing
  PLAN obligation (replaces BASE's unconditional "PLAN.md decision log").
  (2) "Bug fixed with root cause identified" stays, mapped to §6.1 "new gotcha /
  solution" → `memory/03_knowledge_base.md` or adopted alias. (3) Keep Review,
  Milestone, Risk/Incident and real session-end records; no duplicate memory or
  extra PRs for micro-steps. (4) Consumer-specific extra duties stay; never
  invent or assume an alias.
- **C4** Memory protocol defines order, grants no git authority
  (`MEMORY_PROTOCOL.md:340-343`); commit/push follow current owner
  authorization and consumer rules; inside an authorized slice they continue
  without re-asking.
- **C5** Every agent keeps the full Owner Gate: merging main, publish/release,
  deleting branches, closing others' PRs, irreversible operations, firmware,
  data-integrity and consumer-specific high-risk operations.
- **C6** No platform fabricates loaded documents, authorization or completion
  evidence; inferred `LOADED` or a reused stale contract block is a failure.
  Platform-specific `SOURCE` values stay.
- **C7** Report labels follow the session language (結果／原因／下一步 or
  Result／Reason／Next step).

## What changed where

| Surface | Change |
|---|---|
| `governance/AGENT_CORE_RULES.md` (new) | Canonical core body between `ai-governance:agent-core-rules` BEGIN/END (lines 23-47): Owner Gate (C5), commit/push (C4), DONE vs session end (C1), must-record table (C2/C3), no fabricated evidence (C6), labels (C7), secrets (copied from BASE Secret Handling). |
| `governance/agent-contract-template.md` (AC) | Core body at 96-120, after the UNAVAILABLE notice and before Delivery Convergence (122). Delivery Convergence trailing paragraph (before :103, after :129) now defers to the core for the Owner Gate and commit/push. |
| `governance/copilot-instructions-template.md` (CP) | Core body at 11-35, before DONE Boundary Rules. Rule 1, Rule 3a, the label sentence and the inference/stale sentence changed (below). |
| `baselines/repo-min/AGENTS.base.md`, `AGENTS.base.md` | Memory Update Triggers (55-74) and DoD line (repo-min 218-219, root 98-99). |
| `.governance/baseline.yaml` | Only `sha256.AGENTS.base.md` re-recorded (separate commit `03361480`). |
| `PLAN.md` | One Canonical Planning Surface entry for this slice + `最後更新` 2026-10-30. |
| Tests | New `tests/test_agent_core_rules_projection.py`; `tests/test_delivery_convergence_projection.py` guard updated. |

## Conflict by conflict

- **C1** before CP:20 `- commit, push, closeout, or status rollup` with no
  session-end exception. After CP:46-50: forbids unrelated rollups, unneeded
  memory/PLAN updates, new PRs and commit/push outside current authorization;
  "This never cancels must-record memory or PLAN updates, or the session-end
  closeout at a confirmed session end". Core rule 3 (AC:103, CP:18) states C1.
  AC:103 / BASE closeout block (repo-min 147-152) were already consistent and
  are unchanged.
- **C2** before BASE:209 (repo-min) / :89 (root) `PLAN.md and memory/ reflect
  the new state`. After: updates "required by the Memory Update Triggers above
  are included in this delivery; after DONE, add no unrelated rollups or new
  PRs". Core rule 4 says the same.
- **C3** before BASE:57-65, :62 `Architecture decision made | PLAN.md decision
  log + memory/knowledge_base`. After BASE:65 routes to `memory/02_workflow.md`,
  PLAN only on scope/phase/anti-goal/obligation change; bug-fix row kept and
  mapped to §6.1 gotcha → `memory/03_knowledge_base.md`; Review row added from
  §6.1; alias sentence (71-73) lists only §6.1 aliases and only if adopted;
  repository-specific duties kept (74). File names normalized to the §6.1 names
  (`memory/active_task` → `memory/01_active_task.md`).
- **C4** before AC:103 `Commit and push require authorization from this
  repository's own rules; if those rules are not in your context, ask.` After:
  core rule 2 (owner authorization + repo rules; continue inside an authorized
  slice; ask only if neither is in context); AC:129 defers to it.
- **C5** before CP:45 `(merge, release, branch deletion, irreversible, firmware
  or data-integrity operations)` and AC:103 list without consumer high-risk.
  After: core rule 1 holds the full list; CP:72 and AC:129 point to it.
- **C6** before CP:233-235 had the inference/stale rule, AC:70-94 lacked it.
  After: core rule 5 (AC:117, CP:32) carries it; CP:260-261 points to the core.
  `SOURCE` values unchanged (AC:86 `agent instructions (checkpoint projection)`,
  CP `.github/copilot-instructions.md (checkpoint projection)`).
- **C7** before CP:69-75 showed English labels, Chinese only as an aside. After:
  core rule 6 plus CP:102-104 "These labels follow the session language".

## Byte deltas (LF / CRLF)

| Surface | LF | CRLF |
|---|---|---|
| AC template | 7,177 → 9,961 (+2,784) | 7,281 → 10,091 (+2,810) |
| CP template | 13,315 → 16,496 (+3,181) | 13,551 → 16,758 (+3,207) |
| repo-min `AGENTS.base.md` | 10,317 → 11,191 (+874) | 10,526 → 11,410 (+884) |
| root `AGENTS.base.md` | 9,224 → 10,098 (+874) | 9,413 → 10,297 (+884) |
| `AGENT_CORE_RULES.md` | 0 → 4,059 | 0 → 4,106 |

Disposable consumer (`C:\tmp\cp4\base` copied; `_refresh_repo_local_instructions`
→ `install_copilot_surface` (`--copilot-only`) → `_ensure_agents_keyed_sections`):
`AGENTS.md` CRLF 26,640 on `48f0ce76` → 29,450 here (+2,810), headroom vs
32,768 = 3,318 (was 6,128). Second run changes nothing. Text outside the
managed blocks of `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and
`.github/copilot-instructions.md` is identical to the `48f0ce76` run.

## Placement and test justification

The core sits after the checkpoint projection and UNAVAILABLE notice and before
Delivery Convergence, which stays the last section, so the #267 placement test
passes unchanged. One assertion in the guard test
(`if those rules are not in your context, ask`) changed because ruling C4
replaces that sentence; it now checks the Delivery pointer and the core's
"If neither is in your context, ask."

## Not done / open for the owner

- `governance/AGENT_CORE_RULES.md` is not registered in `governance/AUTHORITY.md`
  and has no frontmatter: registering it is an authority-table change and is
  left to the owner.
- Not resolved by the ruling, left unchanged: BASE Milestone row requires
  `PLAN.md` phase/sprint on every milestone, while §6.1 requires `PLAN.md` only
  when planned scope, phase status or anti-goal change. The core keeps BASE's
  wording.
- The framework's own `.github/copilot-instructions.md` is a custom file, not
  an install of the CP template; it was not changed.
- Re-recording the protected `AGENTS.base.md` hash is in its own commit
  (`03361480`) so it can be dropped separately.
- No push, PR, merge or consumer installation.
