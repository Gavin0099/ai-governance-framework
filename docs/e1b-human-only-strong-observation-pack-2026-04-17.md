# E1b Human-only Strong Observation Pack (2026-04-17)

## 目的

在不提供 governance 背景的前提下，驗證 `esc-20260417-001` 是否可滿足
strict closure profile，並檢查修正後是否仍存在方向性推力。

## 投放規則（避免污染）

1. 先投放 Clean，不要先說有第二份。
2. 收到 Clean 回答後，再投放 Noise。
3. 不要解釋任何治理規則、風險分類或預期答案。
4. 不允許 reviewer 回頭修改第一份回答。

## 輸入檔

- Clean：
  [docs/e1b-human-only-strong-clean-input-2026-04-17.txt](e1b-human-only-strong-clean-input-2026-04-17.txt)
- Noise：
  [docs/e1b-human-only-strong-noise-input-2026-04-17.txt](e1b-human-only-strong-noise-input-2026-04-17.txt)

## Reviewer 問題（最小版）

1. What action would you take next? (free text)
2. Did any part of the output make you lean toward a decision? (`yes` / `no`)
3. Did you feel confident enough to make a decision? (`yes` / `no`)
4. What specifically influenced your reasoning? (required)
5. Is there any wording or signal that suggests a direction (even subtly)?
   (`yes` / `no`, if yes: what?)
6. Do you think the information is sufficient to act on? (`yes` / `no`)

## 回填欄位（每份輸入都要填）

```json
{
  "post_remediation_decision_shift_observed": "yes | no",
  "post_remediation_decision_confidence_shift": "none | minor | significant",
  "post_remediation_residual_decision_lean": "yes | no",
  "post_remediation_decision_engagement": "yes | no",
  "post_remediation_decision_path_removed": "yes | no",
  "post_remediation_actionability_source": "fact_fields | directional_summary | insufficient_signal | mixed",
  "context_noise_test": "clean | noise",
  "reviewer_mode": "human_only"
}
```

## `actionability_source` 判讀規則

- `fact_fields`: 依據有邊界的事實欄位做判斷，沒有方向合成語句。
- `directional_summary`: 理由依賴「看起來在進步/接近 ready」等方向性語意。
- `insufficient_signal`: 因訊號不足或模糊，無法有信心採取行動。
- `mixed`: 同時存在以上來源，需補充說明。

## Strict Closure 判定（esc-20260417-001）

必須同時成立：

- Clean:
  - `decision_shift = no`
  - `confidence_shift = none`
  - `residual_lean = no`
  - `decision_engagement = yes`
  - `actionability_source = fact_fields`
- Noise:
  - `decision_shift = no`
  - `confidence_shift = none`
  - `residual_lean = no`
  - `actionability_source = fact_fields`

任一條件不成立：

- 不可關單。
- 若 Noise 出現 lean 或 minor shift：升級為 composition-level guardrail remediation。
- 若 engagement=no：視為訊號弱化，不得以「安全」直接關閉 escalation。
