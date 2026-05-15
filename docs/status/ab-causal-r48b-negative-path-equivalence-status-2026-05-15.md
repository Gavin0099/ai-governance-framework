# AB Causal r48b Negative-Path Equivalence Status (2026-05-15)

As-of: 2026-05-15  
Repo: ai-governance-framework  
Mode: equivalence validation (no policy expansion)

## Objective

Validate r45.4b-equivalent deny-path governance behavior.

## Result

- status: pass
- decision: mechanism_stable_candidate
- unsupported_count: 0

## Key Checks

- deny-path enforcement equivalence: pass
- fail-closed semantics preserved: pass
- reason-code semantics unchanged: pass

## Artifacts

- status: `ab-causal-agf-cross-repo-status-2026-05-15.md`
- checkpoint: `ab-causal-agf-cross-repo-checkpoint-2026-05-15.json`
- run command: `python governance_harness.py`
