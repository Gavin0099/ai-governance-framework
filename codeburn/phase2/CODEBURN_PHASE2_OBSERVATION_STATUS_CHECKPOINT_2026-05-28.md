# CodeBurn Phase 2 Observation Status Checkpoint (2026-05-28)

Purpose: consolidate current evidence into a decision checkpoint.

This checkpoint does not add new features and does not upgrade authority.

Boundary unchanged:
- analysis_safe_for_decision=false
- decision_usage_allowed=false
- Decision authority: none

## Scope Consolidated

1. Phase 1 boundary validator status
2. L0 manual ingest hardening status
3. Codex gap coverage calibration status
4. Copilot base smoke status
5. Known gaps
6. Allowed claims vs forbidden claims
7. README wording recommendation

## Evidence Summary

### 1) Phase 1 boundary validator

- Status: pass
- Evidence command:
  - `python codeburn/phase1/validate_phase1_data.py --db codeburn/phase1/examples/token_probe_sample.db --include-analysis --format json`
- Interpretation:
  - Phase 1 CLOSED boundary remains intact.
  - No evidence supports decision-authority upgrade.

### 2) L0 manual ingest hardening

- Status: completed (L0 path only)
- Evidence surfaces:
  - `codeburn/phase2/codeburn_manual_usage_ingest.py`
  - `codeburn/phase2/examples/manual_usage_fixture.json`
  - `codeburn/phase2/examples/manual_usage_batch_valid.json`
  - `codeburn/phase2/examples/manual_usage_batch_invalid_negative.json`
  - `codeburn/phase2/examples/manual_usage_batch_invalid_empty.json`
- Verified behavior:
  - single JSON object and JSON array input supported
  - deterministic validation
  - fail-whole-batch no-write behavior
- Explicit classification:
  - L0 Manual Batch Ingest Hardening: completed
  - Phase 2 Codex/Copilot calibration: unchanged by this step

### 3) Codex gap coverage calibration

- Status: completed for tested fixtures (classification-level)
- Evidence file:
  - `codeburn/phase2/CODEBURN_CODEX_GAP_COVERAGE_MAINLINE_2026-05-28.md`
- Consolidated interpretation:
  - Codex ingest path can deterministically classify tested local-session malformed/gap fixtures without crash.
  - This is not equivalent to provider-complete ingestion.

### 4) Copilot ingest status

- Status: base smoke verified
- Current position:
  - Base smoke path passed in prior calibration evidence.
  - Gap coverage expansion for Copilot is pending.

## Capability Status (Checkpoint)

- L0 manual ingest: hardened (single + batch JSON with fail-whole-batch validation)
- Codex ingest: tested gap fixtures classified (accepted/skipped/quarantined/warning-admitted)
- Copilot ingest: base smoke verified, gap calibration pending
- Decision authority: none

## Known Gaps (Explicit)

1. Codex `rate_limits` field-level validation is deferred.
2. Codex missing token stats remains warning-admitted (not clean fully-populated token evidence).
3. Copilot gap fixture expansion has not yet been executed.
4. Local artifact observation is not billing truth.

## Allowed Claims (Current)

- CodeBurn is an optional observation layer.
- L0 manual ingest is hardened for validated single/batch JSON input.
- Codex ingest is smoke-verified to classify tested local-session gap fixtures for analysis-only observation.
- Copilot base ingest smoke is verified for analysis-only observation under current tested fixture scope.

## Forbidden Claims (Current)

- CodeBurn is provider-complete.
- CodeBurn provides billing truth.
- CodeBurn can enforce budget gates.
- CodeBurn can rank agent efficiency for governance decisions.
- Smoke pass implies decision-safe authority.

## Decision

- Recommendation: Limited Proceed
- Rationale:
  - observation-layer evidence is sufficient for bounded analysis-only usage
  - known semantic/coverage gaps are explicitly documented
  - authority boundary remains unchanged

## README Wording Recommendation

Recommended wording:

`CodeBurn is an optional observation layer. L0 manual ingest is hardened for validated single/batch JSON input, and Codex/Copilot ingest paths are smoke-verified for analysis-only evidence collection under tested fixtures. Decision usage remains disabled.`

Optional strict addendum:

`Known limits: Codex rate_limits field-level validation and Copilot gap coverage remain deferred; local artifact observation is not billing truth.`

