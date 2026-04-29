# A/B Round 2B Live Attempt Review (USB Only)

## Scope

Run ID: `2026-04-29-round2b-live-002-usb-single-session`

Target:

- `usb-hub-contract`

## Execution Order Check

Applied order:

1. execution parity
2. prompt lock
3. live behavior capture
4. artifact derivation
5. reviewer summary
6. bounded claim

## Parity Gate

Artifact:

- `artifacts/ab-live/2026-04-29-round2b-live-002-usb-single-session/usb-hub-contract/execution-parity.json`

Result:

- `parity_ok=false`
- key blocker: `memory_carryover_absent=false`

## Live Capture Output

Per-task raw evidence exists for both groups:

- `group-a/task-01..04/`
- `group-b/task-01..04/`

Each task folder includes:

- `raw_prompt.txt`
- `raw_agent_response.md`
- `actions.log`
- `files_changed.txt`
- `tests.log`
- `validator-output.json`
- `task-result.json`

## Claim Boundary

This run provides a captured single-session A/B evidence package,
but does **not** satisfy the dual fresh-session parity requirement.

Status:

- live behavior evidence: `captured_with_parity_block`
- live A/B claim: `not supported`

## Next Step

Re-run same target with dual fresh-session operator flow to satisfy:

- `memory_carryover_absent=true`
- `parity_ok=true`
