# Claim Binding Adoption Validation

## Goal
Validate that claim-enforcement outputs are actually reflected in reviewer decisions, not only generated as advisory artifacts.

## Scope
- Transition focus from governance runtime correctness to governance adoption evidence.
- Primary question: when `enforcement_action` is `downgrade` or `block`, do reviewer claims and final closeout decisions follow the gate?

## Mandatory Signals
Track these rates from `governance_tools/closeout_audit.py` outputs:
- `drift_rate`
- `downgrade_rate`
- `blocked_rate`
- `override_rate`
- `invalid_override_rate`

## Override Validity Contract
An override is valid only when `override_reason` includes at least one marker:
- `evidence_ref:`
- `risk_ack:`

Invalid examples:
- `looks fine`
- `seems okay`
- empty string

## Default-On Criteria for `--require-claim-binding`
Promote to CI default when all conditions remain true for at least one review window:
1. `drift_rate` is stable (no sustained upward trend in the selected window).
2. `override_rate` remains acceptable for the team baseline.
3. `invalid_override_rate` stays near zero.
4. No major reviewer friction is reported in the closeout notes.

If criteria fail, keep opt-in mode and publish a blocker note with measured causes.

## Pressure Test Protocol
1. Select 1-2 active repos.
2. Run closeout audit in require mode:
   - `python governance_tools/closeout_audit.py --project-root <repo> --require-claim-binding --format json`
3. Record outcomes:
   - number of claims downgraded
   - number of claims blocked
   - number of reviewer overrides
   - number of invalid overrides
4. Confirm whether reviewer final claim language actually changed after enforcement output.

## Decision Rule
A governance rule not enforced in reviewer decisions is advisory, not governance.

## Report Output Contract
Each adoption validation report must include:
- `governance_adoption_status=<insufficient_evidence|monitoring|default_on_ready>`
- `require_claim_binding_mode=<opt_in|default>`
- `observation_window_start=<YYYY-MM-DD>`
- `observation_window_end=<YYYY-MM-DD>`

Current expected status for repos without claim-binding artifacts:
- `governance_adoption_status=insufficient_evidence`
- `require_claim_binding_mode=opt_in`

## Next Validation Checklist (Executable)
1. Define observation window:
   - `observation_window_start: <YYYY-MM-DD>`
   - `observation_window_end: <YYYY-MM-DD>`
2. Ensure artifact generation exists per closeout:
   - `artifacts/claim-enforcement/**/claim-enforcement-check.json`
3. Ensure mandatory fields exist in each check:
   - `enforcement_action`
   - `reviewer_override_required`
   - `reviewer_response.decision`
   - `reviewer_response.override_reason`
4. Run require-mode audit for each target repo:
   - `python governance_tools/closeout_audit.py --project-root <repo> --require-claim-binding --format json`
5. Verify 5 rates are computable (not `null`):
   - `drift_rate`
   - `downgrade_rate`
   - `blocked_rate`
   - `override_rate`
   - `invalid_override_rate`
6. Re-evaluate default-on criteria and emit explicit decision:
   - `default_on_decision=<ready|not_ready>`
   - `blocker_note=<measured reason when not_ready>`
