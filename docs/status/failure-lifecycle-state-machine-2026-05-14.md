# Failure Lifecycle State Machine

As-of: 2026-05-14  
Scope: runtime reliability incident handling

## State Graph

`detected -> classified -> isolated -> recoverability_decision -> (recovered | compensation_required | escalated) -> replay_assessed -> closed`

## State Definitions

| state | entry condition | required output | next states |
|---|---|---|---|
| detected | any anomaly signal above threshold | incident_id, raw signal | classified |
| classified | primary failure class assigned | class, severity, owner | isolated |
| isolated | blast radius bounded | isolation_action, boundary status | recoverability_decision |
| recoverability_decision | recovery strategy selected | recovery_mode | recovered, compensation_required, escalated |
| recovered | direct recovery succeeded | recovery_evidence, mttr | replay_assessed |
| compensation_required | direct rollback not possible | compensation_plan | replay_assessed, escalated |
| escalated | human authority required | escalation_ticket, authority_token | replay_assessed, closed |
| replay_assessed | replayability determined | replay_status, divergence_note | closed |
| closed | resolution accepted | closure_reason, postmortem_flag | terminal |

## Invariants

- no incident may jump from `detected` to `closed`
- `safety:S3` must pass through `escalated`
- `compensation_required` must include explicit side-effect journal links
- `closed` requires one of: `recovered`, `compensated`, or `accepted_with_escalation`

## Lifecycle Record Schema

```yaml
incident_id: ""
primary_class: ""
severity: ""
state: ""
state_entered_at_utc: ""
owner: ""
isolation_action: ""
recovery_mode: "retry|replay|rollback|compensate|manual"
replay_status: "replayable|non_replayable|diverged"
closure_reason: ""
postmortem_required: false
```
