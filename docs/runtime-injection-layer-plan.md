# Runtime Injection Layer Plan

> 狀態：planning boundary fixed
> 更新日期：2026-04-08

## Purpose

這份文件的目的不是把 repo 宣告成完整 execution harness，而是把 `Runtime Injection Layer` 的架構責任切乾淨。

它要回答的是：

- 哪些治理規則是 canonical source
- 哪些規則會被投影到 agent 可見表面
- 哪些 runtime signal 屬於 observation
- 哪些結果才進 enforcement / decision

這份計畫刻意不把 injection、observation、enforcement 混成同一層。

## Four-Layer Model

目前這條線用四層模型描述：

1. `Canonical Governance Source`
2. `Injection / Compilation`
3. `Observation`
4. `Enforcement`

### 1. Canonical Governance Source

負責：

- 定義規則
- 宣告 authority
- 提供 machine-readable source of truth

在本 repo 中，典型來源包括：

- `governance/`
- `contract.yaml`
- decision boundary / testing / review / architecture docs

不負責：

- 直接生成 agent payload
- 假設 agent 已消費規則

### 2. Injection / Compilation

負責：

- 將 canonical policy 投影成 agent surface 可承載的 runtime payload
- 做 `policy selection`
- 做 `policy slicing`
- 做 `policy degradation / projection`

這一層不是 pretty-printer。  
它處理的是：

- 哪些規則值得注入
- 哪些規則在某個 agent 上只能保留最小版本
- 哪些規則不應注入，而應交給外部 enforcement

不負責：

- 直接裁決 verdict
- 假設注入就等於 agent 理解與遵守

### 3. Observation

負責：

- 收集 agent 實際行為與 runtime surface
- 收集注入是否被看見、執行是否可觀測
- 產生可供 reviewer / runtime 使用的 signal

Observation 再拆成兩類：

#### a. Consumption Observation

回答：

- agent 有沒有看到該看的東西
- injected policy 是否進入可見表面
- context 是否 degraded

典型訊號：

- policy snapshot injected?
- rule pack loaded?
- context degraded?

#### b. Execution Observation

回答：

- agent 實際做了什麼
- evidence / memory / coverage 是否完整
- tool / file / validation surface 是否被觸發

典型訊號：

- edited files
- invoked tools
- skipped validation
- runtime surface manifest
- execution surface coverage
- memory sync / schema signals

### 4. Enforcement

負責：

- 根據 observation signal 決定 allow / escalate / deny
- 將 decision 綁到可解釋的 runtime / reviewer surface

重要前提：

> Observation 只有在被定義成 decision input 時，才算真正接上 enforcement。  
> 光是 artifact 可見，不等於 enforcement 已使用。

## Core Invariant

> Injection is advisory. Enforcement is authoritative.

意思是：

- injection 可以幫助 agent 看見規則
- 但 injection 本身不等於 authority
- enforcement 不應假設 agent 真的吃下了注入內容
- 對低信任 agent，完全可以不注入，只靠外部 enforcement

## Why Injection Is Hard

Runtime injection 的難點不只是格式轉換，而是：

### 1. Injection 是 lossy projection

不是：

```text
canonical policy -> compile -> agent payload -> 可靠遵守
```

而比較像：

```text
canonical policy -> lossy projection -> agent internal interpretation -> 不可完全驗證
```

### 2. 不是每個 agent 都值得當 injection target

有些 agent 可以承載較完整的治理責任，有些只能承載極短約束，有些根本只適合 wrapper-only 治理。

### 3. Injection 的 ROI 必須受 enforcement 約束

若某 agent surface 對 injection 的承載力很低，就不應為了形式完整而硬塞更多 policy。

## Agent Classification

目前用最小的 capability-aware 分類：

### `instruction_capable`

特徵：

- 能讀 repo context
- 能承載較完整的 working rules
- 能穩定接住 runtime payload

策略：

- 可使用較完整的 advisory payload

### `instruction_limited`

特徵：

- 只能穩定承載 very-short constraints
- context window 或 instruction persistence 較弱

策略：

- 只注入 hard prohibitions / escalation triggers / minimum review hints

### `wrapper_only`

特徵：

- 不適合當 policy consumption surface
- 只能靠 wrapper / tooling / artifact review / session boundary 治理

策略：

- 不作為 injection target

## Current Repo Mapping

### Canonical Source

目前已存在：

- `governance/`
- `contract.yaml`
- `docs/decision-boundary-layer.md`
- `governance/TESTING.md`

### Injection / Compilation

目前只有雛形，尚未正式抽象成 injection responsibility：

- rule pack loading
- runtime suggestion / preview
- adapter normalization
- minimal runtime injection snapshot

### Observation

目前已存在的 substrate：

- runtime surface manifest
- execution surface coverage
- decision_context
- memory schema / sync signals
- advisory observation mapping

### Enforcement

目前實際落點：

- `pre_task`
- `post_task`
- `session_end`
- reviewer-facing adoption / run surfaces

## Decision Coupling

這條線真正重要的不是「有沒有 injection」，而是：

> 哪些 observation signal 會進入 decision context，哪些只是 artifact。

目前已知的 decision-coupled context fields：

- `surface_validity`
- `coverage_completeness`
- `memory_integrity`

## Minimal Slice

這個 plan 的 first slice 只應包含：

1. 明確定義四層責任
2. 分開 `consumption observation` 與 `execution observation`
3. 定義 agent classification
4. 萃出 minimal runtime injection snapshot
5. 讓 reviewer-facing / runtime context 能讀到最小 injection-related signals

刻意不做：

- multi-agent orchestration
- full adapter matrix
- automatic prompt rewriting
- dynamic token budgeting
- runtime hard gate
- verdict precedence rewrite

## Snapshot Direction

第一版不要追求 full schema，而是做：

> runtime-consumable projection of existing governance source

也就是：

- 由既有 policy / contract / docs 萃出 minimal injection snapshot
- 先讓 runtime hooks 消費
- 再看 observation 是否能回證它

## Consumers

這條線第一個 consumer 應該是 runtime，不是 adapter matrix。

優先 consumer：

- `pre_task_check`
- `post_task_check`
- reviewer-facing interpretation surface

先不做：

- runtime hard gate
- machine-facing authority expansion

## Non-Goals

這份 plan 不主張：

- prompt-engineering OS
- generic orchestration runtime
- token packing optimizer

它真正處理的是：

- governance-aware runtime injection boundary
- observation-aware decision context substrate
- future enforcement seam

## One-Line Summary

這條線的重點不是把 policy 塞進 prompt，而是把「canonical policy -> bounded injection -> observable runtime behavior -> decision context」的責任邊界切乾淨。
