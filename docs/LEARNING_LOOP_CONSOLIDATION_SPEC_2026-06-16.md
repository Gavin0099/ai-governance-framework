# Learning-Loop Consolidation — Design Spec (DRAFT)

> **Status**: DESIGN-ONLY. No runtime change, no enforcement change, no new
> authority surface. **Phase E is paused** — this spec is pause-gated: drafting
> it does not un-pause anything, and none of its tranches may start without an
> explicit trigger or un-pause decision.
> **Not committed authority.** This is a `docs/` proposal artifact, awaiting
> diff review. It does not override PLAN, AUTHORITY, or any governance codex.
> **Claim ceiling**: drafting this spec does NOT mean the learning loop exists,
> is operational, or is endorsed for build.

---

## Problem

The framework catches its most common failure class — claim / state drift
(derived surface or prose asserting more than canonical/evidence supports) —
**primarily through human review**. It already owns every organ of a learning
loop, but the organs are not wired into a loop:

- A reviewer finding flows to memory prose via `REVIEW_CRITERIA.md` §7
  (`memory/04_review_log.md`, `memory/03_knowledge_base.md`) **and stops there**.
- It does not deterministically become a *replayable* regression asset, a
  *classified* taxonomy entry, or a *claim-boundary* delta.

Consequence: the same failure class recurs in new shapes and is re-caught by a
human each time. The cost of a finding is paid once (catching it) but its value
is not banked (preventing the next instance automatically).

**Evidence (this session alone caught 5 distinct drift failures; none became a
re-runnable test):**

| # | Failure | Caught by | False claim it would have supported |
|---|---------|-----------|-------------------------------------|
| 1 | env-shadow ledger regression (CLI default shadowed `None`→env sentinel) | human review of `3221da6`, fixed `5e38638` | "no-write mode propagated" while Stop hook silently ignored env |
| 2 | mutation mandate drift (`616d90b` dropped the mandate; `19f451e` restored) | human review | memory asserting "PLAN now mandates…" while PLAN no longer held it |
| 3 | workflow trigger missing `memory/**` (P1-A) | reviewer thread before `5deb8bb` | CI memory blocker "covers memory tasks" while the trigger missed them |
| 4 | reviewer polling final/pending confusion | observed mid-session, recorded in PLAN claim boundary | a pending thread read as an ACCEPT verdict |
| 5 | source-hook ≠ installed-hook false negative | observed when P1-D advisory didn't fire until `hook_installer` re-run | "advisory is live" while `.git/hooks/pre-push` was stale |

The gap is **wiring existing parts into a loop, not building parts.**

## Target outcome

A reviewer finding deterministically produces, or is checkably linked to, three
existing-format artifacts:

1. a **taxonomy classification** — but see Open Design Question OQ-1: the repo
   has **three unreconciled category spaces**, and the claim/state-drift class
   these seeds belong to maps most naturally to `SEMANTIC_FAILURE_TAXONOMY.md`
   (SF-01..SF-07), **not** to `failure_disposition.FAILURE_KINDS` (which is the
   test-result disposition axis);
2. a **replayable eval case** (graduating `failure_mode_test_matrix.v0.1.json`),
3. a **claim-boundary delta** (referencing the de-facto claim ledger).

So the next occurrence of that failure class is caught by a re-runnable test,
not by a human noticing. The loop is **advisory/observational** — it never
auto-blocks (blocking would be a separate OP-HC decision, out of scope here).

## Scope

1. **Inventory** the existing taxonomy / claim / decision / memory / eval
   surfaces and state, for each, whether the design *references* or *extends*
   it (never duplicates).
2. **Define the ingestion loop**: reviewer finding → taxonomy entry → eval
   case → claim-boundary delta, naming the existing artifact at each hop.
3. **Define a minimal eval scenario schema** by graduating
   `failure_mode_test_matrix.v0.1.json` (status `draft`) — not a new system.
4. **Seed** with the 5 real failures above, mapped to the schema.

## Non-goals (mandatory)

- No new enforcement; no blocking path; nothing auto-fails a build.
- No runtime change.
- **No second taxonomy** — `SEMANTIC_FAILURE_TAXONOMY.md` +
  `failure_disposition.py` are the single classification source.
- No `governance_tools/_common.py` (deferred separately; no live trigger).
- No claim that the learning loop is operational, wired, or endorsed.
- No 8 new authority docs; this spec adds **zero** authority surfaces.
- Not IDE-native interception, not a multi-agent orchestration platform
  (outside repo boundary per tech-spec gotchas).

## Affected surfaces (referenced, not changed by this spec)

| Existing surface | Role in the loop | Design action |
|------------------|------------------|---------------|
| `governance/SEMANTIC_FAILURE_TAXONOMY.md` (SF-01..SF-07) | semantic failure modes — closest fit for the claim/state-drift class | **reuse** as the classification home for drift findings (see OQ-1) |
| `governance_tools/failure_disposition.py` | **test-result** disposition (`FAILURE_KINDS`: external_exclusion / integration_drift / platform_mock / stale_assertion / unknown) | **do NOT use** for drift findings — different axis; mislabeling here would itself be authority drift |
| `governance/failure_mode_test_matrix.v0.1.json` | draft machine-readable eval scenarios (`id`/`category`/`description`/`artifacts_under_test`) | **graduate** — the eval schema extends this, same shape |
| `governance/taxonomy_expansion_log.ndjson` | expansion signal (unknown_count vs threshold), currently dormant | **reactivate as signal source**, not new log |
| `governance/REVIEW_CRITERIA.md` §7 | reviewer ingestion → memory prose | **extend the tail** — prose hop gains a structured-asset hop |
| `memory/03_knowledge_base.md` | anti-pattern store | **link**, not replace |
| PLAN claim boundaries + `governance/CLAIM_ENFORCEMENT_EVIDENCE_POLICY.md` | de-facto, scattered claim ledger | **index/consolidate by reference**; PLAN stays canonical source |

## Boundary and API considerations

- **Eval schema MUST extend** the v0.1 matrix fields (`id`, `category`,
  `description`, `artifacts_under_test`, `scenarios[]`). `category` MUST resolve
  to a *named, existing* taxonomy value — but **which** taxonomy is OQ-1 below.
  The v0.1 matrix today uses a runtime-failure-mode set
  (`missing_required_evidence`, `invalid_evidence_schema`, `policy_conflict`,
  `runtime_failure`, `determinism_replay`) that is itself a *third* space,
  distinct from both SF-codes and `FAILURE_KINDS`. No new category space may be
  invented by this loop.
- **Taxonomy expansion stays reviewer-gated** — the loop may *propose* a new
  `FailureKind` but cannot self-add one (preserves the existing trust rule).
- **Claim ledger consolidation is by reference**: an index that points at the
  authoritative PLAN claim-boundary blocks; it does not become a second source
  of truth (that would be the exact authority-drift this framework fights).
- **Replay portability**: eval cases MUST be machine-independent (no absolute
  paths / drive letters) — this session already hit the `D:\meiandraybook`
  cross-machine drift; the schema must not repeat it.

## Failure paths / risk points

- **Eval landfill** — low-value cases accumulate; mitigate by admitting only
  cases traceable to a *real* reviewer finding (no fabricated scenarios), mirroring
  the deferred-debt-report discipline from P1-D.
- **Second-taxonomy drift** — if `category` ever diverges from `FAILURE_KINDS`,
  two taxonomies disagree. Mitigation: schema validation pins `category` to the
  frozenset.
- **Loop creeping into enforcement** — any auto-block silently violates the
  Phase E pause. Mitigation: the loop is observational; blocking is an explicit
  separate OP-HC decision with its own mutation contract.
- **Fabricated seeds** — seeds not tied to real commits/memory weaken evidence.
  Mitigation: each seed cites a commit or memory record from this session.
- **Spec-as-commitment** — drafting ≠ approval to build (tech-spec gotcha).

## Evidence plan (tied to repo tools)

- **Classification**: validate seed `category` values against
  `failure_disposition.FAILURE_KINDS` (read-only check, no new tool).
- **Replay**: a future eval runner would follow the existing pattern of
  `scripts/run_e8a_fixture.py` / `scripts/replay_verification.py` — referenced,
  not built in this spec.
- **Signal**: `taxonomy_expansion_log.ndjson` already records unknown-vs-threshold;
  the loop reads it rather than inventing a signal.
- **For this spec itself (design-only)**: the only evidence required is that the
  5 seed cases each trace to a real commit/memory record (table above), and that
  the affected-surfaces table cites artifacts that exist. No runtime evidence is
  claimed.

## Open design questions (must be answered before any tranche)

- **OQ-1 (taxonomy reconciliation) — surfaced while drafting this spec.** The
  repo holds **three unreconciled category spaces**: (a) `FAILURE_KINDS`
  (test-result disposition), (b) the v0.1 matrix runtime-failure-mode set, (c)
  `SF-01..SF-07` (semantic). A claim/state-drift finding has no single obvious
  home. The loop cannot "just add a taxonomy entry" until this is decided. This
  is a *design decision*, not a wiring detail, and it is itself an instance of
  the framework's own authority-fragmentation problem. **Recommendation**: adopt
  SF-codes as the home for the drift class and record the cross-walk to the
  other two spaces by reference — but this needs explicit ratification, not a
  default.
- **OQ-2**: does the ingestion loop terminate at "linked artifacts exist"
  (advisory) or does it ever assert a re-run gate? This spec assumes the former;
  the latter is a separate OP-HC decision.

## Implementation tranche recommendation

**Smallest meaningful first tranche (still pause-gated; needs trigger/un-pause):**

> One eval case — **#1 env-shadow regression** — expressed in the graduated
> schema, because it is the only one of the five with *empirical before/after
> proof already captured this session* (regression demonstrated, fix demonstrated).
> Plus the one-page ingestion-loop wiring description (finding→kind→eval→claim).
> **Design/draft artifacts only — no runner, no enforcement, no runtime touch.**

Explicitly **not** in the first tranche: the other 4 seeds, any eval *runner*,
any CI wiring, any claim-ledger file. Each subsequent tranche is independently
pause-gated and trigger-required.

**Recommended gate before any tranche starts**: an explicit un-pause decision
(or a real new occurrence of one of the 5 failure classes, which would itself be
the failure-driven trigger).

---

## Provenance

- Seeds and surface citations are drawn from the 2026-06-12 → 2026-06-16 session
  work (commits `5e38638`, `19f451e`, `5deb8bb`, `9ba68ec`; memory records in
  `memory/2026-06-1*.md`).
- Architecture-impact preview NOT run: this spec proposes no code change, so
  touched-file estimation is N/A by design.
