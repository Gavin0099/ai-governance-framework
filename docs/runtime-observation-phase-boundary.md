# Runtime Observation Phase Boundary

> 狀態：phase semantics fixed
> 更新日期：2026-04-08

## Purpose

這份文件的目的不是做 pre/post 功能分工表，而是把 observation signal 的**時間語義**寫死。

它要防止的誤解是：

- 還沒成熟的 signal 被太早拿來做判斷
- pre-task signal 被拿去推論未來執行行為
- post-task signal 被誤用成 agent 已理解 injected policy 的證明

目前只用 3 個現有 signal 當例子：

- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Phase Definitions

### Pre-Task Observation

回答：

- task execution 前就能成立的觀測
- 風險、前置可見性、環境狀態
- snapshot-derived escalation hints

典型內容：

- context quality
- missing preconditions known before action
- policy projection / minimum risk posture

不應假裝知道：

- edit 前是否真的 reread
- validation 是否真的會發生
- execution 過程中會產生哪些 evidence

### In-Task / Execution Observation

回答：

- execution 過程中真實發生的 read / edit / tool / validation 行為
- file-scope / coverage / reread / validation order 等 execution-time signals

典型內容：

- read coverage
- edit-before-reread patterns
- validation-after-edit presence

目前 repo 還沒有 generic in-task observation layer，但 architecture 上必須承認這個 phase 的存在，避免把 execution-time signal 硬擠進 pre 或 post。

### Post-Task Observation

回答：

- task execution 後才能完整觀測的結果
- evidence completeness
- behavioral compatibility
- advisory compliance proxy
- trace reconstruction

典型內容：

- edit 後 evidence 是否產出
- validation 是否真的執行
- advisory proxy 是否有較完整的 execution backing

不應假裝證明：

- agent 已理解 injected policy
- absent observation 就等於 compliance proof

## Signal Admissibility by Phase

| Signal | Pre 可成立 | In-task 可成立 | Post 可成立 | 可否進 verdict | Notes |
|---|---|---|---|---|---|
| `context_degraded` | yes | yes | yes | indirect / enforced elsewhere | environment / context quality，不等於 behavioral compliance |
| `required_evidence_missing` | partial | yes | yes | yes / enforced elsewhere | pre 只能先看到部分風險；post 才能較完整判 evidence completeness |
| `require_full_read_for_large_files` | weak | stronger | stronger | no, advisory only | pre 只能先看到 visibility 風險；post 才較適合當 behavioral compatibility evidence |

## Boundary Rules

以下規則固定不變：

- pre-task signal 不得假裝推定未來執行行為
- post-task signal 不得回溯聲稱 agent 已理解 injected policy
- absent observation 不得當作 compliance proof
- advisory signal 在任何 phase 都不得單獨改 verdict
- environment degradation signal 不得被改寫成 behavioral failure

## Current Signals

### `context_degraded`

現在主要由：

- `pre_task_check`

承接。

它的語義是：

- environment / context quality 下降
- 可影響 escalation posture
- 不是 behavioral failure

在 post-task 中，它可以幫助 reviewer 理解：

- agent 是在 degraded 條件下執行
- 但不能單獨被用來宣告這次 execution 不合規

### `required_evidence_missing`

這個 signal 比其他 advisory signal 更靠近 execution completeness。

pre-task：

- 只能先看到部分 evidence risk
- 例如 task text 或前置條件提示該有某些 evidence

post-task：

- 才能更完整地判斷 evidence 是否真的缺失
- 因此它與 escalation / stop 路徑相鄰，但仍不能被誤降級成單純 reviewer hint

### `require_full_read_for_large_files`

目前定位是：

- advisory-only observation
- 比較接近 partial visibility / truncation / review risk

pre-task：

- 只能先提醒 large-file visibility 風險

post-task：

- 才比較可能形成較強的 behavioral compatibility evidence

明確不是：

- proof_of_compliance
- proof_of_violation
- edit legitimacy gate

## Pre/Post Closure Pattern

有些 signal 不應該被看成 pre 或 post 二選一，而是：

```text
pre 提醒風險 -> post 評估後果
```

這種 closure pattern 目前最適合的例子是：

- `context_degraded`
- `require_full_read_for_large_files`

對應意思是：

- `pre_task_check` 提供 risk posture / advisory warning
- `post_task_check` 再用 execution 後的 evidence 補上 interpretation

## Current Posture

目前 repo 的實際落點是：

### `pre_task_check`

負責：

- environment state
- minimum precondition surface
- snapshot-derived escalation hints
- advisory-only large-file visibility proxy

### `post_task_check`

負責：

- evidence completeness
- domain validator results
- runtime / validator output interpretation

目前刻意不做：

- generic in-task observation layer
- direct advisory-to-verdict coupling
- single-proxy derived proof-bearing compliance signal

## Next Move

如果未來要往前走，優先應補的是：

- `pre_task` / `post_task` 的 signal producer contract
- execution-time signal 的 bounded producer
- post-task 的 advisory proxy interpretation

但不應默默滑向：

- 把所有 observation 都塞進 `pre_task_check`
- 把 phase semantics 擴成 machine authority

## One-Line Summary

這份文件固定的是：signal 不只分種類，也分成熟時間。  
沒有時間語義的 observation，最後很容易變成「訊號很多，但判斷時機錯了」。
