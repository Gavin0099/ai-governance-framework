# AI Governance 變異契約：審查收尾閘門

狀態：`PENDING`
日期：2026-06-27
範圍：文件契約定義；不納入目前兩個未追蹤 Python 檔案

## 問題

目前工作樹有兩個未追蹤檔案嘗試以變異驗證（mutation proof）命名審查收尾
閘門（reviewer closeout gate）檢查，但它們只包裝現有的標準收尾行為，
沒有套用或模擬原始碼變異。

若直接納入，會讓審查者誤以為儲存庫已證明「移除審查收尾閘門會被偵測到」。
實際上，E1 變異目錄對規則變異（rule mutation）的門檻更高：必須有明確
變異契約、測試樣本、預期違規碼，以及隔離執行的真實規則變異。

## 目前儲存庫事實

- 變異目錄：`docs/e1-mutation-catalog.md`
- 既有真實規則變異執行腳本：`governance_tools/mutation_proof_runner_phase2.py`
- 既有 closeout 變異場景：`closeout_bypass`
- 主要治理表面：`governance_tools/state_reconciliation_validator.py`
- 既有檢查邊界：`assess_phase_d_closeout`
- 預期違規碼：`phase_d_completed_without_reviewer_closeout_artifact`
- 既有第二階段解讀：`VULNERABLE` 表示變異逃過測試，缺口被記錄；不表示整個
  治理強制機制已失效。
- 目前未追蹤檔案：
  - `governance_tools/reviewer_closeout_mutation_proof.py`
  - `tests/test_governance_mutation_proof.py`

本切片不納入、改名、暫存、提交或修補這兩個未追蹤檔案。

## 目標結果

把審查收尾閘門的變異契約重新固定到既有 E1 第二階段模型：

- 標準變異場景使用 `closeout_bypass`。
- 真實規則變異必須修改 `state_reconciliation_validator.py` 的收尾閘門區塊。
- 測試樣本必須讓 `PLAN.md` 或 state 把 Phase D 標成 passed，同時缺少
  `artifacts/governance/phase-d-reviewer-closeout.json`。
- 成功判定必須以精確違規碼
  `phase_d_completed_without_reviewer_closeout_artifact` 是否仍出現為準。
- 包裝式失敗即關閉回歸輔助檢查不能宣稱變異驗證。

## 範圍

本切片只允許：

- 記錄審查收尾閘門變異契約。
- 釐清 `closeout_bypass` 與未追蹤包裝式輔助檢查的差異。
- 對齊 `docs/e1-mutation-catalog.md` 的真實規則變異語意。

## 非目標

本切片不做：

- 不納入目前兩個未追蹤 Python 檔案。
- 不改 `governance_tools/**` 執行環境或執行腳本行為。
- 不改 `tests/**`。
- 不新增變異執行腳本。
- 不執行 `git worktree` 變異驗證。
- 不宣稱審查收尾閘門已取得 `PROTECTED`。
- 不宣稱審查收尾閘門已有跨工具冗餘。

## 受影響表面

- 文件表面：
  - `docs/governance/reviewer-closeout-gate-mutation-contract-2026-06-27.md`
  - `docs/e1-mutation-catalog.md`

未觸及的治理敏感表面：

- `governance_tools/**`
- `runtime_hooks/**`
- `schemas/**`
- `.github/workflows/**`
- 記憶寫入器 / 收尾 / 閘門政策檔案

## 邊界與 API 考量

這份契約不建立新 API。

若未來開實作切片，必須在獨立範圍內決定：

1. 沿用 `governance_tools/mutation_proof_runner_phase2.py` 的
   `closeout_bypass` 場景，並只修正文件、測試樣本或報告命名。
2. 或將包裝式檔案降級命名為失敗即關閉回歸輔助檢查，但不得稱為
   變異驗證。

兩者不能混在同一個宣稱裡。`PROTECTED` 只能來自真實規則變異後仍能觀察到
精確違規碼；目前包裝式輔助檢查只能支持目前行為回歸宣稱。

## 失敗路徑或風險點

- 若把包裝式輔助檢查當成變異驗證，會造成治理強制機制宣稱膨脹。
- 若另創 `remove_reviewer_closeout_gate` 名稱，會和既有 `closeout_bypass`
  變異目錄 / 執行腳本場景分裂。
- 若只看標準收尾結構描述結果，會錯過真正的
  `state_reconciliation_validator` 閘門移除風險。
- 若把 `VULNERABLE` 解讀成治理強制機制已失效，會把已記錄的單點缺口
  誤讀成整體治理失效。

## 證據計畫

文件契約切片的最小驗證：

- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/reviewer-closeout-gate-mutation-contract-2026-06-27.md`
- 確認 `git status --short` 仍顯示兩個未追蹤 Python 檔案未被暫存。
- 子代理唯讀審查：檢查宣稱上限、E1 變異目錄對齊，以及未追蹤檔案
  是否保持排除。

未來實作切片的驗證，若真的要改執行腳本或測試，才需要：

- 針對受影響測試的聚焦 pytest
- `governance_tools/mutation_proof_runner_phase2.py --scenario closeout_bypass`
- 檢查工作樹清理

## 實作切片建議

下一個最小實作切片應二選一：

1. **真實規則變異路徑**：沿用 `closeout_bypass`，補齊或重跑第二階段執行腳本
   的審查者用報告，並保持 `VULNERABLE` / `PROTECTED` 解讀一致。
2. **回歸輔助檢查路徑**：把包裝式檔案重新命名與降級成失敗即關閉
   回歸輔助檢查，不使用變異驗證名稱，不更新 E1 `PROTECTED` 狀態。

在這兩條路徑被明確選定前，目前兩個未追蹤 Python 檔案應維持排除。

## 用語規範套用狀態

本文件已套用 `docs/governance/ai-governance-document-language-style-guide-2026-06-27.md`
的中文主讀格式：

- 人類敘事以中文為主。
- 檔名、路徑、變異場景、違規碼、欄位名稱與原始狀態保留原文。
- 保留原文的識別字使用 backtick。
- `mutation proof` 類語意以「變異驗證」描述。
- `runner` 類語意以「執行腳本」描述。
- `slice` 類語意以「切片」描述。

## 宣稱上限

本文件只能宣稱：

- 審查收尾閘門的變異契約已被文件化。
- 標準場景應對齊既有 `closeout_bypass`。
- 目前兩個未追蹤 Python 檔案不應作為本切片的變異驗證納入。

本文件不得宣稱：

- 已新增或修復變異驗證。
- 已執行測試或執行腳本。
- 審查收尾閘門已受 `PROTECTED` 保護。
- Phase E 治理強制機制已完成。
- 任何執行環境、鉤子機制、持續整合（CI）、結構描述、記憶或 `governance_tools` 行為已改變。
