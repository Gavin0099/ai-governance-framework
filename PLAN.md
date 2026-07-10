# PLAN.md - AI Governance Framework

## Canonical Planning Surface

> **最後更新**: 2026-07-06
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
> **Created**: 2026-04-10
> **Risk tier**: L2
> **Planning window**: 2026-03 through 2026-07
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

Current refresh - 2026-07-10:

Theme:

- Keep Phase E in validity-before-expansion posture while reducing governance
  noise and surfacing which defenses actually change decisions.
- Treat the 2026-07-06 test-signal quality line as report-only visibility for
  consumer/domain-contract test evidence, not as a readiness gate.
- Use decision-change and context-cost artifacts to decide what to keep,
  merge, downgrade, or investigate before adding more governance surface.
- Preserve the 2026-06 cache-aware / AUTHORITY_MANIFEST line as candidate-only
  unless a named harness consumer and evidence contract are separately scoped.

Completed in latest committed scope:

- [x] No-governance baseline experiment Slice A pre-registered one fixed task,
  two matched arms, four mechanical metrics, and pre-committed dispositions;
  correction `7a3f906d` accurately distinguishes older round2b evidence from
  the current protocol.
- [x] Stale self-audit carriers were dispositioned and current task authority
  was synchronized through `ecc17c58` / `8dac8c82`.

- [x] Cache-aware docs phase collected the harness/repo/enforcement boundary:
  prompt cache, compaction control, deferred tool loading, and mode-as-tool-call
  remain HARNESS-only; repo-feasible work is limited to reviewer-facing
  detection/accountability artifacts.
- [x] Cache-aware receipt alignment clarified that `REVIEW_RECEIPT`,
  mode/auth, tool-denial, and compaction receipts remain candidate/PENDING
  evidence unless a later adopted contract changes their authority.
- [x] Operator prompt playbook now records daily rules that keep sub-agent
  receipts evidence-only and keep push, memory write, and cross-repo write under
  main-thread gates plus explicit authorization.
- [x] Runtime adoption review packet closed the cache-aware docs phase and
  identified the first feasible implementation tranche:
  `AUTHORITY_MANIFEST` generator plus authority-change invalidation signal.
- [x] AUTHORITY_MANIFEST implementation tech spec narrowed the tranche:
  derive from or extend `.governance/baseline.yaml`, summarize
  `governance_drift_checker.py` semantics, and do not create a parallel
  authority map.
- [x] Read-only `AUTHORITY_MANIFEST v1` candidate generator implemented with
  focused tests. It derives authority file membership from `.governance`
  `baseline.yaml`, summarizes `governance_drift_checker.py`, and emits
  base/head authority-change invalidation signals.
- [x] Read-only AUTHORITY_MANIFEST preflight consumer simulation implemented
  with focused tests. It emits reviewer-facing `reuse_candidate`,
  `reload_required`, `cache_unsafe`, and `not_checked` decisions without
  provider cache integration or enforcement.
- [x] CHANGELOG Unreleased entries record both AUTHORITY_MANIFEST candidate
  generator and preflight consumer surfaces without version bump, release
  publish, prompt-cache behavior, runtime hooks, CI/pre-push/gates, or
  enforcement claims.
- [x] Hermes no_agent local observer claim ledger updated to
  `observed_six_scheduled_runs` for job `025890509ebf`, based on six
  scheduled artifacts from 2026-06-25 through 2026-06-30 while preserving
  non-claims for reliability, SLA, provider-free runtime, governance authority,
  enforcement, and future scheduled success.
- [x] Report-only `test_signal_quality_audit` tooling reached v0.2: domain
  contract repos can be scanned for validator fixture pairing, fixture-manifest
  expected-result mapping, placeholder validator labeling, fixture-runner
  presence, lexical weak-test signals, and explicit cannot-claim boundaries.
- [x] Consumer-facing update instructions now surface semantic test-quality
  expectations: no happy-path-only tests for non-trivial changes, independent
  expected values, regression tests for reproducible bugs when feasible,
  mock-only weakness, and validator pass/fail fixture expectations.
- [x] Retrieval Authority Round A and Cache-Aware Round B design clusters were
  consolidated into summary/index docs with source-note pointer banners and
  classification metadata. Source notes remain preserved; they were not
  archived, invalidated, or reclassified by the pointer update.
- [x] `docs/governance/decision-change-ledger.seed.json` was added as a seed
  artifact for classifying recent governance outputs by decision effect,
  including the distinction between output-line evidence and future
  inventory-line zombie-defense visibility.
- [x] `docs/governance/context-cost-budget-design-2026-07-06.md` separated
  per-slice context-read budgeting from the decision-change ledger so
  agent-read telemetry does not pollute defense-output classification.

Current next candidate:

- [x] Slice B voided under owner-approved Pre-Run Amendment 2 (FINAL).
  The first A1 attempt is excluded as a protocol-fidelity failure: its
  writes/validation were blocked by the effective Codex sandbox/policy
  despite the frozen `workspace-write` spec, and it produced no scoreable
  output (scratch repo unchanged at seed `dd34ac3`); receipts are retained.
  The observed voluntary `AGENTS.md` read is handled intent-to-treat: Arm A
  is defined as no harness-injected governance, and voluntary governance-doc
  reads are recorded per run as an observed variable. The Arm B entrypoint
  is now frozen (hook_installer --hooks-only + hook_install_validator
  valid=true). The required write-capability probe in a disposable non-task
  repo failed under the same Codex configuration: the model reported a
  read-only workspace, policy rejected the write, `write-probe.txt` was
  absent, and the repo remained clean at seed `a619e13`. This is the further
  protocol gap named by the hard lock, so Slice B is void. No valid baseline
  run or score exists; continuation requires a separate v2 pre-registration.

- [x] v2 Pre-0 execution-surface qualification passed on the final authorized
  attempt. The v2 experiment is void before Run 1; see
  `docs/status/no-governance-baseline-v2-void-2026-07-10.md`. Its first fresh
  Arm A scratch root was not eligible (no copied task file or seed commit), and
  the freeze did not bind seed construction/tree hash. Under v2's zero-amendment
  rule, no replacement scratch may be improvised. No Codex session, OpenAI API
  transmission, run, score, metric, or attribution conclusion occurred. The first attempt failed before
  helper launch because nested `.sandbox-bin` Codex lacked package identity.
  The second used the correct package-context launcher but reused a scratch
  root owned by `CodexSandboxOffline`, so write-ACE setup failed. The final,
  capped attempt used a fresh disposable repo whose root was created by
  launcher user `daish`, plus the identical `Invoke-CommandInDesktopPackage`
  launcher, PFN `OpenAI.Codex_2p2nqsd0c76g0`, AppId `App`,
  `-PreventBreakaway`, package `26.707.3748.0`, native `elevated`, and
  `workspace-write`. Helper setup completed with `errors=[]`; `apply_patch`
  created the sole changed file, whose exact bytes are
  `workspace-write-ok\n`, and readback/status succeeded. Future v2 scratch
  repos must be created by the launcher user outside sandbox context;
  qualification does not transfer across launcher or package version.
  v2 locks the successful ICIDP launcher/PFN/AppId/`-PreventBreakaway`, native
  `elevated`, `workspace-write`, and package `26.707.3748.0`; every run must
  retain a matching package check. Scratch roots must be created outside the
  sandbox by launcher user `daish`; no amendment is allowed after the v2 freeze.

- [x] v3 offline dress rehearsal completed without an API call. It demonstrated
  fresh scratch construction, literal JSON seed mutation, mutation-probe
  behavior (8 fixtures / 7 matched / 1 named mismatch), clean post-probe state,
  seed-tree hash `27b7d8f9e7c7b7bccce5d47ce991c92a6e3fea71`, and assembled
  package-context launcher arguments. v3 is not preregistered or authorized to
  run; see `docs/status/no-governance-baseline-v3-offline-dress-rehearsal-2026-07-10.md`.

- [x] v3 Arm B offline rehearsal completed without an API call. A fresh clone
  matched the Arm A seed tree hash; `hook_installer --hooks-only` reported
  `ok=true`, `hook_install_validator` reported `valid=true`, and a local commit
  trace showed `.git/hooks/pre-commit` invocation with a clean poststate. The
  package-context hook path remains untested. v3 is not preregistered or
  authorized to run; see
  `docs/status/no-governance-baseline-v3-arm-b-offline-dress-rehearsal-2026-07-10.md`.

- [x] Decision note keeps the AUTHORITY_MANIFEST preflight path in Unreleased
  candidate-only state until a named real harness consumer and evidence
  contract are separately scoped:
  `docs/governance/authority-manifest-preflight-evidence-decision-2026-07-02.md`.
- [x] Decision note defines the evidence boundary for v1.3.0 release-prep:
  release-surface consistency and consumer-side proof are required before any
  release-prep slice can start:
  `docs/governance/v1.3.0-release-prep-evidence-boundary-2026-07-02.md`.
- [ ] Do not start v1.3.0 release-prep until the scoped release-surface
  consistency packet and named consumer-side proof packet are collected and
  reviewed.
- [ ] Run a read-only decision-change ledger inventory-line pass to identify
  zombie, duplicate, noisy, rare-critical, and unknown governance defenses
  before merging, downgrading, or retiring any surface.
- [ ] Keep any context-cost companion record as a future candidate only until
  there is evidence that per-slice summaries change review, implementation, or
  consolidation decisions without becoming their own governance overhead.

Claim ceiling for this sprint:

- CLAIMED: cache-aware planning and the first repo-feasible implementation
  tranche are documented and implemented as read-only candidate tooling:
  AUTHORITY_MANIFEST generation, authority-change invalidation, and preflight
  consumer simulation.
- CLAIMED: report-only test-signal quality audit visibility exists for domain
  contract repos, with v0.2 fixture-manifest and fixture-runner reporting.
- CLAIMED: governance-overhead analysis has seed artifacts for decision-change
  classification and context-cost design.
- NOT CLAIMED: prompt cache implementation, cache hit/miss monitoring,
  compaction control, mode/auth/tool-denial receipt tooling, runtime hook/CI
  wiring, enforcement, canonical authority promotion, external harness
  adoption, v1.3.0 release readiness, cross-repo writes, automatic test-quality
  enforcement, industry-grade test proof, noisy-surface retirement, measured
  token savings, or context-cost compliance.

Latest milestone commits:

- `470b95a docs(governance): add cache-aware runtime adoption packet`
- `2974840 docs(governance): specify authority manifest implementation tranche`
- `36dc391 docs(memory): record authority manifest tech spec push`
- `454391c feat(governance): add authority manifest candidate generator`
- `88f1bdf feat(governance): add authority manifest preflight consumer`
- `0d5f1bd docs(changelog): record authority manifest generator`
- `8e9754b docs(changelog): record authority manifest preflight consumer`
- `58f8a30 docs(hermes): update no-agent recurrence ledger`
- `8090517 docs(hermes): record sixth no-agent observation`
- `6e6d059 docs(memory): record Hermes observed-six ledger update`
- `1c9abeff fix(governance): harden test signal manifest parsing and surface fixture runners`
- `a5ae276e feat(governance): surface semantic test quality guidance`
- `2ac950bc docs(governance): classify design note surfaces`
- `d4173978 docs(governance): consolidate retrieval authority round a summary`
- `f3b2b1ee docs(governance): add cache-aware round b summary`
- `7d952d35 docs(governance): sync cache-aware classification metadata`
- `5ce59b81 docs(governance): add consolidation pointers to source notes`
- `023c65c0 docs(governance): seed decision-change ledger`
- `5add91e5 docs(governance): design context cost budget`
- `86257f97 docs(memory): record context cost budget design`

Latest scoped evidence:

- `.venv\Scripts\python.exe -m governance_tools.governance_drift_checker
  --repo . --format json` reports `ok=true`, `severity=ok`,
  `plan_inventory_current=true`, and `plan_freshness=true` before this
  bookkeeping refresh.
- `python -B -m pytest tests/test_authority_manifest.py -p no:cacheprovider`
  passed focused generator coverage before commit.
- `python -B -m pytest tests/test_authority_manifest_preflight.py
  --basetemp .tmp_pytest_authority_manifest_preflight_review -p no:cacheprovider`
  passed 6/6 before commit.
- `python -m pytest tests/test_test_signal_quality_audit.py --basetemp
  .tmp_tsqa` passed 19 tests for the v0.2 test-signal audit surface before the
  2026-07-06 hardening memory record.
- `git diff --check` passed for the decision-change ledger seed and
  context-cost design notes before their source commits.
- Hermes read-only observation inspected `jobs.json`, six output artifacts,
  and `agent.log` under `C:\tmp\hermes-noagent-checklist-deploy-20260623`,
  supporting `observed_six_scheduled_runs` but not reliability.
- 2026-06-28 through 2026-07-06 canonical memory records bind the cache-aware
  receipt alignment, operator rules, runtime adoption packet, baseline
  analysis, authority manifest implementation, preflight consumer simulation,
  changelog dispositions, Hermes observed-six ledger update, test-signal audit
  v0.2, design-note consolidation, decision-change seed, and context-cost
  design.

Historical sprint context - 2026-06-10:

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
- [x] Response Envelope Contract v0.2: added Evidence Term Glossing
  (plain-language requirement) as an advisory reviewer-facing convention;
  registered the contract in `governance/AUTHORITY.md` and routed glossing in
  `AGENTS.md` router #2. Advisory only; `response_envelope_validator.py`
  unchanged; no gate, no enforcement claim. v0.3 adds the Next-Step Judgment
  required closing section (status / basis / recommended action / cannot-claim)
  for decision-readability; still advisory, validator still unchanged.
- [x] Consumer .gitignore hygiene: `adopt_governance.py` now ships a managed,
  idempotent, non-destructive artifact/pyc ignore block to consuming repos on
  adopt and `--refresh`, so a consumer no longer goes permanently dirty from
  regenerated runtime artifacts / tracked `.pyc` (root-caused from
  gl_electron_tool F-7 evidence). Memory is intentionally not ignored. Covers
  the adopt/refresh path only; already-adopted repos must re-run refresh + a
  one-time `git rm --cached`.
- [x] F-7 updater hygiene: `external_governance_submodule_updater.py` now also
  ensures the same managed `.gitignore` block on the managed-updater path
  (dry-run reports a `gitignore_hygiene` field; apply writes + stages
  `.gitignore`), reusing the canonical block from `adopt_governance` (single
  source, no drift). Reported as an advisory field, intentionally NOT folded
  into `final_status` (the 5-layer contract is unchanged). Both adopt/refresh
  and the F-7 updater now carry hygiene; already-dirty repos still need a
  one-time `git rm --cached`.

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

Completed 2026-06-17 -> 2026-06-18 (reviewed per-slice, pushed; latest
head = `7942572`):

- [x] OQ-2 resolved: learning-loop terminus is advisory-only (record ->
  taxonomy/memory/eval/claim-boundary linkage -> warning signal); no re-run
  gate / CI / completion blocker.
- [x] OQ-1 ratified: layered taxonomy framework -- `semantic_failure`
  (SF-code) is the primary reviewer-finding taxonomy; `scenario_type` is a
  separate replay-shape axis; `FAILURE_KINDS` is `result_disposition` only;
  cross-walks read-only, no flat merge, no fourth taxonomy.
- [x] Gate 3 opening criteria + schema-prep boundary defined in
  `docs/LEARNING_LOOP_CONSOLIDATION_SPEC_2026-06-16.md`. Gate 3 is NOT opened
  (5 conditions unmet; binding = repeated drift trigger + owner unpause).
- [x] Taxonomy-alignment prep advisory implemented (`483b920`) and hardened
  for missing/malformed/BOM input (`7472cb2`): advisory-only, exit 0 unless
  `--strict`.
- [x] Option B ledger untrack implemented (`ffd9609`): the two runtime ledgers
  are ignored + `git rm --cached`, local files kept; readers verified to
  tolerate absence.
- [x] Runtime ledger milestone export, manifest-only (`bf798d4`): BOM-safe,
  advisory by default, `--strict` / `--include-raw` opt-in; export bundles
  are committable.

Claim ceiling for the above: learning-loop implementation remains paused and
advisory-only; OQ-1/OQ-2 resolved does NOT open Gate 3; no banking, replay
runner, CI/completion gate, or enforcement exists.

Completed 2026-06-21 (reviewed per-slice, pushed to origin/main):

- [x] Hermes adapter line reached mock-backend smoke coverage:
  adapter scaffold, accepted-input interface doc, deterministic stub runner,
  standard smoke registration, input-driven mock backend fixture, fail-closed
  parse / allowlist behavior, and fixture disclaimer were committed with
  focused tests.
- [x] CI enforcement claim ceiling documented in
  `docs/governance/ci-enforcement-claim-ceiling.md`: push checks are
  post-facto detection/accountability; PR coverage is stronger; prevention
  claims require verified required checks / branch protection outside the
  workflow file.

Claim ceiling for 2026-06-21 updates: Hermes remains mock-backend /
accepted-input smoke only; no real Hermes model, hosted/local backend,
general code-writing runtime, model reliability, or non-bypassable governance
wrapping is claimed. CI claim-ceiling work is documentation-only; it does not
change workflow behavior, hooks, branch protection, or enforcement level.

## Active Claim Boundaries

Test-signal quality audit line (2026-07-06):

- CLAIMED: report-only domain-contract test-signal audit tooling exists in
  `governance_tools/test_signal_quality_audit.py` and can surface validator
  fixture pairing, fixture-manifest expected-result mapping, fixture-runner
  presence, placeholder labeling, and weak lexical test-signal candidates.
- CLAIMED: consumer-facing update instructions now state semantic test-quality
  expectations for non-trivial work and validator fixture pairs.
- NOT CLAIMED: the framework proves any consumer repo has industry-grade tests,
  validates fixture truth, enforces test quality, changes readiness gates,
  rewrites consumer tests, or semantically proves behavior protection.

Decision-change / context-cost line (2026-07-06):

- CLAIMED: `docs/governance/decision-change-ledger.seed.json` provides a seed
  classification model and recent evidence-backed examples for whether
  governance outputs changed later decisions.
- CLAIMED: `docs/governance/context-cost-budget-design-2026-07-06.md`
  separates per-slice context-read accounting from defense-output
  classification.
- NOT CLAIMED: a full inventory-line pass has been run, any defense has been
  retired or downgraded, context savings have been measured, context-cost
  companion records exist, or compliance with context-budget rules is enforced.

Cache-aware / AUTHORITY_MANIFEST line (2026-06-28 -> 2026-06-29):

- CLAIMED: cache-aware governance surfaces have been classified into
  HARNESS-only, REPO-feasible, and ENFORCEMENT-limited boundaries.
- CLAIMED: the first repo-feasible implementation tranche exists as read-only
  candidate tooling: `AUTHORITY_MANIFEST v1` generator, base/head
  authority-change invalidation signal, and AUTHORITY_MANIFEST preflight
  consumer simulation.
- CLAIMED: generator semantics derive from existing `.governance/baseline.yaml`
  and `governance_drift_checker.py` surfaces instead of creating a competing
  authority map.
- NOT CLAIMED: prompt cache is implemented, cache hit/miss is monitored,
  compaction is controlled by this repo, candidate receipts are authoritative,
  CI/runtime/pre-push/gate enforcement is wired, external harnesses have
  adopted the cache-aware specs, or v1.3.0 release-prep is justified.

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

Hermes executor-adapter line (2026-06-21):

- CLAIMED: Hermes accepted-input adapter surface, interface documentation,
  deterministic stub runner, standard smoke registration, and input-driven
  mock-backend fixture path with focused tests for fail-closed parse /
  allowlist behavior and response-file contract.
- CLAIMED: the separate Hermes no_agent local observer line has
  `observed_six_scheduled_runs` for job `025890509ebf`, with six scheduled
  output artifacts from 2026-06-25 through 2026-06-30 and observation-only
  claim ceiling.
- NOT CLAIMED: verified external Hermes governance compliance, true Hermes
  model integration, hosted/local backend reliability, model-generated
  tool-call reliability, general-purpose code-writing runtime completion,
  provider-free runtime, future scheduled success, or non-bypassable governance
  wrapping.

CI enforcement claim ceiling (2026-06-21):

- CLAIMED: documentation of the current in-repo GitHub Actions boundary:
  push-triggered checks are post-facto detection/accountability; four heavier
  jobs are PR-only; branch protection / required-check settings are outside
  the workflow file and were not verified here.
- NOT CLAIMED: prevention-grade enforcement, verified GitHub branch protection,
  required status checks enabled, local hooks installed everywhere, adapters as
  runtime sandboxes, or CI proof of framework correctness.

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

Structured PLAN Reconciliation Declaration (advisory implemented, 2026-06-12):

- CLAIMED: writer-level `--plan-reconciliation` field with taxonomy
  validation implemented in `governance_tools.memory_record`; missing
  declarations recorded as `not_declared` with advisory; malformed
  declarations rejected at write time; pre-push advisory reports
  undeclared records; the gate target is silent drift, not deferred
  drift.
- NOT CLAIMED: blocking enforcement (P1-F, separate OP-HC decision),
  deferred-debt report, P1-E FP/FN window completed, PLAN auto-sync,
  retroactive declaration coverage for historical records, or that a
  deferred declaration equals reconciliation.

Scope taxonomy (P1-I, 2026-06-12):

- CLAIMED: four scope sets defined by evidence duty with membership
  criteria; meiandraybook classified (f7_consumer + submodule_consumer,
  not fleet); hardcoded fleet enumeration explicitly accepted with a
  named re-evaluation trigger; manifest-driven generator deferred,
  failure-driven.
- NOT CLAIMED: fleet coverage complete, all consumers monitored,
  copy-based consumer update path solved, scope manifest implemented,
  or repo-class freshness SLA defined.

Fleet freshness (P1-H, 2026-06-12):

- CLAIMED: event-driven freshness policy adopted; refresh via the
  registered generator required before rollout / release / external
  claims citing fleet state; `required_verified` ratio defined as
  freshness-window evidence.
- NOT CLAIMED: fleet health restored, continuous monitoring, weekly
  cadence, repo-class SLA, or that idle-period decay is a defect.

Adoption model (P2-C, 2026-06-12):

- CLAIMED: consumer role taxonomy canonicalized in
  `docs/ADOPTION_MODEL.md` (submodule consumer, F-7 consumer, external
  contract repo, copy-based audit-only, unsupported/unknown), each with
  required evidence, allowed claims, prohibited claims, and upgrade
  path; copy-based consumers classified audit-only (classification and
  audit wording supported); classification-precedes-tooling rule.
- NOT CLAIMED: copy-based update automation (unsupported; ceiling: not
  solved), any new tooling, fleet rollout, F-7 generality, or that
  classification of a class equals evidence of a consumer in it.

Publish surfaces (P2-E, 2026-06-13):

- CLAIMED: per-surface publish decision checkpoint canonicalized —
  description and topics allowed only after exact-text ratification
  under a mechanism-only ceiling; badge deferred until the first gated
  release; release publish remains gated; prohibited wording classes
  recorded; publish text may never claim above the README capability
  table.
- NOT CLAIMED: any publish surface edited, any release published, any
  badge added, promotion readiness, or that P2 core documentation
  completion equals public-promotion ready.

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

P0 - cache-aware authority manifest implementation readiness:

- [x] Close cache-aware docs phase with implementation readiness packet and
  claim ceilings.
- [x] Record that `AUTHORITY_MANIFEST v1` must reuse or extend the existing
  `.governance/baseline.yaml` plus `governance_drift_checker.py` path.
- [x] Write the docs-only implementation tech spec for the first tranche.
- [x] Before implementation, confirm high-rigor review boundary for a read-only
  authority manifest generator plus focused tests.
- [x] Implement the generator as a separate read-only tooling slice.
- [x] Implement the AUTHORITY_MANIFEST preflight consumer simulation as a
  separate read-only tooling slice.
- [x] Record CHANGELOG Unreleased dispositions for the generator and preflight
  consumer simulation.
- [x] Document that the preflight path remains Unreleased candidate-only until
  a named real harness consumer and evidence contract are separately scoped.

Non-goals for this pending work:

- Do not implement prompt cache, runtime hooks, CI/pre-push/gate enforcement,
  baseline rewrites, memory behavior, release publishing, or cross-repo writes
  as part of the first tranche.

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
- [x] Verify hook installer carries managed pre-commit memory workflow advisory:
  satisfied by accepted apply evidence (`memory_workflow_hook_advisory=verified`,
  `hook_validator_enforcement=verified` in `3ddff9d` record).
- [x] Verify consuming repo `AGENTS.md` routes memory tasks to dispatcher before
  memory completion claims: verified read-only against origin/main
  (`governance:key=memory_workflow` keyed section, AGENTS.md:583).
- [ ] Verify external repo closeout receipts persist schema `1.2` memory workflow
  fields: PENDING PRODUCTION VALIDATION — code path verified 2026-06-13:
  `schema_1_2_code_ready=true` (submodule `0eafe10`,
  `CLOSEOUT_RECEIPT_SCHEMA_VERSION="1.2"`, all `memory_workflow_*` fields
  present); `stop_hook_path_verified=true` (`.claude/settings.json` Stop hook
  points to submodule `session_closeout_entry.py`);
  `latest_existing_receipt_schema=1.1` (receipt `20260531T160517Z`);
  `post_f7_natural_receipt_exists=false`; `production_schema_1_2_validation=pending`.
  Manual invocation (Option A) explicitly deferred: a hand-triggered receipt
  cannot prove Stop hook production path or natural session context, and would
  create evidence that looks like F-7 natural-session validation but cannot
  support that claim — do not create it unless labeled `manual_invocation_only /
  not_natural_session / not_production_closeout_evidence`.
  Close condition (all six must be observed in the same natural-session receipt):
  open a real meiandraybook session after F-7, allow the normal Stop hook to
  close it, then inspect the newest `artifacts/runtime/closeout-receipts/` entry
  and verify: (1) `schema_version == "1.2"`; (2) `memory_workflow_dispatch_ran`
  exists; (3) `memory_workflow_status` exists; (4) `memory_workflow_warning_codes`
  exists; (5) `memory_workflow_blocker_codes` exists; (6)
  `memory_workflow_guard_summary` exists. Check box only after all six confirmed.
- [x] Keep submodule pointer update reported as stage success only, not F-7
  completion: accepted evidence shows `full_update_completed` came from full
  surface verification, not pointer-only.
- [x] Closeout: seven-field reconciliation checklist filled manually in the
  2026-06-12 closeout memory record (the P1-D design fixture).
- [x] Memory record explicitly declares `plan_reconciliation: updated`
  (PLAN re-scoped and reconciled before the record was written).
- [x] Reviewer verdict, push status, and not-claimed boundary recorded as
  separate fields in the closeout record.
- [x] No blocking validator added in this slice.

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
- [x] Refresh fleet matrix snapshot as part of F-7 verification evidence:
  `governance_repo_matrix_snapshot_20260612_173313` generated. Findings:
  required_verified dropped 9/10 -> 1/10 (ratio 0.9 -> 0.1) from two weeks
  of evidence decay under the 7d window; freshness_blocked_count=6;
  meiandraybook is NOT in fleet scope (snapshot does not cover the P1-C
  target); the generator exists only as a session artifact
  (`artifacts/session/governance_repo_matrix_20260525.ps1`), not a
  registered tool.
- [x] Verify memory file naming against `memory_layout` aliases during F-7
  application: meiandraybook uses `memory/02_tech_stack.md`, compatible with
  both `F7_GOVERNANCE_ALLOWLIST` and `memory_layout` aliases. Divergence
  seed remains latent for consumers using `02_workflow.md`; NOT claimed
  resolved.
- [x] Observe and record rollback path expectation: submodule pointer chain
  on origin/main is `da1d4f3 -> 0eafe10 -> 554607f -> b14c15b`; rollback =
  checkout previous known-good pointer (`554607f`) inside the submodule and
  commit on a clean worktree. Observation only; no procedure implemented.

P1 - update rollback documentation (P1-C follow-up; do not start before
the P1-C rollback observation exists):

- [x] Document rollback procedure for a failed F-7 update / failed smoke
  after governance update. Updating governance is itself a trust-surface
  change and must be reversible per the core principle (expensive,
  explicit, reversible). (Closed 2026-06-13:
  `docs/fleet/governance-update-rollback.md` — what can / must not be
  auto-rolled-back, pre-rollback evidence capture, execution order with
  clean-worktree stop-at-diagnosis gate, post-rollback verification
  (behind-latest is the correct post-rollback state), and claim ceiling
  after rollback. Grade caveat recorded in the doc: derived from the
  P1-C read-only observation, never execution-tested; the first real
  rollback is its own evidence-producing slice. No rollback executed,
  no updater/F-7/hook/validator change, no consumer repo touched.)

P1-D - Structured PLAN Reconciliation Declaration (design agreed 2026-06-12;
do not start before the P1-C fixture exists):

- Goal: every completion-oriented memory record must declare whether it has
  been reconciled with PLAN, and if not, why not. The gate target is silent
  drift, not deferred drift. This is NOT PLAN auto-sync and must not induce
  agents to edit canonical PLAN to legalize their own completion claims.
- [x] Add `--plan-reconciliation` field to `governance_tools.memory_record`
  (2026-06-12): `updated` | `not_applicable` | `deferred:<reason>`;
  omission is recorded as `not_declared` with a writer advisory (never
  blocks); malformed values are rejected as input errors (exit 2).
- [x] Deferred reasons validated against the reason taxonomy
  (`requires-human-plan-review`, `awaiting-reviewer-verdict`,
  `scope-split-next-slice`, `canonical-update-not-authorized`,
  `dirty-workspace-prevents-safe-edit`); empty or vacuous reasons
  (`later` / `todo` / `pending` / `soon` / `TBD`) rejected. Taxonomy
  extension is PR-only.
- [x] Pre-push advisory implemented on the current-date memory gate seam:
  reports session-derived records in today's memory file lacking a
  declaration; advisory only, never blocks. 11 focused tests added
  (validation, render, CLI rejection, CLI advisory).
- [ ] P1-E: collect 2-4 weeks of false-positive / false-negative samples
  before any blocking decision (window started 2026-06-12; first data
  point: 14 of 15 same-day records pre-date the field).
  Checkpoint 2026-06-27: two-week observation evidence recorded in
  `docs/governance/p1e-plan-reconciliation-two-week-sample-2026-06-27.md`.
  Report output after the 2026-06-27 canonical memory record exists:
  updated=34, not_applicable=110,
  deferred=7, not_declared=24, pre_field=249, malformed=0; all deferred
  records use `scope-split-next-slice`, oldest deferred sample is 10d old
  (2026-06-17), oldest not_declared sample is 15d old (2026-06-12), and
  no deferred/not_declared records appeared after 2026-06-24 in the checked
  June daily files. Focused validation passed
  (`tests/test_deferred_debt_report.py`: 12 passed), and an independent
  read-only reviewer thread approved the conclusion as Low risk.
  Snapshot boundary: these counts are an observation of this worktree /
  commit-state memory tree; future canonical memory records are expected to
  change the live report totals without invalidating this checkpoint.
  Claim ceiling: observation-class evidence only; this checkpoint may inform
  reviewer judgment about whether to open a separate P1-F OP-HC /
  mutation-contract slice, but it does not authorize a blocker, prove memory
  semantic correctness, complete the full 2-4 week window, or add any hook /
  CI / pre-push / gate / enforcement behavior.

P1-G - registered reproducible fleet matrix generator (completed
2026-06-12):

- [x] Generator promoted from session artifact to
  `scripts/governance_repo_matrix.ps1`; framework root parameterized
  (`AI_GOVERNANCE_FRAMEWORK_ROOT` override, script-relative default);
  output path policy documented in the tool header.
- [x] Reproducibility metadata emitted: `matrix_generated_at` (UTC),
  `generation_tool`, `generation_tool_commit`, `source_repo_set`
  (definition=hardcoded-in-tool, company/private repo lists, scope file
  used for classification), `evidence_window_days`.
- [x] `governance_tools/fleet_matrix_snapshot_validator.py` validates
  snapshot metadata; 6 focused tests including legacy-shape rejection
  and generator static checks.
- [x] Reproduction verified: registered tool regenerated the fleet matrix
  output type (snapshot `20260612_180253`) and passes the validator.
- Claim boundary — CLAIMED: fleet matrix generation is reproducible
  through a registered, attributable tool. NOT CLAIMED: fleet evidence
  fresh, refresh cadence solved, monitored repo set correct, fleet
  health restored, or meiandraybook in scope.

P1-H - fleet freshness cadence decision (decided 2026-06-12):

Decision: event-driven (Option A adopted now; Option C repo-class SLA
deferred; Option B weekly scheduler rejected for now).

- [x] Observed freshness behavior recorded: required_verified 9/10
  (2026-05-29) -> 1/10 (2026-06-12 refresh after 14 idle days) -> 2/10
  (after same-day framework pushes). Decay and recovery both track real
  activity; the 7d window operated as designed — this was evidence
  decay, not regression.
- [x] Semantics defined: `required_verified` ratio is freshness-window
  evidence (a time-window observation), NOT a permanent health score.
  A low ratio after an idle period is expected decay.
- [x] Policy adopted: fleet freshness is event-driven. A fleet matrix
  refresh via the registered generator is REQUIRED before rollout,
  release, or any external presentation claim that cites fleet state.
- [x] Weekly scheduler explicitly rejected for now: ritual-refresh risk,
  background-execution claim burden, and missed-run semantics cost —
  the same boundary class as manual/resume-triggered reviewer polling.
- [x] No new automation or background execution claim introduced.
- [x] Repo-class freshness SLA (Option C) deferred until the scope
  taxonomy slice defines which repos belong to which policy.

P1-I - scope taxonomy for governance repo sets (decided 2026-06-12):

Each scope is defined by what a member repo's evidence must prove, not by
where the repo happens to live:

- `fleet_scope`: repos whose governance state feeds the freshness matrix.
  Membership criteria: locally checked out where the registered generator
  runs; governance surfaces adopted or onboarding-tracked; cited by
  release / rollout / external claims. Evidence duty: freshness-window
  matrix (event-driven per P1-H).
- `submodule_consumer_scope`: any repo consuming the framework through a
  git submodule. Evidence duty: framework.lock / submodule pointer
  currentness only.
- `f7_consumer_scope`: subset of submodule_consumer_scope receiving
  managed F-7 full updates (AGENTS keyed sections, managed hooks, memory
  workflow router). Evidence duty: per-update F-7 apply / verification
  evidence, event-driven.
- `external_contract_repo_scope`: repos providing domain contracts that
  the framework consumes. Evidence duty: contract validation evidence,
  event-driven.

Set relations: f7_consumer is a subset of submodule_consumer; fleet may
intersect any other set (observed today: Kernel-Driver-Contract,
verilog-domain-contract, and writing-contract are simultaneously fleet
members and contract repos). Membership in one set does not inherit the
evidence duties of another.

Decisions:

- [x] meiandraybook classified: f7_consumer_scope and
  submodule_consumer_scope; NOT fleet_scope — and the taxonomy does not
  require it there, because its claims are update-evidence-based
  (pointer currentness + F-7 verification), not freshness-matrix-based.
  No automatic fleet addition performed.
- [x] hardcoded-in-tool repo set: ACCEPTED for now as the operational
  enumeration of fleet_scope (single operator environment; set stable
  since 2026-05-25; self-declared in snapshot metadata). Re-evaluation
  trigger: the first taxonomy-driven membership change request, or a
  second operator environment.
- [x] Scope manifest decision recorded: a manifest extending
  `governance/fleet/governance_scope.yaml` (which today classifies tiers
  but does not enumerate members) is the correct long-term single
  source; migrating the generator to manifest-driven enumeration is
  DEFERRED until the first real membership change requires it
  (failure-driven; no tool change in this slice).
- [x] Repo-class freshness SLA (P1-H Option C) remains deferred until
  this taxonomy survives at least one real membership decision.
- [x] No repo-set mutation performed; generator untouched.
- [ ] P1-F: upgrading to a current-diff blocker changes what counts as a
  legal completion claim and is therefore an [OP-HC] decision requiring
  FP data, a rollback path, and its own mutation contract. Not authorized
  by this item.
- [x] Add a non-blocking deferred-debt report (deferred count by reason,
  oldest deferred age, PLAN-touched records without `updated` status) to
  prevent acknowledged-drift from becoming a landfill.
  (Implemented 2026-06-13 exactly per the checkpoint below:
  `governance_tools/deferred_debt_report.py`, read-only, deterministic
  given `--as-of`, json/human stdout, optional `--output`; the four
  checkpoint observables only; pre_field guard verified by a dedicated
  test; historical non-UTF-8 daily files (2026-04-10, 2026-05-04)
  surfaced as `files_with_decode_errors` via lossy decode — observed,
  not repaired. 12 focused tests passed; adjacent memory_record /
  memory_workflow 23 tests passed. First real-repo run as-of
  2026-06-13: updated=18, deferred=0, not_declared=14 (oldest
  2026-06-12, matching the P1-E first data point), pre_field=249,
  malformed=0. No CI wiring, no thresholds, no gate semantics, no
  historical record rewritten.)

Deferred-debt report implementation checkpoint (decided 2026-06-13;
no code written in this slice):

- Report scope (exactly four observables, all machine-decidable from
  record fields):
  1. count of session-derived records by `plan_reconciliation` value
     (`updated` / `not_applicable` / `deferred:<reason>` /
     `not_declared`);
  2. deferred breakdown by taxonomy reason;
  3. oldest age per deferred reason (days since record's file date);
  4. `not_declared` count and oldest age (the silent class the gate
     targets).
- Explicitly OUT of report scope: semantic detection of "PLAN-touched
  records without `updated`". Whether a record's work touched PLAN is
  not machine-decidable from record fields; `not_declared` and
  `deferred` are the observable proxies. The original PLAN wording is
  narrowed to these proxies; semantic detection would require content
  analysis and is not claimed.
- Input source: canonical daily memory files `memory/YYYY-MM-DD.md`
  only, parsed with the same record format the memory workflow uses.
  Records pre-dating the field (before 2026-06-12) are bucketed as
  `pre_field` and are NOT debt — they are expected history, consistent
  with the P1-E first data point (14 of 15 same-day records pre-dated
  the field).
- Output format: read-only tool, `--format json|human` to stdout,
  optional `--output <path>`; deterministic given the same inputs; no
  ledger append, no artifact mutation by default (no-write discipline).
- Claim ceiling: observation-class only. A deferred declaration with a
  taxonomy reason is a legal honest state, not a failure; a
  `not_declared` is advisory-era data, not a violation; the report has
  no thresholds, no pass/fail, and is not a gate input. It may later be
  cited as evidence by the P1-F decision but cannot close P1-E or
  authorize blocking by itself.
- Implementation slice (when opened): `governance_tools/`
  read-only tool plus focused tests; non-goals pre-declared — no
  validator change, no CI wiring, no blocking semantics, no thresholds,
  no auto-cleanup, no rewriting or reclassifying historical records.

P1 - selective enforcement decision (closed 2026-06-12 by P1-A, `5deb8bb`):

- [x] Decide whether any CI or hook path should opt into `--fail-on-blocker`:
  CI workflow path only, current-diff scope.
- [x] Preserve default advisory mode unless current-diff blocker false-positive
  rate is acceptable: hooks remain advisory.
- [x] Do not upgrade historical `missing_canonical_memory` or `unbound_memory`
  warnings into blockers without separate approval: preserved, warning-only.
P1 - structured memory freshness:

- [x] Define freshness / rollover policy for structured canonical memory files
  such as `memory/01_active_task.md`. (Policy v1 canonicalized 2026-06-13:
  `docs/structured-memory-freshness-policy.md` — staleness defined as
  event-driven contradiction against PLAN at HEAD, not age; rollover is
  event-driven with no SLA and no scheduled refresh; repair only in a
  dedicated bookkeeping slice derived from PLAN plus the latest closure
  record, never from session narrative; mandatory pre-repair comparison
  surfaces with stop-at-diagnosis on PLAN/closure disagreement;
  post-repair claim ceiling is point-in-time consistency only.
  Policy-only slice: no writer, hook, validator, or automation change.)
- [x] Define whether `PLAN.md` to structured-memory consistency should become
  a validator-backed self-check. (Decided 2026-06-13 in policy v1 §6:
  manual event-driven comparison now; advisory tooling deferred
  failure-driven; blocking enforcement remains a separate OP-HC-class
  decision with its own mutation contract. Not a validator today.)
- [ ] Do not claim structured memory sync is solved by daily memory writer
  completion alone. (Standing constraint; restated in policy v1 §5.)
- [x] Follow-up (gated on policy v1 being canonical, which it now is):
  apply the policy to refresh the currently-stale
  `memory/01_active_task.md` in a dedicated bookkeeping slice per policy
  §3-§5. Policy definition and policy application must not share a
  slice. (Applied 2026-06-13: pre-repair comparison ran per §4 — PLAN
  at HEAD `ce6de50` vs closure record 2026-06-13, no disagreement, stop
  rule not triggered; file rewritten from PLAN + closure record only,
  with refresh provenance header; claim recorded as point-in-time
  consistency with PLAN as of `ce6de50` only. Not claimed: freshness
  solved, sync automated, future staleness prevented, writer compliance
  enforced.)

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

- [x] Classify whether copy-based consumers are supported, audit-only, or
  unsupported for automated update. Current claim ceiling: not solved.
  Classification first; do not design support tooling before P1-C
  consumer evidence exists. (P2-C 2026-06-12: classified **audit-only**
  for classification/audit wording; automated update **unsupported**
  (zero copy-based consumer evidence). Canonical taxonomy in
  `docs/ADOPTION_MODEL.md`: five consumer classes each with required
  evidence, allowed claims, prohibited claims, upgrade path; sole
  upgrade path to managed updates is migration to submodule consumer;
  classification-precedes-tooling rule stated; aligned to P1-I scope
  sets with PLAN-wins precedence. No tooling designed or changed.)

P2 - external presentation:

- [x] Refresh GitHub repository description. (P2-G closed 2026-06-13:
  ratified C3 string applied manually by the user in the GitHub web UI —
  no authorized agent-side metadata write path existed and none was
  created; agent verification via unauthenticated GET
  /repos/Gavin0099/ai-governance-framework returned exact_match=True
  against the PLAN-recorded string, em dash intact, repo
  updated_at=2026-06-12T16:44:24Z. Agent metadata mutation: none.)
- [ ] Add relevant topics. (Gated by P2-E: allowed only after exact-list
  ratification; descriptive taxonomy nouns only.)
- [ ] Align README badge with current release state. (P2-E decision:
  DEFERRED until the first gated release exists; no badge before that.)
- [x] Align README capability table with current reality: mutation topology
  caveat on the fail-closed gate row, audit-framework-not-security-boundary
  positioning sentence, and MEM-DISPATCH capability row. (P2-A 2026-06-12:
  table gained a Claim class axis — Enforced / Advisory / Observation /
  Cannot claim — with definitions; MEM-DISPATCH row added as Advisory +
  selective Enforced scoped to current-diff `active_non_canonical_writer`;
  stale "10 required repos verified" wording removed; positioning sentence
  now present in both ZH and EN sections.)
- [x] State in README that the fleet freshness ratio is time-window
  evidence under an event-driven refresh policy, not a permanent health
  score (prevents idle-period decay being read as regression). (P2-A
  2026-06-12: freshness-semantics paragraph added to both Fleet sections
  per P1-H semantics; idle-period decay stated as designed behavior.)
- [x] Prepare English reviewer-facing docs (README, starter-pack,
  onboarding SOP). Split (P2-B 2026-06-12). (Parent closed 2026-06-13
  once all four sub-items carry evidence. Closure scope: this closes the
  README English review pass only — English readability + claim-class
  consistency. NOT claimed: bilingual content parity. The English README
  half contains sections newer/more complete than the Chinese half
  (Agent Runtime Governance Profile, Governance Artifact Discipline Index,
  f7 Key-Documents row, one-line apply prompt); that asymmetry is a
  bilingual-content gap, not an English-readability failure, and any
  parity repair is a separate slice.)
  - [x] Reviewer entry doc `docs/REVIEWER_ENTRYPOINT.md` created: claims /
    non-claims / evidence required for done / advisory-vs-enforcement
    reading rules; linked from README Key Documents (ZH+EN). Bounded by
    PLAN Active Claim Boundaries with explicit PLAN-wins precedence.
  - [x] Starter-pack English review pass. (P2-D 2026-06-12: full English
    mirror section added to `examples/starter-pack/README.md`; adoption
    model alignment note added in both languages — copying starter-pack
    files does not make a repo a governed consumer; upgrade path is
    submodule adoption.)
  - [x] Onboarding SOP English review pass. (P2-D 2026-06-12: SOP scoped
    to the submodule-consumer path; Step 0 classification gate added per
    `docs/ADOPTION_MODEL.md` with copy-based stop rule; internal GitLab
    hostname replaced with `<framework-remote-url>` placeholder; claim
    ceiling section added — onboarding evidence only, no fleet or
    currentness claims.)
  - [x] README English review pass. (Done 2026-06-13. Dedicated English
    readability + claim-class consistency pass over the README English
    half: ten-row capability table reviewed — Status / Claim class
    identical across both language halves, no claim drift; all claim
    ceilings intact (audit-not-security-boundary, single-point E1-B
    Phase 2 / mutation protection not claimed, copy-based unsupported,
    Agent Runtime Profile not-X clauses, freshness not-a-health-score).
    One claim-neutral readability edit applied: "claim tasks are
    complete" -> "claim that tasks are complete" (README.md). NOT
    claimed: all English docs reviewed, bilingual parity completed,
    README perfect, content symmetry achieved. Residual originally
    identified 2026-06-13 is now evidenced by this slice.)
  - [x] README bilingual content parity. (Done 2026-06-13. Commits
    2493af9 + 6301918. Four English-only sections mirrored to Chinese
    half: one-line apply prompt, f7 key-documents row, Agent Runtime
    Governance Profile with all seven claim-ceiling clauses, Governance
    Artifact Discipline Index. Commit 2493af9 additionally calibrated
    Chinese intro claim text (removed 'enforceable' / 'auditable'
    overloading) and added trust model paragraph missing from Chinese
    half. Mixed-commit (a402122) identified during remediation; split
    into two clean boundary commits. Verdict: ACCEPT_WITH_CAVEATS.
    Workspace: clean for review/commit purposes after excluding two
    declared runtime ledger side effects. NOT claimed: full bilingual
    symmetry, complete content parity, or any runtime guarantee
    expansion.)
- [ ] Publish a release only after release notes and claim ceiling are
  accurate. (P2-E adds: release notes must use the Claim class taxonomy
  and link `docs/REVIEWER_ENTRYPOINT.md`.)

P2-E - publish-surface decision checkpoint (decided 2026-06-13; no
publish surface edited in this slice):

Governing rule: publish surfaces (GitHub description, topics, badges,
release notes) are claim amplifiers — they are read as first-impression
self-claims with no Claim class column attached. No publish-surface text
may claim above the README capability table; on conflict, the table and
the Active Claim Boundaries win.

Prohibited wording classes on any publish surface: "solved", "fully
automated", "production-ready", "secure" / "security boundary",
"fleet-ready" / "fleet rollout complete", "supports all repos",
"automatic adoption" / "automatic updates", and any wording that
contradicts the audit-framework-not-security-boundary positioning or
the copy-based audit-only classification.

Per-surface decisions:

- [x] GitHub description: ALLOWED, gated on exact-string ratification.
  Ceiling: mechanism description only (contract-bound execution,
  artifact-backed verification, fail-closed decisions); no outcome
  claims. The exact string is the deliverable of its own slice and must
  be recorded in PLAN before applying.
- [x] GitHub topics: ALLOWED, gated on exact-list ratification. Ceiling:
  descriptive taxonomy nouns only; no maturity-, guarantee-, or
  scale-implying topics.
- [x] README badge: DEFERRED. A badge must reflect a real, gated release
  state; no release currently passes release-notes gating, so any badge
  now is decoration or inflation. Revisit at the first gated release.
- [x] Release publish: remains GATED by the existing canonical rule
  (accurate release notes and claim ceiling first), plus the Claim class
  taxonomy / reviewer-entrypoint linkage requirement above.

Activation rule: each ALLOWED surface still requires its own slice whose
deliverable is the exact text or list, checked against this ceiling and
user-ratified before the edit is applied. "P2 core documentation
calibration complete" does not equal "public promotion ready".

P2-F - GitHub description candidate strings (proposed 2026-06-13;
RATIFIED 2026-06-13: C3 selected by user):

Ratified final GitHub description (exact string):

    Audit framework for AI-assisted engineering: contract-bound
    execution, artifact-backed verification, fail-closed decisions
    — not a security boundary.

(Single line when applied; wrapped here for PLAN readability.)

Ratified claim ceiling: mechanism-only. The description may describe
the framework's audit/governance mechanisms but must not imply security
coverage, fleet readiness, automatic adoption, or production
completeness. Ratification rationale recorded: C2 rejected for
deflationary mismatch (real Enforced rows exist); C3 is zero-increment
relative to README canonical text.

Candidate history:

- C1: "AI-agent governance framework for claim calibration, evidence
  discipline, and reviewer-facing adoption boundaries."
  Ceiling check: no prohibited wording; "framework" matches the repo
  name itself, so it adds no claim beyond the name.
- C2: "Documentation-first controls for AI-agent claim calibration,
  evidence discipline, and adoption boundaries."
  Ceiling check: no prohibited wording, but flagged for
  under-claiming: the capability table contains real Enforced rows
  (fail-closed gate, selective CI blocker, runtime hooks are code, not
  docs). "Documentation-first" invites readers to expect zero runtime
  enforcement, creating a deflationary mismatch with the table.
  Calibration means accurate, not minimal.
- C3 (recommended): "Audit framework for AI-assisted engineering:
  contract-bound execution, artifact-backed verification, fail-closed
  decisions - not a security boundary."
  Ceiling check: zero-increment claim - the mechanism triple is the
  README first line verbatim and the trailing clause is the canonical
  positioning sentence; it claims exactly what the README already
  claims, nothing more.

Ratification rule (satisfied 2026-06-13): exactly one candidate
(possibly amended) must be ratified by the user; the ratified string is
recorded above as final. The description metadata edit slice (P2-G) is
now unblocked for the exact ratified string only. Topics remain a
separate slice (P2-H) — they are not bundled, because topic words like
"security" / "automation" / "ci" can re-amplify claims independently.

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

Generated compatibility snapshot boundary:

- `artifacts/governance/version_compatibility.json` is a generated
  compatibility snapshot, not the canonical source of version truth.
- Source of truth: rerun `governance_tools.governance_version_check` /
  session-start version compatibility logic when reviewer-facing evidence is
  needed.
- The generated snapshot is ignored so runtime smoke / session-start
  regeneration does not create tracked dirty state.
- Ignoring the snapshot does not remove the need to verify version
  compatibility when a task claims version compatibility evidence.

Known local EOL/status residual:

- `tests/test_governance_drift_checker.py` may appear modified on this Windows
  workspace because of local Git EOL/status behavior.
- Latest evidence: working hash equals the HEAD blob
  (`4de281e3acecad47b4e23c16cbb58187e78e0bb2`); `git diff --raw` reports no
  content diff; `git ls-files --eol` reports `i/lf w/lf`.
- Treat this as a local hygiene residual, not a source diff, unless new evidence
  shows a real content change.

Policy:

- Do not stage these files with documentation, memory workflow, or F-7 commits.
- Treat them as runtime side effects unless explicitly audited for promotion.
- Overall workspace remains NOT CLEAN while these files are dirty.
- Do not claim workspace clean while the EOL/status residual remains visible.

2026-06-18 owner-ratified ledger policy direction:

- Option B selected: these two ledgers should become ignored-by-default runtime
  artifacts.
- Durable reviewer-facing evidence must come from explicit audit / reviewer
  milestone export, not accidental runtime append commits.
- Implemented 2026-06-18: ledgers untracked + ignored (`ffd9609`, local files
  kept); manifest-only milestone export tool added (`bf798d4`). No runtime
  writer / hook / validator / closeout change.
- NOT CLAIMED: raw-snapshot export refinement, reviewer-handoff export
  integration (separate slices), historical evidence migration, workspace
  clean, or Gate 3 opening.

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

This planning / structured-memory bookkeeping refresh is done when:

- `PLAN.md` records the 2026-07-06 current focus, completed scope, pending
  work, claim ceilings, and non-claims.
- `memory/01_active_task.md` is refreshed from `PLAN.md` plus canonical daily
  memory, not from unbound session narrative.
- Claim ceilings and non-claims are explicit.
- Scoped diff checks pass for `PLAN.md` and `memory/01_active_task.md`.
- `governance_drift_checker` is checked before and after the refresh.
- The refresh is committed separately from unrelated runtime ledgers.
- A canonical memory record is written after the commit.

## Cannot Claim From This PLAN Alone

- Cannot claim that all historical evidence was migrated into this file.
- Cannot claim that external repos are updated.
- Cannot claim fleet enforcement completion.
- Cannot claim memory historical debt cleanup.
- Cannot claim semantic verification of every historical milestone.
- Cannot claim GitHub release / README / topics are current.
- Cannot claim workspace clean while runtime ledgers remain dirty.
