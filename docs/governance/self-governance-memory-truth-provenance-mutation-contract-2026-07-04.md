# AI Governance 變異契約：記憶 truth/provenance 盲點

狀態：`PENDING`
日期：2026-07-04
範圍：report-only `VULNERABLE` baseline；不改 enforcement

## 目的

本文件把記憶治理表面上的兩個 truth/provenance 盲點固定成可回歸的
`VULNERABLE` baseline：

- `Fabricated Anchor`：記憶 entry 只要包含看似合法的 `commit` hash 或
  `session_id`，`memory_authority_guard` 目前會視為已綁定。
- `Unverified Test Evidence`：`test_evidence` 是自由文字，guard 目前不驗證
  測試是否真的執行或是否有可追溯執行紀錄。

這不是修復切片。它只把紅隊審計指出的盲點寫成可檢查的契約，避免後續把
presence/format check 說成 truth/provenance enforcement。

## 對應識別字

- 契約 ID：`self_governance_memory_truth_provenance`
- 主要治理表面：`governance_tools/memory_authority_guard.py`
- 測試檔：`tests/test_self_governance_memory_truth_provenance_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`VULNERABLE`

## Scenario S1：`Fabricated Anchor`

對抗性輸入：

- 記憶 entry 包含 `commit: deadbee` 或其他 5–40 位十六進位字串。
- 記憶 entry 包含任意非空白 `session_id`。

目前觀察：

- `_entry_is_bound` 回傳 `(True, "ok")`。
- 不執行 `git cat-file` 或 session existence 檢查。

期望 baseline：

- focused test 應固定目前行為為 `VULNERABLE`。
- 若未來新增 provenance 檢查，此測試應失敗，要求更新本契約與 catalog 狀態。

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
- 在 `docs/e1-mutation-catalog.md` 登記 report-only `VULNERABLE` baseline。
- 新增 focused tests，證明目前行為仍是已知 vulnerable baseline。

## 非目標

本切片不做：

- 不修改 `governance_tools/**` 行為。
- 不修改 hook、pre-push、CI、schema 或 gate policy。
- 不新增 blocking enforcement。
- 不驗證 `test_evidence` 的真偽。
- 不驗證 `session_id` 是否存在。
- 不驗證 `commit` hash 是否存在於 git object database。
- 不處理 `claim_enforcement_checker` 的 self-labeled claim 盲點；那是另一個表面。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_memory_truth_provenance_mutation_contract.py -q`
- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md tests/test_self_governance_memory_truth_provenance_mutation_contract.py`

測試通過的含義：

- 目前盲點已被 report-only test 固定。
- 目前行為仍是 `VULNERABLE`。

測試通過不代表：

- provenance 已驗證。
- evidence truth 已驗證。
- 記憶治理表面已取得 `PROTECTED`。
- 任何 enforcement、hook、CI 或 gate 行為已改變。

## 宣稱上限

本文件只能宣稱：

- 記憶 anchor/evidence truth 盲點已被文件化。
- 兩個 memory-focused scenario 已登記為 report-only `VULNERABLE` baseline。
- focused tests 可回歸目前 vulnerable 行為。

本文件不得宣稱：

- 盲點已修復。
- `memory_authority_guard` 已能驗證 anchor provenance。
- `memory_authority_guard` 已能驗證 `test_evidence` 真偽。
- Phase E enforcement 完成。
- self-governance truth/provenance surface 已受 `PROTECTED` 保護。
