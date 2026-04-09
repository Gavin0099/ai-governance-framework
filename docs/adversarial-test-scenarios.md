# Adversarial Test Scenarios

> 版本：1.0  
> 相關文件：`docs/learning-governance-test-pack.md`、`docs/decision-quality-invariants.md`、`docs/governance-mechanism-tiers.md`

---

## 目的

conformance test pack（`learning-governance-test-pack.md`）測的是：
機制在條件清楚時，是否能被正確套用。

它不測的是：
當條件變成對抗性、誤導性、或觀測不完整時，機制是否仍站得住。

這份文件專門測三種 conformance pack 打不到的失敗條件：

1. **misleading evidence**  
   證據看起來像支持某個結論，但其實不支持
2. **partial observability**  
   系統掌握的資訊不完整，必須決定要承認邊界還是硬往下判
3. **conflicting signals**  
   兩個機制同時給出互相衝突的導引

如果一個系統能通過 conformance pack，卻在這裡失敗，表示它得到的是**內部一致性**，而不是**外部穩健性**。這份 scenario pack 的目的，就是找出這個缺口。

## 與 conformance pack 的差異

conformance pack 的正解，原則上可以靠仔細讀 framework 文件推導出來。

這份 adversarial pack 故意設計成：

- 表面閱讀會把你引向某個直覺答案
- 真正的正解取決於你能不能發現表面沒說出的缺口
- 部分 scenario 沒有單一正解，只有正確的**處理程序**

如果某題沒有單一答案，verdict 會描述：

- 需要採取的 process
- 必須避免的 failure modes

## 使用方式

這份文件適合在 conformance pack 已穩定通過之後使用。  
目的不是替 framework 再加新規則，而是回答：

- 現有規則在壓力下是否仍然成立
- reviewer 是否知道機制的邊界
- 團隊會不會把 consistency 誤當成 correctness

## 主要測試面向

### A. Misleading Evidence

測的是：

- 重複出現的 pattern 是否被錯當成 root cause
- structural evidence 是否被錯當成 causation
- targeted fix 的非復發是否被錯當成分類確認

### B. Partial Observability

測的是：

- 觀測不完整時，團隊是否會誠實承認不足
- 單一來源、多筆紀錄是否被錯當成獨立 corroboration
- calibration / observation window 漂移時，是否能避免自利式解讀

### C. Conflicting Signals

測的是：

- executable signal 與 advisory signal 衝突時，是否能維持正確 precedence
- reviewer agreement 是否被錯當成 correctness
- framework 是否能誠實承認某些 failure 在目前 observation model 中根本不可見

### D. Refusal Correctness

測的是：

- 在 evidence 不足時，是否能停在 `cause_unknown`
- proposal 雖通過 gate，但 evidence 本身不可判時，是否能 `defer_with_condition`
- deferral 本身有成本時，是否能區分「不知道」與「不能不做決定」

## 評分方式

這份 pack **不採數字分數**。  
真正要看的是：團隊能不能對每個 scenario 說清楚：

- 自己套用的是哪個機制
- 這個機制到底能測到哪裡
- 它在哪裡應該停下來

如果一個團隊每題都答對，卻說不出機制邊界，那不算通過。

## 搭配 conformance pack 的建議

| 面向 | Conformance pack | Adversarial pack |
|---|---|---|
| 主要測什麼 | 內部一致性、正確套用 | 對抗條件下的穩健性 |
| 是否有單一正解 | 多半有 | 有些題只有正確 process |
| 通過代表什麼 | 規則能被正確執行 | 系統知道自己的邊界 |
| 失敗代表什麼 | 套用機制有缺口 | 過度自信或 boundary blindness |

建議順序：

1. 先跑 conformance pack
2. conformance 穩定後再跑 adversarial pack

原因很簡單：如果連基本機制都還沒穩定，先上 adversarial scenario 只會把理解混亂和真正的邊界問題混在一起。
