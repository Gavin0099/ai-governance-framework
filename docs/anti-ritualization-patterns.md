# Anti-Ritualization Patterns

> 版本：1.0
> 相關文件：`docs/misinterpretation-log.md`, `docs/falsifiability-layer.md`, `docs/learning-loop.md`

---

## 目的

這份文件用來描述 framework 在治理成長過程中最需要避免的一種退化：

> 機制還在，但語義已經空掉；流程看起來更完整，判斷卻沒有變得更可靠。

這裡把這種退化稱為 `ritualization`。

ritualization 不是單純文件很多，也不是流程很多，而是：

- scaffold 存在，但沒有真正約束行為
- wording 很漂亮，但 reviewer 仍無法重建判斷
- observation 被記錄了，但沒有形成可驗證結果

---

## 核心判斷

要判斷某個機制是否 ritualized，不看它「有沒有做」，而看它是否仍保有下列能力：

- 能產生 reviewer 可用的判讀差異
- 能對後續 decision 產生 bounded influence
- 能指出 failure 在哪裡成立
- 能被 falsify，而不是只靠敘事保住自己

如果某個機制只剩形式存在，卻不再改變任何可觀測判斷，它就很可能已 ritualized。

---

## 常見模式

### Pattern 1：Scaffold Presence

**形式**

- 有模板
- 有表格
- 有欄位
- 有固定步驟

**問題**

團隊開始把 scaffold 的存在本身當成治理完成，而不再檢查內容是否真的支撐判斷。

**Detection signal**

- reviewer 能指出欄位存在，但說不出其判斷意義
- artifact 內容大量重複 generic wording
- same template repeatedly yields no decision differentiation

### Pattern 2：Blind Spot Labeling

**形式**

- 每次都會寫 blind spot
- 每次都會列 risk
- 每次都會說需要更多 evidence

**問題**

blind spot 變成固定陪襯，而不是具體指出這次看不到什麼、因此不能判什麼。

**Detection signal**

- blind spot 敘述可替換到任何 run 而不影響意思
- reviewer 讀完仍不知道缺的是哪個 decision input

### Pattern 3：Observation Without Decision Use

**形式**

- 有 log
- 有 trace
- 有 signal

**問題**

observation 被記錄下來，但沒有形成後續可用語義，只是累積 activity。

**Detection signal**

- signal 出現與否不改變 reviewer interpretation
- trace 增長，但沒有形成可重建結論

### Pattern 4：Activity as Progress

**形式**

- log entry 變多
- checklist 變多
- update 次數變多

**問題**

系統把 activity volume 誤當 progress，卻沒有證據顯示 recurring failure 降低。

**Detection signal**

- change rate 增加，但 recurring failure 沒下降
- reviewer workload 上升，但 clarity 未改善

### Pattern 5：Severity Inflation

**形式**

- 越來越多項目被判成 medium/high
- escalation 常態化

**問題**

severity 失去區分力，最後所有問題都被說得很重要，但系統沒有更好地處理真正重要的問題。

**Detection signal**

- medium/high 分布長期失衡
- escalation 數量增加，但 correction quality 未改善

---

## 防止 ritualization 的最低要求

一個 companion mechanism 若要避免 ritualization，至少要保有：

1. 明確用途：它是用來改善哪一段判斷？
2. 明確 consumer：誰會讀？怎麼用？
3. 明確邊界：不能被拿來做什麼？
4. 明確 falsifiability：何時算它已失效？

---

## 不是什麼

這份文件不是要反對 scaffold、template 或 workflow。

它要防的是：

> 系統把形式保留下來，卻默默失去原本想保護的判斷能力。
