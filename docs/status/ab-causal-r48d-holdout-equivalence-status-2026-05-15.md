# AB Causal r48d Holdout Equivalence Status (2026-05-15)

As-of: 2026-05-15  
Repo: ai-governance-framework  
Mode: equivalence validation (no policy expansion)

## Objective

Validate r47-equivalent holdout reproducibility for fixed-seed cross-repo harness.

## Result

- status: pass
- seeds: 350101/350102/350103
- deterministic outcomes across same seed set

## Key Checks

- decision consistency by seed: pass
- unsupported_count: 0
- freeze boundary intact: pass

## Artifacts

- per-seed results: `ab-causal-cross-repo-agf-arm-*-s*-condition-break-result-2026-05-15.json`
- checkpoint: `ab-causal-agf-cross-repo-checkpoint-2026-05-15.json`
- run command: `python governance_harness.py`
