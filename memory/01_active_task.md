# Active Task

## Current Focus

- **Phase E: Software Fundamentals as AI Governance**
- Goal: Use software engineering fundamentals (Mutation Proof, Spec Ambiguity Detection) to constrain AI Coding risks.
- Principle: **Validity before Expansion** — prove existing governance is real before adding more.

## Current Status

- **Phase D Closed**: Officially marked `passed` in PLAN.md; reviewer closeout artifact `artifacts/governance/phase-d-reviewer-closeout.json` signed by `Gavin0099`.
- **E1-A Mutation Catalog Established**: `docs/e1-mutation-catalog.md` defines critical failure modes (Mutation vs Fixture) and exact violation codes.
- **E1-B Phase 1 Protected**: `governance_tools/mutation_proof_runner.py` established; initial 3/3 negative fixtures (forged artifact, missing root, state mismatch) verified as PROTECTED.
- **E1-B Phase 2 CLOSED (topology discovery)**: `governance_tools/mutation_proof_runner_phase2.py` implemented using `git worktree` isolation. All 4 catalog mutation scenarios executed (2026-05-12). Result: 4/4 VULNERABLE — enforcement topology mapped, gaps documented.
  - Key finding: most enforcement surfaces are single-point. Precedence Bypass has incidental partial redundancy (`authority_state_active` survives mutation), but **partial redundancy ≠ protected**.
  - Claim boundary: Phase 2 = topology discovery, NOT protection proof.
- **Enforcement Policy**: PLAN.md now mandates: "No mutation contract = No enforcement claim".

## Pause Condition (Active)

Phase E is in **pause** — do NOT proceed to E2 or add new governance surfaces until at least one of the following is observable:

1. A specific ambiguous term in PLAN.md/requirements causing reviewer confusion (triggers E2)
2. A production incident that would have been prevented by a spec (triggers E3)
3. A replay drift event showing inconsistency that current mutation tests cannot explain

**Rationale**: topology discovery must not automatically become governance inflation. Engineering cost of premature validator > benefit of theoretical coverage.

## Next Steps (blocked until pause condition met)

- **E2: Spec Ambiguity Validator** — blocked; no observable ambiguity trigger yet
- **E3: Production → Spec Loop** — blocked; no production incident evidence yet
- **AB Cost Backfill** — frozen as `tooling_ready / evidence_pending`; unblock only with real scalar telemetry for 4 runs (vsc-A/B, vtb-A/B)
- **Maintenance**: Keep `governance-proof-report.json` updated after any governance tool change.
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)

- **R35 boundary conclusion synced (2026-05-15)**:
  - Classification is now fixed as `threshold_dependent_confirmed`.
  - Fixed-condition 3-seed evidence: `pass=0`, `fail=3` under `direction_tolerance=-1.5`, `exploration_floor=0`, `max_latency_delta=10`.
  - Active objective remains: recover strict-regime stability instead of policy/threshold-dependent pass narratives.
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
