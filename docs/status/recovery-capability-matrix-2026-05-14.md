# Recovery Capability Matrix

As-of: 2026-05-14  
Purpose: avoid generic retry behavior across incompatible failure classes.

## Capability Table

| failure class | replay | auto-retry | rollback | compensate | quarantine | human escalation |
|---|---|---|---|---|---|---|
| cognition | conditional | no | limited | yes | optional | conditional |
| orchestration | yes | yes (bounded) | conditional | conditional | yes | conditional |
| governance | no | no | conditional | yes | yes | required for S2+ |
| economics | conditional | no | yes | optional | yes | conditional |
| determinism | yes (required for diagnosis) | no | yes | optional | yes | required if unresolved |
| safety | no | no | conditional | yes (strict) | yes (mandatory) | mandatory |

## Policy Rules

- `auto-retry` must be disabled for `safety`, `governance`, and unresolved `determinism`.
- `quarantine` is mandatory whenever side-effect class is `irreversible` or incident severity is `S3`.
- `compensate` requires side-effect journal entry and reviewer approval.

## Execution Contract

Before any automated recovery action:
1. verify class + severity
2. lookup capability row
3. check action allowlist
4. emit decision trace
5. execute or escalate

## Matrix Record Template

```yaml
incident_id: ""
class: ""
severity: ""
capability_selected:
  replay: false
  auto_retry: false
  rollback: false
  compensate: false
  quarantine: false
  escalate: false
decision_rationale: ""
```
