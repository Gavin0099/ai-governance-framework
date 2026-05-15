# AB Causal Cross-Repo — 3rd Repo Replication Gate: ai-governance-framework (2026-05-15)

As-of: 2026-05-15
Mode: real-task violation_rate (external_observation_contract enforcement)
decision: **mechanism_stable_candidate**
Checkpoint: see ab-causal-agf-cross-repo-checkpoint-2026-05-15.json

| arm_id | arm_type | seed | A_rate | B_rate | abs_delta | result |
|---|---|---:|---:|---:|---:|---|
| cr-agf-arm-1-s350101 | baseline-strict | 350101 | 16.0 | 0.0 | -16.0 | pass |
| cr-agf-arm-1-s350102 | baseline-strict | 350102 | 12.0 | 0.0 | -12.0 | pass |
| cr-agf-arm-1-s350103 | baseline-strict | 350103 | 20.0 | 0.0 | -20.0 | pass |
| cr-agf-arm-2-s350101 | one-cause-one-fix | 350101 | 16.0 | 8.0 | -8.0 | pass |
| cr-agf-arm-2-s350102 | one-cause-one-fix | 350102 | 12.0 | 6.0 | -6.0 | pass |
| cr-agf-arm-2-s350103 | one-cause-one-fix | 350103 | 20.0 | 10.0 | -10.0 | pass |

## Metric

- A_rate = ungoverned_violation_count × scale_factor (violations present in raw input)
- B_rate = governed_remaining_violations × scale_factor (violations not caught by governance)
- Governed violations include:
  - V1=forbidden field 'verdict'
  - V2=forbidden field 'gate_verdict'
  - V3=forbidden field 'closure_verified'
  - V4=confidence_level=high without evidence_refs (arm-1 only)
  - V5=forbidden field 'promote_eligible'

## Arm Differentiation

- arm-1 (baseline-strict, confidence_strict_mode=True): enforces all V1-V5
  → B_rate=0.0 for all seeds (all violations caught)
- arm-2 (one-cause-one-fix, confidence_strict_mode=False): enforces V1/V2/V3/V5 only
  → B_rate>0 for all seeds (V4 violations survive governance)
- arm-2 is detectable: B_rate differs from arm-1 (V4 violations remain)
- Both arms pass (abs_delta < -1.5) — arm-2 shows partial governance effect

## Cross-Repo Replication Status

This is the 3rd repo in the cross-repo replication sequence:
- Repo A (gl-electron-tool): threshold_dependent_persists
- Repo B (financial-pdf-reader): mechanism_stable_candidate (all layers)
- Repo C (ai-governance-framework): **mechanism_stable_candidate**

With 2 of 3 repos reaching mechanism_stable_candidate (arm-1 strict baseline),
the global claim upgrade prerequisite is satisfied for arm-1.
arm-2 causal differentiation is NOW detectable in this repo.

## Claim Boundary (Per Protocol)

Allowed: "Current AI governance effect is observable but condition-dependent."
Disallowed: "Mechanism robustness confirmed" / "Generalized uplift proven"

Global claim upgrade requires review of cross-repo replication evidence.
