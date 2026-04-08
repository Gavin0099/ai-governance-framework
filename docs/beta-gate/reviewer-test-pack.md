# Reviewer Test Pack - Beta Gate Condition 2

> 版本：1.1
> 建立：2026-03-30
> 更新：2026-04-08
> 適用：author-side test operator
> 不要在 reviewer 開始前把這份文件給他

---

## Part 1 - 你在測什麼

這份文件定義的是作者端如何跑一次 cold-start reviewer run。

reviewer 在開始前**不會**拿到這份文件。

reviewer 的起始條件由 `reviewer-test-brief.md` 定義：

- GitHub repo URL
- 一句 framing
- 不提供 file pointer
- 不提供作者導讀

---

## Part 2 - reviewer 的任務目標

預期 reviewer 會依序嘗試：

1. 弄清楚這個 framework 是做什麼的
2. 弄清楚如果要導入 project，應該怎麼 adopt
3. 跑或至少描述 AI-assisted work session 的最小 flow
4. 找到治理漂移時要怎麼檢查

當 reviewer 完成，或卡住到無法繼續時，就停止。

---

## Part 3 - Failure Log

這一段用來保留 reviewer 的原始體感。不要事後把它修成太乾淨的總結。真實、凌亂的筆記通常比整理過頭的摘要更有價值。

### 3.1 第一個 confusion point

第一個出現「我看不懂」的時刻：

```text
當時正在看的 file 或 page:

我原本期待在這裡看到什麼:

我實際看到什麼:

到這個時候大概花了多久:
```

---

### 3.2 第一個 blockage

第一個真正卡住、無法往前推的地方：

```text
我當時在嘗試什麼:

我做了哪些嘗試:

為什麼沒有成功（依我當下理解）:

有沒有找到 workaround? (Y/N)
如果有，是什麼:
```

---

### 3.3 Concept confusion

任何 reviewer 遇到但不理解的名詞 / 概念：

```text
Term / concept:
在哪裡看到的:
我原本以為它是什麼:
如果後來有搞懂，我現在認為它是什麼:
```

每個 confusing concept 都複製一份 block。若沒有，可留白。

---

### 3.4 Navigation confusion

任何 reviewer 不知道下一步該去哪裡找的時刻：

```text
我當時在找:

我去看了哪些地方:

最後在哪裡找到（或：一直沒找到）:
```

每次 navigation failure 複製一份 block。若沒有，可留白。

---

### 3.5 Final state

```text
Did you complete Task 1 (understand what this is for)?   Y / N / Partial
Did you complete Task 2 (understand adoption)?           Y / N / Partial
Did you complete Task 3 (describe minimum session flow)? Y / N / Partial
Did you complete Task 4 (find drift check)?              Y / N / Partial

If you stopped early: what was the last thing you tried before stopping?

One sentence describing what this framework is, in your own words:
```

---

## Part 4 - Debrief questions

reviewer 結束後，再問：

1. 你第一個打開的檔案是什麼？為什麼？
2. 從哪個時點開始，你覺得事情有開始變清楚？
3. 最大的阻礙是什麼？
4. 如果要跟同事說值不值得 adopt，你會怎麼說？
5. 你覺得哪一個改動最能減少摩擦？

---

## Part 5 - Author interpretation

### 如何判讀 failure log

| 症狀 | Failure type | 不要這樣做 | 應該這樣做 |
|---------|-------------|-----------|------------|
| 10 分鐘後仍找不到入口 | Structural | 直接重寫 README | 先在 repo root 加一個更清楚的 pointer |
| 找到對的檔案，但誤解其用途 | Naming | 一直加解釋 | 修標題或第一句 |
| 概念懂了，但跑不起來 | Friction | 一直加文件 | 修命令或補一個例子 |
| 20 分鐘後還是完全搞不懂 | Conceptual | 全部重構 | 找出最關鍵、能打開其他理解的那個概念 |
| 把 framework repo 和 consuming repo 混在一起 | Conceptual | 只加 warning | 讓 distinction 變成 README 第一層就會看到的內容 |

### 計分

跑完後，用：

- `docs/beta-gate/onboarding-pass-criteria.md`

### 收到 log 後

原始 reviewer log 請存到：

- `docs/beta-gate/reviewer-run-<YYYY-MM-DD>.md`

在提修法前，先用：

- `docs/beta-gate/reviewer-signal-split.md`

分類第一個有意義的 failure。

在看完整份 log 之前，不要急著修。
也不要一次修超過每個 failure 的最低層原因。
