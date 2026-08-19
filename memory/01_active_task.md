<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-19 on `feat/gate3-historical-materialization`. A
> point-in-time summary, not canonical memory, and not evidence that anything
> below was re-verified today.
>
> **No branch head and no commit count are written here.** Both go stale on the
> next commit — including the one correcting them, which is how two revisions of
> this file were wrong on landing. `origin/main..HEAD` is the authority.
>
> **Cleaned up 2026-08-19 to return this file to `SAFE`** from 171 lines and
> 9575 characters. The checkpoint table and per-tranche narrative are preserved
> in `memory/04_review_log.md`, `PLAN.md` and the commit messages. Nothing
> append-only was rewritten. Corrected claims are marked below.

## Current Focus

- Gate 3 native directory-handle boundary. The Windows stdlib cannot bind a
  directory ancestor on this interpreter, so an ancestor swapped for a junction
  between check and use cannot be excluded by stdlib means. Built in separately
  authorized tranches, each reviewed at exact digests before it is committed.
- The consumed Gate 3 A/B pair is `NON_SUCCESS` and cannot be reused, retried or
  replaced. Credentials, preflight and live remain unauthorized.
- F-7's update-available truth correction is complete and inactive. No further
  F-7 expansion without a new observed consumer failure.

## Where The Work Is

Twenty tranches are merged to `main` as `5204cd18` — M1 through M3-a, including
the native boundary N1/N2/N3a/N3b/N3c-1/N3c-2, the held-handle read, and M2.
`PLAN.md` carries them as milestone entries and `memory/04_review_log.md` carries
their reviews; neither is repeated here.

**The feature branch is pushed and nothing on it is merged.** `origin/main` is
unchanged at `5204cd18`, no pull request is open, and a reader taking state from
`main` alone stops at M3-a. The unmerged range is `origin/main..HEAD`; its size
is whatever Git says when the pull request is opened.

The substantive tranches in that range — **not** the whole of it, since record
and cleanup commits sit alongside them unlisted:

| Tranche | Commit |
| --- | --- |
| M3-b design, and its three refused amendments | `8a8dbc2c` |
| M3-b design revision 6 | `70d62fd1` |
| M3-b-1 closed loader and return frame | `cfa2c1ec` |
| M3-b-1 module-audit opt-out fix | `80b2a74c` |
| BLOCKED-1 amendment, allowlist widened to five | `fa10dda8` |
| BLOCKED-2 amendment, two verifier checks retired | `4ea55d3e` |
| BLOCKED-3 process-control design slice | `95838ac0` |

Merge history: PR #72 `5d184ee6`, #73 `d7d5485c`, #75 `5204cd18`; #74 was
another agent's work, merged only to clear BEHIND.

## Paused And Blocked

- **B-1**, the structural non-`repr` boundary, is
  `CHANGES_REQUESTED / PAUSED_BEHIND_M4`: five files preserved complete and
  unstaged — `gate3_private_rendering.py`, its tests, and the wiring in
  `gate3_route_v2.py`, `gate3_route_v2_codex.py` and
  `gate3_final_message_runner_integration.py`. Its construction-contract blockers
  are fixed; what blocks it is that changing the first two breaks the source pin
  the historical candidate is verified against.
- **BLOCKED-1 and BLOCKED-2 are resolved by amendment** (`fa10dda8`,
  `4ea55d3e`), under explicit human authorization. M3-b-3 therefore has a defined
  callee and a defined verification contract, and needs only to be written and
  reviewed. It owns the parent-side result object and the two "not asserted"
  markers, which the BLOCKED-2 amendment requires and does not build.
- **BLOCKED-3 is written and still open** (`95838ac0`). No authorization closes
  it — it asked for a design slice, not an amendment. Ownership, the unwind
  matrix and error translation are closed; **the layouts are not**, because the
  oracle needs a digest-pinned SDK package absent here and the offsets will not
  be written from recollection. It closes when the slice is accepted **and** that
  artifact exists. M3-b-2 does not begin before then.
- **How the child receives the materialized root is unresolved.** argv, the
  environment and the inbound frame have no field for it. Recorded in the code
  as an open dependency rather than defaulted.
- Nothing is wired to M2, M3-a or M3-b-1. `materialize()` and `cleanup()` refuse
  while `handle_boundary_available()` is `False`; `ACTIVE` is `False` and nothing
  calls in. M2's verification is still not entirely handle-bound: the
  enumeration remains a path walk.
- **M4 is not started.** Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. Review the three blocker commits at exact digests. Two are amendments and must
   be read as amendments, not as diffs.
2. **BLOCKED-3's remaining half.** Obtain the pinned SDK package `f8787b2f…`,
   extend `gate3_native_expected_layout_extract.py` by the seven process-control
   types, regenerate `gate3-native-expected-layout.json`, commit it with its
   extractor digest. Only then may the `ctypes` structures be declared.
3. **M3-b-3**, the tranche actually unblocked.
4. **M3-b-2**, after step 2 lands and the slice is accepted.
5. Answer how the child receives the materialized root before either needs it.
   The runner's trust root stays an accepted assumption of M3.
6. M4: the historical candidate verified against materialized historical bytes
   instead of the live worktree.
7. B-1 re-review and delivery, once M4 removes the dependency its edits break.

## Open Risks

- Session binding is unrepaired: no envelope exists under
  `artifacts/runtime/sessions/` for the active `session_id`, so every
  `session_end` firing fails closed before any field is evaluated and appends one
  more record. `memory/2026-08-16.md` grows for that reason alone.
- The closeout parser is line-oriented — `_parse_fields` partitions on the first
  colon, so a key whose body starts on the next line parses as empty. Diagnosed;
  the closeout file was reformatted, the parser was not changed.
- `03_knowledge_base.md` states a 14-day `PLAN.md` freshness threshold while
  `governance_tools.plan_freshness` reports `Policy = Sprint (7d)`. Unreconciled.
- The historical candidate is verified by comparing live worktree bytes against
  `SOURCE_COMMIT`, so any slice touching `gate3_route_v2.py` or
  `gate3_route_v2_codex.py` breaks it. B-1 is the first, not the last; M4 fixes
  it.

## Claim Ceiling

- Cannot claim Gate 3 success, treatment effect, or Skill effectiveness.
- Cannot claim the native boundary is reachable: `handle_boundary_available()`
  and `ACTIVE` are both `False`, so no production path reaches it. **Corrected
  twice:** this said no committed tranche creates, renames or deletes a
  filesystem object, untrue since `495fe52f` (N3c-2); the replacement then
  over-claimed the other way, since N3c-2 also touches objects it did not create.
  Accurately, and separating the two: **every object N3c-2 creates, writes,
  mark-deletes or deletes is one it created itself; the borrowed `base` and its
  ancestors are only opened, pinned and revalidated, never created, marked or
  deleted by the boundary.**
- Cannot treat accepted design bytes as an implementation, or exact-digest review
  approval as runtime evidence.
- Cannot claim any committed tranche executes, spawns, compiles or imports
  historical code.
- **Corrected:** the mutation boundary was drawn one commit too early. The final
  M3-b-1 state, `80b2a74c`, does carry `36 declared / 36 valid / survivors none`.
  What is true of it is that the evidence **cannot be re-run**: the harness was
  session-local and is not in the repository. The boundary is therefore
  `fa10dda8` — the allowlist widening and everything after it carry **no**
  mutation evidence.
- Cannot claim a real consumer was updated or adopted, or that report-only
  behavior is enforcement.
- Cannot claim the workspace is clean; it is NOT CLEAN by design here.
