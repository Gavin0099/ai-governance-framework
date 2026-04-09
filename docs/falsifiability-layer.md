# Falsifiability Layer

> Version: 1.0
> Related: `docs/misinterpretation-log.md`, `docs/anti-ritualization-patterns.md`, `docs/decision-quality-invariants.md`

---

## 目的

一個無法被證明錯誤的治理決策，就無法被真正評估。

這份文件定義 expansion proposal 與治理決策的 falsifiability requirement。  
它是 proposal 被接受前最後一道檢查，不再問：

> reasoning sound 不 sound？

而是問：

> 如果 reasoning 錯了，我們要怎麼知道？

沒有這一層，治理只會累積，不會學習。

---

## 核心要求

每個被接受的 expansion proposal，都必須在 decision time 明確寫出：

### Falsification condition

也就是：  
若這個決策是錯的，未來會出現什麼具體、可觀測的結果？

這個條件必須符合：

- **Specific**：不是「問題還在」，而是「某類 log entry 仍以某頻率出現」
- **Observable**：能透過 log、artifact、reviewer behavior 檢查
- **Time-bounded**：何時應該能看到 failure signal
- **Decision-reversing**：若條件成立，應觸發 re-evaluation，而不是只是記下來

---

## 為什麼 Process Quality 不夠

一個 proposal 可以同時滿足：

- reasoning 看起來完整
- evidence 看起來足夠
- 結構上完全合規

但最後仍然是錯的。

process quality 與 decision correctness 並不是同一件事。  
只量 process quality，系統只會累積「看起來很合理的錯決策」。

falsifiability layer 的作用，就是把 process quality 接到 decision quality。

---

## Falsification Condition 範例

**弱、不可接受：**

> If the problem persists, we would know the dimension was insufficient.

問題是：
- `problem persists` 沒有定義
- 沒有 baseline
- 不可操作

**可接受：**

> If `activation_state` continues to appear in log entries as a decision input  
> at a rate of 2+ entries per observation window after the new dimension is introduced,  
> the dimension failed to address the root cause.

**可接受：**

> If the total log entry rate does not decrease in the observation window  
> following the change, the dimension added complexity without reducing  
> misinterpretation frequency.

---

## Falsification 不等於自動 reversal

觀察到 falsification condition，代表應重新檢查決策；  
它不是自動 rollback。

正確流程應是：

1. 在 misinterpretation log 記下 falsification event
2. 回看原 proposal 與其 reasoning
3. 判斷 failure 出在：
   - dimension design
   - implementation
   - falsification condition 自己太嚴
4. 明確決定：
   - reverse
   - adjust
   - maintain（附新 justification）
5. 明確記錄 outcome：
   - `doc_updated`
   - `model_adjusted`
   - `threshold_changed`
   - `no_change_with_justification`

**不允許 silent non-response。**

---

## Guard Against Explanation Drift

當 falsification condition 成立時，最常見反應是解釋它為什麼「不算」：
- edge case
- temporary issue
- unrelated factor

這種解釋不是不能用，但它本身也必須可以被 falsify。  
如果你說不出：

> 如果這個解釋也錯了，我們會觀察到什麼？

那它就不是 analysis，而只是 narrative。

---

## 與 Misinterpretation Log 的關係

falsification condition 應在 observation window close 時被檢查。  
misinterpretation-log 的 end-of-window checklist 應包含：

> 之前被接受的 proposal，其 falsification condition 現在是否已可觀測？

如果答案是 yes，就必須進 re-evaluation。  
這不代表原決策一定錯，只代表現在需要重新判斷。

---

## 沒有這一層會發生什麼

若缺少 falsifiability requirement，治理會只朝一個方向累積：擴張。

因為：
- 新增的東西很可見
- 錯掉的決策若沒人檢查，幾乎不可見
- 而「檢查什麼」若沒先定義，就永遠不會自動發生

結果就是：
- 系統只會長大
- 只會意外縮回
- 過去決策不會真正回饋到未來決策

---

## 範圍

這一層適用於：
- accepted expansion proposals
- trigger threshold / severity definition 的重大變更
- proposal gate requirement 本身的重大調整

不適用於：
- 純 documentation update
- wording clarification
- log 中的 `doc_updated` 類 resolution

這一層治理的是模型結構性變更，不是日常維護。
