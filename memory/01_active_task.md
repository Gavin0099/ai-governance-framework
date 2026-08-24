<!-- ARCHIVED: active_task_20260727_003214.md (2026-07-27 00:32:14) -->
<!-- Prior point-in-time snapshot: archive/active_task_20260727_003214.md -->

---

# Active Task

> Refreshed 2026-08-19, after PR #76 merged. A point-in-time summary, not
> canonical memory, and not evidence that anything below was re-verified today.
>
> **No branch head and no commit count are written here.** Both go stale on the
> next commit — including the one correcting them, which is how two revisions of
> this file were wrong on landing. `origin/main..HEAD` is the authority.
>
> Full history is in `memory/04_review_log.md`, `PLAN.md` and the commit
> messages. Corrected claims are marked below.

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

PR #76 merged as `f802dba4`, carrying the entries through the BLOCKED-3 design
slice below; M1 through M3-a merged earlier. Later branch work remains in the
same inventory without encoding a branch head or ahead count. For current merge
state, `git log --oneline origin/main..HEAD` is authoritative.

| Tranche | Commit |
| --- | --- |
| M3-b design, and its three refused amendments | `8a8dbc2c` |
| M3-b design revision 6 | `70d62fd1` |
| M3-b-1 closed loader and return frame | `cfa2c1ec` |
| M3-b-1 module-audit opt-out fix | `80b2a74c` |
| **BLOCKED-1 amendment**, allowlist widened to five | `fa10dda8` |
| **BLOCKED-2 amendment**, two verifier checks retired | `4ea55d3e` |
| BLOCKED-3 process-control design slice | `95838ac0` |
| Post-merge record reconciliation | `dc71c3f9` |
| BLOCKED-3 measured layouts and pure declarations | `fe44deb4` |

Two of those change executable authority or the meaning of passing verification,
and both are now in `main`: the allowlist is five modules, and two verifier
checks are retired from the reconstruction path. **BLOCKED-3 is CLOSED** after
acceptance of the design slice and measured-layout commit `fe44deb4`. CI had no
failures before the PR #76 merge: twelve passed, two skipped.

Merge history: PR #72 `5d184ee6`, #73 `d7d5485c`, #75 `5204cd18`, #76
`f802dba4`; #74 was another agent's work, merged only to clear BEHIND.

## Paused And Blocked

- **B-1**, the structural non-`repr` boundary, is
  `CHANGES_REQUESTED / PAUSED_BEHIND_M4`: five files preserved complete and
  unstaged — `gate3_private_rendering.py`, its tests, and the wiring in
  `gate3_route_v2.py`, `gate3_route_v2_codex.py` and
  `gate3_final_message_runner_integration.py`. Its construction-contract blockers
  are fixed; what blocks it is that changing the first two breaks the source pin
  the historical candidate is verified against.
- **BLOCKED-1 and BLOCKED-2 are resolved by amendment** (`fa10dda8`,
  `4ea55d3e`), under explicit human authorization, and both are now in `main`.
  M3-b-3 therefore has a defined callee and a defined verification contract.
  That is **authority, not sequence**: it runs inside the child M3-b-2 creates,
  so it is still third. It owns the parent-side result object and the two
  "not asserted" markers, which the BLOCKED-2 amendment requires and does not
  build.
- **BLOCKED-3 is CLOSED** (`95838ac0`, `fe44deb4`). The design slice is accepted;
  the pinned package digest was verified and the oracle now covers eighteen
  types, including seven measured process-control layouts with matching pure
  declarations and independent fixtures. Fresh-context exact-digest review
  approved the commit; 386 scoped tests and the canonical 201-test gate passed.
  No symbol is bound or called, `ACTIVE` remains `False`, and M3-b-2 has not begun.
- **Materialized-root transport is resolved as design, not implemented.** The
  accepted `GATE3HL\0` v1 envelope carries one unchanged M3-a frame and root.
  The full absolute base remains parent-trusted; M3-b-2 is unstarted.
- Nothing is wired to M2, M3-a or M3-b-1. `materialize()` and `cleanup()` refuse
  while `handle_boundary_available()` is `False`; `ACTIVE` is `False` and nothing
  calls in. M2's verification is still not entirely handle-bound: the
  enumeration remains a path walk.
- **M4 is not started.** Group C candidate `20f202e1...` is on HOLD.

## Next Steps

1. Define and authorize bounded **M3-b-2** against the accepted launch-envelope
   design; do not include M3-b-3.
2. **M3-b-3**, which runs inside the child M3-b-2 creates: authority unblocked,
   sequence not.
3. M4: the historical candidate verified against materialized historical bytes
   instead of the live worktree.
4. B-1 re-review and delivery, once M4 removes the dependency its edits break.

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

- Support #4691271 cleanup reported complete; Finding 33 temporarily unblocked by an exact untracked identity config pending guard-stack integration. <!-- memory_record_projection:active-task-summary:12bbe5f61f5609e3a9395e2ce6e5f9c2ea90b5f8c66f4ffd19fb7c2b1632a601 -->

- Repo PUBLIC by owner authority for consumer access; severe PR #95 exposure cleared, known mild exposure remains pending Gate 3 or public-need re-review. <!-- memory_record_projection:active-task-summary:1e46e921a10d8a6520c22eb25c18444d406f9dee50e743b88519ce2bb47f86d8 -->

- M3-b-2A merged by PR #108 at a59b0aef; status reconciliation is isolated, and M3-b-2B remains not started. <!-- memory_record_projection:active-task-summary:2eeb723b50a4c9513b6cecfbafb29471ef7d9d0ac29cd973b1fd97200a75a9ac -->
