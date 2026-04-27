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
4. `resolved`
5. `invalidated`
6. `archived`

Definitions:
- `created`: artifact emitted, not yet consumed by release/promotion surfaces.
- `active`: current authority context for escalation/release decisions.
- `superseded`: replaced by a newer authority artifact for same escalation.
- `resolved`: escalation closure accepted under current authority policy.
- `invalidated`: authority no longer legitimate under current policy context
  (coverage-era shift, stale forced routing, contradictory evidence, or trust breach).
- `archived`: retained for audit only; no decision authority.

---

## State Transition Rules

Allowed transitions:
- `created -> active`
- `active -> superseded`
- `active -> resolved`
- `active -> invalidated`
- `superseded -> archived`
- `resolved -> archived`
- `invalidated -> archived`

Forbidden transitions:
- any transition from `archived` back to authoritative states
- `resolved -> active` without explicit reopen artifact
- `superseded -> active`

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
- `resolved`
- `archived`

Required semantics:
- `active`: participates in normal authority validation and block reasons.
- `invalidated`: must force release block with explicit reason set.
- `resolved` / `superseded` / `archived`: must not independently block release.

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

`resolved` means:
- authority obligations for this escalation are complete under current policy
- release decisions no longer block on this escalation authority artifact

`archived` means:
- preserved for forensic/audit replay only
- excluded from release blocking and promotion gating inputs

---

## Consumer Requirements

Consumers (release surface and promotion path) must:
1. evaluate only lifecycle-active authority records as authoritative inputs
2. ignore superseded/resolved/archived records for blocking decisions
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

