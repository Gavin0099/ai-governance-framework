# A/B Round 2B Governance Falsification Attempt (Start)

## Scope

Run ID: `2026-04-29-round2b-live-001`

Targets:

- `nextjs-byok-contract`
- `usb-hub-contract`

## Gate Result

Execution parity gate evaluated first, as required.

Per-target parity artifacts:

- `artifacts/ab-live/2026-04-29-round2b-live-001/nextjs-byok-contract/execution-parity.json`
- `artifacts/ab-live/2026-04-29-round2b-live-001/usb-hub-contract/execution-parity.json`

Result:

- `parity_ok=false` for both targets
- primary failing condition: `memory_carryover_absent=false`

## Decision

- Round 2B live status: `execution_parity_failed`
- Live behavior evidence claim: `blocked`
- Live A/B claim: `not supported`

## Falsification Posture

Round 2B is a governance falsification attempt, not a success-validation run.

Reviewer must prioritize:

- weakest supported axis
- earliest falsification signal

before any overall posture statement.

Per-axis reviewer output must follow:

- `docs/ab-round2b-falsification-matrix.md`

## Claim Boundary

This start record confirms protocol discipline (gate-before-execution),
not live behavior evidence collection completion.
