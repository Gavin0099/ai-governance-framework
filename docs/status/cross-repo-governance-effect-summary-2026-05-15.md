# Cross-Repo Governance Effect Summary (2026-05-15)

As-of: 2026-05-15  
Scope: `gl_electron_tool`, `financial-pdf-reader`, `ai-governance-framework`

## Consolidated Claim

`AI governance effect is reproducible across three repos under defined, condition-dependent validation paths.`

## Non-Upgrade Boundary

Not allowed:
- `governance universally works`
- `universal semantic correctness proven`
- `generalized robustness proven for all task topologies`

## Repo Execution + Results

| repo | command | key result | evidence type | unsupported |
|---|---|---|---|---:|
| financial-pdf-reader | `python governance_harness.py --run-full` | Layer2/Layer3 pass, bridge valid, decision `mechanism_stable_candidate` | negative-path equivalence, transfer smoke equivalence, holdout equivalence, synthetic-real bridge | 0 |
| ai-governance-framework | `python governance_harness.py` | arm1=3/3, arm2=3/3, `arm2_detectable=true`, decision `mechanism_stable_candidate` | negative-path equivalence, transfer smoke equivalence, holdout reproducibility | 0 |
| gl_electron_tool | `npm test -- firmwareUpdateService.test.js` | 62/62 pass (r46/r47/r1.2 slices included) | runtime negative-path, transfer/holdout family, IPC authority hardening verification | 0 |

## Evidence Interpretation

1. Cross-repo reproducibility is supported at bounded claim strength.
2. Effect remains condition-dependent by topology and runtime context.
3. Evidence supports runtime authority discipline and fail-closed behavior, not universal semantic correctness.

## Referenced Status Pages

- `ab-causal-r48-cross-repo-consolidated-status-2026-05-15.md`
- `ab-causal-r48b-negative-path-equivalence-status-2026-05-15.md` (per repo)
- `ab-causal-r48c-transfer-smoke-equivalence-status-2026-05-15.md` (per repo)
- `ab-causal-r48d-holdout-equivalence-status-2026-05-15.md` (per repo)
