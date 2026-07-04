# AI Governance 變異契約：normalizer alias-miss 靜默丟欄位盲點

狀態：`PARTIALLY REMEDIATED`
日期：2026-07-04
範圍：report-only advisory 可見性；不改 enforcement、不改 gating

## 目的

本文件把 `runtime_hooks/adapters/shared_normalizer.py` 的 alias-miss 盲點固定成
可回歸的 baseline，並記錄第一個修復切片。

`normalize_payload` 透過固定 alias 清單還原 gate 輸入（`task`、`response_file`、
`checks_file`、`contract`、`risk`、`oversight` 等）。若呼叫方把一個
gate 相關欄位放在 alias 之外的名字（例如 bare `evidence`、`checks`、`proof`、
`attestation`、`risk_score`），該欄位會**靜默變成 absent/default**，下游 gate
從此看不到它——這讀作 **under-enforcement 而非 fail-closed**。

本切片新增一個 **report-only** 偵測 `detect_unmapped_gate_keys`，並把結果掛在
正規化輸出的 `metadata.unmapped_gate_relevant_keys`（advisory list，空 = 乾淨）。
它讓「被靜默丟棄的 gate 相關欄位」變成 reviewer/agent 可見，**不改變 gate 實際
強制什麼**。

## 對應識別字

- 契約 ID：`self_governance_normalizer_alias_miss`
- 主要治理表面：`runtime_hooks/adapters/shared_normalizer.py`
- 測試檔：`tests/test_self_governance_normalizer_alias_miss_mutation_contract.py`
- 目錄登記：`docs/e1-mutation-catalog.md`
- 變異類型：`Negative Fixture`
- 目前狀態：`PARTIALLY REMEDIATED`

## Scenario S1：`Unmapped Gate-Relevant Key`（已修復為 advisory 可見）

對抗性輸入：

- payload 把 gate 相關內容放在 alias 之外的鍵，例如
  `{"evidence": "...", "proof_file": "...", "risk_score": "high"}`。
- 這些鍵不在 `_KNOWN_CONSUMED_KEYS` 內。

目前觀察（修復後）：

- `normalize_payload` 的實際欄位仍不含這些鍵（gating 行為不變）。
- 但 `metadata.unmapped_gate_relevant_keys` 會列出這些被丟棄的 gate 相關鍵，
  讓靜默丟棄變成可見。
- `detect_unmapped_gate_keys(payload)` 可獨立作為 report-only 呼叫。

期望 baseline：

- focused test 應固定 unmapped gate 相關鍵會被 surface。
- 這是 advisory 可見性，不是 enforcement；gate 仍只作用在已對映的欄位上。

## Scenario S2：`Token-Scoped Detection Limit`（仍 VULNERABLE，誠實登記）

對抗性輸入：

- 一個 gate 相關欄位用**不含任何 `_GATE_RELEVANT_TOKENS` 子字串**的鍵名
  （例如自創的隱晦名稱），仍會被靜默丟棄且不被 surface。

目前觀察：

- 偵測是 token-based 結構代理，無法涵蓋任意鍵名。
- 這類鍵仍靜默丟棄且 `unmapped_gate_relevant_keys` 不列出。

期望 baseline：

- focused test 應固定此漏報極限為 `VULNERABLE`。
- 若未來改用「白名單 schema：任何未知鍵都 surface/拒絕」的嚴格模型，此測試應
  失敗，要求更新本契約與 catalog 狀態。

## 範圍

本切片只允許：

- 記錄 `shared_normalizer` 的 alias-miss 盲點。
- 在 `docs/e1-mutation-catalog.md` 登記 S1 修復狀態與 S2 remaining `VULNERABLE`。
- 新增 report-only `detect_unmapped_gate_keys` 與 `metadata` advisory 欄位。
- 新增 focused tests，證明 S1 可見性與 S2 remaining vulnerable 行為。

## 非目標

本切片不做：

- 不改變 `normalize_payload` 已對映欄位的值或 gate 行為。
- 不新增 blocking enforcement，不拒絕任何 payload。
- 不改 hook、pre-push、CI、schema 或 gate policy。
- 不改用嚴格白名單 schema（任何未知鍵 fail-closed）；那是更大的獨立決策。
- 不擴充 alias 清單本身；surface 未對映鍵，不代表已支援它們。

## 證據計畫

本契約的最小驗證：

- `python -B -m pytest tests/test_self_governance_normalizer_alias_miss_mutation_contract.py -q`
- `python -B -m pytest tests/test_runtime_normalize_event.py tests/test_runtime_adapters.py -q`（回歸）
- `git diff --check`

測試通過的含義：

- unmapped gate 相關鍵會被 report-only surface 到 `metadata`。
- 已對映欄位與 gate 行為無回歸。
- token 涵蓋不到的隱晦鍵名仍被 report-only test 固定為 `VULNERABLE`。

測試通過不代表：

- normalizer 已 fail-closed 於未知鍵。
- 所有 gate 輸入現在都保證被看見。
- 任何 enforcement、hook、CI 或 gate 行為已改變。

## 宣稱上限

本文件只能宣稱：

- normalizer alias-miss 盲點已被文件化。
- unmapped gate 相關鍵已修復為 report-only advisory 可見性。
- token 涵蓋不到的鍵名仍登記為 report-only `VULNERABLE` baseline。
- focused test 可回歸目前行為。

本文件不得宣稱：

- normalizer 已對未知鍵 fail-closed。
- gate 現在保證看見所有輸入。
- self-governance normalizer surface 已受 `PROTECTED` 保護。
- Phase E enforcement 完成。
