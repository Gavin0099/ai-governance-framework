# Side-Effect Journal Schema

As-of: 2026-05-14  
Purpose: capture irreversible/compensating execution history for safe recovery.

## Lifecycle

`intent -> staged -> applied -> verified -> compensated(optional) -> recovered_state`

## Record Schema

```yaml
journal_id: ""
incident_id: ""
timestamp_utc: ""
actor_role: "planner|coder|reviewer|auditor|system"
action:
  summary: ""
  target: ""
  side_effect_class: "reversible|compensating|irreversible|forbidden-autonomous"
intent:
  authority_token: ""
  scope_hash: ""
  expected_result: ""
staged:
  checkpoint_id: ""
  preconditions_passed: true
applied:
  executed: false
  execution_ref: ""
verified:
  status: "pass|fail|partial"
  evidence_ref: ""
compensation:
  required: false
  action_ref: ""
  status: "none|pending|done|failed"
recovery_state:
  final_state: "open|recovered|escalated|closed_with_exception"
  replay_status: "replayable|non_replayable|diverged"
```

## Constraints

- `irreversible` requires non-empty `authority_token` and reviewer approval.
- `forbidden-autonomous` must never enter `applied.executed=true`.
- `verified.status=fail` requires compensation or escalation.
- journal rows are append-only; corrections must be new rows.

## Minimal Storage Contract

- journal file path: `artifacts/runtime/side-effect-journal.ndjson`
- one JSON object per line
- monotonic timestamps in UTC
