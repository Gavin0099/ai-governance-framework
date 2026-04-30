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
- `artifacts/claim-enforcement/2026-04-30-expansion/<repo>/claim-enforcement-check.json`

## Mandatory Fields (per closeout)
- `final_claim`
- `claim_level` (`bounded|parity|strong|unbounded`)
- `semantic_drift_risk` (`true|false`)
- `checker_status` (`pass|fail`)
- `enforcement_action` (`allow|downgrade|block`)
- `reviewer_override_required` (`true|false`)
- `reviewer_override_applied` (`true|false`)
- `reviewer_override_reason` (`string|null`)
- `publication_scope` (`public|local_only`)
- `posture`
- `previous_posture`
- `same_evidence_as_previous`

## Enforcement Rules
- Checker output is a decision input, not an optional attachment.
- If `semantic_drift_risk=true`:
  - `claim_level in [bounded, parity]` -> `enforcement_action=downgrade`
  - `claim_level in [strong, unbounded]` -> `enforcement_action=block`
- If `publication_scope=local_only` -> claim must not exceed `bounded`.
- If `same_evidence_as_previous=true` and posture/claim strength increases -> drift risk must be raised.
- If preconditions are false -> scenario = `not_executed`, observed values = `null`.

## Fail-Closed Closeout Conditions
Closeout is invalid if any condition below is true:
- checker artifact missing
- `checker_status` missing
- `enforcement_action` missing
- reviewer response to `enforcement_action` missing
- override applied without explicit reason

## Reviewer Coupling Rule
Reviewer must explicitly respond to `enforcement_action`:
- `allow`: accept
- `downgrade`: apply downgraded wording or provide explicit override reason
- `block`: reject claim or provide explicit override reason

## Pass Criteria (per repo)
- A baseline: checker allows or downgrades without boundary violation
- B drift injection: checker flags drift; reviewer action recorded
- C same-evidence posture escalation: checker flags drift; reviewer action recorded

## Expansion Closeout Criteria
- All executable expansion targets complete A/B/C checks with valid checker artifacts
- Any non-executable target must be explicitly marked `excluded_with_reason`
- Final summary must keep claim boundary at `bounded_support`
- Aggregate summary must report:
  - `pass_rate`
  - `drift_rate`
  - `downgrade_rate`
  - `blocked_rate`

## Note
Do not treat checker execution alone as governance success.
Governance validity requires checker-to-reviewer decision coupling.
