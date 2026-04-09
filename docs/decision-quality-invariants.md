# Decision Quality Invariants：如何區分「真的正確」與「只是還沒被打臉」

> 版本：1.0  
> 相關文件：`docs/falsifiability-layer.md`、`docs/learning-loop.md`、`docs/learning-stability.md`、`docs/governance-mechanism-tiers.md`

## 目的

一個 decision 沒有產生 failure，不等於它已被驗證；它只是不曾被反駁。

absence of failure 可能代表三種情況：

1. decision 真的是對的
2. decision 還沒被充分測到
3. 測試條件根本沒涵蓋它會失敗的情境

learning loop 處理的是 failure。  
falsifiability layer 處理的是「如何證明 decision 錯了」。  
這份文件補的是最後那個缺口：

> 一個 decision 要怎樣才算 genuinely correct，而不只是暫時沒被挑戰？

## 三個 invariants

### 1. Consistency

**同樣的 evidence，應導出同樣的 decision。**

如果兩個 reviewer 或同一 reviewer 在不同時間，對 materially identical input 做出不同 decision，至少有一個 decision 有問題，或者 decision process 並沒有真的被既定 criteria 約束。

Consistency 不是 uniformity，而是：

- decision 由 evidence 和 stated criteria 決定
- 不該由 reviewer 身分、時機、或無關上下文決定

### 2. Robustness

**不相關的變化，不應改變 decision。**

如果 decision 會因 wording、順序、reviewer 疲勞、環境脈絡等 irrelevant variation 而改變，表示 decision basis 混入了噪音。

Robustness 不是 rigidity，而是：

- 該穩定的地方保持穩定
- 真正 relevant 的變數才允許影響結果

### 3. Positive Falsifiability

**每個被接受的 decision，都應該有一個可觀測條件，讓我們日後能說它是對的。**

falsifiability layer 定義的是「什麼情況下 decision 會被證明錯」。  
positive falsifiability 則要求：

> 什麼觀測結果會讓我們說：這個 decision 被驗證了，而不是只是沒出事。

可接受的形式應類似：

> 如果在某個時間範圍內出現某個具體可觀測結果，且沒有某個 confound，那麼這個 decision 可視為得到正向驗證。

## Misaligned Success

misaligned success 指的是：

- 系統的表面指標看起來健康
- failure rate 很低
- log 很乾淨
- verdict 也很穩定

但實際上 decision quality 正在下降。

常見形式：

- **over-conservatism**：系統只敢在熟悉區域做決策
- **blame-avoidance routing**：選擇較不容易被歸責的決策路徑
- **coverage narrowing**：能影響決策的 evidence type 越來越少
- **exploration reduction**：系統不再測試自己的邊界

這些情況都可能維持低 failure rate，卻是 decision quality degradation。

## 與 learning loop 的關係

learning loop 在 failure 出現時閉環。  
decision quality invariants 則要求：就算沒有 failure，也要問 decision 是否真的被驗證。

最低限度的正向證據應至少符合一項：

- 相似 evidence 由不同 reviewer 複核後得到相同 decision
- 經 irrelevant variation 測試後，decision 沒變
- 事先定義的 positive falsifiability condition 被觀測到

如果三者都沒有，就不能說 decision 已被驗證；最多只能說它尚未被反駁。

## 目前不提供的東西

這份文件目前**不提供**：

- consistency 的自動量測系統
- robustness 的完整 probing framework
- positive falsifiability 的 runtime hard gate

也就是說，這三個 invariant 目前主要是：

- diagnostic properties
- periodic review prompts

而不是 fully instrumented control mechanisms。

## 一句話結論

這份文件要守住的是：低 failure rate 不等於高 decision quality；若沒有 consistency、robustness、與 positive falsifiability，系統只是在累積「還沒被證偽的決策」。
