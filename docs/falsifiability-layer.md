# Falsifiability Layer

> Version: 1.0
> Related: `docs/misinterpretation-log.md`, `docs/anti-ritualization-patterns.md`, `docs/decision-quality-invariants.md`

---

## 目的

`Falsifiability Layer` 用來約束所有 expansion proposal、模型調整與治理變更：

> 一個 proposal 不能只描述自己為什麼看起來合理，還必須說明在什麼條件下應被視為失敗。

這一層的核心不是悲觀，而是防止 system 用漂亮的 reasoning 掩蓋不可驗證的調整。

---

## 核心要求

每個重要 proposal 在被接受時，都應盡量同時附帶一個 `falsification condition`。

一個可接受的 falsification condition 至少要具備：

- **Specific**：指出哪種 failure signal 算作失敗
- **Observable**：必須能從 log、artifact、reviewer 行為或其他 surface 被看到
- **Time-bounded**：不能無限延後，應有 observation window
- **Decision-reversing**：一旦命中，要能觸發 re-evaluation，而不是只有紀錄

如果 proposal 完全說不出自己在什麼情況下會被證明無效，通常代表它還只是 narrative，不足以升格成治理調整。

---

## Process Quality 與 Decision Quality

process quality 很重要，但不等於 decision correctness。

一個 proposal 可能：

- reasoning 很完整
- evidence 看起來很多
- 文件寫得很漂亮

但若沒有 falsifiability，它仍可能只是不可驗證的自我說服。

`Falsifiability Layer` 的功能，就是把 process quality 再往前推一步，要求 proposal 必須留下失敗條件與可逆路徑。

---

## Falsification Condition 範例

### 不夠好的寫法

> If the problem persists, we would know the dimension was insufficient.

問題：

- `problem persists` 太模糊
- 沒有 baseline
- 沒有時間窗口

### 比較好的寫法

> If `activation_state` continues to appear in log entries as a decision input
> at a rate of 2+ entries per observation window after the new dimension is introduced,
> the dimension failed to address the root cause.

### 另一個例子

> If the total log entry rate does not decrease in the observation window
> following the change, the dimension added complexity without reducing
> misinterpretation frequency.

---

## 命中 falsification 後要做什麼

當 falsification condition 被命中時，不能只記一筆事件然後繼續前進。
至少要完成：

1. 在 `misinterpretation log` 中記錄 falsification event
2. 回看原 proposal 的 reasoning 與 evidence
3. 判斷 failure 屬於：
   - dimension design 問題
   - implementation 問題
   - falsification condition 本身定義得太弱
4. 產生明確 outcome，例如：
   - `doc_updated`
   - `model_adjusted`
   - `threshold_changed`
   - `no_change_with_justification`

---

## Guard Against Explanation Drift

命中 falsification 後，最容易出現的壞味道是 explanation drift，也就是：

- 把 failure 重新解釋成 edge case
- 說成 temporary issue
- 或宣稱是 unrelated factor

如果每次 falsify 都能用敘事繞過，falsifiability 就只是形式，不是約束。

所以這一層要求：

> 命中 failure condition 時，預設應先進入 re-evaluation，而不是先找理由保住原 proposal。

---

## 與 Misinterpretation Log 的接點

observation window 結束時，`misinterpretation-log` 應能回答：

> 這個 proposal 的 falsification condition 是否被命中？

如果答案是 yes，就要觸發 re-evaluation。
如果答案始終無法判定，表示 observation 設計本身還不夠好。

---

## 不是什麼

`Falsifiability Layer` 不是：

- 為了形式而多寫一段 if-then
- 對每個小改動都要求重型驗證
- 用來否定所有治理調整

它的作用是：

> 把重要 proposal 從「看起來合理」推到「若失敗時也能被系統誠實承認」。
