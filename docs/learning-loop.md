# Learning Loop

> Version: 1.0
> Related: `docs/falsifiability-layer.md`, `docs/misinterpretation-log.md`

---

## 目的

一個能偵測 failure、卻不會因此改變的系統，不叫 learning，只叫 logging。

這份文件定義本 framework 的最小 learning loop：
- failure 被觀察到之後，至少要發生什麼
- 哪些變化才算 learning response
- repeated failure 應如何改變之後的決策

learning loop 不是用來追究責任，而是確保觀察會產生更新，讓系統因經驗而變得不同。

---

## 三個核心問題

### 1. 每個 observed failure 都一定要改嗎？

**不用。**  
但每個 observed failure 都必須有一個明確決定：改，還是不改。

最小合法回應必須落在以下四種之一：

| Outcome | Meaning | Required documentation |
|---------|---------|----------------------|
| `model_adjusted` | 維度、threshold 或 mechanism 改了 | 改了什麼、為什麼 |
| `doc_updated` | 只澄清文件，模型不變 | 澄清了什麼、為什麼足夠 |
| `no_change_justified` | 看過後確認現行模型仍正確 | 為何這次 failure 不推翻模型 |
| `investigation_pending` | 資訊還不夠，先不決定 | 還缺什麼資訊、何時補齊 |

`investigation_pending` 不是無限期狀態。  
它必須在下一個 observation window 內轉成另外三種之一。

**不允許 silent non-response。**  
有 falsification event 卻沒有 documented outcome，等同 learning loop 沒有關閉。

---

### 2. 最小有效 change 長什麼樣？

#### 對 `model_adjusted`

必須是：
- 維度定義不同了
- threshold 真的變了
- mechanism 行為真的不同了

不能只是換句話說同一件事。

#### 對 `doc_updated`

必須是具體文件變更，而且能改變 reviewer 下一次遇到同類情況時的做法。  
若只是重寫 wording，卻不改變行為，不算 learning response。

如果同一 failure 再發生，先前的 `doc_updated` 就必須被重新檢查，而不是直接沿用。

#### 對 `no_change_justified`

必須書面說明：
- 這次 failure mode 是什麼
- 為什麼現行模型仍能正確處理
- 如果未來觀察到什麼，才會改變這個判斷

只有「模型沒問題」是不夠的。

---

### 3. Repeated failure 應如何改變未來決策？

同一類 failure 一再出現，不只是個別 incident，而是對模型結構的訊號。

當同一類 proposal 兩次以上被 falsify：

1. 這個類別進入 **skepticism zone**
2. 後續 proposal 在這區域需要更高 evidence bar
3. 必須明確把 pattern 命名出來，而不是只看成多個獨立 incident
4. 下一個 proposal 進來時，提案者必須回答：
   - 為什麼這次會成功，而前幾次失敗？

**skepticism zone 不是永久狀態。**  
若同一類連續兩次 proposal 都安全度過完整 observation window，就可以明確 retire 該 zone。

---

## 在這個系統裡，Learning 是什麼

learning 不是知道得更多，而是：

> 因為曾經觀察到 failure，系統之後真的表現得不一樣

最小 evidence 可以是：

- 某個決策和以前不一樣了
- 某個 category 被更審慎對待了
- 某個 mechanism 因 failure 被調整了
- 某個 assumption 被正式點名成尚未驗證

如果 failure 發生後，上述事情都沒有發生，那 learning loop 就沒有關閉。

---

## Learning Loop 的順序

```text
Proposal accepted with falsifiability condition
        ->
Observation window 執行
        ->
Window close：檢查 falsification condition 與 untested assumptions
        ->
   [No failure]                         [Failure observed]
        ->                                      ->
命名未驗證 assumptions                     記錄 outcome：
確認模型仍足夠                             model_adjusted / doc_updated /
negative pressure 生效                      no_change_justified / investigation_pending
```

若同一 category repeated failure：
- 命名成 skepticism zone
- 之後 proposal 必須回應 trajectory

---

## Learning Loop 不做什麼

- 不保證模型一定收斂到正確
- 不自動做決策
- 不取代 judgment

它只是決定：
- failure 被看見後，最低限度必須怎麼回應

---

## 與其他文件的關係

| Document | Role |
|----------|------|
| `misinterpretation-log.md` | 記 observation，觸發 falsification check |
| `falsifiability-layer.md` | 定義什麼叫 falsification condition |
| `anti-ritualization-patterns.md` | 檢查 learning loop 本身是否 ritualized |
| `learning-loop.md` | 定義 failure 發生後最低限度必須如何關閉 loop |

只有當 observation 真的產生 documented outcome，learning loop 才算關閉。
