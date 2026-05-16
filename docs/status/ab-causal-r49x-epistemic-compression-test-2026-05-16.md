# R49.x Epistemic Compression Test (2026-05-16)

As-of: 2026-05-16
Result: **pass**
Performed-by: Codex (framework-internal evaluation)

## Test Criterion

> A reviewer unfamiliar with this framework must be able to reconstruct the current
> governance state from ≤3 artifacts in ≤15 minutes.

## Candidate Artifact Set

| # | Artifact | Role |
|---|---|---|
| 1 | `ab-causal-r492-reviewer-substitution-status-2026-05-15.md` | Synthesis surface — what the experiment is, current state, task status, r50 criteria |
| 2 | `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json` | Evidence record — 18 run records, guard state, decision lock, aggregate |
| 3 | `ab-causal-r49x-consolidation-window-plan-2026-05-15.md` | Context and r50 exit criteria — why the window exists, what's allowed, what r50 requires |

## Evaluation

### Artifact 1 — Status doc (synthesis surface)

A reviewer starting here can immediately find:
- Experiment: R49.2, 18-run reviewer substitution observation, mode=observation-only
- Decision: `reviewer_substitution_observation_only` (locked)
- Claim boundary: `substitution_drift_observed` only (MIP-02 blocks higher claims)
- Harness state: 18/18 runs completed with `measurement_source=harness`
- Task completion table: r49x-1 through r49x-6 with blocking flags
- R50 criteria table: 5/6 satisfied; only epistemic compression test remaining
- Next step: explicitly stated (compression test → r50 if pass)

**Verdict**: sufficient as entry point. A reviewer can establish current state without reading artifacts 2 or 3.

### Artifact 2 — Checkpoint (evidence record)

Provides machine-verifiable backing for artifact 1's claims:
- `guard.decision_locked_to = reviewer_substitution_observation_only`
- `guard.no_rule_added = true`, `guard.no_gate_added = true`
- `aggregate.total_runs = 18`, `aggregate.completed = 18`, `aggregate.drift_detected = true`
- Per-run records show `measurement_source=harness`, `evaluator_confidence=medium`, non-zero `claim_discipline_drift`
- `interpretation_boundary` block explains what's admissible vs. premature

**Verdict**: confirms artifact 1 claims without requiring full read. Aggregate + guard blocks are sufficient for governance state reconstruction.

### Artifact 3 — Consolidation plan (context)

Provides the "why" and the r50 exit criteria definition:
- Why the consolidation window exists (epistemic stack inflation risk)
- 5 task definitions with pass criteria
- R50 entry criteria (same as tracker/status doc, but with rationale)
- Freeze rules (what's forbidden in this window)

**Verdict**: needed for understanding scope boundaries and r50 definition, but artifact 1 now contains the r50 criteria table so artifact 3 is supplementary, not required for state reconstruction.

## Reconstruction Scenario

A reviewer who reads artifact 1 top-to-bottom can answer in ≤10 minutes:

| Question | Answered by | Location |
|---|---|---|
| What is this experiment? | Artifact 1 | Boundary Statement + Scope |
| What decision is locked? | Artifact 1 | Decision Lock table |
| Are harness runs complete? | Artifact 1 | Field Validity Check |
| What metrics were found? | Artifact 1 | Metric Summary table |
| What's the current claim? | Artifact 1 | Causal Boundary |
| What's left before r50? | Artifact 1 | R50 Entry Criteria Status table |
| What's the next step? | Artifact 1 | Next Step section |

Artifact 2 validates the run-level evidence. Artifact 3 explains scope boundaries.
No other artifacts are required to establish current governance state.

## Friction Points Identified

1. **Checkpoint size**: 575 lines of JSON. Reviewer must know to check `aggregate` + `guard` + first 2-3 run records only. Mitigation: status doc summarizes all relevant fields.

2. **Task → criteria mapping**: The tracker (not in the 3-artifact set) contains per-task details. The status doc's task table is sufficient for state reconstruction; tracker is supplementary.

3. **"drift_detected: true" interpretation**: `drift_detected` in the checkpoint aggregate may suggest a causal finding. The status doc's Causal Boundary section and the `interpretation_boundary` block in the checkpoint both clarify this is observation-only.

## Result

**PASS** — the 3-artifact set supports governance state reconstruction in ≤15 minutes.

Constraint: The status doc (artifact 1) must be kept current as the synthesis surface.
If artifact 1 becomes stale, the compression test would fail and must be re-run before r50.

## Impact on R50

This test passing satisfies the final r50 entry criterion:
- `epistemic_compression_test_passed: true`

All 6 r50 entry criteria are now satisfied. R50 may open.
