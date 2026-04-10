# DBL First Slice Validation Plan

> 更新日期：2026-03-31
> 相關文件：`docs/decision-boundary-first-slice.md`

---

## 目的

這份文件定義如何驗證 `Decision Boundary Layer` 的 first slice 是否成立。

驗證重點不是 feature expansion，而是確認第一刀已經足以證明：

- slice 能進 runtime verdict
- slice 能留下 reviewer 可用 artifact
- reviewer 不會把 limitation 誤讀成 capability proof
- obvious false-pass / false-compliance pattern 能被看見

---

## 驗證原則

first slice 不需要一次驗證整個 DBL。

它只需要證明：

1. 缺失狀態可被顯式表達
2. reviewer 能用 artifact 重建缺失原因
3. insufficiency-like case 不會被包裝成通過
4. adversarial / gaming case 不會輕易騙過 surface

---

## Step 0：Reviewer Signal

先確認 reviewer failure 是否能被記錄成正式 signal。

要看的不是 reviewer 有沒有不滿，而是：

- reviewer 是否能指出缺失點
- reviewer outcome 是否能穩定落到 failure layer

---

## Step 1：最小缺失案例

建立一個最基本的 missing-precondition example，例如：

- spec 不完整
- sample 缺失
- fixture 不足以支撐 failing condition

目標是確認 slice 能把 absence 顯式表達出來，而不是默默 pass。

---

## Step 2：Reviewer Reconstruction

把 Step 1 的 artifact 交給 reviewer，確認 reviewer 是否能只靠 artifact 重建：

- 缺的是什麼
- 為什麼這會改變 decision posture
- verdict 為何不是 capability proof

這一步對應：
- `docs/dbl-first-slice-reviewer-reconstruction-kit.md`

---

## Step 2.5：Adversarial / Gaming Case

加入一個 formal presence 但 semantic insufficiency 的案例，例如：

- 有 spec，但缺少 failure-path coverage
- 有 sample，但不足以支撐 correctness claim
- 有 fixture，但 assertion 不足

這一步是用來測：

- slice 是否只會看見 presence
- 還是能避免 pseudo-compliance

---

## Step 3：Independent Reviewer Onboarding

最後才進正式 reviewer onboarding gate。

這一步要確認 reviewer 是否能在不依賴作者口頭補充的情況下，完成對 first-slice DBL 的理解與判讀。

---

## 通過條件

first slice 至少應滿足：

1. reviewer 可從 artifact 重建 first-slice decision
2. insufficiency-like example 不被誤讀成 supported capability
3. adversarial case 能暴露 surface 的限制，而不是被當成 pass
4. reviewer failure 能被歸類到具體 layer，而不是只停在籠統 fail

---

## 一句話

這份 validation plan 的目標不是把 first slice 包裝成熟，而是證明它已經是一個真正的 decision surface，而不是只有 framing 的 demo。
