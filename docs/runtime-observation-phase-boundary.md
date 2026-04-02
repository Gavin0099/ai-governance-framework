# Runtime Observation Phase Boundary

## Purpose

這份文件定義 observation signal 在不同 runtime phase 中的時間語義與責任歸屬。

目的不是做元件分工表，而是先回答三件事：
- 哪些 signal 在 task execution 前就可成立
- 哪些 signal 必須依賴 execution 後事件才成立
- 哪些 signal 雖然在 pre 可見，但必須到 post 才能形成閉環

這份文件只處理目前已存在、且已被 runtime 或 docs 觸碰到的三個 signal：
- `context_degraded`
- `required_evidence_missing`
- `require_full_read_for_large_files`

## Phase Definitions

### Pre-Task Observation

定義：
- task execution 前即可成立的 observation
- 偏向環境狀態、前置可見性、policy projection、minimum risk posture

適合處理：
- context quality
- missing preconditions known before action
- snapshot-derived escalation hints

不適合處理：
- 未來執行行為的推定
- edit 前 reread 是否真的發生
- validation 是否真的執行

### In-Task / Execution Observation

定義：
- task execution 進行中才會產生的 observation
- 偏向 read / edit / tool / validation / file-scope 行為事件

適合處理：
- read coverage
- edit-before-reread patterns
- validation-after-edit presence

目前 repo 尚未有正式的 generic in-task observation layer。
這一層先保留為 architecture slot，避免把 execution-time signal 硬擠進 pre 或 post。

### Post-Task Observation

定義：
- task execution 後才能較完整判讀的 observation
- 偏向 evidence completeness、behavior compatibility、advisory compliance proxy、trace reconstruction

適合處理：
- edit 後 evidence 是否真的產出
- advisory proxy 是否具備較完整的行為脈絡
- pre-task risk 是否在 post-task 形成實際後果

不適合處理：
- 回溯宣稱 agent 已理解 injected policy
- 將 absent observation 直接當成 compliance proof

## Signal Admissibility by Phase

| Signal | Producible in pre | Producible in in-task | Producible in post | Usable in verdict | Notes |
|---|---|---|---|---|---|
| `context_degraded` | yes | yes | yes | indirect / enforced elsewhere | 屬於 environment / context quality，不是 behavioral compliance |
| `required_evidence_missing` | partial | yes | yes | yes / enforced elsewhere | pre 只能看到明確缺失；post 才能看到實際 evidence completeness |
| `require_full_read_for_large_files` | weak | stronger | stronger | no, advisory only | pre 階段只能看到 large-file visibility 風險；不能假裝推定未來讀取行為 |

## Boundary Rules

以下規則先寫死：

- pre-task signal 不得假裝推定未來執行行為
- post-task signal 不得回溯宣稱 agent 已理解 injected policy
- absent observation 不得當作 compliance proof
- advisory signal 在任一 phase 都不得單獨改 verdict
- environment degradation signal 不得被重新解讀成 behavioral failure

## Current Signal Notes

### `context_degraded`

- 現在最自然的落點是 `pre_task_check`
- 在 `pre` 成立時，可作為 escalation context
- 到 `post` 時，只能與後續 evidence / behavior 一起解讀，不可單獨推導 failure

### `required_evidence_missing`

- 在 `pre` 階段可部分成立：
  - 例如 task_text 已明確缺 precondition signal
- 在 `post` 階段可更完整成立：
  - evidence 應產出卻未產出
  - validation result 應存在卻不存在
- 這個 signal 雖在 taxonomy 中屬 advisory family，但已有既有 escalation / stop 路徑處理其決策效果

### `require_full_read_for_large_files`

- 目前只適合作為 advisory-only observation
- `pre` 階段只能產出：
  - large-file visibility / truncation / summary-first 風險提醒
- 若未來進入 `post`，也只能變成：
  - stronger behavioral compatibility evidence
- 它仍然不是：
  - proof_of_compliance
  - proof_of_violation
  - edit legitimacy gate

## Pre/Post Closure Pattern

有些 signal 不是 pre 或 post 二選一，而是要看閉環：

- `pre`
  - 看見風險或 degradation
- `post`
  - 才能判讀這個風險是否在 execution 後形成實際後果

第一個應採用這種閉環思維的 signal：
- `context_degraded`
- `require_full_read_for_large_files`

這代表：
- `pre_task_check` 適合做 risk posture / advisory warning
- `post_task_check` 更適合做 behavior compatibility / evidence completeness interpretation

## Current Posture

目前 repo 的健康邊界是：

- `pre_task_check`
  - environment state
  - minimum precondition surface
  - snapshot-derived escalation hints
  - advisory-only large-file visibility proxy

- `post_task_check`
  - evidence completeness
  - domain validator results
  - runtime / validator output interpretation

尚未成立的是：
- generic in-task observation layer
- direct advisory-to-verdict coupling
- proof-bearing compliance signal derived from a single proxy

## Next Move

下一步若要繼續，應優先考慮：
- 補 `pre_task` / `post_task` 的 signal producer contract
- 或選一個真正適合 post-task 的 advisory proxy

而不是把更多 execution-time推定硬塞進 `pre_task_check`。
