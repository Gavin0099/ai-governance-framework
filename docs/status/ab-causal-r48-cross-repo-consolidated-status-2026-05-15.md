# AB Causal r48 Cross-Repo Consolidated Status (2026-05-15)

As-of: 2026-05-15  
Scope: consolidated interpretation for `gl_electron_tool`, `financial-pdf-reader`, `ai-governance-framework`

## Repo Summary

| repo | r48b negative-path | r48c transfer smoke | r48d holdout | unsupported | detectable | consolidated |
|---|---|---|---|---:|---|---|
| gl_electron_tool | pass (prior closure baseline via r45.4b family) | pass (topology-tagged transfer family) | pass (holdout transfer family) | 0 | topology-sensitive | authority boundary stable; runtime topology remains sensitive |
| financial-pdf-reader | pass | pass | mechanism_stable_candidate (3/3) | 0 | true | equivalence_confirmed |
| ai-governance-framework | pass | pass | pass (fixed-seed reproducibility) | 0 | true (arm2 differentiable) | equivalence_confirmed |

## Financial-PDF-Reader r48 Detail

- `r48b`: pass  
  - V1 observed_fact downgrade: pass  
  - V2 confidence cap: pass  
  - V3 forward-looking detect: pass  
  - V4 rhetorical flag: pass  
  - V5 attribution required: pass  
  - fail-closed: pass  
  - replay determinism: pass
- `r48c`: pass  
  - financial/operational no-intervention path: pass  
  - strategic_narrative attribution path: pass  
  - management_expectation attribution + confidence cap: pass  
  - detectable: true
- `r48d`: `mechanism_stable_candidate`  
  - seeds: `350201/350202/350203`  
  - deltas: `-20.0 / -16.0 / -20.0`  
  - pass_count: `3/3`  
  - suite_decision: `equivalence_confirmed`

## Consolidated Interpretation

1. Cross-repo evidence supports reproducible runtime authority discipline and negative-path stability under defined conditions.
2. Evidence remains heterogeneous by runtime topology and task structure.
3. Repo-level strong confirmations (`financial-pdf-reader`, `ai-governance-framework`) do not erase topology sensitivity signals from `gl_electron_tool`.

## Claim Boundary

Allowed:

- `Current AI governance effect is observable but condition-dependent.`
- `financial-pdf-reader and ai-governance-framework show r48 equivalence-confirmed behavior under fixed-rule constraints.`

Disallowed:

- `universal robustness confirmed`
- `semantic correctness generally solved across all repos`

## Next-Step Routing

1. `financial-pdf-reader`: stay in observation window (no policy expansion).
2. `ai-governance-framework`: keep semantic layer observation-only; continue taxonomy/invariant/hotspot surfaces.
3. `gl_electron_tool`: proceed with `R1.2-B` (compatibility shim hardening + cross-window replay authority tests).
