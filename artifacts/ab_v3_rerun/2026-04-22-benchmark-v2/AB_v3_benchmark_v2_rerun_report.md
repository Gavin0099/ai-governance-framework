# AB v3 Benchmark v2 Rerun Report

- Date: 2026-04-22
- Scope: decision_policy_v1 with benchmark v2 gradient case pack (12 cases)
- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)

## Metrics

| Metric | B1 | B2 | B3 |
|---|---:|---:|---:|
| wrong_action_rate | 0.00 | 0.00 | 0.00 |
| false_positive_rate | 0.50 | 0.50 | 0.67 |
| justified_action_rate | 0.50 | 0.50 | 0.33 |
| recovery_accuracy | 0.50 | 0.50 | 0.33 |
| decision_efficiency | 2.00 | 2.00 | 2.00 |
| proceed_with_assumption_rate | 0.00 | 0.00 | 0.00 |

## Short Read

- Compare B2/B3 against B1 on recovery/justified metrics.
- Check if high-risk+strong-evidence cases avoid unnecessary deferral.
- Check if proceed_with_assumption appears as a usable middle state.

## Artifacts

- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2\raw_B1.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2\raw_B2.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2\raw_B3.json`
- Scorecard: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2\scorecard.json`
