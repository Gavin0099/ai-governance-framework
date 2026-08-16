<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-16 against branch head `0d95023d`, using the `PLAN.md` in
> this uncommitted reconciliation diff rather than the `PLAN.md` contained in
> that commit. Source of truth: that reconciliation diff plus the exact-digest
> reviews recorded in it. This is a point-in-time task summary, not a canonical
> session-derived memory entry and not evidence that any claim below was
> independently re-verified today.

## Current Focus

- Gate 3 native directory-handle boundary. The Windows standard library cannot
  bind a directory ancestor on this interpreter, so an ancestor swapped for a
  junction between check and use cannot be excluded by stdlib means. The
  boundary is being built in separately authorized tranches, each one reviewed
  at exact digests before it is committed.
- The consumed Gate 3 A/B pair is `NON_SUCCESS` and cannot be reused, retried
  or replaced. Credentials, preflight and live remain unauthorized.
- The earlier F-7 update-available truth correction is complete and inactive.
  No further F-7 framework expansion is active without a new observed consumer
  failure.

## Completed Checkpoints

| Checkpoint | Commit |
| --- | --- |
| M1 bootstrap authority chain | `896bc64c` |
| Native boundary design, ADR-0001, ABI characterization | `1c78de39` |
| SDK expected-layout oracle | `c4c7e14e` |
| N1 ctypes declarations and expected-layout gate | `62c3488b` |
| N2 System32 loader and signature binding, no bound export called | `62c3488b` |
| N3a fail-fast exit | `ce43bb56` |
| N3b runtime facts | `8b04c2d8` |
| Design revision 17, access-mask amendment | `0d95023d` |

All seven are pushed to `origin/feat/gate3-historical-materialization`.

## Paused And Blocked

- **N3c-1** (pin the ancestor chain) is `PAUSED / CHANGES_REQUESTED`: written
  in the worktree, uncommitted and paused. It was executed locally only for the
  bounded submitter-reported access-mask probe, which opened a volume-root
  handle and observed `ERROR_ACCESS_DENIED`; no committed tranche opens a
  handle. Exact SHA-256
  `065f4fa76b37b8c2097850068926b2477164b2efefeb30cdf535368c19a1283a`. It still
  carries revision 16's role-1 access mask, and two reviewer-named defects are
  outstanding: `CloseHandle` is called outside `_guarded()`, and the
  `open_chain()` cleanup path can mask the original error with `CLOSE_FAILED`.
- **M2** read-only materialization is `CHANGES_REQUESTED` behind an interim
  fail-closed refusal; M3 and M4 are blocked behind it.
- **B-1** implementation is paused and preserved complete and unstaged.
- Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. Submit the memory reconciliation diff for review; do not stage, commit or
   push it beforehand.
2. Open the separate bounded closeout slice that produces a current-session
   closeout carrying all seven required fields, consistent with the
   session-bound candidate for the same `session_id`.
3. Resume N3c-1 only under new explicit owner authorization, applying revision
   17's role-1 mask and closing the two named defects.
4. N3c-2, which would create and delete real filesystem objects, needs its own
   authorization and has none.

## Open Risks

- `artifacts/session-closeout.txt` is a legacy shared closeout still describing
  a CP-8 session from 2026-05-30. Every `session_end` firing reads it, fails
  closed, and writes one canonical memory record. It is deliberately untouched
  by the memory reconciliation slice.
- The closeout checker reports `WORK_COMPLETED` as a missing required field
  even though the field is present with a multi-line body, which suggests the
  parser does not read multi-line field bodies. This is observed, not
  diagnosed, and no fix is claimed.

## Claim Ceiling

- Cannot claim Gate 3 success, treatment effect, or Skill effectiveness.
- Cannot claim the native boundary is reachable: `handle_boundary_available()`
  and `ACTIVE` are both `False`, and no committed tranche opens a handle,
  creates or deletes a filesystem object, or runs the absence probe.
- Cannot treat accepted design bytes as an implementation, or exact-digest
  review approval as runtime evidence.
- Cannot claim that a real consumer was updated or fully adopted.
- Cannot claim that report-only behavior is enforcement.
- Cannot claim the workspace is clean; it is NOT CLEAN by design here.
