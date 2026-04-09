# Expansion Admission Gate

> 狀態：active
> 建立日期：2026-03-30
> 適用範圍：所有擬加入 governance runtime 的新 surface

---

## 目的

治理框架最常見的失敗方式，不是實作很差，而是：

> 加進了許多聽起來合理、實際上卻不必要的新 runtime surface。

因此，任何新的：

- import
- hook
- signal source
- dict key
- decision input

都必須先通過這道 gate，才能進 codebase。

這不是官僚檢查點，而是一個強迫你回答關鍵問題的機制：

> 這個東西真的有存在必要嗎？

---

## 什麼情況會觸發這道 gate

以下任一成立時，就要進 `Expansion Admission Gate`：

- 新增 runtime-consumed signal
- 新增 governance artifact 欄位
- 新增 influence verdict 的 decision input
- 新增需要被 reviewer 理解的新 surface
- 新增跨 hook / tool / artifact 的耦合欄位

如果只是：

- wording cleanup
- typo fix
- 不影響 runtime / reviewer semantics 的純文件整理

則不需要進這道 gate。

---

## 核心問題

每個 proposed addition 至少要回答：

1. 它要防的是哪個 failure mode？
2. 這個 failure mode 現在真的存在嗎？
3. 為什麼不能用既有 surface 處理？
4. 它會不會引入新的 authority、duplication 或 interpretive burden？
5. 它進來後，誰要消費它？

若答不清楚，就不應擴。

---

## 最小接受條件

新 surface 只有在以下條件都成立時才應被接受：

- 有明確 failure mode 對應
- 有明確 consumer
- 不重複既有 truth source
- 不偷渡新 authority
- 複雜度小於它防止的 failure mode

若只是：

- 「以後可能有用」
- 「看起來很合理」
- 「先放著也無妨」

都不算接受理由。

---

## 常見拒絕理由

以下情況應預設拒絕：

- 只是把同一個 signal 用另一種名字再包一層
- 只是把 human-readable note 結構化，但沒有 consumer
- 想先擴 surface，再回頭找失敗模式
- 會讓 reviewer / runtime / docs 各自長出不同語意
- 只因為「還能做」而不是「非做不可」

---

## 和 entry-layer 的關係

`Expansion Admission Gate` 的工作是判斷：

> 這個 runtime surface 是否應該存在。

`entry-layer` 的工作是判斷：

> 一旦它存在，它應該以什麼 bounded shape 進來。

也就是：

- expansion admission 解決「要不要有」
- entry-layer 解決「進來後長什麼樣」

---

## 和 advisory / closeout 線的關係

這道 gate 之所以重要，是因為 advisory、closeout、runtime injection 這幾條線都很容易發生相同問題：

- 一開始只有觀測需求
- 後來慢慢長成 authority
- 最後 consumer 與 producer 各自演化成不同語意

用這道 gate 的目的，就是在進 codebase 前先擋下「因為能擴所以擴」的慣性。

---

## Non-goals

這道 gate 不負責：

- 決定 feature 的最終 UX 細節
- 取代正式設計文件
- 取代 code review
- 為已被接受的 surface 補寫 justification

它的工作只有一個：

> 在 runtime surface 進場前，先確認它值得存在。

---

## 一句話結論

如果一個 proposed addition 無法明確說明它防的是什麼 failure、為什麼既有 surface 不夠、以及誰會真的消費它，那它就不該進 governance runtime。
