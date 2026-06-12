# Structured Memory Freshness Policy

Status: policy v1, **policy-only** — no writer, hook, validator, or
automation change accompanies this document.
Scope: structured canonical memory files that act as authority surfaces,
primarily `memory/01_active_task.md`. Daily session-derived records
(`memory/YYYY-MM-DD.md`) are explicitly out of scope: they are
append-only evidence, not refreshable status surfaces, and are never
"stale" in this policy's sense.

Motivating evidence (2026-06-13): `memory/01_active_task.md` Current
Status ends at the P1-B era and its Next Steps still list "P1:
Structured memory freshness policy" as future work — while PLAN.md at
HEAD records P1-C through P1-I, the P2-A..G arc, and rollback
documentation as closed. The file is an authority surface actively
misleading any session that reads it first. This is the documented gap
the file itself predicted ("freshness, rollover, and PLAN consistency
are not yet automatically validated").

## 1. What counts as stale

Staleness is **event-driven contradiction, not age** (same boundary
class as P1-H fleet freshness: idle time alone proves nothing).

`memory/01_active_task.md` is stale when any of:

1. An item it presents as *current focus* or *next step* is recorded as
   closed in PLAN.md pending work (checkbox + evidence note) at HEAD.
2. A claim it presents as *active gap* has been closed by a canonical
   PLAN claim-boundary block.
3. A session closure record in daily memory (with
   `plan_reconciliation: updated`) supersedes its Current Status arc.

Observable test, no tooling required: compare its Next Steps list
against PLAN checkboxes; any "next" item already checked in PLAN is a
staleness signal.

Not staleness: being silent about work PLAN never tracked, idle periods,
or being shorter than PLAN. The file is a pointer surface, not a mirror.

## 2. Rollover policy

- `memory/01_active_task.md` is a **rewritable status surface**, unlike
  daily records (append-only evidence). Rewriting it is not history
  rewriting, because it is not the evidence chain — daily records are.
- Rollover is **event-driven**: the refresh trigger is a closed session
  arc (a session closure record exists) or a detected staleness signal
  under section 1. There is no scheduled refresh and no freshness SLA —
  rejecting ritual refresh for the same reasons P1-H rejected a weekly
  fleet scheduler.
- Historical Context section may be retained and compacted; compaction
  must not delete pointers to evidence (commits, artifact paths).

## 3. Who may repair, and from what

- Repair happens in a **dedicated bookkeeping slice** — never bundled
  into an implementation slice, and never done silently "while passing
  through".
- The repair source of truth is **PLAN.md at HEAD plus the latest
  session closure record**. Repair is derivation downstream of PLAN
  ("memory derived from PLAN, not ahead of it" — the existing
  reconciliation fixture field). An agent must not refresh the file from
  its own session narrative alone.
- The repair commit must carry a session-derived memory record with
  `plan_reconciliation` declared, binding the refresh to a commit.

## 4. Pre-repair comparison surfaces (mandatory)

Before rewriting, the repairing agent must compare against, and must not
introduce any claim absent from:

1. PLAN.md pending work and Active Claim Boundaries at HEAD.
2. The latest session closure record in daily memory.
3. The drift checker state (`severity=ok` expected before and after).

If PLAN and the closure record disagree, stop at diagnosis: that is a
PLAN reconciliation problem, not a memory refresh problem, and repairing
the memory file would launder the inconsistency.

## 5. Claim ceiling after repair

CAN claim:

- `memory/01_active_task.md` is consistent with PLAN.md as of commit X
  (point-in-time consistency, decaying event-driven thereafter).

CANNOT claim:

- Structured memory sync is "solved" (standing PLAN constraint: the
  daily writer's existence does not solve structured memory sync).
- Any automated freshness validation exists (none does; this policy is
  manually applied).
- That the refreshed file is itself evidence — it remains a pointer
  surface; evidence lives in daily records, PLAN, and artifacts.

## 6. PLAN-consistency checking: decided posture

- Now: **manual, event-driven comparison** under sections 1 and 4. This
  policy deliberately adds no tooling.
- Advisory tooling (e.g. a checker that flags closed-in-PLAN items still
  listed as next steps): **deferred, failure-driven** — build it only
  after this manual policy demonstrably fails or is repeatedly skipped.
- Blocking enforcement: a separate OP-HC-class decision with its own
  mutation contract (same class as P1-F). Not proposed here.

## 7. Follow-up boundary

Applying this policy to refresh the currently-stale
`memory/01_active_task.md` is a **separate follow-up slice**, gated on
this policy being canonical first. Policy definition and policy
application must not share a slice — otherwise the policy is being
written to legalize the repair that is already happening.
