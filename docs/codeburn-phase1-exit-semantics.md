# CodeBurn Phase 1 Exit Semantics

Version: `v1.0.0`  
Applies to: `Script/codeburn_phase1_7day_summary.py`

## Status Definitions

### PASS
PASS requires all of the following:
- `daily_contract_validation=true`
- `activation_coverage_met=true`
- `runtime_validation_status=verified`

### NOT_READY
NOT_READY means required readiness conditions are not yet met, but no hard
contract break was detected.

Typical reasons:
- `insufficient_evidence`
- `activation_coverage_not_met`
- `runtime_validation_not_verified`
- `low_sample_window`

### FAIL
FAIL is reserved for contract or governance breakage, not for missing evidence.

Examples:
- schema corruption or required field missing
- guard field missing
- decision boundary widened
- `analysis_safe_for_decision` incorrectly set to true
- `decision_usage_allowed` incorrectly set to true

## Evidence Classification

The report should distinguish:
- no evidence
- insufficient evidence
- evidence present but not passing readiness
- system/contract breakage

`token_comparability_guard=false` does not automatically imply FAIL.
When evidence is absent or insufficient (for example empty DB, low sample, or
non-comparable token source), classify as NOT_READY with explicit reasons.
