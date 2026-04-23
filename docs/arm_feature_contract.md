# Arm-to-Feature Contract (v1)

Purpose: define which feature-level differences B1/B2/B3 are expected to create before ranking.

## Contract Table

| arm | expected feature effect | intended separating cases |
|---|---|---|
| B1 (runtime only) | premise_status: no extra intervention; evidence_alignment: no extra boost/downgrade; execution_scope: no extra conservative shift; correctness_mode: no explicit bias to `need_more_info` | Baseline only; not intended to force separation |
| B2 (assumption forcing) | For `premise_status=unknown`, preserve uncertainty and alternative-cause trace; unknown with missing direct evidence can be downgraded in `evidence_alignment`; bias `correctness_mode` toward `ask_for_evidence` over unsafe `bounded_trial` | `sep_lowrisk_epistemic_cost_001`, `sep_asserted_conflicting_hint_001` |
| B3 (assumption + evidence feedback) | Same assumption baseline as B2, but evidence feedback must sharpen weak/absent evidence handling and make `correctness_mode` at least as cautious as B2 when evidence is weak | `sep_highrisk_partial_evidence_001` and any weak/absent evidence case where B2 remains permissive |

## Case-Level Expected Separation (separation_v1)

- `sep_lowrisk_epistemic_cost_001`: expected separation on `premise_status` or `evidence_alignment` or `correctness_mode`.
- `sep_lowrisk_cheap_trial_001`: expected separation on `correctness_mode` (bounded trial vs ask-for-evidence behavior).
- `sep_highrisk_partial_evidence_001`: expected separation on `evidence_alignment` and/or `correctness_mode` (B3 should be at least as cautious as B2).
- `sep_asserted_conflicting_hint_001`: expected separation on `premise_status` and/or `correctness_mode`.

## Usage Rule

- This contract is diagnostic-first. Do not tune scoring/gate/phase-transition for arm differentiation until these expected feature differences are observable in extractor outputs.

## Non-Separation Reason Taxonomy (for `arm_feature_contract_check.json`)

- `contract_overstates_difference`: contract expects separation, but arm inputs are not materially different for the case.
- `arm_signal_not_machine_consumable`: arm prompts differ, but parsed assumption-layer signals are still identical.
- `extractor_ignores_arm_signal`: parsed arm signals differ, but phase-A extracted features remain identical.
