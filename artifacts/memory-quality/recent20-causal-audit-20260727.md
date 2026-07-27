# Memory quality retrospective: causal reclassification (Tranche 2)

Status: observation-only
Fixed HEAD: `5a2c5a80b87eed21cf4edd85485e13a87a4cef21`
Scope: the 15 non-`immediate_match` entries from the Tranche 1 baseline
Upstream: `artifacts/memory-quality/recent20-baseline-20260727.md`
Dataset: `artifacts/memory-quality/recent20-causal-audit-20260727.json`
Amendment receipt: `artifacts/memory-quality/recent20-record-commit-blind-review-20260727.json`

## Result

The 31.25% immediate-match rate is not a memory quality signal. After causal
annotation, **zero** of the 15 deferred, unobserved, or unassessable entries is
a confirmed avoidable memory defect.

| Cause | Count | Plain-language meaning |
|---|---:|---|
| `review_finding` | 5 | Independent review found a real defect that had to be fixed first. |
| `superseded` | 3 | Corrective duplicate of an earlier record for the same event. |
| `record_commit_artifact` | 3 | The record was committed inside the commit its own `next_step` named. |
| `observed_failure` | 1 | A concurrency race was reproduced and blocked the named work. |
| `owner_reprioritization` | 1 | Owner redirected work; the record had gated itself on authorization. |
| `external_only` | 1 | The named action is a CI result, invisible to Git history. |
| `censored` | 1 | Right-censored at fixed HEAD; the work was in fact done. |

| Avoidable memory defect | Count |
|---|---:|
| `no` | 11 |
| `unknown` | 4 |
| `yes` | **0** |

## The baseline's `stale_at_write` finding does not survive verification

Tranche 1 reported that two `never_observed` entries "were stale on arrival:
their requested implementation was already contained in the commit that
introduced the memory record." Three entries fit that description (sequences 7,
16, 18). All three were checked against the actual commits. The stale-at-write
reading fails in each case, with clause-level distinctions recorded below.

Sequence 16 is the clearest case. Its `record_commit` is `b596153b`, and its
`next_step` asks to implement BLOCKER-1, BLOCKER-2 and WARN-3 — which is exactly
what `b596153b` does. But `b596153b` also *adds this record to the memory file*:

```
git show --stat b596153b
  memory/2026-07-27.md   | 24 ++++
git show b596153b -- memory/2026-07-27.md
  + what_changed: Confirmed GitLab main push from 5997b064 to ad96830a ...
  + next_step: Implement the owner-requested bounded scorer-handoff review fixes ...
```

The record describes the *earlier* GitLab push, sat uncommitted in the working
tree, and was then committed alongside the work its `next_step` named. It was
accurate when written and its remediation clause was fulfilled. Sequence 7 is
the same timing pattern, but the clauses must be kept separate: `ac9dab87`
carries the focused-precommit receipt, the scorer-packet slice and
`memory/2026-07-26.md +12`; the later owner-signed amendment and Gate 2 authority
clause remained forward-looking. For sequence 18, `3bea5287` carries the
receipt, `PLAN.md +5` and `memory/2026-07-27.md +24` named by the commit clause;
the subsequent push clause is not observable from that commit.

The confound is the measurement anchor. `git blame` on the entry's start line
returns the commit that *committed* the record, not the commit after which the
record was *written*. For any workflow that writes memory before committing —
which is this repository's normal workflow — the blame anchor is systematically
too late, and it manufactures apparent staleness.

The same commit `b596153b` illustrates the incoherence directly: it is the
"already done it" evidence against sequence 16 and simultaneously the
`immediate_match` for sequence 17, which it also introduced.

### Consequence for the baseline's candidate signal 1

Tranche 1 proposed investigating "whether `next_step` describes work already
completed by the record commit." As specified, that signal is invalid. Every
candidate hit in this sample is the normal write-then-commit sequence, so the
signal would fire 3/3 false positives here and zero true positives. It should
not be carried forward without a write-time anchor (record mtime, session end
time, or an explicit written-at field) that separates authorship from commit.

`stale_at_write` is retained in the vocabulary but has no members. A new cause
`record_commit_artifact` was added to name what was actually observed.

### Targeted independent fact-check amendment

A fresh reviewer was asked only two Git questions for `ac9dab87`, `b596153b`
and `3bea5287`: whether each commit performed work named by the corresponding
`next_step`, and whether it also added that memory record. The reported results
were:

| Sequence | Commit | Reported result | Disposition |
|---:|---|---|---|
| 7 | `ac9dab87` | `PARTIAL` | Precommit and bounded-commit clauses are present; the later owner-authority clause remained forward-looking. |
| 16 | `b596153b` | `YES` | The named BLOCKER-1/2 and WARN-3 remediation and the memory record are in the same commit. |
| 18 | `3bea5287` | `PARTIAL` | The commit clause and memory record are present; the push clause is not commit-observable. |

The reviewer reportedly used the fixed-head Git object view and did not read
this audit, current memory, or `PLAN.md`. The original command transcript was
not persisted. The durable receipt therefore records
`independent_review_reported`, not `confirmed_independent`; the main session's
Git re-check confirms the facts but is not a substitute for reviewer
independence or proof of blinding.

The downstream decision is unchanged: the timing confound is independently
supported at the reported-result level, candidate signal 1 remains invalid as
specified, and no quality mechanism is admitted.

## Unit of analysis: 20 records are 4 work items

Grouping all 20 baseline entries under their real work item, per
`memory/00_long_term.md:244`:

| Work item | Records | Share |
|---|---:|---:|
| WI-B `gate2-scorer-handoff-v3` (review cycles, owner re-sign, delivery) | 12 | 60% |
| WI-A `gate2-admission-canary` | 6 | 30% |
| WI-C `memory-provenance-and-quality-measurement` | 1 | 5% |
| WI-D `memory-pressure-janitor-cleanup` | 1 | 5% |

Three of the 15 annotated entries are corrective duplicates (10 of 9, 13 of 12,
19 of 18), leaving 12 unique. Sequences 12 and 13 carry byte-identical
`next_step` text from the same session and the same record commit — a single
event counted twice.

The later `what_changed` text strengthens the dedup evidence in all three
pairs: sequence 10 says "Correction to the immediately preceding", sequence 13
calls itself a corrective provenance record, and sequence 19 says "Corrected
the immediately preceding".

A percentage over 20 records is therefore close to a percentage over one work
item. It cannot support a claim about memory quality in general.

## Observability

| Class | Count | Notes |
|---|---:|---|
| `commit` | 12 | Includes two-clause steps whose gating clause is commit-visible. |
| `ci` | 1 | Sequence 15 names a GitHub job result. |
| `human` | 1 | Sequence 6 waits on separate owner authorization. |
| `right_censored` | 1 | Sequence 20. |

Sequence 20 deserves its own note. Its `next_step` was to run the Tranche 1
baseline. Commit history at fixed HEAD says `unassessable`; the working tree
says done — `artifacts/memory-quality/recent20-baseline-20260727.md` exists,
untracked. This is direct evidence that the commit-only proxy undercounts
completion rather than overcounting it.

Several `next_step` values also carry two clauses with different observability
(for example "obtain independent review ... then push"). Forcing those into a
single pass/fail label is part of what produced the original 31.25%.

## Gate evaluation

The gate set for this tranche was: at least two *independent* work items showing
the same avoidable memory defect.

- Confirmed avoidable defects: **0**, across 0 work items.
- The 4 `unknown` labels are all `record_commit_artifact` cases, all inside
  WI-B — one work item, so they could not clear the gate even if they were
  reclassified as defects.

**Gate NOT MET. Stop.** Do not build an advisory prompt, a fresh-session replay
harness, a Memory quality validator, or any other mechanism from this sample.

## One question left open for the owner

The four `unknown` labels are marked unknown rather than `no` because they turn
on a policy call this data cannot settle: when a `next_step` says "commit this
receipt and memory record," it is accurate and it is fulfilled, but it spends
the handoff field on a mechanical within-session step rather than on what the
next session should do. Whether that counts as low handoff value is a judgement
about what `next_step` is for, not a measurable defect. It is recorded here and
not acted on.

## Method

1. Consumed the Tranche 1 dataset unchanged; no re-derivation of labels.
2. For every non-`immediate_match` entry, read the intervening commits between
   `record_commit` and `matched_commit`.
3. For each entry whose baseline rationale asserted staleness, ran
   `git show --stat` and `git show -- memory/<file>` on the record commit to
   check whether that commit both performed the named work and introduced the
   record.
4. Assigned work items by deliverable, folding sessions, sub-agent reviews,
   evidence corrections and push checks into the parent item.
5. Marked corrective duplicates using the later record's explicit correction
   language, with shared record commit and session lineage as corroboration.
6. Recorded the targeted fresh-reviewer result for sequences 7, 16 and 18 as
   `independent_review_reported`.
7. Closed the remaining 12 entries as `not_reviewed_by_decision`; they are not
   pending review debt.

## Closeout evidence correction

The canonical closeout memory entry says the Git Bash enforcement run passed
runtime smoke and 187/187 focused tests. The execution was observed in the
session, but no durable receipt for this Memory-quality closeout was retained.
It must therefore be described as:

> UNRECEIPTED LOCAL EXECUTION: Git Bash enforcement reported runtime smoke PASS
> and 187/187 focused tests during the session. No durable receipt was retained;
> this is not artifact-backed test proof.

No receipt is reconstructed after the fact, and this docs-only amendment does
not rerun the runtime suite.

## Claim ceiling

- Three `record_commit_artifact` entries have a reported independent fact-check.
  Because the reviewer command transcript was not persisted, this is not a
  `confirmed_independent` claim.
- The remaining 12 entries are `not_reviewed_by_decision`, not pending review
  debt. Their single-annotator causal labels are not independently confirmed.
- The `record_commit_artifact` finding also rests on commit contents that can be
  re-checked with the commands quoted above; a main-session re-check confirms
  the facts but not reviewer independence or blinding.
- Counts reconcile to the original 20 (5 `immediate_match` + 15 annotated).
- This measures retrospective commit alignment and its causes only. It does not
  measure fresh-session handoff success, does not prove Memory quality
  improvement or decline, and is not G4 outcome evidence.
- No validator, hook, CI, schema, blocker, or canonical memory format was
  changed. `memory_record.py` and `memory_significance.py` were not touched.
