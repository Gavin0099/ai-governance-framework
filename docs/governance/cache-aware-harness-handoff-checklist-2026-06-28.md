# 快取感知 Harness 交接檢查清單 - 2026-06-28
> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.


狀態（Status）：`PENDING`
範圍（Scope）：docs-only harness handoff checklist
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
強制執行（enforcement）變更：否
提示快取強制執行（prompt cache enforcement）：不宣稱

## 目的

本檢查清單整理外部代理框架（agent harness）若要採用本組快取感知
（cache-aware）規格，必須提供哪些 evidence。

本文件承接下列候選規格：

- `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`
- `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md`
- `docs/governance/cache-aware-tool-denial-receipt-spec-2026-06-28.md`
- `docs/governance/cache-aware-compaction-summary-field-spec-2026-06-28.md`

這份文件不是 adoption receipt，不是 runtime gate，也不是 prompt cache implementation。
它只定義：外部 harness 若聲稱採用這組規格，至少應帶回哪些可稽核證據。

## 核心原則

```text
採用宣稱必須有 evidence。
快取行為必須由 harness 或 provider 證明。
repo 文件不能自行升格成 runtime enforcement。
```

本儲存庫可以描述規格與檢查清單。
本儲存庫不能單獨證明外部 harness 已採用、已執行、已監控或已阻擋不安全行為。

## 最小 Handoff Packet

外部 harness 若要聲稱「已採用本組 cache-aware 規格」，最小交接包應包含：

```text
CACHE_AWARE_HARNESS_HANDOFF_PACKET v0.1
repo:
head:
base_ref:
harness_name:
harness_version:
generated_at:
authority_manifest:
stable_prefix_source_refs:
dynamic_tail_source_refs:
mode_authorization_receipts:
tool_denial_receipts:
compaction_summary:
cache_miss_classification:
runtime_enforcement_claim:
prompt_cache_behavior_claim:
non_claims:
evidence_refs:
harness_dependent: true
repo_enforces_runtime: false
repo_enforces_prompt_cache: false
```

這個 packet 是候選交接形狀，不是現有 artifact 或正式 schema。

## 必要 Evidence

### 1. Authority Manifest：權威清單

必須提供：

```text
authority_manifest:
  manifest_version:
  authority_files:
  authority_hashes:
  base_ref:
  head:
  manifest_hash:
  invalidates_cache_on_change:
```

檢查重點：

- 是否對齊 `AUTHORITY_MANIFEST v1` 候選欄位；
- 是否列出 `AGENTS.md` 與相關 `governance/` 權威文件；
- 是否能判斷權威文件改變時需要強制失效；
- 是否避免把 `generated_at` 放進穩定前綴。

不得宣稱：

- 權威清單已由本儲存庫 runtime 產生；
- 權威清單存在就代表 prompt cache 已安全啟用。

### 2. Stable / Dynamic Source Refs：穩定與動態來源參照

必須提供：

```text
stable_prefix_source_refs:
  source:
  path:
  hash:
  authority_class:
  claim_ceiling:

dynamic_tail_source_refs:
  source:
  current_head:
  git_status_ref:
  user_done_ref:
  review_receipt_ref:
  authorization_ref:
```

檢查重點：

- 穩定前綴只放耐久、可雜湊、可重新取得的權威；
- 動態尾端保留 `HEAD`、dirty-tree、review、authorization 與最新 user `DONE`；
- 使用者授權狀態沒有被折疊進穩定前綴；
- 動態來源改變時會觸發重新驗證。

不得宣稱：

- source refs 本身證明 cache hit rate；
- source refs 本身授權 push、memory write 或 cross-repo write。

### 3. Mode / Authorization Receipts：模式與授權回執

必須提供與任務相符的候選 receipt 或等價 evidence：

```text
mode_authorization_receipts:
  mode_state_receipt:
  push_authorization_receipt:
  memory_write_authorization_receipt:
  cross_repo_write_authorization_receipt:
  destructive_action_authorization:
```

檢查重點：

- 使用者自然語言只作為請求或授權來源參照，不直接成為 machine-acceptable state；
- push 授權應限定 commit、remote、branch，且預設 single-use；
- memory write 授權不取代 `governance/MEMORY_PROTOCOL.md` 或標準寫入器；
- cross-repo write 授權必須明確目標 repo、允許路徑與 preflight；
- destructive action 必須有獨立明確授權。

不得宣稱：

- 文件中的 receipt 範例等於現有 runtime schema；
- sub-agent review 可以自行發行 push 或 memory write 授權。

### 4. Tool Denial Receipts：工具拒絕回執

必須提供：

```text
tool_denial_receipts:
  tool:
  requested_action:
  side_effect_class:
  denied_by:
  denial_reason:
  authority_ref:
  requires_user_authorization:
```

檢查重點：

- 工具可見性沒有被當成工具執行授權；
- 工具拒絕不是靜默失敗；
- denial evidence 可以區分 mode denied、authorization missing、scope denied、sandbox denied 等原因；
- 工具拒絕 receipt 沒有被升格成授權 receipt。

不得宣稱：

- `TOOL_DENIAL_RECEIPT` 已由本儲存庫 runtime 產生；
- 工具拒絕已被 machine-enforced，除非 harness 提供獨立 evidence。

### 5. Compaction Summary：壓縮摘要

必須提供：

```text
compaction_summary:
  authority_state:
  evidence_state:
  dirty_tree_state:
  review_receipt_state:
  claim_ceiling:
  not_claimed:
  authorization_state:
  next_allowed_action:
  next_forbidden_action:
```

檢查重點：

- 壓縮摘要保留權威、證據、dirty-tree、review、宣稱與授權邊界；
- review approval 沒有被壓縮成 push approval；
- `not_claimed` 沒有被省略；
- next allowed action 與 next forbidden action 分開；
- dirty residual 或 excluded scope 沒有被壓掉。

不得宣稱：

- 壓縮摘要已被 runtime machine-enforced；
- 壓縮摘要可以取代原始 receipt。

### 6. Cache Miss Classification：快取未命中分級

必須提供：

```text
cache_miss_classification:
  miss_type:
  trigger:
  expected_or_incident:
  authority_or_permission_changed:
  evidence_ref:
```

檢查重點：

- authority / permission / freshness 改變造成的 miss 被標為 expected；
- tool schema order、timestamp in stable prefix 等非預期震盪才標為 incident；
- model switch、provider TTL、short task miss 有各自合理分類；
- cache miss 分級不被用來責備正確的安全失效。

不得宣稱：

- 本儲存庫能測量 cache hit rate；
- 本儲存庫能判斷 provider cache key 或 TTL。

### 7. Runtime Enforcement Non-Claim：執行環境強制執行不可宣稱

必須提供：

```text
runtime_enforcement_claim:
  runtime_enforced: false | harness_reported | runtime_gate_reported
  enforcement_evidence_ref:
  repo_claim: docs_only

prompt_cache_behavior_claim:
  prompt_cache_implemented: false | harness_reported | provider_reported
  cache_behavior_evidence_ref:
  repo_claim: docs_only
```

檢查重點：

- `runtime_enforced: false` 是預設；
- `prompt_cache_implemented: false` 是預設；
- runtime enforcement 只能由 harness 或 runtime gate evidence 支持；
- prompt cache behavior 可以由 harness 或 provider evidence 支持；
- repo 文件不得自行升格 claim。

不得宣稱：

- repo-local docs 已經等於 runtime enforcement；
- PENDING spec 已經等於 harness adoption。

## Handoff Review Questions

審查外部 harness adoption claim 時，至少問：

1. 哪些 authority files 被載入？hash 是什麼？
2. 哪些內容在 stable prefix？哪些在 dynamic tail？
3. 哪些權威、權限或 freshness 變更會強制失效？
4. 使用者授權如何從自然語言請求轉成 typed state？
5. 工具可見但被拒絕時，是否留下 denial evidence？
6. 壓縮摘要是否保留 `claim_ceiling` 與 `not_claimed`？
7. review approval 是否被誤升格成 push authorization？
8. cache miss 是 expected safety/freshness/permission miss，還是 incident？
9. runtime enforcement claim 的 evidence 來自哪裡？
10. prompt cache behavior claim 的 evidence 來自哪裡？

若任何答案缺少 evidence，handoff claim 應降級為 `docs_aligned_only`。

## Handoff Verdict Labels

候選 verdict：

| Verdict | 中文主稱 | 意義 |
| --- | --- | --- |
| `docs_aligned_only` | 僅文件對齊 | harness 尚未提供採用或 runtime evidence |
| `harness_claimed` | harness 自稱採用 | harness 提供 adoption claim，但 evidence 尚未完整 |
| `evidence_supported` | 證據支持 | adoption claim 有足夠 refs，可供 review |
| `runtime_enforced` | 執行環境已強制 | 需外部 runtime evidence；repo 不可自行宣稱 |
| `provider_reported_cache` | provider 回報快取 | 需 provider 或 harness cache evidence |
| `rejected` | 拒絕 | claim 缺少必要 evidence 或越界 |

預設 verdict 是 `docs_aligned_only`。

## 與外部框架的責任分界

本儲存庫可以定義：

- handoff packet 候選欄位；
- harness adoption 需要哪些 evidence；
- 哪些 claim 必須由 harness 或 provider 提供；
- runtime enforcement 與 prompt cache implementation 的不可宣稱邊界。

本儲存庫不能保證：

- 外部 harness 已採用；
- 外部 harness 已產生 receipt；
- 外部 harness 已阻擋不安全副作用；
- prompt cache 已實作；
- cache hit rate 已被監控；
- runtime gate 已實作；
- provider 行為符合本文件假設。

因此所有 handoff packet 都必須保留：

```text
harness_dependent: true
repo_enforces_runtime: false
repo_enforces_prompt_cache: false
```

## 非目標

本檢查清單不做以下事情：

- 不修改 runtime；
- 不修改 tests；
- 不修改 PLAN；
- 不修改 artifacts；
- 不修改 `governance_tools/`；
- 不新增工具或工具 schema；
- 不新增正式 schema；
- 不實作 prompt cache；
- 不監控 cache hit rate；
- 不新增 harness integration；
- 不宣稱外部 harness 已採用本組 specs；
- 不宣稱 runtime enforcement；
- 不宣稱 prompt cache implementation。

## 可行下一步

如果本檢查清單經審查維持可行，後續可以拆成獨立 docs-only 切片：

1. receipt alignment note：確認 handoff packet 與 review / closeout / response envelope 的引用方式；
2. operator checklist：把 cache-aware 文件轉成日常操作檢查清單；
3. implementation readiness review packet：若要開始 runtime / harness integration，先準備給 Claude 或 human reviewer 的高風險 review packet。

在這些切片完成前，本文件維持 `PENDING`。

## 宣稱上限

本文只能宣稱：

- proposed cache-aware harness handoff checklist；
- proposed evidence requirements for authority manifest, source refs, mode/auth receipts, tool denial receipts, compaction summary, cache miss classification, and non-claims；
- harness-dependent boundary remains explicit；
- repo does not claim runtime enforcement；
- repo does not claim prompt cache implementation；
- no runtime/tests/PLAN/artifacts behavior changed。

本文不得宣稱：

- 外部 harness 已採用本組 specs；
- prompt cache 已實作；
- cache hit rate 已被監控；
- runtime gate 已實作；
- receipt schema 已正式存在於執行環境；
- tool permission policy 已改變；
- 本文件可授權任何實際副作用。
