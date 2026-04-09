# DBL First-Slice Reviewer Test Pack

> 版本：1.0  
> 建立日期：2026-03-31  
> 對象：外部 reviewer（第一輪不接受作者口頭補充）  
> 範圍：只測 Step 2 reconstruction

---

## Part 1：你在測什麼

這份測試**不是**要你驗完整 framework onboarding。

你要測的是：目前 `Decision Boundary Layer (DBL)` 的第一個可執行 slice，  
是否能只靠範例與 framing materials 被正確重建。

你在閱讀時的任務不是順手幫 framework 改進。

你的任務是：

- 閱讀指定材料
- 回答下面四個問題
- 記錄哪些地方讓你過度推論、低估、或產生猶豫

---

## Part 2：第一輪要讀的材料

第一輪只讀這三份：

1. `examples/README.md`
2. `examples/decision-boundary/minimal-preconditions/README.md`
3. `examples/decision-boundary/insufficiency-like-preconditions/README.md`

第一輪閱讀期間，不要向作者詢問補充說明。

---

## Part 3：Reviewer 任務單

請用自己的話回答以下四題：

1. 目前這個 first-slice DBL gate 看起來**能判什麼**？
2. 目前這個 first-slice DBL gate 看起來**不能判什麼**？
3. 在什麼情況下，雖然證據在語義上偏弱或不完整，這個 gate 仍可能會通過？
4. `insufficiency-like` 那個例子是 capability proof 還是 limitation proof？為什麼？

---

## Part 4：誤讀記錄

閱讀過程中請隨手填，短句即可。

### 4.1 第一個 over-inference 點

```text
我當時在讀哪個檔案或句子：

我以為 framework 在主張什麼：

哪個措辭讓我產生這個想法：
```

---

### 4.2 第一個 hesitation 點

```text
我在哪裡停住或不確定：

我不確定的是什麼：

我原本期待檔案補充什麼，但它沒有：
```

---

### 4.3 最終分類

```text
這些例子是否讓我分清 explicit presence 和 semantic sufficiency？
Y / N / Partial

我是否把 insufficiency-like 例子理解成 limitation proof？
Y / N / Partial

任何 green test / passing result 是否讓我以為 framework 已能判 adequacy？
Y / N

如果有，這個 impression 來自哪裡？
```

---

## Part 5：提交格式

請把你的筆記存成：

`docs/dbl-first-slice-reviewer-run-<YYYY-MM-DD>-<initials>.md`

如果要用模板，可從 `docs/dbl-first-slice-reviewer-findings-template.md` 開始。

---

## Part 6：怎樣算成功重建

只有在 reviewer 明確得出以下結論時，才算重建成功：

- 目前這個 slice 主要面向 `explicit-precondition / missingness`
- `semantic sufficiency` 仍然不在目前範圍內
- `insufficiency-like` 範例展示的是限制，不是新能力

如果 reviewer 把 `insufficiency-like` 例子理解成「runtime 已能判 adequacy」的證據，  
這次 reconstruction 應視為失敗。
