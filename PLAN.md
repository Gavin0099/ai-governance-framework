# PLAN.md - AI Governance Framework

## Canonical Planning Surface

> **最後更新**: 2026-07-22
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

## Work Item Glossary

Use this short decoder when reading historical or current PLAN labels.  A code
preserves traceability; the phrase states its purpose.  The checkbox and
nearby status text remain the authority for whether an item is complete.

| Label | Plain-language purpose |
| --- | --- |
| Phase A--E | Major work periods: core baseline; adoption/memory foundations; runtime observation; external adoption/reviewer workflow; and the current failure-boundary/exclusion/usage-enforcement line. |
| P0 / P1 / P2 | Priority groups; the letter identifies a work item within that group. |
| P1-C | First external F-7 verification for `meiandraybook`; the natural-session closeout-receipt check completed read-only on 2026-07-22, while its separate consumer memory blocker remains outside P1-C. |
| P1-D | Structured `plan_reconciliation` declaration for canonical memory records. |
| P1-E | Observation evidence for declaration behavior; it does not by itself authorize enforcement. |
| P1-F | Decision about stronger declaration enforcement. Decided 2026-07-18: keep advisory and do not add a current-diff blocker; reopen only after a natural post-Option-B `not_declared` failure. |
| P1-G / P1-H | Reproducible fleet-matrix generator / future decision about fleet-update freshness. |
| P2-E | Rules for public-facing release surfaces such as topics, badges, and release notes. |
| F-7 | Governed full framework update for a consumer repository, with staged evidence; a pointer update alone is not F-7 completion. |
| E2 | Retrospective external-engineer adoption evidence. It is usability/adoption evidence, not runtime-effectiveness proof. |
| Gate 3 | Frozen learning-loop unpause gate; it opens only under its documented criteria and explicit owner approval. |
| E1-B, E8A, CE-1C/1D, R49.x, Round A/B | Historical experiment, claim-enforcement, or retrieval/cache study labels. Read their linked artifact before treating them as active work. |
| v1 / v2 / v3 | Versions of the no-governance baseline experiment; their individual status and claim boundary are recorded in the current task and status artifacts. |

Phase D completion note:

- Reviewer closeout artifact was signed by Gavin0099 on 2026-04-28.
- Later Phase C / runtime reconciliation gaps were tracked as follow-up work,
  not as a reason to inflate current Phase D claims.

Phase E posture:

- Validity before expansion.
- Failure-driven governance only.
- No broad enforcement upgrade without observed failure and scoped evidence.

## Current Sprint - 2026-06-10

Current refresh - 2026-07-24:

Theme:

- Record the Evidence-Backed Engineering Skill Program as a review-only plan
  before any Engineering Skill exists. The program is a method for studying
  whether mature engineering methods change agent outcomes; it does not assert
  that any method works.

Completed in this slice:

- [x] `docs/governance/evidence-backed-engineering-skill-program-2026-07-24.md`
  records the Skill / Harness / External Validator / Governance responsibility
  boundary, the Bug Fix four-arm experiment, natural task sourcing, independent
  oracle, blind post-hoc scoring separated from Arm D treatment-time validator
  feedback, outcome and cost metrics, commit and receipt evidence anchoring
  (`linked_commit` vs `linked_head_commit`), Gates 0-5, and
  INVALID / NEGATIVE / INSUFFICIENT stop outcomes.
- [x] The candidate-method appendix classifies further methods as priority
  study, cross-cutting methods, or deferred study. Every appendix entry is a
  deferred candidate, not an implementation commitment or a roadmap.
- [x] Gate 1 freezes the experimental Skill treatment packet as an experiment
  input only; a repo-visible provisional Skill may exist no earlier than
  Gate 3, and Gate 3 is a screening decision, not a powered inference.
- [x] No Engineering Skill was created or modified, no experiment was run, and
  no validator, schema, runtime, hook, CI, gate, or enforcement changed.

Current refresh - 2026-07-22:

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

- [x] Validator-delegation census plan was published to canonical main at
  `6a20d0a6`, then the bounded fixed-snapshot artifact was published at
  `a89ee202` with closeout recorded at `63462432`.
- [x] The published census artifact is intentionally frozen to base
  `e737572e`, `population_count=197`, and normalized hash
  `b590fb5fef8dc1a921655877091447a44f42232219c8d91c3a413f467e74da6f`.
  This remains a historical fixed snapshot only; it does not claim coverage
  of any later tip, and it does not authorize delegation implementation,
  retirement, migration, or external adoption.
- [x] No further census action is currently authorized. The fixed-snapshot
  claim boundary remains in force until a separate owner-approved slice
  explicitly authorizes refresh or downstream use.

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

- [x] This bookkeeping alignment slice is complete once `PLAN.md` and
  `memory/01_active_task.md` are reconciled against the published census
  history. No new framework implementation slice is active at this commit.
- [x] A plain-language response failure has already been observed rather than
  remaining hypothetical: two comprehension failures required a report rewrite
  before an engineer or the owner could act. This satisfies the
  failure-driven eligibility condition for a separate response-quality slice;
  it does not authorize implementation by itself.
- [x] Owner-authorized on 2026-07-17 and implemented at `61673ca9`: mechanical
  plain-language final-report validation exists as opt-in
  `--check-response-quality` in `response_envelope_validator.py`, requiring
  `conclusion`, `recommended_action`, and `next_action` to be non-empty and
  positioned before `evidence_refs`. Default validator behavior is unchanged,
  and no hook, CI, gate, or default invocation enables the check; enabling it
  anywhere remains a separate owner decision. The slice stayed separate from
  census refresh, delegation implementation, module retirement, consumer
  migration, and release preparation.
- [x] Second failure-driven response-quality slice (owner-authorized
  2026-07-18): direct owner feedback showed a report passing the v0.4
  structural check was still unreadable — field presence does not equal
  comprehension. Added opt-in `--check-plain-summary`: `conclusion`,
  `reason`, `next_action` exactly once before `evidence_refs`, each a
  sentence rather than a bare machine token (tokens need a plain-language
  gloss; `next_action: none` rejected). The observed unreadable reply is a
  must-fail regression fixture; the owner's three-line plain version is a
  must-pass fixture. Contract v0.5 records the honest boundary: structural
  proxy only — it raises the probability of readable reports and cannot
  prove comprehension; the real success signal remains direct reader
  feedback. Default behavior unchanged; no hook/CI/gate enables either
  check.
- [x] Third failure-driven owner-summary refinement (owner-authorized
  2026-07-22): a real completion report still made the owner decode technical
  state before finding the result and next move. Contract v0.6 now makes the
  literal first three non-empty lines `Result / Reason / Next step` (translated
  to the session language), moves technical evidence after that preface, and
  uses actual reader understanding as acceptance. The existing opt-in
  validator remains unchanged; no hook, CI, gate, or default enforcement was
  added.
- [x] G4 manual work-item case 001 records that response-readability line as one
  self-hosted early outcome signal rather than counting its sessions, commits,
  validation, and memory events as separate samples. It binds the natural
  failure, v0.6 response, owner replay acceptance, four owner interventions,
  observable delivery cost, recurrence boundary, and absent transfer evidence
  in `docs/status/g4-work-item-case-001-owner-summary-2026-07-22.md`. G4 remains
  unclaimed; no independent consumer, non-author, cross-repo, sustained, or
  benefit-over-cost conclusion follows from this case.
- [x] The first cross-consumer G4 observation checkpoint groups five natural
  work-item candidates across `Bookstore-Scraper`, `meiandraybook`, and
  `Enumd-private-vault` without counting sessions or commits as samples. It
  records two qualifying cases, one Bookstore zero-effect / owner-corrected
  case, and two insufficient-evidence Mei candidates in
  `docs/status/g4-cross-consumer-observation-checkpoint-2026-07-22.md`.
  This is early multi-consumer outcome evidence only: G4, sustained outcomes,
  non-author independence, and benefit-over-cost remain unclaimed.
- [x] The 2026-07-24 successor checkpoint preserves the 2026-07-22 snapshot
  and adds one distinct Bookstore slow-source / Grimm work item, producing
  three qualifying cases, one zero-effect case, and two insufficient-evidence
  Mei candidates in
  `docs/status/g4-cross-consumer-observation-checkpoint-2026-07-24.md`.
  The new Bookstore case retains its `linked_commit=e478409` receipt-anchor
  warning; canonical memory binds the product correction to `c9cd494`.
  Enumd Phase I-R remains one continuing private-vault case, and Mei PR #9
  does not become a new sample from PR volume alone. Qualifying breadth remains
  two consumers; G4, sustained outcomes, independent review, comparable cost,
  and benefit-over-cost remain unclaimed.
- [ ] For every other framework-expansion direction, wait for a real consumer
  failure or a new product need before opening a slice.

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

- [x] v3 preregistration frozen from both rehearsed arms at
  `docs/governance/no-governance-baseline-v3-preregistration-2026-07-10.md`.
  It binds the baseline/seed/task hashes, launcher/package/provenance locks,
  both arm procedures, and a pre-declared zero-scoreable-output exclusion rule
  for package-context Arm B hook-environment failure. The owner subsequently
  authorized task-prompt and scratch-content transmission for Run 1 only. Arm
  A Run 1 completed through the owner-executed launcher and is archived at
  `docs/status/no-governance-baseline-v3-a1-archive-2026-07-11.md`; its raw
  evidence and poststate are retained, but no metrics, blind review, ledger,
  or attribution conclusion has been created.

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
- [x] Read-only decision-change ledger inventory-line pass completed at
  `e30b1576` (`docs/governance/decision-change-ledger.inventory.v0.1.json`).
  All 193 `governance_tools` modules were compared against wiring and output
  evidence; 40 candidates were escalated, 4 were marked retire_candidate, and
  the retire-candidate line was later fully dispositioned.
- [ ] Use the completed inventory-line results as historical input only. Do
  not merge, downgrade, or retire any governance surface without a separate
  authorized slice and evidence for the specific change.
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
- CLAIMED: a bounded validator-delegation census fixed snapshot was published
  as a historical artifact pinned to `e737572e` / 197 modules, with no
  delegation, retirement, migration, or adoption authority attached.
- NOT CLAIMED: prompt cache implementation, cache hit/miss monitoring,
  compaction control, mode/auth/tool-denial receipt tooling, runtime hook/CI
  wiring, enforcement, canonical authority promotion, external harness
  adoption, v1.3.0 release readiness, cross-repo writes, automatic test-quality
  enforcement, industry-grade test proof, noisy-surface retirement, measured
  token savings, context-cost compliance, current-tip census coverage, or any
  actionability derived solely from the census artifact.

Latest milestone commits:

- `8a98df2e chore(memory): record P1-F publication`
- `ba50b0f4 docs(governance): close P1-F as advisory`
- `c8c06f3e feat(governance): add opt-in plain-summary validation`
- `63462432 chore(memory): record validator census publication`
- `a89ee202 docs(governance): add validator census e737 snapshot`
- `a3dbf022 feat: add fail-closed offline submodule onboarding`

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
- CLAIMED: the read-only inventory-line pass was run at `e30b1576` and
  produced a bounded historical inventory artifact.
- NOT CLAIMED: the inventory artifact by itself retires or downgrades any
  defense, proves the dispositions are globally complete beyond the recorded
  retire-candidate line, measures context savings, creates context-cost
  companion records, or enforces context-budget rules.

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

P0 - composite workspace census evidence closeout (completed 2026-07-14):

- [x] Independently review and approve the eToken-only composite workspace
  authority tech spec while preserving repository sovereignty, discovery-only
  IDE evidence, and repo-local F-7 completion semantics.
- [x] Implement the report-only census in `6e4e5439` with an explicit
  coordinator root and sibling allowlist; keep every valid membership
  `unratified` and prohibit consumer writes, F-7 invocation, commit, and push.
- [x] Run the census against isolated copies of the three eToken repositories;
  confirm the four-line human conclusion and JSON agree with
  `E2-CONSUMER-03`, with the original consumer repositories unchanged.
- [x] Reconcile the tech spec and E2 packet to the implementation checkpoint
  and isolated validation result.

Claim ceiling: the report-only census exists and exposes per-repository gaps.
It does not establish bilateral membership, workspace governance authority,
workspace-wide F-7, G4 operator value, or general fleet demand. The live eToken
census JSON was not retained as a durable tracked receipt.

Deferred follow-up: observe normal-user census use before claiming G4 value,
then request a separate owner decision on any bilateral membership endpoint.
Do not expand F-7 from this completed tranche.

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
- [x] Verify external repo closeout receipts persist the pinned writer schema
  and memory-workflow fields: completed by read-only adjudication on 2026-07-22.
  The qualifying natural-session artifact is meiandraybook receipt
  `closeout_receipt_20260722T062442354802Z.json`. The consumer gitlink and
  nested framework HEAD are `8a98df2e`, whose writer emits schema `1.4`; the
  receipt has `schema_version="1.4"` and persists all six close-condition
  surfaces in the same artifact: `memory_workflow_dispatch_ran`,
  `memory_workflow_status`, `memory_workflow_warning_codes`,
  `memory_workflow_blocker_codes`, and `memory_workflow_guard_summary`, plus
  the pinned schema match.
  Natural Stop-hook provenance is external to the receipt's `unknown` identity
  fields: meiandraybook `.claude/settings.json` routes `Stop` to the pinned
  `session_closeout_entry.py`, and the matching Claude session transcript
  records `attachment_type=hook_success`, `hookName=Stop`, `hookEvent=Stop`,
  `cwd=D:\meiandraybook`, and the same session UUID approximately 19 ms after
  receipt creation. No manual receipt was created or replayed for this verdict.
  Separate consumer memory state remains explicit: the receipt reports
  `active_non_canonical_writer=1` and `memory_completion_claim_allowed=false`.
  That blocker prevents a clean consumer memory-completion claim but does not
  invalidate P1-C schema/field persistence or natural Stop-hook provenance;
  its correction requires a separately authorized consumer-memory slice.
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
  expectation observed; manual reconciliation fixture produced; the 2026-07-22
  natural Stop-hook receipt matches pinned schema `1.4` and persists the P1-C
  memory-workflow close-condition fields.
- CANNOT CLAIM: F-7 works for all consumers; fleet rollout complete;
  copy-based consumers solved; rollback procedure implemented; blocking
  validator added; automatic PLAN reconciliation solved; primary
  meiandraybook worktree updated; stale dirty worktree resolved; the F-7
  apply was originally executed in this slice; the 2026-07-22 consumer
  closeout gate passed; consumer memory completion was allowed; the separate
  `active_non_canonical_writer` blocker was corrected.
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
  at that time, omission was recorded as `not_declared` with a writer
  advisory (never blocks), while malformed values were rejected as input
  errors (exit 2). This historical writer behavior was superseded by P1-F
  Option B at `c06014c4`: the canonical writer now requires an explicit
  declaration and rejects omission with exit 2 before any memory write.
  Historical parsing can still represent older omitted declarations as
  `not_declared`; the writer contract does not make omission a current-diff
  blocker.
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
- [x] P1-E: collect 2-4 weeks of false-positive / false-negative samples
  before any blocking decision (window started 2026-06-12; first data
  point: 14 of 15 same-day records pre-date the field).
  Final checkpoint 2026-07-17 (day 35; window complete):
  `docs/governance/p1e-plan-reconciliation-final-checkpoint-2026-07-17.md`
  with machine-readable snapshot alongside. All 44 `not_declared` records
  are classified: 14 absent-field on the introduction day plus 30
  advisory-era literal `not_declared` produced by the pre-Option-B
  canonical writer's omission normalization; every one is canonical-writer
  output legal at write time, and the last is dated 2026-07-10 — the day
  before Option B (`c06014c4`) made the CLI declaration mandatory. Zero
  `not_declared` growth in the sample from 2026-07-11 onward; `deferred`
  flat at 7 (all `scope-split-next-slice`, none after 2026-06-24);
  `malformed` 0 across the window. FP/FN conclusion (corrected 2026-07-18
  after review): treating advisory-era literals as violations would be
  false positives; no false negatives observed in the sample, but Option B
  covers the CLI entry point only — `build_session_derived_record()` still
  defaults to `not_declared` and the runtime `session_end` hook calls it
  without a declaration, so that path can still emit `not_declared` and is
  unobserved, not eliminated. As of this checkpoint there is no observed
  failure driver for a current-diff blocker; the Option B CLI contract is
  sufficient for the CLI path observed in this window. Whether the runtime
  path needs the same treatment is a separate failure-driven,
  owner-authorized question. This closes P1-E collection only. P1-F was
  subsequently decided on 2026-07-18: maintain advisory and add no
  current-diff blocker; reopen only after a natural post-Option-B
  `not_declared` failure.
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
- [x] P1-F decided 2026-07-18 by owner: maintain advisory and do not add a
  current-diff blocker. Option B at `c06014c4` addressed the observed CLI
  omission path, with zero sample growth after 2026-07-11. The runtime
  `session_end` path can still emit `not_declared`, but no natural
  post-Option-B failure has been observed; a current-diff blocker is not a
  substitute for a writer-path fix. Reopen a separate failure-driven slice
  only if a natural post-Option-B `not_declared` record appears. This
  decision does not claim the runtime writer path is fixed.
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

P3 - Engineering Skill Program, pre-push bug study (Gate 1 complete; Gate 2 process integrity not established; Skill effectiveness not claimed):

- [x] Gate 0 admissibility recorded for the pre-push version-bump advisory bug
  (`dea492b7`); bug preserved unfixed at baseline `33006f09`.
- [x] Gate 1 pre-registration frozen values (`2c02c074`) then narrowed and
  hash-frozen (amendment v1, `61b285b2`).
- [x] **Gate 1 COMPLETE** — amendment v2 (verified named-ref bundle isolation;
  producer-safe vs designer-only validator split; unified status) owner re-signed
  2026-07-24 and confirmed by a read-only re-review.
- [x] Gate 2 preflight answer-safe setup (Gate 2 preflight manifest 2026-07-24):
  baseline bundle artifact built + verified (designer-side rebuild source only;
  the producer receives a sanitized allowlist export in a fresh object DB — tree
  36c346fa, 0 meta objects — NOT the raw bundle), execution order frozen [D,C,A,B]
  from seed 20260724, packet hashes re-verified, validator pins confirmed real,
  producer receipt template prepared.
- [x] Scorer-handoff v3 reason-code remediation independently approved and owner
  re-signed 2026-07-27 at exact manifest SHA-256
  `7104b2e03da9e61c8191430fd337b7b73effb41eb787b55e3364a21d1ac2147c`
  (commit `b596153b`). The signature is append-only; canonical promotion remains
  a separate slice and Gate 2 execution remains 0.
- [x] **Canonical promotion slice — DONE 2026-07-27.** The Gate 2 preflight
  manifest's scorer-handoff pointers and authority line were updated to the
  re-signed v3 packets (`scorer-handoff-contract-v3.json` `16bf661b…`,
  `scorer_handoff_v3.py` `77360e8f…`, `scorer_packet_v2.py` `a9671133…`).
  Nothing was recomputed. Departing from the amendment v3 precedent, the
  amendment v4 status line was **not** edited: amendment v4's own sha256 is
  recorded as `files[1]` in the owner-signed candidate manifest, so editing it
  would invalidate the signature it carries (amendment v4 Section E). Owner
  chose the append-only method. Signed bytes verified UNCHANGED and
  `verify-candidate` re-run post-promotion at 15/15 PASS
  (`artifacts/evidence/test-results/receipt-gate2-scorer-handoff-v3-promotion-20260727.json`).
  Promotion supersedes scorer-handoff v2 only; producer treatments, arm order,
  budgets, validators and scoring release gates are unchanged. Gate 2 execution
  remains 0 and resource admission is NOT performed.
- [x] Gate 2 experiment-local runner admission completed 2026-07-27 on the exact pinned image.
  Commit `3acd2659` adds only the experiment-local bounded runner, hash-pinned
  offline pytest payload, producer adapter/policies and admission evidence.
  Fresh live admission `gate2-arm-runner-admission-20260727-214036` passed fixed
  input read, 4/4 frozen tests, signed Arm D validator exits
  (shellcheck=1/ruff=1/mypy=0), negative and positive pushed-ref reproduction,
  one commit receipt and clean final status. Canonical focused precommit passed
  runtime smoke plus 187/187 tests.
- [x] Four answer-blind producer containers and two mapping-blind scorer slots
  were provisioned under `gate2-formal-20260727-213336`; the fail-closed
  resource audit passed exact image, network-none/read-only/cap-drop/no-new-
  privileges, tree/head/clean status, packet/payload digests, fresh contexts and
  scorer-slot mapping absence. This proves local resource provisioning, not the
  still-required live admission of two scorer model contexts. The first admitted set
  (`gate2-formal-20260727-212713`) was superseded before any adapter/model call
  because its run/container identifiers encoded arm letters that canonical v3
  source attestation would have exposed to scorers. The replacement uses opaque
  `OUTRUN-*` identifiers.
- [x] Owner granted destination-specific authorization and two independent live
  scorer contexts passed admission before formal execution. Formal arms then ran
  in the frozen `D -> C -> A -> B` order on the exact pinned image. D, C and A
  completed with verified producer packets; B reached the frozen 1800-second
  wall-clock cap without a clean output commit or producer `result.json` and is
  recorded as `failed_timeout`. The runbook treats inability to complete as a
  legitimate result, so B was not retried and no synthetic scorer packet was
  created. With only three scorable arms, both pre-mapping scorer submissions,
  mapping release and the preregistered process-integrity decision remain not
  run. The claim-limited terminal record is
  `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence-live/execution-evidence/gate2-formal-20260727-213336/blocked-summary.json`.
- [x] **Terminal-timeout amendment admitted for a new run — 2026-07-28.**
  Commit `1c8dcc79` preserves the blocked run, adds a separate strict
  `terminal_timeout_v1` packet, and fixes only the experiment-local Windows
  process-tree timeout cleanup. The exact amendment-set manifest is
  `dd2b97eb1a47796b5320d0581b299b5f123ab5b8416736690a6cf93d93bf09df`.
  Focused runner/packet tests passed, the real Windows tree-kill smoke passed,
  and canonical focused precommit passed 187/187. A new formal run has not
  started at this checkpoint; it still requires fresh resource/scorer
  admission. The old run is not salvageable or reinterpreted by this amendment.
- [ ] **Gate 2 execution artifacts preserved; process integrity
  `NOT_ESTABLISHED`, corrected 2026-07-28.** Fresh master
  `gate2-formal-20260728-115533` passed resource and scorer admission on the
  exact pinned image. Producer arms ran once in frozen `D -> C -> A -> B`
  order with `D=complete`, `C=terminal_timeout_complete`, `A=complete`, and
  `B=complete`; the preserved external-rate-limit B attempt was non-counted
  and the fresh B replacement alone supplied the counted outcome. Both
  independent Haiku scorers submitted scores, acceptance judgments,
  completion-claim/evidence consistency judgments, and treatment guesses with
  confidence. Mapping release and all four packet/handoff reverifications are
  preserved, but the retained evidence has no create-once timestamp, digest,
  or receipt chain that independently proves both submissions preceded mapping
  release. The earlier process-integrity `PASS` is therefore withdrawn.
  Sanitized evidence is
  committed at `1d12f6d1` under
  `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence-live/execution-evidence/gate2-formal-20260728-115533/`.
  The corrected decision records process integrity as `NOT_ESTABLISHED` and
  Skill effectiveness as `NOT_CLAIMED`.
  - **Admission state recorded 2026-07-27 (owner-accepted scope).** The
    2026-07-25 admission canary (`canary-20260725T164626Z`) is a historical PASS
    report for **producer-channel** admission, including nine isolation checks
    (network none, read-only rootfs, all capabilities dropped, no-new-privileges,
    non-root uid, no host bind mount, tmpfs workspace, no docker socket, pinned
    image). Its recorded execution paths are under a `D:` root; this checkout does not
    contain that live JSON evidence and the run was **not reproduced locally**
    (Docker daemon not running at record time). **Scorer-side is NOT RUN**:
    `admission-canary/evidence-live/` contains `capture_scorer_packet.py`,
    `verify_scorer_packet.py` and tests, but zero execution artifacts — tool
    presence is not execution evidence. Therefore **resource admission is NOT
    complete**, Gate 2 has not started, and arm execution remains 0.
    Receipt: `artifacts/evidence/test-results/receipt-gate2-admission-state-20260727.json`.
    Claimable: a historical producer-channel admission report exists.
    This historical note is superseded for current admission status by the two
    completed items above. It remains valid historical evidence about what had
    not yet run at that earlier checkpoint.

Claim ceiling: formal master `gate2-formal-20260728-115533` preserves four
scorable outcomes, two scorer submissions, mapping release, a corrected
decision, and successful packet/handoff reverification. It does not
independently establish that both submissions preceded mapping release, so Gate
2 process integrity is not established. The product pre-push hook, frozen
baseline, shared runtime, CI, gates, and enforcement are unchanged. This one
pilot does not establish treatment or Skill effectiveness, does not constitute
independent consumer evidence, and does not establish framework-level G4.
Judge engineering-method / external-tool value only in the separately governed
Gate 3 analysis; do not begin bulk tool replacement from this result.

- [ ] **Gate 3 paired-screening preregistration candidate revised
  2026-07-29; re-review/signature pending.** Commit `c5be84db` binds the
  preregistered mapping before producer execution, requires two distinct scorer
  contexts, rejects zero or unavailable core-cost data as promotion evidence,
  and verifies each admitted outcome against retained input bytes, a clean
  output commit, portable Git bundle, exact diff, event log and test receipts.
  The experiment-local common-harness contract is now part of the exact
  candidate set. Focused tests passed 33/33; canonical precommit passed runtime
  smoke plus 190/190; `core.autocrlf=true` index checkout preserved all seven
  candidate paths byte-for-byte. Exact candidate-manifest SHA-256:
  `51ac12190156eb0465d8e39a562eec0d31145bf41da5ddf8d5f1c6781a5a6801`.
  This is not independently approved, owner-signed or canonical. Gate 3 remains
  blocked on independent review of these revised bytes, explicit owner
  signature, later promotion, natural-bug/resource admission and separate start
  authority.

- [x] **Gate 3 common-harness non-counted synthetic rehearsal completed
  2026-07-29.** Implementation commit `d9f48148` produced two clean synthetic
  A/B output commits and a complete seven-event chain through
  `mapping_released`. The durable summary SHA-256 is
  `30cb88b9475d075bcf25e704f965ae8a5957c764b4f7e4eba9cf4e88f4434405`;
  chain head SHA-256 is
  `47272ba7d3518cd375eb1896466bad6c1602270be5189da5021e403adc483a27`.
  Retained bytes, baseline/output commits, exact diffs, receipts, mappings and
  structured writes replayed successfully; named mutations failed. Focused
  tests passed 45/45, canonical precommit passed 190/190 and a
  `core.autocrlf=true` checkout preserved all 55 claimed exact-byte paths.
  This rehearsal is synthetic and non-counted; its scorer fixtures are not
  independent judgments and it does not approve, sign, promote or start Gate 3.

- [x] **Gate 3 Codex credential-seeding canary ended as a non-counted negative
  result on 2026-07-30.** The independently approved implementation at
  `ad0ee5a8` invoked the one authorized exact-two/no-replacement orchestration,
  but the run terminated at private cleanup verification and published no
  public packet. The only residue was read-only synthetic Git object
  directories; exact manual cleanup completed, and cleanup hardening commit
  `479f45f5` subsequently passed independent review, focused tests 123/123 and
  canonical runtime governance 194/194. The privacy-safe negative receipt is
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/receipt-gate3-codex-auth-v1-20260730-145456-negative.json`.
  Session execution is not reconstructed from deleted private evidence, so the
  authorization is conservatively treated as consumed and no replacement was
  run. This does not establish a successful live A/B canary, does not count
  toward Gate 3, and does not open Gate 3.

- [x] **Gate 3 Codex credential-seeding canary v2 ended as a non-counted,
  non-scoreable packet-build negative result on 2026-07-30.** Implementation
  commit `5055cc32` preserved an atomic privacy-safe failure receipt for run
  `gate3-codex-auth-v2-20260730-175032`. The one authorized exact-two,
  no-replacement orchestration recorded two successful ChatGPT login
  preflights, exactly two session invocations and exit code 0 for both arms,
  then failed at `packet_build`. The operator-observed error was `rollout must
  contain one world_state`; the retained receipt proves the packet-build
  failure stage but intentionally does not retain raw stderr. Cleanup passed
  with zero residue, and no success packet was attempted, present or admitted.
  Independent review approved the 923-byte failure receipt at SHA-256
  `75efa6be6b05fbc7ed47583e70426ed4b958dba3b19da536480f3f9ad6f66c1b`
  as privacy-safe negative evidence. The authorization is consumed and no
  replacement was run. Before requesting another pair, audit the pinned
  rollout `world_state` assumption offline and add privacy-safe diagnostic
  evidence for that failure shape. This result does not count toward Gate 3
  and does not open Gate 3.

- [x] **Gate 3 Codex credential-seeding canary v3 ended as a non-counted,
  non-scoreable route-prepare negative result on 2026-07-31.** Run
  `gate3-codex-auth-v3-20260731-114500` failed at `route_prepare` before any
  session was invoked: credential preflight and both arm login statuses are
  `NOT_OBSERVED`, the credential runner receipt is `NOT_CREATED`, and
  `session_invocations` is 0. No rollout was produced, so the receipt carries
  no rollout diagnostics. Cleanup passed with zero residue and no success
  packet was attempted, present or admitted. The 960-byte privacy-safe
  failure receipt at SHA-256
  `048fed0a4e75a9170c5ec0c5cac4cb6c407da11e2dd2cc7a59f53e64b1f52865`
  is retained under
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-codex-auth-v3-20260731-114500.failure/`.
  This result does not count toward Gate 3 and does not open Gate 3.

- [x] **Gate 3 Codex credential-seeding canary v4 ended as a non-counted,
  non-scoreable packet-build negative result on 2026-07-31.** Run
  `gate3-codex-auth-v4-20260731-121500` recorded a passing credential
  preflight, `PASS` login for both arms, a `VALID` runner receipt, exactly two
  session invocations and exit code 0 for both arms, then failed at
  `packet_build`. The retained rollout diagnostics show arm A failing the
  `source` parse phase with `public` `NOT_RUN`, and arm B never parsed at all
  (`source` and `public` both `NOT_RUN`) because the first arm aborted the
  build. Both arms retained an identical source census
  (`raw_count=2`, `object_payload_count=2`, `state_object_count=2`,
  `full_true_count=1`). Cleanup passed with zero residue and no success packet
  was attempted, present or admitted. The 1533-byte privacy-safe failure
  receipt at SHA-256
  `fd1a55fc8bab933d3b88dd01a32992f3a99541216ce534a113ac4fa1214785fd`
  is retained under
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-codex-auth-v4-20260731-121500.failure/`.
  This result does not count toward Gate 3 and does not open Gate 3.

- [x] **Gate 3 Codex credential-seeding canary v5 ended as a non-counted,
  non-scoreable packet-build negative result on 2026-07-31.** Run
  `gate3-codex-auth-v5-20260731-184000` recorded the same passing execution
  profile as v4 (preflight `PASS`, both logins `PASS`, `VALID` runner receipt,
  exactly two invocations, exit code 0 for both arms) and again failed at
  `packet_build`. This is the first run in which arm A cleared both parse
  phases (`source` `PASS`, `public` `PASS`) with both censuses retained; arm B
  failed the `source` phase with `public` `NOT_RUN`. Cleanup passed with zero
  residue and no success packet was attempted, present or admitted. The
  1653-byte privacy-safe failure receipt at SHA-256
  `c1fd794d1b991e7a489defe0b1b6618f707b11631bc2ebb4fcc7010bd2c16191`
  is retained under
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-codex-auth-v5-20260731-184000.failure/`.
  This result does not count toward Gate 3 and does not open Gate 3.

- [x] **Tool-input wrapper mismatches now carry privacy-safe classification.**
  Implementation commit `f242c7a6` bumps the failure receipt schema to
  `gate3-codex-live-canary-failure-receipt.v3` and, on the packet-build
  failure path only, records the rejected tool call's family, envelope shape,
  argument shape and a field-name census restricted to a fixed allowlist of
  structural key names. No command, argument value, path, raw payload or
  credential material is retained, and unrecognized keys are counted without
  being named. Acceptance of the known-legal wrappers is unchanged. Evidence
  receipts v3 through v5 were recorded in `52d3b2bb` and predate this schema,
  so all three are schema v2 and carry no wrapper classification.

- [x] **One authorized pair attempts every arm against every parse phase, and
  says so when it cannot.** Implementation commit `67afb38a` keeps scanning
  after a rejected tool call
  so every mismatch in a rollout is censused before the first error is
  re-raised unchanged, caps retention at
  `WRAPPER_MISMATCH_RETENTION_LIMIT` while recording the full count so
  truncation is visible, and adds `_census_unparsed_arms` so an arm that
  aborts the build no longer leaves the other arm at `NOT_RUN`. The census
  pass writes no staging or chain state, admits nothing and swallows its own
  errors, so it cannot mask or replace the original failure. Admission is
  unchanged. The remaining gap, that a source-phase failure left the public
  phase `NOT_RUN` because the public rollout is only produced after the
  source parse succeeds, is addressed by `_census_incomplete_arms`: it
  censuses the public phase from bytes sanitized in memory with the build's
  own sanitizer. Nothing is written to disk, because a sanitizer's output is
  not the same thing as output proven publishable and a copy of private
  material should not be given a path it could outlive the call through.
  Those bytes are equivalent by construction to the staged artifact but are
  not it, so any arm censused this way is flagged with
  `public_phase_from_diagnostic_copy` and must not be read as the public
  rollout admission would have seen.

  This is not an unconditional guarantee that all four arm-by-phase cells are
  filled, and must not be described as one. The helper can only fill a cell
  when the prompt, the plan, the source rollout and the sanitizer are all
  usable; when its own setup, sanitization or parse fails, the cell stays
  `NOT_RUN`. What is guaranteed is that such a cell is no longer silent: each
  phase carries a `census_status` from the fixed vocabulary
  `CENSUS_STATUSES`, so a reader can tell a phase nobody reached from one
  where the diagnostic pass itself broke. No exception text and no path is
  retained. Failure receipt schema is now
  `gate3-codex-live-canary-failure-receipt.v7`.

- [x] **The frozen route's wrapper acceptance is byte-exact, and that is the
  root cause of the v4/v5 packet-build failures.** The offline probe
  `gate3_wrapper_acceptance_probe.py` classified 14 plausible tool-input
  shapes at zero authorization cost; the report is retained at
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-offline/wrapper-acceptance-probe-20260801.json`.
  Only the two shapes the route pins are accepted. All 12 others are
  rejected, including five that change nothing semantically: key order,
  spacing after a colon, quoted object keys, the result variable name and a
  trailing semicolon. Every field name in `SAFE_TOOL_INPUT_FIELD_NAMES`
  other than `command` and `workdir` is also rejected, which confirms that
  allowlist is a census vocabulary and not an accept list. Because
  `SHELL_WRAPPER_RE` admits one byte sequence, ordinary run-to-run
  formatting variance in model output is sufficient to fail `packet_build`,
  which is consistent with the failing arm moving from A in v4 to B in v5
  under the same frozen route. This is a characterization of the acceptance
  set; it is not evidence that the CLI emits any particular rejected shape.

- [x] **A real-emission corpus scan separates cosmetic wrapper variance from
  privilege-affecting variance, and shows the pinned-build evidence is
  circular.** `gate3_wrapper_corpus_scan.py` classifies `exec` tool inputs in
  an existing local rollout corpus against the frozen route, at zero
  authorization cost and without invoking a session. Across several thousand
  emissions spanning several CLI builds, a small minority were accepted and
  the rejections resolved into a few dozen distinct structural signatures.
  Most rejected emissions were cosmetic, dominated by an execution-bound
  field and by envelope and argument-shape differences that change nothing
  about what the call does; a substantial minority were privilege-affecting,
  carrying approval-policy, sandbox-permission or shell-semantics fields, so
  a parse-and-compare that accepted wrappers by decoded command alone would
  hand those boundaries away. Separately, every field name in every rejected
  emission was already in `SAFE_TOOL_INPUT_FIELD_NAMES`, which independently
  confirms the census vocabulary is complete.

  These figures are stated qualitatively on purpose. An earlier revision of
  this entry, and the commits that introduced it, recorded exact session,
  emission, build and rejection counts derived from a private corpus. Precise
  counts of that kind are a usage profile, so the wording was narrowed here
  rather than in history: the earlier revision remains reachable in this
  branch's git history and was deliberately not rewritten. Exact figures
  remain reproducible locally by whoever holds the corpus, using the
  committed scanner.

  Limitations, and they are the load-bearing part: every emission observed on
  the pinned CLI build came from the 2026-07-29 common-harness rehearsal, the
  same runs the wrapper was written against, so that build has zero
  independent evidence in this corpus and its acceptance rate must not be
  read as confirmation. The v3 to v5 emissions are unavailable because the
  canary wipes its private runtime. The corpus is private material: it is a
  usage profile even after redaction, so no report is retained in this
  repository, no corpus location or digest is recorded, and the scan output
  is git-ignored. The scanner defaults to folding thinly-attested signatures
  into a count-only bucket and offers an aggregate-only mode, which is the
  only shape that should ever be considered for publication, and then only
  after human review. Anyone re-running the scan on their own corpus
  reproduces the method; the numbers above are this corpus only.

- [x] **The unclassified emission group was three different failures wearing
  one label, and the diagnostic now separates them.** The group that
  classified as `other` tool family with an unparsed argument turned out to
  contain multi-call inputs, inputs calling a tool the frozen route does not
  carry at all, and inputs containing no tool call. Those are not
  interchangeable: a route-scope violation is a different finding from
  ordinary wrapper variance, and a receipt that labels them identically
  cannot be read. `_tool_input_wrapper_diagnostic` now reports a
  `rejection_class` drawn from `WRAPPER_REJECTION_CLASSES`, plus the total
  `tools.*` token count and how many name a frozen-route family. Tool names
  outside the route are counted but never named, because a corpus can carry
  private MCP tool names and the class is what a reader needs. Re-running the
  corpus scan resolves the whole rejected population into the four classes,
  with single-frozen-call dominant and the remainder split across
  multiple-call, out-of-route-tool and no-tool-call. The out-of-route group
  is the material one: those were previously indistinguishable from
  formatting variance. Failure receipt
  schema is now `gate3-codex-live-canary-failure-receipt.v5`. Acceptance is
  still unchanged; this is diagnosis only.

- [x] **Wrapper acceptance policy decided 2026-08-01: cosmetic equivalence is
  admitted, the execution bound is not.** The semantic-equivalence contract is
  wired into acceptance and independently reviewed. It admits whitespace, key
  order, quoted keys, the result variable's name, a trailing semicolon, direct
  text-await and an inline patch argument, and refuses extra fields,
  privilege-affecting fields, multiple calls, out-of-route tools, unvalidated
  envelopes, duplicate fields and any value the route already rejects. The
  acceptance policy, including content digests of the contract and the route
  validators, is bound into the route receipt, the source attestation and the
  context identity; the A/B check and route verification both require a
  matching digest. Route receipt is `v4`, failure receipt is `v8`, and a
  refusal carries the contract reason into the published receipt.

  `TOLERATED_FIELDS` stays empty. The case for admitting the execution bound
  rested on a corpus statistic drawn from ordinary interactive sessions on
  other CLI builds with a different tool surface, which is not the population
  the frozen route produces. The non-circular evidence under frozen-route
  conditions points the other way: in live canary v5, arm A cleared both parse
  phases while acceptance was still byte-exact, meaning an entire session of
  calls matched the frozen shape with no execution bound present. Tolerating
  the field would be a widening with no demonstrated need. The machinery for
  doing so is retained and tested, so the decision is cheap to revisit if a
  frozen-route run ever shows the field emitted; it should not be revisited on
  the strength of the corpus statistic alone.

- [x] **Superseded by the decision above: decide the wrapper acceptance
  policy before requesting another pair.** Retained for the reasoning that
  led there; the conclusion it reaches is no longer the current position.
  The probe establishes that byte-exact acceptance cannot survive normal
  emission variance, so further live pairs will keep failing at
  `packet_build` for reasons that carry no scientific content. Two options,
  owner decision: pin the emission shape from the prompt side so variance
  never arises, or replace `SHELL_WRAPPER_RE` with a parse-and-compare that
  accepts any wrapper whose decoded command, workdir and tool family match
  the frozen route. The second widens what the route admits and is a
  governance-surface change, so it needs review before implementation, not
  after. The corpus scan constrains this decision: any parse-and-compare must
  reject the privilege-affecting field set outright rather than compare on
  the decoded command alone, and pinning from the prompt side reduces
  variance without proving the model will comply. Owner decision on
  2026-08-01 was to change neither surface yet and continue offline.

- [x] **Gate 3 preregistration amendment v1 independently approved and owner
  signed 2026-08-02 at exact manifest SHA-256
  `d64817c2ceb190f43764b0d08c098deb821ca4755e273e045dec34812cc97d00`
  (commit `32e109d8`).** Independent semantic review returned APPROVED after
  the final two findings, typed observation evidence and exact diff-byte
  binding, were closed and their regressions were shown to detect the absence
  of the checks they name. The owner approved that exact digest.

  The signature is append-only. No signed byte was edited, following the
  amendment v4 precedent: the amendment is `files[1]` of the signed manifest,
  so editing its status line would invalidate the signature it carries. For
  the same reason the manifest's own `authorization` field still reads
  `pending_independent_review_and_owner_signature` — editing it would change
  the very digest that was signed. This PLAN line is the authority record and
  supersedes that field; a reader who consults only the manifest will see the
  pre-signature wording, which is a known and deliberate cost of append-only
  signing.

  Canonical promotion is recorded here rather than by rewriting a pointer,
  because Gate 3 has no separate preflight manifest of the kind the Gate 2
  promotion updated. Nothing was recomputed. `verify-candidate` was re-run
  after promotion and the signed bytes verified UNCHANGED at 7/7 PASS.

  This does not authorize the final canary, natural-bug or resource
  admission, Gate 3 start, or any counted execution. Counted Gate 3 execution
  remains at zero.

- [x] **Final authorized non-counted canary v6 executed 2026-08-02 and failed
  at `packet_build`. Gate 3 is PAUSED. Counted execution remains 0.** Run
  `gate3-codex-auth-v6-20260802-130957`, authorized as exactly two sessions
  with no replacement under `non_counted_codex_live_canary_only`. The
  authorization is consumed and no replacement was run.

  Execution succeeded and admission did not. Credential preflight PASS, both
  arm logins PASS, runner receipt VALID, exactly two session invocations, exit
  code 0 on both arms, cleanup PASS with zero residue classes, no success
  packet attempted, present or admitted, `scoreable` false. The privacy-safe
  negative receipt is retained unmodified at SHA-256
  `12edf19a0165f0e5de76f3eeea397a0a5d91193b02b520b6a9aa582111174765`.

  What the evidence does and does not support, stated carefully because the
  first summary of this run overstated it:

  - The wrapper was **not** tested. `wrapper_mismatch_counts` is zero for both
    arms in both phases, and that means the parser never reached the wrapper
    scan, not that the wrappers matched. Session context identity is validated
    at `gate3_codex_live_canary.py:1846` and the wrapper scan begins at
    `:1970`, so the run stopped before admission of tool inputs was ever
    attempted. No claim about wrapper conformance may be drawn from this run.
  - The root cause is operator-observed, not independently reproducible from
    the retained public evidence. The runtime error named `originator` as the
    frozen context field that differed. The receipt records only
    `failure_stage=packet_build`; it carries no fixed-vocabulary mismatch
    field, and the private rollouts were wiped by cleanup. The cause is
    therefore consistent with the code's fail-closed branch but cannot be
    re-derived from the public artifact.
  - Arm A's diagnostics are internally inconsistent: `source_census` is
    populated and `parse_phases.source` is `FAIL` while
    `census_status.source` reads `not_attempted`. The census is written before
    the context check raises, but `census_status` is only set by the
    diagnostic completion pass, which skips a phase that is no longer
    `NOT_RUN`. The four-cell diagnostic state cannot be described as
    internally consistent. Left unfixed in this slice deliberately.

  Stop-line disposition: the handoff carries two limits, at most one further
  non-counted pair and no replacement session. The wrapper clause was an
  additional trigger, not a condition that grants further attempts when a
  failure is non-wrapper. The single authorized pair has been used, so no
  further live pair is authorized and none may be requested without the owner
  explicitly revising the stop line.

  Not done in this slice and not to be inferred: no census fix, no relaxation
  of the frozen `originator` expectation, no re-authorization. Whether
  `originator` belongs in the frozen identity at all is an offline decision;
  changing it would alter the signed contract and require fresh review,
  signature and promotion rather than reuse of the 2026-08-02 approval.

### Gate 3 Live Canary Readiness As Of 2026-08-01

Stated deliberately narrowly. An earlier revision of this section described
the remaining work as a final stretch before counted execution; that was too
optimistic and is corrected here.

Gate 3 is PAUSED as of 2026-08-02. The single authorized non-counted canary
was executed and failed at `packet_build`; the authorization is consumed and
counted execution remains at zero. Resuming requires an owner decision to
revise the stop line, not merely another fix.

- Codex launcher, credential seeding, authentication and session execution:
  passing. v4 and v5 each invoked exactly two sessions with exit code 0 on
  both arms and cleaned up with zero residue.
- Producer-output admission: not passing. No run has produced a scoreable
  packet, so the producer workflow must not be described as having succeeded
  end to end.
- Failure receipt: attempts every arm against every parse phase and records a
  fixed-vocabulary reason when it cannot complete one, with public-phase
  observations taken from a diagnostic copy flagged as such. It is not an
  unconditional guarantee that all four cells are filled, and it still
  describes only why a build failed; it is not evidence about producer
  output.
- Offline corpus characterization: complete as a method. As acceptance-policy
  evidence it is limited and cannot decide a contract on its own: the pinned
  build's emissions in the corpus came from the same rehearsal the wrapper
  was written against, and the v3 to v5 failing rollouts were wiped by
  cleanup and cannot be replayed.
- Wrapper acceptance policy: decided 2026-08-01, wired, and independently
  reviewed. The execution bound is not tolerated. The earlier description of
  this as an unwired proposal awaiting corrected review is superseded; it
  described the state before `8fba4cba` and `880ce166`.
- Acceptance policy digest: `e9567eedc20365978998be27ccc4dd8ad80a289143154f4984dc6dad0ffbaa9e`, over contract
  `b000d3bc34f21a958d3d7b14f5c00c82e7ef94fb68b3d3f2ffca051f15b49c13`
  and route validators
  `c959bc4ef91af2d08ed7b1c0ae7d3c149c441386825366199a874f9deb6dec3b`.
  This supersedes `35a45dc4…d76c266c`, which was recorded as frozen before the
  preregistration semantic review. That review required the scorer packet to
  carry an exact field set, and the canary's own packet builder emitted a
  field outside it, so the canary had to change and the digest moved with it.
  The move was a consequence of a required fix, not a drift; it is noted here
  rather than quietly re-pinned. Any further edit to either file, including a
  comment, moves it again.
- Acceptance policy evidence identity: changed. Admission semantics did not
  change when the execution-bound decision was recorded, but the policy digest
  did, because it deliberately pins the contract's own bytes and the docstring
  was edited. The consequence is narrow and must be stated narrowly. Codex
  live-route receipts carrying an earlier `acceptance_policy_sha256`, and
  evidence whose verification depends on that field, are refused by the
  current route verifier. That is the intended fail-closed behaviour, and it
  makes exactly that material historical evidence: it attests to what happened
  under the policy of its day and cannot be re-verified under this one.

  It does not reach further. The common-harness rehearsal and the
  preregistration candidate bytes are verified by tooling that does not
  consult the acceptance policy digest, and both still verify under the
  current tools: `gate3_common_harness.py verify` returns `status=PASS` with
  all seven checks passing, including `candidate_exact_bytes`, and the
  candidate manifest is still
  `d64817c2ceb190f43764b0d08c098deb821ca4755e273e045dec34812cc97d00`,
  which supersedes `51ac1219…a5a6801` and `38e2bf33…0ccedfb6`. An
  earlier revision of this entry described all prior rehearsal and canary
  evidence as historical, which was wrong and is corrected here.
- Stop line, agreed 2026-08-01: at most one further non-counted live pair. If
  it fails on another wrapper detail, Gate 3 pauses and the experiment channel
  is re-evaluated. No additional census tooling, no replacement session.
- Preregistration: candidate only. Independent approval, owner exact-byte
  signature and canonical promotion are all outstanding.
- Natural-bug and resource admission, and separate Gate 3 start authority:
  outstanding. These gate counted execution, not the final non-counted canary.

Order of work from here, and no step may be skipped. Publication hardening,
the acceptance policy proposal, the owner decision, the acceptance
implementation and its independent review are all complete. What remains:

1. Independent review of the preregistration candidate bytes.
2. Owner exact-byte signature.
3. Canonical promotion.
4. A separate exact-two, no-replacement authorization for the final
   non-counted Codex route canary, which runs under
   `non_counted_codex_live_canary_only` and does not require Gate 3 to have
   been started.
5. Natural-bug and resource admission, after that canary.
6. Separate Gate 3 start authority.
7. Counted execution.

Steps 4 and 6 are different authorizations and must not be conflated: the
final canary proves the route, and Gate 3 start authority opens the counted
experiment. An earlier statement in this branch ordered the canary after Gate
3 start authority; that was wrong and is corrected here.

Cannot claim from this section: that only minor fixes remain, that the
producer workflow has succeeded, that offline corpus evidence is sufficient
to decide acceptance, that the current policy digest is final, or that a
successful canary would by itself open Gate 3.

- [x] **The red credential-boundary test was a test-environment assumption,
  not a runtime guard defect.**
  `test_pair_runner_rejects_non_temp_private_runtime_before_login` had been
  failing since at least `2fe5ad61`. The fixture fed pytest's `tmp_path` as
  the supposedly-outside-Temp path, but on a default Windows setup pytest's
  basetemp lives under `%TEMP%`, so the input was inside the very root
  `Assert-UserTempPath` checks. The guard correctly did not fire, execution
  continued into the credential preflight, and the assertion that no session
  binary had been invoked failed. The runner itself is correct: its temp-root
  guard covers all fifteen private-runtime path arguments and runs before the
  credential seed, the login preflight and the launcher. The fixture now
  builds a path anchored outside the temp root and self-checks that
  assumption, and the test asserts the guard by name rather than accepting
  any non-zero exit, so a later failure that ran the preflight first can no
  longer satisfy it. The full Gate 3 runtime suite is green at 225/225.

- [x] **Resolved: read across v4 and v5 before requesting another pair.**
  Closed by the offline characterization, the semantic wiring and the stop
  line. The reading below stands as the reasoning of its day, with one
  correction: the inference that the acceptable-wrapper set is under-specified
  relative to what the model emits drew on corpus-wide statistics from a
  different tool surface. Under frozen-route conditions, v5 arm A cleared both
  parse phases under byte-exact acceptance. The failing
  arm moved between runs (v4 failed on arm A, v5 failed on arm B) under the
  same frozen route, so the rejected wrapper shape varies run to run rather
  than being a fixed per-arm defect. Treat the acceptable-wrapper set as
  under-specified relative to what the model actually emits, and resolve that
  offline against synthetic rollouts rather than by spending further
  authorized pairs. Raw rollouts are wiped by cleanup
  (`residue_classes=[]`, `raw_output_retained=false`), so no run to date can
  be replayed offline and every live pair yields only the first mismatch
  encountered.

### Cannot Claim From The v3 To v5 Canary Entries

- Cannot claim which implementation commit each of v3, v4 and v5 executed
  against; the failure receipts do not record an implementation commit, and
  the mapping above is stated only from receipt contents.
- Cannot claim independent review of the v3, v4 and v5 receipts; unlike the
  v2 receipt, these three are recorded here without a review approval.
- Cannot claim the authorization disposition for v3. The receipt shows
  `session_invocations=0` and `replacement_sessions=0`, so no session was
  spent, but whether the authorization is treated as consumed is an owner
  decision and is not decided here.

## Canonical Memory Provenance Tranche 1 (completed 2026-07-27)

- [x] Canonical memory CLI writer, runtime session-end writer, authority guard,
  and checkpoint baseline reader share one local Git commit-object provenance
  decision.
- [x] Hash-shaped text alone no longer creates `memory_binding: bound`;
  explicit invalid Git-worktree commits fail before memory mutation, while
  auto-detect failure and non-Git paths remain writable as unbound.
- [x] `mixed_scope_memory_binding` reports staged or commit-range closeout
  scopes that combine bound canonical memory with non-closeout paths. The
  signal remains report-only and is absent from hook, CI blocker, pre-push, and
  memory blocking policy.
- [x] Focused replay covers the CFU release-artifact mixed-scope must-fail case
  and the product-commit then memory-closeout-commit must-pass case.
- [x] Read-only scoped review findings were resolved before commit.
- [x] Separate Memory quality measurement slice: retrospectively classified the
  most recent 20 canonical entries, then causally reclassified the 15
  non-immediate cases under four real work items.
- [x] The causal audit found zero confirmed avoidable memory defects. Three
  apparent stale-at-write cases were `record_commit_artifact` false positives:
  `git blame` identifies when a prewritten record was committed, not when it was
  authored.
- [x] The admission gate was not met. Stop without adding an advisory prompt,
  fresh-session replay harness, `governance_tools` validator, hook, CI, schema,
  or blocker.

Claim ceiling: Tranche 1 establishes local commit provenance consistency and a
report-only mixed-scope observation. It does not prove remote delivery, memory
prose truth, Memory quality improvement, consumer replay outcomes, or G4 value.

Memory quality measurement claim ceiling: the recent-20 baseline and causal
audit are single-annotator, retrospective observations. Reviewer agreement
remains pending; the sample is concentrated in four work items and is not G4
outcome evidence.

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

- `PLAN.md`, `memory/01_active_task.md`, and `.governance/baseline.yaml`
  are point-in-time aligned to pre-refresh HEAD `8a98df2e`.
- `PLAN.md` and `memory/01_active_task.md` record the completed opt-in
  plain-summary v0.5 slice and the owner-decided P1-F advisory disposition.
- `governance_drift_checker` returns `severity=ok` after the governed
  baseline refresh.
- Runtime, hook, CI, gate, and enforcement behavior remain unchanged.
- Scoped diff and memory-workflow checks pass for the changed surfaces.
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

## Gate 3 Codex Route Admission Canonical Promotion — 2026-08-04

- [x] The formal Codex route admission implementation, mutation evidence and
  governing amendment were independently reviewed and returned `APPROVED`.
- [x] Exact candidate manifest prepared at commit `67fdc61b`:
  `artifacts/experiments/prepush-bugfix-20260724/candidate/gate3-codex-route-admission-v1-candidate-manifest.json`.
- [x] The manifest covers nine byte-preserved files and is 2,633 bytes with
  SHA-256
  `d8f441aea3a611f291e2714b7b0b3614dd5970dfb00320075c44f7097625c14a`.
- [x] On 2026-08-04 the owner explicitly signed that exact manifest digest and
  authorized canonical promotion.
- [x] Canonical promotion is effective for the exact bytes named by that
  manifest. The signature is append-only: the manifest's pending authorization
  wording remains unchanged because editing it would invalidate the signed
  digest. This PLAN entry is the authority record.
- [x] Post-sign verification confirmed all nine file byte counts and SHA-256
  values, `-text` byte preservation for every member and the manifest, and the
  reviewed implementation source commit
  `65f321611cb63c9b7f344c513ec8dcdc39cd8742` as a reachable ancestor.

Promotion scope and next gates:

- This promotion authorizes the formal admission policy identity only. It does
  not authorize a calibration session, non-counted live pair, natural-bug or
  resource admission, Gate 3 start, or counted execution.
- The previously consumed final-canary authorization remains consumed. The
  2026-08-01 stop line was superseded by the append-only owner ruling below;
  that ruling permits a future authorization request but does not itself grant
  session authority.
- Natural-bug/resource admission and separate Gate 3 start authority remain
  mandatory before any counted A/B/C/D execution. Counted Gate 3 execution
  remains zero.

Cannot claim from this promotion: a successful live scorer packet, restored
live-pair authority, natural-bug/resource admission, Gate 3 start authority,
or any measured Skill effect.

### Gate 3 non-counted canary stop-line revision — 2026-08-04

- [x] The owner superseded the consumed 2026-08-01 stop line for one narrow
  purpose: a future request may seek authorization for exactly one additional
  non-counted A/B canary pair.
- [x] Any such request must specify exactly two new sessions, no replacement,
  a clean detached execution worktree, a fixed run ID and the canonically
  promoted implementation identity.
- [x] This ruling is not execution authorization. No session may start until
  the owner separately grants an exact-session authorization for that pair.
- [x] Whether the pair succeeds or fails, the revised stop line is consumed
  after that one authorized attempt. No replacement or further pair follows
  automatically.
- [x] This ruling changes neither formal admission semantics nor the signed
  manifest. Historical handoff text remains unchanged as evidence of the
  authority that applied at its own time.

Still required independently: natural-bug/resource admission and Gate 3 start
authority. Counted A/B/C/D execution remains zero.

Cannot claim from this ruling: current live-session authority, a scheduled or
running canary, a successful scorer packet, natural-bug/resource admission,
Gate 3 start authority or any counted result.

## Gate 3 Route Admission Promotion Correction — 2026-08-04

- [x] Zero-session preflight from clean detached commit `f8ce1f17` rejected the
  promoted manifest before CLI installation, credential handling or session
  invocation. Eight of nine entries reproduced; the committed
  `gate3_wrapper_semantic_contract.py` blob is 20,114 bytes with SHA-256
  `b000d3bc34f21a958d3d7b14f5c00c82e7ef94fb68b3d3f2ffca051f15b49c13`,
  while the signed manifest recorded a 20,594-byte CRLF working-copy value.
- [x] The prior owner signature and canonical promotion for manifest SHA-256
  `d8f441aea3a611f291e2714b7b0b3614dd5970dfb00320075c44f7097625c14a`
  are invalid for clean-checkout execution. This correction is append-only and
  does not rewrite the historical signature or promotion record above.
- [x] The candidate manifest was rebuilt from the committed blobs at
  `f8ce1f17954ec61da73369562626714d7e429258`; all nine member byte counts and
  SHA-256 values reproduce from Git blobs. The rebuilt 2,633-byte candidate
  manifest has SHA-256
  `1034a53ca1f8416ab45f1ea07c85efd82efd17df38047736d79b19b8fb055071`;
  a detached `core.autocrlf=true` checkout reproduced all nine entries with a
  clean status. Independent approval remains required.

Current authority boundary:

- The rebuilt manifest is an unsigned candidate pending independent review and
  a new exact-byte owner signature. It is not canonically promoted.
- The failed preflight invoked zero sessions. No CLI, credential copy, private
  rollout, staging tree or synthetic repository survived cleanup.
- No prior live authorization may be reused for the rebuilt manifest. A future
  canary requires a new owner signature, canonical promotion and a separately
  granted exactly-two/no-replacement session authorization.
- Natural-bug/resource admission and independent Gate 3 start authority remain
  mandatory before counted execution. Counted A/B/C/D execution remains zero.

Cannot claim from this correction: independent approval of the rebuilt
manifest, a new owner signature, canonical promotion, live-session authority,
a successful scorer packet, natural-bug/resource admission, Gate 3 start
authority or any counted result.

## Gate 3 Route Admission Owner Signature — 2026-08-04

- [x] Independent review returned `APPROVED` for the clean-checkout-derived
  candidate manifest committed in checkpoint `654b148d`.
- [x] The owner signed the exact 2,633-byte manifest at SHA-256
  `1034a53ca1f8416ab45f1ea07c85efd82efd17df38047736d79b19b8fb055071`.
- [x] Post-sign verification matched the committed manifest identity and all
  nine member byte counts and SHA-256 values against their pinned Git blobs.
- [ ] Canonical promotion remains separately authorized and has not occurred.

This signature authorizes no session, live pair, natural-bug/resource
admission, Gate 3 start or counted execution. A future promotion must cite this
exact digest, and any manifest-byte change requires a new review and signature.

Cannot claim from this signature: canonical promotion, live-session authority,
a successful scorer packet, natural-bug/resource admission, Gate 3 start
authority or any counted result.

## Gate 3 Route Admission Canonical Promotion — Corrected Identity — 2026-08-04

- [x] The owner separately authorized canonical promotion of exact manifest
  SHA-256
  `1034a53ca1f8416ab45f1ea07c85efd82efd17df38047736d79b19b8fb055071`.
- [x] The promoted manifest is the 2,633-byte candidate committed at checkpoint
  `654b148d`; post-sign verification matched all nine member identities against
  the Git blobs pinned by source commit
  `f8ce1f17954ec61da73369562626714d7e429258`.
- [x] This corrected promotion supersedes only the invalid clean-checkout
  identity `d8f441ae...c14a`. Historical signature, failure and correction
  records remain append-only and are not rewritten.

Promotion scope and remaining gates:

- This promotion establishes the formal Gate 3 Codex route-admission policy
  identity. It does not authorize a session or canary pair.
- Any future non-counted pair still requires a new, explicit exactly-two,
  no-replacement execution authorization with a fixed run ID and clean detached
  worktree.
- Natural-bug/resource admission and independent Gate 3 start authority remain
  mandatory before counted A/B/C/D execution. Counted execution remains zero.

Cannot claim from this promotion: live-session authority, a successful scorer
packet, natural-bug/resource admission, Gate 3 start authority or any counted
result.

## Gate 3 Preregistration Identity Repin — 2026-08-04

- [x] The authorized zero-session preflight for fixed run ID
  `gate3-codex-auth-v8-20260804-160000` stopped during `prepare`, before CLI
  installation, login, credential copying or session invocation. The promoted
  preregistration manifest reproduced five of six members; its `.gitattributes`
  identity described historical bytes rather than the current committed bytes.
- [x] The current committed `.gitattributes` is 7,337 bytes with SHA-256
  `abe5c1648ee22adce810bea5d2c5ac9a2a7e67b9c3cd9b7d7a49c24f5fcbe91b`.
  The preregistration candidate manifest has been repinned to that identity and
  to source commit `3c2f194f38464bdccdb75384fe000bc9e5e3c49a`.
- [x] The resulting 1,843-byte preregistration candidate manifest has SHA-256
  `cbbcea0f614c3e34b03c2a102a71393de71b05da5fdae25884b98aff579e095b`.
  It supersedes promoted preregistration identity
  `d64817c2...` but is currently unsigned and unpromoted.
- [x] The live-canary expected preregistration digest and its regression test
  now point to the repinned candidate. Because those implementation bytes
  changed, the route-admission candidate manifest was rebuilt as a coordinated
  identity update.
- [x] The resulting 2,672-byte route-admission candidate manifest has SHA-256
  `71ec318b86bb56b2d683226a3ba46938e5e8186c8dd57aeb1ff027366a42ca70`.
  It supersedes promoted route-admission identity
  `1034a53c...5071` but is currently unsigned and unpromoted.
- [x] Independent review rejected an earlier repin draft because its
  `reviewed_implementation_commit` named the prior promotion commit rather than
  a commit containing the proposed implementation bytes. Because this slice
  is not authorized to commit, the corrected candidate removes that false
  anchor and explicitly records
  `pending_independent_review_of_proposed_bytes` instead.
- [x] A clean proposed-commit checkout reproduced preregistration verification
  6/6, route-admission verification 9/9 and live-canary `prepare` without
  installing a CLI or invoking a session.

Authority boundary:

- The stopped v8 attempt invoked zero sessions. Its exactly-two authorization
  does not automatically transfer to changed preregistration or
  route-admission identities.
- Both replacement manifests require independent review, exact-byte owner
  signatures and separate canonical promotions before any future live
  execution request may be considered.
- Natural-bug/resource admission and independent Gate 3 start authority remain
  mandatory before counted A/B/C/D execution. Counted execution remains zero.

Cannot claim from this repin: independent approval, owner signature, canonical
promotion, live-session authority, a successful scorer packet,
natural-bug/resource admission, Gate 3 start authority or any counted result.

## Gate 3 Dual Manifest Owner Signature and Canonical Promotion — 2026-08-04

- [x] Independent review returned `APPROVED` for the five-file repin committed
  at checkpoint `911ea562db6b799ae41eeec55a8f69e54a3e33b5`.
- [x] The owner signed exact preregistration manifest SHA-256
  `cbbcea0f614c3e34b03c2a102a71393de71b05da5fdae25884b98aff579e095b`
  and exact route-admission manifest SHA-256
  `71ec318b86bb56b2d683226a3ba46938e5e8186c8dd57aeb1ff027366a42ca70`.
- [x] The owner separately authorized canonical promotion of those same two
  exact identities. No manifest byte was rewritten to record its own approval.
- [x] Canonical verification at checkpoint `911ea562` matched both signed
  manifest digests and every pinned member: preregistration 6/6 and
  route-admission 9/9. Evidence is bound to
  `artifacts/evidence/test-results/receipt-gate3-dual-manifest-promotion-20260804.json`.
- [x] These promoted identities supersede preregistration promotion
  `d64817c2...` and route-admission promotion `1034a53c...5071` for future
  execution. Historical authority and failure records remain append-only.

Promotion scope and remaining authority:

- This promotion establishes the current preregistration and formal Codex
  route-admission identities. It does not authorize a session or canary pair.
- A future non-counted pair requires a new explicit exactly-two,
  no-replacement authorization naming a fixed run ID and these promoted
  identities. The earlier v8 authorization was consumed by a zero-session
  preflight attempt and does not transfer.
- Natural-bug/resource admission and independent Gate 3 start authority remain
  mandatory before counted A/B/C/D execution. Counted execution remains zero.

Cannot claim from this promotion: live-session authority, a successful scorer
packet, natural-bug/resource admission, Gate 3 start authority or any counted
result.
