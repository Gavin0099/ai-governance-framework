# Mainline Risk R1: Callback Lifecycle Contract (Draft v0.1)

As-of: 2026-05-15  
Scope: runtime lifecycle authority for async callback flows  
Status: draft-for-implementation

## 1) Purpose

Define callback authority over time so runtime can survive async races (`cancel`, `unplug`, `window-close`, `timeout`) without stale callback side effects.

Primary objective:
- prevent callback execution after authority is revoked
- preserve runtime survivability under partial failure
- keep decisions reviewer-auditable

## 2) Core Model

Lifecycle authority is bound to `session_id` (opaque), not pointer-like identity.

Authority tuple:
- `session_id`
- `state`
- `owner_scope` (ui/window/runtime/service)
- `revocation_reason` (if revoked)
- `generation` (monotonic token for stale-callback rejection)

## 3) State Machine

States:
1. `CREATED`
2. `ACTIVE`
3. `CANCEL_PENDING`
4. `UNPLUG_PENDING`
5. `CLOSED_PENDING`
6. `COMPLETING`
7. `COMPLETED` (terminal)
8. `CANCELLED` (terminal)
9. `ABORTED_UNPLUG` (terminal)
10. `CLOSED` (terminal)
11. `TIMED_OUT` (terminal)

Rules:
- Terminal states are irreversible.
- Any callback entering with stale `generation` is dropped (`CALLBACK_STALE_GENERATION`).
- Transition to terminal state revokes callback authority immediately.

## 4) Event Priority (Conflict Resolution)

When multiple events race on same `session_id`, resolve by priority:

1. `UNPLUG`
2. `WINDOW_CLOSE`
3. `CANCEL`
4. `TIMEOUT`
5. `NORMAL_COMPLETE`

Interpretation:
- `UNPLUG` dominates because hardware presence invalidates operation legitimacy.
- `WINDOW_CLOSE` revokes UI authority even if runtime still alive.
- `CANCEL` revokes requested operation authority.
- `TIMEOUT` is fallback revocation when no stronger event observed.

## 5) Transition Contract

Allowed transitions (minimum set):
- `CREATED -> ACTIVE`
- `ACTIVE -> CANCEL_PENDING -> CANCELLED`
- `ACTIVE -> UNPLUG_PENDING -> ABORTED_UNPLUG`
- `ACTIVE -> CLOSED_PENDING -> CLOSED`
- `ACTIVE -> COMPLETING -> COMPLETED`
- `ACTIVE -> TIMED_OUT`

Illegal transitions:
- any `terminal -> non-terminal`
- `CANCELLED -> COMPLETED`
- `ABORTED_UNPLUG -> COMPLETED`
- `CLOSED -> COMPLETED`

On illegal transition attempt:
- no state mutation
- emit `LIFECYCLE_ILLEGAL_TRANSITION`
- return fail-closed result to caller

## 6) Callback Legality Matrix

Callback categories:
- `progress_callback`
- `completion_callback`
- `error_callback`
- `cleanup_callback`

Legality by state:
- `ACTIVE`: progress/error allowed
- `COMPLETING`: completion/error/cleanup allowed
- `CANCEL_PENDING|UNPLUG_PENDING|CLOSED_PENDING`: error/cleanup allowed, progress disallowed
- terminal states: only idempotent cleanup allowed

Disallowed callback handling:
- reject execution
- emit `CALLBACK_AUTHORITY_REVOKED`
- append runtime observation event

## 7) Revocation Semantics

Revocation must be explicit:
- set `revoked=true`
- set `revocation_reason`
- increment `generation`
- invalidate outstanding callback tickets

Required reason codes:
- `REVOKED_BY_UNPLUG`
- `REVOKED_BY_WINDOW_CLOSE`
- `REVOKED_BY_CANCEL`
- `REVOKED_BY_TIMEOUT`
- `REVOKED_BY_TERMINAL_TRANSITION`

## 8) Idempotency + Survivability

Runtime must tolerate duplicate/late signals:
- duplicate cancel/unplug/window-close are no-op after terminal
- cleanup callback must be idempotent
- timeout after terminal is ignored with observation log only

No panic/crash path allowed for lifecycle races.

## 9) Observability Contract (Reviewer-Facing)

Emit structured event for each lifecycle decision:
- `event_time`
- `session_id`
- `state_before`
- `event`
- `priority_rank`
- `state_after`
- `authority_valid` (bool)
- `reason_code`
- `dropped_callback_count`

Minimum metrics:
- `stale_callback_drop_rate`
- `illegal_transition_count`
- `terminal_after_revocation_callback_count`

## 10) Non-Goals (R1)

- no new governance gate
- no policy expansion
- no semantic correctness auto-judgement
- no pointer identity exposure to UI

## 11) Implementation Checklist

1. Add lifecycle state enum + transition guard.
2. Add priority resolver for concurrent events.
3. Bind callback tickets to `session_id + generation`.
4. Add revoke-and-invalidate primitive.
5. Add structured lifecycle observation events.
6. Add race tests:
   - cancel vs complete
   - unplug vs complete
   - window-close vs progress
   - timeout vs cancel
7. Add replay test ensuring terminal irreversibility.

## 12) Exit Criteria (R1 Done)

R1 is complete when:
- all illegal transition tests fail-closed
- stale callbacks are rejected deterministically
- event priority outcomes are deterministic and replayable
- no callback mutates state after terminal transition
