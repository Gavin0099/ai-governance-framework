# Advisory Signal Taxonomy：advisory signal 分類與使用邊界

## 目的

這份 taxonomy 的目的不是增加 detection coverage，而是把 advisory signal 的治理位階固定下來：

- 統一 advisory signal 的語義分類
- 限制 advisory signal 的可用範圍
- 防止 advisory 被誤當成 compliance proof、violation proof，或 final verdict input

這份 taxonomy 不會自動提升 runtime authority，也不會改寫 verdict semantics。

## Signal Classes

### Degradation Advisory

代表 runtime 可見性、上下文完整性、讀取完整性，或觀測條件本身出現下降。

特徵：

- 基礎多半來自 environment / runtime state
- 主要用途是 reviewer 警戒與 trace annotation
- 不等於 behavioral failure

目前例子：

- `context_degraded`
- `require_full_read_for_large_files`

### Behavioral Advisory

代表某些外部可觀測行為與 requirement 不相容，但證據仍不足以證明真正違規。

特徵：

- 依賴 observable proxy
- 是 compatibility evidence，不是 compliance proof
- 不能單獨升格成 verdict authority

目前 first slice 尚未正式納入可執行的 behavioral advisory signal。

### Evidence Advisory

代表裁決、驗證、或 reviewer reconstruction 所需的證據不足、缺失、或不可用。

特徵：

- 更接近 execution completeness 問題
- 與 escalation path 相鄰
- 雖屬 advisory family，但可能已有其他 runtime 路徑在處理

目前例子：

- `required_evidence_missing`

## Allowed Uses

advisory signal 目前允許的用途：

- 出現在 reviewer trace
- 出現在 human-readable warning
- 出現在 session / run record
- 提升 reviewer 警戒
- 成為後續 observation / instrumentation 是否需要補強的依據

advisory signal 不會因為可見，就自動取得 runtime authority。

## Disallowed Uses

advisory signal 目前明確禁止被拿來做：

- `proof_of_compliance`
- `proof_of_violation`
- 單獨改變 final verdict
- 在沒有額外 evidence 的情況下直接升級成 hard gate
- 把 environment degradation 重新解讀成 behavioral failure

## Decision Distance

每個 advisory signal 都要標明它離 decision / enforcement 有多近：

- `far`
  - 只適合 reviewer-visible warning / trace annotation
- `near`
  - 可提升 reviewer 警戒，但不能直接改 verdict
- `adjacent`
  - 靠近 enforcement，但仍不能單獨當作 proof
- `enforced_elsewhere`
  - 屬於 advisory family，但已有其他 runtime path 正式處理

## Current Signals Mapping

| Signal | Class | Producer | Current consumer | Decision distance | Allowed uses | Disallowed uses | Notes |
|---|---|---|---|---|---|---|---|
| `context_degraded` | `degradation_advisory` | `pre_task_check` 透過 runtime injection snapshot trigger 產生 | `pre_task_check`、human output、reviewer trace | `enforced_elsewhere` | escalation context、reviewer warning、trace | compliance proof、violation proof、單獨行為判斷 | 它描述的是 runtime state degradation，不是 consumption proof |
| `required_evidence_missing` | `evidence_advisory` | decision-boundary / runtime injection trigger | `pre_task_check`、human output、reviewer trace | `enforced_elsewhere` | escalate / stop path、reviewer 可見性、evidence completeness interpretation | 不可被壓扁成一般 reviewer hint，也不是 behavioral compliance proof | 雖屬 advisory family，但已有 escalation / stop 語義 |
| `require_full_read_for_large_files` | `degradation_advisory` | `runtime_injection_observation.py` | `pre_task_check` consumption observation、human output、reviewer trace | `far` | advisory observation、warning、trace annotation | proof_of_compliance、proof_of_violation、edit legitimacy gate | 只代表 large-file visibility / coverage 風險，不代表 relevant section coverage |

## Non-Equivalence Rules

以下推論明確禁止：

- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single-event presence ≠ behavioral compliance
- environment degradation ≠ behavioral failure

## Current Posture

目前 advisory slice 的 posture 是：

- snapshot 已存在
- runtime 已開始消費 snapshot
- executable advisory proxy 已落地
- observation 已能在 reviewer surface 被看見

但目前仍然**不是**：

- generic compliance proof
- direct verdict coupling from advisory proxy
- hard gate based on advisory-only signal

如果之後要重開這條線，必須先回答 advisory signal 是否真的出現新的 consumer 或新的誤讀風險。
