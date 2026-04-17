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

### Cross-field synthesis disqualification rule

**若 reviewer 的自由文字理由包含跨欄位抽象總結，則不得判為 `fact_fields`。**

以下語句不論 reviewer 如何自填結構欄位，皆應升格為 `directional_summary` 或 `mixed`：

| 語句類型 | 範例 | 應判為 |
|----------|------|--------|
| 跨欄位合成趨勢 | 「最近測試提升、建置穩定，所以傾向往前」 | `directional_summary` |
| 方向性整合 | 「整體顯示正向改善」 | `directional_summary` |
| 軟 readiness 推論 | 「雖然還在 transitioning，但整體往正向發展」 | `directional_summary` |
| 跨欄位合成但有保留 | 「測試提升算是正向，不過我沒有完全確定」 | `mixed` |

**判讀原則**：表面來源是 fact fields，但認知路徑已做方向合成 → 不算 `fact_fields`。
審查 reviewer 的自由文字理由，不只看 structured 欄位填什麼。

**Free-text overrides structured fields (mechanical rule, not judgment call).**

If conflict exists between free-text and structured fields:
- `actionability_source` MUST be downgraded from `fact_fields`.
- Classification follows free-text interpretation, not structured input.
- No case-by-case discretion: if cross-field synthesis appears in free-text,
  the override is unconditional.

> Free-text is ground truth. Structured fields are secondary confirmation only.

## Two Failure Modes（必須分開辨識）

回填結果不成立時，先判定是哪一種 failure，再決定下一步：

### Failure A — Directional Reactivation

Noise 下仍出現：
- `residual_lean = yes`
- `confidence_shift = minor` 或 `significant`
- reviewer 自由文字含跨欄位方向合成語句

代表：**composition guardrail 失敗**。guardrail 未能阻止 reviewer 把多欄位拼成 readiness 敘事。

下一步：升級為 **presentation composition redesign**（重新決定哪些欄位可同屏、哪些必須拆開、哪些 summary 句型禁止生成）。

### Failure B — Safe but Unusable

Clean 雖通過安全條件，但：
- `decision_engagement = no`
- `actionability_source = unclear / none / insufficient_signal`
- reviewer 只能選擇 hold，因資訊已碎化至無法判斷

代表：**guardrail 過度抑制**，安全但不可用。

下一步：不得以「安全」直接關閉 escalation。需重新評估呈現密度 — guardrail 不應讓 clean output 失去決策可用性。

**Hard closure prohibition:**
> Closure is invalid if `decision_engagement = no`, even when no decision shift
> or lean is observed.

「沉默成功」（safe + not misleading + reviewer cannot act）不算通過。

---

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
- 若 Noise 出現 lean / shift / reviewer 自由文字含跨欄位合成語句：**Failure A → 升級為 presentation composition redesign**，不再做 wording 微調。
- 若 Clean 的 engagement=no 或 actionability_source=insufficient_signal：**Failure B → 不得以「安全」關閉**。
- 若兩者均未成立但理由不確定：回填 `mixed` 並附說明，交人工裁決。

### Interpretation order (mandatory sequence)

**判讀必須依以下順序，不允許顛倒：**

1. **Free-text reasoning (Q1, Q4)** — primary signal
   Read first. Identify any cross-field synthesis or directional language.

2. **Cross-field synthesis detection** — override layer
   If synthesis found: unconditionally override structured fields.
   `actionability_source` is downgraded; no discretion.

3. **Structured fields** — secondary confirmation only
   Valid only if consistent with free-text interpretation.
   Structured fields must not be used to contradict a validated free-text
   interpretation.

> Decision safety is evaluated based on human reasoning traces (free-text),
> not on structured outputs alone. Structured fields are considered valid
> only if consistent with free-text reasoning and free from cross-field synthesis.

### Free-text audit requirement

**回填 `actionability_source` 前，必須先審 reviewer 的第 Q1 和 Q4 自由文字。**

不能只看 structured 欄位。Q1（free text）和 Q4（reasoning）的語句若含跨欄位抽象合成，
依 Cross-field synthesis disqualification rule 升格，structured 欄位填什麼不影響這個判定。

---

### Final closure condition

**Closure is valid only if ALL of the following hold:**

1. Free-text (Q1, Q4) shows no directional synthesis or cross-field abstraction.
2. `decision_engagement = yes` (both clean and noise).
3. No `residual_lean` under both clean and noise contexts.
4. Structured fields are consistent with free-text interpretation (no override triggered).

Any single condition failing → closure invalid. No exceptions.
