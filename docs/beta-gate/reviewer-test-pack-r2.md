# Reviewer Test Pack — Beta Gate Condition 2（R2）

> 版本：2.0
> 建立日期：2026-03-30
> 適用對象：external reviewer（cold start, no author guidance）

---

## Part 1 — 你在測什麼

你要測的是一個用於 AI-assisted development 的 open-source governance framework。

**你的工作不是先把它學會；你的工作是試著使用它，並記錄實際發生了什麼。**

起點：<https://github.com/Gavin0099/ai-governance-framework>

請先用瀏覽器打開這個 URL。除非命令明確要求，否則不要先 clone repo。

時間預算：約 30–60 分鐘。

---

## Part 2 — Ground rules

- 不要向作者提問
- 不要靠作者補口頭背景
- 不要用 context 猜測缺失步驟
- 只根據 repo 內可見文件與可執行路徑操作

如果某一步走不下去，請記錄：

- 你在哪一步卡住
- 你看到的精確 failure
- 你是如何判斷沒有下一步的

---

## Part 3 — 你需要交付什麼

你要留下的不是隨意筆記，而是一份 reviewer run artifact。至少要包含：

- 你從哪個入口開始
- 你讀了哪些文件
- 你實際嘗試了哪些命令
- 第一個真正的 blocker 是什麼
- 你最後的 gate verdict 是什麼

如有需要，可搭配：

- `docs/beta-gate/reviewer-run-sheet.md`
- `docs/beta-gate/reviewer-signal-split.md`
- `docs/beta-gate/onboarding-pass-criteria.md`

---

## Part 4 — 評分重點

這個 test pack 關注的不是「你有沒有很努力」，而是：

- cold-start reviewer 能不能自己找到正確入口
- onboarding wording 是否足夠清楚
- minimum session flow 是否可依文件重建
- execution path 是否真的可走
- failure 能否被正確歸因，而不是只剩 pass/fail

---

## 一句話結論

R2 test pack 的目的，是讓 external reviewer 在沒有作者幫助的情況下，真實暴露這個 framework 的 onboarding / execution / communication 問題，而不是替它補敘述後再給分。
