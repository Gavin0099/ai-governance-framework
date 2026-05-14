# Runtime Reliability Evidence Layer v0.1

As-of: 2026-05-14  
Status: established  
Scope: observation plane only

## Contract

This layer emits runtime reliability evidence artifacts for observation and analysis.

It is explicitly **non-enforcement**:
- `decision_usage_allowed: false`
- `gate_consumption_allowed: false`
- `producer_mode: observation_only`
- `schema_version: "0.1"`

## Artifacts

- `artifacts/runtime/incident-log.ndjson`
- `artifacts/runtime/recovery-log.ndjson`
- `artifacts/runtime/side-effect-journal.ndjson`
- `artifacts/runtime/determinism-boundary-log.ndjson`

## Producer Surfaces

- `runtime_hooks/core/post_task_check.py` -> incident log append
- `runtime_hooks/core/session_end.py` -> recovery log + side-effect journal append
- `governance_tools/runtime_enforcement_feedback.py` -> determinism boundary log append

## Safety Boundary

- write failures are non-fatal (`safe_append_observation_event`)
- no gate, policy, or verdict flow may consume these logs in v0.1
- promotion to enforcement requires separate contract revision and explicit authority review

## Validation

- schema and append behavior verified by `tests/test_runtime_reliability_observation.py`
- negative test enforces no consumption in gate/runtime policy files
