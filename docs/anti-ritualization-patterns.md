# Anti-Ritualization Patterns

> Version: 1.0
> Related: `docs/misinterpretation-log.md`

---

## 目的

任何需要人類思考的治理機制，都可能在形式上被遵守，但真正的思考並沒有發生。  
這就是 ritualization：形式還在，實質已經消失。

這份文件整理：
- 哪些 framework 機制最容易 ritualize
- ritualized compliance 長什麼樣
- 應該看哪些 detection signal

它**不新增規則**。  
它只是幫你辨認：既有規則是否已經失去作用。

**Scope limitation：**  
本 framework 的 scaffold 主要用來支撐需要 justification 的顯性推理。  
在低模糊、低歧義情境中，它不應取代有經驗者的直覺判斷。若強迫所有判斷都重建成顯性 scaffold，反而可能拖慢決策卻不提升品質。

---

## Ritualization 長什麼樣

ritualization 通常不是惡意，而是自然的最低認知阻力路徑。  
原本用來幫助正確思考的 scaffold，久了也會變成一種模板：產出看起來像正確思考的東西，但其實沒經過真正思考。

常見 signal：
- misinterpretation log 的 entries 越來越短
- 不同 reviewer 寫出越來越相似的套話
- observation 和 log entry 的時間差固定非常短
- counterfactual 欄位總是套同樣格式
- 在整個 observation window 中沒有人質疑任何 grouping decision

---

## Pattern Catalog

### Pattern 1：只填 scaffold，沒有真正推理

**Mechanism：** expansion proposal gate 的 counterfactual scaffold

**Ritualized form：**

```text
Alternative mechanism: Could be temporary behavior
Why this mechanism fails: Because it happened multiple times
```

**問題在哪裡：**
- `Could be temporary` 沒有指出任何具體機制
- `happened multiple times` 不是反駁機制，而只是重述觀察

**Detection signal：**  
「Why this mechanism fails」沒有指向任何具體 system property，例如檔案、時間範圍、流程、計數、人員。  
如果這段話可原封不動貼到任一 proposal 仍成立，通常就是 ritualized。

**Self-detection probe：**  
你最沒把握的是哪一段推理？如果答不出來，或回答「全部都很有把握」，有可能根本沒真的建構推理過程。

---

### Pattern 2：ritual blind spot

**Mechanism：** expansion proposal gate 中的 blind spot requirement

**Ritualized form：**

```text
Unobserved area: Other parts of the system
```

或

```text
Unobserved area: Modules not yet covered
```

**問題在哪裡：**  
這些句子永遠成立，但完全不需要理解系統，也不指出任何可調查的對象。

**Detection signal：**  
其他 reviewer 能根據這段 blind spot 描述真的去調查某個東西嗎？如果不能，通常是 ritualized。

**Self-detection probe：**  
你能不能點名一個具體檔案、hook、workflow，說它可能有同樣問題但尚未檢查？如果不能，代表 blind spot requirement 沒有被實質滿足。

---

### Pattern 3：去掉關鍵字，但結論還在

**Mechanism：** interpretation vs observation 的語言區分測試

**Ritualized form：**

```text
Activation state was applied in a context where it influenced the outcome
of the review.
```

**問題在哪裡：**  
表面上沒有使用 `misused`、`incorrectly` 這種字，但 `influenced the outcome` 其實還是在偷偷帶結論。

**Detection signal：**  
另一位 reviewer 若有不同先驗，能不能基於這句話讀出不同結論？如果不能，它仍然在輸送判斷，而不是純觀察。

**Self-detection probe：**  
如果完全不暗示對錯，你會怎麼描述 reviewer 真正做了什麼？若那個版本和原文差很多，原文多半仍是 conclusion-laden。

---

### Pattern 4：沒有 activity，卻拿「沒新問題」當證據

**Mechanism：** negative pressure rule（沒有新 entries = model 足夠）

**Ritualized form：**  
reviewer 在 observation window 結束時寫：

> no new misinterpretations observed

但那段時間其實幾乎沒有 meaningful reviewer interaction。

**問題在哪裡：**  
negative pressure 只有在真的有觀察發生時才有意義。  
「因為沒看，所以沒看到」不是 sufficiency 證據。

**Detection signal：**  
這個 window 中到底有幾個實際 reviewer interaction？若少於 3 個，window 結果通常不具代表性。

**Self-detection probe：**  
你能不能說出一個這個 window 裡實際發生、但沒有出現 misinterpretation 的 reviewer interaction？如果不能，這個 window 很可能沒有足夠 activity。

---

### Pattern 5：severity inflation

**Mechanism：** low / medium / high severity classification

**Ritualized form：**  
多個 window 下來，幾乎所有 entry 都被歸成 `medium`，卻沒有再分類、再校正或 resolution。

**問題在哪裡：**  
`medium` 變成預設檔位，而不是有語義的分類。severity gradient 被壓平了。

**Detection signal：**  
若當前 log 幾乎全部是 `medium`，而不是依觀察類型分散在 low / medium / high，很可能分類已 ritualized。

**Self-detection probe：**  
最近三個 `medium` entry，有沒有其實可以算 `low`？若無法講出它們為何不是 `low`，那 `medium` 可能只是 reflexive default。

---

## 偵測到 Ritualization 之後該怎麼做

ritualization 不是要懲罰的 violation，而是 signal：  
代表某個機制已經太容易被形式遵守。

正確回應是修機制，不是怪 reviewer。

當某 pattern 被確認 ritualized：

1. 在 misinterpretation log 記一筆：
   - `type = under-reading`
   - `owner = framework`
2. 判斷這個機制需要的是：
   - 更高 friction
   - 更銳利的 example
   - 更好的 probe question
3. 修原機制，不要只是再疊更多規則

**不要靠新增 companion mechanism 來補 ritualized mechanism。**  
一個 ritualized mechanism 加上新 companion，常常只會得到兩個 ritualized mechanism。

如果一個機制持續需要加規則才不會被誤用，問題可能不是 wording，而是抽象層級錯了。

---

## 最難察覺的 Ritualization

最危險的 ritualization，是 reviewer 主觀上真的覺得自己有在思考，但實際推理非常淺。

這無法完全靠 mechanism design 杜絕。  
最可靠的 signal 幾乎都來自外部：
- 另一位 reviewer 看完覺得不可信
- 後續觀察與原本淺推理預測完全不符

這也是為什麼：
- observation window
- reviewer diversity

比任何單一 scaffold 更重要。  
淺推理通常只會在高壓、長時間、或跨 reviewer 對照時暴露出來。
