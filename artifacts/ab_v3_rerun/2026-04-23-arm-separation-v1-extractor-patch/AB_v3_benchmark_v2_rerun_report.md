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
| correct_action_rate | 0.00 | 0.25 | 0.25 |
| epistemic_correctness_rate | 0.50 | 0.50 | 0.50 |
| epistemic_trajectory_rate | 0.50 | 1.00 | 1.00 |
| recovery_accuracy | 1.00 | 0.50 | 0.50 |
| decision_efficiency | 1.50 | 2.00 | 2.00 |
| proceed_with_assumption_rate | 0.00 | 0.00 | 0.00 |
| bounded_execution_capture_rate | 0.00 | 0.00 | 0.00 |
| mean_trial_cost | 0.20 | 0.23 | 0.23 |
| evidence_consistency_rate | 0.75 | 0.75 | 0.75 |
| premise_misclassification_rate | 0.00 | 0.00 | 0.00 |
| strong_evidence_underuse_rate | 0.00 | 0.00 | 0.00 |
| evidence_gate_violation_rate | 0.50 | 0.50 | 0.50 |

- Hard Fail (wrong+proceed): B1=False (count=0), B2=False (count=0), B3=False (count=0)
- Gate Hard Fail (evidence gate): B1=2, B2=2, B3=2

## Arm Separation

- action_separated_cases: 1
- ranking_separated_cases: 1
- action_or_ranking_separated_cases: 1
- stop_rule_pass(min>=2): False
- sep_lowrisk_epistemic_cost_001 (separation+low-risk+high-epistemic-cost): actions B1/B2/B3=reframe/need_more_info/need_more_info; top2 B1=['reframe', 'need_more_info'] B2=['need_more_info', 'reframe'] B3=['need_more_info', 'reframe']; action_sep=True ranking_sep=True
- sep_lowrisk_cheap_trial_001 (separation+low-risk+cheap-trial): actions B1/B2/B3=proceed/proceed/proceed; top2 B1=['proceed', 'proceed_with_assumption'] B2=['proceed', 'proceed_with_assumption'] B3=['proceed', 'proceed_with_assumption']; action_sep=False ranking_sep=False
- sep_highrisk_partial_evidence_001 (separation+high-risk+partial-evidence): actions B1/B2/B3=proceed/proceed/proceed; top2 B1=['proceed', 'proceed_with_assumption'] B2=['proceed', 'proceed_with_assumption'] B3=['proceed', 'proceed_with_assumption']; action_sep=False ranking_sep=False
- sep_asserted_conflicting_hint_001 (separation+asserted-root-cause+conflicting-hint): actions B1/B2/B3=reframe/reframe/reframe; top2 B1=['reframe', 'need_more_info'] B2=['reframe', 'need_more_info'] B3=['reframe', 'need_more_info']; action_sep=False ranking_sep=False

## Arm-to-Feature Contract Check

- cases_total_with_expectation: 4
- cases_with_any_expected_feature_separation: 3
- cases_missing_expected_feature_separation: 1
- possible_reason_counts: {'contract_overstates_difference': 0, 'arm_signal_not_machine_consumable': 0, 'extractor_ignores_arm_signal': 1, 'separated': 3}
- sep_lowrisk_epistemic_cost_001 (separation+low-risk+high-epistemic-cost): expected_features=['premise_status', 'evidence_alignment', 'correctness_mode']; has_any_expected_separation=True; possible_reason=separated
- sep_lowrisk_cheap_trial_001 (separation+low-risk+cheap-trial): expected_features=['correctness_mode']; has_any_expected_separation=True; possible_reason=separated
- sep_highrisk_partial_evidence_001 (separation+high-risk+partial-evidence): expected_features=['evidence_alignment', 'correctness_mode']; has_any_expected_separation=True; possible_reason=separated
- sep_asserted_conflicting_hint_001 (separation+asserted-root-cause+conflicting-hint): expected_features=['premise_status', 'correctness_mode']; has_any_expected_separation=False; possible_reason=extractor_ignores_arm_signal

## Arm Signal Visibility Probe

- scope: separation_v1
- path_counts: {'arm_encoding_not_observable_pre_extraction': 0, 'extractor_collapses_visible_arm_signal': 1, 'separated_through_extractor': 3, 'unexpected_post_only_delta': 0}
- closure_recommendation: extractor_patch
- closure_reason: Pre-extraction deltas are visible but collapse before/within phase-A extraction.
- sep_lowrisk_epistemic_cost_001 (separation+low-risk+high-epistemic-cost): pre_delta_any=True post_delta_any=True path=separated_through_extractor
- sep_lowrisk_cheap_trial_001 (separation+low-risk+cheap-trial): pre_delta_any=True post_delta_any=True path=separated_through_extractor
- sep_highrisk_partial_evidence_001 (separation+high-risk+partial-evidence): pre_delta_any=True post_delta_any=True path=separated_through_extractor
- sep_asserted_conflicting_hint_001 (separation+asserted-root-cause+conflicting-hint): pre_delta_any=True post_delta_any=False path=extractor_collapses_visible_arm_signal

## Collapse Locator

- dominant_collapse_type: feature_extraction_collapse
- counts: {'feature_extraction_collapse': 1, 'score_mapping_collapse': 1, 'phase_transition_collapse': 1, 'not_collapsed_or_mixed': 1}

## Artifacts

- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\raw_B1.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\raw_B2.json`
- Raw: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\raw_B3.json`
- Scorecard: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\scorecard.json`
- Arm Separation: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\arm_separation.json`
- Arm Feature Contract Check: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\arm_feature_contract_check.json`
- Arm Signal Visibility Probe: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\arm_signal_visibility_probe.json`
- Per-phase Feature Delta Dump: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\per_phase_feature_delta_dump.json`
- Collapse Summary: `artifacts\ab_v3_rerun\2026-04-23-arm-separation-v1-extractor-patch\collapse_summary.json`
