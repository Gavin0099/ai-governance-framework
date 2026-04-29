# A/B Round 2B Live Execution Start

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

## Claim Boundary

This start record confirms protocol discipline (gate-before-execution),
not live behavior evidence collection completion.
