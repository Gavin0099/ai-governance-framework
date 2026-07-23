# G4 Cross-Consumer Observation Checkpoint - 2026-07-24

Date: 2026-07-24
Framework repository: `ai-governance-framework`
Consumer repositories: `Bookstore-Scraper`, `meiandraybook`,
`Enumd-private-vault`
Checkpoint status: recorded
Observed work-item candidates: 6
Classification: 3 qualifying, 1 zero-effect, 2 insufficient evidence
G4 status: NOT ACHIEVED

## Plain-Language Result

One new Bookstore work item qualifies with a receipt-anchor warning. The
existing Enumd case remains qualifying after correcting the reviewed repository
from `Enumd` to `Enumd-private-vault`. The two Mei candidates remain
insufficient; PR #9 is delivery evidence for that existing work and is not a
new sample merely because it is another PR.

The qualifying count increases from two to three, but cross-consumer breadth
does not increase: two qualifying cases are in Bookstore and one is in Enumd.
The observations remain concentrated on 2026-07-22 and 2026-07-23 under the
same owner and closely related agent environment.

## Relationship To The 2026-07-22 Checkpoint

The 2026-07-22 checkpoint is retained as a historical snapshot. It still
records the evidence available then: two qualifying cases, one zero-effect
case, and two insufficient-evidence candidates.

This successor checkpoint adds the distinct Bookstore slow-source / Grimm work
item and corrects the later review target for Enumd. It does not rewrite the
earlier checkpoint, convert phases or PRs into extra samples, or claim that the
new and carried-forward cases have equal evidence strength.

## Observation Method And Boundary

- One natural product work item is one observation candidate. Commits,
  sessions, test runs, phases, PRs, and memory records are evidence within a
  case, not additional samples.
- Consumer conclusions use committed evidence and read-only GitHub PR metadata.
  Dirty or uncommitted consumer content is excluded.
- `Enumd-private-vault` is the intended private-vault consumer. The separate
  `Gavin0099/Enumd` repository is not evidence for this checkpoint.
- Enumd Phase I through Phase R is one continuing private-data triage work
  item. Later phase and PR counts expose activity and cost but do not increase
  the case count.
- Mei PR #9 is not a third Mei case solely because it bundles more commits and
  checks. A distinct natural product goal and outcome would be required before
  adding another candidate.
- No consumer action was replayed, no consumer receipt was rewritten, and no
  consumer repository was modified for this checkpoint.
- No raw private-vault note, secret value, or row identity is reproduced.

## Work-Item Adjudication

| Case | Natural product goal | Governance signal and agent action change | Observed outcome | Verdict |
|---|---|---|---|---|
| `BS-KNSH-20260722` | Produce a stable, import-ready KNSH ordering catalog without fabricated identities. | The high-risk slice was separated from the governance update; the agent stabilized virtual ISBNs, excluded duplicate real ISBNs, added pass/fail fixtures and an execution harness, and stopped before an unauthorized production import. | 449 rows processed, 446 sale records retained, 3 duplicate-real-ISBN rows excluded, 0 parse errors, 0 ISBN conflicts, and 427 referenced covers present. | **qualifying** |
| `BS-SLOW-GRIMM-20260723` | Complete the five slow-source validation work, repair real Grimm price corruption, and finish Chinglin without publishing unreviewed generated output. | The agent preserved the initial Grimm domain failure and Chinglin completeness failure instead of reporting overall success. It fixed comma-grouped price parsing, added regression coverage, reran the failed live paths, and kept generated exports outside the PR. | PR #2 merged as `bc513fa`. Canonical memory binds the product correction to `c9cd494` and reports 173 tests passing, six repaired Grimm pages at prices 1100-2400, and a complete Chinglin run with 252 records and zero request or parse errors. **WARNING:** the full-pytest receipt still says `linked_commit=e478409`, the parent checkpoint before the final product commit. | **qualifying with receipt-anchor WARNING** |
| `BS-REGISTRY-ACTIONS-20260722` | Unify the 17-publisher registry and validation pipeline without unnecessary recurring Actions cost. | The governance baseline produced no observable pre-change warning about the weekly Actions schedule or the owner's branch expectation. The owner rejected the schedule; the agent then removed it and made the workflow manual-only. | Registry and validation pipeline shipped; the workflow is manual-only. | **zero-effect / owner-corrected** |
| `MEI-ADMIN-ORDERS-20260722` | Restore the admin order list after a composite-FK query regression. | Regression coverage and failure-state UX exist, but committed evidence still does not bind a deployed product replay to a governance-caused action change. | PR #9 remains draft with no reviews. Its current checks pass except `Phase Gate Verification`, which is skipped. Merge and deployment outcome remain absent. | **insufficient evidence** |
| `MEI-CHECKOUT-SKEW-20260722` | Prevent duplicate or ambiguous checkout behavior across deployment-version skew. | The agent added a unique deployment ID, persisted the draft before submission, and warned buyers to verify unknown outcomes instead of blindly retrying. The evidence remains commit- and PR-local. | PR #9 does not add a new sample or prove deployment success. No committed production replay currently upgrades this case. | **insufficient evidence** |
| `ENUMD-RESIDUAL-QUEUE-IJ-20260722` | Triage residual sensitive-review work without exposing private note contents or falsely closing credential review. | Phase I separated review layers and Phase J materialized anonymous context rows while preserving unfinished state and no-remediation boundaries. Later Phase K-R work continues the same queue lifecycle; it is not split into extra cases. | Original anchors `bce809c`, `f9def2c`, PR #4 / `e5681c3`, and PR #5 / `b33e4d8` remain present in `Gavin0099/Enumd-private-vault`. PR #7 through PR #16 are merged continuations, including the PR #8 framework update to `74b70252` and the Phase R selection at PR #16 / `111c4e7`. PR #17 is a draft continuation. | **qualifying** |

## Evidence Anchors

### Bookstore-Scraper

- KNSH evidence is carried forward unchanged from the 2026-07-22 checkpoint.
- Slow-source / Grimm product commit: `c9cd494`.
- Canonical memory commit: `9ba3d17`, with `commit: c9cd494`.
- Merged delivery: PR #2, merge commit `bc513fa`.
- GitHub checks on PR #2:
  - `Validate exports/latest against IMPORT_CONTRACT v2`: success;
  - `Interception Ledger Check`: success.
- Receipt warning:
  `artifacts/evidence/test-results/grimm-price-fix-full-pytest-20260723.json`
  records `exit_code=0` but `linked_commit=e478409`.
- Interpretation boundary: the warning is not repaired here. This checkpoint
  does not claim that the receipt proves the tests ran against `c9cd494`.

### meiandraybook

- Existing candidate anchors remain those recorded in the 2026-07-22
  checkpoint.
- PR #9 head: `d95b144`.
- Read-only GitHub state on 2026-07-24:
  - `state=OPEN` — the PR is not merged;
  - `isDraft=true` — the PR is still marked as a draft;
  - `reviews=[]` — no reviewer has submitted a review;
  - `mergeCommit=null` — no merge commit exists;
  - `Phase Gate Verification=SKIPPED` — that check did not execute;
  - the other reported governance, database, documentation, memory, and
    violation checks succeeded.
- Interpretation boundary: passing PR checks show delivery verification, not a
  deployed product outcome or a governance-caused behavior change.

### Enumd-private-vault

- Correct repository: `https://github.com/Gavin0099/Enumd-private-vault`.
- Original qualifying anchors:
  - Phase I feature `bce809c`, validation `978c5ef`, PR #4 merge `e5681c3`;
  - Phase J feature `f9def2c`, validation `ff3dd90`, PR #5 merge `b33e4d8`.
- Continuation evidence:
  - Phase L PR #7 merged as `784f46c`;
  - Phase M framework update PR #8 merged as `3b0d290`;
  - Phase N PR #9 merged as `52ef082`;
  - Phase O selection PR #10 merged as `bdfd999`;
  - later same-work-item PRs continue through merged Phase R PR #16
    (`111c4e7`);
  - Phase R PR #17 remains draft.
- Interpretation boundary: the continued phases do not prove credential
  remediation, independent review, lower long-term cost, or additional G4
  samples.

## Count, Breadth, And Evidence Strength

| Measure | 2026-07-22 checkpoint | 2026-07-24 checkpoint | Interpretation |
|---|---:|---:|---|
| Qualifying work items | 2 | 3 | One distinct Bookstore work item added. |
| Zero-effect / owner-corrected | 1 | 1 | No change. |
| Insufficient-evidence candidates | 2 | 2 | Mei PR #9 does not create a new sample. |
| Consumers with qualifying cases | 2 | 2 | Bookstore and Enumd; breadth did not increase or decrease. |
| Observation dates | 1 | 2 adjacent dates | Still too concentrated for sustained evidence. |

The three qualifying cases are not equally strong. The new Bookstore case has
a receipt-anchor warning; the Enumd case has many continuation PRs but remains
one owner-led work item; none of the three establishes independent non-author
use.

## Owner Intervention And Observable Cost

| Case | Owner intervention | Observable cost | Missing cost evidence |
|---|---|---|---|
| Bookstore KNSH | None recorded; absence is unknown, not zero. | Multiple product and evidence commits plus scoped tests and contract checks. | Human review time, token cost, maintenance cost, and avoided rework. |
| Bookstore slow-source / Grimm | No direct correction recorded for the bounded repair. | Four branch commits, one merged PR, failed and passing live-source runs, regression tests, and retained diagnostic evidence. | Human minutes, agent/token cost, rerun cost, future maintenance, and quantified data-error impact. |
| Bookstore registry / Actions | Direct owner correction removed the recurring Actions schedule. | Registry delivery plus a follow-up correction commit. | Durable owner-review minutes and quantified Actions cost avoided. |
| Mei admin / checkout | No qualifying outcome intervention recorded. | PR checks and implementation commits exist, but deployment replay cost is absent. | Production outcome, rework avoided, owner assistance, and maintenance cost. |
| Enumd Phase I-R | No independent reviewer is recorded for the qualifying boundary. | Many phases and PRs within one continuing queue work item; this is execution cost, not sample volume. | Human review time, false-positive/negative rate, remediation outcome, and long-term maintenance cost. |

The available costs remain non-comparable. Commit, phase, and PR counts are not
converted into human effort or governance benefit.

## Transfer And Recurrence

Observed transfer:

- Qualifying evidence still spans two consumer repositories and two domains:
  commerce catalog integrity and private-vault security triage.
- The Bookstore cases show two distinct product goals inside one consumer.
- The Enumd continuation shows repeated use inside one work item, not
  independent recurrence.

Remaining gap:

- The same owner and closely related agent environment remain involved.
- No qualifying case has an independent reviewer attached to its outcome
  claim.
- The evidence covers two adjacent dates, not multiple weeks.
- Comparable before/after rework, reviewer time, false-positive rate,
  false-negative rate, and maintenance cost remain unavailable.
- Mei has not yet supplied a committed deployment/product replay that can be
  adjudicated as an outcome.

## G4 Contribution And Claim Ceiling

This checkpoint supports only the following bounded claim:

> The framework has three early qualifying consumer work-item observations,
> one observed zero-effect case requiring owner correction, and two unresolved
> Mei candidates. The qualifying evidence spans Bookstore and Enumd, but it is
> concentrated in time, owner, and agent environment.

It does not establish:

- G4 achieved;
- sustained or statistically comparable outcomes;
- independent non-author use without owner assistance;
- that governance benefit exceeds execution or maintenance cost;
- that the Bookstore receipt proves testing against `c9cd494`;
- that passing Mei PR checks prove deployment or product success;
- that Enumd credentials were reviewed, rotated, or remediated;
- that phases, PRs, sessions, or receipts are additional samples; or
- that any hook, CI, gate, runtime, schema, tool, or enforcement changed.

## Next Observation

Wait for a naturally completed consumer outcome. For Mei, require a committed
deployment/product replay and identify the governance signal that changed an
agent action before upgrading either existing candidate. Separately, seek
multi-week and independent-review evidence; do not manufacture replay, repair a
consumer receipt from this framework task, or split an existing work item to
increase the count.
