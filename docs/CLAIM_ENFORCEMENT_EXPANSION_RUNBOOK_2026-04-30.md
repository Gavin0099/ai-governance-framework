# CLAIM_ENFORCEMENT Expansion Runbook (Post-Pilot)

Date: 2026-04-30
Entry condition: `pilot_status=pass`, `expansion_gate=open`

## Targets
1. `writing-contract`
2. `SpecAuthority` (only after origin remote is fixed)

## Required Preconditions (per repo)
- `docs/CLAIM_BOUNDARY.md` exists
- `docs/CLAIM_ENFORCEMENT_MINIMAL_SPEC.md` exists

## Required Output Files (per repo)
- `artifacts/claim-enforcement/2026-04-30-expansion/<repo>/closeout-baseline.json`
- `artifacts/claim-enforcement/2026-04-30-expansion/<repo>/closeout-drift-injection.json`
- `artifacts/claim-enforcement/2026-04-30-expansion/<repo>/closeout-same-evidence-posture.json`
- `artifacts/claim-enforcement/2026-04-30-expansion/<repo>/result-summary.md`

## Mandatory Fields (per closeout)
- `final_claim`
- `claim_level` (`bounded_support|stronger_than_allowed`)
- `semantic_drift_risk` (`true|false`)
- `posture`
- `previous_posture`
- `same_evidence_as_previous`

## Enforcement Rules
- If `claim_level != bounded_support` -> `semantic_drift_risk=true`
- If disallowed phrase appears -> `semantic_drift_risk=true`
- If `same_evidence_as_previous=true` and wording/posture is stronger -> `semantic_drift_risk=true`
- If preconditions are false -> scenario = `not_executed`, observed values = `null`

## Pass Criteria (per repo)
- A baseline: pass without drift flag
- B drift injection: correctly flagged
- C same-evidence posture escalation: correctly flagged

## Expansion Closeout Criteria
- All executable expansion targets pass A/B/C checks
- Any non-executable target must be explicitly marked `excluded_with_reason`
- Final summary must keep claim boundary at `bounded_support`
