# Decision Context Bridge

## 目的

這份文件定義一個最小橋接層，將目前已存在的：

- execution surface signals
- coverage completeness signals
- memory integrity signals

正式綁到 decision artifact 的語義中。

目標不是改 verdict，也不是增加新的 rule engine。

目標是：

> 讓每個 decision 都能明確說出：
> 它是在什麼完整度上下文下做出的。

## 問題定義

目前 repo 已經有兩條並行系統：

### 1. Decision System

- verdict
- trace
- DBL / pre_task / post_task
- reviewer handoff

### 2. Integrity Signal System

- runtime surface manifest
- execution coverage
- memory schema / memory sync signals

現在的問題不是缺 signal，而是：

> signal 還沒有正式進入 decision artifact。

所以目前可能出現：

- decision = ok
- 但 execution coverage incomplete
- 但 memory integrity partial
- 但 reviewer 不知道這些 signal 對該 decision 的可信度代表什麼

## 最小橋接做法

第一版只加一個欄位：

```json
"decision_context": {
  "surface_validity": "complete | partial | unknown",
  "coverage_completeness": "complete | partial | missing",
  "memory_integrity": "complete | partial | not_applicable"
}
```

這個欄位的定位是：

- context
- not verdict
- not policy
- not enforcement

## 三個 Context 維度

### 1. `surface_validity`

回答：

- 目前 decision 所依賴的 execution/evidence surface 是否完整且沒有明顯 mismatch

第一版 signal 來源可接：

- `unknown_surfaces`
- `orphan_surfaces`
- `evidence_surface_mismatch`

### 2. `coverage_completeness`

回答：

- 目前 decision 是否在可接受的 execution coverage 下做出

第一版 signal 來源可接：

- `missing_hard_required`
- `missing_soft_required`
- `dead_never_observed`
- `dead_never_required`

### 3. `memory_integrity`

回答：

- 目前與該 decision 相關的 repo memory / host-agent memory 狀態是否完整

第一版 signal 來源可接：

- `memory_sync_missing`
- `host_memory_not_applicable`
- `repo_memory_written_only`
- `memory_schema_status`

## 第一版 Mapping 原則

第一版不要做複雜加權或 scoring。

只做最小 mapping：

### `surface_validity`

- `complete`
  - 無 `unknown_surfaces`
  - 無 `orphan_surfaces`
  - 無 `evidence_surface_mismatch`
- `partial`
  - 任一 signal 非空
- `unknown`
  - 無法取得 manifest / consistency 結果

### `coverage_completeness`

- `complete`
  - `missing_hard_required=0`
  - `missing_soft_required=0`
  - 無 dead surface signal
- `partial`
  - 任一 coverage signal 非空
- `missing`
  - coverage model 未執行或 decision 無 coverage result

### `memory_integrity`

- `complete`
  - memory schema complete
  - 無 required sync missing
- `partial`
  - schema partial
  - 或只有 repo memory，沒有 host sync
- `not_applicable`
  - 這個 decision/track 不要求 host memory sync

## 第一版 Consumer

第一版只服務三個 consumer：

1. reviewer
2. agent adoption baseline
3. future session_end / verdict artifact readers

先不要讓它直接影響：

- runtime stop/pass
- policy precedence
- authority escalation

## 建議落點

第一版最適合加在：

- `runtime-verdict`
- `session_end` summary output
- reviewer / adoption run record

不一定要一次全接。

最小路徑可以是：

1. 先定 schema
2. 先在一個非阻擋 artifact 出現
3. reviewer 先消費

## 非目標

第一版不做：

- trust score
- numeric confidence score
- automatic verdict downgrade
- runtime hard gate
- policy override

## 驗收條件

第一版完成時，至少要滿足：

1. `decision_context` 不重寫現有 verdict semantics
2. reviewer 能看出：
   - decision 是在完整、部分、或未知上下文中做出
3. context 值可回溯到既有 signal，而不是新發明的黑箱評分
4. agent-assisted baseline 能引用這個 context，而不只引用 raw signal

## 一句話總結

> 這一步的目的不是讓 signal 變 verdict，
> 而是讓 verdict 有正式可引用的完整度上下文。
