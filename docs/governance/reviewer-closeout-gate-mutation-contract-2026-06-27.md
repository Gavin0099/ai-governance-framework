# AI Governance 變異契約：Reviewer Closeout Gate

狀態：`PENDING`
日期：2026-06-27
範圍：文件契約定義；不納入目前兩個未追蹤 Python 檔案

## 問題（Problem）

目前工作樹有兩個未追蹤檔案嘗試以 `mutation proof` 命名 reviewer closeout
gate 檢查，但它們只包裝現有的 canonical closeout 行為，沒有套用或模擬原始碼
變異。

若直接納入，會讓 reviewer 誤以為儲存庫已證明「移除 reviewer closeout gate
會被偵測到」。實際上，E1 catalog 對 rule mutation 的門檻更高：必須有明確
變異契約、測試樣本、預期違規碼，以及隔離執行的真實規則變異。

## 目前儲存庫事實（Current Repository Truth）

- 變異目錄：`docs/e1-mutation-catalog.md`
- 既有真實規則變異執行腳本：`governance_tools/mutation_proof_runner_phase2.py`
- 既有 closeout 變異場景：`closeout_bypass`
- 主要治理表面：`governance_tools/state_reconciliation_validator.py`
- 既有檢查邊界：`assess_phase_d_closeout`
- 預期違規碼：`phase_d_completed_without_reviewer_closeout_artifact`
- 既有 Phase 2 解讀：`VULNERABLE` 表示變異逃過測試，缺口被記錄；不表示整個
  enforcement 已失效。
- 目前未追蹤檔案：
  - `governance_tools/reviewer_closeout_mutation_proof.py`
  - `tests/test_governance_mutation_proof.py`

本 slice 不納入、改名、stage、commit 或修補這兩個未追蹤檔案。

## 目標結果（Target Outcome）

把 reviewer closeout gate 的變異契約重新固定到既有 E1 Phase 2 模型：

- canonical 變異場景使用 `closeout_bypass`。
- 真實規則變異必須修改 `state_reconciliation_validator.py` 的 closeout gate 區塊。
- 測試樣本必須讓 `PLAN.md` 或 state 把 Phase D 標成 passed，同時缺少
  `artifacts/governance/phase-d-reviewer-closeout.json`。
- 成功判定必須以精確違規碼
  `phase_d_completed_without_reviewer_closeout_artifact` 是否仍出現為準。
- 包裝式 fail-closed 回歸輔助檢查不能宣稱 mutation proof。

## 範圍（Scope）

本 slice 只允許：

- 記錄 reviewer closeout gate 變異契約。
- 釐清 `closeout_bypass` 與未追蹤包裝式輔助檢查的差異。
- 對齊 `docs/e1-mutation-catalog.md` 的真實規則變異語意。

## 非目標（Non-Goals）

本 slice 不做：

- 不納入目前兩個未追蹤 Python 檔案。
- 不改 `governance_tools/**` runtime 或 runner 行為。
- 不改 `tests/**`。
- 不新增 mutation runner。
- 不執行 git worktree mutation proof。
- 不宣稱 closeout gate 已取得 `PROTECTED`。
- 不宣稱 reviewer closeout gate 已有 cross-tool redundancy。

## 受影響表面（Affected Surfaces）

- 文件表面：
  - `docs/governance/reviewer-closeout-gate-mutation-contract-2026-06-27.md`
  - `docs/e1-mutation-catalog.md`

未觸及的治理敏感表面：

- `governance_tools/**`
- `runtime_hooks/**`
- `schemas/**`
- `.github/workflows/**`
- memory writer / closeout / gate policy files

## 邊界與 API 考量（Boundary And API Considerations）

這份契約不建立新 API。

若未來開 implementation slice，必須在獨立範圍內決定：

1. 沿用 `governance_tools/mutation_proof_runner_phase2.py` 的
   `closeout_bypass` 場景，並只修正文件、fixtures 或報告命名。
2. 或將包裝式檔案降級命名為 fail-closed 回歸輔助檢查，但不得稱為
   mutation proof。

兩者不能混在同一個宣稱裡。`PROTECTED` 只能來自真實規則變異後仍能觀察到
精確違規碼；目前包裝式輔助檢查只能支持目前行為回歸宣稱。

## 失敗路徑或風險點（Failure Paths Or Risk Points）

- 若把包裝式輔助檢查當成 mutation proof，會造成 enforcement claim inflation。
- 若另創 `remove_reviewer_closeout_gate` 名稱，會和既有 `closeout_bypass`
  catalog/runner 場景分裂。
- 若只看 canonical closeout schema 結果，會錯過真正的
  `state_reconciliation_validator` gate removal 風險。
- 若把 `VULNERABLE` 解讀成 enforcement 已失效，會把 documented single-point gap
  誤讀成整體治理失效。

## 證據計畫（Evidence Plan）

文件契約 slice 的最小驗證：

- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/reviewer-closeout-gate-mutation-contract-2026-06-27.md`
- 確認 `git status --short` 仍顯示兩個未追蹤 Python 檔案未被 stage。
- sub-agent read-only review：檢查 claim ceiling、E1 catalog 對齊，以及未追蹤檔案
  是否保持排除。

未來 implementation slice 的驗證，若真的要改 runner 或 tests，才需要：

- focused pytest for touched tests
- `governance_tools/mutation_proof_runner_phase2.py --scenario closeout_bypass`
- 檢查 worktree cleanup

## 實作切片建議（Implementation Tranche Recommendation）

下一個最小 implementation tranche 應二選一：

1. **真實規則變異路徑**：沿用 `closeout_bypass`，補齊或重跑 Phase 2 runner
   的 reviewer-facing report，並保持 `VULNERABLE`/`PROTECTED` 解讀一致。
2. **回歸輔助檢查路徑**：把包裝式檔案重新命名與降級成 fail-closed
   回歸輔助檢查，不使用 mutation proof 名稱，不更新 E1 protected status。

在這兩條路徑被明確選定前，目前兩個未追蹤 Python 檔案應維持排除。

## 宣稱上限（Claim Ceiling）

本文件只能宣稱：

- reviewer closeout gate 的變異契約已被文件化。
- canonical 場景應對齊既有 `closeout_bypass`。
- 目前兩個未追蹤 Python 檔案不應作為本 slice 的 mutation proof 納入。

本文件不得宣稱：

- 已新增或修復 mutation proof。
- 已執行測試或 runner。
- closeout gate 已受 `PROTECTED` 保護。
- Phase E enforcement 已完成。
- 任何 runtime、hook、CI、schema、memory 或 governance_tools 行為已改變。
