# AB Causal r48c Transfer Smoke Equivalence Status (2026-05-15)

As-of: 2026-05-15  
Repo: ai-governance-framework  
Mode: equivalence validation (no policy expansion)

## Objective

Validate r46-equivalent transfer smoke behavior.

## Result

- status: pass
- decision: mechanism_stable_candidate
- arm2_detectable: true (`confidence_strict_mode=False` produces non-zero governed B_rate)

## Key Checks

- transfer effect observability: pass
- unsupported_count: 0
- policy semantics unchanged: pass

## Artifacts

- status: `ab-causal-agf-cross-repo-status-2026-05-15.md`
- checkpoint: `ab-causal-agf-cross-repo-checkpoint-2026-05-15.json`
- run command: `python governance_harness.py`
