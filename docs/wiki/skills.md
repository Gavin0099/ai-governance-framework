# Skills 與工程方法

「Repo 有 Skills」不等於「Agent 更會寫 code」。先分清楚 Skill 在介入哪個階段。

## Governance Skill

主要改善實作前後的工程收斂：

- tech spec；
- precommit；
- runtime smoke；
- reviewer handoff；
- external onboarding；
- domain contract authoring；
- wrap-up。

它們能限制 scope、提高 evidence quality、改善 review 與 handoff，但不直接提供 root-cause algorithm。

## Engineering Skill

直接介入實作方法，例如：

- 系統化 debug；
- regression-first bug fix；
- safe refactor；
- API evolution；
- concurrency diagnosis；
- performance profiling；
- driver／firmware 特定修正策略。

這類 Skill 必須用 coding outcome 驗證，不能只因 recipe 看起來合理就正式發布。

## Bug Fix Safety 的合理假設

一套候選流程可以是：

1. 重現 bug；
2. 提出 root-cause hypothesis；
3. 建立獨立 expected behavior；
4. 寫出修正前會失敗的 regression test；
5. 做最小修正；
6. 跑 targeted tests；
7. 確認測試確實能抓回原始缺陷；
8. 執行適用 validator；
9. 限制完成宣稱。

這套設計「合理」與「已證明有效」是兩件事。正式採用前至少要回答：

- treatment 是否比 control 更常找到正確 root cause？
- 是否減少錯誤修改或返工？
- 額外 token 與工時是多少？
- 不同模型／任務的效果是否穩定？
- 失敗時是 Skill 無效，還是實驗工具鏈造成？

## Skill admission 原則

新的 Skill 不應因為「可能有用」就加入。合理門檻：

- 有自然任務暴露重複失敗；
- 現有規則無法覆蓋；
- recipe 能改變一個可觀測決策；
- 有清楚的重評與淘汰條件；
- 量測包含使用成本，不只成功率。

目前 repo 實際偵測到的 Skill metadata，請看[Repository 自動摘要](./generated/repository-status)。該頁由每次 build 重新產生，避免手寫數量長期失真。
