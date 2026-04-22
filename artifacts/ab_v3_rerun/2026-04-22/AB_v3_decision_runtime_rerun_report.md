# AB v3 Decision Runtime Rerun Report

- Date: 2026-04-22
- Scope: pre_task_check decision_policy_v1 rerun on 6 benchmark cases (wrong x4, valid x2)
- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + feedback)

## Metrics

| Metric | B1 | B2 | B3 |
|---|---:|---:|---:|
| wrong_action_rate | 0.17 | 0.17 | 0.17 |
| false_positive_rate | 0.17 | 0.17 | 0.17 |
| justified_action_rate | 0.67 | 0.67 | 0.67 |
| recovery_accuracy | 0.67 | 0.75 | 0.75 |
| decision_efficiency | 2.00 | 1.67 | 1.67 |

## Interpretation

- B1 shows baseline behavior with limited explicit assumption handling.
- B2 increases caution under uncertainty but may increase unnecessary deferral.
- B3 uses follow-up evidence to recover utility while keeping wrong actions low.

## Artifacts

- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22\raw_B1.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22\raw_B2.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22\raw_B3.json`
- Scorecard: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22\scorecard.json`
