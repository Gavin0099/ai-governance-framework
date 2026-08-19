<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-19 against branch head `ff463f83`. This is a point-in-time
> task summary, not a canonical session-derived memory entry, and not evidence
> that any claim below was independently re-verified today.
>
> **Cleaned up 2026-08-19 to return this file to `SAFE`.** It had reached 171
> lines and 9575 characters. What was removed is the twenty-eight-row checkpoint
> table and the per-tranche narrative; both are preserved unchanged in
> `memory/04_review_log.md`, in `PLAN.md`'s milestone entries, and in the commit
> messages themselves. Nothing append-only was rewritten. Two claims were
> corrected rather than shortened, and they are marked below.

## Current Focus

- Gate 3 native directory-handle boundary. The Windows standard library cannot
  bind a directory ancestor on this interpreter, so an ancestor swapped for a
  junction between check and use cannot be excluded by stdlib means. The
  boundary is built in separately authorized tranches, each reviewed at exact
  digests before it is committed.
- The consumed Gate 3 A/B pair is `NON_SUCCESS` and cannot be reused, retried or
  replaced. Credentials, preflight and live remain unauthorized.
- F-7's update-available truth correction is complete and inactive. No further
  F-7 expansion without a new observed consumer failure.

## Where The Work Is

Twenty tranches are merged to `main` as `5204cd18` — M1 through M3-a, including
the native boundary N1/N2/N3a/N3b/N3c-1/N3c-2, the held-handle read, and M2.
`PLAN.md` carries them as milestone entries and `memory/04_review_log.md` carries
their reviews; neither is repeated here.

**Ten commits are ahead of `main` and none are merged.** They are pushed to
`feat/gate3-historical-materialization` at `ff463f83`, local and upstream `0/0`,
`origin/main` unchanged. No pull request is open. A reader taking state from
`main` alone stops at M3-a.

| Ahead of `main` | Commit |
| --- | --- |
| M3-b design, and its three refused amendments | `8a8dbc2c` |
| M3-b design revision 6 | `70d62fd1` |
| M3-b-1 closed loader and return frame | `cfa2c1ec` |
| M3-b-1 module-audit opt-out fix | `80b2a74c` |
| BLOCKED-1 amendment, allowlist widened to five | `fa10dda8` |
| BLOCKED-2 amendment, two verifier checks retired | `4ea55d3e` |
| BLOCKED-3 process-control design slice | `95838ac0` |

plus three record commits: `62da7b6f`, `09597ace`, `ff463f83`.

Merge history: PR #72 `5d184ee6`, PR #73 `d7d5485c`, PR #75 `5204cd18`. PR #74
was another agent's work, taken only to clear BEHIND.

## Paused And Blocked

- **B-1**, the structural non-`repr` boundary, is
  `CHANGES_REQUESTED / PAUSED_BEHIND_M4`: five files preserved complete and
  unstaged — `gate3_private_rendering.py`, its tests, and the wiring in
  `gate3_route_v2.py`, `gate3_route_v2_codex.py` and
  `gate3_final_message_runner_integration.py`. Its construction-contract
  blockers are fixed; what blocks it is that changing the first two files breaks
  the source pin the historical candidate is verified against.
- **BLOCKED-1 and BLOCKED-2 are resolved by amendment** (`fa10dda8`,
  `4ea55d3e`), under explicit human authorization. M3-b-3 therefore has both a
  defined callee and a defined verification contract, and needs only to be
  written and reviewed. It owns the parent-side result object and the two
  "not asserted" markers, which the BLOCKED-2 amendment requires and does not
  build.
- **BLOCKED-3 is written and still open** (`95838ac0`). No authorization closes
  it — it asked for a design slice, not an amendment. Ownership, the unwind
  matrix and error translation are closed; **the layouts are not**, because the
  oracle needs a digest-pinned SDK package absent from this environment and the
  offsets will not be written from recollection. It closes when the slice is
  accepted **and** that artifact exists. M3-b-2 does not begin before then.
- **How the child receives the materialized root is unresolved.** argv, the
  environment and the inbound frame have no field for it. Recorded in the code
  as an open dependency rather than defaulted.
- Nothing is wired to M2, M3-a or M3-b-1. `materialize()` and `cleanup()` refuse
  while `handle_boundary_available()` is `False`; `ACTIVE` is `False` and nothing
  calls in. M2's verification is still not entirely handle-bound: the
  enumeration remains a path walk.
- **M4 is not started.** Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. Review the three blocker commits at exact digests. Two are amendments and
   must be read as amendments, not as diffs.
2. **BLOCKED-3's remaining half.** Obtain the pinned SDK package at
   `f8787b2f…`, extend `gate3_native_expected_layout_extract.py` by the seven
   process-control types, regenerate `gate3-native-expected-layout.json`, commit
   it with its extractor digest. Only then may the `ctypes` structures be
   declared.
3. **M3-b-3**, the tranche actually unblocked.
4. **M3-b-2**, after step 2 lands and the slice is accepted.
5. Answer how the child receives the materialized root before either tranche
   needs it. The runner's trust root stays an accepted assumption of M3 and must
   not be restated as solved.
6. M4: the historical candidate verified against materialized historical bytes
   instead of against the live worktree.
7. B-1 five-file re-review and delivery, once M4 removes the dependency its
   edits break.

## Open Risks

- Session binding is unrepaired: no envelope exists under
  `artifacts/runtime/sessions/` for the active `session_id`, so every
  `session_end` firing fails closed before any field is evaluated and appends one
  more record. `memory/2026-08-16.md` grows for that reason alone.
- The closeout parser is line-oriented — `_parse_fields` partitions on the first
  colon, so a key whose body starts on the next line parses as empty. Diagnosed;
  the closeout file was reformatted to match and the parser was not changed.
- `03_knowledge_base.md` states a 14-day `PLAN.md` freshness threshold while
  `governance_tools.plan_freshness` reports `Policy = Sprint (7d)`. Observed, not
  reconciled.
- The historical candidate is verified by comparing live worktree bytes against
  `SOURCE_COMMIT`. Any slice touching `gate3_route_v2.py` or
  `gate3_route_v2_codex.py` breaks that comparison. B-1 is the first and will not
  be the last; M4 is the intended fix.

## Claim Ceiling

- Cannot claim Gate 3 success, treatment effect, or Skill effectiveness.
- Cannot claim the native boundary is reachable: `handle_boundary_available()`
  and `ACTIVE` are both `False`, so no production path reaches it. **Corrected in
  cleanup:** this entry used to add that no committed tranche creates, renames or
  deletes a filesystem object. That stopped being true at `495fe52f` (N3c-2),
  which creates, writes, deletes and runs the absence probe. What remains true is
  narrower — every object it touches is one it created itself, under a `base`
  the caller supplies and this code never creates, deletes or marks.
- Cannot treat accepted design bytes as an implementation, or exact-digest review
  approval as runtime evidence.
- Cannot claim any committed tranche executes, spawns, compiles or imports
  historical code.
- **Corrected in cleanup:** M3-b-1's 36/36 zero-survivor mutation battery is real
  but **cannot be re-run** — the harness was session-local and is not in the
  repository. Nothing after `cfa2c1ec`, including the widened allowlist, carries
  mutation evidence.
- Cannot claim a real consumer was updated or adopted, or that report-only
  behavior is enforcement.
- Cannot claim the workspace is clean; it is NOT CLEAN by design here.
