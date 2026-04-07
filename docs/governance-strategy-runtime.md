# Governance Strategy Runtime

## 目的

這份文件定義 agent governance strategy 的動態決策機制：

- 如何從可觀測證據得出 classification（不是猜測）
- 當 runtime 狀態改變時，strategy 如何隨之轉換
- 如何偵測 strategy 與實際 runtime 的不一致（mismatch）

它是 `governance-strategy-matrix.md` 的執行層補丁。
矩陣定義了「各 class 要用什麼策略」；這份文件定義「class 是怎麼決定的，以及怎麼維持正確」。

---

## 核心修正：agent_class 是 session state，不是固有屬性

`governance-strategy-matrix.md` 定義了三個 agent class：
`instruction_capable` / `instruction_limited` / `wrapper_only`

但這個 classification **不是 agent 的固有屬性**，而是 **session-level 的觀測結果**。

同一個 agent surface 在不同情境下可以是不同 class：

| 情境 | effective class |
|------|----------------|
| local repo + CLAUDE.md loaded + hooks active | `instruction_capable` |
| CLI call + context truncated or degraded | `instruction_limited` |
| API call without hooks, no persistent instruction | `wrapper_only` |

這代表：

> classification 必須在每個 session 的 pre_task 階段重新觀測，不能假設跨 session 穩定。

---

## Classification Evidence Model

Classification 的來源必須是可觀測的 runtime 證據，而不是對 agent 品牌的靜態假設。

### Evidence Schema

```yaml
classification_evidence:
  # 可讀寫 repo 檔案（直接觀測）
  has_file_access:
    value: true | false
    source: observed | assumed
    note: "observed = 工具調用成功；assumed = 由 adapter type 推導"

  # 有效 persistent instruction 存在且被承載
  instruction_loaded:
    value: true | false | unknown
    source: observed | assumed
    note: "observed = CLAUDE.md/AGENTS.md 確認被讀取；unknown = 無法驗證"

  # context 完整性
  context_integrity:
    value: full | degraded | unknown
    source: observed | assumed
    note: "observed = 無截斷信號；degraded = 有截斷或 token warning"

  # pre/post hook 可攔截
  tool_gate:
    value: active | missing | unknown
    source: observed | assumed
    note: "observed = hook 執行成功；missing = 無 hook 記錄"
```

### Classification 決策規則

```
if tool_gate == missing OR trust_level == untrusted:
    → class = wrapper_only
    # tool gate 失效時，不管其他能力，必須降至 wrapper_only

elif context_integrity == degraded OR instruction_loaded == false:
    → class = instruction_limited
    # context 被截斷或指令未載入，injection 不可信

elif has_file_access == true
  AND instruction_loaded == true | unknown
  AND context_integrity == full | unknown
  AND tool_gate == active:
    → class = instruction_capable
    # 全部 observed 或合理假設為 capable

else:
    → class = instruction_limited  # 保守 default
```

**原則：不確定時往下分類（保守）**，而不是往上假設能力。

---

## Strategy Transition Graph

Strategy 不是 session 開始時設定一次就不動了。以下情況必須觸發 class 降級：

### Transition Rules

```
[instruction_capable] ──(context_degraded detected)──→ [instruction_limited]
[instruction_capable] ──(tool_gate_missing detected)──→ [wrapper_only]
[instruction_limited] ──(tool_gate_missing detected)──→ [wrapper_only]
```

降級是單向的，同一個 session 內不得升級：

> session 內的 capability 只能降低，不能被後來的信號「恢復」。
> 一旦 `tool_gate` 失效或 `context_degraded`，本 session 的 strategy 保持降級到結束。

### 觸發降級的 runtime signals

| Signal | 觸發條件 | 降級方向 |
|--------|---------|---------|
| `context_degraded` | token budget warning / truncation detected | capable → limited |
| `tool_gate_missing` | pre_task hook 未執行 / hook record absent | any → wrapper_only |
| `instruction_load_failed` | CLAUDE.md/AGENTS.md 讀取失敗 | capable → limited |
| `trust_level_downgraded` | runtime risk signal 觸發 trust 調整 | any → lower class |

---

## Strategy Mismatch Detection

當 session 的宣告策略（`governance_strategy`）與實際 runtime 觀測不一致時，
需要產生可見的 risk signal。

### Mismatch Rules

**Rule 1：Injection claimed but not observable**

```
if governance_strategy IN ["injection+enforcement", "minimal_injection+enforcement"]
AND consumption_observation.injection_payload_loaded == false | unknown:
    → risk: injection_ineffective
    → advisory: "injection payload cannot be confirmed; enforcement path must be treated as sole active layer"
```

**Rule 2：Enforcement claimed but hook absent**

```
if governance_strategy IN ["injection+enforcement", "no_injection+strict_enforcement"]
AND tool_gate == missing:
    → risk: enforcement_gap
    → advisory: "pre/post hook not active; governance path reduced to artifact review only"
```

**Rule 3：Capable strategy with degraded context**

```
if governance_strategy == "injection+enforcement"
AND context_integrity == degraded:
    → risk: strategy_drift
    → advisory: "session context degraded; injection payload reliability reduced; consider reclassifying to instruction_limited"
```

**Rule 4：No strategy recorded**

```
if governance_strategy == null | missing:
    → risk: unclassified_session
    → advisory: "governance strategy not declared; treating session as instruction_limited with conservative enforcement"
```

### Mismatch 的處置原則

- Mismatch 觸發 **advisory signal**，不直接 block（除非是 `enforcement_gap` 且無任何 fallback）
- Mismatch signal 進入 `decision_context`，供 reviewer 和後續 session 參考
- 系統不應試圖「自動修正」mismatch；它只負責讓問題可見

---

## Runtime 欄位更新

以下欄位在 `session_start` 或 `pre_task_check` 輸出中記錄：

### `classification_evidence`（新增）

記錄 classification 的觀測來源，讓 reviewer 知道 class 是 observed 還是 assumed：

```yaml
classification_evidence:
  has_file_access: observed
  instruction_loaded: observed
  context_integrity: full
  tool_gate: active
```

### `effective_agent_class`（新增）

記錄本 session 的實際 class（區別於 adapter 的靜態假設）：

```
effective_agent_class: "instruction_capable"
                     | "instruction_limited"
                     | "wrapper_only"
```

### `governance_strategy`（已在 matrix 定義，這裡補觸發邏輯）

由 `effective_agent_class` 自動派生：

```
instruction_capable  → "injection+enforcement"
instruction_limited  → "minimal_injection+enforcement"
wrapper_only         → "no_injection+strict_enforcement"
```

### `injection_reliance`（已在 matrix 定義）

```
injection_reliance: "none"    # 目前所有已知 session 應為 none
                  | "partial" # 需要說明 enforcement 的哪個判斷點依賴了 injection
                  | "high"    # 架構警告：必須審查
```

---

## 與現有 runtime 的整合點

| 現有路徑 | 整合點 | 說明 |
|---------|-------|------|
| `session_start.py` | 記錄 `classification_evidence` + `effective_agent_class` | 在 session init 時做第一次 classification |
| `pre_task_check.py` | 重新觀測 `context_integrity` + `tool_gate` | 每次 task 前重評，觸發 transition rule |
| `session_end.py` | 輸出 `governance_strategy` 進 artifact | 讓 reviewer 看到本 session 走的治理路徑 |
| `decision_context` | 傳遞 `classification_evidence` + `strategy_mismatch` | 讓後續 session 能參考歷史狀態 |

---

## 邊界

這份文件不負責：
- 定義各 class 的具體 injection payload 內容（見 `runtime-injection-layer-plan.md`）
- 定義 observation signal 的完整清單（見 `runtime-injection-observation-mapping.md`）
- 定義各 class 的策略內容（見 `governance-strategy-matrix.md`）

它只負責：
- 從 runtime 證據推導 `effective_agent_class`
- 定義 class 降級的單向規則
- 偵測 strategy mismatch 並產生可見 signal
- 定義三個新 runtime 欄位：`classification_evidence` / `effective_agent_class` / mismatch signals
