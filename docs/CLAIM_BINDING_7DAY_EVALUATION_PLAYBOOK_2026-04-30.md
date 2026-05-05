# Claim Binding 7-Day Evaluation Playbook

## Purpose
Evaluate whether claim-binding has both pipeline integrity and decision effectiveness before enabling CI default-on.

## Preconditions
- Framework repo includes:
  - `governance_tools/runtime_completeness_audit.py`
  - `governance_tools/closeout_audit.py`
  - `scripts/run_claim_binding_evaluation.ps1`
- Target repo produces runtime artifacts under `artifacts/runtime/` and `artifacts/claim-enforcement/`.

## Daily Command (Day 1 to Day 7)
```powershell
powershell -ExecutionPolicy Bypass -File E:\BackUp\Git_EE\ai-governance-framework\scripts\run_claim_binding_evaluation.ps1 `
  -ProjectRoot E:\BackUp\Git_EE\cli `
  -BaselineBefore 2026-04-30T00:00:00+00:00 `
  -OutputDir artifacts/claim-binding-eval
```

## Expected Daily Outputs
- `artifacts/claim-binding-eval/claim-binding-eval-<timestamp>.json`
- `artifacts/claim-binding-eval/claim-binding-eval-<timestamp>.md`

## Decision Rules
### Integrity Gate (must pass every day)
- `window_integrity.pass = true`
- `pipeline_existence.pass = true`

### Effectiveness Gate (must be observed in 7-day window)
- At least one day where:
  - `decision_activation.pass = true`

### Override Discipline Gate (must pass every day)
- `override_discipline.pass = true`

## Final 7-Day Verdict
- `default_on_ready` only if:
  - Integrity gate passes for all 7 days
  - Decision activation observed at least once
  - Override discipline passes for all 7 days
- Otherwise `not_ready` with blocker reasons.

## Trust Boundary Note
Always include this in review summary:
- `historical data: pre-claim-binding (non-comparable)`

## Boundary Separation Note
This playbook is for claim-binding readiness evaluation and can produce a
`default_on_ready` or `not_ready` operational verdict for claim-binding flow
only. It is separate from the token observability governance boundary.

Token observability fields (for example `token_count`, `token_trust`,
`token_observability_level`, `provenance_warning`) remain non-authoritative in
their own contract and MUST NOT be consumed for automated decision, gating, or
enforcement in this playbook.
