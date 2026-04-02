# Advisory Signal Taxonomy

## Purpose

這份文件的目的不是增加 detection coverage，而是先把 advisory signal 的治理位階寫死。

它負責三件事：
- 統一 advisory signal 的語義分類
- 限制 advisory signal 的可用範圍
- 防止 advisory signal 被誤當成 compliance proof、violation proof、或 final verdict input

這份 taxonomy 不新增新的 runtime authority，也不直接改變 verdict semantics。

## Signal Classes

### Degradation Advisory

代表 runtime 可見性、上下文完整性、或讀取完整性下降。

特徵：
- 比較接近 environment / runtime state
- 可以提升 reviewer 警戒
- 不等於 behavioral failure

典型例子：
- `context_degraded`
- `require_full_read_for_large_files`

### Behavioral Advisory

代表外部可觀測行為與某 requirement 不相容，但不足以證明違規。

特徵：
- 依賴 observable proxy
- 只能提供 compatibility evidence
- 不可直接升格成 compliance proof

目前 first slice 尚未有正式 executable behavioral advisory signal。

### Evidence Advisory

代表裁決、驗證、或 reviewer reconstruction 所需證據不足、缺失、或不可用。

特徵：
- 與 execution completeness 較接近
- 常與 escalation path 相鄰
- 分類為 advisory，不等於自動降級其既有 runtime 意義

典型例子：
- `required_evidence_missing`

## Allowed Uses

advisory signal 目前允許的用途：
- reviewer trace 可見
- human-readable warning 可見
- session / run record 可摘要
- 提升 reviewer 警戒
- 作為後續 observation / instrumentation 設計的依據

在明確文件化前，advisory signal 不應被擴張到更多 runtime authority。

## Disallowed Uses

advisory signal 目前不得被用於：
- `proof_of_compliance`
- `proof_of_violation`
- 單獨改變 final verdict
- 在無額外 evidence 下升級成 hard gate
- 將 environment degradation 重新解讀成 behavioral failure

## Decision Distance

為了避免 advisory signal 被誤接成裁決權，先定義一個最小距離分類：

- `far`
  - 只適合 reviewer-visible warning / trace annotation
- `near`
  - 可提升 reviewer 警戒或審查強度，但不直接改 verdict
- `adjacent`
  - 接近 enforcement，但仍不可單獨當成 proof
- `enforced_elsewhere`
  - 屬於 advisory family，但已有其他 runtime path 處理其決策效果

## Current Signals Mapping

| Signal | Class | Producer | Current consumer | Decision distance | Allowed uses | Disallowed uses | Notes |
|---|---|---|---|---|---|---|---|
| `context_degraded` | `degradation_advisory` | `pre_task_check` via runtime injection snapshot trigger | `pre_task_check`, human output, reviewer trace | `enforced_elsewhere` | escalation context, reviewer warning, trace | compliance proof, violation proof, standalone behavior judgment | 這是 runtime state degradation，不是 consumption proof |
| `required_evidence_missing` | `evidence_advisory` | decision-boundary / runtime injection trigger | `pre_task_check`, human output, reviewer trace | `enforced_elsewhere` | escalate / stop path, reviewer visibility, evidence completeness interpretation | 被重寫成單純 reviewer hint、被當成 behavioral compliance proof | 雖屬 advisory family，但已有既有 escalation / stop 語義 |
| `require_full_read_for_large_files` | `degradation_advisory` | `runtime_injection_observation.py` | `pre_task_check` consumption observation, human output, reviewer trace | `far` | advisory observation, warning, trace annotation | proof_of_compliance, proof_of_violation, edit legitimacy gate | 目前只能表示 large-file visibility / coverage 風險，不代表 relevant section coverage |

## Non-Equivalence Rules

以下推論一律禁止：

- observed proxy present ≠ requirement satisfied
- observed proxy absent ≠ requirement violated
- single event presence ≠ behavioral compliance
- environment degradation ≠ behavioral failure

## Current Posture

目前這條線的定位是：

- snapshot 已存在
- runtime 已消費部分 snapshot 欄位
- executable advisory proxy 已開始落地
- observation 可被 reviewer 看見

但尚未成立的是：

- generic compliance proof
- direct verdict coupling from advisory proxy
- hard gate based on advisory-only signal

下一步若要往前走，應優先補：
- advisory signal 的 pre/post observation boundary
- 或第二個不同型別的 advisory proxy

而不是直接把現有 advisory signal 升格成裁決依據。
