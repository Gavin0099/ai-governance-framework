# AI Governance — R2 closeout, over-governance reduction and bounded autonomous loop handoff

**Date:** 2026-10-30 (Asia/Taipei)  
**Status:** PROPOSAL / CLAUDE HANDOFF ONLY — docs-only, not adopted runtime policy.  
**Target:** Gavin0099/ai-governance-framework.  
**Original common-ancestor baseline:** main at 48f0ce767677c83504e23ac0d3141d81ceca5d88. **This stacked docs-only Draft PR targets the unmerged #270 branch** (feat/i2-core-rules-pr), rather than re-opening unrelated main PLAN freshness debt; it must not be merged ahead of #270.  
**Related implementation:** Draft PR #270, exact HEAD 898fc7db3c82da64e992dc4cd6237650534fdf4e (NOT merged at this snapshot).  
**Existing plan:** [2026-10-29 instruction architecture autonomous loop](2026-10-29-instruction-architecture-autonomous-loop.md). This document is a current-status and decision-impact handoff, **not another implementation plan or authorization**.

## 1. One-paragraph owner goal

The owner wants AI coding agents to **finish the approved product slice with the necessary safety and evidence, and stop**. Routine tests, scoped corrections, review follow-up, Draft PR evidence updates and CI observation should not demand repeated human confirmations **when already authorized by both owner and repository rules**. A bounded agent loop and quiet heartbeat should reduce interruptions, **not create another governance framework, gate, memory stream, task chain or endless optimization loop**. Owner-only decisions (merge, release, irreversible / firmware / data-integrity operations, protected trust changes, new task scope) remain owner-only.

## Owner 摘要（繁體中文）

- **R2 / #270：**核心規則、容量量測與 F-7 正向實測已完成；最新 898fc7db 的 CI 為 11 項成功／1 項預期跳過，Codex Review 無新發現，但 PR 仍是 Draft／未合併。
- **R1 Memory：**缺少明確的 Knowledge Base 候選寫入流程；TacticalGo Active Task 已進入 EMERGENCY，既有 B2 誠實回報 PARTIAL。先處理契約與經授權的 disposable archive，不能用放寬安全規則換取綠燈。
- **R3 過度治理：**完成產品任務優先；真正影響當前驗收的問題在原授權內修，無關 P2/P3 不新增 PR／Gate／Review，DONE 就停止。
- **Loop／心跳：**已做過一次安靜本機監控；建議每 60 秒寫本機 log，只在階段變更、實際結果或連續三次無進展時通知，並先診斷長時間指令，不自動重啟。
- **Owner Gate 保留：**合併／發布、根目錄 protected BASE Hash、正式 Consumer Archive、R1 執行與新的 Loop 工具都不因本提案取得授權。

## 2. Verified status versus future work

| Area | Evidence as of this snapshot | Claim ceiling / unfinished work |
| --- | --- | --- |
| R0 governance documentation inventory | 64 governance Markdown files, approximately 429 KB in main, classified by load role and use | Inventory done; **do not read/review all 64 again**. File count is not prompt-injection volume |
| R2 core rules and delivery | #270 HEAD 898fc7db; 133 locally related tests PASS. Exact-HEAD GitHub checks: 11 success, 1 expected skipped. Codex Review summary for 898fc7db: completed, no findings | **Draft, not merged.** GitHub automatic review is not owner merge authorization. Claude and Copilot real agent sessions: NOT RUN |
| R2 F-7 behavior | Real disposable Codex N1 rejected pointer-only completion; N2 actually ran F-7, independent read-only check confirmed full_update_completed, no unauthorized commit/push. Latest fix measures final AGENTS.md after all F-7 edits in external and submodule paths; mutation test proves the boundary regression catches the omission | Capacity overflow is **warning/report-only**, not a block. First update run by an old submodule cannot use new warning logic until a later run. Existing managed F-7 region can overwrite consumer text placed inside that region |
| R2 loading budget | Full F-7 installs in two consumer copies fit under 32,768 B (30,582 / 30,134 CRLF bytes); installer-only is around 36 KB and now reports budget warning | Do not infer every platform actually loaded the entire file. Existing consumer-owned content outside managed blocks must survive |
| R1 memory | Disposable K1 pilot proved no-hook could falsely claim DONE after skipping root-cause recording. Hook detected omission and obtained honest DELIVERY PARTIAL; non-obligation UI case passed | Autonomous positive completion **not proved**. See section 3. Do not rerun completed A/C or repeat failed B2 unchanged |
| R3 over-governance/effectiveness | Delivery Convergence already says product slice first, failure-driven expansion, scope-matched checks and stop at DONE; #270 within-scope P2 follow-up demonstrates successful no-extra-approval handling | Need evidence that ordinary agents actually stop doing unrelated work; do not add a new generic instruction stack |
| R4 historical / specialist docs | Inventory identifies archive candidates and active canonical references | Low priority; do not move/delete MRCSP or other referenced contracts just because they look old |
| Quiet heartbeat / loop | #270 local watcher wrote one-minute logs outside the repo; meaningful notifications used phase/result changes, with 3 unchanged polls as a stall-investigation trigger; it stopped when CI and Review reached terminal states | This was a **one-run local monitor**, not a reusable cross-repo controller or promised background automation |

**Source links:** [#270](https://github.com/Gavin0099/ai-governance-framework/pull/270); [R2 Codex review summary](https://github.com/Gavin0099/ai-governance-framework/pull/270#issuecomment-6517308160); [Delivery Convergence](../../governance/agent-contract-template.md); [memory pressure rule §7.4](../../governance/SYSTEM_PROMPT.md); [memory writer contract](../../governance/MEMORY_PROTOCOL.md).

### R2 details that must not be silently re-opened

- #270 added one canonical AGENT_CORE_RULES.md and byte-matched projections to Codex/Claude/Gemini and Copilot templates; registered canonical/on-demand in AUTHORITY/frontmatter (not always loaded twice).
- Kept owner/commit/push gates, real session-end distinction, must-record triggers, no fabricated LOADED, language-local report labels and secrets guard.
- Aligned Milestone semantics: update Memory when triggered; update PLAN only when phase/scope/anti-goal or an existing PLAN obligation changes.
- Fixed both F-7 warning forwarding paths and **final-file remeasurement**; a dedicated regression starts below budget at install and goes above after F-7 keyed sections, and fails when the fix is removed.
- Rewrote PR description instead of accumulating stale appendices. No extra N1/N2 rerun required for docs-only future work.

## 3. R1 Memory is a real product blocker; do not relax its safety rules for a green test

Facts from verified source and disposable pilot:

1. governance_tools.memory_record currently targets **daily, review-log, active-task-summary**, not memory/03_knowledge_base.md.
2. governance/SYSTEM_PROMPT.md §6.1 requires recording a confirmed new bug gotcha in the Knowledge Base, but MEMORY_PROTOCOL's canonical-writer prose and consumer router wording need a precise distinction between session-derived event records and candidate reusable knowledge.
3. A candidate KB entry **is not promoted / reviewed knowledge**. A daily record bound to a real fix commit does not alone satisfy the KB obligation; do not fabricate an approved_by reviewer or promotion.
4. TacticalGo memory/01_active_task.md was measured at **236 lines / 33,868 Unicode characters**, which is EMERGENCY because §7.4 uses lines OR characters (12,000-character threshold).
5. Under EMERGENCY, the bounded-maintenance exception expressly requires **no memory modifications** and no full memory writer/closeout round trip. B2 therefore correctly returned DELIVERY PARTIAL, rather than bypassing §7.4.

**Next R1 decision, NOT authorized by this document:** confirm the legal candidate-KB + canonical-daily workflow, and separately approve **disposable archive + verified replacement-state cutover** before *one new* B2 positive-path trial. It must retain original hashes and current-state anchors, remeasure pressure, not run legacy fail-closed cleanup, and must not imply permission to modify the real TacticalGo Consumer. Real TacticalGo archive requires its own explicit owner scope. The v5 freeze remains frozen.

## 4. R3 over-governance: decide whether a finding blocks this delivery

Observed failure pattern: a small requested feature leads to optional tests, new SOP, unrelated refactor, repeated P2/P3 fixes, additional review, repeated requests for approvals already granted, or redundant PLAN/memory updates. Those activities consume time/tokens and can obscure the actual product deliverable.

**Use existing Delivery Convergence, not a new global gate:**

| Finding or event | Decision for an agent operating under a specific approved scope |
| --- | --- |
| Confirmed defect breaks the current acceptance, safety, authorization, data integrity, or reproducibility | Fix within authorized scope; HOLD/escalate when authority or decision is missing |
| Review P2/P3 **does affect current acceptance** and the fix is narrow (like #270 final-file capacity warning) | Fix and run targeted delta verification; do **not** ask the owner to approve each small correction |
| Review P2/P3 is unrelated, speculative or non-blocking for the current owner decision | One-line disposition in next options; **no new implementation, PR, test suite, gate or re-review** |
| Reviewer requests additional tests unrelated to changed semantic blast radius | Do not run them merely for completeness; explain scope-match |
| Approval for normal edit/test/commit/push/Draft PR update already exists in both owner instructions and repo rules | Continue within that exact permission; no repeated approval request |
| New architectural policy, scope, irreversible action, merge/release/firmware, protected hash or material unknown impact | Pause the affected path and seek an explicit owner ruling |
| Mandatory Memory or genuine SessionEnd still required | Do not drop that obligation to make DONE green; if it cannot be completed, report honest PARTIAL |
| Approved DONE and required evidence reached | STOP; list optional improvements as options only |

Review severity label alone is insufficient: **current-decision impact**, not just P2/P3, determines whether a correction is mandatory. Preserve a bounded review loop: suggested ceiling **two independent review rounds and three bounded correction iterations** for a pilot; exceeding it is HOLD, not an excuse to open another governance project. This is a candidate loop operating limit, not an established universal policy.

**Measure effectiveness with existing session/CI/git evidence, without building a dashboard:** usable product DONE, unrelated governance side quests, redundant owner confirmations, re-review cycles, false blockers, unsafe omissions, and optionally elapsed time/token cost when genuinely observable. Never infer population-wide improvements from a single run.

## 5. Proposed quiet loop and heartbeat (future pilot, not installed here)

**Suggested state path:** APPROVED_SLICE → IMPLEMENT → TARGETED_TEST → DELTA_REVIEW → (bounded FIX if real blocker) → INDEPENDENT_VERIFY → DONE / PARTIAL / HOLD. This is orchestration of existing tools; it must not replace owner authority, session lifecycle or existing real verifiers.

- **Heartbeat:** record local run state about every 60 seconds in a runtime log outside memory/ (for the #270 example: C:\tmp\pr270-watch.log), not in memory/01_active_task.md. Suggested fields: task/run identity, exact HEAD, phase, last progress/event count, active child command/process, last check, conclusion and reason.
- **Notify the owner only when:** a phase changes, a meaningful result/terminal failure occurs, or **three consecutive polls show no observable progress**.
- **Three unchanged polls do not prove a hang:** first inspect active subprocess, command, CI progress and last output. Do not auto-kill, auto-restart, install a new watcher, or exceed original task authority.
- **Review and CI watcher:** observe exact-HEAD checks and comments, not just the newest comment; stop itself once all required checks and targeted review reach terminal states. Report observed status, not guesses. Never claim a watcher keeps running after the actual local process ends.
- **Loop must stop:** after agreed DONE, nonrecoverable policy/permission conflict, review/repair cap, new scope, or owner-gated operation. Unrelated independent pre-authorized slices may proceed when safe.
- **Do not make monitoring into governance churn:** no heartbeat commits, no per-minute chat messages, no new PR for a nonblocking warning, no nightly cleanup as an unapproved side effect.

Do not introduce a general persistent daemon, additional gate, policy schema, task database or dashboard merely to automate this one observed local workflow. Reuse the existing runner/logging and assess a single disposable pilot first, when separately authorized.

## 6. Minimal targeted acceptance, not another giant A/B campaign

| Need | Smallest useful check | Claim ceiling |
| --- | --- | --- |
| R2 #270 | Existing final HEAD CI/review and already completed S-F7 N1/N2 | R2 engineering evidence; does not prove S-MEM/Claude/Copilot runtime compliance |
| R1 positive write | Single disposable B2 after approved archive and canonical write-path clarification; verify KB candidate + daily writer evidence + matching commit + memory_workflow | A B2 positive result for that context; not autonomous KB promotion |
| R1 false-block control | Reuse successful no-memory-obligation S-UI evidence, rerun only if changed behavior could affect it | No unnecessary blocked UI task in that scenario |
| R3 sidequest behavior | One small product slice plus irrelevant review suggestion; verify agent finishes product and does not spawn new work | Single-run behavioral proof, not statistical effectiveness |
| R3 safety counterexample | One previously verified owner/scope refusal test if applicable to changed surface | No weakening of owner gate |
| Future loop monitor | One bounded local run, simulating normal progress, three unchanged polls, meaningful terminal transition and terminal shutdown | Monitoring semantics only; not proof of async deployment to all repos |

Static consistency checks and tests remain valuable; **prompt loaded**, **tool installed**, **tool actually invoked**, **policy enforced** and **task completed** are separate evidence classes. Do not claim one from another.

## 7. Outstanding decisions and constraints

- **#270 merge**: exact-head owner approval remains mandatory. This docs PR is not approval to merge #270.
- **PR #271 dependency:** this docs-only Draft targets the unmerged #270 branch, not main. It requires #270 to be handled first; never merge #271 early, force-push either branch or treat this as approval for #270.
- **CRLF-only overflow warning**: user acknowledgement/sign-off pending for a slightly broader interpretation of the owner ruling; do not silently represent it as explicitly ratified.
- **Framework root AGENTS.base.md**: modifying its protected hash is held separately (hold/i2-root-base-rehash); no such change here.
- **R1 implementation / disposable archive**: separate owner authorization; this document does not authorize it.
- **Real TacticalGo Consumer cleanup**: separate owner authorization.
- **Claude/Copilot real runtime behavior**: NOT RUN; do not upgrade projection/static evidence to actual runtime success.
- **Historical files and MRCSP**: treat canonical and referenced materials carefully; R4 archival isn't urgent and must not be a prerequisite for R1/R3.

## 8. Instructions for Claude receiving this handoff

1. Read this handoff and the **latest exact** #270 PR/CI/Review status. Read the 2026-10-29 proposal as historical scope and the relevant canonical governance files when needed; don't silently treat #270 as merged.
2. **Produce one short decision table**: already complete / actual blocker / nonblocking next option / explicit owner decision; prefer the smallest next step. Focus first on R1 Memory semantics, then R3 efficiency; preserve R2 evidence.
3. For an implementation requested later, first identify **exact bounded scope, DONE, safety nonclaims, existing permission** and its nearest real verifier. Do not repeatedly ask about already authorized internal steps.
4. **Do not implement or start a loop based on this docs PR alone.** No new code, hooks, canonical-rule changes, consumer archives, extra PRs, protected-hash edits, merge or deployment are implied.
5. If a source is missing from the actual agent context, say NOT LOADED / NOT VERIFIED. A projected [Governance Contract: UNAVAILABLE] block is not proof SYSTEM_PROMPT.md was read. Never invent review, CI, runtime, or authorization evidence.
6. When a work item is DONE, deliver a concise result, decision-relevant caveats and at most the necessary owner choice. No extra improvement loop for a speculative P2/P3.

**Proposal DONE for this PR:** one docs-only handoff, no behavior changes, no consumer mutations, no adopted authority changes. The success of any future R1/R3 loop is a **separate** decision and requires real test evidence.