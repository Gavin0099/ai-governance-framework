# 系統架構

框架的真正邊界不是檔案數量，而是從授權到 publication 的證據鏈是否閉合。

## 端到端路徑

| 階段 | 問題 | 主要產物 |
|---|---|---|
| Session start | 這次工作受哪些權威來源約束？ | Rules、PLAN、repo state |
| Pre-task | DONE、scope 與 required evidence 是什麼？ | Task contract |
| Agent execution | 修改是否保持在授權邊界？ | Diff、tool output |
| Post-task | 證據是否真的支持完成宣稱？ | Test output、validator result |
| Decision gate | 缺 scope、缺 evidence 或 authority 不明時怎麼辦？ | PASS / FAIL / BLOCKED |
| Closeout | 下一個人能否重查本次結果？ | Receipt、non-claims |
| Memory | 下一個 session 從哪個已驗證狀態開始？ | Commit-bound handoff |

## Authority 分層

治理文件不是同等權威。實作與 reviewer 應先確認：

1. canonical：定義正式行為與邊界；
2. reference：解釋或提供操作格式；
3. derived：由工具產生的摘要、matrix 或狀態；
4. session-derived：特定工作階段的觀察與交接。

derived artifact 不能反向覆蓋 canonical contract；一次 session 成功也不能自動升級為永久規則。

## Publication path 才是強制邊界

一個 validator 存在，不代表它會阻擋錯誤進入 `main`。要宣稱 enforced，至少要能回答：

- 哪個事件會呼叫它？
- 失敗時 exit code 與 workflow 結果是什麼？
- direct push、不同 Agent surface 或手工更新能否繞過？
- gate 驗證的是實際發布內容，還是較早的暫存狀態？
- branch protection 是否真的要求該 check？

## 公開 Wiki 的資料邊界

這個網站採明確 allowlist：

| 來源 | 用途 | 是否直接發布 |
|---|---|---|
| `docs/wiki/**` | 人工維護的 Wiki 內容 | 是 |
| `README.md` | 版本與對外定位摘要 | 僅抽取公開欄位 |
| `PLAN.md` | 最後更新日與 canonical 連結 | 僅抽取公開欄位 |
| `CHANGELOG.md` | 最新 release heading | 僅抽取公開欄位 |
| `.agents/skills/*/SKILL.md`、`.claude/skills/*/SKILL.md` | Skill 名稱與描述 | 僅抽取 metadata |

`memory/`、`artifacts/`、receipts、transcripts、consumer 私有資訊不會被 generator 掃描。
