# E1b Round 3 Cognitive Leakage Evaluation Template

Use this after receiving reviewer answers for clean/noise observations.

## Inputs

- reviewer_q1_action
- reviewer_q4_reasoning (required)
- reviewer_q2_lean (`yes`/`no`)
- reviewer_q3_engagement (`yes`/`no`)
- reviewer_q5_direction_signal (`yes`/`no`)
- reviewer_q6_sufficient_to_act (`yes`/`no`)

## Step 1: Detect implicit synthesis from free text

Set:
- `free_text_synthesis=yes` if Q1/Q4 contains directional impressions not
  derivable from bounded facts (e.g., "looks better", "seems stable",
  "appears improving", "close to ready").
- `free_text_synthesis_trigger` = exact phrase(s).

Else:
- `free_text_synthesis=no`
- `free_text_synthesis_trigger=n/a`

## Step 2: Apply override (mandatory)

If `free_text_synthesis=yes`:
- `post_remediation_decision_path_removed=no`
- `post_remediation_actionability_source` must not be `fact_fields`
- classify as directional leakage even if structured yes/no fields look safe

## Step 3: Fill structured fields

```json
{
  "post_remediation_decision_shift_observed": "yes | no",
  "post_remediation_decision_confidence_shift": "none | minor | significant",
  "post_remediation_residual_decision_lean": "yes | no",
  "post_remediation_decision_engagement": "yes | no",
  "post_remediation_actionability_source": "fact_fields | directional_summary | insufficient_signal | mixed",
  "post_remediation_free_text_synthesis": "yes | no",
  "post_remediation_free_text_synthesis_trigger": "string",
  "post_remediation_decision_path_removed": "yes | no"
}
```

## Step 4: Decision

- **Close allowed** only if:
  - clean and noise both have `free_text_synthesis=no`
  - `residual_lean=no`
  - `decision_confidence_shift=none`
  - `decision_engagement=yes` (clean)
  - `actionability_source=fact_fields`
- Otherwise:
  - keep escalation open
  - if leakage reappears in noise, escalate to presentation composition redesign
