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

Structured PLAN Reconciliation Declaration (design only, 2026-06-12):

- CLAIMED: design agreed and recorded as P1-C fixture + P1-D items; the gate
  target is silent drift, not deferred drift; the atomic completion condition
  is declaring ledger state, not auto-syncing PLAN.
- NOT CLAIMED: implemented, enforced, blocking, or that a deferred
  declaration equals reconciliation.

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

P1-C0 - canonicalize silent-drift findings before F-7 verification
(completed 2026-06-12; no implementation, no F-7 run, no debt claimed
resolved):

- [x] P1-C gains fleet snapshot refresh as verification evidence.
- [x] P1-C gains memory_layout alias verification note.
- [x] E2 retrospective adoption evidence collection entered canonical
  tracker as P1 evidence-class item.
- [x] README capability table caveats entered canonical tracker (P2).
- [x] English reviewer-facing docs entered canonical tracker (P2).

P1-C - F-7 external rollout verification with manual PLAN reconciliation
fixture (scoped to `meiandraybook` only; one slice one evidence; do not
claim rollout complete):

Re-scope note (2026-06-12, ratified): P1-C may accept prior
clean-remediation-worktree F-7 apply evidence when the primary consumer
worktree is stale/dirty and re-running apply would create duplicate or
misleading verification evidence. In that case, P1-C scope becomes
post-apply evidence verification, not re-application. Acceptable evidence
sources: meiandraybook origin/main, the 2026-06-11 memory records
(`678c4c9` / `3ddff9d`), framework-side fleet snapshot, and read-only
checks against current remote state. Not acceptable: pull/merge/apply on
the stale primary dirty worktree, bundling stale-worktree cleanup into
P1-C, or re-running the completed apply to manufacture new evidence.

- [x] Use F-7 external apply path to distribute `memory_workflow` to a
  consuming repo: satisfied by the prior clean-remediation-worktree apply
  (2026-06-11, recorded at meiandraybook origin/main `678c4c9`/`3ddff9d`,
  `f7_final_status=full_update_completed`). Accepted per the re-scope
  note; NOT executed in this slice.
- [ ] Verify hook installer carries managed pre-commit memory workflow advisory.
- [ ] Verify consuming repo `AGENTS.md` routes memory tasks to dispatcher before
  memory completion claims.
- [ ] Verify external repo closeout receipts persist schema `1.2` memory workflow
  fields.
- [ ] Keep submodule pointer update reported as stage success only, not F-7
  completion.
- [ ] Closeout: manually fill the seven-field reconciliation checklist
  (PLAN item touched / PLAN status updated / claim boundary updated /
  memory derived from PLAN not ahead of it / reviewer verdict / push
  status / remaining non-claims).
- [ ] Memory record explicitly declares `plan_reconciliation` status
  (`updated` | `not_applicable` | `deferred:<reason>`); if PLAN is not
  updated, a specific deferred reason is mandatory.
- [ ] Record reviewer verdict, push status, and not-claimed boundary as
  separate fields, not merged into one completion claim.
- [ ] Do not add any blocking validator in this slice; this closeout is the
  design fixture for P1-D.

P1-C claim ceiling (locked 2026-06-12 before execution):

- CAN CLAIM: meiandraybook used as first external F-7 verification target;
  selected F-7 update surfaces verified or explicitly failed; fleet snapshot
  refreshed as evidence; memory_layout alias behavior observed; rollback
  expectation observed; manual reconciliation fixture produced.
- CANNOT CLAIM: F-7 works for all consumers; fleet rollout complete;
  copy-based consumers solved; rollback procedure implemented; blocking
  validator added; automatic PLAN reconciliation solved; primary
  meiandraybook worktree updated; stale dirty worktree resolved; the F-7
  apply was originally executed in this slice.
- Hard limit: on unexpected dirty state, destructive update behavior, or
  ambiguous repo role, stop at diagnosis and report; do not push through
  remaining checklist items. A verification slice must not silently become
  a remediation slice.
- [ ] Refresh fleet matrix snapshot as part of F-7 verification evidence
  (current snapshot 2026-05-29 exceeds its own 7d evidence window).
- [ ] Verify memory file naming against `memory_layout` aliases during F-7
  application (known divergence seed: `F7_GOVERNANCE_ALLOWLIST` hardcodes
  `02_tech_stack.md` while `memory_layout.py` accepts three aliases).
  Verify and record only; do not claim alias divergence resolved.
- [ ] Observe and record rollback path expectation during the F-7 update
  (what reverting to the previous framework commit would require if smoke
  fails after update). Observation only; no rollback implementation
  claimed in this slice.

P1 - update rollback documentation (P1-C follow-up; do not start before
the P1-C rollback observation exists):

- [ ] Document rollback procedure for a failed F-7 update / failed smoke
  after governance update. Updating governance is itself a trust-surface
  change and must be reversible per the core principle (expensive,
  explicit, reversible).

P1-D - Structured PLAN Reconciliation Declaration (design agreed 2026-06-12;
do not start before the P1-C fixture exists):

- Goal: every completion-oriented memory record must declare whether it has
  been reconciled with PLAN, and if not, why not. The gate target is silent
  drift, not deferred drift. This is NOT PLAN auto-sync and must not induce
  agents to edit canonical PLAN to legalize their own completion claims.
- [ ] Add required `--plan-reconciliation` field to
  `governance_tools.memory_record`:
  `updated` | `not_applicable` | `deferred:<reason>`.
- [ ] Deferred reasons must come from a reason taxonomy (e.g.
  `requires-human-plan-review`, `awaiting-reviewer-verdict`,
  `scope-split-next-slice`, `canonical-update-not-authorized`,
  `dirty-workspace-prevents-safe-edit`); reject empty or vacuous reasons
  (`later` / `todo` / `pending` / `soon` / `TBD`).
- [ ] Pre-push advisory only (reuse the current-date memory gate seam):
  report completion-class records missing a reconciliation declaration;
  do not block.
- [ ] P1-E: collect 2-4 weeks of false-positive / false-negative samples
  before any blocking decision.
- [ ] P1-F: upgrading to a current-diff blocker changes what counts as a
  legal completion claim and is therefore an [OP-HC] decision requiring
  FP data, a rollback path, and its own mutation contract. Not authorized
  by this item.
- [ ] Add a non-blocking deferred-debt report (deferred count by reason,
  oldest deferred age, PLAN-touched records without `updated` status) to
  prevent acknowledged-drift from becoming a landfill.

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

P1 - adoption evidence collection (E2-relevant; evidence class, not
presentation class):

- [ ] Collect retrospective E2 adoption evidence from the two engineer
  onboardings: onboarding artifacts from their environments, friction log
  (time to green smoke, walls hit, remediation source), and author
  intervention count declaration.
- [ ] Record evidence grade explicitly as retrospective / self-reported.
- [ ] Do not claim sustained lifecycle, E2 closure, or low framework
  friction from this evidence alone.

P2 - adoption model:

- [ ] Classify whether copy-based consumers are supported, audit-only, or
  unsupported for automated update. Current claim ceiling: not solved.
  Classification first; do not design support tooling before P1-C
  consumer evidence exists.

P2 - external presentation:

- [ ] Refresh GitHub repository description.
- [ ] Add relevant topics.
- [ ] Align README badge with current release state.
- [ ] Align README capability table with current reality: mutation topology
  caveat on the fail-closed gate row, audit-framework-not-security-boundary
  positioning sentence, and MEM-DISPATCH capability row.
- [ ] Prepare English reviewer-facing docs (README, starter-pack,
  onboarding SOP).
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
