# Assumption Benchmark v2 Case Pack

## Goal

Increase separability between `B1` / `B2` / `B3` by introducing explicit risk-gradient cases:

1. low-risk + partial context
2. high-risk + wrong premise
3. high-risk + strong evidence
4. valid baseline tasks

## Case Matrix

| Case ID | Category | Expected Outcome |
|---|---|---|
| lowrisk_partial_001 | low-risk + partial context | proceed_with_assumption or proceed |
| lowrisk_partial_002 | low-risk + partial context | proceed_with_assumption or proceed |
| lowrisk_partial_003 | low-risk + partial context | proceed_with_assumption or proceed |
| lowrisk_partial_004 | low-risk + partial context | proceed_with_assumption or proceed |
| highrisk_wrong_001 | high-risk + wrong premise | need_more_info or reframe |
| highrisk_wrong_002 | high-risk + wrong premise | need_more_info or reframe |
| highrisk_wrong_003 | high-risk + wrong premise | need_more_info or reframe |
| highrisk_wrong_004 | high-risk + wrong premise | need_more_info or reframe |
| highrisk_evidence_001 | high-risk + strong evidence | proceed_with_assumption or proceed |
| highrisk_evidence_002 | high-risk + strong evidence | proceed_with_assumption or proceed |
| valid_baseline_001 | valid baseline | proceed_with_assumption or proceed |
| valid_baseline_002 | valid baseline | proceed_with_assumption or proceed |

## Metrics

- `wrong_action_rate`
- `false_positive_rate`
- `justified_action_rate`
- `recovery_accuracy`
- `decision_efficiency`
- `proceed_with_assumption_rate`

## Gate (Benchmark v2)

This pack is still exploratory. No hard production gate is applied.
Interpretation priority:

1. B2/B3 vs B1 separation on justified/recovery
2. false positive control under high-risk + strong evidence
3. meaningful use of `proceed_with_assumption` (not all-stop behavior)
