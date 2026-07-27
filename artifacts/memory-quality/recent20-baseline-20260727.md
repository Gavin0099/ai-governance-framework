# Memory quality retrospective: recent-20 baseline

Status: observation-only
Fixed HEAD: `5a2c5a80b87eed21cf4edd85485e13a87a4cef21`
Sample: 20 most recent committed `session-derived` canonical memory entries
Dataset: `artifacts/memory-quality/recent20-context-20260727.json`

## Result

The sample does **not** show that `next_step` is usually abandoned. It shows a
different problem: the named work usually appears later, but often is not the
actual next action.

| Classification | Count | Share of all 20 | Plain-language meaning |
|---|---:|---:|---|
| `immediate_match` | 5 | 25% | The next commit aligns with the entry. |
| `deferred_match` | 8 | 40% | The work appears later, after other commits. |
| `never_observed` | 3 | 15% | No later matching commit is visible. |
| `unassessable` | 4 | 20% | Commit history alone cannot decide. |

Among the 16 assessable entries, 13 eventually matched: **81.25%**. Only 5 of
those 16 matched the immediate next commit: **31.25%**.

This means the stronger observed failure is priority/order accuracy, not total
non-completion.

## Failure-mode breakdown

- Eight entries named work that later happened, but other work came first.
- Two of the three `never_observed` entries were stale on arrival: their
  requested implementation was already contained in the commit that introduced
  the memory record.
- One `never_observed` entry was a genuine unobserved continuation: the
  authorized revision-7 canary never appeared before work moved to scorer-packet
  construction.
- Three entries depended on push or external CI state that later Git commits
  cannot time-order reliably.
- The newest entry is right-censored because fixed HEAD has no later commit.

## Method

1. Read only committed `HEAD` blobs under `memory/2026-*.md`; working-tree
   memory changes were excluded.
2. Select the last 20 `session-derived` entries by file date/order and in-file
   record order.
3. Retain each entry's linked commit as provenance context.
4. Use `git blame` on the entry start line to find the commit that actually
   introduced the record.
5. Compare `next_step` with commits after that record commit on the first-parent
   path, falling back to an ancestry path when needed.
6. Apply a human semantic label from the four-category vocabulary. The script
   stores each label, matched commit, rationale, and confidence beside the raw
   history context.

Using the record-introduction commit matters: comparing only with the linked
implementation commit would often misclassify the memory closeout commit itself
as the next action.

## Entry-level labels

| # | Source | Label | Matched commit | Short rationale |
|---:|---|---|---|---|
| 1 | `2026-07-26:28` | deferred | `eab44eeb` | Parallel-safety remediation preceded the live canary. |
| 2 | `2026-07-26:40` | immediate | `eab44eeb` | Next commit carried live-canary run evidence. |
| 3 | `2026-07-26:52` | immediate | `e8979673` | Next commit revised runbook and transport. |
| 4 | `2026-07-26:64` | immediate | `e8979673` | Next commit addressed the review blockers. |
| 5 | `2026-07-26:76` | immediate | `9a96c2e7` | Next commit carried run-4 NO-GO evidence. |
| 6 | `2026-07-26:88` | never observed | — | Work moved to scorer packet; no revision-7 canary appeared. |
| 7 | `2026-07-26:100` | never observed | — | Requested scorer-packet commit was already the record commit. |
| 8 | `2026-07-26:112` | deferred | `3bea5287` | Review remediation intervened before approval/re-sign. |
| 9 | `2026-07-26:124` | deferred | `3bea5287` | Further remediation preceded owner re-sign. |
| 10 | `2026-07-26:136` | deferred | `3bea5287` | Same review/re-sign continuation completed later. |
| 11 | `2026-07-26:148` | deferred | `3bea5287` | Re-review found another fix before re-sign. |
| 12 | `2026-07-27:4` | deferred | `b596153b` | Push was recorded before later review evidence. |
| 13 | `2026-07-27:16` | deferred | `b596153b` | Corrective duplicate retained the same ordering mismatch. |
| 14 | `2026-07-27:28` | deferred | `b596153b` | Cleanup came first; delivery/review evidence appeared later. |
| 15 | `2026-07-27:40` | unassessable | — | CI is external; GitLab restoration was already complete. |
| 16 | `2026-07-27:52` | never observed | — | Requested remediation was already in the record commit. |
| 17 | `2026-07-27:64` | immediate | `3bea5287` | Next commit recorded approval and owner re-sign. |
| 18 | `2026-07-27:76` | unassessable | — | Commit already existed; remaining action was remote push. |
| 19 | `2026-07-27:88` | unassessable | — | Same receipt/push observability boundary. |
| 20 | `2026-07-27:100` | unassessable | — | No later commit exists at fixed HEAD. |

## Interpretation and limits

- These 20 entries are concentrated in one Gate 2/scorer-handoff workflow and
  are not 20 independent workstreams.
- Entries 12 and 13 have identical `next_step` text; corrective records can
  overweight one event.
- Commit alignment is a retrospective proxy. It does not run the stronger
  fresh-session handoff test.
- A deferred result can be caused by valid owner intervention or newly observed
  failures; it is not automatically bad writing.
- Push, CI, approval, and other external actions need a separate observability
  class rather than being forced into pass/fail.

## Decision

Do not add a Memory quality validator from this sample. The baseline supports a
later, still advisory-only investigation of two candidate signals:

1. whether `next_step` describes work already completed by the record commit;
2. whether external actions are explicitly marked as not commit-observable.

Before treating the 31.25% immediate-match rate as representative, repeat the
measurement on a stratified sample spanning multiple dates and workstreams, and
deduplicate corrective entries.

## Claim ceiling

This baseline measures retrospective commit alignment only. It does not prove
Memory quality improvement, fresh-session handoff success, causality, G4 value,
or that any candidate signal should become enforcement.
