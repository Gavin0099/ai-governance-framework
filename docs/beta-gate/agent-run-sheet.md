# Agent Run Sheet

> 狀態：active
> 建立日期：2026-03-31
> 適用範圍：agent-assisted adoption runs

---

## 目的

這份文件定義 agent-assisted adoption run 的最小記錄結構。

目標不是寫一篇成功故事，而是留下：

- 可 replay
- 可 challenge
- 可 compare

的 run record。

它存在的目的，是讓 agent-assisted adoption 被評估成一種可審計的執行模型，而不是一次性的 demo。

---

## 最小應記錄的內容

每次 agent-assisted adoption run，至少應記錄：

- agent identity
- repo commit / framework commit
- 起始輸入與 framing
- 採用的 documented path
- 主要命令 / 檢查步驟
- 產生的關鍵 artifact
- 最終判定與理由

---

## 使用原則

這份 run sheet 不要求把所有細節都寫成長篇敘事。  
它要求的是：

- 留下足夠重播線索
- 讓 reviewer 能 challenge 關鍵判斷
- 讓不同 agent run 可以被比較

如果少了這些欄位，agent-assisted adoption 很容易退化成「一次成功 demo」，而不是可審核流程。

---

## 一句話結論

`Agent Run Sheet` 的作用，是把 agent-assisted adoption 從一次性的操作紀錄，收斂成可 replay、可 challenge、可 compare 的最小審計結構。
