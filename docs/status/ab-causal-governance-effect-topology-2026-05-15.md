# AB Causal Governance Effect Topology (2026-05-15)

As-of: 2026-05-15  
Scope: post 3-repo cross-repo observation synthesis  
Global claim boundary: "Current AI governance effect is observable but condition-dependent."

## Why This Exists

Recent results show cross-repo heterogeneity:

- `gl-electron-tool`: `threshold_dependent_persists`
- `financial-pdf-reader`: `mechanism_stable_candidate` (harness-local + real-task matched runs reported)
- `ai-governance-framework`: `mechanism_stable_candidate`

The main need is no longer "more pass counts".  
The main need is a topology model that explains **where governance has leverage** and **where it weakens**.

## Topology Dimensions

Use these dimensions to classify tasks before selecting mechanism families.

1. `determinism_level`
- high: stable inputs, low runtime nondeterminism
- low: runtime timing/state interactions dominate

2. `schema_contract_strength`
- high: strong structural/evidence contracts available
- low: weak or implicit structure

3. `observability_coverage`
- high: key failure modes are visible in artifacts/metrics
- low: key failures hide in async/runtime behavior

4. `control_surface_leverage`
- high: single policy/control toggles measurably shift outcomes
- low: policy toggles show little measurable shift

5. `external_env_dependency`
- high: external timing/process/environment dominates outcomes
- low: mostly internal deterministic processing

## Current 3-Repo Mapping (Working Model)

| repo | topology signal | leverage class | current decision |
|---|---|---|---|
| gl-electron-tool | lower determinism, higher orchestration/runtime coupling, lower observable leverage | weak-to-medium | threshold_dependent_persists |
| financial-pdf-reader | higher contractability, evidence-structured tasks, measurable governed/ungoverned separation | medium-to-strong | mechanism_stable_candidate |
| ai-governance-framework | contract-heavy governance tasks, detectable control-surface effect (arm2 detectable=true) | strong | mechanism_stable_candidate |

## Interpretation Rules

1. `mechanism_stable_candidate` in one repo does not imply universal robustness.
2. `threshold_dependent_persists` in one repo is not an outlier to ignore; it is a topology warning.
3. Heterogeneity is first-class evidence, not noise.

## Mechanism Routing Guidance (Next Generation)

For strong-leverage topologies:
- prioritize contract/evidence enforcement surfaces
- use policy toggles with measurable distribution-shift diagnostics

For weak-leverage topologies:
- do not inflate governance stacks by default
- prioritize runtime-state observability, failure-surface instrumentation, and task decomposition
- treat strict-fail as either robustness failure or metric-misalignment candidate; audit both

## Anti-Inflation Guardrail

Do not upgrade to:
- "robustness confirmed"
- "generalized uplift proven"

Unless:
- matched real-task strict gate passes across heterogeneous topology classes, and
- effect remains measurable with unsupported_count=0.

## Immediate Next Step

Build `topology-tagged experiment routing`:
- every new AB run must declare topology tags
- mechanism families are selected by topology class, not globally applied defaults
- result interpretation must include topology-conditioned claim bounds

