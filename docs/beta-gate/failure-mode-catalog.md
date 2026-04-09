# Beta Gate Failure Mode Catalog

> 狀態：active
> 建立日期：2026-03-30
> 目的：作為 onboarding failure 的 canonical 記錄，用來判斷新的 reviewer run 是重現既有 failure，還是暴露新的 failure。

---

## 這份 catalog 怎麼用

當 reviewer run 出現 failure 時，先檢查這裡：

1. 這次 failure 是否符合既有條目？若符合，記成 reproduction，並說明差異。
2. 若不符合，新增一條，不要硬塞進舊分類。

不要為了讓 catalog 看起來整齊，就把不同 failure 合併成同一條。  
錯誤合併會吃掉真正的訊號。

---

## FM-001：No-Python Execution Block

**首次觀察：** R2 reviewer run，2026-03-30

### 描述

reviewer 無法產生 governance artifact，原因不是 reviewer 停止操作，而是：

- `python`、`python3`、`py` 都不可用
- 文件中當時也沒有 recovery path

### 這類 failure 的辨識要點

- 問題發生在 execution 開始前後
- onboarding 理解本身可能成立
- 但 adoption / drift / runtime tool 無法真正執行

### 分類意義

這類 failure 不應被誤記成：

- reviewer 不夠熟悉流程
- reviewer 沒依指示操作
- governance artifact 遺失

它是 execution precondition 不成立。

---

## Catalog 使用規則

每次新增或重現 failure mode 時，至少要記：

- 首次觀察時間
- 觸發條件
- failure 的真正層級
- 容易被誤分類成什麼

這樣 catalog 才不會變成一堆模糊標題，而能真的幫 reviewer run 分流。

---

## 一句話結論

`Beta Gate Failure Mode Catalog` 的工作不是蒐集所有壞事，而是把 reviewer onboarding / execution / governance failure 分類清楚，避免後續把不同 failure 誤當成同一個問題。
