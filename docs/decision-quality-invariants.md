# Decision Quality Invariants：決策品質的不變條件

> 版本：1.0  
> 關聯文件：`docs/falsifiability-layer.md`、`docs/learning-loop.md`、`docs/learning-stability.md`、`docs/governance-mechanism-tiers.md`

## 目的

這份文件定義 decision quality 不應只靠 failure absence 來判定。
沒有失敗，不代表：
1. decision 本身是正確的
2. decision 的依據是穩定的
3. 系統具備在真實壓力下維持品質的能力

`learning loop` 負責收集 failure。  
`falsifiability layer` 負責確保 decision 可被檢驗。  
這份文件則定義那些即使 failure rate 看起來不高，也不能被放棄的品質不變條件。

> 一個 decision 要被視為 genuinely correct，不能只靠「沒有出事」來證明。

## 核心 invariants

### 1. Consistency

**在相同 evidence 與相同 criteria 下，應得到相容的 decision。**

如果兩個 reviewer 或兩次重建在 materially identical input 下得到不同 decision，問題不一定在結果本身，也可能在 decision process 的 criteria 不夠穩定。

Consistency 不等於 uniformity，而是要求：
- decision 能對應到 stated criteria
- reviewer 之間不會因無關變因而產生實質分歧

### 2. Robustness

**在無關變因改變時，decision 不應輕易漂移。**

如果 decision 會因 wording、reviewer 表達方式、或其他 irrelevant variation 而改變，代表 decision basis 對噪音過度敏感。

Robustness 不等於 rigidity，而是要求：
- 能抵抗無關的表述差異
- 對 relevant variation 保持足夠敏感

### 3. Positive Falsifiability

**系統必須能指出：在什麼條件下，現在的 decision 會被推翻或被證明不足。**

`falsifiability layer` 的意義，不是要否定 decision，而是要讓 decision 具備可被檢驗的條件。
`positive falsifiability` 的重點是：

> 若沒有辦法指出什麼 evidence、什麼情境、或什麼 probing 會改變目前的 decision，就很難說這個 decision 真正可被驗證。

這不是鼓勵隨意推翻，而是要求系統能明示 confound、反例條件與可檢驗界線。

## Misaligned Success

`misaligned success` 指的是：

- 指標看起來進步，但實際決策品質沒有提高
- failure rate 下降
- log 看起來乾淨
- verdict 看起來穩定

但 decision quality 仍然可能退化。  
常見形式包括：
- **over-conservatism**：過度保守，避開高風險情境以換取表面穩定
- **blame-avoidance routing**：把責任推向更安全的路徑，而不是改善判斷品質
- **coverage narrowing**：只關注容易量化的 evidence type，忽略關鍵訊號
- **exploration reduction**：減少 probing，讓錯誤不容易被發現

因此，光看 failure rate，無法保證沒有 decision quality degradation。

## 與 learning loop 的關係

`learning loop` 收集 failure 與改進訊號；  
`decision quality invariants` 則避免系統把「failure 變少」誤認為「decision 變好」。

真正值得追蹤的，不只是某次修復是否通過，而是：

- 相同 evidence 是否仍能被 reviewer 穩定重建成相容 decision
- irrelevant variation 是否仍會讓 decision 漂移
- 是否仍能指出 positive falsifiability condition

如果這些條件不成立，即使 failure rate 暫時下降，也不能直接宣稱 decision 品質已經提高。

## 在目前 repo 的定位

這份文件目前是**方法論約束**，不是：
- consistency 的自動化 gate
- robustness 的完整 probing framework
- positive falsifiability 的 runtime hard gate

它目前提供的是：
- diagnostic properties
- periodic review prompts
- 用來校正 learning loop 的判讀邏輯

不是 fully instrumented control mechanism。

## 一句總結

這份文件要表達的是：降低 failure 不是 decision quality 的充分條件；只有當 consistency、robustness 與 positive falsifiability 都維持住，才比較能說 decision 系統真的變好。
