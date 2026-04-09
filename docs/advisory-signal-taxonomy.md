# Advisory Signal Taxonomy：advisory 訊號分類與使用邊界

## 目的

這份 taxonomy 的目的不是增加 detection coverage，而是統一 advisory signal 的語義分類、限制其可用範圍，並防止 advisory 訊號被誤當成 compliance proof、violation proof 或 final verdict input。

這份文件只定義 advisory family 的權限邊界，不新增 runtime authority，也不修改既有 verdict semantics。

## Signal Classes

### `degradation_advisory`

代表 runtime 可見性、上下文完整性或讀取完整性下降。

特徵：
- 主要來自 environment / runtime state
- 可進 reviewer trace 與 trace annotation
- 不應被重解讀為 behavioral failure

目前例子：
- `context_degraded`
- `require_full_read_for_large_files`

### `behavioral_advisory`

代表外部可觀測行為與某個 requirement 不相容，但不足以證明違規。

特徵：
- 依賴 observable proxy
- 屬於 compatibility evidence，不是 compliance proof
- 不可直接升格為 verdict authority

目前 first slice 尚未正式納入穩定的 `behavioral_advisory` signal。

### `evidence_advisory`

代表裁決、驗證或 reviewer reconstruction 所需證據不足、缺失或不可用。

特徵：
- 接近 execution completeness 問題
- 可能與既有 escalation path 相鄰
- 雖屬 advisory family，但可能已在其他 runtime 路徑中具有既有作用

目前例子：
- `required_evidence_missing`

## Allowed Uses

advisory signal 目前可以被用在：

- reviewer trace
- human-readable warning
- session / run record
- reviewer 警戒提升
- observation / instrumentation 設計是否要補強的依據

advisory signal 目前不應被用來直接擴張 runtime authority。

## Disallowed Uses

advisory signal 不可被當成：

- `proof_of_compliance`
- `proof_of_violation`
- final verdict 的單獨依據
- 在沒有額外 evidence 的情況下升格成 hard gate
- 將 environment degradation 重新詮釋成 behavioral failure

## Decision Distance

`decision_distance` 用來描述 advisory signal 與 decision / enforcement 的距離：

- `far`
  - 適合 reviewer-visible warning 或 trace annotation
- `near`
  - 可以提升 reviewer 警戒，但不直接改變 verdict
- `adjacent`
  - 接近 enforcement，但不能單獨作為 proof
- `enforced_elsewhere`
  - 屬於 advisory family，但其決策意義已由其他 runtime path 處理

## Current Signals Mapping

| Signal | Class | Producer | Current consumer | Decision distance | Allowed uses | Disallowed uses | Notes |
|---|---|---|---|---|---|---|---|
| `context_degraded` | `degradation_advisory` | `pre_task_check` 與 runtime injection snapshot trigger | `pre_task_check` human output / reviewer trace | `enforced_elsewhere` | escalation context / reviewer warning / trace | compliance proof / violation proof / 單獨裁決 | 代表 runtime state degradation，不是 consumption proof |
| `required_evidence_missing` | `evidence_advisory` | decision-boundary / runtime injection trigger | `pre_task_check` human output / reviewer trace | `enforced_elsewhere` | escalate / stop path / reviewer 的 evidence completeness interpretation | 只被視為 reviewer hint；不可作 behavioral compliance proof | 雖屬 advisory family，但與 escalation / stop 路徑相鄰 |
| `require_full_read_for_large_files` | `degradation_advisory` | `runtime_injection_observation.py` | `pre_task_check` consumption observation / human output / reviewer trace | `far` | advisory observation / warning / trace annotation | `proof_of_compliance` / `proof_of_violation` / edit legitimacy gate | 只表示 large-file visibility / coverage 風險，不代表 relevant section coverage |

## Non-Equivalence Rules

必須明確禁止以下推論：

- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single-event presence ≠ behavioral compliance
- environment degradation ≠ behavioral failure

## Current Posture

目前 advisory slice 的 posture 是：

- snapshot 已存在
- runtime 已消費 snapshot
- executable advisory proxy 已落地
- observation 已進 reviewer surface

但目前仍然**不是**：

- generic compliance proof
- direct verdict coupling from advisory proxy
- hard gate based on advisory-only signal

如果之後要讓 advisory signal 進一步影響 consumer，應先重新確認其權限邊界，而不是直接擴張 authority。
