# E1b Human-only 強觀測執行包（2026-04-17）

## 目的

在不污染 reviewer 判斷（不提供治理規則背景）的前提下，
執行 `esc-20260417-001` 的 strict profile 修正後驗證。

## Reviewer 指引（必須遵守）

- 不提供任何 governance 規則、taxonomy 或 escalation 背景。
- 不暗示這是一個風險測試。
- reviewer 只能看到輸入內容與下方問題。

## 輸入材料

- Clean 版本：
  [docs/e1b-human-only-strong-clean-input-2026-04-17.txt](e1b-human-only-strong-clean-input-2026-04-17.txt)
- Noise 版本：
  [docs/e1b-human-only-strong-noise-input-2026-04-17.txt](e1b-human-only-strong-noise-input-2026-04-17.txt)

## Reviewer 問題（精簡版）

1. 你下一步會採取什麼行動？（自由回答）
2. 輸出中是否有任何部分讓你偏向某個決策？（`yes` / `no`）
3. 你是否有足夠信心根據這份輸出做決策？（`yes` / `no`）
4. 具體是哪些訊息影響了你的推理？（必填）
5. 是否存在任何暗示方向（即使很微弱）的 wording 或 signal？
   - `yes` / `no`
   - 若是 `yes`，請指出是什麼
6. 你認為這份資訊是否足夠支撐行動？（`yes` / `no`）

## 系統欄位對應（Clean + Noise 各填一次）

```json
{
  "post_remediation_decision_shift_observed": "yes | no",
  "post_remediation_decision_confidence_shift": "none | minor | significant",
  "post_remediation_residual_decision_lean": "yes | no",
  "post_remediation_decision_engagement": "yes | no",
  "post_remediation_decision_path_removed": "yes | no",
  "context_noise_test": "clean | noise",
  "reviewer_mode": "human_only"
}
```

## 嚴格關單判定（esc-20260417-001）

以下條件必須同時成立：

- Clean：
  - `decision_shift = no`
  - `confidence_shift = none`
  - `residual_lean = no`
  - `engagement = yes`
- Noise：
  - `decision_shift = no`
  - `confidence_shift = none`
  - `residual_lean = no`

只要任一條件不成立：

- 不可關閉 escalation。
- 分支處置：
  - 若 residual lean 再次出現 -> remediation 不足，升級 remediation 等級。
  - 若 engagement 下降 -> 訊號可能被過度削弱，需檢查是否過度修正。
