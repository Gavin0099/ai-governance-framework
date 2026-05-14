# Reliability Baseline (R1)

As-of: 2026-05-14  
Window: last validated runs before R2 control-plane rollout

## Baseline Fields

```yaml
failure_rate_by_class:
  cognition: null
  orchestration: null
  governance: null
  economics: null
  determinism: null
  safety: null
critical_safety_incident_rate: null
mttr_minutes: null
rollback_success_rate: null
cost_per_successful_task: null
p95_latency_seconds: null
```

## Collection Rules

- Use identical measurement path across pre/post comparisons.
- Report per-class failure first; aggregate only as secondary.
- Separate observation-only signals from enforcement-triggered outcomes.

## Acceptance for Baseline Completion

1. all six failure classes have non-null values
2. at least one full week of comparable data
3. documented data-source lineage for each metric
