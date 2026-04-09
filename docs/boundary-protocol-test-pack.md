# Boundary Protocol 測試包

> Covers commits: `f0a9935` -> `e6f73d3`
> Scenario count: 16（Parts A-F）
> Scenario IDs: `A.1`, `A.2`, `B.1`, `B.2`, `B.3`, `C.1`, `C.2`, `C.3`, `D.1`, `D.2`, `E.1`, `E.2`, `F.1`, `F.2`, `F.3`, `F.4`
> Passing score:
> - `14-16`：strong pass
> - `11-13`：marginal pass，重看 Part C、D、F
> - `<11`：fail
> Documents under test:
> - `docs/boundary-crossing-protocol.md`

Prerequisite：建議先熟悉 `docs/learning-governance-test-pack.md`。  
這份 pack 是 **conformance test**，不是 adversarial pack。邊界辨識的 adversarial 測試在 `docs/adversarial-test-scenarios.md` Part D。

---

## 如何使用

每個 scenario 都給你一個輸入情境，要求你做 judgment call。  
看完 scenario 先自己寫答案，再打開 `Verdict` 比對。

若你的答案和 verdict 不同，不要立刻假設自己錯。也可能是 verdict 本身有問題。  
真正的分歧應記錄下來。

---

## 說明

這份 pack 的目的，是檢查 reviewer 或 operator 是否能在 boundary condition 出現時，做出與 protocol 一致的處理，而不是只會背誦名詞。

> Scenario count: 16（Parts A-F）
