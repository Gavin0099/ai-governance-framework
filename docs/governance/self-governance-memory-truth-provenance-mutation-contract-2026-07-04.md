# AI Governance 變異契約：記憶 truth/provenance 盲點

狀態：`PARTIALLY REMEDIATED`
日期：2026-07-04
範圍：report-only baseline + anchor provenance remediation；不改 enforcement

## 目的

本文件把記憶治理表面上的 truth/provenance 盲點固定成可回歸的 baseline，
並記錄第一個修復切片：

- `Fabricated Commit Anchor`：已修復。當 `project_root` 是 git worktree 時，
  記憶 entry 的 `commit` / `commit_hash` 必須 resolve 成 git commit object
  才能作為 bound anchor。
- `Fabricated Session Anchor`：已修復。任意非空白 `session_id` 不再能單獨作為
  fallback binding；必須對到既有 runtime artifact provenance。
- `Unverified Test Evidence`：`test_evidence` 是自由文字，guard 目前不驗證
  測試是否真的執行或是否有可追溯執行紀錄。

這不是 enforcement 升級。它把紅隊審計指出的盲點寫成可檢查的契約，並修復
memory anchor provenance 表面，避免後續把 remaining presence/format check
說成完整 truth/provenance enforcement。

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
- 測試執行紀錄不存在，且沒有任何外部 evidence artifact 被引用。

目前觀察：

- `run_guard` 不產生 evidence-truth 類違規碼。
- `violation_counts_by_code` 可維持空集合，`ok` 仍為 `True`。

期望 baseline：

- focused test 應固定目前行為為 `VULNERABLE`。
- 若未來新增 evidence-truth 檢查，此測試應失敗，要求更新本契約與 catalog 狀態。

## 範圍

本切片只允許：

- 記錄 `memory_authority_guard` 的 truth/provenance 盲點。
- 在 `docs/e1-mutation-catalog.md` 登記 commit-anchor 修復狀態與 remaining
  report-only `VULNERABLE` baselines。
- 新增 focused tests，證明 anchor provenance 修復與 remaining vulnerable 行為。
- 修復 git worktree 內 `commit` / `commit_hash` anchor 的 git object
  provenance 檢查。
- 修復 `session_id` fallback，使其必須對到既有 runtime artifact provenance。

## 非目標

本切片不做：

- 不修改 hook、pre-push、CI、schema 或 gate policy。
- 不新增 blocking enforcement。
- 不驗證 `test_evidence` 的真偽。
- 不處理 `claim_enforcement_checker` 的 self-labeled claim 盲點；那是另一個表面。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_memory_truth_provenance_mutation_contract.py -q`
- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md tests/test_self_governance_memory_truth_provenance_mutation_contract.py`

測試通過的含義：

- fabricated commit hash 在 git worktree 中不再算 bound anchor。
- fabricated session_id 不再算 bound anchor；provenance-backed session_id 仍可
  作為 fallback binding。
- free-text `test_evidence` 仍被 report-only test 固定為 `VULNERABLE`。

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
- evidence-truth scenario 仍登記為 report-only `VULNERABLE` baseline。
- focused tests 可回歸目前行為。

本文件不得宣稱：

- 所有盲點已修復。
- `memory_authority_guard` 已能驗證 `test_evidence` 真偽。
- Phase E enforcement 完成。
- self-governance truth/provenance surface 已受 `PROTECTED` 保護。
