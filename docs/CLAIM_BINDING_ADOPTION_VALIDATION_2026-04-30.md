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
