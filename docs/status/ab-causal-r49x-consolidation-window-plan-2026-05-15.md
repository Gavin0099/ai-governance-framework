# AB Causal R49.x Consolidation Window Plan (2026-05-15)

As-of: 2026-05-15
Mode: consolidation — no new scenarios, no scope expansion
Decision: `r49x_consolidation_window_open`

## Why This Window Exists

R49.2 has established `scaffold_validated` status with three epistemic layers:

| Layer | Field | Core question |
|---|---|---|
| Governance | `metrics` + `interpretation` | What happened after reviewer substitution? |
| Measurement | `measurement_source` + `harness_exit_code` | Was anything actually measured? |
| Evaluator | `evaluator_confidence` | Is the evaluator honest about its own limits? |

The risk before R50 is **epistemic stack inflation**:
each new layer adds observability but reduces cognitive usability.
The consolidation window exists to verify the current stack is stable
before adding new surface area.

## Inflation Risk Definition

A system is at inflation risk when:
- artifact count > reviewer attention budget
- signal count > decision-relevant signal count
- `unknown → fail` or `unknown → pass` mappings exist implicitly anywhere
- no single reader can reconstruct governance state from ≤3 artifacts

## Five Consolidation Tasks

### R49.x-1: Evaluator Neutrality Smoke

**Goal:** Confirm evaluator bias is not dominating substitution signals.

**Method:**
- Run baseline (no substitution: original_owner reviews own scenario)
- Compare metrics to substituted runs
- If baseline and substituted runs produce identical metric distributions: evaluator is not scenario-blind (bias risk)
- If baseline is consistently "better": check for familiarity bias in harness path

**Pass criterion:** evaluator_confidence distribution is consistent across original and substituted owners.
**Not a gate** — observation only. Documents evaluator behavior before interpreting R49.2 results.

---

### R49.x-2: Substitution Replay Stability

**Goal:** Verify reviewer substitution does not independently break replay determinism.

**Method:**
- For each completed R49.2 run with `measurement_source: harness`:
  - Re-run with same seed and same substituted_owner
  - Check if `replay_deterministic` is consistent across re-runs
- A `replay_deterministic: false` that appears only in substituted runs (not baseline) is a genuine fragility signal.
- A `replay_deterministic: false` that also appears in baseline is a harness stability problem, not a substitution problem.

**Pass criterion:** replay consistency rate ≥ baseline rate ± 5%.
**Not a gate** — flags causal attribution error if replay instability is misread as substitution fragility.

---

### R49.x-3: Hotspot Transferability

**Goal:** Does the semantic hotspot surface shift when reviewer changes?

**Method:**
- Use existing hotspot surface spec (`reviewer-semantic-hotspot-surface-spec-2026-05-15.md`)
- Compare hotspot rankings between original_owner and substituted_owner runs
- If hotspot set is stable: reviewer tacit knowledge is not encoded in hotspot selection
- If hotspot set shifts: substitution changes what the evaluator considers risky (evaluator adaptation signal)

**Pass criterion:** hotspot_id overlap ≥ 70% across original/substituted pairs.
**Not a gate** — observation. Feeds into metric usefulness ranking.

---

### R49.x-4: Metric Usefulness Ranking

**Goal:** Which of the 5 tracked metrics carry genuine information vs. are correlated or redundant?

**Method:**
- After ≥6 harness runs: compute pairwise correlation across metrics
- Flag metrics where:
  - Always null regardless of substitution → observability gap
  - Always identical across substitution pairs → no substitution sensitivity
  - Highly correlated with another metric → redundant surface
- Propose candidate metric removals or reclassifications

**Output format:**

| Metric | Signal type | Usability |
|---|---|---|
| `claim_discipline_drift` | `decision_relevant` / `observational` / `redundant` / `high_cost_low_info` | keep / compress / remove |

**Not a gate** — informs future metric surface decisions. No metric removed without explicit review.

---

### R49.x-5: Null Semantics Audit

**Goal:** Confirm null/unknown values are not being implicitly converted downstream.

**Method:**
- Inspect all consumers of checkpoint runs (scripts, report generators, any downstream artifact)
- Check for patterns like:
  - `if ($metric -eq $null) { $metric = 0 }` (null → zero leakage)
  - `if (-not $confidence) { $confidence = "high" }` (unknown → optimistic leakage)
  - Aggregation functions that silently drop nulls and change denominators
- Document any found with fix or explicit acknowledgment

**Pass criterion:** zero implicit null conversions found, OR each found conversion is explicitly documented with rationale.
**This is a blocking condition for R50 entry.** Null semantics must be clean before expanding the epistemic stack.

---

## Epistemic Compression Criteria

Before R50, the following compression test must pass:

> A reviewer unfamiliar with this framework must be able to reconstruct the current governance state from ≤3 artifacts in ≤15 minutes.

Proposed canonical 3-artifact set:
1. `ab-causal-r492-reviewer-substitution-status-2026-05-15.md` — what the experiment is and what it found
2. `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json` — the evidence record
3. This document — the consolidation window and compression criteria

If the 3-artifact test fails, the epistemic stack must be compressed before R50 opens.

## Signal Classification Taxonomy

| Class | Definition | Treatment |
|---|---|---|
| `decision_relevant` | directly influences a governance gate or claim | keep, surface prominently |
| `observational_only` | useful for interpretation but not for decisions | keep, collapse by default |
| `historically_useful` | needed for lineage but not runtime-relevant | archive, not in live summaries |
| `high_cost_low_info` | expensive to measure, low signal-to-noise | candidate for removal |

## R50 Entry Criteria

R50 may open when ALL of the following are true:

1. R49.x-5 (null semantics audit) passes — zero implicit conversions
2. R49.x-4 (metric usefulness ranking) completed — metric surface documented
3. Epistemic compression test passes — 3-artifact reviewability verified
4. At least one R49.x task found a genuine signal (not all noise) — confirms the consolidation window was not empty
5. `evaluator_confidence: unknown` rate < 100% across R49.2 runs — at least some harness evidence collected

## What R50 Is NOT

R50 must not be:
- A continuation of reviewer substitution with more scenarios (that is R49.2 scope expansion, not R50)
- A response to a specific observed drift before its cause is understood
- An addition of new governance rules before evaluator neutrality is confirmed

## Freeze Rule (Hard Boundary)

R49.x consolidation window allows **ontology implementation only**, and blocks ontology expansion.

### Ontology Expansion (Disallowed in R49.x)
- adding new NT / MIP / SA classes
- changing semantics of existing NT / MIP / SA classes
- introducing new interpretation classes that elevate observation into causal finding

### Ontology Implementation (Allowed in R49.x)
- coding existing NT / MIP / SA semantics into runners/checkpoints
- fail-closed record hardening
- dedupe and contract-smoke hardening
- interpretation-boundary enforcement that downgrades premature causal labels to MIP-02-compliant observations

### Consolidation Guard
- `R49.x consolidation window only allows ontology implementation, not ontology expansion.`

## Artifacts

- R49.2 status: `ab-causal-r492-reviewer-substitution-status-2026-05-15.md`
- R49.2 checkpoint: `ab-causal-r492-reviewer-substitution-checkpoint-2026-05-15.json`
- Consolidation tracker: `ab-causal-r49x-consolidation-tracker-2026-05-15.json`
- Hotspot surface spec: `reviewer-semantic-hotspot-surface-spec-2026-05-15.md`

## Non-Goals

- No new scenarios in this window
- No new governance rules
- No scope expansion
- No R50 planning until compression test passes
