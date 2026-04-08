# Runtime Governance 狀態

更新日期：2026-04-08

## 摘要

這個 repo 現在不只是文件型的 `AI governance framework`。更準確地說，它已經是一個 **machine-interpretable governance runtime**，能把治理規則、execution surface、evidence、decision、memory / state 與 reviewer-facing surface 串成可觀測、可審查、可生成 artifact 的 bounded runtime。

同時也要明講它目前**不是**：

- full execution harness
- machine-authoritative advisory system
- generic multi-agent orchestration platform

目前比較準的整體狀態是：

- 主 runtime spine 已完成
- closeout / decision_context / observation surface 已落地
- adoption、status surface、consuming repo 驗證持續收斂中

## 目前能力分層

### 1. Decision Layer

這是最早成形、也是仍然最核心的一層。主要處理：

- contract / risk / oversight / memory_mode 等 machine-readable governance state
- `pre_task_check` / `post_task_check` / `session_end` 的 verdict 與 trace
- evidence-based enforcement
- proposal-time guidance 與 change-control summary

代表性元件：

- `governance_tools/contract_validator.py`
- `governance_tools/state_generator.py`
- `runtime_hooks/core/pre_task_check.py`
- `runtime_hooks/core/post_task_check.py`
- `runtime_hooks/core/session_end.py`
- `governance_tools/change_control_summary.py`

### 2. Execution Awareness Layer

這一層處理「runtime 實際治理了哪些 surface」與「哪些 surface 應該存在但還沒被接住」。

目前已落地：

- runtime surface manifest
- manifest consistency smoke
- execution surface coverage first slice

代表性元件：

- `governance_tools/runtime_surface_manifest.py`
- `governance_tools/runtime_surface_manifest_smoke.py`
- `governance_tools/execution_surface_coverage.py`
- `governance_tools/execution_surface_coverage_smoke.py`

### 3. Advisory / Observation Layer

這一層不是新的 authority，而是把 advisory signal 的位階、時間語義與 producer responsibility 寫死，避免 observation 被誤升格成 proof 或 verdict input。

目前已完成的 bounded slice：

- advisory signal taxonomy
- runtime observation phase boundary
- advisory signal producer contract
- pre / post reviewer-facing advisory rendering
- 至少一個跨 surface consistency example

這一層目前刻意維持：

- reviewer-visible
- non-verdict-bearing
- non-machine-authoritative

### 4. Memory / State Integrity Layer

這一層處理 memory schema、host-agent sync gap 與 session closeout promotion visibility。

目前已落地：

- consuming repo `memory/01~04` scaffold
- `memory schema partial/complete` 檢查
- host-agent memory gap / sync policy / sync signal
- `session_end` 的 `memory_closeout` visibility

這表示系統至少能回答：

- 這次 session 是否被視為高價值 candidate
- promotion 是否被考慮
- 最終 decision 與 reason 是什麼

### 5. Session Workflow / Closeout Layer

這是近期補齊的主線。核心不是多一個 closeout 文件，而是把 session 收尾從 AI 自述，改成有 trust boundary 的 canonical workflow。

目前形狀是：

- producer 寫 candidate
- system 產 canonical closeout
- downstream consumer 只吃 canonical

對應能力包括：

- canonical closeout producer
- closeout context injection
- closeout audit
- session index
- `/wrap-up` candidate drafting surface

## 已穩定的 bounded capabilities

以下能力現在可視為已收斂、可用，但仍維持 bounded scope：

- runtime governance spine
- canonical closeout workflow
- `decision_context` bridge
- runtime surface manifest / coverage
- memory closeout visibility
- classification governance companion slice

這些能力的共通特徵是：

- 有明確 producer / canonical / consumer 邊界
- 有至少一個真實 consumer
- 有對應測試或 smoke
- 沒有被過早擴張成 generic platform

## 刻意保守的邊界

目前 repo 仍刻意**不做**以下事情：

- 不把 advisory signal 直接接進 verdict authority
- 不把 advisory semantics 擴成 machine-facing authority
- 不把 execution coverage 做成 full matrix completion game
- 不把 `/wrap-up` 變成唯一官方 closeout 入口
- 不把 runtime injection 擴成 full adapter matrix / generic orchestration substrate

換句話說，這個 repo 現在追求的是：

- 可審查
- 可觀測
- 可驗證

不是：

- 大而全
- 到處攔截
- 自動裁決一切

## 建議閱讀順序

如果你想理解這個 repo 現在的 bounded runtime reality，建議依序讀：

1. `README.md`
2. `docs/decision-context-bridge.md`
3. `docs/session-workflow-enhancement-plan.md`
4. `docs/status/closeout-audit.md`
5. `docs/status/runtime-surface-manifest.md`
6. `docs/status/execution-surface-coverage.md`

## 當前判斷

目前最重要的不是再多加幾個 checker，而是：

- 讓 consuming repo 實際走到這些 bounded runtime path
- 觀察 closeout / advisory / audit 的真實 session 分布
- 保持 status surface、README 與實際 runtime 邊界一致

一句話總結：

> 這個 repo 現在已經是一個 machine-interpretable governance runtime，但它仍刻意把自己限制在 reviewer-friendly、evidence-aware、bounded governance substrate，而不是 full execution platform。
