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
- **CodeBurn v1.1 Baseline COMPLETE (2026-05-22)**: P0-P7 + STATUS_SNAPSHOT all committed. Architecture freeze stable. No P8 in scope.
  - See: `CODEBURN_V1_1_ARCHITECTURE_FREEZE.md`, `CODEBURN_V1_1_STATUS_SNAPSHOT.md`, `CODEBURN_P7_ADVISORY_THRESHOLD_GOVERNANCE.md`
- **Runtime Enforcement Attachment v0.1 COMPLETE (2026-05-23)**: `test_enforcement_promotion_gate.py` is the sole risk-sensitive-friction foothold — blocks `--warn-only` removal without observed interception. Does not govern external execution. All other session commits classified observation-only or housekeeping.

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

## R35 Boundary (2026-05-15)

- Classification fixed as `threshold_dependent_confirmed`.
- Fixed-condition 3-seed evidence: `pass=0`, `fail=3` under `direction_tolerance=-1.5`, `exploration_floor=0`, `max_latency_delta=10`.
- Active objective: recover strict-regime stability instead of policy/threshold-dependent pass narratives.

## Active Observation Targets (2026-05-22, no infrastructure required)

- Citation pattern drift: boundary omission, shorthand expansion, qualifier drop
- Leading signals: "按 v1.1" without §reference; AT threshold cited without AT-2 qualifier; "per freeze" without specific FCP/§
- Propagation telemetry starts with citation observation, not instrumentation.
- [x] Promoted memory: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- [x] Promoted memory: CodeBurn v1.1 baseline complete + Daily Memory Gate v0.1 stabilization (2026-05-22)
