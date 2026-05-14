# Failure Classification Matrix

As-of: 2026-05-14  
Owner: GavinWu  
Scope: runtime reliability layer

## Rules

- Each incident must have exactly one `primary_class`.
- Optional `secondary_tags` are allowed for cross-cutting context.
- Rollup charts must report per-class rates first, then aggregate.

## Classes

| class | definition | typical examples | owner | target_slo | required recovery path |
|---|---|---|---|---|---|
| cognition | model output quality/logic failure | hallucination, wrong inference, claim overreach | model/runtime owner | <= 2% per 7d | correction + reviewer verification |
| orchestration | execution flow coordination failure | retry storm, deadlock, tool-call loop | runtime orchestration owner | <= 1% per 7d | throttle/freeze + queue reset |
| governance | policy/authority enforcement failure | invalid escalation, bypass of required gate | governance/control-plane owner | 0 critical | hard block + authority reset |
| economics | cost/latency budget failure | token runaway, excessive retries | platform economics owner | <= budget threshold | throttle + degrade mode |
| determinism | replay/state consistency failure | non-replayable result, state divergence | state/replay owner | <= 0.5% per 7d | checkpoint restore + diff reconcile |
| safety | unsafe or irreversible action risk | unapproved external action, destructive side effect | safety owner | 0 critical | execution freeze + manual approval |

## Severity Levels

| severity | meaning | action |
|---|---|---|
| S0 | informational deviation | observe only |
| S1 | recoverable, bounded impact | automatic recovery allowed |
| S2 | significant impact or repeated S1 | freeze + reviewer intervention |
| S3 | critical safety/authority breach | hard stop + incident process |

## Incident Record Template

```yaml
incident_id: ""
timestamp_utc: ""
primary_class: "cognition|orchestration|governance|economics|determinism|safety"
secondary_tags: []
severity: "S0|S1|S2|S3"
detected_by: ""
trigger_signal: ""
impact_summary: ""
automatic_recovery_applied: true
recovery_path: ""
mttr_minutes: 0
rollback_used: false
freeze_used: false
postmortem_required: false
```

## Dashboard Minimum

- class-wise incident counts (7d / 30d)
- class-wise critical rate (S3)
- class-wise MTTR
- top 3 recurring trigger signals per class
