# Active Task

## Current Focus

- **Current focus: Canonical governance consistency after self-check repair**
- Goal: keep `PLAN.md`, structured memory, and authority surfaces aligned after
  MEM-DISPATCH, F-7, encoding repair, and reviewer-blocker fixes.
- Principle: **Validity before Expansion** - do not claim enforcement or memory
  freshness beyond the documented, validated surface.

## Current Status

- **P1-A selective CI blocker shipped (2026-06-12, `5deb8bb`)**: CI-only
  current-diff `active_non_canonical_writer` blocker with `memory/**` workflow
  triggers; hooks remain advisory; historical debt remains warning-only.
  Closes PLAN "P1 - selective enforcement decision".
- **Runtime ledger no-write mode shipped (2026-06-12, `9f7fa1e`)**: smoke path
  sets `AI_GOVERNANCE_NO_LEDGER_WRITE=1`; tracked ledger writes skipped and
  observable; explicit `session_end` default writes preserved. Root
  side-effect redesign NOT claimed.
- **Cross-remote sync verified (2026-06-12)**: local HEAD = gitlab/main =
  origin/main = `9f7fa1e`.
- **Reviewer polling boundary recorded (2026-06-12)**: polling is manual /
  resume-triggered only; no automatic polling or reviewer handoff automation
  is claimed. Observed thread-append pending/final confusion documented in
  PLAN claim boundaries.
- **P1-B canonical status reconciliation (2026-06-12)**: PLAN pending work,
  claim boundaries, and this file synced to pushed reality; next slice is
  P1-C scoped F-7 verification for `meiandraybook` only.
- **Self-check visible blockers repaired (2026-06-11)**: framework drift
  checker reports `severity=ok`, `warnings=[]`, and `errors=[]` after baseline,
  PLAN inventory, memory schema, AUTHORITY ghost-ref, cp950 output, pytest temp
  ignore, and global Git ignore warning repairs.
- **MEM-DISPATCH framework-side path complete**: `governance_tools.memory_workflow`
  covers daily session-derived memory dispatch, canonical writer guidance,
  authority guard summary, optional blocker mode, hook advisory, and closeout
  receipt schema `1.2` persistence.
- **F-7 framework-side implementation closed**: role-aware F-7 orchestration
  prevents submodule pointer-only updates from claiming full update completion.
  Fleet rollout remains separate adoption work.
- **Mutation mandate repaired**: `PLAN.md` now contains the canonical mandate
  "No mutation contract = No enforcement claim." This restores the previously
  false active-task claim that PLAN held the mandate.
- **Current active gap**: structured canonical memory files such as
  `memory/01_active_task.md` are authority surfaces, but their freshness,
  rollover, and PLAN consistency are not yet automatically validated.

## Pause Condition (Active)

Phase E expansion remains paused. Do NOT proceed to E2 or add new governance
surfaces until at least one of the following is observable:

1. A specific ambiguous term in PLAN.md/requirements causing reviewer confusion
   (triggers E2)
2. A production incident that would have been prevented by a spec (triggers E3)
3. A replay drift event showing inconsistency that current mutation tests cannot
   explain

**Rationale**: topology discovery must not automatically become governance
inflation. Engineering cost of premature validator > benefit of theoretical
coverage.

## Next Steps

- **P1: Structured memory freshness policy** - define how
  `memory/01_active_task.md` rolls over and how PLAN consistency should be
  checked before claiming structured memory is current.
- **E2: Spec Ambiguity Validator** - blocked; no observable ambiguity trigger yet.
- **E3: Production Spec Loop** - blocked; no production incident evidence yet.
- **AB Cost Backfill** - frozen as `tooling_ready / evidence_pending`; unblock
  only with real scalar telemetry for 4 runs (vsc-A/B, vtb-A/B).
- **Maintenance**: Keep `governance-proof-report.json` updated after any
  governance tool change.

## Historical Context Retained

- Phase D was marked `passed` in PLAN.md with reviewer closeout artifact
  `artifacts/governance/phase-d-reviewer-closeout.json` signed by `Gavin0099`.
- E1-A mutation catalog established `docs/e1-mutation-catalog.md`.
- E1-B Phase 1 initial negative fixtures were verified as protected.
- E1-B Phase 2 topology discovery found 4/4 catalog mutation scenarios
  vulnerable; topology discovery is not protection proof.
- CodeBurn v1.1 baseline and Runtime Enforcement Attachment v0.1 remain
  historical milestones, not current active work.