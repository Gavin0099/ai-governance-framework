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

1. a **taxonomy classification** — recommended as Layer 1 (SF-code) under the
   layered taxonomy model in OQ-1 (**ratified 2026-06-17**);
   `failure_disposition.FAILURE_KINDS` is Layer 3 (result disposition), not the
   primary finding axis;
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
| `governance_tools/failure_disposition.py` | **Layer 3 — result disposition** (`FAILURE_KINDS`: external_exclusion / integration_drift / platform_mock / stale_assertion / unknown) | **reuse only as the post-run result axis**; never the primary finding taxonomy (that is Layer 1 / SF-codes). Using it as the primary axis would itself be authority drift |
| `governance/failure_mode_test_matrix.v0.1.json` | draft machine-readable eval scenarios (`id`/`category`/`description`/`artifacts_under_test`) | **graduate** — the eval schema extends this, same shape |
| `governance/taxonomy_expansion_log.ndjson` | expansion signal (unknown_count vs threshold), currently dormant | **reactivate as signal source**, not new log |
| `governance/REVIEW_CRITERIA.md` §7 | reviewer ingestion → memory prose | **extend the tail** — prose hop gains a structured-asset hop |
| `memory/03_knowledge_base.md` | anti-pattern store | **link**, not replace |
| PLAN claim boundaries + `governance/CLAIM_ENFORCEMENT_EVIDENCE_POLICY.md` | de-facto, scattered claim ledger | **index/consolidate by reference**; PLAN stays canonical source |

## Boundary and API considerations

- **Eval schema (OQ-1 ratified — layered model)**: extend the v0.1
  matrix but **split the single `category` into the three layers** so different
  questions live in different fields rather than one flattened enum:
  ```json
  {
    "id": "LL-ENV-SHADOW-001",
    "semantic_failure": "SF-05",
    "scenario_type": "deterministic_repo_behavior",
    "description": "CLI default shadowed None into the env sentinel...",
    "artifacts_under_test": ["governance_tools/...", "scripts/hooks/..."],
    "expected_signal": "warning",
    "result_disposition": null
  }
  ```
  `semantic_failure` = what the failure is (Layer 1 / SF-code).
  `scenario_type` = how to check it (Layer 2 / replay shape).
  `result_disposition` = filled **only after a run** (Layer 3 / `FAILURE_KINDS`);
  if no run yet it stays `null` and is never the seed's primary classification.
  No new category space is invented; the v0.1 `category` field is superseded by
  these named layers, not by a fourth taxonomy.
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
- **Layer-collapse drift** — the risk is conflating the three layers
  (semantic / scenario-type / result-disposition) into one `category` enum.
  Mitigation: keep them as separate fields; pin `semantic_failure` to SF-codes
  and `result_disposition` to `FAILURE_KINDS`, and never use the result axis as
  the primary finding classification. (OQ-1 ratified — layered model.)
- **Loop creeping into enforcement** — any auto-block silently violates the
  Phase E pause. Mitigation: the loop is observational; blocking is an explicit
  separate OP-HC decision with its own mutation contract.
- **Fabricated seeds** — seeds not tied to real commits/memory weaken evidence.
  Mitigation: each seed cites a commit or memory record from this session.
- **Spec-as-commitment** — drafting ≠ approval to build (tech-spec gotcha).

## Evidence plan (tied to repo tools)

- **Classification**: validate a seed's `semantic_failure` against
  `SEMANTIC_FAILURE_TAXONOMY.md` SF-codes (read-only, no new tool).
  `scenario_type` is a separate replay-shape field; `result_disposition`
  (`FAILURE_KINDS`) is NOT a seed field — it is filled only after a run, never
  as the primary classification. (OQ-1 ratified — layered model.)
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

- **OQ-1 (taxonomy reconciliation) — RESOLVED: owner-ratified 2026-06-17.** The
  repo holds three category spaces that answer three *different* questions; a
  flat merge would crush three abstraction layers into one enum. The ratified
  resolution is a **layered taxonomy framework, not a flat merge**:
  - **Layer 1 — Semantic failure (primary).** `SEMANTIC_FAILURE_TAXONOMY.md`
    SF-codes answer "what is this failure, semantically?" A reviewer finding is
    classified here first (e.g. SF-05 Evidence Mismatch). This is the primary
    taxonomy for the learning loop.
  - **Layer 2 — Eval scenario type (replay shape).** Answers "if this finding
    becomes an eval, what *kind* of check is it?" — e.g.
    `deterministic_repo_behavior`, `artifact_consistency_check`,
    `operator_reality_misread`, `hook_installation_state_check`. Separate field
    about *how to test*, not *what the failure is*; does not replace or compete
    with the SF-code.
  - **Layer 3 — Result disposition.** `failure_disposition.FAILURE_KINDS`
    (`integration_drift`, `stale_assertion`, `platform_mock`,
    `external_exclusion`, `unknown`) answers "after an eval runs and fails, how
    is that result handled?" A test-result axis only; must NOT be the primary
    taxonomy for reviewer findings.
  - Cross-walk among the three layers is **referential and read-only**; it does
    not collapse them into one enum and does not create a fourth taxonomy or a
    second source of truth.
  - **Status: RESOLVED (owner-ratified 2026-06-17).** Ratification text: SF-code
    is the primary taxonomy for reviewer findings; eval scenario type is a
    separate replay-shape axis for eval cases; `FAILURE_KINDS` remains
    `result_disposition` only, for post-run test/eval interpretation;
    cross-walks are read-only references only — no flat merge, no fourth
    taxonomy, no direct substitution across layers.
  - **Claim ceiling (critical — do not overclaim).** Ratifying OQ-1 removes
    ONLY the taxonomy gate. It does **not** unpause learning-loop
    implementation. OQ-2 already fixes the loop to advisory-only, and Gate 3
    (un-pause / repeated drift-class trigger) is still unmet. **Permitted now**:
    taxonomy-alignment prep only — spec status, schema field definitions,
    read-only cross-walk rules, and advisory-only validator tests that prevent
    `FAILURE_KINDS` being used as the primary finding taxonomy. **Not
    permitted**: CI blocker, completion gate, re-run gate, or any claim that
    learning-loop implementation has started. Correct claim: "OQ-1 ratified;
    taxonomy blocker removed; implementation remains limited to advisory / spec
    / schema preparation until un-pause criteria are met."
- **OQ-2 (advisory terminus vs re-run gate) — RESOLVED: owner-ratified
  advisory-only (2026-06-16).** The loop terminates at "structured record →
  taxonomy / memory / eval / claim-boundary linkage → future warning/reminder
  signal in later reviews." It does **not** introduce a re-run gate, CI
  blocking, completion blocker, or any build/closeout auto-fail. Owner
  rationale: taxonomy spaces are not yet reconciled and the eval schema is still
  draft/graduation; a premature gate would turn immature classification and
  draft artifacts into real authority, risking new claim/authority drift. Any
  future enforcement is a separate OP-HC decision with its own mutation
  contract, out of scope here.

## Design notes (non-enforcement; folded from review 2026-06-16)

These refine the design without adding enforcement, runtime, validator, CI, or
authority surfaces.

- **Two eval classes (becomes Layer-2 `scenario_type`).** Findings split into
  (a) deterministic repo-behavior failures (env-shadow regression,
  workflow-trigger bypass, source-vs-installed hook) which fixture cleanly, and
  (b) operator-reality-misread failures (stale-summary claim,
  viewer-artifact-vs-file corruption, analyze-vs-apply overrun) which are about
  agent/reviewer discipline and may NOT be expressible as a deterministic
  fixture. They share Layer 1 (SF-code) but differ at Layer 2 (`scenario_type`);
  class (b) may need a process/discipline check, not a fixture. Banking is not
  monotonically good — admit only high-signal reproducible cases (see Eval
  landfill).
- **Claim-boundary linkage must derive from PLAN.** The loop's claim-boundary
  hop indexes/points at PLAN's authoritative claim boundaries; it must not
  become a second source of truth. Open authority consideration, same family as
  OQ-1; not ratified here.
- **Banking is earned, not automatic.** The loop makes *re-running* a banked
  eval automatic, but the *creation* of each eval (choosing the assertion,
  writing the fixture, binding the claim) stays a deliberate per-finding capture
  act. It reduces re-detection cost for *known* failure classes only; it does
  not run for free and decays without sustained capture. Compounding is earned,
  not a free flywheel.

## Gate boundaries: taxonomy-alignment prep vs Gate-3 rollout

OQ-1 and OQ-2 are resolved; **Gate 3 (un-pause) is NOT open.** This section
fixes what may be built now vs what must wait, so the boundary is not
self-expanded by an agent.

**Allowed now — taxonomy-alignment prep** (make the ratified layered model
representable + statically checkable; no loop, no gate, no completion effect):

- update schema field names: `semantic_failure` / `scenario_type` /
  `result_disposition`;
- update eval fixtures / seed format to express the layered taxonomy;
- add static validators that check schema *shape*;
- add advisory-only validators that check: reviewer findings use
  `semantic_failure` / SF-code as primary; `result_disposition` is not
  prefilled before an eval runs; `scenario_type` does not alias a semantic
  failure name; `FAILURE_KINDS` appears only as `result_disposition`;
- add tests proving these validators emit **warning/advisory/report only** —
  they do NOT block CI or completion;
- update docs, examples, sample JSON, read-only cross-walk references.

**Not allowed until Gate 3 un-pause — implementation rollout** (changes
governance *consequences*):

- automatic banking of reviewer findings into a learning-loop bank;
- automatic eval-case generation into a regression suite;
- wiring any learning-loop validator into a CI blocker;
- feeding learning-loop results into `completion_claim_allowed`;
- turning advisory warnings into fail/blockers;
- adding blocking behavior to `memory_workflow` / `governance_drift_checker` /
  pre-commit / pre-push;
- claiming repeated drift-class is regression-protected;
- claiming the learning loop is unpaused / implemented / enforced.

> **One line:** prep may validate taxonomy *shape*; rollout changes governance
> *consequences*.

The "advisory validator that prevents `FAILURE_KINDS` as primary" is allowed
prep **only if**: advisory-only; its test merely proves detection; not wired to
CI/completion; claims neither enforcement nor unpause. It may claim "detects
taxonomy layer misuse" — **not** "prevents taxonomy drift", and certainly not
"learning-loop gate is active".

## Gate 3 opening criteria

Gate 3 opens ONLY when **all** of the following hold — it does **not** open just
because OQ-1 and OQ-2 are resolved:

1. **Repeated drift-class trigger** — at least two comparable reviewer findings
   (or owner-confirmed examples) map to the same `semantic_failure` class or a
   clearly related SF-code cluster. A single finding may be banked as a seed but
   must not open Gate 3.
2. **Advisory signal proof** — advisory checks / prototype validators show the
   class can be detected without unacceptable false positives and without
   collapsing `semantic_failure` / `scenario_type` / `result_disposition`.
3. **Stable minimal schema** — the seed schema can represent `semantic_failure`,
   `scenario_type`, `result_disposition`, `expected_signal`,
   `artifacts_under_test` without using `FAILURE_KINDS` as the finding taxonomy.
4. **Bounded rollout scope** — the first rollout is explicitly limited to
   advisory-only; no CI blockers, completion gates, re-run gates, or automatic
   enforcement. Split: **Gate 3A** = implementation allowed, advisory-only;
   **Gate 3B** = enforcement consideration, ratified separately.
5. **Explicit owner unpause** — the owner explicitly records that Gate 3 is
   satisfied and authorizes the next rollout slice, in spec / PLAN / memory.
   Agents may NOT infer Gate 3 from OQ-1/OQ-2 being resolved.

**Current status:** OQ-1 done, OQ-2 done, **Gate 3 NOT opened.** Permitted next:
taxonomy-alignment prep only.

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
