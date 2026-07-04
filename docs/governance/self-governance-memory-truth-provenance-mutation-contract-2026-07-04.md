# AI Governance 變異契約：記憶 truth/provenance 盲點

狀態：`PARTIALLY REMEDIATED`
日期：2026-07-04
範圍：report-only baseline + anchor/evidence provenance remediation；不改 enforcement

## 目的

本文件把記憶治理表面上的 truth/provenance 盲點固定成可回歸的 baseline，
並記錄第一個修復切片：

- `Fabricated Commit Anchor`：已修復。當 `project_root` 是 git worktree 時，
  記憶 entry 的 `commit` / `commit_hash` 必須 resolve 成 git commit object
  才能作為 bound anchor。
- `Fabricated Session Anchor`：已修復。任意非空白 `session_id` 不再能單獨作為
  fallback binding；必須對到既有 runtime artifact provenance。
- `Unverified Test Evidence`：已部分修復。成功型 `test_evidence` 需要指向
  存在的 artifact path；guard 仍不重新執行測試，也不驗證 artifact 內容真偽。
- `Canonical Writer Bypass`：已部分修復。active-window 內，若 entry 使用
  非 `session-derived` 的 `memory_type`，但同時帶有 session memory 欄位，
  guard 會產生 report-only warning。

這不是 enforcement 升級。它把紅隊審計指出的盲點寫成可檢查的契約，並修復
memory anchor provenance、evidence artifact provenance、以及 session-shaped
memory type bypass 表面，避免後續把 remaining presence/format check 說成
完整 truth/provenance enforcement。

## 對應識別字

- 契約 ID：`self_governance_memory_truth_provenance`
- 主要治理表面：`governance_tools/memory_authority_guard.py`
- 測試檔：`tests/test_self_governance_memory_truth_provenance_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`PARTIALLY REMEDIATED`

## Scenario S1a：`Fabricated Commit Anchor`

對抗性輸入：

- 記憶 entry 包含 `commit: deadbee` 或其他 5–40 位十六進位字串。

目前觀察：

- 當呼叫方提供的 `project_root` 是 git worktree 時，`_entry_is_bound`
  會用 `git cat-file -e <hash>^{commit}` 驗證 commit object。
- fabricated commit hash 會回傳
  `(False, "commit_hash_not_found_no_session_id")`。
- 真實可 resolve 的 commit hash 仍回傳 `(True, "ok")`。

期望 baseline：

- focused test 應固定 fabricated commit hash 不再算 bound。
- 這個修復仍是 report-only guard 行為，不是 blocking enforcement。

## Scenario S1b：`Fabricated Session Anchor`

對抗性輸入：

- 記憶 entry 包含任意非空白 `session_id`。

目前觀察：

- 沒有 runtime artifact provenance 的任意 `session_id` 會回傳
  `(False, "session_id_provenance_not_found")`。
- 對到 canonical closeout、runtime verdict、或 claim-enforcement packet 的
  `session_id` 仍回傳 `(True, "ok")`。

期望 baseline：

- focused test 應固定 fabricated session_id 不再算 bound。
- 這個修復仍是 report-only guard 行為，不是 blocking enforcement。

## Scenario S2：`Unverified Test Evidence`

對抗性輸入：

- canonical-looking memory entry 宣稱 `test_evidence: PASS: 38 passed`。
- 測試執行紀錄不存在，且沒有任何既有 evidence artifact 被引用。

目前觀察：

- `run_guard` 會產生 `test_evidence_provenance_not_found` warning。
- 引用存在的 `artifacts/...` 路徑時，不產生該 warning。
- `ok` 仍為 `True`；此檢查維持 Phase 1 report-only。

期望 baseline：

- focused test 應固定無 artifact 的成功宣稱會 report warning。
- focused test 應固定 artifact-backed 成功宣稱不會被誤報。
- 若未來新增 evidence semantic truth 檢查，此契約與 catalog 狀態必須更新。

## Scenario S3：`Canonical Writer Bypass Via Non-Session Memory Type`

對抗性輸入：

- active-window daily memory entry 使用 `memory_type: note`。
- entry 同時包含 session memory 欄位，例如 `record_format_version`、`writer`、
  `commit`、`memory_binding`、`test_evidence`、`next_step`。

目前觀察：

- `run_guard` 會產生 `session_like_non_session_memory_type` warning。
- 該 warning 會出現在 `memory_workflow --run-guard` summary / warnings。
- `ok` 仍為 `True`；此檢查不進 `active_non_canonical_writer` blocker。

期望 baseline：

- focused test 應固定 session-shaped `memory_type: note` 會 report warning。
- 純粹的 `human-note` entry 不應被誤報。
- active-window 之前的歷史 typed memory entries 保持 grandfathered，避免把
  歷史 taxonomy 債誤報成當前 bypass。

## 範圍

本切片只允許：

- 記錄 `memory_authority_guard` 的 truth/provenance 盲點。
- 在 `docs/e1-mutation-catalog.md` 登記 commit-anchor 修復狀態與 remaining
  report-only `VULNERABLE` baselines。
- 新增 focused tests，證明 anchor provenance 修復與 remaining vulnerable 行為。
- 修復 git worktree 內 `commit` / `commit_hash` anchor 的 git object
  provenance 檢查。
- 修復 `session_id` fallback，使其必須對到既有 runtime artifact provenance。
- 修復成功型 `test_evidence` 的 artifact provenance warning。
- 讓 `memory_workflow --run-guard` 摘要該 report-only warning，但不把它升級為
  blocker。
- 修復 active-window 內 session-shaped non-session `memory_type` 的 report-only
  bypass warning，並讓 `memory_workflow --run-guard` 摘要該 warning。

## 非目標

本切片不做：

- 不修改 hook、pre-push、CI、schema 或 gate policy。
- 不新增 blocking enforcement。
- 不把 `session_like_non_session_memory_type` 納入 `active_non_canonical_writer`
  blocker。
- 不重新執行測試，且不驗證 `test_evidence` 或 artifact 內容的語義真偽。
- 不處理 `claim_enforcement_checker` 的 self-labeled claim 盲點；那是另一個表面。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_memory_truth_provenance_mutation_contract.py -q`
- `python -B -m pytest tests/test_memory_workflow.py -q`
- `python -B -m pytest tests/test_memory_authority_guard.py -q`
- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md governance_tools/memory_authority_guard.py governance_tools/memory_workflow.py tests/test_memory_authority_guard.py tests/test_memory_workflow.py tests/test_self_governance_memory_truth_provenance_mutation_contract.py`

測試通過的含義：

- fabricated commit hash 在 git worktree 中不再算 bound anchor。
- fabricated session_id 不再算 bound anchor；provenance-backed session_id 仍可
  作為 fallback binding。
- 成功型 `test_evidence` 若沒有既有 artifact provenance，會產生
  `test_evidence_provenance_not_found` report-only warning。
- artifact-backed 成功型 `test_evidence` 不會產生該 warning。
- session-shaped `memory_type: note` 在 active window 內會產生
  `session_like_non_session_memory_type` report-only warning。
- 純 `human-note` 不會因 memory type 本身被誤報。

測試通過不代表：

- evidence truth 已驗證。
- 記憶治理表面已取得 `PROTECTED`。
- 任何 enforcement、hook、CI 或 gate 行為已改變。

## 宣稱上限

本文件只能宣稱：

- 記憶 anchor/evidence truth 盲點已被文件化。
- commit-anchor fabricated hash 盲點已在 git worktree 內修復為 report-only
  provenance 檢查。
- session-anchor fabricated token 盲點已修復為 report-only artifact provenance
  檢查。
- evidence artifact provenance 盲點已修復為 report-only warning baseline。
- canonical writer bypass via non-session `memory_type` 已修復為 active-window
  report-only warning baseline。
- focused tests 可回歸目前行為。

本文件不得宣稱：

- 所有盲點已修復。
- `memory_authority_guard` 已能驗證 `test_evidence` 真偽。
- Phase E enforcement 完成。
- self-governance truth/provenance surface 已受 `PROTECTED` 保護。
