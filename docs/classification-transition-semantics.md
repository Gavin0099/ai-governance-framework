# Classification Transition Semantics：classification 如何合法變動

## 目的

這份文件定義 `effective_agent_class` 與 `initial_agent_class` 之間的合法 transition。

它要回答三件事：

1. 哪些 transition 合法
2. `reclassification_reason` 要落在哪個 taxonomy
3. downgrade / upgrade 應對 runtime 帶來什麼 reaction

這份文件和 `docs/classification-evidence-semantics.md` 的分工是：

- evidence semantics：各 evidence 欄位代表什麼
- transition semantics：evidence 被 runtime 解讀後，classification 可以怎麼變

---

## 合法 transition 表

```text
[instruction_capable]  -> [instruction_limited]   LEGAL
[instruction_capable]  -> [wrapper_only]          LEGAL
[instruction_limited]  -> [wrapper_only]          LEGAL

[instruction_limited]  -> [instruction_capable]   ILLEGAL
[wrapper_only]         -> [instruction_limited]   ILLEGAL
[wrapper_only]         -> [instruction_capable]   ILLEGAL
```

### 為什麼 upgrade 不合法

同一個 session 內，capability proxy 最多只能支持保守 downgrade，不能支持 upgrade。

原因：

- classification evidence 觀測到的是 proxy，不是 capability truth
- proxy 的強訊號不代表 session 內真的獲得更高 capability
- 若允許 upgrade，任何偶發 anomaly 都可能把 classification 撐高

所以：

- downgrade 是保守收斂
- upgrade 則代表 proxy inconsistency 或 schema anomaly

---

## `reclassification_reason` taxonomy

每次 classification 發生變動，都應給一個可解釋的 reason。

目前 taxonomy：

| Reason | 觸發條件 | 說明 |
|---|---|---|
| `context_degraded` | `context_integrity == degraded` | affirmative degradation signal |
| `instruction_load_failed` | `instruction_loaded == false` | instruction surface 缺失 |
| `tool_gate_missing` | `tool_gate == missing` | closeout / gating surface 缺失 |
| `conservative_downgrade` | 其他保守收斂情況 | default downgrade reason |
| `classification_anomaly_upgrade` | `effective_order > initial_order` | 非法 upgrade，代表 anomaly |

`null` 表示 classification 沒有變動，或 `initial_agent_class` 本身不存在。

---

## Runtime Reaction

### 合法 Downgrade

觸發條件：

- `classification_changed == True`
- `reclassification_reason != classification_anomaly_upgrade`

系統反應：

1. `governance_strategy` 或 `decision_context` 反映更保守的 posture
2. `session_end warnings[]` 寫入 advisory warning
3. `reclassification_reason` 進入 reviewer 可見 surface

例：

```text
governance: classification_downgrade from 'instruction_capable' to 'instruction_limited'
(reason: context_degraded); governance_strategy tightened to 'minimal_injection+enforcement'
```

### 非法 Upgrade（Anomaly）

觸發條件：

- `classification_changed == True`
- `effective class > initial class`

系統反應：

1. `reclassification_reason` 固定為 `classification_anomaly_upgrade`
2. `session_end warnings[]` 記錄 anomaly warning
3. effective class 不應真的被當成新的 authority 來源

例：

```text
governance: classification_anomaly -- agent class upgraded from 'instruction_limited'
to 'instruction_capable' within session; upgrades are unexpected and may indicate
proxy inconsistency
```

---

## 進入 artifact 的欄位

| 欄位 | 出現位置 | 用途 |
|---|---|---|
| `initial_agent_class` | `session_start` / `session_end` | 保留起始 classification |
| `effective_agent_class` | `session_end` | 記錄最終 class |
| `classification_changed` | `session_end` | 是否發生 transition |
| `reclassification_reason` | `session_end` | 給 reviewer 的解釋 taxonomy |
| downgrade warning | `warnings[]` | reviewer-visible warning |
| upgrade anomaly warning | `warnings[]` | anomaly flag |

---

## 非目標

這份文件目前**不做**：

- 以 downgrade 直接改 enforcement threshold
- mid-session checkpoint 重算 classification
- 因 downgrade 而 block session

它只做：

- transition 合法性定義
- `reclassification_reason` taxonomy
- 對應的 runtime reaction 與 reviewer-visible 記錄
