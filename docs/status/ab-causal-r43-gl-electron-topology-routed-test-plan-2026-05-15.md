# AB Causal r43 Test Plan — gl-electron-tool (Topology-Routed, 2026-05-15)

As-of: 2026-05-15  
Repo: `gl-electron-tool`  
Topology class (working): `weak-to-medium leverage`  
Prior state: `threshold_dependent_persists`

## Objective

Run a topology-routed AB test that targets weak-leverage characteristics without governance-layer inflation.

## Fixed Protocol (Unchanged)

- seeds: `350101`, `350102`, `350103`
- `max_retry=3`
- checkpoint required
- strict gate unchanged:
  - any arm with `pass_count=3/3` and `unsupported_count=0` => `mechanism_stable_candidate`
  - if all required arms `unsupported_count=0` and no arm reaches 3/3 => `threshold_dependent_persists`
  - any required arm `unsupported_count>0` => `inconclusive`

## Topology Tags (Must Be Declared In Run Artifacts)

- `determinism_level`: `low_to_medium`
- `schema_contract_strength`: `medium`
- `observability_coverage`: `medium_to_low`
- `control_surface_leverage`: `low`
- `external_env_dependency`: `high`

## Arm Design (Topology-Routed)

Do not add new governance layers.  
Use runtime-state observability and decomposition-oriented single-variable arms.

- `r43-arm-1` baseline strict
- `r43-arm-2` runtime-state observability enhancement (single variable)
- `r43-arm-3` task decomposition constraint (single variable)

Rule:
- one arm = one variable change
- no mixed-variable arm
- no direction_tolerance relaxation

## Required Outputs

- `ab-causal-r43-gl-electron-status-2026-05-15.md`
- `ab-causal-r43-gl-electron-checkpoint-2026-05-15.json`
- per-case JSON results with:
  - `injected_controls`
  - `causal_threat_probe`
  - `unsupported`
  - `attempts_used`

## Topology-Conditioned Interpretation Block (Mandatory)

Include this section in final status:

1. whether weak-leverage topology showed any strict-pass arm
2. whether observed changes are mechanism effect or metric-coupling artifacts
3. whether result updates global claim boundary (default: no)

## Claim Boundary

Allowed:
- "Current AI governance effect is observable but condition-dependent."

Disallowed:
- "Robustness confirmed"
- "Generalized uplift proven"

