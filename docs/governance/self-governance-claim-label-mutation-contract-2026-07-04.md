# AI Governance 變異契約：claim-label 自我標記盲點

狀態：`PENDING`
日期：2026-07-04
範圍：report-only `VULNERABLE` baseline；不改 enforcement

## 目的

本文件把 `claim_enforcement_checker` 的 self-labeled claim 盲點固定成可回歸的
`VULNERABLE` baseline。

目前 `claim_enforcement_checker.evaluate` 主要依賴 caller 提供的
`claim_level`、`same_evidence_as_previous`、`posture`、`publication_scope`，
以及兩個 lexical trigger：`proven` 與 `production-ready`。如果一段實質上較強
的宣稱避開這兩個字面詞，並把 `claim_level` 自標為 `bounded`，checker 目前會
回傳 `enforcement_action: allow`。

這不是修復切片。它只把紅隊審計指出的 claim-label 盲點寫成可檢查契約，
避免後續把 lexical/self-label check 說成 semantic-vs-evidence enforcement。

## 對應識別字

- 契約 ID：`self_governance_claim_label`
- 主要治理表面：`governance_tools/claim_enforcement_checker.py`
- 測試檔：`tests/test_self_governance_claim_label_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`VULNERABLE`

## Scenario S1：`Self-Labeled Bounded Claim`

對抗性輸入：

- `final_claim` 使用高於 bounded support 的語意，例如保證跨儲存庫治理決策可靠。
- `claim_level` 自標為 `bounded`。
- `final_claim` 避開 `proven` 與 `production-ready` 兩個 lexical trigger。
- `publication_scope` 設為 `public`，避開 `local_only_claim_level_exceeds_bounded`。

目前觀察：

- `semantic_drift_risk` 回傳 `False`。
- `enforcement_action` 回傳 `allow`。
- `checker_status` 回傳 `pass`。

期望 baseline：

- focused test 應固定目前行為為 `VULNERABLE`。
- 若未來新增 semantic-vs-label 或 evidence-vs-claim 檢查，此測試應失敗，
  要求更新本契約與 catalog 狀態。

## 範圍

本切片只允許：

- 記錄 `claim_enforcement_checker` 的 claim-label 盲點。
- 在 `docs/e1-mutation-catalog.md` 登記 report-only `VULNERABLE` baseline。
- 新增 focused test，證明目前行為仍是已知 vulnerable baseline。

## 非目標

本切片不做：

- 不修改 `governance_tools/**` 行為。
- 不修改 hook、pre-push、CI、schema 或 gate policy。
- 不新增 blocking enforcement。
- 不建立 semantic claim classifier。
- 不驗證 `final_claim` 的實際強度。
- 不驗證 evidence 是否支撐 claim。
- 不修復 memory anchor/evidence truth 盲點；那已由另一份 memory contract 記錄。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_claim_label_mutation_contract.py -q`
- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/self-governance-claim-label-mutation-contract-2026-07-04.md tests/test_self_governance_claim_label_mutation_contract.py`

測試通過的含義：

- claim-label 盲點已被 report-only test 固定。
- 目前行為仍是 `VULNERABLE`。

測試通過不代表：

- claim 語意強度已被驗證。
- evidence-vs-claim 一致性已被驗證。
- `claim_enforcement_checker` 已取得 `PROTECTED`。
- 任何 enforcement、hook、CI 或 gate 行為已改變。

## 宣稱上限

本文件只能宣稱：

- claim-label self-label 盲點已被文件化。
- `Self-Labeled Bounded Claim` 已登記為 report-only `VULNERABLE` baseline。
- focused test 可回歸目前 vulnerable 行為。

本文件不得宣稱：

- 盲點已修復。
- `claim_enforcement_checker` 已能判斷 claim 實際語意強度。
- `claim_enforcement_checker` 已能驗證 evidence 是否支撐 claim。
- Phase E enforcement 完成。
- self-governance claim-label surface 已受 `PROTECTED` 保護。
