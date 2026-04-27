# E1B Phase C — Authority Lifecycle Contract

> Purpose: define when authority is valid, when it expires, and when it must
> stop participating in release blocking.
>
> Scope: lifecycle semantics of escalation authority artifacts produced by the
> canonical authority writer path.

---

## Why Phase C Exists

Phase B established operational trust root semantics:
- who may emit authority artifacts
- how forged artifacts are detected and fail closed

Phase C addresses the missing half:
- when an authority artifact is still authoritative
- when it must be superseded, invalidated, or archived

Without lifecycle semantics, old authority can be misapplied as current
authority, causing either permanent blocking or false cleanliness.

---

## Lifecycle States

Canonical lifecycle states:
1. `created`
2. `active`
3. `superseded`
4. `resolved_provisional`
5. `resolved_confirmed`
6. `invalidated`
7. `archived`

Definitions:
- `created`: artifact emitted, not yet consumed by release/promotion surfaces.
- `active`: current authority context for escalation/release decisions.
- `superseded`: replaced by a newer authority artifact for same escalation.
- `resolved_provisional`: closure declared by authority writer path but not yet
  reviewer-confirmed; audit-visible but not release-unblocking.
- `resolved_confirmed`: reviewer-confirmed closure eligible to stop release
  blocking for this escalation.
- `invalidated`: authority no longer legitimate under current policy context
  (coverage-era shift, stale forced routing, contradictory evidence, or trust breach).
- `archived`: retained for audit only; no decision authority.

---

## State Transition Rules

Allowed transitions:
- `created -> active`
- `active -> superseded`
- `active -> resolved_provisional`
- `resolved_provisional -> resolved_confirmed`
- `active -> invalidated`
- `superseded -> archived`
- `resolved_provisional -> archived`
- `resolved_confirmed -> archived`
- `invalidated -> archived`

Forbidden transitions:
- any transition from `archived` back to authoritative states
- `resolved_provisional -> active` without explicit reopen artifact
- `resolved_confirmed -> active` without explicit reopen artifact
- `superseded -> active`
- `active -> resolved_confirmed` direct transition (must pass provisional state)

Reopen rule:
- reopening requires a new artifact (new provenance), not status mutation of
  archived/resolved artifact.

---

## Release Blocking Participation

Only these states participate in release blocking:
- `active`
- `invalidated`

Non-blocking (audit-only) states:
- `superseded`
- `resolved_provisional`
- `resolved_confirmed`
- `archived`

Required semantics:
- `active`: participates in normal authority validation and block reasons.
- `invalidated`: must force release block with explicit reason set.
- `resolved_provisional` / `superseded` / `archived`: must not independently
  block release and must not unblock release.
- `resolved_confirmed`: may end authority blocking for that escalation if no
  other active/invalidated authority records remain.

This prevents:
- once-blocked forever-blocked drift
- stale authority being interpreted as current authority

---

## Invalidation Triggers (minimum set)

An `active` artifact must transition to `invalidated` when any of the following
holds:
1. coverage-era mismatch invalidates protected claim legitimacy
2. forced routing becomes stale/overdue beyond policy tolerance
3. escalation marked closed elsewhere but authority artifact not lifecycle-cleared
4. contradictory trusted authority artifact exists for same escalation ID
5. provenance/trust check regression discovered post-write

All invalidations must carry:
- `invalidation_reason_code`
- `invalidation_evidence_refs`
- `invalidated_at`

---

## Supersession Rules

For the same `escalation_id`, at most one artifact may be `active`.

When a new authority artifact is accepted:
- old `active` becomes `superseded`
- new artifact becomes `active`

Supersession is monotonic:
- no "reactivate old artifact" path

---

## Resolver / Archiver Semantics

`resolved_provisional` means:
- closure is proposed, not final
- audit-visible status only
- release remains blocked until reviewer confirmation

`resolved_confirmed` means:
- authority obligations for this escalation are complete under current policy
- release may unblock for this escalation under consumer aggregation rules

`archived` means:
- preserved for forensic/audit replay only
- excluded from release blocking and promotion gating inputs

---

## Transition Authority Contract (Phase C Slice 1 minimum)

Transition authority is stricter than state shape.

Minimum required rules:
1. `resolved` must not directly unblock release.
   Only `resolved_confirmed` is release-unblocking.
2. `author_provisional` resolution is audit-only.
   It can produce `resolved_provisional` but cannot produce
   `resolved_confirmed`.
3. Auto-resolution to `resolved_confirmed` is forbidden.
   Reviewer-confirmed transition is required (`resolved_provisional ->
   resolved_confirmed`).

Operational mapping (current policy intent):
- `active -> resolved_provisional`: authority writer path allowed
- `resolved_provisional -> resolved_confirmed`: reviewer-confirmation required
- `active -> resolved_confirmed`: forbidden direct transition
- system automation may assist evidence collection, but not final confirmation

Until these transition-authority checks are runtime-enforced, Phase C Slice 1
is not complete.

---

## Consumer Requirements

Consumers (release surface and promotion path) must:
1. evaluate only lifecycle-active authority records as authoritative inputs
2. ignore superseded/resolved_confirmed/archived records for blocking decisions
   and treat `resolved_provisional` as non-unblocking audit state
3. fail closed if multiple `active` records exist for one escalation ID
4. fail closed if lifecycle metadata is missing on authority-required paths

---

## Phase C Deliverables (implementation targets)

1. Writer schema extension for lifecycle metadata (`lifecycle_state`,
   transition timestamps, reason refs).
2. Directory assessment update to compute per-escalation "current authority" by
   lifecycle state, not file presence only.
3. Replay tests for stale and superseded authority artifacts.
4. Migration path for pre-lifecycle artifacts (compatibility mode with explicit
   "not lifecycle-complete" disclosure).

---

## Status Declaration

Current repository state is:
- Trust Root Established (Operational) — Phase B
- Authority Lifecycle Contract Defined — Phase C design baseline
- Lifecycle runtime enforcement — not yet implemented

