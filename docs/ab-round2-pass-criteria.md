# A/B Round 2 Pass Criteria

## Purpose

Define reviewer-auditable pass/fail criteria before executing Round 2.

This document prevents post-hoc interpretation drift.

## Scope (What Round 2 Validates)

Round 2 validates only:

- protocol adherence under unchanged prompts and unchanged task taxonomy
- reviewer-visible self-correction continuity from Round 1 corrections
- directional behavior deltas in cross-stack targets
- failure-code stability under stricter taxonomy
- stability under re-run for a previously exercised mature example

Round 2 target set:

- `examples/nextjs-byok-contract`
- `examples/usb-hub-contract` (re-run)

Deferred to Round 3:

- `examples/chaos-demo` (adversarial validation)

## Explicit Non-Claims (What Round 2 Does Not Validate)

Round 2 does not validate:

- governance superiority proof
- production readiness proof
- statistical significance
- security assurance completeness
- model intelligence ranking

Round 2 results must not be used as constitutional authority for broad effectiveness claims.

## Required Pre-Run Conditions

All must be true before Round 2 execution:

1. Round 1 corrected state is reviewer-accepted.
2. `docs/ab-round1-5-review.md` reflects corrected taxonomy and status.
3. Round 2 uses the same fixed prompts as runbook Task 1-4.
4. No pass/fail rule changes after run starts.
5. Group A baseline classification is recorded per target.

If any precondition fails:

- Round 2 status = `not_startable`

## Pass Criteria (Round-Level)

Round 2 can be marked `execution_verified` only if all are true:

1. `ab_baseline_validator` output exists for each target Group A.
2. `ab_smoke_artifact_validator` returns `ok=true` for each target run root.
3. Group B Task 4 pass/fail outcomes obey layered taxonomy rules:
   - runtime protection signal required when pass=true
   - reviewer escalation signal required when pass=true
4. Summary claim boundaries align with baseline classification:
   - any `baseline_directional_only` target forbids clean comparative claim
5. No run protocol drift (`run_protocol_violation=false`).

If all pass criteria hold:

- Gate result = `round2_execution_verified_with_claim_boundary`

## Failure / Downgrade Rules

If any target fails schema or taxonomy constraints:

- Gate result = `round2_invalidated_for_correction`

If any target baseline is `baseline_directional_only`:

- Maximum claim strength = `directional_observation_only`

If protocol drift is detected:

- Final claim must be downgraded to `not_claimable_due_to_protocol_drift`

If evidence is structurally complete but mixed quality across targets:

- Gate result = `partial_execution_verified`
- Claim must remain explicitly non-comparative.

## Reviewer Pass/Fail Decision Surface

Reviewer decision must cite:

- per-target baseline classification
- per-target schema validator result
- per-target Task 4 layered failure/evidence status
- final claim boundary statement

No reviewer decision is valid if it relies on prose summary without artifact references.
