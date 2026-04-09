# Learning Governance Test Pack：learning / stability / falsifiability 的一致性測試包

> 涵蓋 commits：`d32444d` 到 `f4e7d33`  
> Scenario 數量：16  
> 通過分數：15–16  
> 測試文件：
> - `docs/anti-ritualization-patterns.md`
> - `docs/falsifiability-layer.md`
> - `docs/learning-loop.md`
> - `docs/learning-stability.md`
> - `docs/decision-quality-invariants.md`
> - `docs/governance-mechanism-tiers.md`

## 這份 pack 在測什麼

這是一份 **conformance test pack**。

它測的是：

- 各機制是否能被正確理解
- reviewer 是否能在現實情境中正確套用這些機制
- framework 內部邏輯是否一致

它**不測**：

- 這些機制是否保證產生外部正確決策
- 外部穩健性是否成立

要測外部穩健性，請看：

- `docs/adversarial-test-scenarios.md`

## 使用方式

每個 scenario 都會給一個情境，要求 reviewer 做出 judgment。

建議流程：

1. 先只看 scenario
2. 寫下自己的答案
3. 再看 verdict
4. 如果答案不同，先比較 reasoning，再決定是自己錯還是 verdict 有問題

這份 pack 不是 vocabulary quiz，而是看你能不能在表面不明顯的情境下，依據 framework 規則做出正確判斷。

## 內容結構

### Part 1：Learning Loop Closure

測的是：

- falsification 出現後，learning loop 是否真的閉環
- recurrence after `doc_updated` 是否被正確重審
- clean window 是否被過度樂觀解讀

### Part 2：Root Cause Classification and Decay

測的是：

- `cause_identified` / `cause_suspected` / `cause_unknown` 的區分
- classification confidence decay 是否被正確理解
- absence of recurrence 是否被錯當成 corroboration

### Part 3：Over-Correction Signals and Advisory Containment

測的是：

- advisory signal 是否被錯當成 gate
- advisory containment rule 是否被正確遵守
- executable signal 與 advisory signal 的位階是否被混淆

### Part 4：Falsifiability

測的是：

- falsification condition 是否夠強
- falsification 之後的 explanation 是否仍然可被反駁
- reviewer 是否會用敘事掩蓋 falsification

### Part 5：Decision Quality Invariants

測的是：

- consistency / robustness / positive falsifiability 是否被正確理解
- clean windows 是否被錯當成 decision correctness 證據

### Part 6：Governance Mechanism Tiers

測的是：

- reviewer 是否能分清 enforceable / diagnostic / deferred
- calibration governance gap 是否被誤當成可自由插值的空白區

### Part 7：Anti-Ritualization

測的是：

- counterfactual scaffold 是否只是形式上填滿
- reviewer 能否識別 ritualized reasoning

## 分數解讀

| Score | Interpretation |
|---|---|
| 15–16 | 機制理解與套用大致符合 framework 預期 |
| 12–14 | 有小型 calibration gap，應回看錯題與團隊解讀 |
| 8–11 | 機制套用已有結構性偏差，需重讀 source docs |
| <8 | adoption 尚未完整，應先回到 onboarding / baseline 階段 |

## 維護要求

若新增或移除 scenario，以下三件事必須一起更新：

- scenario count
- score bands
- manifest 中列出的 document sources

## 一句話結論

這份 test pack 的價值，不在於給出一個漂亮分數，而在於驗證：團隊對 learning / stability / falsifiability 這條治理主線，是否真的理解並能一致套用。
