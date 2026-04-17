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

---

## 第二輪判讀工作表

> 每份輸入（Clean / Noise）各填一份。依步驟順序填，不允許跳步。
> 未完成第一步前，不得看第三步。

### 第一步 — 自由文字主判讀（Q1 / Q4）

逐字掃描 Q1 和 Q4，看是否出現以下任一觸發語句（出現一句即算 synthesis）：

- 「整體變好」「整體趨勢向好」
- 「趨於穩定」「越來越穩定」「在穩定中」
- 「接近 ready」「快到了」「快可以 promote」
- 「可以往前」「可以推進」「可以考慮升級」
- 任何把兩個以上不同欄位的訊號合成為方向性判斷的語句

```
free_text_synthesis:    yes | no
trigger_phrase_found:   （原文引用，或填「無」）
```

**若 `free_text_synthesis = yes` → 停止，直接記錄 Failure A，不繼續填後面步驟。**

---

### 第二步 — 跨欄位覆蓋（第一步為 yes 時無條件執行）

只有 `free_text_synthesis = yes` 時才填此步驟：

```
residual_decision_lean:    yes          # 強制覆蓋
actionability_source:      composed_inference  # 強制覆蓋
decision_path_removed:     no           # 強制覆蓋
```

以上三欄由第一步結果決定，不受第三步 structured 欄位影響。

---

### 第三步 — 結構欄位（僅確認用）

從 Q2 / Q3 / Q5 / Q6 填入。**只有第一步 `free_text_synthesis = no` 時才有效。**

```
decision_shift_observed:       yes | no
decision_confidence_shift:     none | minor | significant
decision_engagement:           yes | no
residual_decision_lean:        yes | no
```

第三步結果不得用來推翻第一步或第二步的結論。

---

### 第四步 — Actionability source 判定

若 `free_text_synthesis = no` 且 reviewer 的理由只引用單一有邊界的事實欄位：

```
actionability_source:  fact_fields
```

其他情況（`free_text_synthesis = yes`、Q4 有合成語句、多欄位合併判斷）：

```
actionability_source:  directional_summary | composed_inference | mixed
```

---

### Failure 判定（機械式）

**Failure A — 方向性重激活**（任一條件成立即觸發）：
- `free_text_synthesis = yes`
- 或（僅 Noise）：`residual_decision_lean = yes`
- 或（僅 Noise）：`decision_confidence_shift ∈ {minor, significant}`

→ 結論：composition guardrail 失敗。**直接升級為 presentation architecture redesign。**
   不再進行 wording 調整。

**Failure B — 安全但不可用**（兩項同時成立）：
- `decision_engagement = no`
- 且 無 decision shift 也無 lean

→ 結論：guardrail 過度抑制。**不得以「安全」關閉 escalation。**

---

### 決策軌跡範本

**`classification_rationale`**（回填時附加）：
```
自由文字無跨欄位合成；structured 欄位與自由文字判讀一致，未引入方向性推論。
```

**`closure_rationale`**（僅當四條 Final Closure Conditions 全部成立時使用）：
```
Clean 與 Noise 均無殘餘決策路徑；decision engagement 保留；
actionability 來源確認為 fact_fields。
```

---

### 提交前快速檢查（不可跳過）

- [ ] 自由文字中有任何「整體趨勢」語句 → 一律當 synthesis，不論語氣軟硬
- [ ] `decision_engagement = no` → 一律不可關單，即使其他欄位全部通過
