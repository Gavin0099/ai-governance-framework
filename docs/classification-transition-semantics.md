# Classification Transition Semantics

## 目的

這份文件定義 `effective_agent_class` 狀態機的轉移規則。

它只做三件事：

1. 哪些 transition 合法（transition table）
2. `reclassification_reason` 的受控允許值（taxonomy）
3. downgrade / upgrade 各自觸發的 runtime reaction

這是 `docs/classification-evidence-semantics.md` 的延伸，
那份文件說清楚「每個欄位代表什麼」；
這份文件說清楚「狀態改變本身受什麼規則約束，以及系統如何反應」。

---

## 合法 Transition 表

```
[instruction_capable]  ──(downgrade)──→  [instruction_limited]   LEGAL
[instruction_capable]  ──(downgrade)──→  [wrapper_only]          LEGAL
[instruction_limited]  ──(downgrade)──→  [wrapper_only]          LEGAL

[instruction_limited]  ──(upgrade)───→  [instruction_capable]   ILLEGAL
[wrapper_only]         ──(upgrade)───→  [instruction_limited]   ILLEGAL
[wrapper_only]         ──(upgrade)───→  [instruction_capable]   ILLEGAL
```

### 為什麼 upgrade 不合法

Session 內的 capability 只能降低，不能恢復。

根本原因是：
- classification evidence 都是 proxy（非 capability truth）
- proxy 可能在 session 不同時間點給出不同結果（不穩定訊號）
- 「升回去」不代表能力真的恢復，更可能代表 proxy 訊號不一致

因此：
- downgrade：訊號顯示能力喪失 → 應保守接受，更新策略
- upgrade：訊號顯示能力回升 → 應視為異常訊號，不更新策略，記錄 anomaly

具體後果：session 內的 effective_agent_class 可以因 downgrade signal 而下調，
但 **不得因後續訊號重新上調**。
一旦降級，本 session 的 governance_strategy 維持在降級後的狀態直到 session 結束。

> 注意：這個規則適用於「同一 session 內的前後對比」。
> 不同 session 各自重新分類，不受前 session 結果約束。

---

## `reclassification_reason` 受控允許值

這個欄位只允許以下有限值集合，不接受任意字串。
有限 taxonomy 是為了讓 downgrade 能被機器聚合、統計、比較。

| 值 | 觸發條件 | 說明 |
|----|---------|------|
| `"context_degraded"` | context_integrity == "degraded" | affirmative degradation signal 被觀測到 |
| `"instruction_load_failed"` | instruction_loaded == "false" | instruction surface 確認不可得 |
| `"tool_gate_missing"` | tool_gate == "missing" | hook 路徑確認缺失 |
| `"conservative_downgrade"` | 以上皆非但仍降級 | 保守 default 觸發（例如 else 分支） |
| `"classification_anomaly_upgrade"` | effective_order > initial_order | **非法升級**，標記為 proxy 不一致 |

`null`：classification 未發生變化，或 initial_agent_class 不可得（無對比基礎）。

### 注意

`"conservative_downgrade"` 應該是少見值。
如果它在統計上高頻出現，代表分類決策邏輯有漏洞或邊界條件沒被處理，需要審查。

`"classification_anomaly_upgrade"` 永遠不應出現在正常 session 中。
如果它出現，代表 proxy 訊號在 session 內不一致，需要調查觸發條件。

---

## Runtime Reaction

### Downgrade（legitimate）

**觸發條件**：`classification_changed == True` 且 `reclassification_reason` 不是 `"classification_anomaly_upgrade"`

**System 動作**：
1. `governance_strategy` 在 `decision_context` 中自動反映降級後的策略（已實作）
   - `instruction_capable → instruction_limited`：strategy 變為 `minimal_injection+enforcement`
   - `any → wrapper_only`：strategy 變為 `no_injection+strict_enforcement`
2. 在 session_end `warnings` 中發出 advisory warning（已實作）：
   ```
   governance: classification_downgrade — 'instruction_capable' → 'instruction_limited'
   (reason: context_degraded); governance_strategy tightened to 'minimal_injection+enforcement'
   ```
3. `reclassification_reason` 記錄進 `decision_context`，供 reviewer 追溯（已實作）

**注意**：downgrade 不 block session，只發 warning。
Block 屬於 enforcement layer 的責任，不是 classification layer 的責任。

---

### Upgrade（anomaly）

**觸發條件**：`classification_changed == True` 且 effective class 比 initial class 「更高」

**System 動作**：
1. `reclassification_reason` 設為 `"classification_anomaly_upgrade"`（已實作）
2. 在 session_end `warnings` 中發出 anomaly warning（已實作）：
   ```
   governance: classification_anomaly — agent class upgraded from 'instruction_limited'
   to 'instruction_capable' within session; upgrades are unexpected and may indicate
   proxy inconsistency
   ```
3. **Effective class 維持降級後的值**，不採用「升級」後的值

> **注意（重要）**：目前的 runtime 實作中，`effective_agent_class` 確實會反映
> 後期 proxy 算出的「較高」值，因為 session_end 的計算是獨立的。
> 這個規則指出：**在 session 內不應信任升級**，但目前實作尚未在 session 內
> 強制鎖定 class（那需要 mid-session checkpoint，目前不在範圍內）。
> 此處的 runtime reaction 是 warning + anomaly flag，不是自動 override。
> 真正的強制鎖定是未來工作。

---

## 與現有欄位的對應

| 欄位 | 存放位置 | 狀態 |
|------|---------|------|
| `initial_agent_class` | session_end: decision_context | 已實作 |
| `effective_agent_class` | session_end: decision_context | 已實作 |
| `classification_changed` | session_end: decision_context | 已實作 |
| `reclassification_reason` | session_end: decision_context | 已實作（taxonomy 受控） |
| downgrade warning | session_end: warnings[] | 已實作 |
| upgrade anomaly warning | session_end: warnings[] | 已實作 |

---

## 邊界

這份文件不負責：
- 定義 enforcement 在 downgrade 之後如何收緊 threshold（見 governance-strategy-matrix.md）
- 定義 mid-session checkpoint（目前 classification 只有 start + end 兩點）
- 定義什麼情況下 downgrade warning 應升為 block（那是 enforcement layer 決定的）

它只負責：
- 定義哪些 transition 合法
- 鎖定 reclassification_reason 的允許值集合
- 說明每種 transition 觸發的 runtime reaction
- 說明「anomaly upgrade」的語義與目前實作的限制
