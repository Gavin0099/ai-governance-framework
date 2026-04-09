# Decision Context Bridge：把 integrity signal 綁到 decision artifact

> 狀態：context bridge defined  
> 更新日期：2026-04-08

## 目的

這份文件定義一個最小 `decision_context`，讓 integrity signals 可以附著到 decision artifact 上，而不引入新的 verdict rule engine。

它要做到的是：

- 不改變 verdict 本體
- 讓 reviewer 能看見 decision 是在什麼完整度上下文中成立

## 為什麼需要這個 bridge

目前 repo 實際上有兩條系統線：

### 1. Decision System

- verdict
- trace
- DBL / `pre_task_check` / `post_task_check`
- reviewer handoff

### 2. Integrity Signal System

- runtime surface manifest
- execution coverage
- memory schema / sync signals
- advisory observations

如果這兩條線沒有被正式綁起來，就會出現：

- decision 顯示 `ok`
- execution coverage 其實不完整
- memory integrity 其實是 partial
- reviewer 卻看不出這個 decision 的成立條件

## Bridge Shape

這個 bridge 的最小形狀是：

```json
"decision_context": {
  "surface_validity": "complete | partial | unknown",
  "coverage_completeness": "complete | partial | missing",
  "memory_integrity": "complete | partial | not_applicable"
}
```

它是：

- context
- not verdict
- not policy
- not authority

## Context Fields

### 1. `surface_validity`

表示 decision 所依賴的 execution / evidence surface 是否完整、是否有 mismatch。

目前對應的 signal：

- `unknown_surfaces`
- `orphan_surfaces`
- `evidence_surface_mismatch`

### 2. `coverage_completeness`

表示目前這個 decision 所需的 execution coverage 是否已滿足。

目前對應的 signal：

- `missing_hard_required`
- `missing_soft_required`
- `dead_never_observed`
- `dead_never_required`

### 3. `memory_integrity`

表示 repo memory / host-agent memory / sync semantics 是否完整。

目前對應的 signal：

- `memory_sync_missing`
- `host_memory_not_applicable`
- `repo_memory_written_only`
- `memory_schema_status`

## Mapping Direction

這個 bridge 不做 numeric scoring，而是 bounded mapping。

### `surface_validity`

- `complete`
  - 沒有 unknown / orphan / evidence mismatch
- `partial`
  - 有 signal，但仍在 bounded interpretation 範圍內
- `unknown`
  - manifest / consistency 狀態本身不明

### `coverage_completeness`

- `complete`
  - 沒有 missing hard/soft requirement，也沒有 dead surface signal
- `partial`
  - 有 coverage 缺口，但仍可 bounded interpretation
- `missing`
  - coverage model 或 required surface 尚未建立

### `memory_integrity`

- `complete`
  - memory schema 完整，且 required sync 沒缺
- `partial`
  - schema partial、repo-only、或 sync 不完整
- `not_applicable`
  - 這次 decision 本身不要求 host memory sync

## Consumers

第一批 consumer 應是：

- reviewer
- session summary reader
- agent adoption baseline
- run record / handoff reader

目前**不是**：

- runtime stop/pass authority
- policy precedence override
- hard gate

## Current Embedding Points

目前 `decision_context` 已附著在：

- runtime verdict / trace artifact
- `session_end` summary
- reviewer-facing baseline / run record surfaces

這樣 reviewer 在看 decision validity 時，不必只看到 raw signal，也能知道 decision 是在什麼 bounded integrity context 下成立。

## Non-Goals

這個 bridge 目前不是：

- trust score
- numeric confidence score
- automatic verdict downgrade
- runtime hard gate
- policy override

## Success Condition

這個 bridge 成功的標準不是更多欄位，而是：

- reviewer 能看出 decision 的完整度上下文
- adoption / run baseline 不再只記 raw signal
- decision artifact 能附帶 bounded validity context，而不偷帶新的 authority

## 一句話總結

這個 bridge 做的不是把 signal 變成 verdict，而是讓 verdict 不再脫離 execution / coverage / memory 的完整度上下文。
