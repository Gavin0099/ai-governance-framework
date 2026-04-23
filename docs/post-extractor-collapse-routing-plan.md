# Post-Extractor Collapse Routing Plan (separation_v1)

Purpose: after minimal extractor patch, route remaining collapse by layer instead of adding broad patches.

## Scope

- Case pack: `separation_v1` only (4 cases).
- Keep fixed: gate logic, score constants, benchmark expansion.
- Target: explain remaining non-stable separation paths with minimal probes.

## Current State Snapshot

- `arm_feature_contract_check`: 3/4 expected feature separation achieved.
- `arm_signal_visibility_probe`: `separated_through_extractor=3`, `extractor_collapses_visible_arm_signal=1`.
- `collapse_summary`: mixed (`feature_extraction=1`, `score_mapping=1`, `phase_transition=1`, `mixed=1`).
- `arm_separation.action_or_ranking_separated_cases=1` (stop rule still fails).

## Routing Probes

### Probe A - Score Mapping Collapse

- Case: `sep_lowrisk_cheap_trial_001`
- Question: why does phase1 (`ask_for_evidence`) converge to final (`direct_fix` / `proceed`)?
- Minimal dump:
- final candidate score vector (`top3`) and reasons
- score delta vs phase1 for each action
- decision override path (if any)
- Expected routing outcome:
- if candidate score ordering flips without feature change -> `score_mapping overwrite`

### Probe B - Phase Transition Collapse

- Case: `sep_highrisk_partial_evidence_001`
- Question: which transition condition rewrites weak/cautious phase1 state to partial/direct-fix final?
- Minimal dump:
- phase1 vs final feature diff (`premise/evidence/scope/mode`)
- transition trigger signals used between rounds
- evidence promotion source used at final
- Expected routing outcome:
- if transition signal overwrites extracted phase1 state -> `phase_transition overwrite`

### Probe C - Residual Feature Extraction Collapse

- Case: `sep_asserted_conflicting_hint_001`
- Question: why do conflicting-hint signals still fail to create arm-sensitive phase-A deltas?
- Minimal dump:
- pre-extraction surface markers by arm
- parsed assumption/evidence signals by arm
- phase-A outputs by arm
- Expected routing outcome:
- if pre/parsed deltas exist but phase-A still identical -> `extractor mapping gap`

## Execution Rules

- Run exactly one `separation_v1` rerun per probe iteration.
- Add new outputs as sidecar JSON artifacts; do not modify score mapping and gate in this step.
- Any rule proposal must be tied to exactly one routed collapse type.

## Closure Condition

- For 4 `separation_v1` cases, at least 3 cases must map to one explicit routed cause:
- `extractor mapping gap`
- `phase_transition overwrite`
- `score_mapping overwrite`
- No "unknown/mixed without explanation" for those 3 cases.

## Out of Scope

- New benchmark packs
- New gating logic
- Score retuning for action-separation cosmetics
- Full extractor rewrite
