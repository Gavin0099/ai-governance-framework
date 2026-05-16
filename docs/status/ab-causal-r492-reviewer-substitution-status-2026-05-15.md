# AB Causal R49.2 Reviewer Substitution Status (2026-05-15)

As-of: 2026-05-16 (updated from 2026-05-15 initial; harness rerun verified)
Mode: observation-only
Decision: `reviewer_substitution_observation_only`
Scaffold state: `harness_evidence_collected`

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

## Harness Rerun (Mode=harness, HarnessScript=scripts/r492_governance_harness.py)

- Preflight: pass
- Consolidation guard active: `no_new_ontology_layers=true`
- Record integrity guards active:
  - memory dedupe present
  - canonical invalid closeout memory fail-closed label present

## Field Validity Check (18 runs) — verified 2026-05-16

- `measurement_source`: valid for all runs
- `null_type`: valid for all runs
- `admissibility_tier`: valid for all runs

Observed distribution:
- `measurement_source = harness` : 18/18
- `evaluator_confidence = medium` : 18/18
- `evaluator_confidence_provenance = harness_self_reported` : 18/18
- `drift_result = measured` : 18/18
- `null_type = null` (harness ran cleanly) : 18/18
- `interpretation = substitution_drift_observed` : 18/18
- `event_log_absent = true` : 18/18 (MIP-04: NT-06, event log infrastructure not yet built)

> **Note on initial status**: An earlier draft of this document (2026-05-15) incorrectly
> reported `measurement_source = harness_error_fallback : 18/18`. That entry was written
> during adapter smoke validation using `governance_harness.py` (the R48 harness, CLI mismatch → NT-01).
> The subsequent real harness rerun using `scripts/r492_governance_harness.py` completed
> successfully for all 18 runs. The checkpoint reflects the correct harness results.

## Metric Summary (from checkpoint)

| Metric | Non-null | Range | Signal class (r49x-4) |
|---|---|---|---|
| `claim_discipline_drift` | 18/18 | 0.10–0.40 | observational_only |
| `unsupported_count` | 18/18 | 0–2 | observational_only |
| `replay_deterministic` | 18/18 | always True | historically_useful |
| `reviewer_override_frequency` | 0/18 | NT-06 | high_cost_low_info |
| `intervention_entropy` | 8/18 | 0.92–1.00 | observational_only |

## R49.x Consolidation Task Status (as of 2026-05-16)

| Task | Status | Blocking r50? |
|---|---|---|
| r49x-1 (evaluator neutrality) | complete | no |
| r49x-2 (replay stability) | **complete** (2026-05-16) | no |
| r49x-3 (hotspot transferability) | complete | no |
| r49x-4 (metric usefulness ranking) | **complete** (2026-05-16) | no |
| r49x-5 (null semantics audit) | complete | yes — passed |
| r49x-6 (null ontology instantiation) | complete | yes — passed |

## Causal Boundary

- `causal_finding_level: observation_only`
- No `tacit_dependency_detected` finding emitted.
- `substitution_drift_observed` is the admissible observation level.

## R50 Entry Criteria Status (as of 2026-05-16)

| Criterion | Status |
|---|---|
| null_ontology_instantiated | ✅ true |
| null_semantics_audit_passed | ✅ true |
| metric_usefulness_ranking_completed | ✅ true (2026-05-16) |
| at_least_one_genuine_signal_found | ✅ true (claim_discipline_drift non-zero 18/18) |
| evaluator_confidence_unknown_rate_below_100pct | ✅ true (unknown rate = 0%) |
| epistemic_compression_test_passed | ✅ true (2026-05-16) |

**R50 unblocked** — all 6 entry criteria satisfied as of 2026-05-16. R50 may open.

## Decision Lock

| Decision | Allowed | Rationale |
|---|---|---|
| `reviewer_substitution_observation_only` | YES | correct for this phase |
| `reviewer_substitution_passed` | NO | premature |
| `reviewer_independence_confirmed` | NO | out of scope for R49.2 |

## Next Step

All r49x consolidation tasks complete. R50 entry criteria all satisfied.
Next: open R50 scope definition (positive confidence accumulation protocol; do NOT re-run R49.2 scenarios — that is scope expansion).

## Artifacts

- dataset: `ab-causal-r492-reviewer-substitution-dataset-2026-05-15.json`
- checkpoint: `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json`
- run script: `run_r492_reviewer_substitution.ps1`
- metric ranking: `ab-causal-r49x4-metric-ranking-2026-05-16.json`

## Non-Goals

- No global reviewer score
- No staffing recommendations
- No automatic reviewer assignment changes
- No scope expansion beyond 3 fixed scenarios
