# Classification Transition Semantics：classification 轉換的合法性與原因

## 目的

這份文件定義 `effective_agent_class` 與 `initial_agent_class` 之間的 transition 語義。
它回答三件事：

1. 哪些 transition 合法
2. `reclassification_reason` 應如何進入 taxonomy
3. downgrade / upgrade 在 runtime 中應如何被解讀

它與 `docs/classification-evidence-semantics.md` 的分工是：
- evidence semantics：每個 evidence 欄位代表什麼
- transition semantics：evidence 被 runtime 使用後，classification 可以怎麼變

---

## 合法 transition 圖

```text
[instruction_capable]  -> [instruction_limited]   LEGAL
[instruction_capable]  -> [wrapper_only]          LEGAL
[instruction_limited]  -> [wrapper_only]          LEGAL

[instruction_limited]  -> [instruction_capable]   ILLEGAL
[wrapper_only]         -> [instruction_limited]   ILLEGAL
[wrapper_only]         -> [instruction_capable]   ILLEGAL
```

### 為什麼 upgrade 被視為異常

在目前的 session-level governance posture 下，classification evidence 更適合支持 downgrade，而不適合支持 upgrade。原因是：
- classification evidence 仍是 proxy，不是 capability truth
- proxy 在單次 session 中較容易證明缺失，不容易證明高能力
- 因此 upgrade 應被視為 anomaly，需要額外審查，而不是正常重新分類

換句話說：
- downgrade 是保守收斂
- upgrade 是 proxy inconsistency 或 evidence anomaly

---

## `reclassification_reason` taxonomy

當 classification 發生變化時，必須帶出明確 reason。
目前 taxonomy 如下：

| Reason | 觸發條件 | 說明 |
|---|---|---|
| `context_degraded` | `context_integrity == degraded` | affirmative degradation signal |
| `instruction_load_failed` | `instruction_loaded == false` | instruction surface 不成立 |
| `tool_gate_missing` | `tool_gate == missing` | closeout / gating surface 不成立 |
| `conservative_downgrade` | 證據不足以維持原始 class | default downgrade reason |
| `classification_anomaly_upgrade` | `effective_order > initial_order` | 異常 upgrade，需要額外審查 |

`null` 只應出現在 classification 沒有發生變化，或 `initial_agent_class` 本來就未知的情況。

---

## Runtime Reaction

### 合法 Downgrade

觸發條件：
- `classification_changed == True`
- `reclassification_reason != classification_anomaly_upgrade`

runtime 應：
1. 在 `decision_context` 中收緊 `governance_strategy`
2. 於 `session_end warnings[]` 追加 advisory warning
3. 把 `reclassification_reason` 暴露到 reviewer-facing surface

範例：

```text
governance: classification_downgrade from 'instruction_capable' to 'instruction_limited'
(reason: context_degraded); governance_strategy tightened to 'minimal_injection+enforcement'
```

### 異常 Upgrade

觸發條件：
- `classification_changed == True`
- `effective class > initial class`

runtime 應：
1. 標記 `classification_anomaly_upgrade`
2. 不把它當成正常能力提升
3. 讓 reviewer 看到這是一個 anomaly，而不是成功升級

## 非目標

這份文件目前**不做**：
- mid-session 多次重分類
- 把 anomaly upgrade 自動轉為 hard failure
- 以 transition 本身直接修改 final verdict

## 一句總結

classification transition semantics 的重點不是讓系統更積極地升級 agent class，而是讓 runtime 以保守、可審計的方式處理 downgrade，並把 upgrade 視為需額外說明的 anomaly。
