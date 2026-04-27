# E1B Trust Root Maturity v0.1 (2026-04-27)

This note records the current trust-root maturity status to avoid false
completion claims.

## Current Status

- authority writer monopoly: achieved
- authority artifact tamper detection: achieved
- release surface fail-closed: achieved
- promotion path provided-assessment authority gate: achieved
- log/register detection redundancy: achieved v0.1
- mandatory register enforcement: not yet
- legacy log strict rejection: not yet

## Boundary Clarifications

1. `legacy_only` is compatibility mode.
   Legacy log entries are tolerated for transition compatibility and do not
   imply full trust-root completion.

2. `register absent` currently falls back to log-only assessment.
   This is intentional for cross-repo migration safety, but means register is
   not yet mandatory trust root.

3. `register active + log missing` is now fail-closed.
   Result: `escalation_expected_missing` with `ok=False` and `release_blocked=True`.

## Transition Direction

- keep compatibility behavior for now (no abrupt repo breakage)
- publish migration criteria for mandatory register enforcement
- define timeline for strict rejection of legacy-only log integrity
