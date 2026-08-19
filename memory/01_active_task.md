<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-19 against branch head `5204cd18`, using the `PLAN.md` in
> this uncommitted reconciliation diff rather than the `PLAN.md` contained in
> the last commit. Source of truth: that reconciliation diff plus the exact-digest
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
| Memory reconciliation, 2026-08-13 to 2026-08-16 | `97ad42e4` |
| Current-session closeout in parser-readable form | `ec0c4046` |
| N3c-1 pinned ancestor chain | `1486fdb5` |
| Failure-attribution correction | `ed9d5d06` |
| Native-boundary test narrowed to a committed file | `4eafdb80` |
| N3c-2 design | `520cc306` |
| N3c-2 creation, deletion and absence probe | `495fe52f` |
| Held-handle read design amendment | `b7235036` |
| Held-handle read implementation | `6e7393e2` |
| M2 handle-bound materialization | `5a04ec79` |
| M3 design, and the revision 10 authority amendment | `a51cd4be` |
| M3-a framed transport | `daf4ec5e` |

All twenty rows are merged to `main`. The branch head is `5204cd18`, which is
`origin/main` itself: PR #75 merged the last two rows plus the milestone
reconciliation that preceded them, and the branch was then fast-forwarded onto
the result. `HEAD` equals `origin/main` and nothing is behind it. The feature
upstream is one commit further back, at `f2901eef`: the fast-forward moved the
local branch onto the merge commit and that has not been pushed to the feature
ref, so `HEAD` is ahead 1 / behind 0 against it.

Merge history for this work item: PR #72 as `5d184ee6`, PR #73 as `d7d5485c`,
PR #75 as `5204cd18`. PR #74 was another agent's work on
`docs/governance/trust-boundary-taxonomy.md` and reached this branch only as a
merge taken to clear BEHIND.

## Paused And Blocked

- **B-1**, the structural non-`repr` boundary, is
  `CHANGES_REQUESTED / PAUSED_BEHIND_M4`: five files preserved complete and
  unstaged, comprising `gate3_private_rendering.py`, its tests, and the wiring
  in `gate3_route_v2.py`, `gate3_route_v2_codex.py` and
  `gate3_final_message_runner_integration.py`. Its two construction-contract
  blockers are fixed; what blocks it is that changing the first two files
  breaks the source pin the historical candidate is verified against.
- **M3-b and M4** are not started. M3-b is the first tranche that executes
  historical code, and it needs its own design slice before any of it is
  written.
- Nothing is wired to M2 or to M3-a. `materialize()` and `cleanup()` refuse
  while `handle_boundary_available()` is `False`; the transport's `ACTIVE` is
  `False` and it has no caller. M2's verification is still not entirely
  handle-bound, because the enumeration remains a path walk.
- Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. Land this reconciliation before M3-b begins, so the record is not trailing
   the merged code at the moment historical execution starts.
2. M3-b, design first: the `-I -S -B` spawn, the closed loader over verified
   byte buffers, and the return channel. The child opens no materialized path
   through that loader; its expected inventory comes from a digest frozen in
   its own code, not from the stream and not from the active head. The runner's
   trust root is an accepted assumption of M3 and must not be quietly restated
   as solved.
3. M4: the historical candidate verified against materialized historical bytes
   instead of against the live worktree.
4. B-1 five-file re-review and delivery, once M4 removes the dependency its
   edits currently break.

## Open Risks

- `artifacts/session-closeout.txt` now describes the current session and parses
  cleanly, but session binding is still unrepaired: no envelope exists under
  `artifacts/runtime/sessions/` for this `session_id`, so every `session_end`
  firing fails closed before any field is evaluated and appends one more
  record. `memory/2026-08-16.md` keeps growing for that reason alone.
- The closeout parser is line-oriented: `_parse_fields` partitions each line on
  its first colon, so a key whose body starts on the next line parses as empty
  and is reported missing. That is diagnosed, and the closeout file was
  reformatted to match; the parser itself was not changed.
- `03_knowledge_base.md` states a 14-day `PLAN.md` freshness threshold, while
  `governance_tools.plan_freshness` reports `Policy = Sprint (7d)`. Observed,
  not reconciled here.
- The historical candidate is verified by comparing live worktree bytes against
  `SOURCE_COMMIT`. Any slice touching `gate3_route_v2.py` or
  `gate3_route_v2_codex.py` breaks that comparison; B-1 is the first to do so
  and will not be the last. M4 is the intended fix.

## Claim Ceiling

- Cannot claim Gate 3 success, treatment effect, or Skill effectiveness.
- Cannot claim the native boundary is reachable: `handle_boundary_available()`
  and `ACTIVE` are both `False`, so no production path reaches it. N3c-1 is
  committed and does open and hold directory handles; what no committed tranche
  does is create, rename or delete a filesystem object, or run the absence
  probe.
- Cannot treat accepted design bytes as an implementation, or exact-digest
  review approval as runtime evidence.
- Cannot claim that a real consumer was updated or fully adopted.
- Cannot claim that report-only behavior is enforcement.
- Cannot claim the workspace is clean; it is NOT CLEAN by design here.
