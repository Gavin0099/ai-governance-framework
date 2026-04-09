# Governance Strategy Runtime：runtime 如何決定 session 的治理姿態

## 目的

這份文件定義 runtime 應如何根據 session evidence 推導：
- `effective_agent_class`
- `governance_strategy`
- `injection_reliance`

這不是 capability truth model，而是**session-level 的治理判斷面**。

## 核心說明

`governance-strategy-matrix.md` 定義的是靜態策略對照表。  
這份文件則說明 runtime 如何在每次 session 中根據可觀測 evidence，推導出實際可用的治理策略。

重點包括：
- classification 是 session-level，不是產品級永久標籤
- downgrade 是正常路徑，upgrade 通常屬於 anomaly
- runtime 只應根據可觀測證據做保守判定

## 分類 evidence

runtime 目前可依賴的最小 classification evidence：

```yaml
classification_evidence:
  has_file_access: true | false | unknown
  instruction_loaded: true | false | unknown
  context_integrity: full | degraded | unknown
  tool_gate: active | missing | unknown
```

相關語義文件：
- `docs/classification-evidence-semantics.md`

## 推導規則

```text
if tool_gate == missing:
    effective_agent_class = wrapper_only

elif context_integrity == degraded or instruction_loaded == false:
    effective_agent_class = instruction_limited

elif has_file_access == true and tool_gate == active:
    effective_agent_class = instruction_capable

else:
    effective_agent_class = instruction_limited
```

這是一套保守推導規則，不是 capability truth。

## Strategy Mapping

由 `effective_agent_class` 對應出治理策略：

| effective_agent_class | governance_strategy | injection_reliance |
|---|---|---|
| `instruction_capable` | `injection+enforcement` | `none` |
| `instruction_limited` | `minimal_injection+enforcement` | `none` |
| `wrapper_only` | `no_injection+strict_enforcement` | `none` |

目前把 `injection_reliance` 固定為 `none`，表示 enforcement 不應依賴 advisory injection 的成功與否。

## Phase Transition

常見 downgrade：
- `instruction_capable -> instruction_limited`
- `instruction_capable -> wrapper_only`
- `instruction_limited -> wrapper_only`

可能的 upgrade：
- `instruction_limited -> instruction_capable`
- `wrapper_only -> instruction_limited`
- `wrapper_only -> instruction_capable`

其中 upgrade 通常屬於 anomaly path，需要額外證據，不應輕易假設。

## Strategy Mismatch Detection

runtime 應檢查以下失配情況：

### 1. Injection claimed but not observable

如果策略宣稱依賴 injection，但 consumption observation 不成立：
- 產生 `injection_ineffective` advisory
- reviewer 應回頭檢查 enforcement 是否仍然完整

### 2. Enforcement claimed but hook missing

如果策略宣稱有 enforcement，但 `tool_gate == missing`：
- 產生 `enforcement_gap` advisory
- session 應退回 wrapper / artifact review posture

### 3. Capable strategy with degraded context

如果策略是 `injection+enforcement`，但 context 已 degraded：
- 產生 `strategy_drift` advisory
- 應考慮把有效 class 降到 `instruction_limited`

### 4. No strategy recorded

如果 session 沒有記錄策略：
- 產生 `unclassified_session` advisory
- runtime 不應假裝自己已完成治理分類

## Runtime 寫入位置

目前這些欄位適合出現在：
- `session_start`
- `session_end`
- `decision_context`
- reviewer-facing summary / trace

## 非目標

這份文件目前**不做**：
- 自動調整 enforcement threshold
- mid-session 持續重分類
- 僅因 downgrade 就直接 block session

## 一句總結

這份文件不是在說 agent 本身是什麼，而是在說 runtime 如何根據每次 session 的可觀測 evidence，保守地決定這次應採用哪種治理策略。
