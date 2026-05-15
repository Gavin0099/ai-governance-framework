# AB Causal r42 Component Ablation Spec (2026-05-15)

Objective: decompose uplift source across governance components.

## Components Under Test

- C1: checkpoint discipline
- C2: replayability requirement
- C3: reviewer visibility surface
- C4: memory explicitness constraint

## Ablation Arms (Single-Component Toggle)

- `r42-arm-baseline`: all components on
- `r42-arm-c1-off`
- `r42-arm-c2-off`
- `r42-arm-c3-off`
- `r42-arm-c4-off`

Rule: one arm toggles one component only; no multi-component mixed ablation.

## Fixed Execution

- seeds: `350101`, `350102`, `350103`
- `max_retry=3`
- checkpoint: `ab-causal-r42-component-ablation-checkpoint-2026-05-15.json`

## Per-Arm Readout

- `completed_seeds`
- `pass_count`
- `fail_count`
- `unsupported_count`
- `delta_vs_baseline_pass_rate`

## Decision

- strict gate unchanged for candidate judgement
- additional decomposition output:
  - rank components by impact magnitude on pass-rate delta
  - mark `primary_effect_driver` only if one component shows consistent negative delta across all seeds

## Output Artifacts

- `ab-causal-r42-component-ablation-status-2026-05-15.md`
- `ab-causal-r42-component-ablation-2026-05-15.json`

