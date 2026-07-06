# Active Task

> Refreshed 2026-07-06 per `docs/structured-memory-freshness-policy.md`.
> Dedicated bookkeeping slice; source surfaces: `memory/2026-07-06.md` and
> `memory/04_review_log.md` at HEAD `e4ede650`.
> Claim: point-in-time consistency with `PLAN.md` and current repo state only.

## Current Focus

- **No active autonomous implementation slice.** Current workspace was synced
  to `origin/main` at `e4ede650` before this bookkeeping refresh.
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

- **Decision-change inventory-line pass completed (2026-07-06)**: committed at
  `e30b1576` as `docs/governance/decision-change-ledger.inventory.v0.1.json`.
  All 193 governance_tools modules were compared against wiring and output
  evidence; 40 candidates were escalated, 4 marked retire_candidate.
- **Retire-candidate focused review completed (2026-07-06)**: four inventory
  retire candidates were reviewed. Two are now resolved (see below); the two
  still open are `clean_pilot_admissibility.py` (needs a human clean-pilot
  policy decision) and `host_agent_memory_sync_signal.py` (needs a
  deprecate-first host-memory sync disposition).
- **Promotion gate duplicate smoke removed (2026-07-06)**:
  `governance_tools/promotion_gate_receipt_smoke.py` was deleted after focused
  digest regression tests confirmed replacement coverage (`af51e631`).
  Promotion-gate behavior, contract version, gates, hooks, and CI were not
  changed.
- **R49.x-4 freeze and producer removal completed (2026-07-06)**: the
  generated artifact was recorded as frozen historical evidence at `371d1378`
  (`docs/status/ab-causal-r49x4-metric-ranking-freeze-2026-07-06.md`) and
  `governance_tools/r49x4_metric_ranking.py` was deleted at `b596198f` per the
  deprecate-first disposition. Lineage references to the frozen artifact are
  preserved; R49.x conclusions were not re-validated.
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

1. Remaining retire-candidate work is decision-blocked: obtain the human
   clean-pilot policy decision for `clean_pilot_admissibility.py` (retire tool
   plus `governance/fleet/cleaning_admissibility_policy.yaml` together, or add
   wiring/tests) and the host-memory sync disposition for
   `host_agent_memory_sync_signal.py` (deprecate-first, or wire/document its
   operator entrypoint). Do not delete either without those decisions.
2. Optional read-only follow-ups from the inventory artifact: cluster reviews
   for `ab_cost_evidence` (5 modules) and `external_integrations`
   (`linear_integrator`, `notion_integrator`), and identifying the consumer of
   the tracked `.latest-main/` snapshot.

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
- Cannot claim any governance defense beyond the two completed removals
  (`promotion_gate_receipt_smoke.py`, `r49x4_metric_ranking.py`) has been
  retired, downgraded, or proven useless.
- Cannot claim context savings were measured.
