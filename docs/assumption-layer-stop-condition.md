# Assumption Layer Stop Condition

## STOP CONDITION - Assumption Layer

Current baseline posture (2026-04-23):

- Mainline runtime profile is `advisory_mainline` (observation and advisory signals only).
- Experimental enforcement (`experimental_enforced`) is sandbox-only and must not be treated as baseline governance direction.

If after 3 months all of the following remain true:

- Assumption Layer does not consistently produce `A != B` behavior
- Wrong-assumption and destructive tests still default to direct execution
- Agent does not delay action or request evidence before implementation

Then:

- Accept that assumption validation is not solved at this layer
- Do NOT expand governance scope
- Do NOT add more enforcement or new governance modules
- Keep enforcement experiments behind explicit opt-in profile flags; no default-path hard blocking

Instead:

- Treat problem framing as human responsibility
- Keep governance focused on execution discipline

## Evaluation Window

- Start date: first committed rollout of `ASSUMPTION_AUDIT.md`
- End date: 3 calendar months later
- Required benchmark set: payload-premise + destructive-removal-premise

## Required Evidence For Continue Decision

At evaluation end, continue only if both are true:

- Stable `A != B` appears across repeated runs
- `B` shows process consequence (`need_more_info` or `reframe`) before implementation
