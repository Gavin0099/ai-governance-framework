# Governance Mechanism Tiers：哪些機制可執行、哪些只能診斷、哪些仍是 deferred

> 版本：1.0  
> 相關文件：`docs/learning-loop.md`、`docs/learning-stability.md`、`docs/falsifiability-layer.md`、`docs/misinterpretation-log.md`、`docs/decision-quality-invariants.md`、`docs/anti-ritualization-patterns.md`

## 目的

隨著 framework 成熟，描述性語言與可執行規則看起來會越來越像。  
兩者都寫得很嚴謹，但 operational status 不一樣：

- 有些機制可以在 decision time 被檢查，違反時會導出**必須動作**
- 有些機制只能提出**必須面對的問題**
- 有些機制目前只能被承認為缺口

這份文件把主要機制分成三個 tier：

- **enforceable**
- **diagnostic**
- **deferred**

這不是重要性排名，而是目前 operational status 的說明。

## Tier Definitions

### Enforceable

一個機制屬於 enforceable，表示：

1. 可透過 log、artifact、或明確 reviewer behavior 重複檢查
2. positive result 會導出具體 required action
3. 兩個 reviewer 面對同樣輸入，應得到同樣結論

enforceable 代表 gate。沒檢查就是 governance failure。

### Diagnostic

一個機制屬於 diagnostic，表示：

1. 它提供一個應被面對的 signal
2. 這個 signal 本身不決定唯一的 required action
3. 合理 reviewer 仍可能得出不同解讀

diagnostic 代表 question，不代表 gate。

### Deferred

一個機制屬於 deferred，表示：

1. 問題已被命名
2. 目前因 instrumentation、baseline、或 calibration 不足，尚不能可靠 enforce 或 diagnose
3. deferred 是明示狀態，不是默默拖延

deferred 代表治理債。若沒有合理 promotion path，未來應明確關閉而不是一直懸著。

## 目前機制分布

### Learning Loop

| Mechanism | Tier | Notes |
|---|---|---|
| 每個 observed failure 都必須有 documented outcome | **Enforceable** | 沒有回應就是治理失敗 |
| `investigation_pending` 必須在下一個 observation window 轉換 | **Enforceable** | 無限 investigation 等同不作為 |
| `doc_updated` 若不改 reviewer behavior，就不算 learning response | **Enforceable** | 不是有寫文件就算完成 |
| recurrence after `doc_updated` 必須重審 prior response | **Enforceable** | 不可重複套用舊回應 |
| direction check after change | **Diagnostic** | 提出必須面對的問題，但不是 gate |
| untested assumptions naming | **Diagnostic** | 命名是必須的，全面調查不是 |

### Falsifiability Layer

| Mechanism | Tier | Notes |
|---|---|---|
| accepted proposal 必須有 falsification condition | **Enforceable** | 條件必須 specific / observable / time-bounded / decision-reversing |
| falsification 發生後必須有 documented re-evaluation | **Enforceable** | 不能默默忽略 |
| explanation drift guard | **Diagnostic** | 問題必須被回答，但不自動導出單一動作 |
| trajectory awareness | **Diagnostic** | 提供 proposal review 的上下文 |

### Misinterpretation Log

| Mechanism | Tier | Notes |
|---|---|---|
| expansion proposal gate：五題都要回答 | **Enforceable** | 回答不完整就退回 |
| counterfactual scaffold 四欄完整 | **Enforceable** | 含 least-confident 欄位 |
| rejected proposal 必須有 rejection reason | **Enforceable** | 否則無法區分 oversight |
| framework owner 必須有一行 justification | **Enforceable** | framework ownership 應保持稀缺 |
| re-raise rejected proposal 必須有新 evidence | **Enforceable** | 重複提交不算 re-raise |
| semantic grouping | **Diagnostic** | 邊界需 judgment |
| sampling bias check | **Diagnostic** | 需提出問題，不是自動動作 |

### Learning Stability

| Mechanism | Tier | Notes |
|---|---|---|
| Signal 2：same failure after two same-level responses | **Enforceable** | 必須升到 `model_adjusted` review |
| Signal 3：skepticism zone 逾期未退場 | **Enforceable** | 會 block 新 zone |
| `no_change_justified` 需 `cause_identified` | **Enforceable** | `cause_suspected` 不足以支撐 |
| classification confidence decay | **Diagnostic** | 仍依賴 per-category calibration |
| Signal 1 / 4 / 5 advisory family | **Diagnostic** | 只能影響 review 問題，不直接當 gate |
| advisory containment rule | **Enforceable** | advisory 不得越權成決策 authority |
| behavioral drift detection | **Diagnostic** | 缺 baseline 與 sample size |
| pre-decision bias detection | **Deferred** | tracing 不足以支撐 |

### Anti-Ritualization

| Mechanism | Tier | Notes |
|---|---|---|
| ritualization pattern detection | **Diagnostic** | 是警訊，不是自動處罰 |
| ritualization confirmed 後必須有 mechanism response | **Enforceable** | 不能只怪 reviewer |
| 不可用新機制去補 ritualized 舊機制 | **Enforceable** | 否則只會得到兩套 ritualized 機制 |

### Decision Quality Invariants

| Mechanism | Tier | Notes |
|---|---|---|
| consistency invariant | **Deferred** | 需要 matched-input 比較基礎設施 |
| robustness invariant | **Deferred** | 需要 deliberate probing |
| positive falsifiability | **Diagnostic** | 現在仍是 required question，不是 gate |
| misaligned success detection | **Diagnostic** | 需定期回顧，不可只看 failure rate |

### Boundary Crossing Protocol

| Mechanism | Tier | Notes |
|---|---|---|
| boundary condition detection | **Diagnostic** | 需 reviewer 能辨識哪一種 boundary |
| `defer_with_condition` | **Enforceable** | 必須有 resolution condition 與 deadline |
| `low_confidence_proceed` | **Enforceable** | 必須帶 boundary tag 與 re-evaluation trigger |
| `escalate` | **Enforceable** | 必須問具體、可回答的問題 |
| `hard_stop` | **Enforceable** | 僅限高風險邊界 |

## Calibration Governance Gap

有些機制雖然已 operable，但關鍵參數仍未被正式治理，例如：

- per-category N
- relevant observation 的定義
- negative pressure validity 的 interaction threshold
- evidence completeness relevance criteria
- behavioral drift baseline
- observation window size

在 formal calibration governance 出來前，這些值應被**顯式記錄**，不能默默讓 reviewer 各自調整。

## Deferred Item Summary

| Mechanism | Deferred because | Promotion condition |
|---|---|---|
| pre-decision bias detection | 缺 baseline 與 sample size | 定義 baseline 與最小 observation count |
| consistency invariant | 缺 matched-input sampling | 建立 reviewer agreement sampling protocol |
| robustness invariant | 反事實不可直接觀測 | 建立 deliberate probing protocol |
| positive falsifiability as gate | proposal format 尚未要求 | 將正向 falsifiability 納入 gate 後觀察一個 window |

## Reading Guidance

採用這份 framework 時，應檢查三件事：

1. enforceable 機制是否覆蓋你在乎的 failure modes
2. deferred gap 裡有沒有你無法接受的項目
3. calibration governance gap 是否會影響你要依賴的機制

## 一句話結論

這份 tier map 的目的，不是證明 framework 完整，而是誠實區分：哪些機制現在真的能 enforce，哪些只能提出問題，哪些仍然只是已命名的缺口。
