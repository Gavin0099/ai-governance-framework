# Runtime Injection Layer Plan：runtime injection 的邊界與最小切片

> 狀態：planning boundary fixed  
> 更新日期：2026-04-09

## 目的

這份文件不是要把 repo 變成完整 execution harness，而是先把 `Runtime Injection Layer` 的責任拆清楚。

它要定義四層：

1. canonical source
2. injection / compilation
3. observation
4. enforcement / decision

重點不是多一層名詞，而是防止 injection、observation、enforcement 再被混成同一件事。

## 四層模型

### 1. Canonical Governance Source

責任：

- 定義規則
- 定義 authority
- 作為 machine-readable source of truth

目前 repo 中的主要位置：

- `governance/`
- `contract.yaml`
- decision boundary / testing / review / architecture docs

它**不負責**：

- 直接變成 agent payload
- 直接推定 agent 的實際理解

### 2. Injection / Compilation

責任：

- 把 canonical policy 投影成 agent surface 可見、runtime 可消費的 payload
- 處理 `policy selection`
- 處理 `policy slicing`
- 處理 `policy degradation / projection`

這一層不是 pretty-printer。

它必須回答：

- 哪些規則要進 payload
- 哪些規則對哪種 agent 是可承載的
- 哪些規則該留給 enforcement 補

它**不負責**：

- 直接做 verdict
- 假裝 payload 已被 agent 正確消化

### 3. Observation

責任：

- 觀測 agent 實際做了什麼
- 觀測 runtime surface、coverage、evidence、memory 等 signal
- 讓 reviewer / runtime 看得到這些訊號

Observation 再拆成兩類：

#### a. Consumption Observation

描述：

- agent 有沒有接觸到該看的東西
- injected policy 有沒有進到可見 surface
- context 是否 degraded

例子：

- policy snapshot injected?
- rule pack loaded?
- context degraded?

#### b. Execution Observation

描述：

- agent 實際做了哪些行為
- evidence / memory / coverage 是否齊全
- tool / file / validation surface 是否被觸發

例子：

- edited files
- invoked tools
- skipped validation
- runtime surface manifest
- execution surface coverage
- memory sync / schema signals

### 4. Enforcement

責任：

- 根據 observation signal 做 allow / escalate / deny
- 形成 decision 與 reviewer-visible runtime surface

關鍵原則：

> Observation 只有在被定義成 decision input 之後，才算真正接上 enforcement。  
> 只是 artifact 可見，不代表已經進入 enforcement。

## Core Invariant

> Injection is advisory. Enforcement is authoritative.

也就是：

- injection 的責任是把規則送進合適的 surface
- 不能因為 injection 存在，就假設它已擁有 authority
- 真正 authoritative 的決策仍來自 enforcement

## 為什麼 injection 需要獨立出來

### 1. Injection 是 lossy projection

```text
canonical policy -> compile -> agent payload -> agent internal interpretation
```

這條鏈路天然會有資訊損失。

### 2. 不是每個 agent 都值得當 injection target

有些 agent 只吃得下 very-short constraints；有些甚至根本不適合作為 policy consumption surface，只能靠 wrapper 治理。

### 3. Injection 的 ROI 取決於 enforcement

如果某個 agent surface 根本不可信，應該先強化 enforcement，而不是一味塞更多 policy。

## Agent Classification

### `instruction_capable`

特徵：

- 能承載 repo context
- 能承載較完整 working rules
- 能接收較厚的 runtime payload

### `instruction_limited`

特徵：

- 只能穩定吃 very-short constraints
- context window 或 instruction persistence 較弱

適合承載：

- hard prohibitions
- escalation triggers
- minimum review hints

### `wrapper_only`

特徵：

- 幾乎沒有可靠的 policy consumption surface
- 主要依賴 wrapper / tooling / artifact review / session boundary 治理

## 目前 repo 的 mapping

### Canonical Source

- `governance/`
- `contract.yaml`
- `docs/decision-boundary-layer.md`
- `governance/TESTING.md`

### Injection / Compilation

目前已有雛形，但尚未正式抽成 injection responsibility：

- rule pack loading
- runtime suggestion / preview
- adapter normalization
- minimal runtime injection snapshot

### Observation

目前已有 observation substrate：

- runtime surface manifest
- execution surface coverage
- `decision_context`
- memory schema / sync signals
- advisory observation mapping

### Enforcement

目前已有 functional path：

- `pre_task_check`
- `post_task_check`
- `session_end`
- reviewer-facing adoption / run surfaces

## Decision Coupling

這份 plan 不要求把 injection 直接接進 decision，而是要求 observation signal 最終能透過 `decision_context` 被 decision artifact 消費。

目前已存在的 decision-coupled context fields：

- `surface_validity`
- `coverage_completeness`
- `memory_integrity`

## Minimal Slice

這份 plan 的 first slice 只做：

1. 定義 architecture boundary
2. 區分 `consumption observation` 與 `execution observation`
3. 定義 agent classification
4. 定義 minimal runtime injection snapshot
5. 讓 reviewer-facing / runtime context 能看見 injection-related signals

目前**不做**：

- multi-agent orchestration
- full adapter matrix
- automatic prompt rewriting
- dynamic token budgeting
- runtime hard gate
- verdict precedence rewrite

## Snapshot Direction

第一個 runtime injection snapshot 的定位應該是：

> runtime-consumable projection of existing governance source

也就是：

- 從既有 policy / contract / docs 中萃取出 minimal injection snapshot
- 供 runtime hooks 消費
- 並讓 observation 能回證其最小行為後果

## Consumers

第一批 consumer 應是 runtime，而不是 adapter matrix。

目前較合適的 consumer：

- `pre_task_check`
- `post_task_check`
- reviewer-facing interpretation surface

目前**不做**：

- runtime hard gate
- machine-facing authority expansion

## Non-Goals

這份 plan 不是：

- prompt-engineering OS
- generic orchestration runtime
- token packing optimizer

它要做的是：

- governance-aware runtime injection boundary
- observation-aware decision context substrate
- 未來 enforcement seam 的前置整理

## 一句話結論

這份 plan 不是把 policy 直接塞進 prompt，而是把 `canonical policy -> bounded injection -> observable runtime behavior -> decision context` 這條鏈路先拆清楚。
