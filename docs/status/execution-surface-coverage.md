# Execution Surface Coverage

- generated_at: `2026-04-01T07:48:31.240700Z`
- repo_commit: `7762c0fd601d8bfeb7502d7d73433f8a85c64967`
- consumer: `reviewer`
- signal_posture: `soft-enforcement`

這個頁面是 execution surface coverage 的人類可讀摘要。它不是在做 execution harness，而是在說明：目前哪些 decision surface 已有最低 coverage，以及還有哪些缺口。

## Decision Status

| Decision | Status | Missing Hard | Missing Soft |
|---|---|---|---|
| `session_start_governance` | `covered` | `0` | `0` |
| `pre_task_governance` | `covered` | `0` | `0` |
| `post_task_governance` | `covered` | `0` | `0` |
| `runtime_reviewability` | `covered` | `0` | `0` |

## Coverage Signals

- missing_hard_required: `0`
- missing_soft_required: `0`
- dead_never_observed: `0`
- dead_never_required: `0`

## Surface Classification

| Surface | Type | Role | Requirement | Used By |
|---|---|---|---|---|
| `session_start` | `runtime_entrypoint` | `decision` | `hard` | `session_start_governance` |
| `pre_task_check` | `runtime_entrypoint` | `decision` | `hard` | `pre_task_governance` |
| `post_task_check` | `runtime_entrypoint` | `decision` | `hard` | `post_task_governance` |
| `session_end` | `runtime_entrypoint` | `decision` | `soft` | `runtime_reviewability` |
| `runtime_verdict_artifact` | `evidence_surface` | `evidence` | `hard` | `runtime_reviewability` |
| `runtime_trace_artifact` | `evidence_surface` | `evidence` | `hard` | `runtime_reviewability` |
| `runtime_decision_model` | `authority_surface` | `authority` | `hard` | `session_start_governance, pre_task_governance, post_task_governance, runtime_reviewability` |
| `decision_boundary_model` | `authority_surface` | `authority` | `soft` | `pre_task_governance` |
| `governance_authority_table` | `authority_surface` | `authority` | `soft` | `runtime_reviewability` |
