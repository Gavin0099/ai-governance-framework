# Runtime Observation Phase Boundary：observation signal 的時間邊界

> 狀態：phase semantics fixed  
> 更新日期：2026-04-09

## 目的

這份文件不是在定義 pre/post 的功能分工表，而是在定義 observation signal 在時間上何時才有資格成立。

核心問題是：

- 哪些 signal 可以在 task execution 前成立
- 哪些 signal 必須等 execution 之後才比較完整
- 哪些 signal 應該用 `pre -> post` closure pattern 理解

目前只用這三個 signal 當例子：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Phase 定義

### Pre-Task Observation

描述：

- task execution 開始前就可觀測的風險
- 前置可見性與最低條件
- snapshot-derived escalation hints

它通常代表：

- context quality
- known missing preconditions
- minimum risk posture

它**不應**假裝知道：

- edit 前有沒有 reread
- validation 最後有沒有真的跑
- execution 之後才會產生的 evidence completeness

### In-Task / Execution Observation

描述：

- execution 過程中的 read / edit / tool / validation 訊號
- file coverage、reread、validation order 等 execution-time signals

目前 repo 還沒有完整 generic in-task observation layer，但這個 phase 必須先被寫出來，避免把 execution-time signal 硬塞進 pre 或 post。

### Post-Task Observation

描述：

- task execution 之後的 evidence completeness
- behavioral compatibility
- advisory compliance proxy
- trace reconstruction

它能做的是：

- 檢查 evidence 是否真的產出
- 解讀 validator / runtime output

它不能做的是：

- 回頭宣稱 agent 一定理解 injected policy
- 把 absent observation 當作 compliance proof

## Signal Admissibility by Phase

| Signal | Pre 可成立 | In-task 可成立 | Post 可成立 | 可否影響 verdict | Notes |
|---|---|---|---|---|---|
| `context_degraded` | yes | yes | yes | indirect / enforced elsewhere | 描述 environment / context quality，不是 behavioral compliance |
| `required_evidence_missing` | partial | yes | yes | yes / enforced elsewhere | pre 只能表達 evidence 風險，post 才較完整反映 evidence completeness |
| `require_full_read_for_large_files` | weak | stronger | stronger | no, advisory only | pre 只能表示 visibility risk，post 才能較完整形成 behavioral compatibility evidence |

## Boundary Rules

- pre-task signal 不得假裝推定未來執行行為
- post-task signal 不得回溯聲稱 agent 已理解 injected policy
- absent observation 不得當作 compliance proof
- advisory signal 在任何 phase 都不得單獨改 verdict
- environment degradation signal 不得被重寫成 behavioral failure

## Current Signals

### `context_degraded`

目前主要由 `pre_task_check` 產生。

它描述的是：

- environment / context quality 下降
- escalation posture 提升
- 不是 behavioral failure

### `required_evidence_missing`

這個 signal 比一般 advisory 更靠近 execution completeness。

在 pre-task：

- 只能表示 evidence risk
- 表示這個 task 的前置條件或 reconstruction surface 不完整

在 post-task：

- 才較完整反映 evidence 是否真的齊全
- 也更接近 escalation / stop 的既有路徑，而不是單純 reviewer hint

### `require_full_read_for_large_files`

目前是一個 advisory-only executable proxy。

它描述的是：

- large-file visibility / truncation / review risk
- 不是 `proof_of_compliance`
- 不是 `proof_of_violation`
- 不是 edit legitimacy gate

## Pre/Post Closure Pattern

有些 signal 應該用這種 closure pattern 理解：

```text
pre 的風險提醒 -> post 的結果評估
```

目前較適合用 closure pattern 的包括：

- `context_degraded`
- `require_full_read_for_large_files`

## Current Posture

### `pre_task_check`

目前主要處理：

- environment state
- minimum precondition surface
- snapshot-derived escalation hints
- advisory-only 的 large-file visibility proxy

### `post_task_check`

目前主要處理：

- evidence completeness
- domain validator results
- runtime / validator output interpretation

目前還**不是**：

- generic in-task observation layer
- direct advisory-to-verdict coupling
- single-proxy derived proof-bearing compliance signal

## 一句話結論

這份文件不是在把 signal 填滿所有 phase，而是在限制：哪些 signal 何時才有資格成立、何時可以被用、以及何時不能被濫推。
