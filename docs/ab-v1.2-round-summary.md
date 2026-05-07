# AB v1.2 Round Summary

Purpose: round-level aggregation under frozen `v1.2`.

Important:
- Observational and comparative only.
- Do not change scoring/fail semantics during a round.
- Record recurring failure modes before any framework adjustment.

---

## Round Header

```yaml
round_id: "2026-05-07-cfu-doc-failure-state"
period_utc: "2026-05-07"
spec_version: "v1.2"
task_family: "failure-state documentation remediation"
baseline_commit_window: "CFU / CFU_non_ai_governance package-local baselines"
runs_A: 3
runs_B: 3
```

## Aggregate Snapshot

| Metric | Arm A | Arm B | Direction | Notes |
|---|---:|---:|---|---|
| hard_failure_rate | 0/3 | 0/3 | tie | no hard failures observed |
| attention_anchoring_failure_rate | 0/3 | 0/3 | tie | no target displacement observed |
| revert_needed_rate | low | low | tie | no immediate revert signal observed |
| unintended_change_avg | low | low | tie | both remained in target docs |
| semantic_consistency_avg | high | very high | B | governed runs more explicit on evidence layers |
| evidence_traceability_avg | medium-high | very high | B | governed runs consistently richer mappings |
| reviewer_edit_effort_avg | low | low-medium | A | non-governed runs were leaner |
| claim_overreach_avg | medium-low | low | B | governed runs stronger on failure-state boundaries |
| actionable_fix_latency_avg_sec | lower | higher | A | governance runtime narration overhead present |
| tokens_per_accepted_fix_avg | lower | higher | A | expected runtime governance cost |
| modification_density_avg | high | high | tie | both completed scoped 4-file remediation slices |
| governance_drag_rate | low | low-medium | A | no blocking drag; measurable runtime burden |
| under_commit_failure_rate | low | low | tie | both delivered material file edits |
| runtime_governance_ratio_avg (obs) | lower | higher | A | cost shifted to transcript in governed arm |
| artifact_governance_ratio_avg (obs) | low | low | tie | no deliverable governance spill observed |
| review_navigation_burden_mode (obs) | medium | medium | tie | governed outputs denser but still reviewer-usable |

## Recurring Failure Modes

1. `runtime overhead shifts to transcript in governed runs`
2. `governed runs improve failure-state inference control consistency`
3. `no recurring attention hijack after v1.2 anchoring gate`

## Stability Notes (No Spec Change)

- Recurring attention hijack observed: `no`
- Recurring governance drag observed: `no (non-blocking overhead observed)`
- Recurring scope drift observed: `no`
- Throughput collapse risk observed: `not yet (watch runtime ratio trend)`

## Decision

```yaml
decision: "continue_observation"
rationale: "v1.2 anchoring appears stable; differences now primarily in failure-state semantic coordination vs runtime overhead distribution."
next_round_task_focus: "partial-failure remediation and dependency-interaction slices under frozen v1.2"
```
