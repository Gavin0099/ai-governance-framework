# P1-E Plan Reconciliation Final Observation Checkpoint - 2026-07-17

Status: observation evidence (final-window checkpoint)
Scope: P1-E plan_reconciliation sample, full observation window closeout
Authority: reviewer-facing evidence only
Runtime behavior change: no
Enforcement change: no
Memory rewrite: no

## Purpose

This note records the final observation checkpoint for P1-E: collect
false-positive / false-negative samples before any blocking decision for
`plan_reconciliation`.

The observation window opened 2026-06-12 (field introduction). The required
2-4 week window is complete: this checkpoint is taken at day 35 (5 weeks).
The two-week checkpoint was recorded on 2026-06-27 in
`p1e-plan-reconciliation-two-week-sample-2026-06-27.md`.

This checkpoint closes the P1-E collection requirement. It does not make the
P1-F decision; upgrading to a current-diff blocker remains a separate
owner-authorized [OP-HC] decision with its own mutation contract.

## Evidence Commands

Report command:

```powershell
python -m governance_tools.deferred_debt_report --project-root . --as-of 2026-07-17 --format human
```

Machine-readable snapshot retained alongside this note:
`p1e-plan-reconciliation-final-checkpoint-2026-07-17.json`.

Focused validation:

```powershell
python -m pytest tests/test_deferred_debt_report.py
```

## Report Output

As of `2026-07-17` the report scanned 94 daily memory files and 796
session-derived records.

Snapshot boundary: these counts describe this worktree / commit-state memory
tree. Because `deferred_debt_report` scans live `memory/` files, future
canonical memory records are expected to change total file / record counts
without invalidating this checkpoint.

```text
counts by plan_reconciliation:
  updated: 61
  not_applicable: 435
  deferred: 7
  not_declared: 44
  pre_field: 249
  malformed: 0

deferred by reason:
  scope-split-next-slice: 7, oldest 30d (2026-06-17)

not_declared:
  44, oldest 35d (2026-06-12)
```

## Classification Of Growth Since The Two-Week Checkpoint

`not_declared` grew 24 -> 44 between 2026-06-27 and 2026-07-17. A read-only
classification pass using the report tool's own parser
(`parse_session_derived_records` / `classify_record`) attributes every one of
the 44 records:

```text
by (date, kind, writer):
  2026-06-12 absent   governance_tools.memory_record: 14
  2026-06-15 literal  governance_tools.memory_record: 1
  2026-06-18 literal  governance_tools.memory_record: 1
  2026-06-21 literal  governance_tools.memory_record: 6
  2026-06-22 literal  governance_tools.memory_record: 2
  2026-06-28 literal  governance_tools.memory_record: 3
  2026-07-01 literal  governance_tools.memory_record: 1
  2026-07-04 literal  governance_tools.memory_record: 6
  2026-07-06 literal  governance_tools.memory_record: 2
  2026-07-09 literal  governance_tools.memory_record: 7
  2026-07-10 literal  governance_tools.memory_record: 1
```

- `absent` = the record has no `plan_reconciliation` field (all 14 on
  2026-06-12, the field introduction day, before the writer emitted it).
- `literal` = the record carries the recorded value
  `plan_reconciliation: not_declared`, which the pre-Option-B canonical
  writer produced by normalizing CLI omission. These records were legal at
  write time under the advisory-era writer contract.
- Every record was written by the canonical writer
  (`governance_tools.memory_record`). No non-canonical writer bypass and no
  writer-contract violation was found in this class.

Key boundary event: P1-F Option B (`c06014c4`, committed 2026-07-11)
changed the canonical writer **CLI** to require an explicit
`--plan-reconciliation` declaration and reject omission with exit 2. The
last `not_declared` record is dated 2026-07-10 — the day before Option B
landed. Zero `not_declared` records appear from 2026-07-11 through
2026-07-17 in this sample.

Path-coverage limit (added 2026-07-18 after review): Option B covers the
CLI entry point only. The underlying helper
`build_session_derived_record()` (`governance_tools/memory_record.py`)
still defaults `plan_reconciliation` to `not_declared`, and the runtime
`session_end` hook (`runtime_hooks/core/session_end.py`) calls that helper
without passing a declaration. That runtime path can therefore still
legally emit `not_declared` records. The window sample simply contains no
post-Option-B records from that path, so its behavior is unobserved — not
eliminated.

The `deferred` class is flat: 7 records, all using the explicit
`scope-split-next-slice` taxonomy reason, dated 2026-06-17 through
2026-06-24, with none added since. `malformed` remains 0 across the entire
window.

## FP/FN Conclusion

Window verdict (observation-class, reviewer-facing):

1. **The observed CLI omission path was closed by the writer contract, not
   by a blocker.** All post-introduction `not_declared` growth in the
   sample came from the advisory-era CLI omission-normalization path. After
   Option B made the declaration mandatory at the CLI boundary
   (non-blocking with respect to diffs; it rejects the write call, it does
   not gate commits), the sample shows 0 new `not_declared` from
   2026-07-11 through 2026-07-17. This is sample-zero-growth, not proof
   that every canonical writer path is closed.
2. **False-positive evidence for a future current-diff blocker:** treating
   the 30 advisory-era literal `not_declared` records as violations would be
   false positives — they were legal writer output when written. Any future
   blocker must bucket them as historical, consistent with the report's
   existing `pre_field`/advisory-era boundaries.
3. **False-negative evidence: none observed, with a known unobserved
   path.** No malformed values, no post-Option-B omissions, and no
   non-canonical writer paths appear in this class during the window. The
   runtime `session_end` helper path retains the `not_declared` default and
   produced no records in the post-Option-B sample, so it is an
   un-triggered potential false-negative path, not a cleared one.
4. **Observed failure driver for P1-F: currently none.** Since 2026-07-11
   there is nothing a current-diff `plan_reconciliation` blocker would have
   blocked in this sample. The evidence supports a narrower statement: the
   Option B CLI contract is sufficient for the CLI writing path observed in
   this window. Whether the runtime `session_end` path needs the same
   treatment is a separate failure-driven, owner-authorized question; this
   slice changes no writer.

## Claim Ceiling

Claimed:

- The P1-E 2-4 week observation window is complete (day 35), with two-week
  and final checkpoints recorded and reproducible through
  `governance_tools.deferred_debt_report`.
- Every `not_declared` record in the window is classified by date, kind
  (absent vs literal), and writer, and all are canonical-writer output legal
  at write time.
- The silent-declaration class shows zero growth in this sample after
  Option B (`c06014c4`, 2026-07-11).
- Focused tests for the report tool passed at this checkpoint.

Not claimed:

- This checkpoint does not decide P1-F. Upgrading to a current-diff blocker
  remains a separate owner-authorized [OP-HC] decision requiring its own
  mutation contract and rollback path.
- Option B is NOT claimed to cover all canonical writer paths. The
  `build_session_derived_record()` helper still defaults to `not_declared`
  and the runtime `session_end` hook calls it without a declaration; that
  path can still emit `not_declared` and was not exercised in the
  post-Option-B sample. The observation window does not prove the absence
  of un-triggered false-negative paths.
- No semantic correctness of memory content, no PLAN synchronization proof,
  and no enforcement behavior is claimed.
- Future writer regressions or new writer paths are not ruled out; the
  zero-growth observation covers 2026-07-11 through 2026-07-17 only.
- No hook, CI, gate, threshold, or blocking semantics were added or changed
  in this slice.
