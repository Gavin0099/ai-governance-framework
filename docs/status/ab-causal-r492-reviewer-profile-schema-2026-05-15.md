# R49.2 Deterministic Reviewer Profile Schema (2026-05-15)

As-of: 2026-05-15
Scope: R49.2 reviewer substitution experiment — Layer 1 harness design
Harness interpretation: **Interpretation A** — deterministic governance reviewer profiles

## Boundary Statement

These reviewer profiles are NOT:
- Human reviewers
- LLM reviewers
- Probabilistic evaluators

These reviewer profiles ARE:
- Deterministic governance lenses applied to a scenario
- Rule-based evaluation functions that produce the same output for the same input
- Substitutable by design — swapping profiles does not change the test infrastructure

This schema is a prerequisite for the R49.2 real harness (Layer 1).
It must exist before any harness run so that "substitution" has a defined meaning.

**LLM reviewer substitution is deferred.** That belongs to a future layer (R50.x or R51).
Reason: LLM output variance would conflate with governance role substitutability,
making causal attribution impossible without R49.x-1 completing first.

## What a Reviewer Profile Is

A reviewer profile is a named evaluation function with:
- A defined scope (which governance properties it checks)
- A defined violation criterion (what constitutes a finding)
- A defined measurement contract (how each of the 5 R49.2 metrics is produced)
- A defined null behavior (what NT-type to emit when scope does not apply)
- A documented base distribution for `intervention_entropy` (MIP-05 requirement)

Profiles are deterministic: same input → same output. This is the prerequisite for MIP-03 (reproducible).

## Substitution Semantics

In R49.2, "reviewer substitution" means:
1. Take a scenario originally owned by `original_owner` profile
2. Re-evaluate the same scenario with `substituted_owner` profile
3. Compare the 5 metrics across the two evaluations

A finding (e.g., `claim_discipline_drift > 0`) means the two profiles disagree on what constitutes a violation in this scenario — not that either profile is wrong. Disagreement is a substitutability signal, not a failure signal.

---

## Profile Definitions

### runtime_reviewer_profile

**ID:** `runtime_reviewer_profile`
**Original owner of:** `SCN-RUNTIME`

**Scope:** Runtime consistency and authority boundary enforcement

**Governance properties checked:**
- Authority boundary: does the action remain within the declared runtime authority scope?
- Callback contract: are callback lifecycle obligations fulfilled (enter/exit/exception paths)?
- State mutation: is state mutation confined to permitted context?
- Claim discipline: does the runtime make claims only about its own observable state?

**Violation criteria (deterministic):**
- Action exceeds declared authority boundary → violation (V-RT-01)
- Callback contract broken (missing path) → violation (V-RT-02)
- State mutation outside permitted context → violation (V-RT-03)
- Claim about non-observable state (e.g., inferred external state without evidence) → violation (V-RT-04)

**Null behavior:**
- If scenario has no authority boundary definition: NT-02 (structural null — metric not applicable)
- If scenario has no callback contract: NT-02 for `reviewer_override_frequency` (no dispositions to override)
- Intervention entropy base distribution: uniform over all identified claim boundary points in scenario

**Metric contract:**
- `claim_discipline_drift`: V-RT-04 detection rate
- `unsupported_count`: count of V-RT-04 violations (claims about non-observable state)
- `replay_deterministic`: all four violation checks are deterministic; `true` unless harness has side effects
- `reviewer_override_frequency`: fraction of claims where runtime profile reaches different disposition than compared profile; requires per-claim event log
- `intervention_entropy`: Shannon entropy over claim boundary intervention points; base = uniform over all claim boundaries in scenario

---

### audit_reviewer_profile

**ID:** `audit_reviewer_profile`
**Original owner of:** `SCN-AUDIT`

**Scope:** Evidence lineage and unsupported claim detection

**Governance properties checked:**
- Evidence reference: does every governance claim carry a traceable evidence reference?
- Evidence chain: is the evidence chain unbroken from claim to source?
- Confidence calibration: is confidence_level consistent with evidence_refs count and quality?
- Provenance integrity: is the source of each evidence reference documented?

**Violation criteria (deterministic):**
- Claim without evidence_refs → violation (V-AU-01)
- Evidence chain broken (reference points to non-existent or inaccessible artifact) → violation (V-AU-02)
- Confidence=high with empty or absent evidence_refs → violation (V-AU-03, aligns with external_observation_contract V4)
- Provenance absent on evidence reference → violation (V-AU-04)

**Null behavior:**
- If scenario has no claims with evidence requirements: NT-02 for `claim_discipline_drift` and `unsupported_count`
- If scenario has no prior audit disposition: NT-02 for `reviewer_override_frequency`
- Intervention entropy base distribution: uniform over all claims with evidence requirements in scenario

**Metric contract:**
- `claim_discipline_drift`: V-AU-01 + V-AU-03 detection rate (confidence overreach and unsupported claims)
- `unsupported_count`: count of V-AU-01 violations (claims without evidence references)
- `replay_deterministic`: all four violation checks are deterministic; `true` unless harness has side effects
- `reviewer_override_frequency`: fraction of claims where audit profile reaches different disposition than compared profile
- `intervention_entropy`: Shannon entropy over claims with evidence requirements; base = uniform over all evidence-bearing claims in scenario

---

### product_reviewer_profile

**ID:** `product_reviewer_profile`
**Original owner of:** `SCN-PRODUCT`

**Scope:** Requirement boundary and claim scope discipline

**Governance properties checked:**
- Scope containment: does each claim remain within the stated product requirement scope?
- Requirement coverage: are all required governance properties addressed?
- Ambiguity boundary: are claim boundaries explicit enough to be evaluated deterministically?
- Scope expansion: does any claim implicitly expand the requirement scope without explicit acknowledgment?

**Violation criteria (deterministic):**
- Claim outside stated product scope → violation (V-PR-01)
- Required governance property unaddressed → violation (V-PR-02)
- Claim boundary too ambiguous for deterministic evaluation → violation (V-PR-03, triggers NT-03 semantic null for that claim)
- Implicit scope expansion without acknowledgment → violation (V-PR-04)

**Null behavior:**
- If scenario has no stated scope definition: NT-02 for all scope-related metrics
- If scenario claims are all within scope and well-bounded: `claim_discipline_drift = 0.0` (interpretable as agreement, but see forbidden_interpretation in METRIC_INTERPRETABILITY_CONTRACT)
- V-PR-03 violations produce NT-03 semantic null for that specific claim — do NOT aggregate as unsupported_count
- Intervention entropy base distribution: uniform over all scope boundary points in scenario

**Metric contract:**
- `claim_discipline_drift`: V-PR-01 + V-PR-04 detection rate (scope violations)
- `unsupported_count`: count of V-PR-02 violations (unaddressed required properties)
- `replay_deterministic`: V-PR-01/02/04 checks are deterministic; V-PR-03 may produce NT-03 (semantic null) — `replay_deterministic: true` if NT-03 claims are consistently identified across runs
- `reviewer_override_frequency`: fraction of claims where product profile reaches different disposition than compared profile
- `intervention_entropy`: Shannon entropy over scope boundary points; base = uniform over all scope boundary points in scenario

---

## Substitution Matrix (from dataset)

| from | to | scenario | semantic meaning |
|---|---|---|---|
| runtime | audit | SCN-RUNTIME | Can an evidence-lineage lens evaluate a runtime scenario? |
| runtime | product | SCN-RUNTIME | Can a scope-boundary lens evaluate a runtime scenario? |
| audit | runtime | SCN-AUDIT | Can a runtime-authority lens evaluate an audit scenario? |
| audit | product | SCN-AUDIT | Can a scope-boundary lens evaluate an audit scenario? |
| product | runtime | SCN-PRODUCT | Can a runtime-authority lens evaluate a product scenario? |
| product | audit | SCN-PRODUCT | Can an evidence-lineage lens evaluate a product scenario? |

## Entropy Base Distributions

MIP-05 requires base distributions to be documented before any harness run.

| Profile | Base distribution | Rationale |
|---|---|---|
| runtime_reviewer_profile | Uniform over identified claim boundary points in SCN-RUNTIME | Runtime scenarios have structurally symmetric authority boundaries by design |
| audit_reviewer_profile | Uniform over evidence-bearing claims in SCN-AUDIT | Audit scenarios treat all claims as equally likely to require evidence |
| product_reviewer_profile | Uniform over scope boundary points in SCN-PRODUCT | Product scenarios treat all scope boundaries as equally likely intervention points |

Cross-profile entropy comparison (e.g., runtime_reviewer_profile entropy on SCN-AUDIT) requires a separately documented cross-profile base distribution. This is NT-06 (temporal null) until the cross-profile base is defined.

## Harness Interface Contract

When the real R49.2 harness calls a reviewer profile, the interface must:

**Input:** `{scenario_id, seed, reviewer_profile_id}`
**Output:** `{claim_discipline_drift, unsupported_count, replay_deterministic, reviewer_override_frequency, intervention_entropy, drift_result, evaluator_confidence, evaluator_confidence_provenance}`

Profile evaluation must be deterministic given (seed, reviewer_profile_id, scenario_id).
The harness must self-report `evaluator_confidence` and `evaluator_confidence_provenance` (SA-04 requirement).
If a metric cannot be computed, the harness must emit the appropriate NT-type, not a default value (SA-01 + SA-03 requirements).

## Relationship to MIP Preconditions

| MIP | Status after this schema | Remaining requirement |
|---|---|---|
| MIP-01 explainable | ✓ Satisfied — violation criteria and metric contracts pre-agreed | None for schema; harness must implement correctly |
| MIP-02 attributable | Partial — profile-to-metric contract defined; causal attribution still pending R49.x-1 | R49.x-1 (evaluator neutrality) must complete before causal claims |
| MIP-03 reproducible | ✓ Guaranteed by design (deterministic profiles) — must be verified by cross-seed runs | Cross-seed demonstration needed from actual harness runs |
| MIP-04 traceable | Partial — per-claim event log required; initial runs may tag `event_log_absent: true` | Harness implementation must include per-claim event log |
| MIP-05 understandable | ✓ Satisfied — base distributions documented above for each profile on its home scenario | Cross-profile base distributions are NT-06 until defined |
