# Beta Gate Condition 2 — Reviewer Test Brief

> 狀態：ready for use
> 建立：2026-03-30
> Gate condition：human self-serve onboarding without author guidance

---

## Purpose

這份 brief 定義的是測試條件，不是 framework 教學文件。

不要在 reviewer 開始前把這份文件給 reviewer。
它主要用來：

- 設定測試條件
- 在跑完後做 debrief

---

## Reviewer 起始條件

reviewer 只會拿到：

- GitHub repo URL：`https://github.com/Gavin0099/ai-governance-framework`
- 一句話：
  - `This is a governance framework for AI-assisted development. See if you can figure out how to use it.`

除此之外，不給：

- 口頭補充背景
- 起始 file pointer
- 作者導覽

---

## Reviewer 可以做什麼

- 讀 repo 裡任何檔案
- 跑任何他自己找到的工具
- 花他需要的時間（目標觀察範圍：約 30–60 分鐘）
- 提早停止，並說明卡在哪裡

---

## 作者不能做什麼

在 session 結束前，作者不能：

- 回答問題
- 指路到某個 file 或 section
- 解釋某個東西是做什麼的
- 告訴 reviewer 他現在是不是在正確方向上

作者唯一能說的話應該像：

> 繼續走，並記錄你現在的想法。

---

## Success condition

若 reviewer 能在沒有提示的情況下做到以下內容，可視為通過：

1. 找到 adopt framework 的主要入口
2. 跑或描述最小 adoption flow（哪些命令、順序大概是什麼）
3. 用自己的話說清楚 `session_start -> pre_task -> post_task` 在做什麼
4. 知道 governance drift 發生時要怎麼處理
5. 產出至少一個 governance-compliant artifact（例如：session start、drift-check output、contract、change proposal）

這 5 項不必全過；依 gate 規則，3/5 可以算 pass。

---

## 要觀察的 failure indicator

若出現以下情況，要記錄：

- reviewer 打開 `README.md` 後立刻關掉
- 10 分鐘後還找不到 entry point
- reviewer 把 framework governance 和 project governance 混為一談
- reviewer 得出「這只是文件」的結論
- reviewer 分不清 `governance_tools/` 和 `runtime_hooks/`
- reviewer 問「我要從哪裡開始？」

---

## Debrief questions（session 結束後問）

1. 你第一個打開的檔案是什麼？為什麼？
2. 從哪裡開始，你覺得這東西是做什麼的開始變清楚？
3. 第一個讓你困惑的點是什麼？
4. 如果你要用一句話跟同事描述這個 framework，你會怎麼說？
5. 你會改 entry path 的哪一點？

---

## 需要記錄的東西

- 到第一個 meaningful action 所花的時間
  - 不是 README skim，而是有方向的探索
- 第一個讓 reviewer 產生理解的檔案
- 第一個 blocker：哪個 file、哪個 section、哪裡不清楚
- reviewer 是否在無提示下走到 minimum adoption flow
- debrief 回答，盡量原文保留

---

## 測試之後

將發現記錄在：

- `docs/beta-gate/reviewer-run-<date>.md`

接著回答一件事：

- 這次 blocker 比較像 conceptual、structural，還是 naming？

這個答案才決定下一個 onboarding change 應該修哪裡。
