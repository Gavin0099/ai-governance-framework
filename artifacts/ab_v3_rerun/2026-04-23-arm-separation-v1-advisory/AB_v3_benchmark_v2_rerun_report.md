# AB v3 Benchmark v2 Rerun Report (Decision Policy v2)

- Date: 2026-04-23
- Scope: decision-policy runtime case pack `separation_v1` (4 cases)
- Enforcement Profile: advisory_mainline
- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)
- Note: exploration anti-collapse constraint enabled for B2/B3 in this experiment.

## Metrics

| Metric | B1 | B2 | B3 |
|---|---:|---:|---:|
| wrong_action_rate | 0.00 | 0.00 | 0.00 |
| false_positive_rate | 0.00 | 0.00 | 0.00 |
| justified_action_rate | 0.50 | 0.50 | 0.50 |
| correct_action_rate | 0.00 | 0.00 | 0.00 |
| epistemic_correctness_rate | 0.50 | 0.50 | 0.50 |
| epistemic_trajectory_rate | 0.50 | 0.50 | 0.50 |
| recovery_accuracy | 1.00 | 1.00 | 1.00 |
| decision_efficiency | 1.50 | 1.50 | 1.50 |
| proceed_with_assumption_rate | 0.00 | 0.00 | 0.00 |
| bounded_execution_capture_rate | 0.00 | 0.00 | 0.00 |
| mean_trial_cost | 0.20 | 0.20 | 0.20 |
| evidence_consistency_rate | 0.75 | 0.75 | 0.75 |
| premise_misclassification_rate | 0.00 | 0.00 | 0.00 |
| strong_evidence_underuse_rate | 0.00 | 0.00 | 0.00 |
| evidence_gate_violation_rate | 0.50 | 0.50 | 0.50 |

- Hard Fail (wrong+proceed): B1=False (count=0), B2=False (count=0), B3=False (count=0)
- Gate Hard Fail (evidence gate): B1=2, B2=2, B3=2

## Arm Separation

- action_separated_cases: 0
- ranking_separated_cases: 0
- action_or_ranking_separated_cases: 0
- stop_rule_pass(min>=2): False
- sep_lowrisk_epistemic_cost_001 (separation+low-risk+high-epistemic-cost): actions B1/B2/B3=reframe/reframe/reframe; top2 B1=['reframe', 'need_more_info'] B2=['reframe', 'need_more_info'] B3=['reframe', 'need_more_info']; action_sep=False ranking_sep=False
- sep_lowrisk_cheap_trial_001 (separation+low-risk+cheap-trial): actions B1/B2/B3=proceed/proceed/proceed; top2 B1=['proceed', 'proceed_with_assumption'] B2=['proceed', 'proceed_with_assumption'] B3=['proceed', 'proceed_with_assumption']; action_sep=False ranking_sep=False
- sep_highrisk_partial_evidence_001 (separation+high-risk+partial-evidence): actions B1/B2/B3=proceed/proceed/proceed; top2 B1=['proceed', 'proceed_with_assumption'] B2=['proceed', 'proceed_with_assumption'] B3=['proceed', 'proceed_with_assumption']; action_sep=False ranking_sep=False
- sep_asserted_conflicting_hint_001 (separation+asserted-root-cause+conflicting-hint): actions B1/B2/B3=reframe/reframe/reframe; top2 B1=['reframe', 'need_more_info'] B2=['reframe', 'need_more_info'] B3=['reframe', 'need_more_info']; action_sep=False ranking_sep=False

## Artifacts

- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-advisory\raw_B1.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-advisory\raw_B2.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-advisory\raw_B3.json`
- Scorecard: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-advisory\scorecard.json`
- Arm Separation: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-advisory\arm_separation.json`
