# Governance Strategy Runtime：runtime 如何決定治理姿態

## 目的

這份文件定義 runtime 如何從 session evidence 推出：

- `effective_agent_class`
- `governance_strategy`
- `injection_reliance`

它不是 capability truth model，而是**session-level 保守治理分類**。

## 核心觀念

`governance-strategy-matrix.md` 定義的是抽象策略。  
本文件定義的是 runtime 在某個 session 中，如何根據 evidence 選擇對應策略。

重點是：

- classification 是 session-level，不是永久人格
- downgrade 合法，upgrade 視為 anomaly
- runtime 只做保守收斂，不做能力膨脹

## 基本 evidence

runtime 目前主要依賴這幾類 classification evidence：

```yaml
classification_evidence:
  has_file_access: true | false | unknown
  instruction_loaded: true | false | unknown
  context_integrity: full | degraded | unknown
  tool_gate: active | missing | unknown
```

更細語義見：

- `docs/classification-evidence-semantics.md`

## 基本分類規則

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

這是保守規則，不是 capability truth。

## Strategy Mapping

由 `effective_agent_class` 對應策略：

| effective_agent_class | governance_strategy | injection_reliance |
|---|---|---|
| `instruction_capable` | `injection+enforcement` | `none` |
| `instruction_limited` | `minimal_injection+enforcement` | `none` |
| `wrapper_only` | `no_injection+strict_enforcement` | `none` |

目前預設 `injection_reliance` 維持 `none`，避免 enforcement 被 advisory injection 取代。

## 合法 Transition

合法 downgrade：

- `instruction_capable -> instruction_limited`
- `instruction_capable -> wrapper_only`
- `instruction_limited -> wrapper_only`

非法 upgrade：

- `instruction_limited -> instruction_capable`
- `wrapper_only -> instruction_limited`
- `wrapper_only -> instruction_capable`

非法 upgrade 應進 anomaly path，而不是真的升級 class。

## Strategy Mismatch Detection

runtime 應額外檢查：

### 1. Injection claimed but not observable

如果策略宣稱有 injection，但 consumption observation 不存在：

- 產生 `injection_ineffective` advisory
- reviewer 應把 enforcement 視為唯一可信層

### 2. Enforcement claimed but hook missing

如果策略宣稱有 enforcement，但 `tool_gate == missing`：

- 產生 `enforcement_gap` advisory
- session 應被視為退化到 wrapper / artifact review posture

### 3. Capable strategy with degraded context

如果策略仍是 `injection+enforcement`，但 context 已 degraded：

- 產生 `strategy_drift` advisory
- 應考慮保守 downgrade 到 `instruction_limited`

### 4. No strategy recorded

如果 session 沒有寫下策略：

- 產生 `unclassified_session` advisory
- runtime 應退回保守解讀

## Runtime 輸出位置

目前這些欄位應出現在：

- `session_start`
- `session_end`
- `decision_context`
- reviewer-facing summary / trace

## 非目標

這份文件目前**不做**：

- 以策略直接改寫 enforcement threshold
- mid-session 反覆重算 classification
- 讓 downgrade 直接 block session

## 一句話結論

這份文件做的不是證明 agent 真實能力，而是讓 runtime 根據可觀測 evidence，保守地選擇該用哪種 governance strategy。
