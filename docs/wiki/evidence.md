# 證據邊界

治理最容易犯的錯，是把「容易計數的 artifact」誤當成「真正想改善的工程結果」。

## Truthfulness 與 Quality 不同

| 問題 | 寫入當下能否確定 | 適合 validator 嗎 |
|---|---:|---:|
| commit hash 是否存在 | 可以 | 可以 |
| receipt 是否綁定該 commit | 可以 | 可以 |
| test command 是否退出 0 | 可以 | 可以 |
| `next_step` 是否真的幫到下個 session | 不可以 | 不適合硬 gate |
| memory 是否降低重查時間 | 需後續觀察 | 應量 outcome |
| Skill 是否讓 bug 修得更好 | 需對照任務 | 應做實驗 |

Quality 通常要到下一段工作才可知。長度、欄位、動詞等 proxy 可以檢查格式，不能證明實際有用。

## Gate 2 在驗證什麼

Gate 2 的困難，不是 recipe 很複雜，而是要區分：

```text
Skill 的效果
vs.
模型隨機性
vs.
任務難度差異
vs.
reviewer 或工具鏈介入
```

一個可信的對照至少需要：

- 相同或可比較的起點；
- control 與 treatment 隔離；
- 獨立 expected behavior；
- 防止答案洩漏；
- 固定或記錄模型、工具與環境；
- scorer 不知道 arm identity；
- 保存 diff、test 與 decision evidence；
- 將實驗成本列入結果。

## 何時應停止補證據

每多一項 artifact，都應回答它會改變哪個決策。以下通常不是有效進展：

- 只讓 receipt 更漂亮，卻不影響 outcome 判定；
- 為每次 reviewer 疑問新增 schema；
- 成功標準在看到結果後反覆調整；
- 實驗管理成本遠大於被測 Skill；
- 尚未跑自然任務，就先建立 dashboard 或 ROI calculator。

## G3 與 G4

G3 可代表治理能力與證據鏈已相對成熟；G4 則需要持續、可比較、非作者獨立使用的工程 outcome。

G4 不能由以下數字推出：

- session-derived record 數；
- commit 數；
- validator 數；
- receipt 數；
- test 數；
- consumer 清單長度。

仍需要的證據包括：

- 真實任務的 before／after rework；
- naturally occurring interception；
- false positive／false negative；
- 非作者在無 owner 協助下使用；
- memory 是否減少跨 session 重查；
- receipt 是否改變後續 Agent 行為；
- 收益是否大於執行與維護成本。

## Wiki 自己的證據邊界

這個網站 build 成功，只能證明：

- 公開 allowlist 的內容可被建置；
- 站內連結與 VitePress 結構在該 commit 可解析；
- GitHub Actions 有產生可部署 artifact。

它不能證明：

- 所有頁面語義都正確；
- repo 的治理機制都有效；
- GitHub Pages 已在 repository settings 啟用；
- consumer adoption 或 Gate 2 已完成。
