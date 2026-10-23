# Active-task replacement preservation matrix - 2026-10-23

Status: **PRE-CUTOVER CANDIDATE / MECHANICALLY VERIFIED / NOT INDEPENDENTLY REVIEWED**

This matrix proves section-level byte preservation by measurement. It is **not**
an independent fidelity review. The 2026-08-30 cutover carried an external
`APPROVED` verdict; no equivalent reviewer ran for this candidate, and that gap
is recorded in the cutover manifest as `review_status: unreviewed`.

Frozen predecessor:

- path: `memory/01_active_task.md`
- verified archive: `memory/archive/active_task_20261023_124358.md`
- SHA-256 (LF-normalized): `a85cafddd7ff3a6fa01f7b41b151ed39f28f0c7d8ace5396757e393f893b7b64`
- Git blob: `291f481b287c8a300cb36c02c826ca2141c75feb` (identical to the predecessor blob)
- bytes/chars/lines/LF/CR: `12069 / 12057 / 148 / 148 / 0`
- BOM/trailing LF: `false / true`
- the worktree predecessor was CRLF (`12217` bytes, `148` CR). The archive stores the
  LF-normalized bytes, which is the identity Git and the pressure check both use.

Replacement candidate: `memory/archive/active_task_20261023_124358_replacement_candidate.md`

- SHA-256: `f3419804f878137d881b97e16b2f1151420a6e0dbcace05420ff9b5a8d067a3e`
- bytes/chars/lines/LF/CR: `9613 / 9601 / 136 / 136 / 0`
- measured pressure after cutover: **WARNING** (`136`/200 lines; `9601` chars)
- EMERGENCY is cleared (chars < 12000 and lines < 250). SAFE (< 8000 chars) is **not**
  reached: the remaining mass is the preserved authority index, Gate 3 state and
  claim ceiling. Compressing those is exactly what the preservation finding
  `885c5de79d414b08136f5a06ed0cba77c81d30c2` guards, so reaching SAFE needs a
  separate authorization and its own independent review.

| Predecessor item and anchor | Class | Preservation mode | Replacement location | Authority / decision effect | Verification |
| --- | --- | --- | --- | --- | --- |
| Current Gate 3 State items 1-4 (adopted source graph and 63-predicate register, formal rev9 STOP, Release-Order design primitive, post-cutover STOP) | irreversible state + authority status | verbatim | Current Gate 3 State | unchanged | BYTE-IDENTICAL (1110 chars) |
| Durable Authority And Evidence Index, 7 rows plus the adoption-status note (all exact commits, blobs and SHA-256 values) | authority reference/status | verbatim | same section | unchanged; no pointer promoted | BYTE-IDENTICAL (2501 chars) |
| Other Retained Workstream State items 1-5 (M3-b-2A/2B, B-1, disclosure state, F-7) | current work state | verbatim | same section | unchanged; dirty work neither authorized nor discarded | BYTE-IDENTICAL (1095 chars) |
| Open Risks items 1-4 (session binding, closeout parser, PLAN freshness conflict, historical candidate verification) | open risk | verbatim | same section | all remain open; no disposition added | BYTE-IDENTICAL (699 chars) |
| Next Decision Boundary items 1-2 | authorization boundary | verbatim | same section | unchanged; no automatic continuation | BYTE-IDENTICAL (347 chars) |
| Claim Ceiling, 7 bullets (Gate 3 / native boundary / design-vs-implementation / M3-b-1 harness / consumer / executor wrapper / NOT CLEAN) | effective claim ceiling | verbatim | same section | unchanged; candidate section text is an exact prefix of the predecessor section | BYTE-IDENTICAL (7/7 bullets) |
| Irreversible State And Prohibitions items 1-3 (consumed A/B pair NON_SUCCESS, historical Gate 2 non-repairable, M3-b/B-1 dirty material) | irreversible state | verbatim | same section items 1-3 | unchanged | BYTE-IDENTICAL |
| Irreversible State And Prohibitions item 4 (janitor fail-closed; 2026-08-30 one-final-manual-replacement-attempt clause) | operational authority/status | SEMANTIC DELTA - re-scoped | same section item 4 | fail-closed prohibition preserved; the spent 2026-08-30 one-attempt clause is scoped to that attempt and this cutover is bound to a separate 2026-10-23 owner authorization | CHANGED - SOLE DISCLOSED DELTA |
| Header predecessor pointer and prepared-on date | provenance pointer | re-bound to this cutover | lines 1-2 and the retrieval-index note | points to the new verified archive and its SHA-256 | CHANGED - intended re-binding |
| 12 superseded active-task-summary projections (L122-L146) | canonical checkpoint projection | REMOVED from the active surface; retained verbatim in the verified archive | Canonical Checkpoint Projections provenance note | each identity independently confirmed in tracked memory files before removal; see the table below | REMOVED - 12/12 recoverable |
| Current active-task-summary projection 5464b03c (Stop wiring 6f097eb8) | canonical checkpoint projection | verbatim | Canonical Checkpoint Projections | retained as the only current projection | BYTE-IDENTICAL |

## Removed projection recoverability (checked before removal)

| Identity (prefix) | Summary | Independent tracked anchor |
| --- | --- | --- |
| `7d9a941064f4` | Solo R2 task/rubric bytes adopted | `memory/2026-09-06.md` |
| `a4e46ca16faf` | Disposable inputs qualified at 695863d1 | `memory/2026-09-06.md` |
| `29735f39f5f0` | v2.1 amendment adopted | `memory/2026-09-06.md` |
| `4abae7efb9b5` | D2 allocation adopted | `memory/2026-09-06.md` |
| `004754f2e357` | Placement adopted; STOP | `memory/2026-09-06.md` |
| `1e46e921a10d` | Repo PUBLIC by owner authority | `memory/04_review_log.md, memory/archive/active_task_20260830_021544.md` |
| `2eeb723b50a4` | M3-b-2A merged by PR #108 | `memory/04_review_log.md, memory/2026-10-01.md` |
| `61990e3b367e` | C1 Gate 1 admission / D5 PR #120 | `memory/04_review_log.md` |
| `e3e590f863c4` | Advisory Skill selection adoption docs | `memory/2026-09-09.md` |
| `c128d26d86b2` | S2 presentation committed | `memory/04_review_log.md, memory/2026-09-14.md` |
| `c25f96c6d651` | H1 implementation committed | `memory/04_review_log.md, memory/2026-09-14.md` |
| `7c2b2b8e8662` | Early-HOLD disposition P1 OPEN | `memory/2026-09-22.md` |

All 12 removed identities resolve in at least one tracked `memory/**` file in
addition to the verified archive. 0 unrecoverable.

## Known residuals (recorded, not fixed)

- No independent fidelity reviewer ran against this candidate SHA-256.
- Removing a projection marker also removes `memory_record`'s idempotency anchor
  for that identity, so an identical re-run could re-append it. This is unchanged
  from the behaviour noted in the abandoned 2026-09-12 attempt; not repaired here.
- `memory/archive/active_task_20260903_224346.md` remains untracked and is not
  part of this provenance chain.
- The Claim Ceiling still names checkpoint `760215c2` while the retained
  projection is `5464b03c`. That inconsistency pre-dates this cutover and is
  preserved verbatim rather than silently corrected.

Result: **MECHANICALLY VERIFIED** for replacement SHA-256 `f3419804f878137d881b97e16b2f1151420a6e0dbcace05420ff9b5a8d067a3e`.
Any later byte change invalidates these measurements.
