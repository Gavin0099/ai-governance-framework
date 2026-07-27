# Agent 工作流程

這個流程的目的，是讓 Agent 的工作可收斂、可驗證、可交接，而不是增加每個小任務的 ceremony。

## 1. 先分類風險

| 類型 | 例子 | 合理流程 |
|---|---|---|
| L0 | typo、格式、presentation-only | 最小修改＋lightweight verification |
| 低風險 L1 | UI copy、狹義 user-facing behavior | 明確邊界＋targeted validation |
| L1 | workflow、I/O、schema 或 API 行為 | Analyze → Define → Verify plan → Implement |
| L2 | security、data integrity、driver／firmware critical path | 完整 architecture、testing 與 human approval |

風險分類不是看改幾行，而是看錯誤後果與跨越的 boundary。

## 2. 定義窄而可驗證的 DONE

好的 DONE：

```text
DONE = 使用者在更新失敗時會看到可採取行動的錯誤訊息，
       且既有成功路徑測試保持通過。
```

不好的 DONE：

```text
DONE = 改善更新流程並補齊治理。
```

後者沒有可量測停止條件，容易把 bug fix 擴張成架構整理或治理新增。

## 3. 先建立可信 expected behavior

Regression test 不應只是複製 production logic。可信 oracle 可以來自：

- 已批准 spec；
- 可重現的既有行為；
- 獨立 reference implementation；
- user-visible acceptance condition；
- domain authority 與明確 boundary case。

如果 expected value 本身不獨立，測試通過只代表兩份相同錯誤彼此一致。

## 4. 做最小修正

實作期間維持：

- 不讀、不改無關 dirty files；
- 不因順手而 refactor 相鄰模組；
- 新 abstraction 必須回答實際 failure；
- targeted tests 先於 full regression；
- 達到 DONE 後停止。

## 5. 將驗證綁定實際版本

完成前確認：

1. diff 是預期 scope；
2. test 確實執行且 result 可重查；
3. evidence 對應目前 commit，而不是較早版本；
4. final response 的宣稱沒有超過證據；
5. 未驗證項目放進 `not_claimed`。

## 6. 交接

一份有用的 handoff 應讓下一個人不用重做整段調查：

- what changed；
- commit；
- test evidence；
- unresolved risk；
- next step；
- cannot claim。

`next_step` 是先前 session 的候選建議，不是未來 Agent 的自動授權；接手時仍要重新確認 repo state 與當前使用者指令。

## 何時不值得套完整流程

一次性 script、prototype、幾分鐘能人工確認的小修正，若治理成本高於返工風險，應走低 ceremony 路徑。治理的判準不是「有沒有留下最多 artifact」，而是「是否以合理成本降低了真實錯誤」。
