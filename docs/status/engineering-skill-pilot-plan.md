# Engineering Skill G4 Pilot — Bug Fix Natural-Case Observation Plan

- Status: RATIFIED, DORMANT（等待自然案例）
- Owner confirmed: 2026-07-17（Gavin，主 session）
- Amendment owner confirmed: 2026-08-20（允許獨立 pre-registration commit、執行期 read-only、replay 後追加 observation，以及 `EXPIRED_NO_CASE` disposition）
- Review chain: Pattern Pack 提案 → Claude review（2026-07-17，六條 evidence 全數實測核實）→ reviewer plan → owner 確認
- Expiry: **2026-09-11**（8 週）。若期限內無自然案例觸發，依 §6 記為 `EXPIRED_NO_CASE` 並回到復審，不自動延續。

## Verdict

APPROVED — 僅批准 G4 假設與觀察方向。Risk Level: Medium。

**不批准**：現在建立六個 Pattern Pack、manifest、schema、validator 或 gate。

依據：G3→G4 owner-ratified boundary（`memory/00_long_term.md` §"G3 to G4 Consumer-Driven Outcome Goal", 2026-07-14）——gate/receipt/工具數量不構成 G4；需自然 consumer 任務的 outcome、成本、FP/FN 與 decision-effect evidence。

## DONE

完成一個**自然發生**的 consumer bug-fix work item，完成 consumer replay，並以一份人工 case record 記錄 outcome、治理成本、owner intervention、FP/FN 與 decision effect；不新增 Pack、Rule、Validator、Schema 或 Gate。

## 1. Admission gate

- 不製造 seeded defect；不為湊 G4 sample 選題。
- task owner 明確分類為 `bug_fix`（heuristic 分類僅 advisory，依 `governance/RULE_REGISTRY.md` Selection Boundary；Agent 不得自行改報任務類型）。
- 啟動前先在 §4 的 case record 完成 pre-registration：問題、實際影響、expected behavior 的權威來源、預期風險，以及預期會影響決策的既有治理表面。
- 沒有自然任務就不啟動、不造資料。

## 2. Workflow Card（人工，放該 consumer task 執行契約，不建 reusable Skill）

1. 重現問題。
2. 指出 expected behavior 的權威來源。
3. 建立修改前會失敗的 signal。
4. 區分 symptom、hypothesis、confirmed root cause。
5. 做最小修正。
6. 驗證 defect 重新引入時 regression test 會失敗（對齊 `governance/TESTING.md` §3.3）。
7. 在 originating consumer 做實際 replay。
8. 列出仍未證明的部分。

## 3. 執行範圍

- Consumer repo：僅該 bug 的 production files、直接相關 tests 與明確 allowlist。
- Framework repo：在任何 consumer production/test 修改前，只允許建立 §4 case record 的 pre-registration 區塊，並以一個獨立 commit 固定其原始 bytes 與 commit hash。Commit timestamp 只作 repository ordering metadata，不宣稱是可信 wall-clock 證明。
- Pre-registration commit 完成後至 consumer replay 完成前，Framework repo **read-only**。
- Consumer replay 完成後，只允許在同一份 case record 追加 post-case observation；pre-registration 區塊必須與建立該檔案的 commit 完全一致。這是 reviewable Git history 約束，不宣稱已有 validator 或 runtime enforcement。
- 不修改：`governance/RULE_REGISTRY.md`、`.agents/skills/**`、`governance_tools/**`、`runtime_hooks/**`、`schemas/**`、gate/receipt/contract semantics。

## 4. 人工 case record

路徑：`docs/status/engineering-skill-natural-case-<work-item>.md`（一次性 Markdown，非新 ledger schema，不自動累計 G4 分數）。

Pre-registration 區塊（consumer 修改前提交）：work-item identity；consumer/user/repo/domain；owner 的 `bug_fix` 分類；問題與實際影響；expected behavior 的權威來源；預期風險；預期會影響決策的既有治理表面；pre-registered hypothesis；`not_claimed` 清單。

Post-case observation（consumer replay 後追加）：sessions 與 owner interventions；修改前後 evidence；consumer replay；review/rework/reopen；observed FP/FN；實際 governance trigger；觀察到的 decision change；額外治理步驟與維護成本；recurrence/transfer evidence；更新後的 `not_claimed` 清單。

Pre-registration 是事前 hypothesis，不是 measured counterfactual。Post-case reviewer 必須從 case record 的建立 commit 讀回原始 pre-registration bytes，確認該區塊未被改寫；不相符時，本案例不得用於 decision-effect 判斷。

**decision effect 欄位必須標明 basis**：n=1 無對照組，只能是 `reviewer-counterfactual-judgment`，不得寫成 measured。cost evidence 同樣為 uncontrolled（無 baseline），STOP/MERGE/SECOND 判斷屬 owner judgment，非 metric-triggered。

## 5. Pilot decision gate（案例結束後三選一）

- **STOP**：無 outcome-complete、無 decision effect，或成本明顯大於價值。
- **MERGE**：有用部分屬於既有 `precommit`、`runtime-smoke` 或 `TESTING.md`，併入既有表面，不建新 Skill。
- **SECOND OBSERVATION**：具體正向 decision effect 且成本可接受；等待第二個獨立 consumer 自然案例。即使進入此路徑，仍不建六個 Pack。

負面前例（kill criteria 已有實例）：`codex-review-fast` 於單一 seeded harness 得到負面 `decision_effect` 後 deprecate 併入 reviewer-handoff/precommit。

## 6. Expiry disposition

若到 **2026-09-11** 仍無符合 admission gate 的自然 consumer `bug_fix`：

- 狀態改為 `EXPIRED_NO_CASE`；沒有案例不構成 Skill 無效或有效的證據。
- 不自動延長、不放寬成非 `bug_fix` 任務、不建立 Skill／Pack／Schema／Validator／Gate。
- Owner 復審時三選一：**STOP**；以書面理由與新 expiry 延長相同 admission gate；或另案明確修改 admission gate。修改 gate 不得以本 plan 的既有批准默默生效。

## Claim ceiling

可宣稱：完成一個自然 consumer observation；該工作項目的工程結果與治理成本；是否觀察到 candidate decision effect。

不可宣稱：已達 G4；Engineering Skill 造成結果改善；Bug Fix Pack 已被驗證；可泛化到其他 repo/domain/user/harness；六個 Pattern Pack 值得建立；新 enforcement 已存在。
