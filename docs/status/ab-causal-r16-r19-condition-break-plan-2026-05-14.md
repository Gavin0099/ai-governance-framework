# AB Causal Condition-Break Plan (r16-r19)

As-of: 2026-05-14  
Scope: extend from r11-r15 `provisionally_confirmed` outcome to causal-threat stress testing.  
Constraint: do not alter frozen rules used for r11-r15 gate; this plan is a new evidence tier.

## Objective

Move from:
- stable observable uplift under fixed protocol

To:
- bounded confidence under explicit condition-break tests against key causal threats.

## Claim Boundary (for external use)

Use this wording:

`Governance-associated observable uplift is provisionally confirmed under the current protocol and task distribution, with strong auditability and procedural integrity but limited causal isolation and external generalization.`

Do not use:
- "governance mechanism confirmed"
- "causal proof completed"
- "generalized across distributions"

## Threat Model Under Test

- reviewer leakage / recognizability
- optimization pressure adaptation
- style-driven scoring leakage
- exploration suppression under ambiguity

## Run Matrix (r16-r19)

| Run | Arm Type | Condition Break | Primary Readout | Pass Signal | Fail Signal |
|---|---|---|---|---|---|
| r16 | hidden-metrics arm | Hide token/latency/KPI visibility from agent | uplift_direction, effect_size_delta_vs_r11_r15 | uplift direction preserved with acceptable effect shrink | uplift collapses or reverses |
| r17 | normalized-output arm | Strip governance style markers before blind review | blind score delta, preference consistency | uplift remains after style removal | uplift disappears after normalization |
| r18 | high-ambiguity slice | Ambiguous tasks with multiple plausible solutions | completion_quality, rework_rate, decision_stability | no severe quality collapse, no guardrail break | unstable decisions or guardrail degradation |
| r19 | exploration-required slice | tradeoff/research/debug tasks requiring search breadth | exploration breadth proxy, final correctness, latency | breadth not suppressed below floor while quality holds | breadth collapse with quality regression |

## Frozen Execution Rules (for r16-r19 only)

- fixed seeds must be declared before each run starts
- one-window one-run (no mid-run metric rule changes)
- blind review required for all runs
- placebo and guardrail lanes are mandatory (not optional/backfill)
- scoped commit + push per completed run
- append observation log and run ledger each run

## Required Metrics Per Run

1. Outcome
- A_rate
- B_rate
- abs_delta
- rel_lift
- p_value
- ci_95

2. Safety / Placebo
- guardrail_reopen_rate
- guardrail_stability_degraded_rate
- guardrail_defect_rate
- placebo_claim_overreach_rate

3. Causal Threat Probes
- recognizability_score (reviewer could infer arm)
- hidden_metric_exposure (yes/no)
- style_marker_presence (pre/post normalization)
- exploration_breadth_proxy (branch_count or alternative_paths_count)

## Per-Run Result Label

- `pass`: primary direction holds AND guardrail pass AND placebo not significant AND arm-specific break test passes
- `fail`: direction reversal OR guardrail breach OR placebo significant in wrong direction OR break test fails
- `inconclusive`: all other states

## Cross-Run Gate (r16-r19)

All must hold:
1. at least 3/4 runs are `pass`
2. no more than 1/4 run is `fail`
3. zero critical guardrail breaches across all runs
4. placebo remains non-significant in at least 3/4 runs
5. no single condition-break arm fully nullifies effect without documented mechanism explanation

Gate output:
- `causal-strength-upgraded` when 1-5 hold
- `causal-strength-unchanged` otherwise

## Reporting Template (copy per run)

```yaml
run_id: ""
window_id: ""
seed: ""
arm_type: "hidden-metrics|normalized-output|high-ambiguity|exploration-required"
task_slice: ""
blind_review: true

outcome:
  A_rate: 0
  B_rate: 0
  abs_delta: 0
  rel_lift: 0
  p_value: 1
  ci_95: "[,]"
  direction: "B_gt_A|A_gt_B|flat"

safety_placebo:
  guardrail_reopen_rate: 0
  guardrail_stability_degraded_rate: 0
  guardrail_defect_rate: 0
  placebo_claim_overreach_rate: 0
  placebo_p_value: 1

causal_threat_probe:
  recognizability_score: 0
  hidden_metric_exposure: "no"
  style_marker_presence_pre: "low|med|high"
  style_marker_presence_post: "low|med|high"
  exploration_breadth_proxy: 0

run_label: "pass|fail|inconclusive"
one_line_interpretation: ""
```

## Minimal Next Actions

1. Create four run stubs using this plan: r16-r19.
2. Execute in order: r16 -> r17 -> r18 -> r19.
3. After each run: update ledger + observation log + scoped commit + push.
4. Publish one final status page: `ab-causal-r16-r19-condition-break-status-2026-05-14.md`.
