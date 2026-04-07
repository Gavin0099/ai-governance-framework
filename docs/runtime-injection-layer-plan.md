# Runtime Injection Layer Plan

## 目的

這份文件定義 `Runtime Injection Layer` 的最小架構邊界。

它不是在宣告新的 prompt system，也不是要立刻做 multi-agent orchestration。
這一層要解決的是：

- 哪些治理規則值得被注入到 agent 可見表面
- 哪些 agent 值得被視為可信的 policy consumption surface
- observation 如何從「可看 artifact」提升成 enforcement 可依賴的 decision input

## 四層模型

這條線的最小完整模型是四層，不是三層：

1. `Canonical Governance Source`
2. `Injection / Compilation`
3. `Observation`
4. `Enforcement`

### 1. Canonical Governance Source

負責：
- 定義規則、契約、風險級別、authority 邊界
- 提供 machine-readable source of truth

目前對應：
- `governance/`
- `contract.yaml`
- decision boundary / testing / review / architecture docs

不負責：
- 決定某個 agent 應該看到多少規則
- 判斷 agent 是否真的讀過規則

### 2. Injection / Compilation

負責：
- 為特定 agent surface 選擇可注入的治理切片
- 把 canonical policy 投影成該 surface 可承載的最小 runtime payload

這一層不是單純格式轉換，而是：
- `policy selection`
- `policy slicing`
- `policy degradation / projection`

也就是說，它要回答：
- 哪些規則需要注入
- 哪些規則不能安全注入，只能留給外部 enforcement
- 當 agent surface 容量不足時，保留哪部分、降級哪部分

不負責：
- 直接做 runtime verdict
- 直接假設 agent 因為看到了 payload 就一定遵守

### 3. Observation

負責：
- 收集 agent 實際 consumption 與 execution 的可審查證據
- 將這些證據轉成 enforcement 可引用的 signal

Observation 至少分兩種：

#### a. Consumption Observation

回答：
- agent 是否看到了應看的治理內容
- context 是否被裁切、降級、或遺漏

例子：
- policy snapshot injected?
- rule pack loaded?
- context degraded?

#### b. Execution Observation

回答：
- agent 實際做了什麼
- runtime surface 是否被走到
- evidence / memory / coverage 是否完整

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
- 將觀測結果納入 verdict interpretation

重要限制：
- observation 只有在被明確列為 decision input 時，才算真的接上 enforcement
- 只有 artifact 而不進 decision model，仍然只是事後可看，不算 enforcement input

## Core Invariant

> **Injection is advisory. Enforcement is authoritative.**

這是這條線最重要的一句話，必須在所有下游設計中保持有效。

含義：
- Injection 的目的是讓 agent 更容易做對事，但 injection 是否成功不影響 enforcement 的責任
- 即使 injection 層完全失效（agent 忽略、壓縮、誤解），enforcement 路徑（pre_task / post_task / session_end）仍然必須能獨立成立
- 任何讓 enforcement 依賴 injection 成功的設計，都是錯誤的信任假設

推論：
- 不能用「我已經注入了規則」作為 enforcement 的替代
- 不能把 injection layer 的完整性當成 trust signal
- Injection 的 ROI 只能用「降低 enforcement 需要攔截的次數」來衡量，不能用「替代 enforcement」來設計

---

## 三個注意事項（為什麼不能高估 Injection）

### 1. Injection 不是確定性轉換

直覺上 injection 是：

```
canonical policy → compile → agent payload → 行為
```

實際上是：

```
canonical policy → lossy projection → agent internal interpretation → 行為
```

Agent 會壓縮 instruction、忽略 context、甚至誤解 rule 的語義。
所以 injection 輸出不等於 agent 行為，injection 成功不等於 policy 被遵守。

### 2. 不同 agent 的承載能力不對等

不是在做「格式轉換」，而是在做 **capability-aware policy reduction**。

同一份 policy 在不同 surface 的有效性差距極大：

| Agent | context | 持久 instruction | tool gate | 確定性 |
|-------|---------|-----------------|-----------|--------|
| Claude Code | 完整 | 支援 | 支援 | 高 |
| Copilot | 幾乎無 | 幾乎無 | 無 | 低 |
| ChatGPT Web | 無 local | 無 | 無 | 低 |

對於低承載 agent，injection 只會製造虛假的「已治理」感，而真正的責任必須由外部 enforcement 承擔。

### 3. Injection 是可替代層，不是必要層

正確的層級關係：

- Injection = optional optimization（可能提升 agent 行為品質）
- Enforcement = required boundary（必須存在，不能依賴 injection）

對 `wrapper_only` class 的 agent，injection 根本不應存在於設計路徑中。
這不是退而求其次，而是對這類 agent 正確的治理策略：直接守住邊界，不浪費在內部注入。

---

## Capability Model

Agent classification 的核心是它的 capability，而不是它的品牌或版本。
相同的 capability profile 適用相同的 injection strategy。

### Capability Schema（第一版）

```yaml
agent_capability:
  has_file_access: true          # 可讀寫 repo 檔案
  supports_persistent_instruction: true  # 可承載跨 session 的 instruction（如 CLAUDE.md）
  supports_tool_gate: true       # 可被 pre/post hook 攔截
  context_window: full           # full / limited / minimal
  deterministic_execution: true  # 行為是否可預期、可重現
  trust_level: high              # high / medium / low / untrusted
```

### Capability 到 Injection Strategy 的映射

```
if capability.supports_persistent_instruction AND trust_level in [high, medium]:
    → use injection (advisory payload)
    → include: selected rules, escalation triggers, hard prohibitions

if capability.context_window == limited OR trust_level == low:
    → minimal injection only
    → include: hard prohibitions only (最高密度，最小切片)

if capability.supports_tool_gate == false OR trust_level == untrusted:
    → skip injection entirely
    → rely on: external wrapper / post-execution artifact review / session boundary enforcement
```

### 與 Agent Classification 的對應

| Class | capability profile | injection strategy |
|-------|-------------------|-------------------|
| `instruction_capable` | file_access=T, persistent_instruction=T, tool_gate=T, context=full, trust=high | full advisory payload |
| `instruction_limited` | persistent_instruction=F or context=limited | hard prohibitions only |
| `wrapper_only` | tool_gate=F or trust=untrusted | no injection; external enforcement only |

---

## 目前 repo 的對應

### Canonical Source

已存在：
- `governance/`
- `contract.yaml`
- `docs/decision-boundary-layer.md`
- `governance/TESTING.md`

### Injection / Compilation

部分存在，但角色未明確：
- rule pack loading
- runtime suggestion / preview
- adapter normalization

目前缺口：
- 尚未被抽象成 `injection responsibility`
- 尚未定義 canonical runtime injection snapshot
- 尚未定義哪些規則該注入、哪些不該注入

### Observation

已存在雛形：
- `runtime surface manifest`
- `execution surface coverage`
- `decision_context`
- memory schema / sync signals

目前缺口：
- consumption observation 幾乎還沒有正式模型
- execution observation 雖有 artifact，但只有部分進入 decision context

### Enforcement

已有功能性路徑：
- `pre_task`
- `post_task`
- `session_end`
- reviewer-facing adoption / run surfaces

目前缺口：
- observation 尚未全面被宣告成 enforcement 可依賴的 decision input

## 先回答的關鍵問題

在動任何 schema 或 adapter 之前，這條線必須先回答：

1. 哪些 observation signal 會影響 verdict interpretation？
2. 哪些 policy 必須 injection，哪些只該由外部 enforcement 處理？
3. 哪些 agent 是可信的 policy consumption surface？
4. 哪些 agent 只能被 wrapper / external enforcement 治理？

## Agent Classification

第一版先把 agent 分成三類：

### 1. `instruction_capable`

特性：
- 可穩定承載明確治理指令
- 可被注入有限但有意義的 runtime payload

例子：
- repository-native coding agent surfaces

### 2. `instruction_limited`

特性：
- 能承載 very-short constraints
- 容量與穩定性不足以承載完整治理切片

處理原則：
- 只注入 hard prohibitions / escalation triggers / minimum review hints

### 3. `wrapper_only`

特性：
- 不可信任其 policy consumption
- 只能被外部 wrapper、tooling、artifact review、或 session boundary 治理

處理原則：
- 不把它當 injection target
- 只把它當 execution surface

## Observation 到 Decision 的最小耦合

> 詳細 observation signal 對照表見：
> [`docs/runtime-injection-observation-mapping.md`](runtime-injection-observation-mapping.md)

這一層最重要的不是產生更多 artifact，而是明確定義：

> 哪些 observation signal 會成為 enforcement 可依賴的 decision input

第一版先只接 context，不改 verdict。

目前可重用的第一批 signals：
- `surface_validity`
- `coverage_completeness`
- `memory_integrity`

後續可再拆成更細 observation，但第一版不需要。

## Minimal Slice

第一刀只做以下事情：

1. 定義 `runtime injection layer` 的四層責任邊界
2. 明確區分 `consumption observation` 與 `execution observation`
3. 定義 agent classification
4. 定義最小 canonical runtime injection snapshot 應包含哪些欄位
5. 指定第一個 consumer 與第一批 decision-coupled context fields

第一刀不做：
- multi-agent orchestration
- full adapter matrix
- automatic prompt rewriting
- dynamic token budgeting
- runtime hard gate
- verdict precedence rewrite

## 第一版 Canonical Runtime Injection Snapshot

在真正做 compiler 前，先固定一個最小 snapshot 形狀。

它至少應包含：
- source policy references
- selected runtime rules
- escalation triggers
- hard prohibitions
- context degradation note
- target agent class

這份 snapshot 是 compiler 的輸入目標，不代表現在就要做完整 generator。

## 第一個 Consumer

第一個 consumer 不應該是 runtime hard gate，而應該是：
- reviewer-facing interpretation surface
- adoption / run baseline evidence

原因：
- 可以先證明 injection/observation 資訊被消費
- 不會太早把不穩定信號升成 block condition

## 實作順序

### Step 1

先完成這份 plan，固定：
- 邊界
-責任
- agent 分類
- minimal slice

### Step 2

從 plan 萃出最小的 canonical runtime injection schema：
- 先做 schema
- 不先做 full compiler

### Step 3

只做一個 generic mapping：
- canonical source -> runtime injection snapshot
- 不碰 adapter-specific emission

### Step 4

再決定 observation 如何補 consumption signals，並與 decision_context 對接。

## 成功標準

這條線的 first slice 算成功，不是因為多了一份 YAML，而是因為：

1. injection / observation / enforcement 的責任不再混淆
2. agent classification 被明講，不再假設所有 agent 都適合 injection
3. observation 不再只是 artifact，而開始有明確 decision coupling target
4. 後續 schema 不會只是另一份 canonical file，而是有預定 consumer 的 runtime layer 輸入

## 邊界保護

這條線必須避免變成：
- 另一套 prompt-engineering system
- generic orchestration OS
- token packing optimizer

它應維持為：
- governance-aware runtime injection boundary
- observation-aware decision context substrate
- future enforcement input seam
