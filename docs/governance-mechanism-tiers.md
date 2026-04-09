# Governance Mechanism Tiers：哪些機制已可執行、哪些仍屬診斷或延後項

> 版本：1.0  
> 關聯文件：`docs/learning-loop.md`、`docs/learning-stability.md`、`docs/falsifiability-layer.md`、`docs/misinterpretation-log.md`、`docs/decision-quality-invariants.md`、`docs/anti-ritualization-patterns.md`

## 目的

這份文件用來區分 framework 內不同治理機制的 operational status。

它不是在列功能清單，而是在回答：
- 哪些機制已經能在 decision time 形成可執行約束
- 哪些機制目前只能提供診斷訊號
- 哪些機制仍屬 deferred，尚未有足夠 instrumentation / baseline / calibration

目前只使用三個 tier：
- **enforceable**
- **diagnostic**
- **deferred**

這能避免把所有概念都誤解成同等成熟。

## Tier Definitions

### Enforceable

要被視為 `enforceable`，至少要同時滿足：
1. 有可觀測的 log、artifact 或 reviewer behavior
2. positive result 對應到 required action
3. reviewer 之間對其後果有穩定共識

`enforceable` 代表這個機制可被視為 governance failure 的正式來源之一。

### Diagnostic

`diagnostic` 機制代表：
1. 能產生穩定、可解釋的 signal
2. 這個 signal 不直接等於 required action
3. 它主要服務於 triage、review 與 calibration

`diagnostic` 是問題，不是 gate。

### Deferred

`deferred` 機制代表：
1. 方向有價值
2. 但 instrumentation、baseline 或 calibration 尚不足
3. 目前不適合直接拿來 enforce 或 diagnose

`deferred` 不是永久放棄，而是暫時不宣稱 operational status。

## 目前機制分級

### Learning Loop

| Mechanism | Tier | Notes |
|---|---|---|
| observed failure 之後的 documented outcome | **Enforceable** | failure 必須對應到治理回應 |
| `investigation_pending` 的 observation window | **Enforceable** | 不允許 investigation 無限懸空 |
| `doc_updated` 後的 learning response | **Enforceable** | 文件更新要形成明確回應 |
| recurrence after `doc_updated` | **Enforceable** | 重複發生代表既有回應不足 |
| direction check after change | **Diagnostic** | 可看趨勢，但不是 gate |
| untested assumptions naming | **Diagnostic** | 幫助 reviewer 發現未知，不直接裁決 |

### Falsifiability Layer

| Mechanism | Tier | Notes |
|---|---|---|
| accepted proposal 必須有 falsification condition | **Enforceable** | 條件需具體、可觀測、可逆轉 decision |
| falsification 觸發後的 documented re-evaluation | **Enforceable** | 不允許 falsification 只存在文件中 |
| explanation drift guard | **Diagnostic** | 幫助檢查說法是否漂移 |
| trajectory awareness | **Diagnostic** | 幫助 proposal review 看見變化脈絡 |

### Misinterpretation Log

| Mechanism | Tier | Notes |
|---|---|---|
| expansion proposal gate 的記錄要求 | **Enforceable** | 需要留下被拒或被接受的理由 |
| counterfactual scaffold | **Enforceable** | 至少要保留最低限度反事實框架 |
| rejected proposal 的 rejection reason | **Enforceable** | 不允許無理由駁回 |
| framework owner justification | **Enforceable** | owner 決策要可追溯 |
| re-raise rejected proposal 的新 evidence 要求 | **Enforceable** | 沒有新證據，不應重提 |
| semantic grouping | **Diagnostic** | 幫助整理誤讀類型 |
| sampling bias check | **Diagnostic** | 幫助檢查觀測分布，不是 gate |

### Learning Stability

| Mechanism | Tier | Notes |
|---|---|---|
| Signal 2：same failure after two same-level responses | **Enforceable** | 應觸發 `model_adjusted` review |
| Signal 3：skepticism zone | **Enforceable** | 屬於可執行 zone rule |
| `no_change_justified` / `cause_identified` | **Enforceable** | `cause_suspected` 仍不足以關閉問題 |
| classification confidence decay | **Diagnostic** | 屬於 per-category calibration |
| Signal 1 / 4 / 5 advisory family | **Diagnostic** | 幫助 review，不直接 gate |
| advisory containment rule | **Enforceable** | advisory 不得越權成 authority |
| behavioral drift detection | **Diagnostic** | 仍依賴 baseline 與 sample size |
| pre-decision bias detection | **Deferred** | tracing 仍不足 |

### Anti-Ritualization

| Mechanism | Tier | Notes |
|---|---|---|
| ritualization pattern detection | **Diagnostic** | 幫助辨識形式化失真 |
| ritualization confirmed 後的 mechanism response | **Enforceable** | 確認後必須有回應 |
| 被認定為 ritualized 的機制不得當 authority | **Enforceable** | 防止形式化機制越權 |

### Decision Quality Invariants

| Mechanism | Tier | Notes |
|---|---|---|
| consistency invariant | **Deferred** | 仍缺 matched-input 量測 |
| robustness invariant | **Deferred** | 仍缺 deliberate probing |
| positive falsifiability | **Diagnostic** | 已是必要問題，但不是 hard gate |
| misaligned success detection | **Diagnostic** | 幫助辨識「看起來成功但其實退化」 |

### Boundary Crossing Protocol

| Mechanism | Tier | Notes |
|---|---|---|
| boundary condition detection | **Diagnostic** | 幫助 reviewer 看見 crossing moment |
| `defer_with_condition` | **Enforceable** | 必須留下 resolution condition 與 deadline |
| `low_confidence_proceed` | **Enforceable** | 必須留下 boundary tag 與 re-evaluation trigger |

## 一句總結

這份 tier 文件的作用，是防止 repo 把所有治理概念都講成同等成熟；只有當機制真正具備可觀測、可重建、可執行的條件時，才應被提升為 `enforceable`。
