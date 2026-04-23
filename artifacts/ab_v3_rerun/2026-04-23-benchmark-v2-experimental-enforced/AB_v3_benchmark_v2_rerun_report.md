# AB v3 Benchmark v2 Rerun Report (Decision Policy v2)

- Date: 2026-04-23
- Scope: decision-policy runtime with benchmark v2 gradient case pack (18 cases)
- Enforcement Profile: experimental_enforced
- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)
- Note: exploration anti-collapse constraint enabled for B2/B3 in this experiment.

## Metrics

| Metric | B1 | B2 | B3 |
|---|---:|---:|---:|
| wrong_action_rate | 0.00 | 0.00 | 0.00 |
| false_positive_rate | 0.00 | 0.00 | 0.00 |
| justified_action_rate | 0.94 | 0.94 | 0.94 |
| correct_action_rate | 0.33 | 0.33 | 0.33 |
| epistemic_correctness_rate | 0.94 | 0.94 | 0.94 |
| epistemic_trajectory_rate | 0.56 | 0.56 | 0.56 |
| recovery_accuracy | 0.90 | 0.90 | 0.90 |
| decision_efficiency | 1.56 | 1.56 | 1.56 |
| proceed_with_assumption_rate | 0.22 | 0.22 | 0.22 |
| bounded_execution_capture_rate | 1.00 | 1.00 | 1.00 |
| mean_trial_cost | 0.23 | 0.23 | 0.23 |
| evidence_consistency_rate | 0.56 | 0.56 | 0.56 |
| premise_misclassification_rate | 0.00 | 0.00 | 0.00 |
| strong_evidence_underuse_rate | 0.00 | 0.00 | 0.00 |
| evidence_gate_violation_rate | 0.28 | 0.28 | 0.28 |

- Hard Fail (wrong+proceed): B1=False (count=0), B2=False (count=0), B3=False (count=0)
- Gate Hard Fail (evidence gate): B1=5, B2=5, B3=5

## Artifacts

- Raw: `artifacts\ab_v3_rerun\2026-04-23-benchmark-v2-experimental-enforced\raw_B1.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-benchmark-v2-experimental-enforced\raw_B2.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-benchmark-v2-experimental-enforced\raw_B3.json`
- Scorecard: `artifacts\ab_v3_rerun\2026-04-23-benchmark-v2-experimental-enforced\scorecard.json`
