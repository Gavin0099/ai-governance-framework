# DBL First-Slice Reviewer Reconstruction Kit

> 狀態：review 輔助包
> 建立日期：2026-03-31
> 依賴：`docs/dbl-first-slice-validation-plan.md`

---

## 為什麼需要這份 kit

Step 2 不是功能測試，而是 current first-slice DBL surface 的 reconstruction test。

目標是確認獨立 reviewer 能否正確推論：

- 現在這個 slice 實際能判什麼
- 它明確不能判什麼
- insufficiency-like example 應被讀成 limitation proof，而不是 capability claim

這份 kit 應該在沒有作者口頭補充的情況下使用。

---

## 要給 reviewer 的輸入

第一輪只給 reviewer 這些材料：

- `examples/README.md`
- `examples/decision-boundary/minimal-preconditions/README.md`
- `examples/decision-boundary/insufficiency-like-preconditions/README.md`

若要直接交給 reviewer，可使用：

- `docs/dbl-first-slice-reviewer-test-pack.md`

第一輪不要加任何口頭說明。

---

## Reviewer 任務

請 reviewer 以書面回答這四題：

1. 目前 first-slice DBL gate 看起來能判斷什麼？
2. 目前 first-slice DBL gate 看起來不能判斷什麼？
3. 在什麼情況下，當前 gate 仍可能 pass，但 evidence 在語意上其實偏弱或不完整？
4. insufficiency-like example 是 capability proof，還是 limitation proof？請說明理由。

---

## 預期的正確重建

只有當 reviewer 清楚抓到大部分以下要點時，才算重建正確：

- explicit signal presence 不等於 semantic sufficiency
- current first slice 只到 precondition level
- insufficiency-like example 是刻意不主張能力的例子
- 那個 example 的 pass 不代表 adequacy judgment
- semantic insufficiency gap 是設計上刻意保留的開口

---

## 失敗訊號

若 reviewer 出現以下情況，應視為重建失敗：

- 認為 current slice 已能做 semantic sufficiency judgment
- 把綠燈測試結果當成 evidence-quality proof
- 把 insufficiency-like example 當成新的 capability demo
- 無法清楚分辨 presence 與 sufficiency

---

## 輸出格式

請把結果記成以下其中一個：

- `reconstructed correctly`
- `reconstructed partially`
- `reconstructed incorrectly`

並額外記下：

- 哪句話、哪個檔案、或哪個 example 造成誤讀
- 這個問題看起來是 framing-only，還是 runtime-related

---

## 工作規則

這一步不是在問 reviewer 夠不夠強。

真正要問的是：

> 目前的 example 與 framing，是否夠強到能防止 reviewer 自己過度腦補系統能力。
