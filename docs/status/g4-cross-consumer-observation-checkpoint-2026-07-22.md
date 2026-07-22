# G4 Cross-Consumer Observation Checkpoint - 2026-07-22

Date: 2026-07-22
Framework repository: `ai-governance-framework`
Consumer repositories: `Bookstore-Scraper`, `meiandraybook`,
`Enumd-private-vault`
Checkpoint status: recorded
Observed work-item candidates: 5
Classification: 2 qualifying, 1 zero-effect, 2 insufficient evidence
G4 status: NOT ACHIEVED

## Plain-Language Result

Two natural consumer work items show that governance changed agent behavior:
the Bookstore KNSH rollout and the Enumd residual security-review queue. One
Bookstore workflow-cost decision required direct owner correction despite the
governance baseline, and two meiandraybook product fixes still lack a completed
consumer replay.

This is the first cross-consumer observation checkpoint. It supports early
repo- and domain-transfer evidence, not sustained G4, independent non-author
use, or a benefit-over-cost conclusion.

## Observation Method And Boundary

- One real work item is one observation candidate. Commits, sessions, test
  runs, PRs, and memory records are evidence within a case, not extra samples.
- Consumer-repo conclusions use committed evidence. The Bookstore Actions-cost
  correction also uses direct owner feedback from the current main session and
  is explicitly marked session-only.
- Dirty or uncommitted consumer work is excluded. In particular,
  `meiandraybook` had another agent's active tracked and untracked work during
  adjudication; none of that content was inspected or used.
- No raw private-vault note, secret value, or Enumd row identity is reproduced
  here. Enumd evidence is limited to aggregate metadata and committed claim
  boundaries.
- This checkpoint does not modify, replay, or rerun a consumer product action.

## Work-Item Adjudication

| Case | Natural product goal | Governance signal and agent action change | Observed outcome | Verdict |
|---|---|---|---|---|
| `BS-KNSH-20260722` | Produce a stable, import-ready KNSH ordering catalog without fabricated identities. | The high-risk slice was separated from the governance update; the agent stabilized virtual ISBNs, excluded duplicate real ISBNs, added pass/fail fixtures and an execution harness, and stopped before an unauthorized production import. | 449 rows processed, 446 sale records retained, 3 duplicate-real-ISBN rows excluded, 0 parse errors, 0 ISBN conflicts, 427 referenced covers present; linked receipts report 144 tests and 32/32 import-contract files passing. | **qualifying** |
| `BS-REGISTRY-ACTIONS-20260722` | Unify the 17-publisher registry and validation pipeline without unnecessary recurring Actions cost. | The governance baseline produced no observable pre-change warning about the weekly Actions schedule or the owner's branch expectation. The owner explicitly rejected the schedule; the agent then removed it and made the workflow manual-only. | Registry and validation pipeline shipped; current replay reports 171 tests, 34/34 import-contract files, and 17 strict publisher checks passing. The workflow is manual-only. | **zero-effect / owner-corrected** |
| `MEI-ADMIN-ORDERS-20260722` | Restore the admin order list after a composite-FK query regression. | A regression test and failure-state UX were added after the framework update, but the committed record does not show that a governance signal caused the decision or that the deployed UI was replayed. | Focused tests report 2/2 passing, build passing, and a corrected read-only Supabase query returning 152 orders. Deployment verification remains the recorded next step. | **insufficient evidence** |
| `MEI-CHECKOUT-SKEW-20260722` | Prevent duplicate or ambiguous checkout behavior across deployment-version skew. | The agent added a unique deployment ID, persisted the draft before submission, and warned buyers to verify unknown outcomes instead of blindly retrying. Evidence is static and commit-local. | Three source-level regression assertions exist, but no committed deploy receipt, production replay, canonical memory entry, or current closeout binds the outcome. | **insufficient evidence** |
| `ENUMD-RESIDUAL-QUEUE-IJ-20260722` | Triage residual sensitive-review work without exposing private note contents or falsely closing credential review. | Phase I separated P1 source-manual, P2 context-metadata, and P2 derived-summary layers. Phase J materialized 16 selected context rows as anonymous stable IDs while enforcing no source review, no queue-disposition change, and no remediation claim. | The current checker reports 302 residual rows, 16 selected context rows, 0 duplicate rows, all 16 `unknown` / `follow_up` / `not done`, and no source-note access. Thirteen focused tests and the repo drift check pass; PR #4 and PR #5 record passing CI runs. | **qualifying** |

## Evidence Anchors

### Bookstore-Scraper

- Framework baseline: gitlink and lock at
  `42ca0157e757653c6079b5f6fda6dae58477f18b` before both observed work items.
- KNSH product commits: `3dffe56`, `fe7038d`, `be4b24c`, `48afffd`.
- KNSH evidence checkpoint: `67204e7`, `memory/2026-07-22.md`,
  `artifacts/evidence/test-results/knsh-final-pytest-20260722.json`, and
  `artifacts/evidence/test-results/knsh-import-contract-20260722.json`.
- Registry and validation commit: `9300875`.
- Manual-only owner correction: `d8a6a1f`.
- Current scoped recheck in the adjudication session:
  - `pytest tests -q -p no:cacheprovider`: 171 passed;
  - `scripts/verify_import_contract_v2.py`: 34/34 passed;
  - `scripts/report_daily_validation.py --strict`: 17 publishers, 0 contract
    failures, 0 publishers above the 5% unexpected-missing-image threshold.
- Image boundary: strict success does not mean zero missing images. The current
  report contains 25 unexpected missing images below threshold: 19 KNSH, 3
  Windmill, and 3 Bookrep. Tmac has 36 exact, time-bounded acknowledged upstream
  misses.

### meiandraybook

- Framework baseline: gitlink and lock at
  `8a98df2e358831733af374c297122ecb74d0d8fe`.
- Governance update: `3d7c3a1`.
- Admin-order fix: `90aeca2`; canonical record: `8a66cda` and
  `memory/2026-07-22.md`.
- Checkout deployment-skew fix: `f8e84c9`, including
  `src/__tests__/checkout-deployment-skew.test.ts` and the PLAN checkpoint.
- Evidence gap: the tracked `artifacts/session-closeout.txt` belongs to the
  earlier resumable image-import work item, not either current candidate.
- Live workspace boundary during adjudication:
  `memory_workflow_required` meant that another agent had an active memory diff;
  `completion_claim_allowed=false` meant that live memory completion could not
  be claimed. No dirty content was used in this checkpoint.

### Enumd-private-vault

- Framework baseline: repo-owned gitlink and lock at
  `42ca0157e757653c6079b5f6fda6dae58477f18b`.
- Phase I: `bce809c`, validation `978c5ef`, merged by PR #4 at `e5681c3`.
- Phase J: `f9def2c`, validation `ff3dd90`, merged by PR #5 at `b33e4d8`.
- Committed evidence: `PLAN.md`,
  `governance/sensitive-review-queue-policy.json`,
  `governance/sensitive-review-context-batch.json`, and
  `tools/test_sensitive_review_queue_consistency.py`.
- Current scoped recheck: 13 focused tests passed; the consistency checker
  returned `ok=true` and `write_performed=false`; governance drift returned
  `severity=ok` with three non-blocking warnings that repo-local core hook files
  are absent. These signals do not prove runtime enforcement or secret
  remediation.

## Owner Intervention And Observable Cost

| Case | Owner intervention | Observable cost | Missing cost evidence |
|---|---|---|---|
| Bookstore KNSH | None recorded for the bounded work item. Absence is unknown, not zero. | Four product commits plus one evidence/memory checkpoint; focused product diff covered 9 files with 1,393 insertions and 43 deletions; product receipts report about two seconds for pytest and under one-second receipt precision for the contract check. | Human minutes, token cost, monetary cost, and maintenance cost. |
| Bookstore registry / Actions | One direct owner correction: do not schedule recurring GitHub Actions because of quota cost. The branch expectation was also raised after direct-to-main delivery. | `9300875` spans 834 files including generated exports and images; non-export scope spans 38 files. `d8a6a1f` changes 2 files. The UI showed approximately 4m45s for the correction, but this is session-only agent elapsed time. | Durable owner-intervention artifact, human review minutes, Actions cost avoided, and maintenance cost. |
| Mei admin / checkout | None recorded for either bounded candidate. | Admin record reports two focused tests plus a build; checkout adds four files and three static assertions. | Deployment replay duration, rework avoided, owner assistance, and production outcome. |
| Enumd Phase I/J | None recorded for the bounded work item. | Two feature commits, two validation commits, two PR merges, two remote CI runs, and a current 13-test replay taking approximately two seconds locally. | Human review time, CI wall time/cost, later source-review rework, and maintenance cost. |

The costs are not comparable enough to calculate a benefit-to-cost ratio.
Generated-data diff size is not treated as human effort, and UI elapsed time is
not treated as owner review time.

## Transfer And Recurrence

Observed transfer:

- The two qualifying cases occur in separate consumer repositories and domains:
  commerce catalog integrity and private-vault security triage.
- Both show a bounded form of governance effect: separate the risky slice,
  preserve explicit authority, retain an honest unfinished state, and avoid
  an inflated completion claim.

Transfer gap:

- The same owner and closely related agent environment remain involved.
- There is no independent non-author completion without owner assistance.
- There is no sustained multi-week recurrence record for either qualifying
  behavior.
- No comparable before/after rework, reviewer time, false-positive rate, or
  false-negative rate is available for these five candidates.
- The Bookstore zero-effect case shows that governance adoption alone did not
  intercept a workflow-cost decision or guarantee branch discipline.

## G4 Contribution And Claim Ceiling

This checkpoint supports the following bounded claim:

> G3 core capabilities are mature, and the framework now has early
> multi-consumer G4 outcome evidence: two qualifying consumer work items, one
> observed zero-effect case requiring owner correction, and two unresolved
> consumer candidates.

It does not establish:

- G4 achieved;
- sustained or statistically comparable outcomes;
- independent non-author use without owner assistance;
- that governance benefit exceeds execution or maintenance cost;
- that receipts prove semantic correctness or authenticity;
- that all 17 Bookstore publishers completed a fresh live refresh;
- that Enumd credentials were reviewed, rotated, or remediated;
- that either meiandraybook fix succeeded in the deployed product; or
- that hooks, CI, gates, runtime, or enforcement changed in this checkpoint.

## Next Observation

Wait for the active meiandraybook agent to finish. Adjudicate the committed
deployment replay for the admin-order and checkout-skew fixes only after the
consumer workspace reaches a reviewable checkpoint. Do not manufacture a
replay, inspect its current dirty work, add a G4 schema/tool, or change another
consumer merely to increase the case count.
