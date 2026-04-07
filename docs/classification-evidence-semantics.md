# Classification Evidence Semantics

## 目的

這份文件定義每個 `classification_evidence` 欄位的語義邊界。

它只做三件事：

1. 每個欄位代表什麼（証明能力範圍）
2. 每個欄位**不能**代表什麼（不得推論的結論）
3. 哪些欄位只是 presence evidence，哪些接近 stronger observation

**為什麼需要這份文件**

治理系統最常見的語義錯誤不是欄位缺失，而是欄位名稱比證據本身更強。
例如 `instruction_loaded: true` 看起來像 consumption evidence，但實際上只是 availability evidence。
如果 reviewer 把 proxy 當 truth 讀，整條治理路徑的風險判斷都會偏低。

---

## 兩層證據分類

| 層級 | 定義 | 能支撐的結論 |
|------|------|-------------|
| **Presence evidence** | 某個 surface 或 capability 的存在被確認 | 治理前提條件存在；不能推論實際被消費或正確執行 |
| **Observation evidence** | 某個 action 或 state 被直接觀測到 | 可以支撐更強的治理結論，但仍需說明觀測方式 |

---

## 欄位語義表

### `has_file_access`

**目前 proxy 行為**：`True` / `observed`，因為 session_end 能執行 I/O

**代表什麼**：
- runtime process（本 hook script）對 repo 有讀寫能力
- host-level file access 已確認

**不能代表什麼**：
- agent surface（AI model 本身）是否具備 file access
- 這個 session 的任何具體 tool call 是否真的讀了 repo 檔案
- 未來 agent 版本或不同 surface 是否仍然有 file access

**精確名稱（下一版考慮）**：`runtime_repo_access_observed`

**注意**：host capability ≠ agent capability。這個 proxy 觀測的是 runtime environment，不是 agent surface。

---

### `instruction_loaded`

**目前 proxy 行為**：檢查 CLAUDE.md / AGENTS.md 是否存在

**代表什麼**：
- instruction surface 存在於 repo（availability）
- agent 有機會讀到這份文件（precondition）

**不能代表什麼**：
- agent 這一輪是否真的讀了這份文件
- agent 是否把 instruction 吃進 context（consumption）
- agent 對 instruction 的理解是否正確（interpretation）
- instruction 是否未被 context compression 壓掉

**精確名稱（下一版考慮）**：`instruction_surface_present`

**注意**：這是 presence evidence，不是 consumption evidence。用 `instruction_loaded` 作為欄位名稱會讓 reviewer 誤以為有更強的保證。

---

### `context_integrity`

**目前 proxy 行為**：掃描 checks.warnings / checks.errors 的特定 keyword（truncat / context_degraded / token_budget / token_warning）

**代表什麼**：
- 如果有匹配：post-task checks 中出現了 context degradation signal，這是 `degraded` 的 observed 依據
- 如果無匹配：沒有觀測到已知 degradation signal（不等於確定 full）

**不能代表什麼**：
- context 真的沒有被壓縮或截斷（absence of signal ≠ absence of problem）
- 沒有 warning 就代表 instruction 完整被接收
- token 使用量是否接近 limit

**現行預設 `full` 的風險**：
> `context_integrity: full` 的 default 應該被視為 `unknown` 的保守代號，
> 而不是「確認 context 完整」。
> 如果沒有 affirmative degradation signal，頂多能說「未觀測到 degradation」，
> 不能說「context 是 full 的」。

**建議**：下一版考慮把 default 改為 `unknown`，只在有 affirmative observation 時才設為 `full`。

---

### `tool_gate`

**目前 proxy 行為**：`active` / `observed`，因為 session_end hook 正在執行

**代表什麼**：
- session closeout boundary 有被攔截（session_end 執行了）
- session 邊界級別的 hook 路徑存在

**不能代表什麼**：
- pre_task hook 是否確實執行過
- post_task hook 是否確實執行過
- 整個 session 期間每一個 task 都有完整 pre/post interception
- 未來 session 的 hook 路徑仍然有效

**精確描述（下一版考慮拆分）**：

```
session_boundary_observed: true       # session_end hook 執行
pre_task_hook_observed: true | false | unknown
post_task_hook_observed: true | false | unknown
```

**注意**：「到達 session_end」只能證明 closeout path 有執行，
不能推論整個 session 都有完整的 pre/post gate 覆蓋。
這是目前三個 proxy 中最容易高估 agent class 的一個。

---

## 綜合風險評估

| 欄位 | 實際層級 | 命名暗示層級 | 風險等級 |
|------|---------|------------|---------|
| `has_file_access` | host process capability | agent capability | 中 — 容易混淆 runtime 和 agent |
| `instruction_loaded` | presence（file exists） | consumption（file was read） | 高 — 直接誤導 reviewer |
| `context_integrity` | signal absence | confirmed full | 中 — default full 過於自信 |
| `tool_gate` | closeout boundary | full session gate coverage | 高 — 暗示完整 interception |

---

## 目前 classification 的正確定位

基於以上語義邊界，目前這套 classification 的準確定義是：

> **第一版 proxy-based governance classification**
>
> 這不是 capability truth model，而是：
> 系統根據目前可得的 proxy evidence，
> 對本 session 的治理路徑做出保守推論，
> 並讓 reviewer 能追溯推論依據。

這個定義允許：
- reviewer 看到 session 如何被分類
- reviewer 看到分類的依據是什麼
- reviewer 質疑依據是否足夠

這個定義不允許：
- 把 `instruction_capable` 當成 agent capability 的保證
- 把 `injection+enforcement` 當成 injection 確實有效的保證
- 把 `tool_gate: active` 當成所有 task 都被 gated 的保證

---

## Strategy Transition 的語義缺口（待補）

目前 `classification_evidence` 在 session_start 和 session_end 各做一次，但沒有對比機制。

需要補的欄位：

```
initial_agent_class: "instruction_capable"
effective_agent_class: "instruction_capable" | <downgraded value>
classification_changed: true | false
reclassification_reason: null | <signal that triggered downgrade>
```

只有這四個欄位存在，才能說系統有一個完整的 classification control loop，
而不只是「前後各做一次標記」。

這個補丁見：`docs/governance-strategy-runtime.md` 的 Transition Rules 章節，
那裡已有規則定義，但目前還沒有 runtime 欄位對應。

---

## 邊界

這份文件不負責：
- 決定現在要不要改欄位名稱（改名有向後相容成本）
- 定義更強的 observation signal 的收集方式
- 改動 classification_evidence schema

它只負責：
- 讓任何讀 `classification_evidence` 的人知道每個欄位代表什麼
- 讓任何寫新 evidence signal 的人知道不要跨越 presence → consumption 的語義邊界
- 防止 reviewer 把弱 proxy 當強保證
