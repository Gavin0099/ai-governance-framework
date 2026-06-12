# PLAN.md - AI Governance Framework

## Canonical Planning Surface

> **最後更新**: 2026-06-12
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
> **Created**: 2026-04-10
> **Risk tier**: L2
> **Planning window**: 2026-03 through 2026-06
> **Encoding status**: UTF-8 reviewer-readable canonical replacement

Purpose:

- Maintain portable AI governance contracts and reviewer-facing evidence.
- Define runtime observation, closeout, claim ceiling, and evidence surfaces.
- Preserve repo-local memory / state authority and traceability.
- Support external repo adoption, readiness, framework version, and source audit.
- Keep governance docs and static validators aligned with observed failures.

Non-goals:

- Not a full execution harness.
- Not a machine-authoritative semantic advisory system.
- Not a generic multi-agent orchestration platform.
- Not an OS sandbox, RBAC system, or enterprise AIMS replacement.

## Encoding Repair Notice - 2026-06-10

This file previously contained a large historical body with mojibake / corrupted
text. That made `PLAN.md` a reviewer-surface defect even though a readable
snapshot existed at the top.

Repair decision:

- Replace the corrupted historical body with this UTF-8 canonical planning
  surface.
- Preserve current phase status, claim boundaries, active work, completed
  milestones, and pending work in readable form.
- Treat detailed historical line-by-line content as recoverable from git history,
  committed artifacts, and canonical memory records rather than from corrupted
  inline text.

Claim ceiling for this repair:

- CLAIMED: reviewer readability of the active `PLAN.md` planning surface.
- NOT CLAIMED: roadmap semantic change, historical evidence migration, artifact
  cleanup, validator behavior change, hook behavior change, or enforcement
  change.

## Phase Overview

- [x] Phase A: Core governance tooling and baseline.
- [x] Phase B: Adoption, validators, freshness, and memory foundations.
- [x] Phase C: Runtime governance, DBL, and observation surfaces.
- [x] Phase D: Session workflow, external adoption, and reviewer entrypoints.
- [>] Phase E: Failure decision boundary, exclusion governance, and usage enforcement.

Phase D completion note:

- Reviewer closeout artifact was signed by Gavin0099 on 2026-04-28.
- Later Phase C / runtime reconciliation gaps were tracked as follow-up work,
  not as a reason to inflate current Phase D claims.

Phase E posture:

- Validity before expansion.
- Failure-driven governance only.
- No broad enforcement upgrade without observed failure and scoped evidence.

## Current Sprint - 2026-06-10

Theme:

- Convert repeated instruction-level failures into deterministic dispatch,
  evidence, and reviewer-readable state without overclaiming enforcement.

Completed in latest committed scope:

- [x] MEM-DISPATCH framework-side implementation completed.
- [x] `governance_tools.memory_workflow` added as deterministic dispatcher for
  memory tasks.
- [x] `memory/**` diffs classify as `governed_memory_task`.
- [x] `--run-guard` integrates memory authority guard summary into dispatcher
  output.
- [x] `--fail-on-blocker` provides opt-in selective blocking for current
  completion blockers.
- [x] `session_end_hook` exposes advisory `memory_workflow` surface.
- [x] `session_closeout_entry` persists `memory_workflow` fields in closeout
  receipt schema `1.2`.
- [x] Managed `pre-commit` hook surfaces memory workflow as advisory only.
- [x] `MEMORY_PROTOCOL.md` documents dispatcher, guard, selective blocking,
  hook advisory, and receipt evidence semantics.
- [x] F-7 framework-side role-aware orchestrator skeleton added.
- [x] F-7 submodule pointer update is demoted to a backend stage, not
  full-update completion.
- [x] External contract repo apply path scaffolded for framework lock, hooks,
  Copilot instructions, and AGENTS keyed-section calibration.
- [x] Windows-safe governance hook installer added with no-BOM framework-root
  config handling.
- [x] Self-hosted canonical memory evidence recorded for MEM-DISPATCH milestone.

Latest milestone commits:

- `0a28633 feat(governance): add memory workflow dispatch`
- `20a2353 docs(memory): record memory workflow milestone`

Latest scoped evidence:

- `python -X utf8 -m pytest tests/test_memory_workflow.py tests/test_session_end_hook_memory_workflow_surface.py tests/test_closeout_receipt_memory_surface.py tests/test_agent_closeout_receipt.py tests/test_pre_commit_memory_workflow_advisory.py tests/test_f7_full_update.py tests/test_hook_installer.py tests/test_hook_install_validator.py tests/test_external_governance_submodule_updater.py --basetemp .tmp-pytest/memory-workflow-commit -o cache_dir=.tmp-pytest/cache` -> 68 passed.
- `python -X utf8 -m governance_tools.memory_workflow --check --repo . --run-guard --fail-on-blocker --format json` -> `active_non_canonical_writer=0`, `blockers=[]`, `completion_claim_allowed=true`.

Completed 2026-06-12 (reviewed per-slice, pushed to gitlab/main and
origin/main, all heads = `9f7fa1e`):

- [x] P1-A selective CI blocker: CI-only current-diff
  `active_non_canonical_writer` blocker with `memory/**` workflow triggers
  and anti-bypass tests (`5deb8bb`).
- [x] Pre-commit memory advisory reporting clarity: guard-not-run vs
  completion-denied disambiguation (`5642134`).
- [x] Runtime ledger no-write mode: `AI_GOVERNANCE_NO_LEDGER_WRITE` /
  `--no-ledger-write`; smoke path no longer writes tracked ledgers; skipped
  writes observable as `skipped_no_write_mode` (`9f7fa1e`).
- [x] Cross-remote sync: local HEAD = gitlab/main = origin/main verified.

## Active Claim Boundaries

Mutation enforcement:

- CLAIMED: canonical mandate that mutation enforcement claims require an
  explicit mutation contract.
- Rule: No mutation contract = No enforcement claim.
- A tool, workflow, hook, or validator may not claim mutation enforcement
  unless its mutation contract is explicitly documented, scoped, and testable.
- NOT CLAIMED: mutation enforcement is implemented for every mutation surface,
  mutation contracts are complete, or mutation catalog presence is enforcement
  by itself.
MEM-DISPATCH:

- CLAIMED: framework-side implementation, tests, docs, hook advisory, session-end
  surface, and closeout receipt persistence.
- NOT CLAIMED: fleet-wide enforcement, all external repos governed, historical
  memory debt resolved, or CI / hook blocking rollout.

F-7:

- CLAIMED: framework-side role-aware orchestrator skeleton and external contract
  apply-path scaffold; submodule consumer apply path refreshes repo-local
  instructions, memory workflow router coverage, and managed hook advisory
  coverage.
- NOT CLAIMED: fleet rollout, all repo roles verified, all external repos
  upgraded, external readiness completion, validators changed, artifact schema
  changed, or existing memory normalized.

Memory authority:

- CLAIMED: canonical writer, active-window guard summary, dispatcher routing,
  and opt-in blocker path.
- NOT CLAIMED: historical debt cleanup, blocking threshold readiness, semantic
  correctness of memory content, or global enforcement closure.

Selective CI enforcement (P1-A, 2026-06-12):

- CLAIMED: CI-only current-diff `active_non_canonical_writer` blocker
  implemented (`5deb8bb`); hooks remain advisory; historical memory debt
  remains warning-only; reviewed and pushed to both remotes.
- NOT CLAIMED: full memory workflow enforcement, full mutation protection,
  blocker class expansion, or fleet CI rollout.

Runtime ledger no-write mode (2026-06-12):

- CLAIMED: runtime smoke path supports no-write mode for tracked ledgers;
  skipped writes are observable as `skipped_no_write_mode`; explicit
  `session_end` default ledger writes preserved.
- NOT CLAIMED: runtime ledger side-effect root redesign, workspace clean
  guarantee, tracked ledgers untracked/ignored/deleted, or elimination of
  all hook / pre-push side effects.

Reviewer polling:

- CLAIMED: reviewer polling is manual / resume-triggered only; bounded
  polling exists only as a behavior constraint in `.agent` role templates.
- NOT CLAIMED: automatic reviewer polling, daemon behavior, or automated
  reviewer handoff.
- Observed confusion (2026-06-12): thread append can create contradictory
  pending/final review states; reviewer protocols must use explicit FINAL
  verdict blocks or read-only extraction.

CodeBurn / token observation:

- CLAIMED: Class C observation-only surfaces and same-provider visible I/O token
  summaries where explicitly enabled.
- NOT CLAIMED: billing truth, efficiency inference, cross-provider comparability,
  or decision-safe cost analysis.

## Pending Work - Ordered

P0 - reviewer surface / trust repair:

- [x] Repair `PLAN.md` encoding / mojibake reviewer-surface defect.
- [x] Run scoped diff check for `PLAN.md` repair.
- [x] Commit `PLAN.md` repair separately from runtime ledgers.
- [x] Record canonical memory evidence for the `PLAN.md` repair commit.

P1-B - canonical status reconciliation after 2026-06-12 push:

- [x] `PLAN.md` reflects pushed reality (P1-A, advisory clarity, no-write
  mode, cross-remote sync recorded with claim boundaries).
- [x] P1-A selective enforcement status no longer stale in pending work.
- [x] Runtime ledger no-write mode claim boundary recorded.
- [x] Reviewer polling recorded as explicitly manual / resume-triggered.
- [x] Inventory refresh passes or reports exact drift: refresh trued-up
  stale overridable hashes (`PLAN.md`, `contract.yaml`, `AGENTS.md`);
  drift checker `severity=ok`, no warnings, no errors.
- [x] No F-7 rollout performed in this slice.

P1-C - F-7 external rollout (next slice: scoped verification for
`meiandraybook` only; one slice one evidence; do not claim rollout complete):

- [ ] Use F-7 external apply path to distribute `memory_workflow` to a consuming
  repo.
- [ ] Verify hook installer carries managed pre-commit memory workflow advisory.
- [ ] Verify consuming repo `AGENTS.md` routes memory tasks to dispatcher before
  memory completion claims.
- [ ] Verify external repo closeout receipts persist schema `1.2` memory workflow
  fields.
- [ ] Keep submodule pointer update reported as stage success only, not F-7
  completion.

P1 - selective enforcement decision (closed 2026-06-12 by P1-A, `5deb8bb`):

- [x] Decide whether any CI or hook path should opt into `--fail-on-blocker`:
  CI workflow path only, current-diff scope.
- [x] Preserve default advisory mode unless current-diff blocker false-positive
  rate is acceptable: hooks remain advisory.
- [x] Do not upgrade historical `missing_canonical_memory` or `unbound_memory`
  warnings into blockers without separate approval: preserved, warning-only.
P1 - structured memory freshness:

- [ ] Define freshness / rollover policy for structured canonical memory files
  such as `memory/01_active_task.md`.
- [ ] Define whether `PLAN.md` to structured-memory consistency should become
  a validator-backed self-check.
- [ ] Do not claim structured memory sync is solved by daily memory writer
  completion alone.

P2 - external presentation:

- [ ] Refresh GitHub repository description.
- [ ] Add relevant topics.
- [ ] Align README badge with current release state.
- [ ] Publish a release only after release notes and claim ceiling are accurate.

P2 - historical debt / evidence disposition:

- [ ] Maintain historical `missing_canonical_memory` / `unbound_memory` debt as
  warning evidence unless a scoped cleanup is approved.
- [ ] Keep CE-1D historical raw packet disposition separate from current runtime
  dirty ledgers.
- [ ] Do not backfill receipts or rewrite memory history without reviewer-approved
  scope.

## Dirty Workspace Policy

Known unrelated dirty runtime ledgers at the time of this PLAN repair:

- `artifacts/claim-enforcement/claim-enforcement-receipts.ndjson`
- `artifacts/session-index.ndjson`

Policy:

- Do not stage these files with documentation, memory workflow, or F-7 commits.
- Treat them as runtime side effects unless explicitly audited for promotion.
- Overall workspace remains NOT CLEAN while these files are dirty.

## Historical Milestone Index

This index preserves reviewer orientation without reintroducing corrupted inline
history.

- Core closeout receipt and evidence chain: operational.
- Claim-enforcement compact receipt boundary CE-1C / CE-1D: implemented with
  historical raw packet disposition still separated from current runtime ledgers.
- Response Envelope Contract and validator: implemented as structural reporting
  convention, not semantic enforcement.
- Fleet governance scope and required-tier verification: implemented with
  prior 10/10 required verified evidence, not a permanent future guarantee.
- F-7 submodule deterministic updater: implemented as a backend stage; full
  update semantics require role-aware orchestration.
- Memory canonical writer and memory authority guard: implemented with active
  sentinel and warning-mode historical debt.
- CodeBurn observation surfaces: implemented as Class C observation-only, not
  billing truth.
- External onboarding SOP: proven in prior repos, but current F-7 external
  rollout remains pending for memory workflow distribution.

## Definition Of Done For Current Planning Slice

This `PLAN.md` repair is done when:

- `PLAN.md` is readable UTF-8 text.
- Current completed scope and pending work are preserved.
- Claim ceilings and non-claims are explicit.
- Scoped diff check passes for `PLAN.md`.
- The repair is committed separately from unrelated runtime ledgers.
- A canonical memory record is written after the commit.

## Cannot Claim From This PLAN Alone

- Cannot claim that all historical evidence was migrated into this file.
- Cannot claim that external repos are updated.
- Cannot claim fleet enforcement completion.
- Cannot claim memory historical debt cleanup.
- Cannot claim semantic verification of every historical milestone.
- Cannot claim GitHub release / README / topics are current.
- Cannot claim workspace clean while runtime ledgers remain dirty.
