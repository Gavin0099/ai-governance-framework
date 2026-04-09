# Learning Stability

> Version: 1.0
> Related: `docs/learning-loop.md`, `docs/falsifiability-layer.md`, `docs/decision-quality-invariants.md`

---

## 目的

一個對每個 signal 都立刻改動的系統，不是 learning，而是 oscillation。

這份文件定義：
- 什麼情況下系統不該改
- 如何辨認 change 正在累積 drift，而不是 improvement
- 當 learning system 自己開始 over-correct 時應如何處理

目標不是阻止 learning，而是避免：

> 因為解釋很多、變更很多，就把 activity 誤當成 progress

---

## 什麼情況下不該改

以下任一條件成立，都足以支持 `no_change_justified`：

1. **failure 是孤立且不重複的**  
   單一 falsification event，且同 category 沒有 prior pattern，通常不足以證明有 structural problem。

2. **failure 根因在 execution，不在 model**  
   若是 implementation、環境、流程錯誤，而不是模型假設錯誤，應修 execution，不一定要改模型。

3. ** proposed change 只是移動不確定性，沒有降低它**  
   如果回答不了「這次 change 是否真的降低不確定性」，就不該輕易改。

4. **兩個 observation window 都沒 recurrence**  
   代表原始 falsification condition 可能只是 transient。

5. **改動會破壞目前其實運作良好的機制**  
   若修一個 failure 會明顯提高其他 failure 類型的風險，就不算 net-positive change。

---

## 如何偵測 Over-Correction

### Signal 1（advisory）

change rate 上升，但 misinterpretation log rate 沒下降。  
這代表系統可能在忙著改，卻沒有打到真正 failure source。

### Signal 2（executable）

同一 failure 在同一層已經 `doc_updated` 兩次，仍持續 recurrence。  
這時下一次不應再直接做第三次 `doc_updated`，而應升到 `model_adjusted` review。

### Signal 3（executable）

skepticism zone 一直累積，卻沒有 retire。  
這表示系統正逐步變得更保守，但沒有證據顯示這些限制真的改善結果。

### Signal 4（advisory）

最近一次 change 在功能上實際抵消了之前的 change。  
即使不是明寫 rollback，只要讓前一個決策路徑失效，也算 functional undo。

### Signal 5（advisory）

proposal rejection rate 上升，但高成本 failure 沒下降。  
這通常表示 gate 變嚴了，但沒有更有效。

---

## Advisory 與 Executable 邊界

advisory signal 只能提醒 reviewer，不得單獨改 decision path。

**只靠 advisory signal，不允許直接做：**
- 提高 evidence bar
- 暫停 proposal evaluation
- 直接提高某 category 的 skepticism

advisory 只有在以下情況之一成立時，才可能進一步影響決策：
- 同一 window 內有至少一個 executable signal 同時成立
- 同一 advisory signal 連續三個 window 都出現，轉成需要 stability review 的 executable signal

---

## Stability Check

每個 observation window 結束時，除了 learning loop 檢查外，再補這幾題：

- [ ] change rate 是否上升，但 misinterpretation frequency 沒有下降？
- [ ] 是否有 failure 在兩次 `doc_updated` 後仍 recurrence？
- [ ] 是否有 skepticism zone 已超過退休檢查期限？
- [ ] 最近 change 是否功能上抵消了前一個 change？
- [ ] proposal rejection rate 是否持續上升？

如果其中兩項以上同時成立，下一個 proposal 接受前應先做 stability review。

---

## Stability Review 的輸出

stability review 至少要落在以下三種之一：

| Outcome | Meaning |
|---------|---------|
| `converging` | 變更方向正在降低 misinterpretation frequency |
| `oscillating` | 變更彼此抵消，或沒有讓 failure 下降 |
| `stable_noise` | 系統正在對 noise 做反應，而不是對 genuine signal 做反應 |

stability review 也必須服從 observation / conclusion separation：  
判斷必須基於 log data，而不是 reviewer 的主觀印象。

---

## Stability 與 Learning 的關係

stability 不是 learning 的反面。  
真正健康的 learning，是：

> change 次數可以少，但每次 change 更可能是對的

不健康的系統則是：

> 對每個 signal 都有反應，卻沒有收斂

把 responsiveness 當 intelligence、把 correction volume 當 learning quality、把 gate strength 當 governance quality，本質上都是同一種誤判。

---

## Calibration Over Time

本系統現在的 thresholds 都只是起始校準，不是永久真理。

若未來發現：
- false positives 太多：提高 threshold
- genuine structural problem 一直漏掉：降低 threshold

threshold calibration 本身也要接受 falsifiability 標準：
- 若現行 threshold 錯了，我們預期會觀察到什麼？
- 觀察到之後，會怎麼改？

---

## Silent Degradation Signals

有些 degradation 不會表現在「更多 change」或「更多 rejection」，而是表面健康、實際品質下降。

這類 signal 包括：

### A. 決策多樣性下降

所有 proposal 都集中在同一類，可能代表系統局部過度最佳化，或 reviewer 已陷入 tunnel vision。

### B. Proposal 越來越短、越來越空

如果 falsifiability condition、alternative mechanism、blind spot 越寫越短，但 acceptance rate 沒變，通常表示 gate 已在退化。

### C. Log 有在記，但 reviewer 不再提問

如果 log 仍持續新增，但已很少產生 follow-up question、disagreement 或 re-evaluation，可能不是 misinterpretation 變少，而是 reviewer 不再 critical。

### D. 沒人說得出當前模型最可能錯在哪

如果沒有人能說出當前模型最可能錯的兩三個地方，多半不是模型超成熟，而是命名弱點的習慣消失了。

### E. 「看起來有在運作」變成預設答案

如果所有 adequacy 問題最後都只回：

> it seems to be working

而不是引用具體 evidence 或未驗證 assumptions，表示系統已從 evidence-based 慢慢滑向 inertia-based。
