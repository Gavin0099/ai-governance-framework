# AB Causal R49.2 Reviewer Substitution Status (2026-05-15)

As-of: 2026-05-15
Mode: observation-only
Decision: `reviewer_substitution_observation_only`
Scaffold state: `scaffold_validated`

## Boundary Statement

R49.2 evaluates reviewer substitutability as an observation-only fragility signal.
It does not prove reviewer independence or governance scalability.

## Objective

Determine whether governance review outcomes are robust to reviewer owner substitution,
or whether specific reviewer roles carry tacit knowledge that cannot be substituted
without introducing claim drift, override cost, or runtime inconsistency.

## Scope

- Scenarios: 3 (SCN-RUNTIME, SCN-AUDIT, SCN-PRODUCT) — fixed from R48 baseline
- Seeds: 350101 / 350102 / 350103 — fixed, same as R48
- Substitution matrix: 3 scenarios × 2 substitute directions × 3 seeds = 18 runs
  - Each scenario contributes its original_owner as the `from` role; 2 others become `to`
  - Substitution pairs are scenario-scoped, not cross-product with all 3 scenarios
- `expected_run_count`: 18 (invariant — must equal actual checkpoint run count)
- No new rules added
- No new gates added

## Tracked Metrics

| Metric | Description |
|---|---|
| `claim_discipline_drift` | Change in claim boundary compliance after reviewer substitution |
| `unsupported_count` | Count of claims without traceable evidence support |
| `replay_deterministic` | Whether substituted run produces same outcome on replay |
| `reviewer_override_frequency` | Rate of reviewer intervention above baseline |
| `intervention_entropy` | Distribution uniformity of reviewer interventions |

## Interpretation Table

| Result | Interpretation |
|---|---|
| substitution 後指標穩定 | reviewer knowledge 可轉移候選 |
| override frequency 上升但 claim 不漂移 | 可替代但成本較高 |
| claim drift / unsupported > 0 | 存在 reviewer tacit dependency |
| replay 不 deterministic | substitution 破壞 runtime consistency |
| entropy 過度集中 | governance knowledge silo 風險 |

## Judgment Frame

不是看 hotspot 有沒有，而是看 hotspot 是否可替代。

## Decision Lock

| Decision | Allowed | Rationale |
|---|---|---|
| `reviewer_substitution_observation_only` | YES | correct for this phase |
| `reviewer_substitution_passed` | NO | premature — implies substitutability proven |
| `reviewer_independence_confirmed` | NO | out of scope for R49.2 |

## Scaffold State

`scaffold_validated` — not `evidence_collected`

| Phase | Meaning |
|---|---|
| `scaffold_validated` | invariant passes, DryRun passes, mode routing correct, measurement fields present |
| `evidence_collected` | harness wired, ≥1 run with `measurement_source: harness`, metrics non-null |

**Next gate to `evidence_collected`:** wire harness, run `-Mode harness` on ≥1 scenario/seed pair,
verify `measurement_source` distinguishes `harness` from `harness_error_fallback`.

## Measurement Source Taxonomy

| `measurement_source` | Meaning |
|---|---|
| `stub` | null metrics, scaffold only |
| `harness` | real metrics from governance_harness.py |
| `harness_error_fallback` | harness failed, metrics reverted to null — do NOT interpret as reviewer fragility |
| `dryrun` | no measurement, loop verification only |

## Evaluator Neutrality

R49.2 begins to govern governance observability itself.

The `evaluator_confidence` field is an epistemic provenance signal for the evaluator —
not a governance gate and not a metric about the reviewer.

| `evaluator_confidence` | Meaning |
|---|---|
| `high` | harness ran cleanly, metric surface well-covered |
| `medium` | harness ran, partial coverage or one metric with low observability |
| `low` | harness ran but significant observability gap — results directional only |
| `unknown` | stub / dryrun / harness_error_fallback — no actual measurement |

**Anti-patterns (explicitly disallowed):**

- `unknown` → `fail` — epistemically dishonest
- `unknown` → `pass` — epistemically dishonest
- `low evaluator_confidence` → `governance fragility` — evaluator adaptation leakage

**Evaluator adaptation leakage risks (to monitor when harness is wired):**

| Leakage type | Surface symptom | Actual cause |
|---|---|---|
| harness familiarity bias | substitution looks like drift | harness knows runtime reviewer better |
| observability gap | `unsupported` appears to increase | audit path less observable to harness |
| metric instability | `entropy` appears to converge | product ambiguity metric not stable |

The next phase (`evidence_collected`) must verify evaluator neutrality before interpreting
any substitution signals as genuine governance fragility.

## Status

- Total runs: 18
- Completed: 0 (stub phase)
- Pending: 18
- Drift detected: pending
- Silo risk flagged: pending

## Artifacts

- dataset: `ab-causal-r492-reviewer-substitution-dataset-2026-05-15.json`
- checkpoint: `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json`
- run script: `run_r492_reviewer_substitution.ps1`

## Parent Lineage

- R48 consolidated: `ab-causal-r48-cross-repo-consolidated-status-2026-05-15.md`
- V1 freeze package: `ab-causal-v1-freeze-package-2026-05-15.json`
- Hotspot surface spec: `reviewer-semantic-hotspot-surface-spec-2026-05-15.md`

## Non-Goals

- No global reviewer score
- No staffing recommendations
- No automatic reviewer assignment changes
- No scope expansion beyond 3 fixed scenarios
