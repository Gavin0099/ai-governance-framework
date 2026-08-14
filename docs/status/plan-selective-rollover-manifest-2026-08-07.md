# PLAN.md selective rollover — manifest (2026-08-07)

> Status: **proposal. No content has been moved.** This manifest exists so the
> rollover can be reviewed item by item before PLAN.md is touched.
>
> **DEPENDENCY — this manifest is a framework-repo pilot only.** It does not
> establish rules that consumer repositories share. Owner adjudication of the
> nine standing constraints and execution of the rollover depend on a
> framework-wide **PLAN lifecycle contract review**, which does not yet exist.
> That review must settle: PLAN profile differences, the consumer template,
> rollover/retention policy, the summary parser contract, semantic freshness,
> and adoption/refresh migration behaviour.
> `governance/fleet/plan_profile_contract.yaml` currently states that
> validation, profile-aware freshness, fleet reporting and consumer remediation
> do **not** yet exist.
>
> **Open ordering decision (owner):** whether this pilot runs first and informs
> the contract, or waits until the contract is approved. The two orderings have
> different rework profiles and this document does not pick one.
> Baseline: `main = f3c9f28e`, PLAN.md 1742 lines, Last Updated 2026-07-30
> (STALE against the 7d Sprint threshold).

## Measured state

| Section | Lines | Share |
|---|---|---|
| Canonical Planning Surface | 25 | |
| Encoding Repair Notice - 2026-06-10 | 23 | |
| Phase Overview | 8 | |
| Work Item Glossary | 34 | |
| **Current Sprint - 2026-06-10** | **514** | 30% |
| Active Claim Boundaries | 196 | 11% |
| **Pending Work - Ordered** | **804** | 46% |
| Canonical Memory Provenance Tranche 1 (completed 2026-07-27) | 35 | |
| Dirty Workspace Policy | 49 | |
| Historical Milestone Index | 21 | |
| Definition Of Done For Current Planning Slice | 20 | |
| Cannot Claim From This PLAN Alone | 12 | |

Checkbox census — **three states, not two**:

| State | Glyph | Count |
|---|---|---:|
| completed | `- [x]` | **175** |
| unchecked | `- [ ]` | **16** |
| **in progress** | `- [>]` | **1** |

The single `[>]` is `PLAN.md:57` — **Phase E, the current phase**. Revision 1
reported "176 checked" by folding `[>]` into completed, which would have
archived the active phase marker as finished work. **`[>]` Phase E stays in the
root PLAN's Phase Overview.**

## The finding that changes the design

**The 16 unchecked boxes are not 16 open work items.** Reading each one in full
context, they fall into three kinds:

| Kind | Count | Nature |
|---|---|---|
| **A — Standing constraint / claim boundary** | **11** | Will never be checked, because it is policy, not a task |
| B — Genuinely open work | **4** | **Three** of those are explicitly gated, deferred, or blocked |
| C — Status note | **1** | Bold prose describing state, formatted as a checkbox |

> **Revision 2 correction.** Revision 1 classified the Gate 3 item (L1577) as
> Kind C and marked it for archival. That was wrong: its own text ends
> *"Gate 3 remains blocked on independent review of these revised bytes,
> explicit owner signature, later promotion, natural-bug/resource admission and
> separate start authority."* It is gated open work, not a historical note. The
> misclassification came from reading the item's **format** (bold prose) rather
> than its ending. Counts above are corrected.

One of them says so in its own text: L1245 ends with
`(Standing constraint; restated in policy v1 §5.)` — a permanent policy
expressed as an unchecked checkbox.

**Open work in this PLAN is four items: one currently ungated** (L1262), plus
three held by explicit decision — `topics` (gated), `README badge` (deferred),
and `Gate 3` (blocked pending independent review and owner signature).

### Why this matters for growth

PLAN.md grows for two reasons, and they are the same disease — no retirement
path — but the second is worse:

1. **Completed work is never removed.** 175 completed items accumulate.
2. **Constraints are recorded in a task list.** A `- [ ]` that can never be
   checked is a permanent line. The section can only grow.

The second is a category error, not a housekeeping lapse. The correct home
already exists: `## Active Claim Boundaries` (196 lines) already uses the
`CLAIMED / NOT CLAIMED` prose form, which is the right shape for a constraint.

This also explains why the Current Sprint section is titled `2026-06-10` and is
514 lines: it is not a sprint, it is a two-month accumulation.

## Item-by-item disposition — all 16 unchecked items

**These dispositions are proposals. Nothing marked "obsolete" or "done" should
be actioned without owner confirmation** — the manifest cannot tell from the
text alone whether a constraint is still in force.

### Current Sprint - 2026-06-10

| Line | Kind | Text (abbrev.) | Proposed disposition |
|---|---|---|---|
| 315 | A | For every other framework-expansion direction, wait for a real consumer failure or a new product need before opening a slice | → Active Claim Boundaries, as prose |
| 392 | A | Do not start v1.3.0 release-prep until the scoped release-surface consistency packet … | → Active Claim Boundaries (release gating) |
| 400 | A | Use the completed inventory-line results as historical input only | → Active Claim Boundaries |
| 403 | A | Keep any context-cost companion record as a future candidate only until … | → Active Claim Boundaries |

### Pending Work - Ordered

| Line | Kind | Text (abbrev.) | Proposed disposition |
|---|---|---|---|
| 1245 | A | Do not claim structured memory sync is solved by daily memory writer completion alone — *self-labelled "Standing constraint"* | → Active Claim Boundaries |
| 1262 | **B** | **Collect retrospective E2 adoption evidence from the two engineer onboardings** | **stays — Active Backlog. The one genuinely actionable item** |
| 1266 | A | Record evidence grade explicitly as retrospective / self-reported | **stays with L1262 as acceptance criteria** — drop the checkbox, keep it directly under the task. Do NOT move to the generic Active Claim Boundaries: that would separate the task from its acceptance condition |
| 1267 | A | Do not claim sustained lifecycle, E2 closure, or low framework … | **stays with L1262 as acceptance criteria**, same reason as 1266 |
| 1293 | B | Add relevant topics (Gated by P2-E: allowed only after exact-list ratification) | stays — Active Backlog, marked **gated** |
| 1295 | B | Align README badge with current release state (P2-E: DEFERRED until first gated release) | stays — Active Backlog, marked **deferred** |
| 1360 | A | Publish a release only after release notes and claim ceiling are … | → Active Claim Boundaries (release gating) |
| 1451 | A | Maintain historical `missing_canonical_memory` / `unbound_memory` debt as warning evidence | → Active Claim Boundaries |
| 1453 | A | Keep CE-1D historical raw packet disposition separate from current runtime … | → Active Claim Boundaries |
| 1455 | A | Do not backfill receipts or rewrite memory history without reviewer-approved … | → Active Claim Boundaries |
| 1530 | C | **Gate 2 execution artifacts preserved; process integrity `NOT_ESTABLISHED`, corrected 2026-07-28** | **split.** The long execution record (arm order, scorer submissions, artifact paths, commit `1d12f6d1`) → archive. But it carries a live claim boundary — *process integrity `NOT_ESTABLISHED`; the earlier `PASS` is withdrawn; Skill effectiveness not claimable* — which **must stay in root PLAN in condensed form** |
| 1577 | **B** | **Gate 3 paired-screening preregistration candidate revised 2026-07-29; re-review/signature pending** | **stays — Active Backlog, marked `blocked pending independent review and owner signature`.** Its text explicitly states Gate 3 remains blocked on independent review, owner signature, promotion, admission and separate start authority. Revision 1 wrongly marked this for archival |

Net effect on the root PLAN's task surface: **4 open items** — one currently
ungated (L1262) and three held by explicit decision (L1293 gated, L1295
deferred, L1577 blocked). Two acceptance-criteria lines (L1266, L1267) stay
attached to L1262 rather than moving.

## Target structure of the root PLAN

Retained, per the canonical planning protocol (`governance/PLAN.md`):

- Canonical Planning Surface (header, Last Updated, Freshness, owner)
- Phase Overview — current phase
- Work Item Glossary
- **Current Sprint** — retitled to the real current date, containing only
  present work
- **Active Backlog** — the 4 items above, each marked with its hold state
  (ungated / gated / deferred / blocked); L1266 and L1267 stay attached to
  L1262 as its acceptance criteria
- **Active Claim Boundaries** — absorbs the **9** standing constraints that are
  not task-specific, plus a condensed Gate 2 boundary (process integrity
  `NOT_ESTABLISHED`, earlier `PASS` withdrawn)
- Definition Of Done For Current Planning Slice
- Cannot Claim From This PLAN Alone
- Dirty Workspace Policy
- Historical Milestone Index
- **Archive pointer** — new, one line

Moved to `docs/status/plan-archive-2026-08.md`:

- the **175** `- [x]` items with their surrounding context — **not** the `[>]` Phase E marker, which stays
- `## Canonical Memory Provenance Tranche 1 (completed 2026-07-27)` — the title
  already says completed
- the Gate 2 long execution record, as prose — **but not its claim boundary**,
  which stays in root PLAN
- `## Encoding Repair Notice - 2026-06-10` — a 2-month-old one-off notice

## Review scope for the rollover (owner-set, 2026-08-07)

This rollover reclassifies governance state, so it gets one full semantic
review — misfiling one item can remove a live gate or claim boundary from daily
view. The review does **not** re-check the technical correctness of the 175
completed items.

| # | Scope | Check |
|---|---|---|
| 1 | Source completeness | All 175 completed, 16 unchecked and 1 in-progress item have exactly one disposition — none missing, none duplicated, and `[>]` is not silently folded into either bucket |
| 2 | Semantics of the 16 | Each read in full, not by first line. Specifically: the 4 real work items remain in root PLAN; L1266/L1267 remain attached to the E2 work; Gate 2's history archives but its `NOT_ESTABLISHED` boundary stays; Gate 3 stays blocked |
| 3 | The 9 standing constraints | **Owner adjudicates each**: still in force → Active Claim Boundaries; superseded → archive **naming the successor**; lifted → record the basis. **Silent deletion is not an option** |
| 4 | Operability of the new PLAN | An agent opening it cold can answer: which phase; what is the one ungated item; which three are gated/deferred/blocked; what cannot be claimed; what is the next executable action |
| 5 | Historical recoverability | Archive preserves original text and context, records source commit and original section, is one click from root PLAN, and is never described as canonical current state |
| 6 | Mechanical verification | Raw-inventory item identity before/after; every active item and claim boundary has a destination; `git diff --check`; freshness; drift checker; baseline refresh `--dry-run` first |

`plan_summary.py` is not an acceptance oracle until its backlog blind spot is
fixed.

This is intended as the final full semantic review **for this pilot, and only
once the framework-wide PLAN lifecycle contract is approved**. If that contract
later changes active-backlog representation, claim-boundary placement, archive
provenance, PLAN profile, freshness, or summary rules, this PLAN needs
re-review. Afterwards, routine review covers only additions, closures, and
cross-period rollover.

## DONE criteria

**DONE is not a line count.** Explicitly:

1. Every item classified B is still reachable from the root PLAN.
2. Every Kind-A constraint is preserved **at its declared destination**: nine
   in Active Claim Boundaries, and L1266/L1267 as acceptance criteria attached
   to L1262. None is silently dropped, and none is moved somewhere the
   disposition table did not say.
3. **Active-item parity is measured against the raw `PLAN.md` checkbox
   inventory, before and after.** `plan_summary.py` is explicitly **not** the
   parity oracle: this same document proves it reports 12 backlog items as
   zero, so requiring its output to match before and after would only prove
   that a known-broken summary stayed equally broken.
   Two acceptable forms:
   - **If `plan_summary.py` is fixed first:** confirm it lists every retained
     item, and it may then serve as a secondary check.
   - **If it is not fixed first:** treat its output as auxiliary information
     only, and do not make it a DONE gate.
4. Archived content is reachable by one link from the root PLAN.
5. Required semantic surfaces (current phase, active sprint, backlog,
   anti-goals/claim boundaries, next measurable slice) all still present.

Line count is an outcome, not a target. On these dispositions the root PLAN
lands near 400–500 lines, but a rollover that hits 400 lines while dropping an
active item has failed.

## Verification plan

| Check | Command |
|---|---|
| freshness | `python -X utf8 governance_tools/plan_freshness.py` |
| active-item parity — **primary** | raw `PLAN.md` checkbox inventory before/after, compared on item identity and surrounding context, not just count |
| active-item parity — **secondary** | `python -X utf8 scripts/plan_summary.py`, **only after the backlog blind spot is fixed**. Until then it is auxiliary output and not a DONE gate |
| structural drift | `python -X utf8 governance_tools/governance_drift_checker.py --repo . --format human` |
| baseline refresh side effects | `adopt_governance` refresh **`--dry-run` first** — it recomputes baseline hashes and may touch the managed `.gitignore`; it is not side-effect-free |
| scoped diff | `git diff -- PLAN.md docs/status/plan-archive-2026-08.md` |
| whitespace | `git diff --check` |

## Separate finding: `plan_summary.py` backlog blind spot

Measured on `f3c9f28e`:

```
## Open Sprint Items          <- 4 items, correct
## Backlog Open: P0=0  P1=0  P2=0
```

The Pending Work section contains 12 unchecked items; `plan_summary` reports
zero. Since `plan_summary` exists to reduce AI reading cost, an agent relying on
it would conclude there is no backlog work at all.

**Consequence for this rollover: `plan_summary` must not be used as the source
of truth for what to archive.** The dispositions above were derived from the raw
file.

This is a defect in `plan_summary.py`, not in PLAN.md, and should be fixed
separately from the rollover — fixing it first would also give a trustworthy
parity check for step 3 of the DONE criteria.

## What this manifest does not do

- It does not move anything.
- It does not decide whether a Kind-A constraint is still in force. Several
  reference decisions (P2-E ratification, v1.3.0 release-prep gating) whose
  current status the owner knows and this document does not.
- It does not propose a framework feature. Any report-only PLAN maintenance
  signal should wait until this manual pilot has run once and shown what the
  real cost and failure modes are.
