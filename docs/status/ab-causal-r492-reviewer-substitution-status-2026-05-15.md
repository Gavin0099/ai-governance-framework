# AB Causal R49.2 Reviewer Substitution Status (2026-05-15)

As-of: 2026-05-15
Mode: observation-only
Decision: `reviewer_substitution_observation_only`
Scaffold state: `harness_evidence_surface_initialized`

## Boundary Statement

R49.2 evaluates reviewer substitutability as an observation-only fragility signal.
It does not prove reviewer independence or governance scalability.

## Interpretation Boundary (MIP-02)

| State | Admissibility |
|---|---|
| `substitution_drift_observed` | admissible observation |
| `tacit_dependency_plausible` | needs R49.x-1 |
| `tacit_dependency_supported` | needs R49.x-1 + R49.x-3 + replay consistency + attribution sufficiency |
| `tacit_dependency_established` | future-level claim only |

Rule: `substitution_drift_observed distribution collected` does **not** imply tacit dependency evidence.

## Scope

- Scenarios: 3 (SCN-RUNTIME, SCN-AUDIT, SCN-PRODUCT)
- Seeds: 350101 / 350102 / 350103
- Substitution matrix: 3 scenarios x 2 substitute directions x 3 seeds = 18 runs
- `expected_run_count`: 18 (invariant)
- No new rules added
- No new gates added

## Harness Rerun (Mode=harness)

- Preflight: pass
- Consolidation guard active: `no_new_ontology_layers=true`
- Record integrity guards active:
  - memory dedupe present
  - canonical invalid closeout memory fail-closed label present

## Field Validity Check (18 runs)

- `measurement_source`: valid for all runs
- `null_type`: valid for all runs
- `admissibility_tier`: valid for all runs

Observed distribution:
- `measurement_source = harness_error_fallback` : 18/18
- `null_type = NT-01` : 18/18
- `interpretation = not_measured` : 18/18

## Causal Boundary

- `causal_finding_level: observation_only`
- No `tacit_dependency_detected` finding emitted in this rerun.

## Decision Lock

| Decision | Allowed | Rationale |
|---|---|---|
| `reviewer_substitution_observation_only` | YES | correct for this phase |
| `reviewer_substitution_passed` | NO | premature |
| `reviewer_independence_confirmed` | NO | out of scope for R49.2 |

## Next Step

Proceed to:
1. R49.x-1 evaluator neutrality
2. R49.x-3 hotspot transferability

No scenario expansion before attribution checks complete.

## Artifacts

- dataset: `ab-causal-r492-reviewer-substitution-dataset-2026-05-15.json`
- checkpoint: `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json`
- run script: `run_r492_reviewer_substitution.ps1`

## Non-Goals

- No global reviewer score
- No staffing recommendations
- No automatic reviewer assignment changes
- No scope expansion beyond 3 fixed scenarios
