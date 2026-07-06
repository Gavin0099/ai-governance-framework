# Active Task

> Refreshed 2026-07-06 per `docs/structured-memory-freshness-policy.md`.
> Dedicated bookkeeping slice; source surfaces: `PLAN.md` at HEAD
> `86257f97`, `memory/2026-07-06.md`, and
> `.venv\Scripts\python.exe -m governance_tools.governance_drift_checker
> --repo . --format json`.
> Claim: point-in-time consistency with `PLAN.md` and current repo state only.

## Current Focus

- **No active autonomous implementation slice.** Current workspace was synced
  to `origin/main` at `86257f97` before this bookkeeping refresh.
- Standing principle: **Validity before Expansion**. Do not add gates,
  enforcement, schema changes, or consumer-repo writes unless an observed
  failure or explicit user scope justifies them.
- Current workline: reduce governance overhead by observing which governance
  outputs change decisions before merging, downgrading, retiring, or promoting
  more surfaces.
- Current report-only implementation line: `test_signal_quality_audit` v0.2
  exists for domain contract repos. It surfaces weak test-signal candidates and
  validator fixture-pair visibility; it is not a readiness gate or test-quality
  proof.
- Current design line: `decision-change-ledger.seed.json` and
  `context-cost-budget-design-2026-07-06.md` are observation/design artifacts.
  They do not retire defenses, measure token savings, or enforce context-budget
  compliance.

## Current Status

- **Retire-candidate focused review completed (2026-07-06)**: four inventory
  retire candidates were reviewed. `promotion_gate_receipt_smoke.py` is the
  only retire-safe candidate for a later deletion slice; `clean_pilot_admissibility.py`
  needs a clean-pilot policy decision, `host_agent_memory_sync_signal.py` needs
  host-memory sync disposition, and `r49x4_metric_ranking.py` needs artifact
  provenance/freeze handling before deletion.
- **Promotion gate duplicate smoke removed (2026-07-06)**:
  `governance_tools/promotion_gate_receipt_smoke.py` was deleted after focused
  digest regression tests confirmed replacement coverage. Promotion-gate
  behavior, contract version, gates, hooks, and CI were not changed.
- **Planning alignment repaired in this slice**: prior active-task state still
  pointed at 2026-06-18 / `f21350e`; `PLAN.md` now records 2026-07-06 current
  focus, milestone commits, claim ceilings, and non-claims.
- **Governance drift baseline before repair**:
  `governance_drift_checker` reported `ok=true`, `severity=ok`,
  `plan_inventory_current=true`, and `plan_freshness=true`.
- **Test-signal quality audit line**: report-only v0.2 tooling is committed
  through `1c9abeff`; 2026-07-06 memory records cite 19 focused tests, fixture
  manifest hardening, fixture-runner visibility, and dogfood observations.
- **Semantic test-quality guidance**: committed at `a5ae276e`; consumer-facing
  update instructions now state independent expected values, regression tests
  for reproducible bugs when feasible, no happy-path-only tests for
  non-trivial changes, mock-only weakness, and validator fixture expectations.
- **Design-note consolidation line**: retrieval-authority and cache-aware
  design clusters now have summary/index docs, classification metadata, and
  source-note pointer banners. Source notes remain preserved and are not
  archived, invalidated, or reclassified by pointer banners.
- **Decision-change ledger seed**: committed at `023c65c0`; it classifies
  recent governance outputs by decision effect and explicitly leaves the
  inventory-line pass as not run.
- **Context-cost budget design**: committed at `5add91e5` and recorded at
  `86257f97`; it separates agent context-read accounting from the
  decision-change ledger and keeps companion records future-candidate only.

## Pause Conditions

- Do not start v1.3.0 release-prep until scoped release-surface consistency
  and named consumer-side proof packets are collected and reviewed.
- Do not promote `test_signal_quality_audit` into readiness, CI, hook, or gate
  behavior without a separate observed-failure-driven scope.
- Do not retire, merge, or downgrade governance defenses from the seed ledger
  alone. A read-only inventory-line pass and rare-critical safety review are
  required first.
- Do not implement context-cost companion records until there is evidence that
  they change decisions without becoming extra governance noise.

## Next Steps

1. Run a read-only decision-change ledger inventory-line pass over governance
   tools, governance docs/protocols, managed instruction surfaces, hook/CI
   entrypoints, and existing seed classifications.
2. Classify candidates as `decision_changing`, `decision_relevant_unacted`,
   `duplicate`, `noisy`, `zombie_candidate`, `rare_critical`, or `unknown`.
3. Recommend one follow-up action only: keep, keep_observe, merge, downgrade,
   retire_candidate, or investigate. Do not implement the recommendation in
   the same slice.
4. Remaining retire-candidate work is decision-only first: decide the
   clean-pilot policy disposition, host-memory sync disposition, and R49.x
   artifact-freeze/provenance handling before deleting any of the other three
   reviewed candidates.

## Historical Context Retained

- Phase E remains in validity-before-expansion posture.
- Cache-aware / AUTHORITY_MANIFEST remains candidate-only without prompt-cache
  control, runtime hook wiring, or harness adoption.
- Learning-loop Gate 3 remains closed; advisory prep does not authorize
  banking, replay generation, CI blockers, or completion gates.
- Public publish surfaces remain gated: GitHub topics require exact-list
  ratification, badge waits for a gated release, and release publish requires
  accurate Claim-class release notes.
- Historical `missing_canonical_memory` / `unbound_memory` debt remains warning
  evidence unless a scoped cleanup is approved.

## Cannot Claim From This Surface

- Cannot claim structured-memory freshness is automated or solved.
- Cannot claim all historical evidence is represented here.
- Cannot claim external repos are updated.
- Cannot claim test quality is enforced or industry-grade.
- Cannot claim any governance defense has been retired, downgraded, or proven
  useless.
- Cannot claim context savings were measured.
