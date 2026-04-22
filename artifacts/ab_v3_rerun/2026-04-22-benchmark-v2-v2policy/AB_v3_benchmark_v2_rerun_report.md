# AB v3 Benchmark v2 Rerun Report (Decision Policy v2)

- Date: 2026-04-22
- Scope: decision-policy runtime with benchmark v2 gradient case pack (12 cases)
- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)
- Note: exploration anti-collapse constraint enabled for B2/B3 in this experiment.

## Metrics

| Metric | B1 | B2 | B3 |
|---|---:|---:|---:|
| wrong_action_rate | 0.00 | 0.00 | 0.00 |
| false_positive_rate | 0.17 | 0.17 | 0.17 |
| justified_action_rate | 0.83 | 0.83 | 0.83 |
| recovery_accuracy | 0.67 | 0.67 | 0.67 |
| decision_efficiency | 1.50 | 1.50 | 1.50 |
| proceed_with_assumption_rate | 0.50 | 0.50 | 0.50 |

## Artifacts

- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2-v2policy\raw_B1.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2-v2policy\raw_B2.json`
- Raw: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2-v2policy\raw_B3.json`
- Scorecard: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\ab_v3_rerun\2026-04-22-benchmark-v2-v2policy\scorecard.json`
