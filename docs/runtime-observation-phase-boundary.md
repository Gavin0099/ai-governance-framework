# Runtime Observation Phase Boundary

> phase semantics fixed
> 更新日期：2026-04-09

## 目的

這份文件不是把 pre/post 當成單純功能分工表，而是定義 observation signal 在什麼時間點才有資格成立。

它要回答的是：
- 哪些 signal 可以在 task 前成立
- 哪些 signal 必須等 execution 後才完整
- 哪些 signal 需要 pre -> post closure 才能正確理解

目前只用三個 signal 當例子：
- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Phase 定義

### Pre-Task Observation

關心：
- task execution 前就能成立的風險
- 前置可見性與上下文品質
- snapshot-derived escalation hints

適合處理：
- context quality
- known missing preconditions
- minimum risk posture

不適合假裝判斷：
- edit 前是否真的 reread
- validation 是否真的有跑
- execution 後才會出現的 evidence completeness

### In-Task / Execution Observation

關心：
- execution 過程中的 read / edit / tool / validation 事件
- file coverage、reread、validation order 等 execution-time signals

目前 repo 還沒有正式的 generic in-task observation layer，但這個 phase 必須先被命名，避免本來屬於 execution-time 的訊號被硬塞進 pre 或 post。

### Post-Task Observation

關心：
- task execution 後的 evidence completeness
- behavioral compatibility
- advisory compliance proxy
- trace reconstruction

不應聲稱：
- agent 一定理解 injected policy
- absent observation 就等於 compliance proof

## Signal Admissibility by Phase

| Signal | Pre 可成立 | In-task 可成立 | Post 可成立 | 可直接進 verdict | Notes |
|---|---|---|---|---|---|
| `context_degraded` | yes | yes | yes | indirect / enforced elsewhere | environment / context quality，不是 behavioral compliance |
| `required_evidence_missing` | partial | yes | yes | yes / enforced elsewhere | pre 只能先提示 evidence risk，post 才能完整判 evidence completeness |
| `require_full_read_for_large_files` | weak | stronger | stronger | no, advisory only | pre 只能提示 visibility risk，post 才比較像 behavioral compatibility evidence |

## Boundary Rules

- pre-task signal 不得假裝推定未來執行行為
- post-task signal 不得反推 agent 已理解 injected policy
- absent observation 不得當作 compliance proof
- advisory signal 在任何 phase 都不得單獨改 verdict
- environment degradation signal 不得重寫成 behavioral failure

## 當前 signals

### `context_degraded`

目前主要在 `pre_task_check` 成立。

它表示的是：
- environment / context quality 下降
- escalation posture 應提高
- 不是 behavioral failure

### `required_evidence_missing`

這個 signal 雖然屬 advisory family，但更接近 execution completeness。

pre-task：
- 可以先提示 evidence risk
- 表示這個 task 可能需要更高證據要求

post-task：
- 才能真正看到 evidence 是否完整
- 也因此更靠近 escalation / stop 語義，而不是單純 reviewer hint

### `require_full_read_for_large_files`

這是目前第一個 advisory-only executable proxy。

它表示：
- large-file visibility / truncation / review risk
- 不是 proof_of_compliance
- 不是 proof_of_violation
- 不是 edit legitimacy gate

## Pre/Post Closure Pattern

有些 signal 需要這種 closure pattern：

```text
pre 提示風險 -> post 評估後果
```

目前最像這種 closure pattern 的有：
- `context_degraded`
- `require_full_read_for_large_files`

## 當前 posture

### `pre_task_check`

主要處理：
- environment state
- minimum precondition surface
- snapshot-derived escalation hints
- advisory-only 的 large-file visibility proxy

### `post_task_check`

主要處理：
- evidence completeness
- domain validator results
- runtime / validator output interpretation

目前不做：
- generic in-task observation layer
- direct advisory-to-verdict coupling
- single-proxy derived proof-bearing compliance signal

## 下一步

真正合理的下一步應該是：
- 定義 pre_task / post_task 的 signal producer contract
- 讓 execution-time signal 有 bounded producer
- 補 post-task 的 advisory proxy interpretation

而不是把 observation 全丟進 `pre_task_check`。

## 一句話總結

這份文件不是在列 signal 清單，而是在限制 signal 何時才算 observation、何時不能被過早拿去做判斷。
