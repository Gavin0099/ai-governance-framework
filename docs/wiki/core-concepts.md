# 核心概念

AI Governance 的關鍵不是增加規則，而是把「誰授權、做了什麼、證據到哪裡、最多能宣稱什麼」分開。

## 三層治理

| 層級 | 解決的問題 | 常見實作 | 真正限制 |
|---|---|---|---|
| 機器強制 | 阻止已定義的不可接受狀態 | CI、gate、validator、exit code | 只能保護已接線的 publication path |
| 工具觸發 | 提供可重複、可查證的檢查 | CLI、dry-run、audit report | 有能力不代表每次都會被呼叫 |
| Agent 自律 | 要求說清楚範圍、證據與 non-claims | `AGENTS.md`、prompt、回覆契約 | 指導不能取代獨立驗證 |

不是所有規則都值得做成 blocker。強制面越大，誤擋、維護與 bypass path 也會越多；只有在錯誤成本、可判定性與實際接線都足夠時，才適合升級成機器強制。

## 四種 Claim class

| Claim class | 可以推論 | 不可以推論 |
|---|---|---|
| Enforced | 在明確寫出的 scope 內會阻擋 | 整套 framework 不可繞過 |
| Advisory | 工具會提示或報告 | 警告一定被處理 |
| Observation | 有資料供人判斷 | 系統已做出治理決策 |
| Cannot claim | 設計中、證據不足或尚未接線 | 功能已存在或已有效 |

## Evidence 不等於 Truth

證據只能支撐它實際觀測到的範圍：

- unit test 通過：支撐特定程式路徑；
- runtime smoke 通過：支撐特定環境中的最小執行；
- receipt 有效：支撐證據鏈的結構與綁定；
- memory 綁定 commit：支撐交接來源；
- reviewer approval：支撐該 reviewer 在指定證據下的判斷。

以上都不能單獨推出「系統安全」「所有 consumer 可用」或「Agent coding 能力提升」。

## DONE 與 Non-goals

一個可靠 task contract 至少要有：

```text
DONE = 一個可量測的產品結果
Allowed scope = 可以碰的檔案或行為
Forbidden scope = 明確不能碰的邊界
Validation = 用什麼證據判斷 DONE
Non-goals = 這一輪刻意不做什麼
```

DONE 的用途不是形式化，而是建立停止條件。達到後仍持續補 telemetry、schema 或相鄰治理功能，通常是 scope drift，不是品質提升。

## Audit framework，不是 Security boundary

這套框架可以：

- 讓手工更新被標記為不完整；
- 讓 evidence 缺失在已接線 gate 失敗；
- 讓 claim inflation 被 reviewer 看見；
- 讓修改與測試版本可以對應。

它不能：

- 阻止有權限的人直接繞過所有工具；
- 取代 OS sandbox、RBAC、branch protection 或企業 AIMS；
- 驗證自然語言是否語義正確；
- 保證每個 Agent surface 都載入同一套規則。
