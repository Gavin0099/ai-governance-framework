# Runtime Injection Layer Plan

> planning boundary fixed
> 更新日期：2026-04-09

## 目的

這份文件不是要把 repo 直接做成 execution harness，而是把 `Runtime Injection Layer` 的邊界釘清楚。

它要回答的是：
- 什麼是 canonical source
- 什麼是 injection / compilation
- 什麼是 observation
- 什麼才算 enforcement / decision

這份 plan 的價值在於先把 injection、observation、enforcement 切開，而不是再長一層漂亮名詞。

## 四層模型

1. `Canonical Governance Source`
2. `Injection / Compilation`
3. `Observation`
4. `Enforcement`

### 1. Canonical Governance Source

負責：
- 定義規則
- 定義 authority
- 作為 machine-readable source of truth

目前 repo 的來源包括：
- `governance/`
- `contract.yaml`
- decision boundary / testing / review / architecture docs

不負責：
- 直接變成 agent payload
- 直接決定 agent 如何理解規則

### 2. Injection / Compilation

負責：
- 把 canonical policy 投影成 agent surface 可以消費的 runtime payload
- 做 `policy selection`
- 做 `policy slicing`
- 做 `policy degradation / projection`

它不是 pretty-printer。

它的問題不是把格式改漂亮，而是決定：
- 哪些規則要進 payload
- 哪些規則這個 agent 吃不下
- 哪些規則要交給外部 enforcement 補

不負責：
- 直接產生 verdict
- 假裝 payload 被 agent 完整理解

### 3. Observation

負責：
- 觀測 agent 真正做了什麼與 runtime surface
- 觀測注入是否被看見、被截斷、被降級
- 給 reviewer / runtime 可用的 signal

Observation 再拆成兩類：

#### a. Consumption Observation

關心：
- agent 是否看見該看的東西
- injected policy 是否真的被送進 surface
- context 是否 degraded

例子：
- policy snapshot injected?
- rule pack loaded?
- context degraded?

#### b. Execution Observation

關心：
- agent 實際做了什麼
- evidence / memory / coverage 是否成立
- tool / file / validation surface 是否被接住

例子：
- edited files
- invoked tools
- skipped validation
- runtime surface manifest
- execution surface coverage
- memory sync / schema signals

### 4. Enforcement

負責：
- 根據 observation signal 決定 allow / escalate / deny
- 把 decision 送回 runtime / reviewer surface

關鍵原則：
> Observation 必須先成為 decision input，才算真的接到 enforcement。  
> 只有 artifact 可見，不等於 enforcement 已接住。

## Core Invariant

> Injection is advisory. Enforcement is authoritative.

意思是：
- injection 負責把規則送進 agent
- 不能把 injection 本身當 authority
- enforcement 不能只因 agent 看起來像有遵守，就直接給高信心結論

## 為什麼 injection 很難

### 1. Injection 是 lossy projection

```text
canonical policy -> compile -> agent payload -> agent internal interpretation
```

它不是無損轉換，而是有損投影。

### 2. 不是每個 agent 都值得當 injection target

有些 agent 只適合 very-short constraints。
有些根本不適合當 policy consumption surface，只適合被 wrapper 治理。

### 3. Injection 的 ROI 依賴 enforcement

如果某個 agent surface 就算吃到 payload，也不能提高可信度，那就不值得灌更多 policy。

## Agent 分類

### `instruction_capable`

特徵：
- 能讀 repo context
- 能承載較長 working rules
- 能穩定接住 runtime payload

### `instruction_limited`

特徵：
- 只能穩定承載 very-short constraints
- context window 或 instruction persistence 較弱

適合：
- hard prohibitions / escalation triggers / minimum review hints

### `wrapper_only`

特徵：
- 不應被視為 policy consumption surface
- 只能靠 wrapper / tooling / artifact review / session boundary 治理

## 目前 repo 對照

### Canonical Source

- `governance/`
- `contract.yaml`
- `docs/decision-boundary-layer.md`
- `governance/TESTING.md`

### Injection / Compilation

目前還沒完整成形，但已有 injection responsibility 雛形：
- rule pack loading
- runtime suggestion / preview
- adapter normalization
- minimal runtime injection snapshot

### Observation

目前已有 observation substrate：
- runtime surface manifest
- execution surface coverage
- decision_context
- memory schema / sync signals
- advisory observation mapping

### Enforcement

目前已有 functional path：
- `pre_task_check`
- `post_task_check`
- `session_end`
- reviewer-facing adoption / run surfaces

## Decision Coupling

這份設計的關鍵不是把 injection 做滿，而是把 observation signal 正式整理進 decision context。

當前已落地的 decision-coupled context fields：
- `surface_validity`
- `coverage_completeness`
- `memory_integrity`

## Minimal Slice

這份 plan 的 first slice 只做：
1. 定義四層責任
2. 拆開 `consumption observation` 與 `execution observation`
3. 定義 agent classification
4. 定義 minimal runtime injection snapshot
5. 讓 reviewer-facing / runtime context 能讀 injection-related signals

不做：
- multi-agent orchestration
- full adapter matrix
- automatic prompt rewriting
- dynamic token budgeting
- runtime hard gate
- verdict precedence rewrite

## Snapshot Direction

第一版更適合做成：

> runtime-consumable projection of existing governance source

也就是：
- 從現有 policy / contract / docs 投影出 minimal injection snapshot
- 先給 runtime hooks 使用
- 再由 observation 回證它是否有價值

## Consumers

第一個 consumer 應該是 runtime，不是 adapter matrix。

目前合理 consumer：
- `pre_task_check`
- `post_task_check`
- reviewer-facing interpretation surface

暫不處理：
- runtime hard gate
- machine-facing authority expansion

## Non-Goals

這份 plan 不做：
- prompt-engineering OS
- generic orchestration runtime
- token packing optimizer

它真正要做的是：
- governance-aware runtime injection boundary
- observation-aware decision context substrate
- future enforcement seam

## 一句話總結

這份設計不是把 policy 塞進 prompt，而是把 canonical policy -> bounded injection -> observable runtime behavior -> decision context 的責任邊界釘清楚。
