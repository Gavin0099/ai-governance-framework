<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-17 against branch head `495fe52f`, using the `PLAN.md` in
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
| Memory reconciliation, 2026-08-13 to 2026-08-16 | `97ad42e4` |
| Current-session closeout in parser-readable form | `ec0c4046` |
| N3c-1 pinned ancestor chain | `1486fdb5` |
| Failure-attribution correction | `ed9d5d06` |
| Native-boundary test narrowed to a committed file | `4eafdb80` |
| N3c-2 design | `520cc306` |
| N3c-2 creation, deletion and absence probe | `495fe52f` |

All fifteen rows are pushed to
`origin/feat/gate3-historical-materialization`, whose head is `495fe52f` and
matches the local branch exactly — `0` ahead, `0` behind.

## Paused And Blocked

- **B-1**, the structural non-`repr` boundary, is
  `CHANGES_REQUESTED / PAUSED_BEHIND_M4`: five files preserved complete and
  unstaged, comprising `gate3_private_rendering.py`, its tests, and the wiring
  in `gate3_route_v2.py`, `gate3_route_v2_codex.py` and
  `gate3_final_message_runner_integration.py`. Its two construction-contract
  blockers are fixed; what blocks it is that changing the first two files
  breaks the source pin the historical candidate is verified against.
- **M2** read-only materialization is `CHANGES_REQUESTED` behind an interim
  fail-closed refusal; M3 and M4 are blocked behind it, and M2 itself cannot
  converge until N3c-2 exists.
- Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. M2 handle-bound rewrite: replace the eight path-based operations with
   `create_directory`, `create_file`, `remove` and `confirm_absent`; require
   `base` to pre-exist and drop `os.makedirs`; delete `_drop_name`,
   `_create_exclusively` and `stale_root`'s `lexists`. Keep `_contained`,
   scoped to `verify`.
2. M3, then M4. M4 is what lets a historical candidate be verified against
   materialized historical bytes instead of against the live worktree.
3. B-1 five-file re-review and delivery, once M4 removes the dependency its
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
