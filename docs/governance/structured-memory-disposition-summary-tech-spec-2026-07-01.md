# Structured Memory Disposition Summary Tech Spec - 2026-07-01

狀態（Status）：`PENDING`
範圍（Scope）：docs-only implementation tech-spec
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
測試行為（test behavior）變更：否
CI 行為（CI behavior）變更：否
pre-push / hook 行為變更：否
強制執行（enforcement）變更：否
消費端儲存庫（consuming repo）變更：否

## Problem

目前 repo 已經有 canonical daily memory writer，但 daily memory 只回答：

```text
今天有沒有留下 session-derived 記錄？
```

它沒有回答：

```text
這次工作是否也應該同步長期或結構化 memory？
如果沒有同步，是不適用、合法延後，還是漏掉？
```

這造成一個反覆出現的使用者痛點：agent 可以完成 daily memory，甚至通過
memory workflow 檢查，但 `memory/01_active_task.md`、knowledge base、review
log，或消費端 repo 自己的 `00-04` 結構化 memory 仍可能過期。也就是說，現有
machine check 驗證的是「有沒有寫 daily memory」，不是「該同步的結構化記憶
是否有 disposition」。

這份 tech-spec 的目的，是定義一個 warning-only 的
`structured_memory_disposition` summary，讓 agent 每次收尾時必須明確宣告結構化
memory 的處置結果，而不是默默跳過。

## Current Repository Truth

已確認的 repo 事實：

- `governance_tools.memory_record.append_session_derived_entry()` 只寫入
  `memory/YYYY-MM-DD.md`，不會自動修改 `memory/00_long_term.md` 或其他
  structured memory files。
- `governance_tools.daily_memory_guard.evaluate_daily_memory_warning()` 是
  advisory-only daily memory guard。它檢查 latest runtime summary 是否缺少
  daily memory path，不檢查結構化 memory 是否同步。
- `governance_tools.memory_authority_guard.check_structural_memory()` 目前只掃
  `memory/00_long_term.md` 的 `##` section promotion markers。它不是消費端
  `00_master_plan.md` / `01_active_task.md` / `02_tech_stack.md` /
  `03_knowledge_base.md` / `04_review_log.md` 五檔模型的同步檢查器。
- `governance_tools.memory_workflow` 的 task keyword 已包含 `active task`、
  `review log`、`knowledge base`，表示 workflow router 已預期這類 memory
  任務存在，但目前沒有 per-file disposition summary。
- `governance_tools.memory_record` 已有 P1-D
  `plan_reconciliation` declaration pattern：
  `updated | not_applicable | deferred:<taxonomy-reason>`。
- `plan_reconciliation` 已有 taxonomy 防呆：
  `deferred:later`、`deferred:todo`、`deferred:pending`、`deferred:soon`、
  `deferred:tbd` 這類空泛理由會被拒絕。
- `docs/structured-memory-freshness-policy.md` 已定義 structured memory freshness
  是 event-driven contradiction，不是年齡；目前 posture 是 manual,
  event-driven comparison，沒有 writer、hook、validator 或 automation。
- `PLAN.md` 仍明確保留 standing constraint：
  不得宣稱 daily memory writer completion 已經解決 structured memory sync。

因此，這個 spec 不是發明新的治理概念；它是把已存在的
`plan_reconciliation` declaration pattern 推廣到 repo-local structured memory
surfaces，但第一版只做 warning-only summary。

## Target Outcome

未來若另行批准 implementation，第一個實作 tranche 應提供：

- 一個 read-only summary 或 writer-side declaration surface，名稱候選：
  `structured_memory_disposition`。
- 每個 repo-local 宣告的 structured memory file 都有一個 disposition：
  `updated | not_applicable | deferred:<taxonomy-reason>`。
- `deferred:<taxonomy-reason>` 重用 P1-D reason taxonomy 與 vacuous-reason 防呆。
- 第一版全部 warning-only：不阻擋 commit、push、closeout、memory completion。
- 報告必須能用人看得懂的語言說明：
  - 哪些 structured memory surfaces 已處置；
  - 哪些不適用；
  - 哪些合法延後；
  - 哪些沒有宣告，因此可能是 silent drift。

## Scope

本 docs-only slice 只新增本 tech-spec：

- `docs/governance/structured-memory-disposition-summary-tech-spec-2026-07-01.md`

未來 implementation tranche 若另行批准，建議允許的最小實作範圍是：

- 一個 read-only checker 或 summary helper，例如
  `governance_tools/structured_memory_disposition.py`；
- focused tests，例如 `tests/test_structured_memory_disposition.py`；
- 必要時，更新 `governance/MEMORY_PROTOCOL.md` 的 advisory wording，說明
  structured memory disposition summary 是 evidence surface，不是 enforcement。

## Non-Goals

本 slice 不做：

- 不修改 `governance_tools.memory_record` runtime；
- 不修改 `daily_memory_guard.py`；
- 不修改 `memory_authority_guard.py`；
- 不修改 `memory_workflow.py`；
- 不修改 pre-commit 或 pre-push hook；
- 不新增 CI gate；
- 不新增 blocking enforcement；
- 不改 `memory/**`；
- 不改 `PLAN.md`；
- 不碰 consuming repo；
- 不硬編任何 consuming repo 的 `00-04` memory 檔名；
- 不宣稱 structured memory sync 已自動解決；
- 不宣稱 daily memory writer 可以代表 structured memory 已同步。

## Affected Surfaces

本 slice 直接影響：

- `docs/governance/structured-memory-disposition-summary-tech-spec-2026-07-01.md`

未來 implementation 可能影響，但本 slice 不授權修改：

- `governance_tools/structured_memory_disposition.py`
- `tests/test_structured_memory_disposition.py`
- `governance/MEMORY_PROTOCOL.md`
- `governance_tools/memory_record.py`
- `governance_tools/memory_workflow.py`
- `governance_tools/daily_memory_guard.py`
- `governance_tools/memory_authority_guard.py`
- managed hook templates
- consuming repo memory files

## Boundary And API Considerations

### Repo-local manifest rule

Framework 不能硬編 structured memory filenames。

本 repo 的 current canonical long-term memory shape 是：

```text
memory/00_long_term.md
```

其他 consuming repos 可能使用：

```text
memory/00_master_plan.md
memory/01_active_task.md
memory/02_tech_stack.md
memory/03_knowledge_base.md
memory/04_review_log.md
```

因此，未來 implementation 必須從 repo-local manifest 讀取 structured memory
surface 清單，而不是在 framework 裡寫死檔名。

Manifest shape 候選：

```yaml
structured_memory:
  files:
    - path: memory/01_active_task.md
      role: active_task
      required_disposition: true
    - path: memory/03_knowledge_base.md
      role: knowledge_base
      required_disposition: true
```

Manifest 位置候選：

- `.governance/baseline.yaml` 的 future extension；或
- `contract.yaml` / repo-local governance config 的 memory section；或
- 一個 explicit CLI input，例如 `--manifest <path>`。

第一版 implementation 應優先選擇 repo 已有的 baseline/config path；不得新增平行
authority file，除非 tech-spec review 先確認沒有合適既有承載面。

### Disposition vocabulary

允許值應重用 P1-D pattern：

| value | meaning |
| --- | --- |
| `updated` | 這次 slice 已同步該 structured memory surface。 |
| `not_applicable` | 這次 slice 不影響該 structured memory surface。 |
| `deferred:<taxonomy-reason>` | 這次確認需要處置，但合法延後，且理由屬於 taxonomy。 |
| `not_declared` | 未宣告；第一版只產生 warning，不阻擋。 |

不建議新增 `needs_update` 作為終止態。

理由：`needs_update` 容易變成新的 silent drift。Agent 每次都可以寫
`needs_update`，但永遠不真正更新或合法延後。若未來真的需要這個狀態，它必須是
短期 transitional state，且需要獨立 aging / repeated-warning 規則；不應列入第一版。

### Taxonomy reuse

第一版應直接重用 `memory_record.py` 的 deferred taxonomy：

- `requires-human-plan-review`
- `awaiting-reviewer-verdict`
- `scope-split-next-slice`
- `canonical-update-not-authorized`
- `dirty-workspace-prevents-safe-edit`

空泛理由仍應拒絕或標為 malformed：

- `later`
- `todo`
- `pending`
- `soon`
- `tbd`

Taxonomy extension 必須走 PR / review，不應讓 agent 任意新增 prose reason。

### Warning-only first

第一版所有 findings 都是 advisory：

```json
{
  "claim_class": "advisory",
  "blocking": false,
  "enforcement": "none"
}
```

即使出現 `not_declared`、malformed disposition 或 missing manifest，也不得直接
fail closed。這沿用 memory authority guard Phase 1 的教訓：先觀測與降低 false
positive，再討論 blocker。

## Claim Ceiling

本 tech-spec 可宣稱：

- 已定義 proposed structured memory disposition summary 的問題、範圍和非目標；
- 已確認 current repo 的 daily writer / daily guard 不會自動同步 structured memory；
- 已建議重用 P1-D `plan_reconciliation` taxonomy；
- 已建議第一版 warning-only；
- 已要求 repo-local manifest，避免硬編 consuming repo memory filenames。

本 tech-spec 不可宣稱：

- structured memory disposition summary 已實作；
- any hook / pre-push / CI / closeout gate 已改變；
- structured memory sync 已解決；
- consuming repo 的 `00-04` memory 模型已被 framework 正式支援；
- `needs_update` aging 或 blocker 已存在；
- daily memory writer completion 等於 structured memory 同步完成。

## Failure Paths Or Risk Points

- **Silent drift persists:** 如果只有 daily memory writer，structured memory 仍可過期。
- **`needs_update` abuse:** 若把 `needs_update` 當合法終止態，agent 可永久延後。
- **Filename lock-in:** 若 framework 硬編 `00-04` 檔名，會不符合本 repo 的
  `00_long_term.md` schema，也會壓過 consuming repo-local 設計。
- **False positives:** 第一版若直接擋 push，會把缺 manifest 或暫時未宣告誤當成
  violation，重演過早 fail-closed 的風險。
- **Parallel authority:** 新增 manifest 時若不復用既有 baseline/config path，可能產生
  第二套 memory authority list。
- **Claim inflation:** summary 只能證明 disposition 被宣告，不證明 memory content
  semantically correct。

## Evidence Plan

本 docs-only slice 的 evidence：

- `git diff --check -- docs/governance/structured-memory-disposition-summary-tech-spec-2026-07-01.md`
- sub-agent read-only review：檢查 scope、non-goals、warning-only posture、
  taxonomy reuse、repo-local manifest rule，以及 claim ceiling。

未來 implementation tranche 的 focused tests 應至少覆蓋：

- clean manifest + all files `updated`；
- all files `not_applicable`；
- one file `deferred:scope-split-next-slice`；
- `deferred:later` rejected or reported malformed；
- one manifest-declared file missing disposition -> `not_declared` warning；
- no manifest -> warning-only `manifest_missing`；
- consuming repo-style `00-04` manifest without hard-coded filenames；
- framework repo-style `00_long_term.md` manifest without hard-coded filenames；
- output has `blocking=false` and does not exit non-zero by default。

## Implementation Tranche Recommendation

Recommended next tranche, only after this spec is reviewed:

```text
DONE = implement read-only structured_memory_disposition reporter;
input repo-local manifest; reuse plan_reconciliation taxonomy;
emit warning-only JSON/human summary; focused tests only;
do not modify memory_record runtime, hooks, CI, closeout, or consuming repos.
```

Deferred options, not commitments:

- Add optional closeout receipt surface for structured memory disposition summary.
- Add advisory hook text when `memory/**` changes are present.
- Add aging report for repeated `not_declared` or future transitional states.
- Consider blocker only after observation window and separate OP-HC / mutation-contract review.
