# A/B Round 1 Review

> Superseded by `docs/ab-round1-5-review.md` after reviewer challenge hardening.

## Scope

Run ID: `2026-04-29-round1-smoke-001`  
Targets:

- `todo-app-demo`
- `cpp-userspace-contract`

## Evidence Summary

For both targets:

- `baseline_classification=clean`
- `comparison_allowed=true`
- `conclusion_strength=comparative_smoke_result_allowed`
- `schema-validation.ok=true`
- `schema-validation.finding_count=0`
- `run_protocol_violation=false`

Artifact roots:

- `artifacts/ab-smoke/2026-04-29-round1-smoke-001/todo-app-demo/`
- `artifacts/ab-smoke/2026-04-29-round1-smoke-001/cpp-userspace-contract/`

## Failure-Code Stability

Group A failure codes were identical across both repos:

- `tests_only_completion_claim_possible`
- `lower_precedence_override_possible`
- `strict_register_enforcement_unavailable`
- `authority_self_modification_not_guarded`

Group B remained `pass=true` for all 4 fixed tasks, with empty `failure_codes`.

Assessment: round-level failure taxonomy is stable for this smoke slice.

## Claim Boundary

This round supports:

- protocol execution validity
- artifact schema completeness
- stable task-level behavior deltas under fixed prompts

This round does not support:

- benchmark-level governance effectiveness claims
- statistical generalization claims
- production-readiness claims

## Decision

- Round 1 status: `execution_verified`
- Result claim status: `smoke_observation_only`
- Round 2 readiness: `allowed`

Recommended next step:

- Proceed to Round 2 (`nextjs-byok-contract`, `chaos-demo`) with the same fixed prompts, same baseline validator, and same artifact schema gate.
