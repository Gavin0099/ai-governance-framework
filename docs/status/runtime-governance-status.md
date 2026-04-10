# Runtime Governance 狀態

更新日期：2026-04-10

## 摘要

這個 repo 目前不適合只用 `AI governance framework` 這種泛稱理解。比較準確的說法是：

- 它是一個 **machine-interpretable governance runtime**
- 它處理的是 `execution`、`evidence`、`decision`、`memory / state` 與 reviewer-facing governance surfaces
- 它已經超過 prompt discipline，但仍是 bounded runtime，不是 full execution platform

本 repo 明確 **不主張**：

- full execution harness
- machine-authoritative advisory system
- generic multi-agent orchestration platform

## 目前的能力切層

### 1. Decision Layer

這一層負責把 task / session 的治理要求整理成可被 runtime 消費的 machine-readable state。

目前包含：

- contract / risk / oversight / memory_mode
- `pre_task_check` / `post_task_check` / `session_end` 的 verdict / trace
- evidence-based enforcement
- proposal-time guidance / change-control summary

主要檔案：

- `governance_tools/contract_validator.py`
- `governance_tools/state_generator.py`
- `runtime_hooks/core/pre_task_check.py`
- `runtime_hooks/core/post_task_check.py`
- `runtime_hooks/core/session_end.py`
- `governance_tools/change_control_summary.py`

### 2. Execution Awareness Layer

這一層負責把 runtime 實際涉及的 surfaces 顯性化，不再把 execution 當成黑箱。

目前包含：

- runtime surface manifest
- manifest consistency smoke
- execution surface coverage first slice

主要檔案：

- `governance_tools/runtime_surface_manifest.py`
- `governance_tools/runtime_surface_manifest_smoke.py`
- `governance_tools/execution_surface_coverage.py`
- `governance_tools/execution_surface_coverage_smoke.py`

### 3. Advisory / Observation Layer

這一層負責把 advisory signal 的語義、phase、producer responsibility 說清楚，但不把它升格成 authority。

目前是 bounded slice：

- advisory signal taxonomy
- runtime observation phase boundary
- advisory signal producer contract
- pre / post reviewer-facing advisory rendering
- 至少一個跨 surface consistency example

它目前的權限邊界是：

- reviewer-visible
- non-verdict-bearing
- non-machine-authoritative

### 4. Memory / State Integrity Layer

這一層負責處理 memory schema、host-agent gap、memory closeout visibility 與 state source-of-truth。

目前包含：

- consuming repo `memory/01~04` scaffold
- `memory schema partial/complete` visibility
- host-agent memory gap / sync policy / sync signal
- `session_end` 的 `memory_closeout` visibility

目前補到的是：

- session 是否被視為 memory candidate
- promotion 是否被考慮
- decision / reason 是否可見

不是「所有工作都一定自動寫入 durable memory」。

### 5. Session Workflow / Closeout Layer

這一層的核心是把 closeout 從 AI 自述，收斂成有 trust boundary 的 canonical workflow。

目前的形狀是：

- producer 先寫 candidate
- system 再寫 canonical closeout
- downstream consumer 只吃 canonical

主要組件：

- canonical closeout producer
- closeout context injection
- closeout audit
- session index
- `/wrap-up` candidate drafting surface

## 目前已完成的 bounded capabilities

目前可以比較穩定說已成立的包括：

- runtime governance spine
- canonical closeout workflow
- `decision_context` bridge
- runtime surface manifest / coverage
- memory closeout visibility
- classification governance companion slice

這些能力都已經有：

- producer / canonical / consumer 分層
- smoke / tests / reviewer-facing surface
- bounded non-goals

## 目前刻意不做的事

- 不把 advisory signal 直接接進 verdict authority
- 不把 advisory semantics 升格成 machine-facing authority
- 不追 full signal x full surface matrix
- 不把 `/wrap-up` 變成唯一 closeout 入口
- 不把 runtime injection 擴成 full adapter matrix / generic orchestration substrate

## 建議閱讀順序

1. `README.md`
2. `docs/decision-context-bridge.md`
3. `docs/session-workflow-enhancement-plan.md`
4. `docs/status/closeout-audit.md`
5. `docs/status/runtime-surface-manifest.md`
6. `docs/status/execution-surface-coverage.md`

## 下一步

目前最合理的方向不是再長更多新 layer，而是：

- 觀察 consuming repo 的真實 adoption 分布
- 觀察 closeout / advisory / audit 是否穩定成立
- 維持 status surface、README、reviewer handoff 與 runtime reality 的對齊

一句話：

> 這個 repo 目前是一個 reviewer-friendly、evidence-aware、bounded 的 governance runtime，而不是 full execution platform。
