# Learning Stability

> Version: 1.0
> Related: `docs/learning-loop.md`, `docs/falsifiability-layer.md`, `docs/decision-quality-invariants.md`

---

## 目的

`Learning Stability` 用來回答一個比「有沒有學習」更難的問題：

> 系統的學習是否真的在收斂，還是只是在過度修正、來回擺盪，或把 activity 誤當成 progress？

這一層不是要降低 responsiveness，而是要避免 learning system 因為每個 signal 都立即反應，最後變成不穩定的 oscillation machine。

---

## 什麼情況下不應急著改

不是每次 falsification event 都應立刻調整。

在做 `no_change_justified` 之前，至少應檢查：

1. **failure 是否屬於既有 pattern**
   - 這是 repeated structural problem，還是單次 incident？
2. **failure 出在 execution 還是 model**
   - 可能是 implementation 問題，不是 governance model 問題
3. **proposed change 是否只是把 noise 當 signal**
   - 不能因為壓力存在就假設一定需要大改
4. **observation window 是否足夠**
   - 太短的 window 很容易把 transient 問題誤當成 recurrent pattern
5. **變更是否真的帶來 net-positive**
   - 有些修正會增加 complexity，但沒有降低真實 misinterpretation

---

## Over-Correction Signals

### Signal 1：change rate 上升，但 misinterpretation 沒下降

如果 change rate 持續變高，但 misinterpretation log 沒有改善，代表系統可能在忙於修正表象，而不是處理 failure source。

### Signal 2：同類 failure 反覆落到 `doc_updated`

如果 recurring failure 每次都只靠 `doc_updated` 回應，而沒有任何 deeper review，通常代表 learning response 太淺。

### Signal 3：skepticism zone 長期無法 retire

如果一個 skepticism zone 進去後長期無法退出，可能表示：

- zone 定義太寬
- falsification 條件太弱
- 或系統不敢承認自己沒有真正收斂

### Signal 4：回滾頻率過高

如果 system 持續做 change -> partial undo -> 再 change，代表學習在 oscillation，而不是 convergence。

### Signal 5：proposal rejection rate 持續升高

如果拒絕率不斷上升，卻沒有對應 evidence 顯示品質提升，可能表示 gate 變嚴，但 decision quality 沒有同步變好。

---

## Advisory 與 Executable 的分工

`Learning Stability` 不要求所有 signal 都立刻進 executable path。

- **advisory signal**：提醒 reviewer 或 operator 注意可能的過度修正
- **executable signal**：在 observation window 足夠、條件夠清楚時，才進入較正式的 stability review

因此：

- advisory 可以先拉高警覺
- executable 應保留給較強的、可重複觀測的穩定度 signal

---

## Stability Check

每個 observation window 結束時，可用下列問題做最小檢查：

- [ ] change rate 是否上升，但 misinterpretation frequency 沒下降？
- [ ] 同類 failure 是否一再只落到 `doc_updated`？
- [ ] skepticism zone 是否遲遲無法 retire？
- [ ] 是否頻繁出現 change 後又快速部分撤回？
- [ ] proposal rejection rate 是否升高，但缺少改善證據？

如果多項同時成立，表示 system 不只是 noisy，而是可能進入 learning instability。

---

## Stability Review Outcome

| Outcome | Meaning |
|---------|---------|
| `converging` | learning response 正在降低真實 misinterpretation frequency |
| `oscillating` | system 持續修正，但 recurring failure 未真正下降 |
| `stable_noise` | 目前看到的是 noise，不足以推論為 genuine structural signal |

`Stability Review` 應保持 observation / conclusion separation，不能把活動量直接當成品質證據。

---

## 與 Learning Loop 的關係

`Learning Loop` 問的是：failure 是否被轉成 documented outcome。
`Learning Stability` 問的是：這些 outcome 長期看是否真的在收斂。

也就是：

> change 不是 learning；能持續降低 recurring failure 的 change，才比較接近有效 learning。

---

## Calibration Over Time

長期來看，某些 thresholds 與 signals 需要校準，例如：

- false positives 過多時，要調整 threshold
- genuine structural problem 被壓低時，也要重新拉高靈敏度

但 calibration 本身也要受 falsifiability 約束，不能只因為近期壓力就任意移動門檻。

---

## 不是什麼

`Learning Stability` 不是：

- 要求 system 永遠不要改
- 把 change volume 當成 learning quality
- 把 gate strength 當成 governance quality

它真正關心的是：

> system 是否能在維持可修正能力的同時，避免陷入過度修正、反覆回擺或長期不收斂。
