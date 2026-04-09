# Learning Governance Test Pack：learning / stability / falsifiability reviewer pack

> 參考 commits：`d32444d`、`f4e7d33`  
> Scenario 數量：16  
> 方法論來源：
> - `docs/anti-ritualization-patterns.md`
> - `docs/falsifiability-layer.md`
> - `docs/learning-loop.md`
> - `docs/learning-stability.md`
> - `docs/decision-quality-invariants.md`
> - `docs/governance-mechanism-tiers.md`

## 這份 pack 是什麼

這不是 conformance test pack。  
它的用途是：
- 檢查 reviewer 是否能正確判讀 learning / stability 類機制
- 驗證 reviewer 是否理解這些方法論之間的邊界
- 幫 framework owner 觀察目前教學與文件是否足夠

它**不是**：
- 直接驗證每個機制在 runtime 中都已完整實作
- 拿來取代對真實失敗案例的觀察

如果要測更偏 adversarial 的誤讀場景，請另外參考：
- `docs/adversarial-test-scenarios.md`

## 使用方式

每個 scenario 都要求 reviewer 做出 judgment。  
最基本流程是：
1. 閱讀 scenario
2. 根據方法論判斷
3. 產出 verdict
4. 檢查 reasoning 是否真的對應到 framework 文件中的邊界

這份 pack 不是 vocabulary quiz；重點是看 reviewer 能不能把 learning / stability / falsifiability 機制放回正確語境。

## 測試分段

### Part 1：Learning Loop Closure

重點：
- falsification 是否能形成 learning loop 閉環
- recurrence after `doc_updated` 是否能被辨識
- clean window 是否能被正確解讀

### Part 2：Root Cause Classification and Decay

重點：
- `cause_identified` / `cause_suspected` / `cause_unknown` 的區分
- classification confidence decay 是否被過度解讀
- absence of recurrence 是否被錯當 corroboration

### Part 3：Over-Correction Signals and Advisory Containment

重點：
- advisory signal 是否被誤當 gate
- advisory containment rule 是否被守住
- executable signal 是否被誤解成 authority

### Part 4：Falsifiability

重點：
- falsification condition 是否具體
- falsification 之後 explanation 是否應重估
- reviewer 是否會把 falsification 誤當成自動否決

### Part 5：Decision Quality Invariants

重點：
- consistency / robustness / positive falsifiability 的區分
- clean windows 是否被錯當成 decision correctness 證明

### Part 6：Governance Mechanism Tiers

重點：
- reviewer 是否能區分 enforceable / diagnostic / deferred
- calibration governance gap 是否被誤讀成 runtime failure

### Part 7：Anti-Ritualization

重點：
- counterfactual scaffold 是否真的存在
- reviewer 是否能辨識 ritualized reasoning

## 評分解讀

| Score | Interpretation |
|---|---|
| 15–16 | reviewer 對這組方法論有穩定理解，已接近 framework 預期 |
| 12–14 | 有 calibration gap，但大致能維持正確判讀 |
| 8–11 | 方法論理解仍不穩，需要回看 source docs |
| <8 | adoption 仍不足，建議先補 onboarding / baseline |

## 設計原則

這份 pack 的重點不是把每個 scenario 做成最難題，而是觀察 reviewer 是否會在 learning / stability / falsifiability 這條線上產生典型誤讀。

## 一句總結

這份 test pack 的用途，是讓 maintainer 看見 reviewer 對 learning governance 這條方法論線是否已形成穩定理解，而不是直接把它當成 runtime correctness 測試。
