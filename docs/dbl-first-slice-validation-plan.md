# DBL First-Slice Validation Plan

> 狀態：驗證計畫
> 建立日期：2026-03-31
> 依賴：`docs/decision-boundary-first-slice.md`

---

## 為什麼需要這份計畫

`Decision Boundary Layer` 的第一個 executable slice 已經存在於：

- runtime
- docs
- minimal example

這足以證明：

- slice 能執行
- slice 能改變 verdict
- slice 能在小型外部 example 中被展示

但這還不足以證明：

- 外部 reviewer 能否只靠 artifact 重建它
- 它能不能抵抗誤讀、誤用或被 gaming
- reviewer onboarding fail 是 onboarding 問題，還是 DBL 本身的問題

所以在擴更多 DBL surface 前，先做這份驗證。

---

## 驗證原則

下一步不是 feature expansion，而是驗證目前 first slice 是否：

1. 能被他人重建
2. 能和單純文件指引區分開來
3. 能暴露 obvious false-pass / false-compliance pattern

簡單說：

> 不只問這個 slice 能不能用，
> 還要問它會不會被誤用、誤讀，或被錯誤放行。

---

## Step 0：先拆 reviewer signal

在把 reviewer 結果當成 gate 之前，要先拆清楚 reviewer failure 到底在測什麼。

目前 reviewer outcome 可能混在一起的有：

- onboarding UX
- 文件理解
- decision reconstruction
- escalation judgment

單純一個 fail 不夠用。

review exercise 應至少把 failure 分成：

- discoverability failure
- interpretation failure
- decision reconstruction failure
- escalation failure

不先拆開，reviewer onboarding 對 DBL 的訊號就太粗。

---

## Step 1：加一個很小的第二個 example

第二個 example 不應重複第一個 absence case。

它應該刻意碰一個 insufficiency-like case，例如：

- spec 存在，但和真正 task 無關
- sample 存在，但只覆蓋 happy path
- fixture 存在，但沒碰到 failing condition

目的：

- 測目前 first slice 的邊界
- 暴露它目前還分不清哪些 insufficiency
- 防止團隊把「absence case 能跑」誤解成「已能處理 sufficiency」

這仍然是很小的 example，不是新的 demo project。

---

## Step 2：對兩個 example 跑 reviewer reconstruction

使用：

- 現有 minimal example
- 新的 insufficiency-like example

並搭配 [`docs/dbl-first-slice-reviewer-reconstruction-kit.md`](dbl-first-slice-reviewer-reconstruction-kit.md)。

這一步還不是正式獨立 reviewer gate，而是先觀察：

- reviewer 哪些地方能乾淨重建
- 哪些地方 reviewer 開始自己補 intuition
- 哪些地方 reviewer 以為系統檢查得比實際還多

目的：

- 驗 DBL reconstruction quality
- 找出 human interpretation 超過 runtime truth 的第一批位置

---

## Step 2.5：加入 adversarial / gaming case

在宣告 first slice 穩定之前，要加一個刻意「形式成立，但語意不足」的 case。

例如：

- spec 存在，但其實不相關
- sample 存在，但沒有 failure-path coverage
- fixture 存在，但 assertion 沒有意義

目的：

- 看當前 gate 是否容易被 trivially gamed
- 區分「minimal」和「容易被繞過」

如果當前 gate 放過這種 case，未必代表 slice 1 設計失敗；  
但它至少證明：

- 目前仍是 explicit-missing-state only
- 後續驗證應處理 insufficiency，不只是 absence

---

## Step 3：回到正式 independent reviewer onboarding

只有在 Step 0、1、2、2.5 做完之後，才適合把 formal reviewer onboarding gate 當成下一個 maturity check。

這樣 failure 才能被診斷：

- discoverability fail -> onboarding 問題
- interpretation fail -> docs / interface 問題
- reconstruction fail -> DBL 問題
- escalation fail -> decision model / authority 問題

這樣 reviewer gate 才有價值，而不是 noisy fail。

---

## 成功標準

第一個 slice 要算「有意義地被驗證」，至少要成立：

1. 外部 reviewer 能只靠 artifact 重建 first-slice decision。
2. reviewer 不需要默默用自己的 intuition 替系統補能力。
3. insufficiency-like example 清楚暴露目前限制，而不是被誤寫成 supported capability。
4. adversarial case 能看出這個 slice 是否容易被 gaming。
5. reviewer failure 能被歸因到特定 layer，而不是一個模糊 onboarding fail。

---

## Non-goals

這份驗證計畫不授權：

- 立刻擴到 identity enforcement
- 立刻擴 capability runtime integration
- 立刻做 full semantic sufficiency inference
- 立刻做完整 precedence engine

那些可以以後再來，但前提是目前 first slice 已被證明是「真的 decision surface」，不是狹窄 demo。

---

## 工作結論

現在真正該問的不是：

> first slice 能不能用？

更重要的是：

> first slice 能不能避免被誤用、誤讀，或被錯誤放行？

這才是目前的下一個驗證邊界。
