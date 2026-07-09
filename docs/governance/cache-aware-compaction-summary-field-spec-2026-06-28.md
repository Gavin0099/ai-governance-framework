# 快取感知壓縮摘要欄位規格 - 2026-06-28

> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.

狀態（Status）：`PENDING`
範圍（Scope）：docs-only compaction summary field design
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 目的

本規格承接下列文件：

- `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`
- `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md`
- `docs/governance/cache-aware-tool-denial-receipt-spec-2026-06-28.md`

前面幾份文件定義穩定前綴（stable prefix）、動態尾端（dynamic tail）、權威清單
（authority manifest）、授權防偽與工具拒絕回執。本文件處理另一個長任務代理
框架（agent harness）常見邊界：壓縮摘要（compaction summary）不能只追求短，
也必須保留治理語意。

壓縮摘要若丟失權威、證據、工作樹、審查回執、宣稱上限、不可宣稱、授權狀態與
下一步邊界，後續工作可能看起來更省 token，卻更容易產生過度宣稱或錯誤副作用。

本文件不實作壓縮摘要，不實作提示快取（prompt caching），不新增 runtime gate，
不新增 schema，不修改任何測試或 artifact。

## 核心原則

```text
壓縮可以丟細節。
不能丟權威、證據、授權與宣稱邊界。
```

好的壓縮摘要應該讓下一個代理可以回答三個問題：

1. 目前能安全相信什麼？
2. 目前不能宣稱什麼？
3. 下一步允許做什麼、禁止做什麼？

若摘要無法回答這三個問題，它不應被視為治理可用的壓縮摘要。

## `CACHE_AWARE_COMPACTION_SUMMARY v0.1`

`CACHE_AWARE_COMPACTION_SUMMARY v0.1` 是候選欄位規格，用於描述外部框架若要壓縮
長任務上下文，應保留哪些治理欄位。它不是現有 artifact，也不是現有 schema。

```text
CACHE_AWARE_COMPACTION_SUMMARY v0.1
repo:
head:
base_ref:
summary_generated_at:
summary_generated_by:
authority_state:
evidence_state:
dirty_tree_state:
review_receipt_state:
claim_ceiling:
not_claimed:
authorization_state:
tool_denial_state:
memory_state:
validation_state:
committed_scope:
uncommitted_scope:
excluded_scope:
next_allowed_action:
next_forbidden_action:
open_risks:
staleness_triggers:
source_summary_refs:
harness_dependent: true
repo_enforces_runtime: false
repo_enforces_prompt_cache: false
```

欄位語意：

| 欄位 | 中文主稱 | 說明 |
| --- | --- | --- |
| `repo` | 儲存庫 | 摘要適用的儲存庫 |
| `head` | 目前提交 | 摘要產生時的 `HEAD` |
| `base_ref` | 基準參照 | 本輪工作使用的 base branch、remote ref 或 commit |
| `summary_generated_at` | 摘要產生時間 | 動態尾端欄位，不應污染穩定前綴 |
| `summary_generated_by` | 摘要產生者 | 產生摘要的框架、工具或代理 |
| `authority_state` | 權威狀態 | 目前採用的指令、治理文件與權威雜湊摘要 |
| `evidence_state` | 證據狀態 | 已檢查命令、檔案、artifact、review 證據與結果 |
| `dirty_tree_state` | 工作樹狀態 | tracked / untracked / staged / excluded dirty scope |
| `review_receipt_state` | 審查回執狀態 | sub-agent 或 reviewer 的 verdict、scope 與 claim ceiling |
| `claim_ceiling` | 宣稱上限 | 目前證據能支持的最強宣稱 |
| `not_claimed` | 不可宣稱 | 明確不得宣稱或尚未驗證的內容 |
| `authorization_state` | 授權狀態 | push、memory write、cross-repo write、destructive action 等授權 |
| `tool_denial_state` | 工具拒絕狀態 | 最近相關 `TOOL_DENIAL_RECEIPT` 或拒絕證據 |
| `memory_state` | 記憶狀態 | 是否已寫記憶、是否需要標準寫入器、是否未授權 |
| `validation_state` | 驗證狀態 | 已跑、未跑、失敗或不適用的檢查 |
| `committed_scope` | 已提交範圍 | 已提交且可引用的變更範圍 |
| `uncommitted_scope` | 未提交範圍 | 尚未提交、不能被當作完成狀態的變更 |
| `excluded_scope` | 排除範圍 | 明確不讀、不改、不 stage 的檔案或目錄 |
| `next_allowed_action` | 下一個允許動作 | 下一步可直接做的最窄動作 |
| `next_forbidden_action` | 下一個禁止動作 | 下一步仍需授權或不得執行的動作 |
| `open_risks` | 未解風險 | 仍需審查、驗證或使用者決策的風險 |
| `staleness_triggers` | 過期觸發 | 會使摘要失效或需要重新讀取的條件 |
| `source_summary_refs` | 摘要來源參照 | 原始對話、receipt、artifact 或 commit 參照 |

## 必保留欄位群

壓縮摘要可以縮短敘事，但下列欄位群不得被完全省略。

### Authority：權威

必保留：

```text
authority_state:
  loaded_authority_files:
  authority_hashes:
  authority_manifest_ref:
  active_repo:
  workspace_boundary:
  governance_protocols_loaded:
```

目的：

- 避免把舊 `AGENTS.md`、舊治理協議或錯誤 repo 邊界帶到下一輪；
- 保留哪些規則有權決定下一步；
- 讓後續代理知道何時必須重新讀取權威文件。

### Evidence：證據

必保留：

```text
evidence_state:
  commands_run:
  files_checked:
  artifacts_checked:
  validation_results:
  review_evidence:
  evidence_gaps:
```

目的：

- 避免把「曾經討論」誤當成「已驗證」；
- 保留 pass / fail / not run / unknown 狀態；
- 讓宣稱能對回實際證據。

### Dirty Tree：工作樹

必保留：

```text
dirty_tree_state:
  tracked_status:
  staged_status:
  untracked_status:
  excluded_dirty_paths:
  dirty_status_command:
  source_clean_evidence:
```

目的：

- 避免在有未提交或未追蹤檔案時宣稱整體完成；
- 保留哪些 dirty path 被明確排除；
- 避免下一輪代理讀、改、stage 不該碰的 residual。

### Review Receipt：審查回執

必保留：

```text
review_receipt_state:
  reviewer:
  verdict:
  scope:
  blocking_findings:
  required_fixes:
  evidence_checked:
  claim_ceiling:
  push_gate:
```

目的：

- 避免把 review approval 擴張成 push approval；
- 保留審查者實際檢查的 scope；
- 讓 required fixes 不會在壓縮後消失。

### Claim Ceiling：宣稱上限

必保留：

```text
claim_ceiling:
  strongest_supported_claim:
  scope_boundary:
  evidence_boundary:
  time_boundary:
  dirty_tree_boundary:
```

目的：

- 防止從「docs-only candidate」漂移成「runtime implemented」；
- 防止從「review-approved local commit」漂移成「remote verified」；
- 防止從「observation」漂移成「enforcement」。

### `not_claimed`：不可宣稱

必保留：

```text
not_claimed:
  runtime_enforcement:
  prompt_cache_implementation:
  harness_adoption:
  semantic_correctness:
  push_authorization:
  memory_write_authorization:
  cross_repo_write_authorization:
```

目的：

- 明確列出目前不能說的話；
- 讓下一輪代理不會因摘要變短而升格宣稱；
- 保留 response envelope 的不可宣稱邊界。

### Authorization State：授權狀態

必保留：

```text
authorization_state:
  mode_state:
  push_authorization:
  memory_write_authorization:
  cross_repo_write_authorization:
  destructive_action_authorization:
  authorization_expiry:
  authorization_source:
```

目的：

- 避免把使用者自然語言轉述誤當成機器可接受授權；
- 確認 push / memory / cross-repo / destructive action 是否仍需明確授權；
- 避免 single-use authorization 被重用。

### Next Action：下一步邊界

必保留：

```text
next_allowed_action:
  action:
  scope:
  allowed_files:
  validation:
  commit_intent:
  push_intent:

next_forbidden_action:
  action:
  reason:
  required_authorization:
```

目的：

- 讓下一輪代理知道是否可以繼續實作，或只能 audit-first；
- 避免 ambiguous continuation 被誤讀成 broad execution；
- 明確分開「建議下一步」與「已授權下一步」。

## 最小摘要要求

若外部框架無法保留完整欄位，最小可接受摘要至少應包含：

```text
repo:
head:
base_ref:
authority_state:
evidence_state:
dirty_tree_state:
review_receipt_state:
claim_ceiling:
not_claimed:
authorization_state:
next_allowed_action:
next_forbidden_action:
harness_dependent: true
repo_enforces_runtime: false
repo_enforces_prompt_cache: false
```

少於這些欄位的摘要，不能支持治理敏感工作的自動延續。

## 快取關係

壓縮摘要本身屬於動態尾端，不屬於穩定前綴。

原因：

- 它描述某一輪工作狀態；
- 它依賴當前 `HEAD`、dirty-tree、review receipt 與授權狀態；
- 它可能因新的 commit、push、review、memory write 或 user authorization 失效；
- 它若進入穩定前綴，可能讓過期授權或過期 evidence 被重用。

如果外部框架支援 prompt cache，壓縮摘要改變通常應視為有意新鮮度未命中或有意
權限未命中，而不是效率事故。

## 過期觸發

下列事件應使既有壓縮摘要失效或至少需要重新驗證：

| 觸發條件 | 反應 |
| --- | --- |
| `HEAD` 改變 | 重新確認 committed / uncommitted scope |
| `origin/main` 或 base ref 改變 | 重新確認 remote tracking state |
| `git status` 改變 | 重新確認 dirty-tree boundary |
| 權威文件 hash 改變 | 重新讀取權威文件 |
| review receipt 被更正或撤回 | 降低宣稱並重新 review |
| push authorization 新增、使用或過期 | 更新 authorization state |
| memory write authorization 新增、使用或過期 | 更新 memory state |
| cross-repo write authorization 新增、使用或過期 | 更新 repo boundary |
| tool denial receipt 新增或更正 | 更新 tool denial state |
| 使用者提供新的 bounded `DONE` | 更新 next allowed / forbidden action |

## 與既有回執的關係

壓縮摘要不得取代既有 receipt。

它只能引用或摘要：

- `REVIEW_RECEIPT`
- `MODE_STATE_RECEIPT`
- `PUSH_AUTHORIZATION_RECEIPT`
- `MEMORY_WRITE_AUTHORIZATION_RECEIPT`
- `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT`
- `TOOL_DENIAL_RECEIPT`
- closeout receipt
- memory record
- response envelope

若原始 receipt 與壓縮摘要衝突，應以原始 receipt 或重新讀取的權威來源為準。

## 與外部框架的責任分界

本儲存庫可以定義：

- 候選壓縮摘要欄位；
- 哪些治理語意不可被壓縮掉；
- 哪些事件應使摘要失效；
- 壓縮摘要不應承載永久授權；
- 本儲存庫不能宣稱 runtime enforcement 或 prompt cache implementation。

本儲存庫不能保證：

- 外部 harness 會產生壓縮摘要；
- 外部 harness 會保留這些欄位；
- 外部 harness 會使用相同 cache key；
- 外部 harness 會監控 cache hit rate；
- 外部 harness 會阻擋過期摘要；
- runtime gate 已實作；
- prompt cache 已實作；
- typed receipt 已存在於執行環境。

因此所有候選摘要都必須保留：

```text
harness_dependent: true
repo_enforces_runtime: false
repo_enforces_prompt_cache: false
```

## 非目標

本規格不做以下事情：

- 不修改 runtime；
- 不修改 tests；
- 不修改 PLAN；
- 不修改 artifacts；
- 不修改 `governance_tools/`；
- 不新增工具或工具 schema；
- 不新增正式 schema；
- 不實作 prompt cache；
- 不監控 cache hit rate；
- 不新增 compaction tool；
- 不宣稱外部 harness 已採用本規格；
- 不宣稱壓縮摘要已被 runtime machine-enforced；
- 不把 sub-agent review 寫成 enforcement。

## 可行下一步

如果本規格經審查維持可行，後續應拆成獨立 docs-only 切片：

1. harness handoff checklist：定義外部框架若要採用 cache-aware specs，必須提供哪些證據；
2. receipt alignment note：確認 compaction summary 與 review / closeout / response envelope 的引用方式；
3. operator checklist：把 cache-aware 文件轉成日常操作檢查清單，但仍不宣稱 runtime enforcement。

在這些切片完成前，本文件維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed `CACHE_AWARE_COMPACTION_SUMMARY v0.1` candidate fields；
- proposed required authority / evidence / dirty-tree / review receipt fields；
- proposed claim ceiling and `not_claimed` preservation；
- proposed authorization state and next action boundary preservation；
- proposed compaction staleness triggers；
- harness-dependent boundary remains explicit；
- repo does not claim runtime enforcement；
- repo does not claim prompt cache implementation；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- runtime gate 已實作；
- prompt cache 已實作；
- compaction tool 已實作；
- 外部 harness 已採用本規格；
- typed receipt 已存在於執行環境；
- 壓縮摘要已可被機器層強制驗證；
- 子代理審查已成為 runtime enforcement；
- 本文件可授權任何實際副作用。
