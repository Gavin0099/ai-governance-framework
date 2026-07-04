# AI Governance 變異契約：claim-label 自我標記盲點

狀態：`PARTIALLY REMEDIATED`
日期：2026-07-04
範圍：report-only advisory 偵測；不改 enforcement、不新增 blocking

## 目的

本文件把 `claim_enforcement_checker` 的 self-labeled claim 盲點固定成可回歸的
baseline，並記錄第一個修復切片。

修復前，`claim_enforcement_checker.evaluate` 主要依賴 caller 提供的
`claim_level`、`same_evidence_as_previous`、`posture`、`publication_scope`，
以及兩個 lexical trigger：`proven` 與 `production-ready`。一段實質上較強的宣稱
只要避開這兩個字面詞，並把 `claim_level` 自標為 `bounded`，checker 會回傳
`enforcement_action: allow`。

本切片新增一個 **結構代理（lexical）** 偵測：當 `claim_level` 是受限等級
（`bounded` / `parity`）但宣稱文字含絕對／全稱強度標記時，標記
`claim_label_understates_claim_text`，並走 checker **既有** 的 `downgrade`
advisory 路徑（`reviewer_override_required: true`）。

這不是 enforcement 升級，也不是語義驗證。它讓「自標受限、實則強宣稱」這個
mutation 從無聲放行變成 reviewer 可見，避免把自填 claim label 當成語義上受限的
事實。

## 對應識別字

- 契約 ID：`self_governance_claim_label`
- 主要治理表面：`governance_tools/claim_enforcement_checker.py`
- 測試檔：`tests/test_self_governance_claim_label_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`PARTIALLY REMEDIATED`

## Scenario S1：`Self-Labeled Bounded Claim`（已修復為 advisory）

對抗性輸入：

- `final_claim` 使用高於 bounded support 的語意，含絕對／全稱強度標記
  （例如 `guarantee`、`completely safe`、`all inputs`）。
- `claim_level` 自標為 `bounded`（或 `parity`）。
- `final_claim` 避開 `proven` 與 `production-ready` 兩個 lexical trigger。
- `publication_scope` 設為 `public`，避開 `local_only_claim_level_exceeds_bounded`。

目前觀察（修復後）：

- `evaluate` 對受限等級掃描 `CLAIM_STRENGTH_MARKERS`。
- 命中時回傳 `semantic_drift_risk: true`、`enforcement_action: downgrade`、
  `reviewer_override_required: true`、`reasons` 含
  `claim_label_understates_claim_text`。
- 修復前同一 payload 回傳 `enforcement_action: allow`、`semantic_drift_risk:
  false`。

期望 baseline：

- focused test 應固定「自標受限 + 強度標記文字」不再無聲放行。
- 這個修復仍是 advisory（downgrade + reviewer override），不是 blocking
  enforcement。

## Scenario S2：`Markerless Strong Claim`（仍 VULNERABLE，誠實登記）

對抗性輸入：

- 語義上強、但不含任何 `CLAIM_STRENGTH_MARKERS` 詞的宣稱，自標 `bounded`。

目前觀察：

- 結構代理無法偵測，仍回傳 `enforcement_action: allow`、`semantic_drift_risk:
  false`。

期望 baseline：

- focused test 應固定此行為為 `VULNERABLE`，明確記錄本代理的漏報極限。
- 若未來新增真正的 semantic-vs-label 或 evidence-vs-claim 判斷，此測試應失敗，
  要求更新本契約與 catalog 狀態。

## 範圍

本切片只允許：

- 記錄 `claim_enforcement_checker` 的 claim-label 盲點。
- 在 `docs/e1-mutation-catalog.md` 登記 S1 修復狀態與 S2 remaining `VULNERABLE`
  baseline。
- 新增 lexical `CLAIM_STRENGTH_MARKERS` 偵測，透過既有 `downgrade` advisory
  路徑輸出。
- 新增 focused tests，證明 S1 修復與 S2 remaining vulnerable 行為。

## 非目標

本切片不做：

- 不修改 hook、pre-push、CI、schema 或 gate policy。
- 不新增 blocking enforcement（不把任何先前 `allow` 升級成 `block`）。
- 不建立 semantic claim classifier；`CLAIM_STRENGTH_MARKERS` 是 lexical proxy。
- 不驗證 `final_claim` 的實際語意強度或 evidence 是否支撐 claim。
- 不修復 memory anchor/evidence truth 盲點；那已由另一份 memory contract 記錄。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_claim_label_mutation_contract.py -q`
- `python -B -m pytest tests/test_claim_enforcement_checker.py -q`（回歸）
- `git diff --check -- docs/e1-mutation-catalog.md docs/governance/self-governance-claim-label-mutation-contract-2026-07-04.md tests/test_self_governance_claim_label_mutation_contract.py governance_tools/claim_enforcement_checker.py`

測試通過的含義：

- 自標受限 + 強度標記文字不再無聲放行，改為 advisory downgrade + reviewer
  override。
- markerless 強宣稱仍被 report-only test 固定為 `VULNERABLE`。
- 既有 3 個 checker 測試無回歸。

測試通過不代表：

- claim 語意強度已被真正驗證。
- evidence-vs-claim 一致性已被驗證。
- markerless 強宣稱盲點已修復。
- 任何 enforcement、hook、CI 或 gate 行為已改變。

## 宣稱上限

本文件只能宣稱：

- claim-label self-label 盲點已被文件化。
- `Self-Labeled Bounded Claim` 已修復為 report-only advisory 偵測（lexical
  proxy）。
- `Markerless Strong Claim` 仍登記為 report-only `VULNERABLE` baseline。
- focused test 可回歸目前行為。

本文件不得宣稱：

- 所有 claim-label 盲點已修復。
- `claim_enforcement_checker` 已能判斷 claim 實際語意強度。
- `claim_enforcement_checker` 已能驗證 evidence 是否支撐 claim。
- self-labeled `claim_level` 現在等於語義上受限。
- Phase E enforcement 完成或 self-governance claim-label surface 已受
  `PROTECTED` 保護。
