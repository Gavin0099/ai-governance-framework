# Review Log

## 2026-03-13 - Governance Progress Snapshot

- Reviewed current repository position after startup, proposal, and change-control features were added.
- Confirmed the repo has moved beyond document-only governance into evidence-aware runtime governance with proposal-time guidance.
- Recorded the key remaining gaps as:
  - semantic verification depth
  - workflow interception coverage
  - reviewer consumption of change-control outputs

## 2026-03-13 - Smoke Regression Fix

- Fixed a CI/runtime smoke regression where `runtime_hooks/smoke_test.py` assumed every human-rendered envelope exposed top-level `event_type`.
- Shared session-start envelopes expose top-level `event_type`, but adapter-driven envelopes rely on `normalized_event.event_type`.
- The formatter now supports both shapes, and regression coverage was added in `tests/test_runtime_smoke_test.py`.

## 2026-03-14 - Local Baseline Validation Blocked

- Started the first prerequisite task for the USB-Hub integration plan: local execution baseline validation.
- Confirmed that this workstation currently has no `python`, `py`, `python3`, or `uv` command available in `PATH`.
- As a result, `pre_task_check.py`, `session_start.py`, and `pytest` could not be executed locally, so runtime maturity remains unverified on this machine.
- Immediate next action is to restore or expose a Python runtime before continuing Phase 1 validation.

## 2026-03-14 - Python Entrypoint Hardening

- Added shared interpreter resolution in `scripts/lib/python.sh`.
- Updated `scripts/run-runtime-governance.sh` and `scripts/verify_phase_gates.sh` to honor `AI_GOVERNANCE_PYTHON` before falling back to `python`, `python3`, or `py -3`.
- Updated installed git hooks to resolve the repository root before sourcing shared shell helpers, avoiding broken relative paths under `.git/hooks`.
- Documented the new override path in `README.md` and `governance_tools/README.md`.

## 2026-03-14 - Local Baseline Restored

- Located the workstation's usable interpreter at `C:\Users\daish\AppData\Local\Python\pythoncore-3.14-64\python.exe` by tracing `D:\Bookstore-Scraper\.venv\pyvenv.cfg`.
- Confirmed the interpreter is Python `3.14.2`.
- Verified `governance_tools/plan_freshness.py --format json` returns `FRESH`.
- Verified `runtime_hooks/core/pre_task_check.py --rules common,python --risk medium --oversight review-required --format human` runs successfully and emits advisory suggestions.
- Ran `scripts/verify_phase_gates.sh` with `AI_GOVERNANCE_PYTHON` set to the discovered interpreter; result: `259 passed`, `4/4 Gates` passed.
- Ran `scripts/run-runtime-governance.sh --mode smoke` with the same interpreter override; shared and adapter smoke flows completed successfully and produced change-control artifacts under `artifacts/runtime/smoke/`.

## 2026-03-14 - contract.yaml Discovery Seam Added

- Added `governance_tools/domain_contract_loader.py` as a stdlib-only loader for minimal external `contract.yaml` files.
- Extended `rule_pack_loader.py` so built-in and external rule roots can be merged during runtime governance.
- Added `--contract` support to `runtime_hooks/core/pre_task_check.py`, `session_start.py`, and `post_task_check.py`.
- `session_start` now carries discovered domain documents, rule roots, and validator metadata into startup context.
- `post_task_check` now validates external rule packs against discovered contract rule roots, instead of rejecting them as unknown.
- Added targeted tests for domain contract loading, external rule-root loading, session-start contract integration, and post-task contract validation.
- Verification:
  - `tests/test_domain_contract_loader.py tests/test_rule_pack_loader.py tests/test_runtime_session_start.py tests/test_runtime_post_task_check.py` -> `29 passed`
  - `tests/test_contract_validator.py tests/test_rule_pack_loader.py tests/test_runtime_pre_task_check.py tests/test_runtime_session_start.py tests/test_runtime_post_task_check.py tests/test_runtime_smoke_test.py` -> `87 passed`

## 2026-03-14 - USB-Hub Example Contract Validation

- Added `examples/usb-hub-contract/` as a minimal dual-repo style domain plugin sample.
- Added a runnable `governance_tools/domain_contract_loader.py --contract ...` CLI so contract discovery can be validated outside unit tests.
- Extended session-start human output to surface domain document names, behavior-override names, and first-line previews.
- Example contract now includes:
  - `contract.yaml`
  - `AGENTS.md`
  - `USB_HUB_FW_CHECKLIST.md`
  - `USB_HUB_ARCHITECTURE.md`
  - `rules/hub-firmware/safety.md`
  - `validators/interrupt_safety_validator.py`
- Validation completed:
  - `domain_contract_loader.py --contract examples/usb-hub-contract/contract.yaml --format human`
  - `session_start.py --contract examples/usb-hub-contract/contract.yaml --format human`
  - `pre_task_check.py --contract examples/usb-hub-contract/contract.yaml --format json`
- Added example-focused tests:
  - `tests/test_domain_contract_example.py`
  - targeted verification result: `17 passed`

## 2026-03-14 - Advisory Domain Validator Execution

- Added `governance_tools/validator_interface.py` with shared `DomainValidator` and `ValidatorResult` types.
- Added `governance_tools/domain_validator_loader.py` for isolated validator discovery, startup preflight, payload building, and advisory execution.
- `session_start.py` now reports validator preflight status so broken domain validators are visible before task execution begins.
- `post_task_check.py` now routes matching external validators and merges their findings as advisory warnings.
- Upgraded `examples/usb-hub-contract/validators/interrupt_safety_validator.py` from placeholder metadata to a real advisory validator that scans ISR code for forbidden calls.
- Verification:
  - `tests/test_domain_validator_loader.py tests/test_domain_contract_example.py tests/test_runtime_session_start.py tests/test_runtime_post_task_check.py` -> `23 passed`
  - `tests/test_contract_validator.py tests/test_domain_contract_loader.py tests/test_domain_validator_loader.py tests/test_domain_contract_example.py tests/test_rule_pack_loader.py tests/test_runtime_pre_task_check.py tests/test_runtime_session_start.py tests/test_runtime_post_task_check.py tests/test_runtime_smoke_test.py` -> `94 passed`

## 2026-03-14 - Firmware Evidence Routing and checks-file Flow

- Extended `governance_tools/domain_validator_loader.py` so firmware-focused payloads can infer `changed_functions`, `interrupt_functions`, and `isr_code` from explicit `checks` fields, raw `diff_text`, unified diff snippets, and changed C file contents referenced by `changed_files`.
- Upgraded the USB-Hub example validator to keep interrupt checks advisory-only and to stay quiet when no interrupt context is detected.
- Added `examples/usb-hub-contract/fixtures/` with a patch-shaped `interrupt_regression.checks.json`, a matching `post_task_response.txt`, and a representative `src/usb_hub.c`.
- Added an end-to-end example test that runs `runtime_hooks/core/post_task_check.py --checks-file ... --contract ... --format json` and confirms the advisory validator is triggered from file-based evidence input.
- Verification:
  - `tests/test_domain_contract_example.py tests/test_domain_validator_loader.py tests/test_runtime_post_task_check.py` -> `27 passed`
  - `tests/test_runtime_session_start.py tests/test_domain_contract_example.py tests/test_domain_validator_loader.py tests/test_runtime_post_task_check.py` -> `30 passed`

## 2026-03-14 - Contract Auto-Discovery Resolver

- Added `governance_tools/contract_resolver.py` so runtime hooks can resolve domain contracts without always requiring `--contract`.
- Resolution order is now:
  - explicit `--contract`
  - `AI_GOVERNANCE_CONTRACT`
  - bounded upward discovery from `project_root` or evidence file paths
- Discovery is intentionally constrained:
  - stop at `.git` boundary
  - stop after ascending 3 levels
  - warn instead of auto-selecting when multiple candidates are discovered
- `pre_task_check.py`, `session_start.py`, and `post_task_check.py` now surface `contract_source` / `contract_path` so runtime behavior is not silent.
- Verification:
  - `tests/test_contract_resolver.py tests/test_domain_contract_loader.py tests/test_runtime_pre_task_check.py tests/test_runtime_session_start.py tests/test_runtime_post_task_check.py` -> `40 passed`

## 2026-03-14 - Contract Metadata In Audit Chain

- `change_control_summary.py` now includes contract resolution details for reviewer-facing summaries.
- `change_control_index.py` now augments cross-session review order with contract context derived from `*_session_start.json`.
- `session_end.py` and `memory_curator.py` now preserve external contract metadata into session-end summaries, candidate artifacts, and curated artifacts.
- This closes the audit trail across:
  - `session_start`
  - change-control summary
  - change-control index
  - session-end summary
  - curated runtime artifact
- Verification:

## 2026-03-15 - Release Surface Overview

- Added `governance_tools/release_surface_overview.py` as a single reviewer-first entrypoint over release readiness, release package summary, and any available generated release manifests.
- The new overview can consume explicit bundle/publication manifests when provided, but also remains useful when generated release-package surfaces have not yet been published.
- `scripts/verify_phase_gates.sh` now exercises the new overview against the phase-gate release-package smoke bundle, so the higher-level release reviewer flow is part of the normal regression surface.
- Release docs and tool docs were updated so alpha evaluation and publish checklists now include the new overview command.
  - `tests/test_change_control_summary.py tests/test_runtime_session_start.py tests/test_runtime_smoke_test.py` -> `16 passed`
  - `tests/test_runtime_session_end.py tests/test_memory_curator.py tests/test_change_control_summary.py tests/test_change_control_index.py` -> `19 passed`

## 2026-03-14 - EDA Python Domain Fit Recorded

- Evaluated Python-heavy IC / EDA verification as a likely Way B fit.
- Key rationale recorded:
  - Python syntax is easy for AI, but DUT mappings, fixed-point constraints, protocol timing, and internal toolchain boundaries are not.
  - The likely failure mode is context hallucination, not parser failure.
- Captured the recommended adoption strategy as "narrow slice first":
  - Cocotb signal mapping
  - golden/reference-model translation boundaries
  - internal EDA toolchain scripting constraints
- This was recorded as a future domain-fit note, not yet promoted into an active new domain contract plan.

## 2026-03-14 - Cross-Repo Hook Path Stabilization

- Updated installed `pre-commit` and `pre-push` hooks so external target repos no longer assume governance scripts live inside the target repository.
- Hooks now resolve `FRAMEWORK_ROOT` in this order:
  - `AI_GOVERNANCE_FRAMEWORK_ROOT`
  - `.git/hooks/ai-governance-framework-root`
  - fallback to the target repo root
- `scripts/install-hooks.sh` now writes `.git/hooks/ai-governance-framework-root` for external installs, so the copied hooks can call back into the shared framework scripts and tools.
- Verified the external install path with:
  - `scripts/install-hooks.sh --target ../Kernel-Driver-Contract --dry-run`
- Re-ran the full phase gates after the hook changes:
  - `scripts/verify_phase_gates.sh` -> `310 passed`, `4/4 Gates`

## 2026-03-14 - Hook Install Validation Tooling

- Added `governance_tools/hook_install_validator.py` to inspect hook installation state for both self-hosted framework repos and external target repos.
- The validator checks:
  - copied `pre-commit` / `pre-push` hook presence
  - `.git/hooks/ai-governance-framework-root`
  - required framework-side scripts and tools referenced by the hooks
- Updated `scripts/install-hooks.sh` and the README docs to surface the validator as the post-install verification path.
- Verification:
  - `tests/test_hook_install_validator.py` -> `4 passed`
  - `scripts/verify_phase_gates.sh` -> `314 passed`, `4/4 Gates`

## 2026-03-15 - Trust Signal Publication Reader

- Extended `governance_tools/trust_signal_snapshot.py` so `PUBLICATION_MANIFEST.json` now carries publication-level status fields such as:
  - `ok`
  - `project_root`
  - `publication_root`
  - `bundle_published`
  - `status_pages_published`
- Added `governance_tools/trust_signal_publication_reader.py` as the stable reader over publication metadata.
- The reader now provides a reviewer-first `summary=...` human output and can be pointed either at an explicit manifest file or the default `artifacts/trust-signals/PUBLICATION_MANIFEST.json`.
- `scripts/verify_phase_gates.sh` now checks both snapshot publishing and the publication reader path, so trust-signal publishing has both a producer and consumer regression surface.
- Verification:
  - `tests/test_trust_signal_snapshot.py tests/test_trust_signal_publication_reader.py` -> `12 passed`

## 2026-03-15 - IC Verification Domain Bootstrap

- Started a third external domain repository: `IC-Verification-Contract`.
- Chose a narrow Phase-1 slice instead of a broad IC platform abstraction:
  - Cocotb-style signal mapping
  - machine-readable `facts/signal_map.json`
  - one advisory validator for unknown DUT signal access
- The bootstrap work exposed two framework assumptions that were no longer valid for this domain:
  - governance contracts did not allow `LANG = Python`
  - `ic-verification` surfaced as an `unknown` domain risk tier
- Updated framework metadata and validation logic so:
  - `contract_validator.py` now accepts `Python`
  - `domain_governance_metadata.py` now treats `ic-verification` as `medium`
- Framework-side validation completed for the new domain:
  - `domain_contract_loader.py` load successful
  - `session_start.py` validator preflight successful
  - `pre_task_check.py` rule activation successful
  - `post_task_check.py` advisory validator execution successful

## 2026-03-14 - Install-And-Verify Hook Flow

- Updated `scripts/install-hooks.sh` so real installs now auto-run `hook_install_validator.py` by default.
- Added `--no-verify` for cases where only copying hooks is desired.
- This lowers the friction between "hook installed" and "hook installation actually verified", especially for external contract repos.
- Verification:
  - `scripts/install-hooks.sh --target ../Kernel-Driver-Contract --dry-run`
  - `scripts/verify_phase_gates.sh` -> `314 passed`, `4/4 Gates`

## 2026-03-14 - External Repo Readiness Checker

- Added `governance_tools/external_repo_readiness.py` as a single onboarding/readiness report for external repos.
- The checker combines:
  - hook installation state
  - `PLAN.md` freshness
  - contract discovery and file completeness
- This gives one place to answer "is this external repo actually ready to participate in runtime governance?"
- Validation:
  - `tests/test_external_repo_readiness.py` -> `3 passed`
  - `governance_tools/external_repo_readiness.py --repo D:\Kernel-Driver-Contract --format human`
    - confirmed `Kernel-Driver-Contract` is contract/PLAN-ready but still hook-incomplete
  - `scripts/verify_phase_gates.sh` -> `317 passed`, `4/4 Gates`

## 2026-03-14 - External Repo Onboarding Entry Point

- Added `scripts/onboard-external-repo.sh` as a single shell entrypoint for:
  - governance hook installation
  - optional contract override
  - readiness assessment
- This reduces external repo setup from multiple loosely coupled commands into one onboarding flow.
- Validation:
  - `scripts/onboard-external-repo.sh --target ../Kernel-Driver-Contract --dry-run`
  - `scripts/verify_phase_gates.sh` -> `317 passed`, `4/4 Gates`

## 2026-03-15 - Governance Smoke In Onboarding

- Added `governance_tools/external_repo_smoke.py` to validate that an external repo can actually power a minimal governance chain, not just pass static readiness checks.
- The smoke now verifies:
  - contract resolution
  - external rule-root existence
  - inferred smoke rules
  - `pre_task_check`
  - `session_start`
- `scripts/onboard-external-repo.sh` now runs this governance smoke by default unless `--no-smoke` is used.
- This closes the specific gap where a bad `contract.yaml` could look "installed" but still fail to energize the actual governance path.
- Verification:
  - `tests/test_external_repo_smoke.py` -> `3 passed`
  - `governance_tools/external_repo_smoke.py --repo D:\Kernel-Driver-Contract --format human`
  - `scripts/verify_phase_gates.sh` -> `320 passed`, `4/4 Gates`

## 2026-03-15 - External Onboarding Smoke Now Replays Compliant Post-Task Fixtures

- Extended `governance_tools/external_repo_smoke.py` so it no longer stops at startup-only checks when a repo already exposes:
  - `fixtures/post_task_response.txt`
  - compliant `fixtures/*.checks.json` baselines
- The smoke now replays compliant post-task fixtures through `post_task_check`, records `post_task_ok`, and captures per-fixture `domain_validator_count`.
- The selection logic is intentionally smoke-oriented:
  - it tries compliant/known/clean/safe baselines
  - it succeeds when at least one compliant baseline passes
  - it does not fail onboarding just because some other compliant-looking fixtures are incomplete for the full framework evidence model
- This makes external onboarding closer to a true domain-validator chain check instead of only a `session_start` / `pre_task_check` liveness probe.
- Verification:
  - `tests/test_external_repo_smoke.py tests/test_external_repo_onboarding_report.py tests/test_external_repo_onboarding_index.py` -> `10 passed`
  - `governance_tools/external_repo_smoke.py --repo D:\Kernel-Driver-Contract --format human` -> `ok=True`, `post_task_ok=True`

## 2026-03-15 - Trust Signal Overview Now Includes External Onboarding Health

- Extended `governance_tools/trust_signal_overview.py` so `--external-contract-repo` no longer feeds only the external policy matrix.
- The same repo list now also flows into `governance_auditor.py` as `external_repos`, which means higher-level trust views can surface:
  - missing onboarding reports
  - failing external smoke
  - failing external `post_task_ok`
  - `external_top_issue=...` lines with suggested next commands
- This closes a subtle trust-signal gap where release/status pages could show a healthy mixed-enforcement policy picture while still hiding that onboarding or validator replay had regressed.
- Verification:
  - `tests/test_trust_signal_overview.py tests/test_trust_signal_snapshot.py tests/test_governance_auditor.py` -> `30 passed`

## 2026-03-15 - Four-Repo Progress Memo And Gap Reframing

- Added `docs/status/four-repo-integration-progress.md` as the formal progress memo for:
  - `ai-governance-framework`
  - `USB-Hub-Firmware-Architecture-Contract`
  - `Kernel-Driver-Contract`
  - `IC-Verification-Contract`
- Recorded the key correction that `validator execution` is no longer the primary framework gap.
- Reframed the most important remaining work as:
  - real facts intake
  - practical git-hook / CI-gate interception coverage
  - deeper semantic verification beyond pattern-based checks
- Tightened the repository boundary statement so future status docs do not imply token-by-token AI output interception as an in-scope goal.

## 2026-03-15 - Competitive Landscape Memo

- Added `docs/competitive-landscape.md` as a stable positioning memo over the closest known reference projects.
- Grouped nearby projects into:
  - closest open-source references
  - adjacent but not direct peers
- Recorded the main differentiation of this repository as the combination of:
  - external domain contracts across separate repos
  - mixed enforcement
  - reviewer/audit publication surfaces
- Added the new landscape doc to README further-reading links so future release/status messaging can reuse the same positioning source.

## 2026-03-15 - README Comparison Entry Added

- Promoted the competitive-landscape memo into a first-class README section under `Comparison & Differentiation`.
- Added a short directional comparison table to the landscape doc so the positioning can be reused more easily in release notes, README updates, or external write-ups.
- Linked the alpha GitHub release draft back to `docs/competitive-landscape.md`, so the release-facing story and the longer positioning memo now point at the same source of truth.

## 2026-03-15 - Competitive Landscape Claims Softened

- Tightened `docs/competitive-landscape.md` so competitor comparisons are explicitly directional rather than framed as exhaustive feature proof.
- Rewrote the comparison table around visible emphasis and center of gravity instead of implying another project definitively lacks cross-repo or contract-based patterns.
- Narrowed the interception borrowing note to `git hook + CI gate` ideas from `agentic-engineering-framework`, which keeps the positioning aligned with the framework boundary against code-generation-time interception.

## 2026-03-15 - Additional Competitive References Added

- Extended `docs/competitive-landscape.md` with additional comparison candidates:
  - `microsoft/agent-governance-toolkit`
  - `SAFi`
  - `GitHub Spec Kit`
  - `Sovereign-OS`
  - `GitHub Agent HQ / Agentic Workflows`
  - `Agent Behavioral Contracts (ABC)` / `POLARIS`
- Recorded the most important new layer distinction:
  - action-level governance around agent/tool execution
  - versus task/session-boundary architecture governance in this repository
- Updated README wording so the project now explicitly states that it governs primarily at the task/session boundary rather than every agent action or generation token.

## 2026-03-15 - Interception And Workflow Embedding Clarified

- Updated `README.md` so the remaining framework gaps are described in practical engineering terms rather than abstract labels.
- `interception coverage` is now explicitly framed as:
  - git hooks
  - CI gates
  - external onboarding / runtime entrypoint hardening
- `workflow embedding` is now explicitly framed as:
  - contract discovery
  - contract-aware smoke
  - reviewer handoff
  - change-control flow ergonomics
- Added the same boundary to `PLAN.md`, making it explicit that this roadmap is about commit/merge-time governance rather than IDE-native or token-level interception.

## 2026-03-15 - Onboarding Report Artifact

- Added `governance_tools/external_repo_onboarding_report.py` to combine readiness and governance-smoke results into a single report.
- `scripts/onboard-external-repo.sh` now writes a JSON report by default to:
  - `memory/governance_onboarding/latest.json` inside the target repo
- The onboarding shell flow now keeps running long enough to emit this report even when readiness or smoke fails, then exits non-zero afterward.
- Verification:
  - `tests/test_external_repo_onboarding_report.py` -> `2 passed`
  - `scripts/onboard-external-repo.sh --target ../Kernel-Driver-Contract --dry-run`
  - `scripts/verify_phase_gates.sh` -> `322 passed`, `4/4 Gates`

## 2026-03-15 - Onboarding Report History And Index

- Extended onboarding report output so it now writes an artifact bundle, not only a single JSON file.
- The default target repo onboarding directory now keeps:
  - `latest.json`
  - `latest.txt`
  - `history/*.json`
  - `history/*.txt`
  - `INDEX.txt`
- This gives external repo setup a minimal time-series audit trail and a reviewer-friendly index.
- Verification:
  - `tests/test_external_repo_onboarding_report.py` -> `3 passed`
  - `scripts/verify_phase_gates.sh` -> `323 passed`, `4/4 Gates`

## 2026-03-15 - Cross-Repo Onboarding Index

- Added `governance_tools/external_repo_onboarding_index.py` so the framework repo can aggregate onboarding state across multiple external repos.
- The index is intentionally simple:
  - reads each repo's `memory/governance_onboarding/latest.json`
  - sorts failures first
  - surfaces missing reports explicitly
- This creates a framework-level view over external governance adoption without merging repos or overloading change-control artifacts yet.
- Verification:
  - `tests/test_external_repo_onboarding_index.py` -> `3 passed`
  - `scripts/verify_phase_gates.sh` -> `326 passed`, `4/4 Gates`

## 2026-03-15 - Auditor Integration For External Onboarding

- Extended `governance_tools/governance_auditor.py` so it can optionally include external onboarding state through `--external-repo`.
- This keeps external repo onboarding drift inside the same high-level governance audit surface instead of creating a fully separate reporting lane.
- Verification:
  - `tests/test_governance_auditor.py` -> `4 passed`
  - `scripts/verify_phase_gates.sh` -> `327 passed`, `4/4 Gates`

## 2026-03-15 - Reviewer-Facing Top Issues For External Repos

- Extended `external_repo_onboarding_index.py` so it now computes a small `top_issues` list from the most urgent failing repos.
- `governance_auditor.py --external-repo ...` now surfaces those top issues directly in human output.
- This shifts the output from "status table only" toward "what should be fixed first".
- Verification:
  - `tests/test_external_repo_onboarding_index.py tests/test_governance_auditor.py` -> `7 passed`
  - `scripts/verify_phase_gates.sh` -> `327 passed`, `4/4 Gates`

## 2026-03-15 - Suggested Commands In External Top Issues

- Extended external onboarding `top_issues` so each issue now carries a suggested next command.
- `governance_auditor.py` human output now surfaces these commands directly, so external repo drift output is more operational and less purely descriptive.
- Verification:
  - `tests/test_external_repo_onboarding_index.py tests/test_governance_auditor.py` -> `7 passed`
  - `scripts/verify_phase_gates.sh` -> `327 passed`, `4/4 Gates`

## 2026-03-15 - Actionable Auditor Triage

- Tightened the reviewer-facing framing so external onboarding issues now read as explicit remediation hints rather than only passive status signals.
- This keeps the current auditor lightweight while making the output more directly usable during governance maintenance.

## 2026-03-15 - Direct CLI Bootstrap Fix

- Fixed a CI regression where `governance_tools/change_control_summary.py` failed when executed as a direct script because package imports no longer had the repo root on `sys.path`.
- Restored the standard script-entry bootstrap pattern across direct `governance_tools/` CLIs that import other `governance_tools.*` modules.
- Added a subprocess regression test to ensure `python governance_tools/change_control_summary.py ...` continues to work as a direct entrypoint.
- Verification:
  - `tests/test_change_control_summary.py` -> `4 passed`
  - `scripts/run-runtime-governance.sh --mode ci` -> passed
  - `scripts/verify_phase_gates.sh` -> `328 passed`, `4/4 Gates`

## 2026-03-15 - Adoption Baseline Docs

- Added `requirements.txt` so clone-first users have an explicit starting dependency set instead of having to infer runtime/test/example requirements from the codebase.
- Added `start_session.md` as a five-minute quickstart that verifies:
  - core tool CLI availability
  - a minimal `pre_task_check`
  - a domain-aware `session_start`
- Updated example documentation to clarify which examples are:
  - runnable demos
  - walkthrough-only narratives
  - scaffolds/templates
- Noted that repo-root quickstart runs can emit advisory pack-suggestion warnings because this framework repo intentionally contains mixed-language fixtures and examples.
- Verification:
  - `governance_tools/contract_validator.py --help`
  - `runtime_hooks/core/pre_task_check.py --project-root . --rules common --risk low --oversight review-required --memory-mode candidate --task-text "Quickstart governance check" --format human`
  - `runtime_hooks/core/session_start.py --project-root . --plan PLAN.md --rules common,hub-firmware --risk medium --oversight review-required --memory-mode candidate --task-text "Validate USB hub firmware response flow" --contract examples/usb-hub-contract/contract.yaml --format human`
  - `scripts/verify_phase_gates.sh` -> `328 passed`, `4/4 Gates`

## 2026-03-15 - Quickstart Smoke Command

- Added `governance_tools/quickstart_smoke.py` as a single-command verifier for the documented onboarding path.
- The tool bundles:
  - a minimal `pre_task_check`
  - a minimal `session_start`
  - optional external contract verification
- This shifts the quickstart from "doc only" toward "documented and executable".
- Added `tests/test_quickstart_smoke.py`.
- Updated `README.md`, `start_session.md`, and `governance_tools/README.md` to point to the new entrypoint.
- Verification:
  - `tests/test_quickstart_smoke.py` -> `2 passed`
  - `governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human`
  - `scripts/verify_phase_gates.sh` -> `330 passed`, `4/4 Gates`

## 2026-03-15 - Quickstart Path In Phase Gates

- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also runs `quickstart_smoke.py` against the bundled USB-Hub contract example.
- This means the documented onboarding path is no longer only "documented and runnable"; it is now part of the framework's routine regression baseline.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `330 passed`, `4/4 Gates`

## 2026-03-15 - CI Dependency Baseline Alignment

- Updated `.github/workflows/governance.yml` so test/runtime jobs now install `requirements.txt` instead of manually installing only `pytest`.
- This keeps CI closer to the documented local onboarding path and reduces the chance that examples/tests drift onto different dependency baselines.

## 2026-03-15 - Example Readiness Inventory

- Added `governance_tools/example_readiness.py` to classify bundled examples as runnable demo, walkthrough, scaffold, or domain-contract sample.
- The checker now reports:
  - required-file completeness
  - runtime readiness for runnable examples in the current environment
  - domain contract load / validator preflight health for `usb-hub-contract`
- Added `tests/test_example_readiness.py`.
- Updated `examples/README.md` and `start_session.md` to point to the new inventory check.
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also runs `example_readiness.py`.
- Verification:
  - `tests/test_example_readiness.py` -> `2 passed`
  - `governance_tools/example_readiness.py --format human`
  - `scripts/verify_phase_gates.sh` -> `332 passed`, `4/4 Gates`

## 2026-03-15 - Strict Runnable Example Validation In CI

- Strengthened `example_readiness.py` so runnable demos are no longer checked only by dependency presence and module import.
- When dependencies are present, runnable-demo validation now also checks:
  - that the module exposes `app`
  - that the app advertises a `/health` route
- Added a unit test covering this deeper runnable-demo smoke without requiring FastAPI.
- Updated `.github/workflows/governance.yml` so GitHub Actions now runs:
  - `python governance_tools/example_readiness.py --strict-runtime --format human`
  after installing `requirements.txt`
- This keeps local adoption checks permissive enough for contributors without demo dependencies, while making CI the strict verifier for runnable example health.
- Verification:
  - `tests/test_example_readiness.py` -> `3 passed`
  - `scripts/verify_phase_gates.sh` -> `333 passed`, `4/4 Gates`

## 2026-03-15 - Alpha Release-Facing Docs

- Added `docs/releases/v1.0.0-alpha.md` as the first release-facing summary inside the repo.
- Added `CHANGELOG.md` and linked the version badge / README entrypoints to the alpha release note.
- Updated `PLAN.md` so the current maintenance stage now explicitly reflects:
  - alpha adoption hardening
  - quickstart / example readiness work
  - release-facing trust-signal work
- Updated `docs/status/runtime-governance-status.md` to reflect the current alpha-era positioning and onboarding assets.

## 2026-03-15 - GitLab CI Baseline Alignment

- Extended `.gitlab-ci.yml` so GitLab CI is no longer substantially behind GitHub Actions.
- Added:
  - `phase-gates` job
  - strict `example_readiness.py --strict-runtime` validation
  - `runtime-enforcement` job
- GitLab runtime/test jobs now also install `requirements.txt`, aligning CI dependency setup across both platforms.

## 2026-03-15 - Release Readiness Gate

- Added `governance_tools/release_readiness.py` to check release-facing trust signals for a specific version.
- Current checks cover:
  - `docs/releases/<version>.md`
  - `CHANGELOG.md`
  - `README.md`
  - `docs/LIMITATIONS.md`
  - `docs/status/runtime-governance-status.md`
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also runs:
  - `release_readiness.py --version v1.0.0-alpha`
- Verification:
  - `tests/test_release_readiness.py` -> `2 passed`
  - `governance_tools/release_readiness.py --version v1.0.0-alpha --format human`
  - `scripts/verify_phase_gates.sh` -> `335 passed`, `4/4 Gates`

## 2026-03-15 - Release-Aware Governance Auditor

- Extended `governance_tools/governance_auditor.py` so high-level self-audits can optionally include release-facing readiness through `--release-version`.
- This keeps constitution alignment, runtime enforcement alignment, external onboarding drift, and release-doc alignment on the same audit surface instead of splitting them into unrelated commands.
- Added auditor regression coverage for the current alpha release baseline.
- Verification:
  - `tests/test_governance_auditor.py` -> `5 passed`
  - `scripts/verify_phase_gates.sh` -> `336 passed`, `4/4 Gates`

## 2026-03-15 - Governance Auditor Added To Phase Gates

- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also runs `governance_auditor.py --release-version v1.0.0-alpha`.
- This promotes the high-level self-audit path from "available tool" to "routine regression surface", keeping constitution/runtime/release alignment executable in the same place as the other onboarding and trust-signal checks.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `336 passed`, `4/4 Gates`

## 2026-03-15 - Summary-First Human Output For High-Level Governance Tools

- Added a shared `governance_tools/human_summary.py` helper for governance-tool human output.
- `release_readiness.py`, `external_repo_onboarding_index.py`, and `governance_auditor.py` now begin with a reviewer-first `summary=...` line instead of forcing operators to scan lower-level fields first.
- `governance_auditor.py` human rendering is now a dedicated function, making output-shape regressions testable without relying only on CLI behavior.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `338 passed`, `4/4 Gates`

## 2026-03-15 - Trust Signal Overview Entry Point

- Added `governance_tools/trust_signal_overview.py` as a single high-level entrypoint for:
  - `quickstart_smoke.py`
  - `example_readiness.py`
  - `release_readiness.py`
  - `governance_auditor.py`
- The new tool is aimed at adoption/release confidence rather than deep debugging; it gives one reviewer-facing `summary=...` line for the repo's current high-level trust posture.
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also executes this overview path.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `340 passed`, `4/4 Gates`

## 2026-03-15 - Alpha Checklist Added To Release Trust Signals

- Added `docs/releases/alpha-checklist.md` as a lightweight, explicit release-facing checklist for the current alpha.
- Extended `governance_tools/release_readiness.py` so release readiness now checks:
  - release note presence
  - changelog alignment
  - runtime status / limitations docs
  - alpha checklist presence and basic coverage
- Verification:
  - `scripts/verify_phase_gates.sh` -> `340 passed`, `4/4 Gates`

## 2026-03-15 - Trust Signal Overview Artifacts In CI

- Extended `governance_tools/trust_signal_overview.py` with `--output` so its overview can be saved as a report, not only printed to the terminal.
- Updated GitHub Actions and GitLab CI to generate:
  - `artifacts/trust-signals/trust_signal_overview.txt`
  - `artifacts/trust-signals/trust_signal_overview.json`
- Extended the tool again so it can also render Markdown dashboard output, and CI now also emits:
  - `artifacts/trust-signals/trust_signal_overview.md`
- This makes the high-level adoption/release posture visible as a pipeline artifact instead of only a local command.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `342 passed`, `4/4 Gates`

## 2026-03-15 - Stable Trust Signal Dashboard Page

- Added `docs/status/trust-signal-dashboard.md` as the stable in-repo landing page for high-level trust signals.
- This page does not try to be the generated report itself; instead it:
  - points to `trust_signal_overview.py`
  - explains the CI artifacts
  - links release note / checklist / limits / runtime status in one place
- Extended `release_readiness.py` so this stable dashboard page is now part of the release-facing trust-signal surface.

## 2026-03-15 - Status Page Index

- Added `docs/status/README.md` as a stable index over:
  - trust-signal dashboard
  - runtime governance status
  - next-steps
- This gives external readers a clearer status-reading order instead of relying only on scattered README links.

## 2026-03-15 - Trust Signal Snapshot Publisher

- Added `governance_tools/trust_signal_snapshot.py` as a publishing-oriented wrapper around `trust_signal_overview.py`.
- The new tool writes a structured bundle with:
  - `latest.*`
  - `history/*`
  - `INDEX.md`
- `scripts/verify_phase_gates.sh` now exercises this publishing path, and GitHub Actions / GitLab CI now use it instead of manually calling the overview renderer three times.
- Verification:
  - `scripts/verify_phase_gates.sh` -> `345 passed`, `4/4 Gates`

## 2026-03-15 - Published Status Pages From Snapshot Publisher

- Extended `governance_tools/trust_signal_snapshot.py` with `--publish-status-dir`.
- The same command can now emit:
  - bundle artifacts (`latest/history/index`)
  - publish-style status pages (`trust-signal-latest.md`, `trust-signal-latest.json`, `README.md`)
- CI now uses this same path, so the publishing format is exercised in both local phase gates and remote pipelines.

## 2026-03-15 - Trust Signal Publication Manifest

- Extended the trust-signal snapshot publisher so both bundle outputs and published status pages now emit manifest JSON.
- New metadata files:
  - `MANIFEST.json`
  - `published/manifest.json`
- This reduces ambiguity around "which snapshot is current" and gives future tooling a stable metadata surface.

## 2026-03-15 - Published Trust Signal History And Index

- Extended the published status path so it now also keeps:
  - `published/history/*`
  - `published/INDEX.md`
- This makes the publication side behave more like the bundle side: latest remains easy to link, but historical published snapshots are now also reviewable.

## 2026-03-15 - Trust Signal Publication Index

- Extended the trust-signal publisher again so it now emits:
  - `PUBLICATION_MANIFEST.json`
  - `PUBLICATION_INDEX.md`
- This publication-level layer links the bundle side and the published side together, reducing the need to know internal directory layout before consuming the latest status output.

## 2026-03-15 - Domain Validator Hard-Stop Enforcement

- Closed the remaining gap between domain-validator execution and governance enforcement.
- `runtime_hooks/core/post_task_check.py` still treats domain-validator findings as advisory by default, but now reads optional contract-level `hard_stop_rules`.
- When a validator returns a `violation` whose `rule_ids` intersect `hard_stop_rules`, the result is now merged into `errors` instead of only `warnings`.
- Added targeted tests covering both:
  - advisory-only contract behavior
  - hard-stop escalation behavior
- This shifts the framework from "validators run but only warn" to "validators run, and selected rule IDs can now block post-task success without changing the discovery seam."

## 2026-03-15 - IC Verification Mixed Enforcement Slice

- Extended the third external contract repo, `IC-Verification-Contract`, to use the new enforcement seam in a narrow, machine-readable way.
- `ICV-001` is now a hard-stop rule because DUT signal presence is backed by `facts/signal_map.json`.
- Clock/reset declaration checks remain advisory, so the domain now demonstrates a mixed enforcement model instead of an all-advisory baseline.
- Verified from the framework side:
  - unknown signal fixture now returns `ok=False`
  - missing clock/reset fixture still returns `ok=True` with warnings
  - clean fixture remains green

## 2026-03-15 - USB Hub Mixed Enforcement Slice

- Promoted `USB-Hub-Firmware-Architecture-Contract` from advisory-only post-task validation into a mixed enforcement slice.
- `HUB-004` is now listed under `hard_stop_rules`, so ISR-side forbidden calls become blocking errors instead of reviewer-only warnings.
- Added a compliant ISR fixture so the repo now has both:
  - a blocking interrupt-regression baseline
  - a clean interrupt-safe baseline
- Verified from the framework side:
  - `interrupt_regression.checks.json` now returns `ok=False`
  - `interrupt_compliant.checks.json` returns `ok=True`

## 2026-03-15 - External Contract Enforcement Matrix

- Added `governance_tools/external_contract_policy_index.py` to compare external contract enforcement posture across repos.
- The new tool summarizes:
  - domain
  - risk tier
  - enforcement profile (`discovery-only`, `advisory-only`, `mixed`)
  - validator readiness
  - `hard_stop_rules`
- Added `docs/status/domain-enforcement-matrix.md` as the stable in-repo landing page for this view.
- This reduces multi-domain policy review from "open three repos and inspect `contract.yaml` by hand" to one framework-level command and one stable status page.

## 2026-03-15 - Trust Signal Publishing Can Include External Contract Policy

- Extended `trust_signal_overview.py` so it can optionally include external contract enforcement posture through repeated `--external-contract-repo`.
- Extended `trust_signal_snapshot.py` and publication manifests so this same cross-domain policy view can flow into published status artifacts.
- Extended `trust_signal_publication_reader.py` so publication summaries now surface:
  - `external_contract_repo_count`
  - `external_contract_policy_ok`
- This keeps trust-signal publishing aligned with the newer multi-domain enforcement view instead of leaving it stranded as a standalone tool.

## 2026-03-15 - Publication Reader Now Carries Compact Policy Summaries

- Extended `trust_signal_snapshot.py` manifests again so they now preserve:
  - `external_contract_profile_counts`
  - `external_contract_policies`
- This means release/status consumers can see per-repo enforcement posture and hard-stop rules without reopening the full markdown dashboard.
- Extended `trust_signal_publication_reader.py` with a dedicated `[external_contract_policies]` section so the publication surface is reviewer-friendly, not only machine-readable.
- Updated README / status docs / governance-tools docs so the richer publication metadata is now described explicitly.

## 2026-03-15 - Published Status Now Emits Dedicated Domain Enforcement Pages

- Extended `trust_signal_snapshot.py` so bundle publishing now also writes:
  - `external-contract-policy-latest.md`
  - `external-contract-policy-latest.json`
  - matching history copies
- Extended the published status surface so it now also writes:
  - `published/domain-enforcement-matrix.md`
  - `published/domain-enforcement-matrix.json`
- Extended `trust_signal_publication_reader.py` so those dedicated policy pages are discoverable from the same reviewer-facing summary.
- Extended `release_readiness.py` so the static `docs/status/domain-enforcement-matrix.md` page is now part of release-facing readiness checks.

## 2026-03-15 - Docs Status Publishing Mode

- Extended `trust_signal_snapshot.py` with `--publish-docs-status`.
- This mode now defaults snapshot outputs into a stable repo-local path:
  - `docs/status/generated/bundle`
  - `docs/status/generated/site`
  - publication metadata rooted at `docs/status/generated`
- Updated status/README docs so this path is now part of the recommended consumption story, not only an implicit convention.

## 2026-03-15 - Docs Status Reader And Publication Root README

- Extended `trust_signal_publication_reader.py` with `--docs-status`, so the stable repo-local generated path can be consumed without manually passing a manifest file.
- Extended `trust_signal_snapshot.py` publication-root generation so `docs/status/generated/README.md` is now emitted as an index/readme for the generated snapshot root.
- Updated README / status docs / governance-tools docs to show both:
  - the ad-hoc artifact path
  - the stable repo-local docs-status path
- The generated-root README is now also summary-first, not just a link list, so it can act as a direct landing page for reviewers.
- `release_readiness.py` now also checks that the top-level status index explicitly points to the generated landing page and generated site readme, tightening the docs-status consumption story.

## 2026-03-15 - Alpha Docs Now Reference Generated Status Flow

- Updated `docs/releases/v1.0.0-alpha.md` so the recommended evaluation path now includes:
  - publishing a repo-local generated status snapshot
  - reading it back through the docs-status reader path
- Updated `docs/releases/alpha-checklist.md` so the docs-status publish/read commands are part of the explicit alpha confidence checks.
- Extended `release_readiness.py` so these release-facing docs are now checked for the generated status path, not only for the older trust-signal overview entrypoint.

## 2026-03-15 - GitHub Release Draft Added To Release Surface

- Added `docs/releases/v1.0.0-alpha-github-release.md` as a repo-tracked GitHub release draft body.
- Updated the alpha release note, alpha checklist, and changelog so the draft is part of the documented release surface instead of an implicit future task.
- Extended `release_readiness.py` so it now verifies:
  - the GitHub release draft exists
  - its heading matches the current version
  - it references the generated status path and status index

## 2026-03-15 - Publish Checklist Added To Release Surface

- Added `docs/releases/v1.0.0-alpha-publish-checklist.md` as a repo-tracked checklist for the actual release publication step.
- Updated the changelog, alpha release note, GitHub release draft, and alpha checklist so the publish checklist is now part of the visible release package.
- Extended `release_readiness.py` so it now verifies the publish checklist exists and still references:
  - docs-status publishing
  - docs-status reader flow
  - `verify_phase_gates.sh`

## 2026-03-15 - Release Package Summary Entry Point

- Added `governance_tools/release_package_summary.py` as a single reviewer-facing summary over the current alpha release package.
- The new tool aggregates:
  - `release_readiness.py`
  - release docs
  - status docs
  - recommended release-facing verification commands
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also executes this package-summary path.
- Updated README, governance-tools docs, and the alpha publish checklist so release preparation has a stable single-command summary, not only scattered links and checklists.

## 2026-03-15 - Release Package Snapshot Bundle

- Added `governance_tools/release_package_snapshot.py` as the persistence layer over `release_package_summary.py`.
- The new tool writes a release-package bundle with:
  - `latest.json`
  - `latest.txt`
  - `latest.md`
  - `history/*`
  - `INDEX.md`
  - `MANIFEST.json`
  - `README.md`
- It also supports a stable repo-local release publication path through `--publish-docs-release`.
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also exercises this release-package snapshot path.

## 2026-03-15 - Release Package Reader Flow

- Added `governance_tools/release_package_reader.py` as the stable reader over generated release-package manifests.
- The reader supports both:
  - direct artifact consumption with `--file`
  - repo-local generated release bundles with `--docs-release`
- Updated alpha release docs, GitHub release draft, alpha checklist, publish checklist, and README so the generated release-package path now has a documented publish/read flow instead of only a snapshot command.
- Extended `scripts/verify_phase_gates.sh` so Gate 3 now also exercises the release-package reader path.

## 2026-03-15 - Generated Release Root Landing Path

- Extended `governance_tools/release_package_snapshot.py` so `--publish-docs-release` now also maintains a stable root under `docs/releases/generated/`.
- The generated release root now keeps:
  - `README.md`
  - `latest.json`
  - `latest.md`
  - versioned subdirectories such as `v1.0.0-alpha/`
- Extended `release_readiness.py` so alpha release docs now explicitly reference this generated release path, not only the generated status path.

## 2026-03-15 - Release Package Publication Reader

- Added `governance_tools/release_package_publication_reader.py` as the stable reader over release-package `PUBLICATION_MANIFEST.json`.
- `release_package_snapshot.py` now emits publication manifests/indexes for both:
  - artifact bundle scope
  - repo-local generated release root
- Updated release docs and generated-release docs so the release-package publish/read flow now includes:
  - snapshot
  - version reader
  - generated-root publication reader

## 2026-03-15 - CI Release Package Artifacts

- Extended GitHub Actions and GitLab CI so the phase-gates job now also generates:
  - `artifacts/release-package/v1.0.0-alpha/`
- CI now also runs `release_package_publication_reader.py` against the generated publication manifest, so the artifact is both produced and consumed in pipeline.
- Updated release docs and README so the CI release-package artifact bundle is part of the visible alpha trust signal surface.

## 2026-03-15 - Stable Release Index

- Added `docs/releases/README.md` as the stable entry point for release-facing artifacts.
- Extended `release_readiness.py` so release readiness now checks:
  - the release index exists
  - it links to the current release note
  - it links to the generated release root
- Updated README, changelog, release note, GitHub draft, and publish checklist so the release index is now part of the visible release surface instead of an implicit directory listing.

## 2026-03-15 - Trust-Signal Publication Root Fix

- Fixed `governance_tools/trust_signal_snapshot.py` so artifact-style publication (`--write-bundle` and/or `--publish-status-dir`) now also defaults `publication_root` instead of requiring a third explicit path.
- This closes a clean-workspace CI bug where `trust_signal_publication_reader.py --file artifacts/trust-signals/.../PUBLICATION_MANIFEST.json` could fail even though local reruns passed because an old manifest already existed.
- Added regression coverage in `tests/test_trust_signal_snapshot.py` for the new default publication-root behavior.

## 2026-03-15 - CI Release Surface Artifacts

- Extended GitHub Actions and GitLab CI so the phase-gates flow now also emits `artifacts/release-surface/`.
- The new artifact preserves `release_surface_overview.py` in human / JSON / Markdown forms, so reviewers have a single high-level release handoff surface inside CI instead of only local CLI output.
- Updated release docs, README, and tool docs so this new artifact path is part of the visible alpha review surface.

## 2026-03-15 - Reviewer Handoff Summary

- Added `governance_tools/reviewer_handoff_summary.py` as the highest-level reviewer entrypoint over `trust_signal_overview.py` and `release_surface_overview.py`.
- Added regression coverage in `tests/test_reviewer_handoff_summary.py` and phase-gate execution coverage in `scripts/verify_phase_gates.sh`.
- Extended GitHub Actions and GitLab CI so the phase-gates flow now also emits `artifacts/reviewer-handoff/` in human / JSON / Markdown forms.
- Updated README, release docs, publish checklist, and tool docs so this new reviewer packet is visible as part of the alpha consumption path.

## 2026-03-15 - Reviewer Handoff Status Page

- Added `docs/status/reviewer-handoff.md` as the stable in-repo landing page for the highest-level reviewer packet.
- Updated `docs/status/README.md` so status reading order now starts with reviewer handoff before trust/release drill-down pages.
- Extended `release_readiness.py` and `tests/test_release_readiness.py` so the reviewer-handoff page is now part of the machine-checked alpha status surface.

## 2026-03-15 - Reviewer Handoff Snapshot And Reader

- Added `governance_tools/reviewer_handoff_snapshot.py` so the highest-level reviewer packet can now be preserved as:
  - `latest.*`
  - `history/*`
  - `INDEX.md`
  - `MANIFEST.json`
  - `README.md`
- Added `governance_tools/reviewer_handoff_reader.py` so that bundle can be consumed through a stable reviewer-first summary instead of opening raw manifest JSON.
- Updated phase gates and CI so reviewer-handoff artifacts are now emitted as a versioned bundle under `artifacts/reviewer-handoff/`, not only as three flat output files.

## 2026-03-15 - Reviewer Handoff Publication Reader

- Extended `governance_tools/reviewer_handoff_snapshot.py` so reviewer-handoff bundles now also emit:
  - bundle-level publication metadata
  - root-level `PUBLICATION_MANIFEST.json`
  - root-level `PUBLICATION_INDEX.md`
  - published site pages under `published/`
- Added `governance_tools/reviewer_handoff_publication_reader.py` so the reviewer packet now has a publication-layer reader flow, matching the pattern already used by trust-signal and release-package artifacts.
- Updated phase gates, CI, and release-readiness checks so this publication layer is part of the normal regression surface instead of a documentation-only convention.
- Extended the same reviewer-handoff line again so it can also publish to a stable repo-local docs path under `docs/status/generated/reviewer-handoff/`, with `--docs-status` as the matching reader path.

## 2026-03-15 - Contract-Aware Runtime Smoke Path

- Extended `runtime_hooks/smoke_test.py` so the documented example payloads can now be replayed with:
  - `--contract`
  - `--project-root`
  - `--plan-path`
- This keeps the existing example JSON fixtures intact while making it much easier to point the smoke path at a real external contract repo.
- Shared and adapter-based smoke flows now pass the explicit contract through to:
  - `session_start`
  - `pre_task_check`
  - `post_task_check`
- Smoke-test human output now also surfaces `contract_source`, `contract_path`, and `domain_contract` when that context is available.
- `scripts/verify_phase_gates.sh` now covers this contract-aware smoke flow directly, so the lower-friction demo path is part of the normal regression surface.
- Extended `scripts/run-runtime-governance.sh` so the shared shell smoke/enforcement wrapper now forwards the same overrides into its runtime smoke calls, keeping the common entrypoint aligned with the lower-friction Python smoke path.
- `scripts/verify_phase_gates.sh` now also runs the contract-aware wrapper smoke path itself, so the shell-level entrypoint is exercised in the same regression surface as the underlying Python tool.
- Extended `runtime_hooks/dispatcher.py` with the same `--contract`, `--project-root`, and `--plan-path` override pattern, so shared-event JSON can now be replayed against an external contract repo without editing the event payload itself.
- Dispatcher human output now also surfaces `contract_source`, `contract_path`, and `domain_contract`, and the contract-aware dispatcher path is now part of phase-gate coverage.
- Added a shared runtime path-override helper so both `smoke_test.py` and `dispatcher.py` now infer:
  - `project_root = <contract-root>`
  - `plan_path = <contract-root>/PLAN.md`
  when only `--contract` is supplied and the contract repo itself exposes `PLAN.md`.
- This reduces the lowest-friction external repo trial path from "contract + project-root + plan-path" to just "contract" for the common runtime demo entrypoints.
- Extended the same shared runtime entrypoints so post-task replay can now override:
  - `response_file`
  - `checks_file`
- This moves the shared runtime demo path closer to real evidence-driven workflows, because a domain contract can now be exercised with a raw governance response plus structured evidence fixtures in one command.

## 2026-03-14 - IC / SoC Governance Direction Recorded

- Recorded a refined future-domain view for IC-related governance.
- The main correction is to prioritize domains by mistake cost and machine-readability, not just by technical novelty.
- Current draft priority:
  - `P0`: SoC integration
  - `P1`: RTL design
  - `P2`: IC verification
  - `P3`: CAD automation
- Also recorded a positioning constraint:
  - for domains like RTL / CDC, the framework should be framed more as a risk declaration and reviewer-focusing system than as a full automatic prevention layer
- Noted `address_collision_validator.py` style address-map checking as a particularly strong future candidate because it combines high value with relatively tractable validation logic.

## 2026-03-26 - Review: `ead27a1` Add workflow observation checkpoint artifacts

- Verdict: `CHANGES_REQUESTED`
- Risk: `Medium`
- Blocking finding:
  - The new reviewer-aid artifacts under `artifacts/workflow-entry/harden-workflow-observation-boundary/` do not satisfy the minimum entry-layer artifact envelope they are colocated with.
  - Evidence:
    - `docs/entry-layer-contract.md` defines `artifact_type`, `skill`, `scope`, `timestamp`, `status`, and `provenance` as required envelope fields.
    - `governance_tools/workflow_entry_observer.py` enforces that same envelope and requires `content` plus recognized artifact-specific payload fields.
    - `attack_coverage_checkpoint.json` and `reviewer_attack_shortlist.json` omit at least `skill`, `provenance`, and `content`.
  - Consequence:
    - The commit makes the `workflow-entry` storage surface internally inconsistent and invites future consumers to treat reviewer-only adjunct files as if they were runtime-recognizable workflow artifacts.
- Warning:
  - The new files reuse the `workflow-entry` namespace even though current runtime recognition only models `tech_spec`, `validation_evidence`, and `pr_handoff`.
  - If reviewer-only adjunct artifacts are meant to stay outside the recognizable loop, they should either move to a separate reviewer namespace or gain an explicit “observer-ignored adjunct artifact” contract.
- Suggestion:
  - The repo already captures partial “do not add” reasoning through `non_goals`, `scope_excluded`, and `explicitly_not_now`, but it still lacks a forced decision record for:
    - what breaks if a proposed mechanism is added
    - what happens if it is not added
    - whether it overlaps an existing mechanism
    - the maintenance / complexity cost of adding it

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260415T095351Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260416T064338Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260416T064347Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260416T071804Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260416T071814Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260416T071851Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260507T055153Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260507T055153Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260507T055203Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260514T104430Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260514T105259Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260514T105339Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T083006Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T083347Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T083809Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T084041Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T084427Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T084804Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T085428Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T085929Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T090221Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T092344Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T092452Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T093557Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T093829Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T094741Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T094959Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T095857Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T100011Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T100328Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T101302Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260515T102514Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260518T112056Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260518T112813Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T020150Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T020854Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T021156Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T021726Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T021855Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T022522Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T023129Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T023627Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T061354Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T062023Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T062910Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T063516Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T064813Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T070119Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260520T071144Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T014415Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T014756Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T015601Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T020053Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T021134Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T021646Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T030307Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T031043Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T032835Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T032905Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T033230Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T034944Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T053539Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T083331Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T083536Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T083936Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T084646Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T085517Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T085612Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T090232Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T090833Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T091805Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T091856Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T092552Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T092717Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T093457Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T093753Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T093836Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T094321Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T094453Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T095103Z.json
- Risk: low
- Oversight: auto

## Promotion: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T101504Z.json
- Risk: low
- Oversight: auto

## Promotion: session
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T101520Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260521T101527Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T012654Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T013320Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T013421Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T013812Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T014119Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T014912Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T020900Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T021747Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T025449Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T062332Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T062738Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T063225Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T064355Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T064733Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T065645Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T070441Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T070842Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T071142Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T071325Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T071420Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T071529Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T071943Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T073300Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T074919Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075042Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075237Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075352Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075643Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075746Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T075905Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T082306Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T082433Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T082939Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T083219Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T083619Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T083822Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T084148Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T085144Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T085349Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T085854Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T085949Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T090122Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T090327Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T090438Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T091045Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T091356Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T091629Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T091836Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T092304Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T092719Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T092909Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T093204Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T093347Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T093436Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T093824Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T094106Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T094218Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T094547Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T094838Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T095426Z.json
- Risk: low
- Oversight: auto

## Promotion: Closeout for Copilot Class D ingestion evidence slice with strict semantic boundaries and fixed smoke/test evidence entrypoints.
- Approved by: governance-auto
- Candidate: E:\BackUp\Git_EE\ai-governance-framework\memory\candidates\session_20260522T095802Z.json
- Risk: low
- Oversight: auto

## Promotion: CodeBurn v1.1 baseline complete + Daily Memory Gate v0.1 stabilization (2026-05-22)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260522T153135Z.json
- Risk: low
- Oversight: auto

## Promotion: CodeBurn v1.1 baseline complete + Daily Memory Gate v0.1 stabilization (2026-05-22)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260522T153452Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T034542Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T035311Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T041336Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T041656Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T041922Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T042101Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T042523Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T044331Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T045223Z.json
- Risk: low
- Oversight: auto

## Promotion: Runtime Enforcement Attachment v0.1 + External Fleet Governance CI (2026-05-23)
- Approved by: governance-auto
- Candidate: D:\ai-governance-framework\memory\candidates\session_20260524T045250Z.json
- Risk: low
- Oversight: auto

## 2026-07-06 - Retire-Candidate Focused Review: Four Governance Tool Candidates

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/MEMORY_PROTOCOL.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `docs/governance/decision-change-ledger.inventory.v0.1.json`
- `governance_tools/clean_pilot_admissibility.py`
- `governance_tools/promotion_gate_receipt_smoke.py`
- `governance_tools/host_agent_memory_sync_signal.py`
- `governance_tools/r49x4_metric_ranking.py`
- `tests/test_host_agent_memory_sync_signal.py`
- `governance/fleet/cleaning_admissibility_policy.yaml`
- tracked-file reference scans via `git grep`

### Decision Summary
**Verdict**: ESCALATED
**Risk Level**: Medium

Reason: the inventory artifact correctly identified four zombie/retire candidates, but focused review found mixed dispositions. One candidate is safe enough for a later removal slice, one is better handled as deprecate-first, and two require owner/lineage decisions before deletion. No defense is retired by this review.

### Governance Audit
- Architecture: no runtime, hook, CI, gate, schema, or authority behavior changed in this review.
- Native Safety: N/A.
- Test Integrity: focused checks matched scope; no full regression run.
- Thread Safety: N/A.
- Baseline Status: Stable for review scope; working tree was clean before review.

### Technical Findings

1. [WARNING] `clean_pilot_admissibility` is not wired, but policy coupling makes direct deletion premature.
   - Location: `governance_tools/clean_pilot_admissibility.py:48`
   - Evidence: inventory says zero references and zero dedicated tests; tracked grep found only the tool itself and the inventory artifact. The tool reads `governance/fleet/cleaning_admissibility_policy.yaml`, which is an observation-only dirty-state policy.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` quality/evidence requirement; seed rare-critical policy requires focused review before retirement.
   - Status: open
   - Disposition: `needs-human-decision`. Decide whether the clean-pilot policy remains useful. If yes, add tests/wiring; if no, retire the tool and policy together in a separate slice.

2. [SUGGESTION] `promotion_gate_receipt_smoke` is a retire-safe candidate because its behavior is covered by stronger tests.
   - Location: `governance_tools/promotion_gate_receipt_smoke.py:46`
   - Evidence: the standalone smoke checks digest stability and contract version; focused pytest ran `tests/test_change_control_summary.py` digest tests plus `tests/test_promotion_gate_digest_regression.py` and passed 16 tests. The smoke script itself also returned ok=true.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` test integrity and evidence matching.
   - Status: open
   - Disposition: `retire-safe-candidate`. A later deletion slice may remove the smoke script after citing the existing digest regression tests as replacement evidence.

3. [WARNING] `host_agent_memory_sync_signal` is tested policy logic, not safe to delete without a host-memory policy decision.
   - Location: `governance_tools/host_agent_memory_sync_signal.py:44`
   - Evidence: tracked grep found a dedicated test file; focused pytest passed all five host-agent memory sync tests. CLI negative probe emitted `memory_sync_missing` and exited non-zero by design.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` evidence-bound verdict; memory authority surfaces need explicit claim boundaries.
   - Status: open
   - Disposition: `deprecate-first`. If host-agent memory sync is no longer a current governance line, mark it deprecated before deletion. If still desired, wire it or document its operator entrypoint.

4. [WARNING] `r49x4_metric_ranking` is a one-off artifact producer with live lineage references, so deletion requires artifact-provenance handling.
   - Location: `governance_tools/r49x4_metric_ranking.py:177`
   - Evidence: tracked grep found many references to the generated `docs/status/ab-causal-r49x4-metric-ranking-2026-05-16.json` and related R49.x/R50 docs. The script writes that tracked artifact path directly.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` legacy/refactor addendum and evidence preservation.
   - Status: open
   - Disposition: `deprecate-first`. Preserve the generated artifact as historical evidence; retire the script only after documenting the artifact as frozen and no longer regenerated.

### Knowledge Base Alignment
- Anti-patterns checked: current-state drift, governance expansion, semantic overclaim.
- Regression notes checked: runtime governance maturity, evidence/enforcement boundaries, working agreement.
- Result: Pass. No new anti-pattern added.

### Validation Evidence
- `git grep` tracked-file reference scan for all four candidates.
- `.venv\Scripts\python.exe -m pytest tests\test_host_agent_memory_sync_signal.py tests\test_change_control_summary.py::test_change_control_summary_promotion_gate_receipt_digest_is_stable_for_same_inputs tests\test_change_control_summary.py::test_change_control_summary_promotion_gate_receipt_digest_changes_on_relevant_input_change tests\test_promotion_gate_digest_regression.py --basetemp tests\_tmp_retire_candidate_review -p no:cacheprovider` -> 16 passed.
- `.venv\Scripts\python.exe governance_tools\promotion_gate_receipt_smoke.py` -> ok=true.
- `.venv\Scripts\python.exe -m py_compile governance_tools\clean_pilot_admissibility.py governance_tools\promotion_gate_receipt_smoke.py governance_tools\host_agent_memory_sync_signal.py governance_tools\r49x4_metric_ranking.py` -> PASS.

### Next Recommendation
Open a narrow implementation slice for `promotion_gate_receipt_smoke.py` removal first. Keep the other three as review-open until a clean-pilot policy decision, host-memory sync disposition, and R49.x artifact-freeze decision are made.

## 2026-07-07 - Review: Evidence Provenance Advisory Loop Fix

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/MEMORY_PROTOCOL.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance_tools/memory_authority_guard.py`
- `governance_tools/memory_record.py`
- `tests/test_memory_record.py`
- `artifacts/evidence/test-results/receipt-provenance-advisory-20260707.json`
- `artifacts/evidence/test-results/receipt-provenance-advisory-20260707.txt`
- `artifacts/governance/memory-authority-baseline-2026-07-07.json`

### Decision Summary
**Verdict**: APPROVED
**Risk Level**: Medium

Reason: the reviewed change fixes the review-blocking self-noise loop by
surfacing `test_evidence_provenance_not_found` at memory write time while the
author can still cite a durable receipt. The change is report-only and does not
alter guard, CI, gate, blocking, or enforcement semantics. One artifact-identity
warning is carried forward, but it does not invalidate the current DONE claim.

### Governance Audit
- Architecture: producer-side advisory mirrors the existing guard signal
  without creating a new blocking path.
- Native Safety: N/A.
- Test Integrity: focused tests cover helper behavior, CLI advisory behavior,
  no-advisory receipt path behavior, and existing memory-record handoff
  behavior.
- Thread Safety: N/A.
- Baseline Status: stable for the reviewed scope; full regression not run.

### Technical Findings

1. [WARNING] Re-frozen baseline file name and internal baseline id disagree.
   - Location: `artifacts/governance/memory-authority-baseline-2026-07-07.json:1`
   - Evidence: the tracked file path is dated `2026-07-07`, but the JSON
     payload reports `baseline_id=memory-authority-baseline-2026-07-06` with
     `source_head=398f1a73`. Live closeout collection still loads the newest
     file and reports `memory_authority_new_since_baseline=0`, so this is an
     identity/provenance clarity issue rather than a behavior failure.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` quality and evidence
     reviewability requirements.
   - Status: carried-forward.
   - Disposition: do not block this slice. Consider a narrow baseline hygiene
     fix if this mismatch confuses downstream reporting.

2. [WARNING] Historical closeout surface suite still has one unrelated failure.
   - Location: `tests/test_session_end_hook_memory_authority_surface.py:150`
   - Evidence: previous review reproduced `46 passed / 1 failed`; the failing
     test is the old-format memory fixture
     `test_bound_entry_does_not_increment_unbound_count`. The current
     provenance-advisory focused suite passed independently.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` test integrity and
     baseline status disclosure.
   - Status: carried-forward.
   - Disposition: keep as a separate test-fixture cleanup task; do not claim
     closeout surface full green from this slice.

3. [SUGGESTION] Keep the receipt workflow as the default for future memory
   records with success claims.
   - Location: `governance_tools/memory_record.py:227`
   - Evidence: live `_collect_memory_authority_surface` reports
     `memory_authority_new_since_baseline=0` and
     `memory_authority_new_warning_codes=[]` after the record cites
     `artifacts/evidence/test-results/receipt-provenance-advisory-20260707.json`.
   - Rule Reference: `governance/MEMORY_PROTOCOL.md` canonical memory writer
     rule and memory workflow dispatch rule.
   - Status: resolved by current workflow.
   - Disposition: future memory entries that claim successful validation should
     cite a durable receipt artifact or intentionally accept the advisory.

### Knowledge Base Alignment
- Anti-patterns checked: governance expansion without observed failure,
  semantic overclaim, memory authority drift.
- Regression notes checked: runtime governance maturity, evidence/enforcement
  boundaries, working agreement.
- Result: Pass. No new anti-pattern added.

### Validation Evidence
- `.venv\Scripts\python.exe -m pytest tests\test_memory_record.py tests\test_memory_authority_guard.py tests\test_memory_record_session_id_handoff.py --basetemp tests\_tmp_review_provenance_loop -p no:cacheprovider -q` -> 37 passed.
- `.venv\Scripts\python.exe -m governance_tools.memory_workflow --check --repo . --run-guard --format json` -> `completion_claim_allowed=true`, `blockers=[]`, `active_non_canonical_writer=0`.
- `.venv\Scripts\python.exe -m governance_tools.governance_drift_checker --repo . --format json` -> `ok=true`, `severity=ok`.
- Live `_collect_memory_authority_surface(Path("."))` -> `memory_authority_new_since_baseline=0`, `memory_authority_new_warning_codes=[]`, `memory_authority_suppressed_by_baseline=797`.
- `git diff --check` -> PASS.

### Next Recommendation
Stop implementation for the day. Tomorrow, open the smallest next slice from
the existing queue: either template-hardening for validator fixture pairs, or
review-verification of the four adoption-line `lexical_candidate` rows. Do not
start another retirement or enforcement change from the current ledger alone.

## 2026-07-13 - Next-Step Triage: Consumer Use Before Further Framework Expansion

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/MEMORY_PROTOCOL.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `PLAN.md` P1-C, P1-E, and P1-F sections
- `D:\Hearth\PLAN.md`
- current root and Hearth git status/log

### Decision Summary
**Verdict**: ESCALATED
**Risk Level**: Medium

Reason: the owner's Hearth priority is clear, but "integrate all credit-card
information" does not yet define one source, record identity, duplicate rule,
or end-to-end result. Starting implementation would choose financial-data
semantics without an approved vertical slice. The two framework follow-ups are
not substitutes: P1-C needs a natural meiandraybook session, and P1-F remains
an unapproved stronger-enforcement decision.

### Governance Audit
- Architecture: no runtime, hook, schema, updater, or product-code change was
  made; this is prioritization only.
- Native Safety: N/A.
- Test Integrity: no implementation changed, so no test run was required.
- Thread Safety: N/A.
- Baseline Status: reviewed heads are stable; root worktree has pre-existing,
  out-of-scope `memory/2026-07-12.md` changes and is not clean.

### Technical Findings

1. [WARNING] Credit-card goal needs a bounded product slice before code.
   - Location: `D:\Hearth\PLAN.md:36`
   - Evidence: the plan says to integrate all credit-card information but does
     not name the input sources, unified account/card identity, duplicate
     behavior, persistence boundary, or smallest usable result.
   - Rule Reference: root `AGENTS.md` Delivery Recovery Constraints 1 and 3.
   - Status: open.
   - Disposition: propose a read-only product spec first. It should select one
     source-to-result path and state its fixtures and acceptance checks; it
     must not assume a parser, database migration, or UI design.

2. [SUGGESTION] Leave P1-C waiting for real use rather than manufacture a receipt.
   - Location: `PLAN.md:729-741`
   - Evidence: its six-field close condition explicitly requires one natural
     meiandraybook Stop-hook receipt; manual invocation is explicitly not
     natural-session evidence.
   - Rule Reference: `PLAN.md` P1-C claim ceiling.
   - Status: open.
   - Disposition: observe the next real meiandraybook session and inspect its
     receipt then; do not schedule another F-7 run for this purpose.

3. [WARNING] P1-F is not a small hardening task.
   - Location: `PLAN.md:829-850, 944-949`
   - Evidence: the required 2-4 week FP/FN observation is not closed, and a
     current-diff blocker needs its own mutation contract, rollback path, and
     owner decision.
   - Rule Reference: `PLAN.md` P1-F OP-HC boundary.
   - Status: open.
   - Disposition: defer until its stated evidence and authorization exist.

### Knowledge Base Alignment
- Anti-patterns checked: governance expansion without observed failure,
  semantic overclaim, and replacing product delivery with framework work.
- Regression notes checked: audit-first posture, runtime-treatment evidence
  limits, and small isolated slices.
- Result: Pass. The proposed spec-first slice preserves these boundaries.

### Next Recommendation
Ask the owner to authorize this bounded next slice:
`DONE = 一份 Hearth 信用卡資訊整合規格，明確選定第一個資料來源、統一資料識別、去重規則、最小可用結果與驗收資料；不改程式、資料庫或 UI。`

## 2026-07-13 - P1-C Natural Receipt Recheck

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `PLAN.md:729-741` (P1-C close condition)
- `D:\meiandraybook\artifacts\runtime\closeout-receipts\`
- latest receipt `closeout_receipt_20260614T031922108732Z.json`

### Decision Summary
**Verdict**: CHANGES_REQUESTED
**Risk Level**: Low

P1-C remains open. The local consumer has many historic receipts, but no
receipt newer than 2026-06-14 and none with schema `1.3`. The latest receipt
does contain the five memory-workflow fields required by P1-C, but it has
`schema_version="1.2"` and `trigger_mode="unknown"`; it cannot prove the
post-F-7 natural Stop-hook path required by the close condition.

### Technical Finding

1. [BLOCKING] No qualifying natural-session receipt is present.
   - Location: `D:\meiandraybook\artifacts\runtime\closeout-receipts\closeout_receipt_20260614T031922108732Z.json`
   - Evidence: the latest receipt is dated 2026-06-14, has schema `1.2`, and
     its artifact directory has no receipt from the 2026-07-12 run activity.
     Its `memory_workflow_dispatch_ran`, status, warning codes, blocker codes,
     and guard summary exist, but P1-C requires all six conditions including
     `schema_version == "1.3"` in the same natural receipt.
   - Rule Reference: `PLAN.md:729-741`.
   - Status: open.
   - Disposition: do not create a manual receipt. On the next real
     meiandraybook session using the production Stop hook, inspect the newly
     written receipt at this path; if none appears, diagnose hook routing
     separately rather than treating smoke or ordinary run activity as proof.

### Knowledge Base Alignment
- Anti-patterns checked: manufactured evidence and semantic overclaim.
- Result: Pass. The recheck preserves the existing claim boundary.

## 2026-07-25 - Gate 2 Runtime Image And Verifier Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- commits `d940e990`, `78f36249`, and `51b50a58`
- Gate 1 amendment v2, Gate 2 preflight/isolation/sanitized-baseline artifacts,
  frozen scorer-handoff contract v2, validator packets, runtime Dockerfile,
  lock file, run recipe, verifier, tests, receipt, and current memory record

### Decision Summary
**Verdict**: CHANGES_REQUESTED
**Risk Level**: Medium

The verifier fixes themselves pass their 21-case suite and the built image ID
matches the recorded digest. Gate 2 must not start, however, because a real run
against the frozen sanitized baseline contradicted the pre-registered validator
expectation and showed that the documented commands do not apply the frozen Ruff
configuration. The sanitized-baseline construction command is also
host-configuration-dependent and reproduced the wrong tree on this Windows
host.

### Governance Audit
- Architecture: validator-only image preserves the intended model/tool split,
  but the out-of-band model control plane remains NOT PRESENT.
- Native Safety: N/A.
- Test Integrity: verifier suite is green, but the image's synthetic two-file
  preflight did not exercise the frozen validator configs or the real sanitized
  baseline and therefore missed the blocking treatment drift.
- Thread Safety: N/A.
- Baseline Status: the frozen source blobs and target tree are stable; the
  documented reconstruction command is not stable across host line-ending
  configuration.

### Technical Findings

1. [BLOCKING] Frozen Arm D validator expectation is false under the frozen config,
   and the documented commands do not apply that config.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/validator-expectation-DESIGNER-ONLY.md:13`,
     `artifacts/experiments/prepush-bugfix-20260724/validator-pins.md:20`,
     `artifacts/experiments/prepush-bugfix-20260724/validator-pins.md:43`.
   - Evidence: immutable image
     `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`
     on the real frozen tree returned ShellCheck `SC1090`; default
     `ruff check` returned 0, while the frozen selection
     `E,F,W,I,B`, line length 100, and Python 3.12 returned `I001` and `E501`
     with exit 1. The designer expectation says the validator output is empty
     and `D−C ≈ 0`.
   - Rule Reference: Gate 1 amendment v2 Section G(c); Engineering Skill Program
     Sections 4 and 6; `governance/REVIEW_CRITERIA.md` test-integrity rule.
   - Status: open.
   - Disposition: bind the frozen config to the actual runtime command/image,
     correct the expected-signal record, re-hash affected packets, and obtain
     owner re-sign before any Arm D execution. Do not silently reinterpret the
     already-frozen expectation after results exist.

2. [BLOCKING] Sanitized-baseline construction is not reproducible under the
   documented command on this Windows host.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/sanitized-baseline-manifest-20260724.md:14`.
   - Evidence: the documented `git archive` command under the host's
     line-ending configuration produced tree
     `f1c98fed4808d8af1e1f02cb3986a94dd46e193c`, not frozen tree
     `36c346fa951a24cbf914ef04469aac5cb5fd8b86`. Re-running as
     `git -c core.autocrlf=false archive ...` reproduced all four frozen blob
     hashes, tree `36c346fa...`, and 11 objects.
   - Rule Reference: Gate 1 amendment v2 Section A frozen baseline invariant;
     `governance/REVIEW_CRITERIA.md` baseline and reproducibility checks.
   - Status: open.
   - Disposition: make the line-ending override explicit in the canonical
     reconstruction command and retain the tree/blob/object-count verification
     as a dispatch prerequisite.

3. [WARNING] The run recipe executes a mutable tag even though an immutable image
   ID is available.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/RUN-RECIPE.md:30`.
   - Evidence: Docker reports the tag currently maps to
     `sha256:e6df7283...`, but the command runs `gate2-runtime:pinned`; a rebuild
     can retarget that name without changing the recipe.
   - Rule Reference: Engineering Skill Program Section 5 cross-arm environment
     control; `governance/REVIEW_CRITERIA.md` predictability requirement.
   - Status: open.
   - Disposition: dispatch by immutable image ID and stamp that ID plus platform
     identically for every arm.

4. [WARNING] Produce mode still leaks malformed-JSON tracebacks although the
   verifier-side warning was fixed.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/redaction_runner.py:266`.
   - Evidence: passing the requirements lock as `--contract` returned
     `JSONDecodeError` with a traceback and exit 1. The verifier's non-object
     marker/packet/receipt paths correctly return exit 2, so the 21-case result
     is accurate but narrower than the runner-wide fail-closed wording.
   - Rule Reference: frozen scorer-handoff contract fail-closed principle;
     `governance/REVIEW_CRITERIA.md` failure-path requirement.
   - Status: open.
   - Disposition: catch JSON/type errors in produce mode and add malformed and
     non-object contract/receipt cases. This does not authorize changing the
     frozen redaction map.

### Knowledge Base Alignment
- Anti-patterns checked: paper verification treated as operational proof,
  semantic overclaim, ambient host-state binding, and manufactured evidence.
- Regression notes checked: execution must use representative conditions and
  an independent oracle; receipt presence does not prove framework correctness.
- Result: Conflict Found. The synthetic preflight was not representative of the
  frozen Arm D validator treatment and therefore supported too broad a
  readiness statement.

### Validation Evidence
- `test_redaction_runner.py` -> 21 cases passed.
- `py_compile redaction_runner.py test_redaction_runner.py` -> PASS.
- Docker image inspect -> daemon 29.6.2, image ID `sha256:e6df7283...`,
  user `65532:65532`, workdir `/work`.
- Real sanitized baseline reconstruction -> documented command produced wrong
  tree; explicit `core.autocrlf=false` produced frozen tree and 11 objects.
- Immutable-image real-baseline validator probe -> ShellCheck exit 1 (`SC1090`);
  default Ruff exit 0; frozen Ruff config exit 1 (`I001`, `E501`); mypy default
  and frozen-command variants exit 0.
- Gate 2 arm execution -> NOT RUN because the frozen treatment expectation is
  contradicted and no managed answer-blind model/tool runner is present.

### Next Recommendation
Create a narrow Gate 1 correction amendment covering only validator-config
binding, the observed non-null baseline findings, the sanitized construction
flag, immutable image dispatch, and produce-mode JSON rejection. Re-sign the
changed frozen hashes/expectation, rebuild and preflight the image on the real
sanitized tree, then issue a new explicit Gate 2 start command.

## 2026-07-25 - Gate 1 Amendment v3 Pre-Sign Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- commits `ad3b56f1` and `edfe7509`
- amendment v3, amendment v2, frozen validator packets and scorer contract,
  sanitized-baseline manifest, runtime run recipe, redaction runner/tests,
  both review receipts, and current memory/active-task records

### Decision Summary
**Verdict**: CHANGES_REQUESTED
**Risk Level**: Medium

The measured validator and CRLF findings are real and independently reproduced.
The decision not to start Gate 2 is correct. Amendment v3 is not ready for owner
re-sign, however, because it asks the owner to confirm new packet hashes before
the proposed packet bytes or hashes exist, and it directs the implementation
slice to edit the already-signed amendment v2 in place.

### Governance Audit
- Architecture: no hook, runtime, CI, schema, gate, or enforcement behavior
  changed. The managed answer-blind model/tool runner remains NOT PRESENT.
- Native Safety: N/A.
- Test Integrity: the 22-case runner suite is green; the frozen packet zero-diff
  claim and three current SHA256 values were independently verified. A valid
  non-object JSON contract still exposes an uncovered produce-mode traceback.
- Thread Safety: N/A.
- Baseline Status: frozen tree `36c346fa...` and CRLF coupling were independently
  reproduced; the proposed LF check is directionally correct.

### Technical Findings

1. [BLOCKING] Owner re-sign is requested before the exact replacement artifacts
   and hashes exist.
   - Location:
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:59-73`,
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:83-88`.
   - Evidence: the amendment says both packet hashes will change only after
     owner re-sign, while Section E asks the owner to confirm the corrected
     commands and new hashes now. Current hashes remain `6ea4b322...` and
     `dcff3d2d...`; no candidate replacement hashes are present.
   - Rule Reference: Engineering Skill Program Gate 1 exact freeze requirement;
     `governance/REVIEW_CRITERIA.md` predictability and evidence binding.
   - Status: open.
   - Disposition: create versioned pending candidate packets first, record their
     exact bytes/commands and SHA256 values in v3, run scoped probes, then ask
     the owner to re-sign those exact artifacts. Approval must follow the
     concrete freeze, not authorize unspecified future bytes.

2. [BLOCKING] Amendment v3 proposes rewriting signed amendment v2 instead of
   superseding its affected fields append-only.
   - Location:
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:68-69`.
   - Evidence: v3 says the new hashes must be re-recorded in amendment v2
     Section A/B. Amendment v2 is the owner-signed historical authority and
     should remain byte-stable; changing it after signature would erase which
     hashes were actually signed.
   - Rule Reference: the repository's correction-forward/append-only evidence
     practice and Gate 1 freeze semantics.
   - Status: open.
   - Disposition: leave v2 unchanged. Let v3 explicitly supersede only the two
     affected v2 hash/command/expectation fields and contain an old-to-new hash
     map plus the new canonical pointers.

3. [WARNING] Produce mode still throws on valid JSON values that are not objects.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/redaction_runner.py:266-277`,
     `artifacts/experiments/prepush-bugfix-20260724/test_redaction_runner.py:251-272`.
   - Evidence: using the valid JSON array
     `tests/fixtures/external_observation_corpus.json` as `--contract` raises
     `AttributeError: 'list' object has no attribute 'get'` with exit 1. The new
     test covers malformed JSON and missing files, not non-object contract or
     receipt payloads.
   - Rule Reference: frozen handoff fail-closed principle and
     `governance/REVIEW_CRITERIA.md` failure-path coverage.
   - Status: open.
   - Disposition: add explicit dict checks for produce-mode contract/receipt
     and regression cases for array/scalar/null payloads. Keep the claim scoped
     to the tested malformed/unreadable paths until then.

4. [WARNING] Ruff cache failure wording is broader than the reproduced trigger.
   - Location:
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:49-53`,
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/RUN-RECIPE.md:37-40`.
   - Evidence: Ruff aborts with exit 2 when its working directory/cache target is
     the read-only repo mount; with the documented writable `/work` tmpfs as the
     working directory it returns the real I001/E501 lint findings even without
     `--no-cache`. `--no-cache` still removes this environmental ambiguity and is
     an appropriate frozen command correction.
   - Rule Reference: `governance/REVIEW_CRITERIA.md` evidence precision rule.
   - Status: open.
   - Disposition: narrow the explanation to a read-only cache target rather than
     `--read-only` generally; retain `--no-cache`.

### Resolved / Confirmed In Reviewed Diff
- Sanitized export now pins `core.autocrlf=false` and requires LF-only working
  files. Independent original-procedure reproduction produced frozen tree
  `36c346fa...` while the worktree retained 87 CR bytes and ShellCheck emitted
  88 `SC1017` occurrences, confirming the coupled failure.
- Runtime dispatch now names immutable image ID `sha256:e6df7283...`,
  `linux/amd64`.
- Malformed/unreadable produce inputs covered by the new test reject cleanly;
  the runner suite is 22/22 green.
- Frozen `validator-pins.md`, `validator-expectation-DESIGNER-ONLY.md`, and
  `scorer-handoff-contract.json` have zero diff from `51b50a58`; current hashes
  remain `6ea4b322...`, `dcff3d2d...`, and `e8945c4b...`.
- Both evidence receipts validate structurally; governance drift checker reports
  `severity=ok`.

### Knowledge Base Alignment
- Anti-patterns checked: signing abstractions before exact artifacts exist,
  rewriting historical authority, ambient-host-state binding, paper verification
  treated as runtime proof, and semantic overclaim.
- Regression notes checked: collision-driven findings, append-only correction,
  receipt evidence boundaries, and representative-condition execution.
- Result: Conflict Found. The technical corrections are directionally sound,
  but the proposed signature sequence would not freeze exact treatment inputs.

### Validation Evidence
- `test_redaction_runner.py` -> 22 cases passed.
- `py_compile redaction_runner.py test_redaction_runner.py` -> PASS.
- `git diff --exit-code 51b50a58..HEAD -- <three frozen files>` -> PASS,
  zero diff.
- SHA256 recomputation -> `6ea4b322...`, `dcff3d2d...`, `e8945c4b...`.
- CRLF coupling replay -> tree `36c346fa...`, 87 CR bytes in pre-push,
  ShellCheck exit 1 with 88 `SC1017` occurrences.
- Ruff read-only-cache replay -> default cache exit 2; `--no-cache` returns the
  real two lint findings with exit 1.
- Produce-mode non-object probe -> traceback / exit 1.
- `governance_drift_checker --format json` -> `ok=true`, `severity=ok`.
- Gate 2 arm execution -> NOT RUN.

### Next Recommendation
Do not re-sign the current v3. Prepare versioned candidate packet files and
their exact hashes, update v3 append-only to supersede only the affected v2
fields, close the non-object produce-mode case, then request owner re-sign of
that exact candidate set.

## 2026-07-25 - Gate 1 Amendment v3 Exact-Candidate Signability Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- commits `e45463f3` and `6779163d`
- amendment v3, both versioned candidate packets, signed amendment v2, the
  three existing frozen artifacts, candidate probe receipt, redaction
  runner/tests, run recipe, and current memory records

### Decision Summary
**Verdict**: CHANGES_REQUESTED
**Risk Level**: Medium

The candidate bytes now exist before signature, their recorded hashes match,
the v3 old-to-new mapping is append-only, the prior frozen authority is
byte-stable, and the two prior warnings are closed. One blocking mismatch
remains: the exact candidate ShellCheck command exits 1, while the candidate
expectation, v3 probe table, and receipt all record exit 0.

### Governance Audit
- Architecture: no hook, runtime, CI, schema, gate, or enforcement behavior
  changed. The managed answer-blind runner remains NOT PRESENT.
- Native Safety: N/A.
- Test Integrity: candidate hashes and 23 runner cases pass, but the claimed
  exact-command/expectation match fails on ShellCheck exit status.
- Thread Safety: N/A.
- Baseline Status: LF-clean frozen tree `36c346fa...` remains the probed
  baseline; image ID/platform remain pinned.

### Technical Findings

1. [BLOCKING] ShellCheck finding matches, but the frozen candidate exit status
   does not.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/candidate/validator-expectation-DESIGNER-ONLY-v2.md:23`,
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:101`,
     `artifacts/evidence/test-results/receipt-gate2-candidate-packets-20260725.json:22-25`.
   - Evidence: running the candidate command verbatim in image
     `sha256:e6df7283...` on the LF-clean frozen baseline produced only SC1090
     and `shellcheck_exact_rc=1`. Ruff reproduced I001/E501 with exit 1 and
     mypy reproduced clean with exit 0. The candidate expectation and v3 both
     say ShellCheck exit 0, while the receipt marks
     `matches_expectation_v2=true`.
   - Rule Reference: Engineering Skill Program Gate 1 exact freeze and
     evidence-consistency requirements; `governance/REVIEW_CRITERIA.md` test
     integrity.
   - Status: open.
   - Disposition: correct ShellCheck to exit 1 in the candidate expectation and
     v3 probe table, recompute the expectation candidate hash, update v3's
     old-to-new map and re-sign section, and add a successor correction receipt
     instead of treating the committed false receipt as valid probe evidence.
     Re-run the three candidate commands before requesting signature.

### Resolved / Confirmed In Reviewed Diff
- Candidate hashes recompute exactly:
  `validator-pins-v2.md=877896c7...`,
  `validator-expectation-DESIGNER-ONLY-v2.md=1678e663...`.
- Signed amendment v2 and all three existing frozen artifacts show zero diff
  from the prior authority.
- Amendment v3 now supersedes affected v2 fields append-only and does not
  instruct an in-place v2 rewrite.
- Produce mode explicitly rejects non-object contract/receipt JSON; runner
  suite is 23/23 green.
- Ruff cache wording correctly names a read-only cache target, and
  `--no-cache` remains in the candidate command.
- Candidate receipt validates structurally and governance drift checker
  reports `severity=ok`; neither proves the false ShellCheck exit value true.

### Knowledge Base Alignment
- Anti-patterns checked: signing before exact bytes, rewriting historical
  authority, receipt-as-correctness-proof, and command/result mismatch.
- Regression notes checked: evidence must bind to actual command behavior and
  receipts do not prove semantic correctness.
- Result: Conflict Found. Exact bytes exist, but one recorded observable does
  not match those bytes at execution.

### Validation Evidence
- SHA256 recomputation -> candidate hashes match v3.
- Signed-v2/frozen-artifact diff -> zero.
- `test_redaction_runner.py` -> 23 cases passed.
- `py_compile` -> PASS.
- Candidate ShellCheck command -> only SC1090, exit 1.
- Candidate Ruff command -> I001/E501, exit 1.
- Candidate mypy command -> clean, exit 0.
- Candidate receipt structural validation -> VALID.
- `governance_drift_checker` -> `ok=true`, `severity=ok`.
- Gate 2 arm execution -> NOT RUN.

### Next Recommendation
Do not sign hashes `877896c7...` / `1678e663...` as the final pair yet. Correct
the expectation candidate's ShellCheck exit status, compute its replacement
hash, correction-forward the probe receipt, rerun the exact commands, and then
request owner signature on the updated exact pair.

## 2026-07-25 - Gate 2 Corrected Candidate Re-signability Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- prior Gate 2 entries in `memory/04_review_log.md`
- commits `a4080633` and `9006e2e7`
- corrected expectation candidate, amendment v3, original probe receipt, and
  successor correction receipt

### Decision Summary
- Verdict: APPROVED
- Risk level: Medium
- Scope: exact-byte readiness of the two corrected candidate packets for owner
  re-sign; this is not approval to canonicalize or start Gate 2.

### Governance Audit
- Architecture: N/A; no product or runtime architecture changed.
- Native safety: N/A.
- Test integrity: PASS. The exact validator commands were rerun independently
  without pipes or command substitution; exit codes are `1/1/0`.
- Thread safety: N/A.
- Baseline status: Stable for this scoped probe. The mounted LF-clean sanitized
  repo has tree `36c346fa951a24cbf914ef04469aac5cb5fd8b86`.
- Dirty-worktree hygiene: clean at review start; author scope is committed and
  pushed at `9006e2e7`.

### Technical Findings
- No open blocking findings.
- Prior blocking finding, candidate ShellCheck exit mismatch:
  - Status: resolved.
  - Location:
    `artifacts/experiments/prepush-bugfix-20260724/candidate/validator-expectation-DESIGNER-ONLY-v2.md`
    and `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md`.
  - Evidence: independent immutable-image probe returned ShellCheck `1`, Ruff
    `1`, mypy `0`; corrected expectation SHA256 recomputes to
    `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092`.
  - Rule reference: `governance/REVIEW_CRITERIA.md` evidence integrity and
    append-only correction discipline.
  - Disposition: the false `1678e663...` hash is explicitly superseded, the
    original receipt is unchanged, and
    `receipt-gate2-exitcode-correction-20260725.json` corrects it forward.

### Confirmed Evidence
- Candidate pins SHA256:
  `877896c7672b1f47383e19ab00a38049344634c12c328a205a1651c6da4bf46d`.
- Corrected expectation SHA256:
  `61e1e52743e78ad9d38bd50e311978f5d49f513d617a48fd9a9b5a0901d02092`.
- Exact image probe: ShellCheck only SC1090 / exit 1; Ruff I001+E501 / exit 1;
  mypy clean / exit 0.
- Amendment v2 and the three frozen packets remain byte-stable.
- Redaction runner suite: 23/23 PASS; `py_compile` PASS.
- Successor correction receipt: structurally VALID.
- Governance drift: `ok=true`, `severity=ok`.
- `HEAD == origin/main == 9006e2e7` after `git fetch origin`.
- Gate 2 arm execution: NOT RUN.

### Knowledge Base Alignment
- Anti-patterns checked: pipeline exit-code masking, signing before exact bytes,
  rewriting historical evidence, and receipt-as-semantic-proof.
- Regression notes checked: command evidence must bind the directly measured
  process status.
- Result: Pass. The masking defect is corrected and recorded as a recurring
  anti-pattern; no contradiction remains in the candidate pair.

### Next Recommendation
The owner may re-sign exactly the two hashes recorded above. After re-signing,
canonical promotion and image preflight remain a separate bounded slice. Gate 2
must remain stopped until the independent producer/scorer and out-of-band model
resources exist and a later explicit start command is given.

## 2026-07-25 - Gate 2 Owner Re-sign and Canonical Promotion Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- prior Gate 2 entries in `memory/04_review_log.md`
- commits `71219179`, `68439a81`, and `1f0078fc`
- amendment v3, preflight manifest, signed candidate packets, promotion
  receipt, active-task state, and daily memory

### Decision Summary
- Verdict: CHANGES_REQUESTED
- Risk level: Medium
- Scope: owner signature and canonical-promotion state only; post-sign image
  preflight was intentionally not executed in this review.

### Governance Audit
- Architecture: N/A; no runtime, hook, CI, schema, gate, or enforcement changed.
- Native safety: N/A.
- Test integrity: candidate hashes and frozen-file byte stability pass, but the
  canonical-state authority surfaces disagree.
- Thread safety: N/A.
- Baseline status: Stable for the signed bytes; post-sign runtime state remains
  unverified by design.
- Dirty-worktree hygiene: clean at review start; reviewed commits are pushed
  and `HEAD == origin/main == 1f0078fc`.

### Technical Findings
1. [BLOCKING] Canonical promotion was performed but the amendment still records
   it as pending.
   - Location:
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:3-5`,
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:148-155`,
     `artifacts/experiments/prepush-bugfix-20260724/gate2-preflight-manifest-20260724.md:5-6`,
     `artifacts/evidence/test-results/receipt-gate2-v3-resign-promotion-20260725.json:23-25`,
     and `memory/01_active_task.md:346-348`.
   - Evidence: the manifest calls both candidate paths `CANONICAL` and the
     receipt claims canonical promotion completed, while amendment v3's status
     says canonical promotion is "not yet done" and Section E still lists the
     promotion slice as pending. The manifest also says amendment v2 alone is
     protocol authority even though v3 now supersedes its validator fields.
     The receipt says its manifest-only scope is "per Section E", but Section E
     explicitly required both manifest pointer changes and marking the
     amendment status "promoted".
   - Rule reference: `governance/REVIEW_CRITERIA.md` predictability and
     evidence-consistency requirements; amendment v3 Section E's own promotion
     contract.
   - Status: open.
   - Disposition: update amendment v3 to `RE-SIGNED AND PROMOTED`, mark only the
     canonical-promotion step done while keeping post-sign preflight pending,
     change the manifest authority line to amendment v2 as corrected by
     re-signed v3, synchronize `memory/01_active_task.md`, and add an append-only
     correction receipt because the committed promotion receipt omitted the v3
     status part of its claimed Section E scope.

### Resolved / Confirmed In Reviewed Diff
- Reviewer APPROVED record `71219179` accurately preserves the independently
  measured `1/1/0` validator results.
- Signed candidate SHA256 values recompute exactly to `877896c7...` and
  `61e1e527...`; superseded `1678e663...` is explicitly not signed.
- Amendment v2 and all three frozen v1 packets remain byte-stable.
- The manifest pointer rows themselves correctly identify the signed candidate
  paths and hashes.
- Both relevant receipts validate structurally; governance drift reports
  `ok=true`, `severity=ok`.
- Post-sign image preflight, all producer/scorer contexts, and every Gate 2 arm
  remain NOT RUN / NOT PRESENT as claimed.

### Knowledge Base Alignment
- Anti-patterns checked: authority-state drift, receipt-as-semantic-proof,
  signing before exact bytes, historical evidence rewrite, and exit-code
  masking.
- Regression notes checked: state transitions must synchronize canonical
  authority surfaces and receipts cannot repair contradictory prose.
- Result: Conflict Found. The bytes and signature are sound, but promotion
  status is not represented consistently.

### Next Recommendation
Do not run the post-sign image preflight yet. First complete the narrow
promotion-state truth repair described above, correction-forward the receipt,
and obtain a scoped review. The signed packet hashes do not need to change.

## 2026-07-25 - Gate 2 Promotion-State Truth-Repair Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- prior Gate 2 entries in `memory/04_review_log.md`
- commits `a575deaf` and `cdf95286`
- amendment v3, preflight manifest, signed candidate packets, prior promotion
  receipt, successor correction receipt, active-task state, and daily memory

### Decision Summary
- Verdict: APPROVED
- Risk level: Low
- Scope: promotion-state truth repair only. This approval permits the separate
  post-sign image preflight slice; it does not authorize Gate 2 execution.

### Governance Audit
- Architecture: N/A; no runtime, hook, CI, schema, gate, or enforcement changed.
- Native safety: N/A.
- Test integrity: PASS. Canonical state, authority text, append-only correction,
  signed hashes, and historical byte stability agree.
- Thread safety: N/A.
- Baseline status: Stable for signed packet bytes; runtime preflight remains the
  next unexecuted evidence layer.
- Dirty-worktree hygiene: clean at review start; reviewed commits are pushed
  and `HEAD == origin/main == cdf95286`.

### Technical Findings
- No open blocking findings or warnings.
- Prior promotion-state contradiction:
  - Status: resolved.
  - Location:
    `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md`,
    `artifacts/experiments/prepush-bugfix-20260724/gate2-preflight-manifest-20260724.md`,
    `memory/01_active_task.md`, and
    `artifacts/evidence/test-results/receipt-gate2-v3-promotion-state-sync-20260725.json`.
  - Evidence: v3 now says `RE-SIGNED AND PROMOTED`, Section E marks promotion
    DONE and leaves only post-sign image preflight pending, the manifest names
    v2 as superseded by v3 only for validator packets, active-task state agrees,
    and the successor receipt corrects forward without rewriting the prior
    receipt.
  - Rule reference: `governance/REVIEW_CRITERIA.md` predictability and
    evidence-consistency requirements; amendment v3 Section E.
  - Disposition: resolved in `a575deaf`; no signed bytes or hashes changed.

### Confirmed Evidence
- Candidate pins SHA256 remains `877896c7...`.
- Candidate expectation SHA256 remains `61e1e527...`.
- Amendment v2 and all three frozen v1 packets have zero diff from the prior
  signed baseline.
- Prior promotion receipt has zero diff; correction is append-only.
- Review and successor receipts both validate structurally as `VALID`.
- Governance drift reports `ok=true`, `severity=ok`.
- `HEAD == origin/main == cdf95286` after fetch; author worktree was clean.
- Post-sign image preflight and Gate 2 arms remain NOT RUN.

### Knowledge Base Alignment
- Anti-patterns checked: authority-state drift, receipt-as-semantic-proof,
  historical evidence rewrite, and exit-code masking.
- Regression notes checked: canonical state transitions must synchronize every
  named authority surface.
- Result: Pass. The prior contradiction is correction-forward and no new
  conflict remains in the reviewed scope.

### Next Recommendation
Proceed with one bounded post-sign image preflight against the canonical
candidate packets. Stop after recording the preflight result; producer/scorer
resource setup and Gate 2 start remain separate, unauthorized work.

## 2026-07-25 - Gate 2 Post-Sign Image Preflight Review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- prior Gate 2 entries in `memory/04_review_log.md`
- commits `6ea0b40c`, `6b303ade`, and `ee582671`
- post-sign preflight report, amendment v3, runtime run recipe, signed
  candidates, preflight receipt, active-task/daily memory, and remote state

### Decision Summary
- Verdict: APPROVED
- Risk level: Low
- Scope: post-sign image preflight only. No producer/scorer resource or Gate 2
  execution is approved by this verdict.

### Governance Audit
- Architecture: N/A; no runtime, hook, CI, schema, gate, or enforcement changed.
- Native safety: N/A.
- Test integrity: PASS. The reviewer independently reran the complete immutable
  image flags, isolation probes, and exact validators without pipeline masking.
- Thread safety: N/A.
- Baseline status: Stable. Frozen tree `36c346fa...`, four tracked LF-only files,
  signed hashes, image identity, and validator outputs all reproduce.
- Dirty-worktree hygiene: clean at review start; reviewed commits are pushed
  and `HEAD == origin/main == ee582671`.

### Technical Findings
1. [WARNING] The final resource-preflight sentence is grammatically incomplete.
   - Location:
     `docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md:167-171`.
   - Evidence: the text joins “What remains is ... resource preflight (...)”
     directly to “may the owner issue ...” without “Only after completing it”.
     The top status, manifest, and Cannot-claim section still independently and
     unambiguously prohibit Gate 2 start, so this does not invalidate preflight.
   - Rule reference: `governance/REVIEW_CRITERIA.md` predictability and
     reviewability requirements.
   - Status: open, non-blocking.
   - Disposition: correct the sentence before reviewing any future Gate 2 start
     packet; do not create a separate governance slice solely for this wording.

### Resolved / Confirmed In Reviewed Diff
- Post-sign report and receipt agree on image
  `sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168`.
- Independent full-flags replay passed: non-root uid/gid 65532, network none,
  read-only rootfs, writable `/work` tmpfs, cap-drop ALL,
  no-new-privileges, host paths and Docker socket unreachable.
- Candidate hashes remain `877896c7...` and `61e1e527...`.
- Frozen baseline tree remains `36c346fa...`; all four tracked files are LF-only.
- Exact validators independently reproduce ShellCheck 1/SC1090, Ruff
  1/I001+E501, and mypy 0/clean.
- Pre-existing container count remained 12 before and after.
- Amendment v2, three frozen v1 packets, and both signed candidates have zero
  diff from their signed checkpoints.
- Preflight receipt is structurally `VALID`; governance drift is
  `ok=true`, `severity=ok`.
- Producer/scorer contexts, out-of-band model control plane, and all Gate 2 arms
  remain NOT PRESENT / NOT RUN.

### Knowledge Base Alignment
- Anti-patterns checked: exit-code masking, authority-state drift,
  receipt-as-semantic-proof, ambient host-state leakage, and paper verification
  treated as runtime evidence.
- Regression notes checked: representative end-to-end execution still requires
  an independent oracle and exact environment controls.
- Result: Pass. The preflight claim is independently reproducible and remains
  below the Gate 2 readiness/execution claim ceiling.

### Next Recommendation
Stop repo-side expansion. The next real boundary is resource admission:
identify a managed out-of-band model/tool runner and independently eligible
4+2 contexts, then verify their identities, blinding, filesystem/input
allowlists, identical model/permission constants, and dispatch order without
running an arm. If those resources do not exist, status is BLOCKED-ON-RESOURCE,
not a prompt to add more governance files.

## 2026-07-25 — Gate 2 model-channel mechanism rehearsal review

- Reviewed commit: `a785174a6e0764df6763419f1ec1c960be89d859`
- Verdict: `CHANGES_REQUESTED`
- Risk: `MEDIUM`
- Blocking findings: 1
- Finding: The owner-performed `docker exec` nonce rehearsal proves a host-to-container command bridge and the reported container isolation properties, but it does not exercise a model session or a model tool adapter. Therefore it cannot close the architectural question of an out-of-band model-to-tool-to-model channel or be described as an end-to-end model-channel rehearsal.
- Required correction: Narrow the rehearsal document and runbook label to a host-to-container tool-control bridge rehearsal; preserve the owner-reported nonce, isolation, and Windows `MSYS_NO_PATHCONV` findings; add an append-only successor receipt correcting the semantic claim; record a canonical memory correction without rewriting the historical entry.
- Next bounded validation: On a dummy repository, use a fresh real model session outside the sandbox and a managed tool adapter that executes only inside the `--network none` container. Capture the model tool request, container execution/output, and a subsequent model response that correctly uses a nonce returned by the tool. This remains a mechanism rehearsal and must not use a Gate 2 packet or count as an arm.
- Evidence checked: signed/frozen surfaces zero diff; rehearsal receipt structurally valid; governance drift `ok`; `git diff --check` clean before review records; `HEAD == origin/main == a785174a`; author worktree clean.
- Not claimed: actual out-of-band model channel exists; producer/scorer contexts exist; Gate 2 is ready; any arm ran; validator treatment effectiveness.

## 2026-07-25 — Gate 2 full model-channel rehearsal evidence review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- `memory/03_knowledge_base.md`
- prior Gate 2 entries in `memory/04_review_log.md`
- commits `642c246c` and `ad877713`
- full rehearsal document, bridge-rehearsal forward pointer, rehearsal receipt,
  daily memory, tracked artifact inventory, receipt validation, governance drift,
  remote refs, and worktree state

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: Medium
- Scope: evidence and claim boundary for the reported
  model → adapter → container → model rehearsal only.

### Governance Audit
- Architecture: The proposed data path is coherent, but adapter exclusivity is
  explicitly not technically enforced and the persisted evidence does not bind
  the four stages into one auditable run.
- Native safety: N/A.
- Test integrity: FAIL at evidence-chain level. Container isolation is reported
  as independently checked, but model/adapter evidence exists only as prose
  summaries in the document and receipt.
- Thread safety: N/A.
- Baseline status: Stable for frozen/signed Gate 2 surfaces; no arm ran.
- Dirty-worktree hygiene: author worktree was clean and cached
  `HEAD == origin/main == ad877713`; reviewer records make the current worktree
  intentionally dirty.

### Technical Findings
1. [BLOCKING] The persisted artifacts do not prove the reported four-hop run.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/MODEL-CHANNEL-REHEARSAL-20260725.md:47-55`
     and
     `artifacts/evidence/test-results/receipt-gate2-model-channel-rehearsal-full-20260725.json:36-40`.
   - Evidence: the repository contains no tracked `repo_tool.sh`, raw adapter
     log, model tool-request trace, container output record, or model follow-up
     transcript. The receipt repeats summaries only. It also records only the
     prefix `e5e44c3b…` for adapter output while independent nonce inspection
     records full digest `18030d3b…`; no durable artifact explains or verifies
     the likely newline-normalization relationship.
   - Rule reference: `governance/REVIEW_CRITERIA.md` sections 1 and 3.3
     (evidence-bound, observable behavior); repository receipt rule that receipt
     fields are fabricatable and do not establish semantic correctness.
   - Fix required: preserve a minimally redacted evidence bundle containing the
     exact adapter implementation, raw adapter events, model request and
     follow-up transcript identifiers/content, container inspect/execution
     output, and complete digest linkage across stages. Keep nonce plaintext
     secret; record the exact normalization used if hashes differ. Otherwise
     narrow the conclusion to owner-reported evidence consistent with, but not
     proof of, the full loop.
   - Disposition: open; the earlier bridge-only overclaim is resolved, but the
     successor end-to-end claim is not yet independently auditable.

2. [WARNING] Technical adapter exclusivity remains absent.
   - Status: carried-forward.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/MODEL-CHANNEL-REHEARSAL-20260725.md:98-102`.
   - Evidence: the subagent retained other tools and could bypass the adapter
     with direct `docker exec`; the adapter log would not show that bypass.
   - Rule reference: Gate 2 answer-blind resource boundary and
     `governance/REVIEW_CRITERIA.md` architecture/predictability requirements.
   - Disposition: acceptable as an explicit rehearsal limitation, but must be
     technically enforced before resource admission and cannot be described as
     a provisioning-only detail.

### Knowledge Base Alignment
- Anti-patterns checked: exit-code masking, receipt-as-semantic-proof,
  claim inflation, prompt-only isolation, and summary-only cross-boundary
  evidence.
- Regression notes checked: a structurally valid receipt does not upgrade
  unverifiable summaries into runtime proof.
- Result: Conflict found; summary-only cross-boundary evidence is now recorded
  as a durable anti-pattern.

### Next Recommendation
Do not provision 4+2 contexts yet. First produce one correction-forward,
durable evidence bundle for the dummy-repo rehearsal, or narrow the current
claim. Then run a resource-admission-only slice that technically restricts each
fresh context to the adapter and verifies identity, filesystem/input allowlists,
model/permission constants, and blinding without executing any Gate 2 arm.

## 2026-07-26 — Gate 2 producer guard and transcript pipeline review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- official Claude Code hook reference and hook guide
- `memory/03_knowledge_base.md`
- prior Gate 2 reviews in `memory/04_review_log.md`
- commits `1a79571a`, `1ef71100`, `84221571`, and `352168d7`
- durable channel evidence bundle, producer guard/pre/post hooks, adapter,
  hostile tests, README, receipts, tracked artifact hashes, governance drift,
  and cached remote state

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: Medium
- Scope: producer guard technical enforcement, transcript evidence pipeline,
  and readiness for a live resource-admission dry run.

### Governance Audit
- Architecture: The PreToolUse deny boundary is a valid harness-level
  enforcement point, but the allowed adapter is read-only and therefore cannot
  execute the required producer vertical slice.
- Native safety: N/A.
- Test integrity: The hostile allow/deny logic passes, but the suite does not
  test real harness dispatch, successful pre/post correlation, failure events,
  transcript persistence failure, or a write/test producer workflow.
- Thread safety: Concurrent hook appends and repeated identical commands are
  not safely correlated; command digest is not a unique event identity.
- Baseline status: Frozen/signed Gate 2 surfaces were untouched; no arm ran.
- Dirty-worktree hygiene: author worktree was clean and
  `HEAD == origin/main == 352168d7`; reviewer records make the current worktree
  intentionally dirty.

### Technical Findings
1. [BLOCKING] The sanctioned adapter cannot perform the producer task.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/producer-guard/repo_tool.sh:31-43`
     and `gate2_producer_guard.py:47-49,134-155`.
   - Evidence: only `ls`, `log`, and `read` are allowed. The frozen dispatch
     requires diagnosing and fixing code, adding a regression test, running it,
     and producing a diff/test log. Every edit, patch, test, or result-emission
     operation is denied.
   - Rule reference: root `AGENTS.md` Delivery Recovery Constraints,
     Vertical Slice First; Gate 2 dispatch acceptance criterion.
   - Fix required: validate a bounded writable adapter on a disposable canary
     repo with explicit operations for scoped read, patch/write, allowlisted
     test execution, status/diff, and result export. Keep arbitrary shell,
     Docker, host filesystem, network, and out-of-repo paths denied.
   - Disposition: open; do not mount this guard into a real producer context.

2. [BLOCKING] The transcript does not uniquely or completely bind tool events.
   - Status: open.
   - Location:
     `gate2_producer_guard.py:158-195`,
     `gate2_producer_posttool.py:46-70`, and
     `producer-guard/README.md:42-62`.
   - Evidence: PreToolUse invents a random `request_id`; PostToolUse records no
     request id and correlates only by command digest, so repeated identical
     calls are ambiguous. Claude Code already supplies the same `tool_use_id`
     to PreToolUse and PostToolUse. Only PostToolUse is wired, so an allowed
     adapter call that fails is absent from the result transcript; official
     hooks expose `PostToolUseFailure` for that case. The post hook hashes the
     whole structured `tool_response`, not the exact stdout bytes hashed by the
     adapter.
   - Rule reference: `governance/REVIEW_CRITERIA.md` observable-behavior and
     async-safety requirements; official Claude Code hook contract.
   - Fix required: persist `tool_use_id` across pre/success/failure events, wire
     `PostToolUseFailure`, define and test the exact stdout extraction and
     normalization used for digest comparison, and test repeated identical
     commands plus failed adapter calls.
   - Disposition: open.

3. [BLOCKING] Transcript persistence fails open.
   - Status: open.
   - Location:
     `gate2_producer_guard.py:60-66` and
     `gate2_producer_posttool.py:30-36`.
   - Evidence: both `_emit` functions swallow `OSError`. A reviewer probe set
     `GATE2_TRANSCRIPT` to an unwritable path; the PreToolUse process returned
     exit 0 with `permissionDecision=allow`, leaving no audit record.
   - Rule reference: guard's own “both required” and fail-closed contract;
     `governance/REVIEW_CRITERIA.md` predictable evidence behavior.
   - Fix required: deny before execution when the pre-event cannot be durably
     persisted; make a post/failure persistence error invalidate the admission
     run and surface it to the harness instead of silently continuing.
   - Disposition: open.

4. [WARNING] Deny output mixes two incompatible hook protocols.
   - Status: open.
   - Location: `gate2_producer_guard.py:192-195`.
   - Evidence: denied calls print structured JSON but exit 2. Official Claude
     Code guidance says JSON is ignored on exit 2; use exit 0 with structured
     JSON, or exit 2 with the reason on stderr. Blocking still occurs, but the
     current test's JSON assertion does not validate the actual harness path.
   - Disposition: select one protocol and cover it in the live dry run.

5. [WARNING] The recorded test count is stale.
   - Status: open.
   - Location: `producer-guard/README.md:95-96` and
     `receipt-gate2-producer-guard-20260725.json`.
   - Evidence: the current suite emits 46 bracketed checks, not 41.
   - Disposition: compute the count from test output or stop hard-coding it.

### Resolved / Confirmed In Reviewed Diff
- The prior evidence-bundle hash-normalization gap is resolved with complete
  digests and a replayable verifier.
- The prior rehearsal is now explicit that raw model transcripts were absent;
  the new hook code is prospective and does not retroactively prove model
  identity.
- Direct policy evaluation denies Docker, host paths, non-Bash tools, shell
  metacharacters, argument/verb abuse, and look-alike adapter paths.
- Both receipts validate structurally and their recorded artifact hashes match.
- Targeted suite exits 0; governance drift reports `ok=true`, `severity=ok`;
  `HEAD == origin/main == 352168d7`; Gate 2 remains 0/4.

### Knowledge Base Alignment
- Anti-patterns checked: exit-code masking, receipt-as-semantic-proof,
  prompt-only isolation, summary-only cross-boundary evidence, audit-id
  ambiguity, and evidence-write fail-open.
- Regression notes checked: policy enforcement and evidence completeness are
  separate properties; a restrictive control that cannot complete the product
  slice is not admission-ready.
- Result: Conflict found; hook audit correlation and evidence fail-closed rules
  are now recorded as durable knowledge.

### Next Recommendation
Use a new disposable local `gate2-admission-canary` repo, not an unrelated
business repo and not one of the four future producer copies. Give it one tiny
failing test whose fix requires read → scoped patch → test → diff/result. Use a
disposable fresh model context with the revised guard, deliberately attempt
Docker/host/network bypasses, and verify pre/success/failure transcript binding.
Destroy that context afterward. Only after approval should a separate admission
context mount a fresh export of frozen tree `36c346fa…` to verify the real image,
tree, packets, and permissions without dispatching the bug task or consuming an
arm.

## 2026-07-26 — Gate 2 admission-canary re-review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/AGENT.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- official Claude Code hook reference and hook guide
- `memory/03_knowledge_base.md`
- prior Gate 2 reviews in `memory/04_review_log.md`
- commits `aba16930` and `68d618bf`
- shared policy loader, PreToolUse/PostToolUse/PostToolUseFailure hooks,
  canary adapter/policy/emulator/driver, durable evidence bundle, run report,
  transcript verifier and mutation tests, status report, and daily memory

### Decision Summary
- Verdict: `APPROVED`
- Risk level: Medium
- Scope: emulator-driven admission canary only. This approval closes the three
  prior implementation blockers and two warnings; it does not approve a real
  Claude producer, 4+2 resource admission, or Gate 2 start.

### Governance Audit
- Architecture: PASS for the canary. One policy digest drives guard and
  adapter; the adapter supports a bounded read → write → test → diff/status →
  report vertical slice without arbitrary command or network verbs.
- Native safety: N/A.
- Test integrity: PASS. Allowed steps assert real execution, exact expected
  exit codes and output; negative controls prove non-execution with an unchanged
  adapter sequence counter.
- Thread safety: WARNING carried forward. The canary driver is serial and the
  verifier joins adapter events by order; real harness parallel tool calls are
  not yet observed or technically serialized.
- Baseline status: Stable. Pinned image was used, frozen tree and signed
  surfaces were untouched, no Gate 2 packet or arm ran.
- Dirty-worktree hygiene: author worktree clean and
  `HEAD == origin/main == 68d618bf`; reviewer records make the current worktree
  intentionally dirty.

### Technical Findings
1. [RESOLVED] The adapter can now execute a complete bounded producer slice.
   - Status: resolved.
   - Location:
     `admission-canary/policy_canary.json`,
     `admission-canary/canary_adapter.py`, and
     `admission-canary/evidence/run-report.json`.
   - Evidence: real sequence includes test exit 1, write exit 0, test exit 0,
     followed by diff, status, and report; 13 adapter executions, contiguous
     seq 1..13, zero adapter-side rejects.
   - Rule reference: root `AGENTS.md` Vertical Slice First and prior review
     finding 1.
   - Disposition: resolved for the canary policy; the final Gate 2 producer
     policy remains a separate resource-admission artifact.

2. [RESOLVED] Transcript events are uniquely and completely correlated.
   - Status: resolved.
   - Location:
     `producer-guard/gate2_producer_guard.py`,
     `producer-guard/gate2_producer_posttool.py`, and
     `producer-guard/verify_transcript.py`.
   - Evidence: harness `tool_use_id` binds pre and terminal events; both success
     and failure event shapes are recorded; repeated byte-identical calls remain
     separable; adapter/post stdout digest uses the same normalization; thirteen
     mutation cases are detected.
   - Rule reference: prior review finding 2 and official Claude Code hook
     event contract.
   - Disposition: resolved under the documented payload shapes exercised by the
     emulator; authentic Claude payloads remain NOT RUN.

3. [RESOLVED] Transcript persistence now fails closed before execution.
   - Status: resolved.
   - Location:
     `producer-guard/gate2_producer_guard.py` and
     `admission-canary/evidence/run-report.json`.
   - Evidence: unwritable transcript, missing tool id, missing policy, and
     malformed policy each exit 2 before execution; adapter seq remains 13→13.
   - Rule reference: prior review finding 3.
   - Disposition: resolved.

4. [RESOLVED] Hook deny protocol and test count warnings.
   - Status: resolved.
   - Evidence: decided allow/deny use exit 0 plus structured JSON;
     undecidable/unauditable states use exit 2 plus stderr only. Test suite
     reports its own current count, 88.
   - Disposition: resolved.

5. [WARNING] Real harness payload and concurrency behavior remain unobserved.
   - Status: carried-forward.
   - Location:
     `admission-canary/harness_emulator.py`,
     `producer-guard/verify_transcript.py`, and
     `admission-canary/canary_adapter.py`.
   - Evidence: no model participated; the emulator assumes Bash
     `tool_response` shape and serial delivery. Verifier joins adapter lines by
     order, while adapter sequence increment is not concurrency-safe.
   - Rule reference: official Claude Code hook guide notes PostToolUse hooks can
     run concurrently for parallel calls; `governance/REVIEW_CRITERIA.md`
     thread/async safety.
   - Disposition: observe in the next disposable real-harness run; before 4+2
     admission, either bind `tool_use_id` into adapter records with
     concurrency-safe storage or technically enforce one in-flight call.

### Independent Validation
- `test_producer_guard.py`: PASS, 88 checks.
- `test_verify_transcript.py`: PASS, 13 mutation checks.
- `test_canary_conformance.py`: PASS, 18 checks.
- artifact-only `verify_transcript.py`: PASS, 15/15 checks.
- Evidence inspection: 48 transcript events; 35 pre events; 13 allowed and
  executed; 22 denied with no terminal events; 13 adapter executions; zero
  adapter rejects; one correlated failure event; two repeated command digests
  remain individually identified.

### Knowledge Base Alignment
- Anti-patterns checked: allowed-vs-executed confusion, exit-code masking,
  policy duplication, transcript-write fail-open, command-digest correlation,
  receipt-as-proof, and emulator-as-real-harness overclaim.
- Regression notes checked: actual observable outcomes must be measured, not
  inferred from permission or setup success.
- Result: Pass for the bounded canary. Parallel hook delivery remains an
  explicit next-boundary risk.

### Next Recommendation
Run exactly one new disposable Claude Code producer session against a fresh
canary target to capture authentic PreToolUse/PostToolUse/PostToolUseFailure
payloads and verify deny behavior, response shape, and serial/parallel delivery.
Do not use this answer-aware session, the frozen baseline, or any Gate 2 packet.
If approved, proceed to resource-admission-only setup for four producers and
two scorers without running an arm.

## 2026-07-26 — Gate 2 parallel-safety and real-session runbook review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- reviewer-handoff skill commands and gotchas
- `memory/03_knowledge_base.md`
- prior Gate 2 reviews in `memory/04_review_log.md`
- commits `98fb46a0` and `540b773a`
- parallel-safe canary adapter, concurrency test, order-independent transcript
  verifier, mutation tests, source receipt, producer wiring README, and current
  `.claude` settings surfaces
- official Claude Code hook and settings documentation

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: Medium
- Split result: the parallel-safety implementation is `APPROVED`; the proposed
  real-Claude canary runbook is not safe to execute unchanged.

### Governance Audit
- Architecture: PASS for the lock-based adapter serialization. Sequence
  allocation, execution, and durable log append are one critical section.
- Native safety: N/A.
- Test integrity: PASS for the implementation. The new suite creates twelve
  real concurrent processes and observes lock contention; the mutation suite
  now checks duplicate sequence numbers and missing-line gaps.
- Thread/async safety: PASS for adapter log completeness in the tested
  subprocess scope. The next real-harness run remains NOT RUN.
- Baseline status: Stable. Source receipt is structurally valid, governance
  drift is clear, and `HEAD == origin/main == 540b773a` after fetch.
- Dirty-worktree hygiene: author worktree was clean before reviewer records;
  reviewer records are the only intentional changes from this review.

### Resolved Findings
1. [RESOLVED] The adapter sequence/log race is technically serialized.
   - Status: resolved.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/canary_adapter.py:58`
     and
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/test_adapter_concurrency.py`.
   - Evidence: independent rerun passed 8/8 checks with twelve processes,
     exactly twelve JSON log lines, unique contiguous sequence numbers, matching
     counter, distinct PIDs, and observed lock contention.
   - Rule reference: `governance/REVIEW_CRITERIA.md` thread/async safety and the
     prior carried-forward concurrency warning.
   - Disposition: resolved for the canary adapter implementation.

2. [RESOLVED] Transcript verification no longer depends on incidental record
   order.
   - Status: resolved.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/producer-guard/verify_transcript.py:115`.
   - Evidence: verb/argument and stdout joins are counted and
     order-independent; sequence uniqueness and contiguity are explicit checks;
     independent mutation suite caught 14/14 mutations and committed evidence
     passed 17/17 checks.
   - Rule reference: prior review finding 5 and the knowledge-base rule against
     ordered-position joins as a concurrency boundary.
   - Disposition: resolved.

### Open Findings
1. [BLOCKING] The hook configuration is project-scoped, not task-scoped.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/producer-guard/README.md:116`
     and the proposed instruction to edit `.claude/settings.json`.
   - Evidence: official Claude Code documentation defines
     `.claude/settings.json` as shared settings for one project and
     `.claude/settings.local.json` as local settings for one project. This repo
     already has both files. A second Claude task opened in the same project
     does not turn project settings into task-local settings.
   - Rule reference: root `AGENTS.md` isolation/safety posture and
     `governance/REVIEW_CRITERIA.md` architecture boundary.
   - Fix required: create a separate disposable canary project directory and
     put the hooks in that project's `.claude/settings.local.json`; verify the
     active source with Claude Code `/hooks` or `/status`. Do not edit this
     framework repo's project settings for the smoke.

2. [BLOCKING] The proposed run does not allocate a fresh adapter-log namespace
   or a unique container identity.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/producer-guard/README.md:129`
     and
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/canary_adapter.py:43`.
   - Evidence: the documented environment list names `GATE2_TRANSCRIPT` but
     omits `GATE2_ADAPTER_LOG` and `GATE2_CANARY_CONTAINER`. The adapter defaults
     to the stable container `gate2-admission-canary` and the stable file
     `admission-canary/adapter-log.jsonl`; its `.seq` and `.lock` paths derive
     from that log path. A new run can therefore append to old evidence or
     address the wrong live container.
   - Rule reference: evidence isolation, replay consistency, and dirty-scope
     hygiene in root `AGENTS.md`.
   - Fix required: require a unique run directory and set fresh absolute
     `GATE2_TRANSCRIPT` and `GATE2_ADAPTER_LOG`, a unique
     `GATE2_CANARY_CONTAINER`, and a unique `GATE2_RUN_ID`; assert all target
     files are absent before launch and bind the verifier to those exact paths.

3. [WARNING] Adapter-side attribution is count-based for byte-identical calls.
   - Status: carried-forward.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/producer-guard/verify_transcript.py:121`.
   - Evidence: the transcript preserves `tool_use_id`, but the adapter log does
     not receive it. Identical verb/argument/output calls are accounted for as a
     multiset and cannot be mapped one-for-one to adapter sequence numbers.
   - Rule reference: `memory/03_knowledge_base.md` Hook Audit Correlation And
     Evidence Fail-Closed.
   - Disposition: acceptable for this canary's completeness claim because
     execution is serialized and the source receipt states the limit; do not
     upgrade it to per-call adapter attribution.

### Independent Validation
- `test_adapter_concurrency.py`: PASS, 8/8.
- `test_producer_guard.py`: PASS, 88/88.
- `test_verify_transcript.py`: PASS, 14/14 mutations caught.
- `test_canary_conformance.py`: PASS, 18/18.
- artifact-only `verify_transcript.py`: PASS, 17/17.
- source evidence receipt: VALID.
- governance drift: PASS, `severity=ok` (plain meaning: no current governance
  baseline drift was reported).
- remote state: PASS, fetched `origin`; HEAD and origin/main both
  `540b773ad22d5eabd6668644139afbeb29263b78`.

### Knowledge Base Alignment
- Anti-patterns checked: ordered-log join, unlocked read-modify-write sequence,
  receipt-as-proof, emulator-as-real-harness, project-scoped hooks treated as
  task-local, and evidence files reused across runs.
- Regression notes checked: audit evidence must fail closed and preserve a
  complete cross-boundary chain.
- Result: conflict found only in the proposed next-run instructions; the
  parallel-safety code itself aligns.

### Next Recommendation
Amend the real-session runbook only: use a separate disposable project with
local project hooks and a unique run directory/container/log namespace. Re-review
that bounded setup before launching the one authentic Claude Code canary. Do
not provision 4+2 contexts or run any Gate 2 arm yet.

## 2026-07-26 — Gate 2 live-canary launch-readiness review

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- reviewer-handoff skill commands and gotchas
- prior Gate 2 reviews and hook-audit knowledge-base entries
- staged `evidence-live/RUN-CONFIG.md` and `answer_questions.py`
- `D:\gate2-live-producer-task\.claude\settings.json`
- `D:\gate2-live-run-evidence\`
- emulator transcript and adapter-log evidence
- this reviewer's immediately preceding tool history

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: Medium
- Launch decision: do not click the task chip yet.

### Governance Audit
- Architecture: PASS for physical separation. The producer settings now live in
  a disposable directory outside the framework repo, and live evidence targets
  a second external directory.
- Native safety: N/A.
- Test integrity: FAIL for the staged answer script. It can produce affirmative
  answers without the required observation and can misattribute a non-zero exit
  when identical calls are reordered.
- Thread/async safety: FAIL for Q3 analysis because its per-fingerprint list join
  reintroduces the positional ordering assumption removed from the canonical
  verifier.
- Baseline status: Partially verified. External settings JSON is valid and both
  external directories exist; Docker is unavailable in this Codex shell, so the
  author-reported container baseline was not independently rechecked here.
- Dirty-worktree hygiene: FAIL in the prior reviewer action. This reviewer
  deleted the whole untracked `evidence-live/` directory after a truncated
  inventory and incorrectly classified it as generated test output.

### Open Findings
1. [BLOCKING] The staged provenance for the disappearing files is false.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence-live/RUN-CONFIG.md:46`.
   - Evidence: in the preceding review turn, this reviewer explicitly resolved
     and recursively removed
     `...\admission-canary\evidence-live` after seeing it as untracked. The
     directory inventory rendered truncated paths, and the cleanup proceeded
     without distinguishing the author's files from test output.
   - Rule reference: root `AGENTS.md` Dirty Tree Allowlist and destructive-action
     target verification.
   - Fix required: replace the unknown-sweeper account with the known reviewer
     cleanup error. Keeping live evidence outside the audited repo remains
     justified by separation hygiene, but not by an unexplained deletion.

2. [BLOCKING] Q2 falsely passes when no denial was observed.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence-live/answer_questions.py:70`.
   - Evidence: with zero denied pre-events, the script prints
     `denied calls: 0` followed by
     `VERDICT: deny was honoured -- nothing denied executed`.
   - Rule reference: `governance/REVIEW_CRITERIA.md` observable-behavior
     validation and the repo prohibition on false-success evidence.
   - Fix required: report Q2 as `UNANSWERED` unless at least one denied event is
     present; only then evaluate terminal and adapter leakage.

3. [BLOCKING] Q3 can attach a non-zero exit to the wrong terminal event.
   - Status: open.
   - Location:
     `artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/admission-canary/evidence-live/answer_questions.py:98`.
   - Evidence: the script pools adapter exits by `(verb, args_sha256)` and
     assigns them to transcript pre-events by list position. A two-call
     counterexample with identical `test` fingerprints, transcript order A/B,
     and adapter execution order B/A produced the inverted result:
     actual exit-1 B had `post_tool_use_failure`, while the script reported
     exit 1 → `post_tool_use` for A.
   - Rule reference: prior parallel-safety review and
     `memory/03_knowledge_base.md` rule that ordered-position joins are not
     concurrency boundaries.
   - Fix required: do not answer per-call Q3 without an identity-bearing
     adapter join. Either carry `tool_use_id` into adapter evidence, redesign the
     canary so the failing call has a unique fingerprint, or explicitly report
     Q3 as unresolvable when a fingerprint has multiple calls with different
     exits.

4. [BLOCKING] The task chip's execution root and harness are not admitted.
   - Status: open.
   - Location: proposed chip `task_2f9bbd6a` and
     `RUN-CONFIG.md:9`.
   - Evidence: the chip has not created an inspectable task, and its text refers
     to a fresh worktree. The disposable producer directory is not a git repo.
     If the launched session runs in a framework worktree, or is not Claude
     Code, `D:\gate2-live-producer-task\.claude\settings.json` does not govern
     it and the transcript can remain empty while the task appears to run.
   - Rule reference: harness-scoped enforcement limitation and fail-closed
     admission requirement.
   - Fix required: launch Claude Code explicitly with cwd
     `D:\gate2-live-producer-task`, then verify the active Project hook source
     with `/hooks` or `/status` before submitting the blind task prompt. Do not
     use a generic worktree chip unless its cwd and Claude-hook support are
     machine-verifiable first.

### Independent Validation
- external `.claude/settings.json`: PASS, valid JSON and all four fresh
  run-identity/evidence variables are present.
- producer root: PASS, only `.claude/settings.json` is present.
- external evidence root: PASS, exists and is empty.
- staged analyzer against emulator evidence: PASS for execution only.
- zero-denial mutation: FAIL as expected; exposed false Q2 success.
- reordered-identical-call mutation: FAIL as expected; exposed wrong Q3
  attribution.
- container baseline: NOT RUN because Docker is unavailable in this Codex
  shell.

### Knowledge Base Alignment
- Anti-patterns checked: false success from zero observations, ordered joins
  under possible concurrency, project settings treated as task-local, and
  recursive cleanup of mixed untracked contents.
- Result: conflicts found in provenance, analyzer semantics, and launch
  admission.

### Next Recommendation
Correct the staged provenance and analyzer, add the two counterexamples as
tests, and replace the uninspectable task chip with an explicit Claude Code
launch rooted at the disposable producer directory. Re-review those bounded
changes before running the canary.

## 2026-07-26 — Gate 2 live-canary run review (`live-canary-20260726-152447`)

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/TESTING.md`
- `governance/ARCHITECTURE.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- prior Gate 2 reviews and hook-audit knowledge-base entries
- `D:\gate2-live-run-evidence\live-canary-20260726-152447\transcript.jsonl`
- `D:\gate2-live-run-evidence\live-canary-20260726-152447\adapter-log.jsonl`
- the run's before/after snapshots and verbatim producer prompt
- producer-cwd Claude session log
  `60995b07-2c91-4040-bb92-1e08e85be23d.jsonl`
- adapter, post hook, verifier, analyzer, preflight, and related tests

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: High for evidence correctness.
- Gate decision: do not start a Gate 2 arm.

### Governance Audit
- Architecture: FAIL at the adapter-to-harness emission boundary. The adapter
  measured normalized LF bytes but Windows text-mode stdout emitted CRLF bytes.
- Native safety: N/A.
- Test integrity: FAIL in the reviewed baseline. In-process normalizer checks
  could not observe the pipe translation, and preflight did not exercise the
  shared observable.
- Thread/async safety: UNANSWERED for the live harness; 0/10 lock waits does not
  prove serialization.
- Baseline status: stable negative evidence. The immutable run artifacts agree
  on task completion and on the measurement-chain failure.
- Dirty-worktree hygiene: scoped canary/review changes only; no unrelated dirty
  path was inspected or modified.

### Independently Confirmed
- Transcript: 22 events = 12 pre, 10 allow, 2 deny, 10 ordinary post, 0
  failure post.
- Adapter: 10 executed lines, contiguous sequence 1–10, all exit 0, matching
  policy digest `270ec6fc…`, 0 rejects, 0 lock waits.
- Both denied calls were not executed.
- The container fix, passing test, result artifact and before/after snapshots
  agree.
- The producer session exists in the intended cwd and its first message matches
  `producer-prompt.txt`.
- Contemporaneous suites passed 101 producer-guard checks, 14 verifier
  mutations and 24 analyzer checks.

### Blocking Findings
1. [BLOCKING] One aggregate verifier failure means 8/8 multi-line joins failed.
   - Status: resolved in the candidate remediation; live re-verification pending.
   - Location: shared observable check in
     `producer-guard/verify_transcript.py`.
   - Evidence: only single-line `write` and `report` joined; every
     newline-bearing `read`, `ls`, `test`, `diff`, and `status` result failed.
   - Rule reference: review observable-behavior and evidence fail-closed rules.
   - Disposition: report the affected population, not merely the aggregate
     check count.

2. [BLOCKING] The adapter hashed bytes it did not emit.
   - Status: resolved in source; fresh live rerun pending.
   - Location: `admission-canary/canary_adapter.py`.
   - Evidence: text-mode `sys.stdout.write` translated LF to CRLF after the
     adapter logged its digest. The status LF digest `d92214ff…` matches the
     adapter; CRLF digest `a254e087…` matches the transcript.
   - Rule reference: cross-tool integration evidence and independent
     expected-value rules in `governance/TESTING.md`.
   - Disposition: emit and measure one byte buffer through
     `sys.stdout.buffer`.

3. [BLOCKING] The test suite could not detect the emission-layer defect.
   - Status: resolved in targeted regression; live rerun pending.
   - Location: `admission-canary/test_canary_conformance.py`.
   - Evidence: the prior test compared two Python normalizers in one process.
   - Rule reference: regression sensitivity and cross-boundary evidence.
   - Disposition: subprocess raw-pipe test now asserts exact LF bytes and checks
     the adapter log digest and byte count against captured bytes.

4. [BLOCKING] Zero candidates were mislabeled as multiple-candidate ambiguity.
   - Status: resolved in source and analyzer regression.
   - Location: `evidence-live/answer_questions.py`.
   - Evidence: eight zero-candidate joins printed “several adapter lines” with
     exits `[]`.
   - Rule reference: fail-closed reporting and observable behavior.
   - Disposition: zero candidates now explicitly report a broken cross-side
     observable; only multiple inconsistent exits use the ambiguity message.

5. [BLOCKING] Preflight returned GO without testing the shared observable.
   - Status: resolved in source and replay; fresh live rerun pending.
   - Location: `evidence-live/preflight_check.py`.
   - Evidence: the old 13/13 preflight passed although sequence 1 was already
     unjoinable.
   - Rule reference: failure-path evidence and claim-boundary requirements.
   - Disposition: a 14th order-independent shared-observable check now requires
     a completed natural output-bearing call. Replaying it on the original run
     returns NO-GO and lists all eight mismatches.

### Warnings
- Q1/Q3/Q5 remain UNANSWERED. The next task must require `test` before any
  `write`, or a competent producer can avoid every non-zero exit.
- Of-record RUN-CONFIG/FINDINGS were stale and are corrected to the real run id,
  paths, baseline, procedure and counts.
- The producer recovered from denied `printf`/base64 and PowerShell attempts by
  computing base64 itself. This narrows F9: explained denials with a legitimate
  route did not deadlock this producer.
- A user-level Hearth Stop hook exists. The run used
  `--setting-sources project`, `/status` reported only Shared project settings,
  and no Hearth commit occurred. Claim only “no observed confound”.
- Ignored runtime artifacts and truncated list displays remain small
  presentation/hygiene issues; they did not change the verdict.

### Remediation Validation
- adapter conformance plus raw subprocess emission: PASS, 23/23.
- analyzer and preflight regressions: PASS, 29/29.
- corrected preflight replay on original run: expected NO-GO, 1/14 failed,
  all eight multi-line mismatches named.
- fresh isolated live rerun: NOT RUN.
- Gate 2 arm: NOT STARTED.

### Knowledge Base Alignment
- Anti-patterns checked: hashing before platform emission, in-process-only
  boundary tests, zero-observation success, positional identity, and count-only
  preflight.
- Regression notes checked: shared observables must describe bytes actually
  crossing the boundary and evidence must fail closed.
- Result: conflicts found and locally remediated; live evidence still pending.

### Next Recommendation
Commit the narrow instrumentation/reporting correction, then perform one fresh
isolated canary with new run/container/log identities and a prompt that forces
the failing test before any write. Preserve the original run unchanged. Stop on
new evidence failure and do not start a Gate 2 arm.

## 2026-07-26 — Gate 2 live-canary remediation rerun review (`live-canary-20260726-161453`)

### Review Inputs Checked
- `governance/REVIEW_CRITERIA.md`
- `governance/TESTING.md`
- `governance/ARCHITECTURE.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`
- run transcript, adapter log, before/after snapshots, analyzer outputs,
  verifier output, frozen prompt, and producer-cwd session log
- adapter, verifier, analyzer, preflight, and focused test evidence
- commit `eab44eeb` and the run-152447 working-tree provenance

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Risk level: High for frozen task identity and evidence artifact integrity.
- Gate decision: do not start a Gate 2 arm.

### Independently Confirmed
- Transcript: 32 events = 18 pre, 14 allow, 4 deny, 13 ordinary post, and
  1 failure post.
- Adapter: 14 executed lines, sequence 1–14, one matching policy digest,
  0 rejects, and 0 lock waits.
- Final verifier: PASS, 17/17; nine eligible multi-line calls joined on the
  shared observable.
- The first test failed before any write, the later test passed, the source was
  repaired, `/work/out/result.json` existed, and snapshots agreed.
- Q1–Q4 are ANSWERED. Q3 uses a population match with one failure; the exact
  failing call remains UNATTRIBUTABLE because its payload has no stdout digest.
- Q5 remains UNANSWERED at 0/14 lock waits.

### Blocking Findings
1. [BLOCKING] `--json-out` streamed an invalid partial artifact to the final
   path.
   - Status: resolved in candidate source and targeted tests; fresh live rerun
     pending.
   - Location: `evidence-live/answer_questions.py`, `evidence_io.py`, and
     `test_answer_questions.py`.
   - Evidence: tuple keys caused `json.dump` to exit 1 after leaving a
     3,697-byte invalid `answers.json`.
   - Disposition: JSON-safe Q4 shape, full serialization before file creation,
     atomic replace, real CLI readback, and failure-path preservation tests.

2. [BLOCKING] PowerShell 5.1 changed the hash-frozen prompt in transit.
   - Status: source/transport checks and revised launch procedure implemented;
     fresh exact live identity pending.
   - Location: `evidence-live/RUNBOOK.md`,
     `prompt_transport_preflight.py`, `prompt_identity_check.py`, and
     `test_prompt_transport.py`.
   - Evidence: source 1,636 bytes, no BOM; session gained U+FEFF and terminal
     CRLF, while all three U+2014 em dashes became `?`.
   - Disposition: forbid PowerShell text piping, validate raw UTF-8 before
     launch, redirect the file through OS-level stdin, and require exact session
     identity immediately after the first message lands.

### Warnings And Claim Boundaries
- The `187` signal is the focused canonical precommit wrapper:
  `AI_GOVERNANCE_PYTHON=/d/ai-governance-framework/.venv/Scripts/python.exe
  bash scripts/run-runtime-governance.sh --mode enforce`. It is not the
  3,955-test full repository suite.
- `eab44eeb` mixed the byte-exact change with earlier working-tree guard
  changes. Run 152447 records that working-tree state; it is not reproducible
  from one named commit.
- One population-matched failure is evidence for this run, not a broad harness
  routing theorem.
- The next task requests three independent reads together to give Q5 an honest
  batch opportunity. No overlap is guaranteed.
- Run 161453's channel evidence remains valid, but its prompt-identity failure
  blocks frozen-packet use in Gate 2.

### Candidate Remediation Validation
- analyzer CLI and atomic failure regressions: PASS, 29/29.
- prompt transport and exact-session identity regressions: PASS, 6/6.
- all evidence-live regressions: PASS, 38/38.
- adapter conformance including raw-pipe emission: PASS, 23/23.
- memory workflow: PASS, completion claim allowed with zero current-diff B0
  blockers.
- canonical focused precommit wrapper: PASS with exit 0; runtime smoke and
  187/187 focused tests passed.
- fresh isolated live rerun: NOT RUN.
- Gate 2 arm: NOT STARTED.

### Knowledge Base Alignment
- Added the reusable rules that final evidence paths must be atomically
  replaced only after complete serialization, and frozen prompts must not cross
  a locale-dependent text pipe.
- Existing fail-closed and raw-boundary evidence rules remain consistent.

### Next Recommendation
Complete scoped validation and the focused precommit gate, commit the bounded
correction, then run one fresh isolated canary with new identities. Require
`exact_prompt_match: true`, valid atomic `answers.json`, and preserve Q5 as
UNANSWERED if the harness still does not overlap calls. Do not start Gate 2.

## 2026-07-26 — Gate 2 live-canary run 3 review (`live-canary-20260726-172217`)

### Decision Summary
- Verdict: `CHANGES_REQUESTED`
- Channel mechanism: Q1–Q4 established.
- Risk level: High for scorer-artifact integrity and treatment validity.
- Gate decision: do not start a Gate 2 arm.

### Independently Confirmed
- Prompt identity: exact at 1,758 bytes / 1,752 codepoints / SHA-256
  `5ae8f64e…`.
- Preflight 14/14 and transcript verifier 17/17.
- Transcript: 34 events = 19 pre, 15 allow, 4 deny, 12 ordinary post, 3
  failure post.
- Adapter: 15 executions, 0 rejected, three non-zero exits
  (`test:1`, `write:2`, `read:1`), one policy and 0 lock waits.
- Atomic analyzer output is valid; Q1–Q4 ANSWERED and Q5 UNANSWERED.
- The workspace task passed and a final result artifact exists.

### Blocking Findings
1. The launcher exit-code form is wrong for every numeric code.
   - `echo %errorlevel%> file` lets `cmd.exe` parse the digit before `>` as a
     descriptor.
   - Candidate fix saves the code and writes with redirection before `echo`.
   - Windows regression covers exits 0 and 12.

2. Mutable `report` replaced the scorer artifact.
   - Sequence 13 wrote the detailed result, sequence 14 failed to read it
     through the repo-only `read`, and sequence 15 replaced it with an 81-byte
     summary.
   - Candidate fix makes report create-once and joins its structured receipt to
     the final operator snapshot.

3. Storage fidelity and semantic intent were conflated.
   - The adapter already returned a stored SHA-256, so “no digest” was too
     broad. It stored the valid 63-byte payload the producer submitted.
   - Candidate fix explicitly compares decoded request bytes with stored digest
     and length, while requiring a producer read-back for semantic intent.

4. Manual base64 is a treatment effect.
   - The producer deleted a module docstring solely to reduce transcription
     risk.
   - Decision: do not reopen a plaintext shell surface. Retain base64, make
     receipts/read-back mandatory, and preregister the burden as a common-mode
     channel effect. Owner signature remains pending.

### Corrected Review Claim
- The claim that no assistant message contained more than one tool call is not
  supported.
- Claude Code stored the three initial tool-use blocks on separate JSONL rows
  sharing message id `msg_011CdQRfQmroHatjsaGYz9WJ`; all occurred before the
  first result. Another logical message contained two calls.
- The run proves batch requests but not overlapping execution. All live lock
  waits remained zero.

### Structural Limits And Warnings
- All three failure payloads lack stdout digests. Q3 is population-only even at
  n=3; route-A per-call attribution is structurally unavailable.
- PowerShell redirected the analyzer console as UTF-16LE. Candidate operator
  capture forces child UTF-8 and atomically writes stdout/stderr/exit.
- The 187-test signal is anchored to
  `AI_GOVERNANCE_PYTHON=/d/ai-governance-framework/.venv/Scripts/python.exe
  bash scripts/run-runtime-governance.sh --mode enforce`; it is not the full
  repository suite.

### Candidate Validation
- adapter write/report receipts: PASS, 5/5.
- adapter conformance: PASS, 23/23.
- adapter concurrency: PASS, 8/8.
- producer guard: PASS, 101/101.
- verifier mutations: PASS, 14/14.
- evidence-live tests: PASS, 50/50.
- final isolated canary: NOT RUN.
- Gate 2 arm: NOT STARTED.

### Next Recommendation
Finish scoped suites, memory workflow and the canonical focused precommit gate;
commit the bounded remediation; then run one final isolated canary. Require
exact launcher exit capture, one immutable report matching the final snapshot,
UTF-8 console artifacts, and separate batch-request versus overlap claims.
Stop on any new blocking and do not start Gate 2.

## 2026-07-26 — Scorer-handoff v3 source-reproduction review fix (`1f583b00`)

### Review Input And Decision
- Input review of `13b9abff`: `CHANGES_REQUESTED` before owner signature.
- Blocking 1 reproduced: a coherent `FIX_DIFF`, raw digest and anon-id rewrite
  passed the 17-check verifier because it tested only published-set
  self-consistency.
- Blocking 2 reproduced: with `core.autocrlf=true`, checkout changed all three
  hashes declared canonical in amendment v4.
- Status after correction: implemented and locally validated; independent
  re-review and owner re-sign remain pending.

### Resolution
- `verify_handoff` now requires explicit scorer-packet, test-log,
  validator-output and contract sources, pins `redaction_runner.py`, rebuilds
  the canonical packet, anonymized receipt and marker, and compares their exact
  bytes with the published set.
- The eight-file candidate manifest verifies its complete file set, the three
  canonical hashes and exact `-text` coverage.
- Amendment v4 records 18/18 handoff tests and makes CR/reserved-marker
  attrition a whole-run pre-scoring NO-GO; selective repair, exclusion or rerun
  is forbidden.

### Evidence
- New packet/handoff tests: PASS 32/32.
- Frozen v2 redaction regression: PASS 23/23.
- Evidence-live: PASS 65/65.
- Fresh synthetic Docker smoke: packet PASS 22/22; handoff source
  reproduction PASS 24/24; disposable container removed.
- Candidate and canonical exact bytes: PASS 11/11 in worktree, index and
  `core.autocrlf=true` checkout.
- Canonical focused precommit: PASS, runtime smoke plus 187/187 selected tests.

### Carried Forward
- `memory_record` implicit parent-anchor behavior remains a separate slice; this
  record used explicit commit `1f583b00`.
- Scorer-packet CLI use-before-validate and the one-way tracked-inventory check
  remain separate non-blocking follow-ups.
- No owner signature, canonical promotion, resource admission, Gate 2 arm or
  push is claimed.

## 2026-07-26 — Scorer-handoff v3 offline-semantics review fix (`9918d3a5`)

### Review Input And Decision
- Input re-review of `1f583b00` plus `0e9c229f`: `CHANGES_REQUESTED` before
  owner signature.
- Blocking N1 reproduced: a source packet with self-consistent artifact
  digests but contradictory tracked-path artifact, workspace inventory and
  scorer core passed the handoff's offline source reconstruction.
- Blocking N2 reproduced: build hard-coded `blinding_compromised=null`, and
  verify required null, so an experimenter could not preserve a real residual
  leak flag in a deterministically reproducible handoff.
- Status after correction: both blockers are resolved in implementation commit
  `9918d3a5`; independent re-review and owner re-sign remain pending.

### Resolution
- Offline reconstruction now repeats the packet verifier's three semantic
  checks before assembling any handoff.
- Build and verify accept the same optional
  `--blinding-compromised-reason`; absence deterministically produces
  null/null, while a non-blank reason produces true plus the exact string.
  Omission, substitution and blank input fail.
- The contract, amendment v4, exact candidate manifest and receipt hashes were
  regenerated. Amendment §F also states that an independent reviewer must
  inspect the self-referential verifier source in addition to running
  `verify-candidate`.

### Evidence
- Original N1/N2 regressions: FAIL before implementation as expected.
- Scorer packet: PASS 14/14.
- Scorer handoff: PASS 20/20, including both new regressions.
- Frozen v2 redaction: PASS 23/23.
- Candidate verifier: PASS 11/11; manifest SHA-256
  `5bea553937a6ec6d2f0e4ef8b8b6719a40db28455199844bcbc22001caed52dc`.
- Canonical focused precommit: PASS, runtime smoke plus 187/187 selected tests.
  Two direct Git Bash attempts failed before gate start because `dirname` was
  absent; the login-shell PATH rerun used the same canonical entrypoint and
  exited zero.

### Carried Forward
- Fresh Docker integration was not rerun for `9918d3a5`; the prior
  `1f583b00` smoke is historical evidence only.
- `scorer_packet_v2.main()` use-before-validate and its no-JSON-on-exception
  behavior remain a separate warning.
- No owner signature, canonical promotion, resource admission, full repository
  suite, push or Gate 2 arm is claimed.

## 2026-07-27 - Scorer-handoff v3 reason-code remediation review

### Review Input And Decision
- Independent read-only review verdict: `APPROVED`.
- Risk level: medium.
- Approval target: exact candidate manifest SHA-256
  `7104b2e03da9e61c8191430fd337b7b73effb41eb787b55e3364a21d1ac2147c`.
- Scope was limited to the scorer-handoff remediation candidate, its contract,
  amendment, tests, manifest, reconstruction evidence, and scoped memory diff.
  Unrelated dirty and untracked paths were not inspected.

### Findings And Resolution
- Prior BLOCKER-1 resolved: arbitrary free-text blinding reasons were replaced
  by three closed reason codes; unknown or substituted values fail closed.
- Prior BLOCKER-2 resolved: raw detail remains in an experimenter-side regular
  UTF-8 file and is discarded before scorer-packet assembly. The independent
  reviewer and scorer artifacts receive the code only.
- Prior WARN-3 resolved: normal pytest collection now executes a wrapper that
  runs all 23 frozen redaction checks, and the test file is pinned in the exact
  candidate manifest.
- Manifest, reconstruction, evidence claims, and byte-preservation controls
  were independently checked and found internally consistent.

### Evidence
- Scorer packet: PASS 14/14.
- Scorer handoff: PASS 21/21.
- Frozen redaction script: PASS 23/23; pytest collection PASS 1/1.
- Candidate verifier: PASS 15/15.
- Offline handoff reconstruction: PASS 24/24.
- Exact manifest digest independently matched the approval target.
- Candidate files and reconstruction evidence reported `text: unset`; scoped
  `git diff --check` passed.

### Not Claimed
- No new Docker or live-container run.
- No owner signature, canonical promotion, resource admission, or Gate 2
  start/arm execution.
- No cryptographic writer authentication or full repository suite.
- No commit, push, clean workspace, or overall task completion for this
  remediation.
- WARN-4, NIT-5, NIT-6, and unrelated dirty paths were outside review scope.

### Next Recommendation
Ask the owner to re-sign the exact approved manifest hash. Any candidate-byte
change requires another independent review.

## 2026-08-13 — Gate 3 runner-integration design provenance and bridge candidate reviews

Three independent reviews in one session: one on a provenance repair, two on
successive revisions of a design candidate.

### Review 1 — P0 design-provenance repair (`APPROVED`)

- Finding that triggered the slice: PR #61 merged the runner/capture integration
  tranche while its PLAN entry stated that the reviewed design authority
  "remains an uncommitted candidate" at SHA-256 `d0d1609b…`. The bytes existed
  only in one local worktree; `git log --all` had no record of the file. A
  merged milestone therefore could not be re-reviewed against its own stated
  design authority.
- Secondary finding: the per-file `-text` convention for digest-pinned
  governance docs lapsed after `gate3-route-v2-ab-design-candidate-20260808.md`.
  Three already-pinned Gate 3 candidates were exposed to fresh-checkout digest
  drift under `core.autocrlf=true`.
- Resolution: commits `dc76c293` (candidate committed unchanged, plus four
  `-text` rules) and `100c6c34` (PLAN reworded as retrospective preservation).
- Verdict `APPROVED`; delivered as PR #62.

### Review 2 — bridge candidate `ed7807d6…` (`CHANGES_REQUESTED`, 5 blocking)

1. Eight open questions were presented to the owner as two; six affected
   authority or privacy and could not be deferred to exact-digest review.
2. The digest was described as a pin target although any decision would
   invalidate it; it was only a pre-decision baseline.
3. Runtime binding of the bridge source was claimed via outer-authority Git blob
   pinning. `RUNTIME_SUBJECTS` is closed, `_check_runtime` requires exact set
   equality, and `RuntimeAuthority` has no `bridge_source` field, so no runtime
   binding was expressible.
4. Moving private preparation inside `invoke()` lands `auth.json` under a state
   machine that forbids ordinary cleanup until a durable seal exists. Credential
   residue recovery was left as "external recovery only" with no locator,
   authorization or profile linkage.
5. Dataclass `repr` exposure and `__call__`/bridge path exclusivity were
   controlled only by convention.

### Review 3 — bridge candidate `71a6943d…` (`CHANGES_REQUESTED`, 1 blocking + 1 warning)

- Blocking: the revision fixed the runtime-binding overclaim but reintroduced the
  same class of error on the workspace baseline, describing it as bound by outer
  authority when `RuntimeAuthority` again has no field able to express it. The
  workspace axis is an evidence-profile discriminator, so an unbound baseline can
  move an execution between `RUNNER_CAPTURE_FINALIZED` and
  `RUNNER_CAPTURE_NEGATIVE`.
- Warning: the evidence plan simultaneously forbade importing a live path and
  permitted an identity-only import of `gate3_route_v2_codex`.
- Author-reported remediation, pending independent exact-digest review: the
  baseline is stated as an unsolved problem, the first tranche uses a retained
  synthetic fixture, no evidence-profile derivation is claimed for that axis, and
  a baseline authority becomes the fifth production-wiring precondition. Import
  wording separates construct/invoke from identity-only import. None of this is
  reviewer-confirmed; the revision at `6c3552e2…` has not been reviewed.

### Evidence

- committed blob SHA-256 `d0d1609bc111bb8cef28f8442f80beddeb6ad87744be9e74723d3e11126a19fd`,
  matching the value PLAN already pinned.
- `git diff --check 0e8f3b79..100c6c34`: PASS. (Recorded as explicit commit
  identities rather than `origin/main..HEAD`, which stops naming the reviewed
  range once the branch merges or moves.)
- `git check-attr text` on all four pinned Gate 3 candidates: `unset`.
- Candidate digest chain: `ed7807d6…` → `71a6943d…` → `6c3552e2…`.

### Not Claimed

- No implementation, credentials, preflight, subprocess or live execution.
- No approval of the bridge candidate; `6c3552e2…` is unreviewed and uncommitted.
- Committing the design bytes after the fact does not establish that the design
  was repository-available before implementation commit `854fef93`.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged.

### Next Recommendation

Independent exact-digest review of `6c3552e2…`. Do not begin the mapping-only
offline tranche before that review returns, and do not treat design approval as
credential, preflight or live authority.

## 2026-08-13 — Gate 3 bridge design candidate accepted (`5e0279c9…`)

### Findings And Resolution
- Two further review rounds followed the record above. Round 3 on `6c3552e2…`
  returned `CHANGES_REQUESTED` with one blocking and one warning: the
  `Authorization Boundary` said "four preconditions" after a fifth had been
  added, so the workspace-baseline authority could be read as outside the
  production blocking set; and the base line named only the pre-merge design
  baseline while the candidate commit sits on a later main.
- Both were corrected with a two-line change. A limited diff confirmed no other
  byte differed (4 insertions, 2 deletions).
- Round 4 on `5e0279c9…` returned `APPROVED` with zero open findings.

### Evidence
- accepted candidate SHA-256
  `5e0279c9115f9f4eb47f3e2fd713091c58e8028be9bc6760ca5f462a21e7a015`,
  design commit `013f227a`, blob identical on the remote branch.
- committed blob CR=0, LF=651.
- `git diff --check origin/main..013f227a`: PASS.
- scope: `.gitattributes` and the candidate file only.
- the four source files named by the candidate are byte-identical between
  `0e8f3b79` and `cc304a90`, verified by blob comparison rather than assumed.
- PR #64 checks: 11 success, 1 skipped, 0 pending, 0 failed.

### Not Claimed
- No GitHub review record exists for PR #64 (`reviews=0`, empty
  `reviewDecision`). Acceptance is the owner's, not an external reviewer's.
- Design acceptance is not implementation, credential, preflight or live
  authority.
- The five production-wiring preconditions remain unsolved; two of them reopen
  the integration contract digest pinned by the runner/capture milestone.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation
Merge the accepted design with its PLAN and memory reconciliation in the same
pull request, then treat the mapping-only offline tranche as a separately
authorized slice.

## 2026-08-14 — Gate 3 mapping-only runner bridge tranche accepted

### Findings And Resolution
- Round 1 on implementation `9ec1ba63…` / test `556a839f…` returned `APPROVED`,
  but the author then self-reported a defect the review had not caught:
  `test_no_credential_bytes_are_written` asserted `list(tmp_path.iterdir()) == []`
  against a pytest-created directory that no code path ever targeted. The
  assertion passes unconditionally, so the test name promised credential-write
  detection that the mechanism could not deliver. The verdict was corrected to
  `APPROVED with 1 WARNING`.
- Resolution: the `tmp_path` fixture and its assertion were removed, the test was
  renamed `test_mapping_tranche_uses_in_memory_fake_preparation`, the assertions
  narrowed to `prepare.calls == 1` and `vars(prepare) == {"calls": 1}`, and the
  docstring states explicitly that this is not credential-write detection.
  Removing the fixture also eliminated an unrelated pytest temp-directory ACL
  sensitivity seen on one rerun.
- Round 2 on test `b85eca62…` returned `APPROVED` with zero open findings.

### Evidence
- implementation SHA-256
  `9ec1ba63e3a58e3bca4eab9570871e9d2584f4c7742cc6ec660f418fbd708c33`, unchanged
  across both rounds; test SHA-256
  `b85eca62c3edf6c6d2112b3abf91b805264b1b648d774109d85eca9a30420993`.
- identical staged, committed and remote blobs, verified at each step.
- focused tests 23/23; five adjacent Gate 3 offline suites 520/520.
- `git diff --check origin/main..b399cb7f`: PASS; scope is the two new files.
- PR #65 checks: 11 success, 1 skipped, 0 pending, 0 failed.

### Not Claimed
- No runtime authority over the bridge source; it is not a `RUNTIME_SUBJECTS`
  member and does not participate in the TOCTOU chain.
- No public workspace evidence: the baseline is a caller-supplied synthetic
  fixture, so `CHANGED`/`UNCHANGED` derived from it is test-local.
- No credential-write detection, no real runner wiring, no credentials,
  preflight, subprocess, network or live execution.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation
Treat the recurring lesson as method, not incident: three of the defects in this
work stream were claims asserted top-down that the underlying mechanism could not
express — twice in design against merged dataclass fields, once in a test name
against its own assertion. Check the mechanism first, then write the claim.
Production wiring stays blocked on the five preconditions; group A is the next
design slice and reopens a pinned contract digest.

## 2026-08-14 — Gate 3 Group A runner integration contract v2

Design accepted at `a720624920ee402a6e490077f806229879929bbc9ba37bb84fd95eb551979e74`
after five rounds; implementation delivered as three separately reviewed commits
on one branch.

### Findings And Resolution

**Design, five rounds.** Every round found one defect in a different place: a
guarantee asserted over a seam that cannot enforce it.

1. `evidence_class = PRODUCTION` is caller intent, not execution provenance,
   because `invoke` is an injected callable. Resolved by admitting `SYNTHETIC`
   only and reserving `PRODUCTION` behind three named preconditions.
2. Dispatching on version inside contract validation is too late, because
   `verify_package` validates the authority first. Resolved by contract-first
   identification from exact canonical bytes.
3. An admission builder does not constrain a coordinator field that accepts any
   callable. Resolved by removing the callback seam entirely; a token-guarded
   capability was rejected as an overstated guarantee, since a private module
   token is an API structural constraint rather than a boundary against a
   hostile in-process caller.
4. An import guard does not constrain what an author ran before pasting a
   literal, and mutation tests measure verifier sensitivity, not literal
   provenance. The "serializer reuse is detectable" claim was withdrawn.
5. Stale affected-surface text still described the superseded admission-builder
   design. Resolved in place.

**A1, one round.** The retained-package test produced its own package with the
modified coordinator, which shows only that a producer round-trips through its
own verifier. Resolved with a frozen pre-A1 fixture captured from the module at
`c2bc090b…`, verified without running any coordinator.

**A2, one round.** The module comment said a v2 model without coordinator
enforcement must not be presented as an active contract, but `verify_package`
would verify a hand-built v2 package. Resolved with
`VERIFIABLE_CONTRACT_VERSIONS` and a regression that relinks every downstream
digest, plus a second test proving that package is internally coherent so the
rejection is demonstrably the gate.

**A3, one round, three blocking.**

- The baseline was read twice from a caller-held mapping, so a mutation between
  admission and comparison left the authority binding something other than what
  was compared. Resolved with an immutable-by-value private snapshot taken
  before any side effect.
- The claim ladder existed only in the design. Resolved by reporting
  `evidence_class` and `baseline_claim` on every profile.
- Hostile mappings leaked their own exception text from `items()` calls outside
  the failure boundary, on both the baseline and observed paths. Resolved by
  closing both to `WORKSPACE_BASELINE_INVALID` (cause dropped) and
  `CAPTURE_FAILED`.

### Evidence

- commits `38991f35`, `7c0ee75e`, `3ca52b49`; six exact digests recorded in the
  corresponding PLAN entry, stable across review.
- five focused Gate 3 offline suites: 570/570.
- `git diff --check`: PASS at every step.
- pre-A1 fixture verified from literal bytes with no coordinator run.
- hostile probe by the reviewer: adding v2 to the verifiable set in memory made
  the same relinked package verify, confirming the A2 rejection came from the
  version gate rather than a stale link.

### Not Claimed

- No claim that any run performed the baseline comparison. Public v2 bytes reach
  `BASELINE_DIGEST_DECLARED`; a supplied matching private map reaches
  `SUPPLIED_BASELINE_MAP_MATCHES_DECLARED_DIGEST`. The third rung is a
  conditional statement about reviewed source, not about execution.
- No production evidence class; `PRODUCTION` is rejected by the v2 validator.
- The oracle fixture is runtime-independent of the production modules and its
  values were independently re-derived. Serializer reuse is not detectable and
  is not claimed to be.
- No real runner wiring, credentials, preflight, subprocess or live execution.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

Three production-wiring preconditions remain: a pre-seal credential-residue
recovery contract, a structural non-`repr` boundary, and machine-enforced path
exclusivity. Group C is the credential-residue design; group B splits into two
tranches because the two mechanisms have different modification surfaces and
failure models. None may be interleaved before the one in progress closes.

## 2026-08-16 — Gate 3 native handle boundary N3c-1

Design revision 17 accepted and committed design-only as `0d95023d`
(`83ca5282c632d65ad34961467359b7c846a1cdc58a5d353b5cd350063feecbb3`).
Implementation delivered as `1486fdb5` after three rounds of independent
exact-digest review.

### Findings And Resolution

**Revision 17, one round.** Revision 16 required a reparse-tag check on every
pinned ancestor while granting `FILE_LIST_DIRECTORY | SYNCHRONIZE`, a mask that
cannot perform one — measured on the volume root,
`GetFileInformationByHandleEx(FileAttributeTagInfo)` returned
`ERROR_ACCESS_DENIED`. Two clauses of the same document could not both hold. The
audit the ruling asked for found no role exempt from querying, so all three
roles were amended rather than role 1 alone. `FILE_WRITE_ATTRIBUTES` was
explicitly rejected as a justification for reading: `0x0080` and `0x0100` are
independent rights.

**Implementation, three rounds.** Three of the round-one and round-two
findings were the same defect wearing different clothes — a test narrower than
the invariant it was named after, passing while proving nothing. The rest were
ordinary implementation defects: a missing ownership API, an accepted invalid
handle, and the `__exit__` masking found in round three.

- `test_no_bound_export_is_invoked_outside_the_guard` inspected a hand-written
  list of two functions, so the two direct `CloseHandle` calls this tranche
  added never registered. Widened to the whole module, exempting only
  `_guarded` and `fail_fast`, with a synthetic case proving the detector fires.
- The "creates nothing" check searched for `ntdll.NtCreateFile(`. The compliant
  call shape — the export handed to `_guarded` as a callable — contains no such
  text, so the check was blind to a violation and to compliance alike.
  Replaced by an AST resolution covering both shapes, with a synthetic
  sensitivity case.
- Evidence 19w asserted only that the query failed, which any failure satisfies.
  `ctypes.get_last_error()` was already being read and discarded; it is now
  attached as a note and asserted by equality as `last_error=5`.
- A `NULL`-only handle check let `INVALID_HANDLE_VALUE` through, because on
  64-bit it is truthy.
- Round three: both `__exit__` methods still masked the body error, because
  `return False` only runs if `close()` returns. The same masking had already
  been fixed in `_anchor` and `open_chain`; the exits were missed because they
  leave through a different door. Fixed with the reverse case also tested, so
  "does not mask" was not implemented as "always swallows".

Ownership was brought to the design: context manager plus `__del__` safety net,
`close()` clearing the handle unconditionally including on failure, second
close a no-op.

### Evidence

- Implementation `c8f40027dbc2900e4b370e6a7fc6dcbc144897b418dbc972b50fd0470adbfca5`;
  tests `9b27a2dd9a081e53372f9a1865ab6d93947812dcea4d42e4aa2926f833f96817`.
  Both paths carry `text: unset`, so committed and remote blobs are
  byte-identical to the reviewed worktree bytes.
- Focused suite 169/169. Surrounding Gate 3 suites 1073 passing and 7 failing.
  Those seven were reported at the time as pre-existing failures untouched by
  this tranche. That attribution was wrong: they are caused by the uncommitted
  B-1 worktree divergence, and at `HEAD` the two files concerned are
  byte-identical to `SOURCE_COMMIT`. N3c-1 neither caused nor could have fixed
  them, but calling them pre-existing obscured a live causal link. Corrected in
  the 2026-08-16 canonical memory rather than by editing this line's original
  claim, which is preserved above in the sentence it replaced.
- Evidence 19w reproduced on a real directory under both masks: revision 16's
  fails with `last_error=5`, revision 17's returns tag `0`.
- Two adjacent slices landed the same day and were reviewed separately:
  `97ad42e4` reconciled `2026-08-13` through `2026-08-16` memory with `PLAN.md`
  and the active task, preserving 34 hook-generated records unrewritten and
  adding three canonical corrections; `ec0c4046` replaced the stale CP-8 shared
  closeout with a current-session one the parser can read.

### Not Claimed

- No claim that the boundary is reachable. `handle_boundary_available()` and
  `ACTIVE` are both `False`, and nothing in production calls this.
- No creation, deletion, rename or absence probe. `NtCreateFile`,
  `SetFileInformationByHandle`, `WriteFile` and `GetVolumeInformationByHandleW`
  stay bound and uncalled, asserted structurally rather than by convention.
- No claim that session binding was repaired by `ec0c4046`. No envelope exists
  for this `session_id`, so `session_end` still fails closed before evaluating
  any field, and the empty `missing_fields` and `content_issues` in the
  candidate mean *not computed*, not clean.
- No claim of durable diagnostic capture from fail-fast, per owner ruling 8's
  slice-specific `NATIVE-INTEROP.md` §4.1 exception.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

The order is `N3c-2 -> M2 -> M3 -> M4 -> B-1`. An earlier draft of this section
recommended closing M2 first, on the reasoning that M2 is the consumer and its
blockers decide the interface. The first half is true and the conclusion is
not: every operation M2 fails closed on is a creation, a write, a deletion or
an absence probe, so M2 cannot converge until N3c-2 exists. What M2 supplies
first is its consumer contract, not its closure.

N3c-2 needs a design-first slice of its own, because it is the first
authorization to create and delete real filesystem objects and to run the
absence probe — a wider safety boundary than opening and holding handles, and
one that N3c-1's approval does not reach. B-1 comes last, behind M4, because
its edits break the source pin the historical candidate is verified against and
M4 is what makes that verification independent of live worktree bytes.

Before N3c-2 is designed, two smaller things: the vacuous assertion at
`test_gate3_native_boundary.py:539`, and an owner decision on whether `base`
must pre-exist.

## 2026-08-17 — Gate 3 native boundary N3c-2

Design accepted as `520cc306`
(`25d0a2522c5bd4a482bb28fcc3c9cdfc62d5c0768f44f897445053fdead6aaba`) after four
rounds; implementation delivered as `495fe52f` after three.

### Findings And Resolution

**Design, four rounds.** Three different kinds of defect, and only one of them
is about evidence.

- *Safety scope.* `_contained` was listed for deletion on the argument that
  containment becomes structural once every open is handle-relative. True of creation and cleanup,
  and only of them: `verify` still resolves `root / relative` by path and still
  calls it. The digest comparison does not cover for it — a digest rejects
  differing bytes and says nothing when an external location holds exactly the
  expected ones, by which time the unauthorized read has happened.
- *Evidence.* Born-read-only was to be shown by a second open failing. Role 3's
  `ShareAccess` is `FILE_SHARE_READ` alone, so that open fails on the share mask
  whether or not the attribute was ever requested — the check would have passed
  against an implementation that dropped the attribute entirely.
- *Behavioural contradiction.* Cleanup control flow required both "every object
  is attempted" and "stop at the first failure, do not attempt the parent"
  within three lines. They are
  different sequences: deletion attempts stop, handle release continues.
- *Unreachable specification.* The replacement observation point — after
  creation, before the first write — does not exist. `create_file` takes the payload and returns a held leaf, so
  reaching between them would mean splitting the surface or adding a callback
  into the phase that must have none.

**Implementation, three rounds.** Three of the five blocking findings were
production defects no test had caught; two were defects in the evidence itself,
and a later round found two more of that second kind.

- A failure between `FILE_CREATE` and the returned ownership object left the
  name on disk with nothing holding it; the caller never received an object, so
  nothing would ever clean it up. Rollback now marks, closes and confirms absent
  through the same code cleanup uses.
- A close during removal reported `CLOSE_FAILED`, which names the wrong problem:
  the object is delete-pending and may still be there. The removal flag is set
  before the mark, because a mark that raises can still have left it pending —
  and the first test of that ordering could not tell the two implementations
  apart, because it let the mark succeed.
- Every creation failure was reported as a taken name, which tells a caller to
  choose another when the volume is full or the parent vanished. Only
  `STATUS_OBJECT_NAME_COLLISION` maps there now, and the stage carried into the
  diagnostic is the role's own rather than always `CREATE_FILE`.
- The read-only evidence was confounded, and its sensitivity check asserted that
  the recorded value differed from a literal — which is what a broken
  implementation produces, so it passed exactly when it should not have. The
  expected values now come from literals copied from revision 17, and each
  mutation re-runs the real assertion and requires it to fail.
- The disposition matrix covered only "forced fallback succeeds". Preferred-only
  is now asserted by recording which information classes are set, and
  both-failing is asserted to leave the object present — reporting
  `CLEANUP_INCOMPLETE` over a name that had in fact gone would send a caller
  looking for nothing.

One submitter assertion was wrong in a useful way: reading a created file back
raised `PermissionError`, because role 3 holds `FILE_WRITE_DATA` and `DELETE`
under a `FILE_SHARE_READ` mask. That is the design working. The sharing
violation became its own assertion, and content verification moved to a fixture
that owns its cleanup and is labelled as not being the role 3 lifecycle.

### Evidence

- Implementation `9142f2c6…`, tests `a044c35b…`; both paths carry `text: unset`,
  so worktree, staged, committed and remote blobs are byte-identical.
- Focused suite 245/245. Across the gate3-route-v2 suites 1158 pass and 7 fail,
  those seven being the B-1 worktree pin failures recorded in `ed9d5d06`.
- Canonical precommit run against the exact committed diff through Git Bash at
  `/usr/bin/bash`: exit 0, 201 passed, `smoke_status=pass`,
  `pytest_status=pass`. It covers `tests/` and not the experiment suites.
- Real-Windows tests create and delete under a base the test creates; the
  complete-cycle test compares `st_ino` before and after to show the base is the
  same object rather than a directory with the same name.

### Not Claimed

- No claim that the boundary is reachable: `handle_boundary_available()` and
  `ACTIVE` are both `False`, and M2 is not wired to any of it.
- No claim that precommit covers the experiment suites; those were run
  separately and are reported separately.
- No claim about `520cc306`'s own precommit, which did not execute successfully
  before that commit and is recorded as a known unverified item.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

M2's handle-bound rewrite, then M3 and M4, then B-1. M2 is where the boundary
first acquires a consumer, so its rewrite is also the first test of whether the
surface designed for it actually fits.

## 2026-08-18 — Gate 3 held-handle read design amendment

Three documents amended together and accepted after eight rounds: the native
handle-boundary design to revision 21, the N3c-2 tranche design to revision 7,
and the historical evidence materialization design to revision 8.

### Findings And Resolution

The amendment began because revision 17 had made the materialized bytes
unreadable by anything at all. Role 3 holds each created file until it removes
it, and its share mask keeps out the openers that matter, so `verify` could not
re-read what it had just written and M3's child could not load the modules it
was supposed to execute. The first proposal — treat the share mask as
guaranteeing immutability and drop the byte check — was rejected, and rightly:
a mask prevents modification, it does not observe bytes, and the same violation
that stopped the parent reading would have stopped the child loading. Role 3
therefore gains `FILE_READ_DATA` and the adapter gains `read_all(leaf)`.

**The recurring finding across the eight rounds was not in the new mechanism.**
It was old specification that did not retire when the thing it described
changed. A `verify` still documented as path-based; a DONE line still requiring
a materialized `sys.path` two rows below a table excluding it; a framing
paragraph superseded by an exact one but left beside it; a `child` row that read
equally as loading from the filesystem or from buffers. Each was correct when
written. Every revision added a specification without asking which existing
paragraph it had just falsified, so the documents ended up specifying two ways
to do one thing — and a reader could implement either.

**Two claims were withdrawn against measurement rather than argument.**

- A held created file was said to admit no other opener. Measured: a native
  `NtOpenFile` for `FILE_READ_DATA` is refused sharing only read, refused
  sharing read and write, and **succeeds** sharing read, write and delete.
  Share compatibility is bidirectional. The justification for reading through
  the creating handle is now that it resolves no name and adds no second
  ownership path — not exclusivity.
- Byte immutability was attributed to the share mask alone while the creating
  handle holds `FILE_WRITE_DATA` throughout. Three things close it together:
  the mask, the opaque handle, and a call census proving no `WriteFile` exists
  after creation. Remove any one and the claim fails.

Other findings closed: `read_all`'s length is sealed at creation rather than
passed in; the read state machine covers all four `ReadFile` outcomes including
a count larger than the request; the rewind is a specified call with a checked
postcondition; the wire format has magic, version, widths, endianness, a raw
digest and a bytewise path ordering; every bound is an exact byte count; the
whole-stream cap was withdrawn as unreachable and recorded as a derived
maximum; and the child's expected inventory comes from a digest frozen in
trusted code rather than from the active head or from the stream.

### Evidence

- boundary `f1d7d8160c307ad656ec96d6089e9eb216272d9faf9068e923eb41bac01714df`;
  N3c-2 `4000b95dc7487976bbcf3b700bc2f475a733fbdda33fe88437d2c630ac38638e`;
  historical `efa07ce87bc829bfeb643bbac7a9dcd52ba80ae1d4f9a113eba45daa65a0514f`.
- The share-compatibility measurement was taken against a real held role 3
  handle under a test-owned base, and is what withdrew the exclusivity claim.
- The derived stream maximum, 34,638,232 bytes, is the sum of the header, the
  candidate-set block, the per-record framing and the aggregate payload; it is
  recorded so the arithmetic is checkable and is explicitly not a gate.

### Not Claimed

- No implementation. `read_all` does not exist in code, and this amendment
  moved no availability flag.
- The directory enumeration in `verify` remains path-based; the adapter offers
  no handle-bound enumeration, and M2 may not claim all verification is
  handle-bound.
- Nothing here is a statement about what the child process could be made to do,
  only about what its trusted loader does.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

Open the merge request for the delivered milestone before continuing. Fifteen
commits is already a large review unit and every later tranche adds to it, while
the current set is self-contained precisely because nothing production reaches
it. Then M2, M3, M4 and B-1 in their own requests.

## 2026-08-18 — Gate 3 held-handle read implementation and M2

Two commits: `6e7393e2` adds `read_all` to the boundary, `5a04ec79` rebuilds M2
on it. Six review rounds between them.

### Findings And Resolution

**The read, two rounds.** The module still named design revision 17 as its
authority while implementing revision 21, and still said it bound eleven
exports where there are now thirteen — the count now derives from `BOUND` rather
than from prose that has to be remembered. Two failure paths had no tests, a
failed rewind and a failed end-of-file probe, and both mutations survived:
checking only the returned position, and dropping the probe's error check while
the main loop stayed correct. The ABI assertion only checked that `argtypes` was
non-empty, which passes for a wrong argument order, a pointer where a value
belongs, or a wrong return type — the mistakes that truncate a handle on 64-bit.
It now compares against an independent ctypes oracle, with five sensitivity
cases proving it rejects a wrong declaration.

**M2, four rounds.** Two findings generalize beyond this module.

*A record can be forged out of valid parts.* Two trees built from the same
commit under different bases produce records with identical labels, identical
digests and correctly-typed handles. Swapping one bundle into the other's record
passed every structural check, and cleanup deleted the tree the record did not
describe. Adding more shape checks would not have helped, because every shape
was right. The fix was to remove the recombination: the tree became a façade
over one authority object, and there are no longer separate fields to mix. An
intermediate fix — a seal indexing a global registry — was itself wrong, and
wrong in a way worth remembering: the registry held the handles by strong
reference, so a caller who lost the tree without cleaning up left every handle
open with no way to reach them again.

*Removing a check can remove a second one nobody noticed it carried.* `verify`'s
byte loop asserted two things: that the bytes are what was written, and that the
caller is asking about the inventory the tree was built from. Deleting the read
took the second with it, and a `verify` comparing path names alone accepted a
map whose every digest was wrong.

Also closed: `verify` snapshotted a caller-supplied `Mapping` while every handle
was open, which is a callback in the phase that must have none — the parameter
is gone and `bindings` is keyword-only so a stale positional call fails at the
signature rather than deep inside the boundary; `_record_of` ran only in
cleanup, so a duplicated, foreign or spent authority was not checked before
reading; and cleanup did not confirm each object absent before moving to its
parent.

### Evidence

- read `f705a215…` / `620ad470…`, focused suite 267;
  M2 `31f6a0f1…` / `f89bf78c…`, focused suite 68.
- Canonical precommit run against each exact diff through Git Bash at
  `/usr/bin/bash`: exit 0, 201 passing, both times.
- Across the `gate3-route-v2` suites, 1,195 pass and 7 fail — the B-1 worktree
  pin failures recorded in `ed9d5d06`, carried by no commit.

### Not Claimed

- M2 is not reachable. `materialize()` and `cleanup()` refuse, because
  `handle_boundary_available()` forwards to the boundary and the boundary
  reports `False` while no admission record and no capability probe exist.
- Verification is not entirely handle-bound. The enumeration is still a path
  walk, and the caveat is asserted by a test rather than left to memory.
- The share mask is not total exclusion: measured, a native reader sharing
  read, write and delete opens a held role 3 file. Reading through the creating
  handle is chosen because it resolves no name and adds no second ownership
  path.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

M3, then M4, then B-1. M3 is where the verified buffers meet a child that must
not open a materialized path, and where the framed transport's bounds and
frozen-digest authority stop being design and start being code.

## 2026-08-19 — Gate 3 M3 design and M3-a

Merged to `main` as `5204cd18` (PR #75). Design `a51cd4be`, implementation
`daf4ec5e`. Seven review rounds: five on the design, two on the implementation.
The first draft of this section claimed five and five. The implementation had
one `CHANGES_REQUESTED` and one `APPROVED`; `daf4ec5e`'s own commit message
already said two rounds, so the record contradicted the commit it described.
Counting review rounds by how much work happened rather than by how many
verdicts were returned is how a number like that grows.

### The finding that shaped the tranche

A child started with `-I -S -B` has exactly four `sys.path` entries, all under
the interpreter's own installation, with `site-packages` absent and the runner's
own directory absent as well. That is the isolation the design asked for, and it
means the child cannot import the transport decoder or
`gate3_historical_bootstrap` either. One mechanism, no sides taken.

It also falsified a clause in the parent design: "every path passes the same
grammar the parent applied" could not be implemented, because the parent's check
asks about root escape on join, the child never joins, and the module cannot be
imported. The subordinate document was marked **blocked** rather than asserting
a stricter grammar over its own authority, and the authority was amended to
revision 10.

### Findings And Resolution

**Two specified evidence items were impossible.** An ordering case wanted a legal
path whose code-point order and UTF-8 byte order differ; byte-wise ordering of
well-formed UTF-8 preserves scalar order, measured across 3,275,520 scalar pairs
and 200,000 random string pairs with zero disagreements. A round-trip case wanted
bytes that decode strictly but do not re-encode to themselves; strict UTF-8 is
canonical, measured across every 1-, 2- and 3-byte sequence with zero failures.
Both were tests named after invariants they could not check. Both rationales were
rewritten beside the tests, because fixing only the test leaves the document
asserting a reason the test no longer has.

**The declared aggregate was not enforced before the payload read.** A stream
declaring zero, with a record declaring one byte and omitting it, returned
`RECORD_TRUNCATED` — the decoder had already tried to read.

**And its neighbour was redundant.** The record loop also compared the running
total against the global bound. A mutation showed that comparison could be
deleted with the suite still green: the header already refuses a declaration
above the bound, so the declared comparison is always the tighter one. Two
comparisons where one decides read as though both were load-bearing, so it was
removed rather than kept.

**The evidence harness spawned git** to read the pinned payloads, while the same
file's docstring said nothing spawns a child. Payloads are synthetic now, the
cost is stated in the docstring, and a test asserts the file imports no
process-starting module.

**The ordering test measured the wrong region.** It searched the whole stream and
found the paths inside the candidate-set JSON rather than the records. The tests
now carry a second, independent framing walker.

Also closed: `path.encode("utf-8")` could raise `UnicodeEncodeError` out of the
encoder for a lone surrogate, escaping the closed error contract; and the grammar
tests accepted either of two codes, which passes an implementation reporting a
NUL as a length overrun.

### Evidence

- implementation `4c477109…` / tests `189588b4…`, focused suite 96/96.
- Eighteen injected defects, each caught, **none surviving** — including both
  aggregate comparisons, both digest comparisons, the authority ordering, the
  encoder's sort key and the closed error mapping.
- Canonical precommit against the exact state: exit 0, 201 passing.
- CI on PR #75: twelve checks passed, none failed, `mergeState=CLEAN` confirmed
  before the merge.

### Not Claimed

- M3-a is unreachable. `ACTIVE = False`, no production caller, no spawn, nothing
  compiled, no historical module imported.
- The trusted computing base is named rather than assumed. The runner is
  executed by path and nothing verifies those bytes first, so "defends against a
  corrupted parent" covers transport and data state and **not** the spawn
  target. Runner identity and its TOCTOU window are accepted trust assumptions,
  not deferred work.
- The child's re-derivation is not independent verification in the strong sense:
  both copies come from one author and one design.
- The round trip is evidence about framing and verification, not about the four
  historical modules — the payloads are synthetic. The authority evidence does
  run against the real retained candidate-set bytes.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

M3-b, design first. It is the first tranche that executes historical code, and
the design must not restate the runner's trust root as solved.

## 2026-08-19 — Gate 3 M3-b design and M3-b-1

On `feat/gate3-historical-materialization`, **not merged to `main`**. Design
`8a8dbc2c`, its revision 6 `70d62fd1`, implementation `cfa2c1ec`, audit fix
`80b2a74c`. Five review rounds on the design, three on the implementation, plus
a pre-push audit that produced the fix commit after the suite was already green.

### The finding that shaped the tranche

The design's main output is arguably not its mechanism but three places where it
found it could not proceed on its own authority, and named them instead of
absorbing them.

**BLOCKED-1.** The reconstruction entrypoint is not in the runtime allowlist:
the functions that rebuild the retained artifacts live in a module the child
never receives. The literal amendment is written out. It widens executable
authority by one module and has to be reviewed as that.

**BLOCKED-2.** Two of the current verifier's checks are retired rather than
moved. An earlier revision said they move to the parent, which is not a
resolution. Against the live worktree they compare the present to the pinned
commit — the exact coupling B-1 is blocked on. Against the materialized tree
they compare a git blob to bytes materialized from that blob, which the M1/M2
chain already asserts more strongly. Retiring a check changes what verification
means, so it is an amendment, not a plumbing decision.

**BLOCKED-3.** The process-control surface is a second native boundary. Naming
its Win32 calls is not specifying it. `NATIVE-INTEROP` requires layouts,
ownership, unwind and error translation first, and an earlier revision offered
one layout oracle and one unwind rule for a surface with eight calls, three
kinds of handle and at least six ways to fail.

### Findings And Resolution

**Metadata a module can grant itself is not authority.** Loader ownership
accepted any loader the finder had made. A module can read its own `__loader__`
and put it on another module's spec. Acceptance now requires four things the
parent recorded itself: the name is one we loaded, the object is the one we
created, `__file__` equals the origin we assigned it, and the loader is the one
we made for that name.

**Position is not what puts a module in scope; having loaded it is.**
`loaded_outside_loader` gated its whole check on the module's current `__file__`
being under the materialized root — and a module's top-level body can assign
`__file__`. A module that set it elsewhere skipped the gate and everything
behind it: object identity, expected origin and exact loader all went unrun. The
one module the audit exists for was the one able to leave its scope. The check
is two passes now: every module we loaded is audited unconditionally, then
everything else in `sys.modules` is scanned for a claim on a position under the
root, by `__file__` or by spec origin. Two hostile tests, because there are two
doors — a body that rewrites both `__file__` and its spec's origin, and one that
replaces the spec object outright. The first rewrites both deliberately, so it
cannot pass by the second pass catching it on position; the unconditional audit
has to be what fires.

**A private module registry is not private.** `load_buffers` took a modules
mapping so tests could pass a dict. The `import` statement consults
`sys.modules` regardless, so a private registry produced a second module object
for every circular import and leaked it into the global table anyway. The
parameter is gone.

**The loader had no materialized-root authority.** `__file__` and origin were
repo-relative, so historical code resolving `Path(__file__)` would land in the
scratch directory, and the bypass check compared against the four origins it
knew rather than against the root — a foreign module loaded from any other file
under that root was invisible to it. Relatedly, root was any non-empty string
and containment was a raw case-sensitive `startswith`, which on Windows treats a
case variant of the same directory as different and accepts a sibling whose name
merely begins with the root.

**Cleanup replaced the error that caused it.** A module body that removed the
finder and then raised surfaced as `LOADER_INSTALL_FAILED`, hiding
`MODULE_EXEC_FAILED` — the rule M2's teardown already carries. And the cleanup
removed only the first finder occurrence, so a body that appended it again left
a live finder answering imports after a successful return.

**A setting can read as a guarantee and provide nothing.** `PYTHONHASHSEED=0` is
ignored under `-I`. Measured, and the determinism claim it supported was
withdrawn rather than re-explained.

**A specified evidence item can be impossible** — two were, the same shape M3-a
produced. **A redundant check reads as load-bearing** — the record loop's
global-bound comparison was deletable with the suite green, because the header
already refuses the declaration above it. **A specification that does not retire
beside the thing replacing it says both and therefore specifies neither** —
revision 4 wrote a new two-branch scratch rule and left three older statements
requiring unconditional removal. **An action can be specified that leaves a real
resource behind** — closing the handles of a suspended process does not
terminate it, and a non-empty scratch directory cannot be removed through a
handle nobody holds.

**Revision 6 corrected the design against its own implementation.** Revision 5
excluded f26, f27 and f28 to BLOCKED-2 together. That is true of f28 and false
of the other two: f26 is the frame's label set and f27 is its internal digest
consistency, both decisions the decoder must make before it can return anything.
An M3-b-1 that omitted them would return a frame it had not finished checking.
The implementation had them because they cannot be left out; the authority said
they belonged to somebody else, and the authority was wrong. The distinction it
was reaching for is now stated directly: the verified frame is not the
reconstruction result.

### Evidence

- Design `ff0099e5…`, implementation `0f82201b…`, tests `cb13f458…`.
- Focused suite 137/137. Mutation battery 36 declared, 36 valid, **zero
  survivors**; deleting the expected-module audit and re-adding the `__file__`
  gate are both caught.
- A third mutation had gone stale against the refactor and was caught by the
  harness's own fail-closed anchor check rather than reported as covered. Six of
  the defects above survived a green suite before their tests existed, which is
  why the harness now fails closed on an anchor that misses or matches twice.
- Canonical precommit against the exact state: exit 0, 201 passing.
- No CI evidence: no pull request has been opened for these commits.

### Not Claimed

- Nothing here executes, spawns, compiles or imports historical code. `ACTIVE`
  is `False`, no availability predicate moved, nothing calls in.
- Canonical precommit passing proves the repository gate still passes with these
  files present. It proves nothing about whether the loader is right.
- The runner's trust root and its TOCTOU window remain accepted assumptions of
  M3, not solved problems.
- How the child receives the materialized root is unresolved. argv, the
  environment and the inbound frame have no field for it, and it is recorded in
  the code as an open dependency rather than defaulted to something convenient.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

Take the three blockers in order and separately: BLOCKED-1's allowlist amendment
for review, BLOCKED-2's retirement decided as an amendment together with the
parent-side result object, and BLOCKED-3 specified to `NATIVE-INTEROP` before
any process-control code is written. M3-b-2 and M3-b-3 do not begin ahead of
them.

## 2026-08-19 — Gate 3 M3-b blockers: two amendments and one slice

On `feat/gate3-historical-materialization`, **not merged to `main`** and not
pushed. BLOCKED-1 `fa10dda8`, BLOCKED-2 `4ea55d3e`, BLOCKED-3 `95838ac0`, after
the record reconciliation `09597ace`. The two amendments were made under
explicit human authorization, each in its own commit, so that each can be
reviewed as an amendment rather than as a line inside a tranche.

### The finding that generalizes

**Nothing failed when executable authority widened.** Adding a fifth module to
`RUNTIME_MODULE_ALLOWLIST` broke no test. Every allowlist assertion compared the
module against itself — the runtime inventory equals
`RUNTIME_MODULE_ALLOWLIST` — and the one test that looked like an independent
binding, the child's copy against the bootstrap's, stays true when both copies
grow together. The suite could not distinguish four modules from five, or from
eleven.

This is the same shape as the M3-b-1 defect it followed: metadata a module can
grant itself is not authority, and here, a list that certifies itself is not a
limit. The fix is the same kind of thing — an authority the subject does not
control. `test_the_allowlist_is_pinned_to_a_literal_outside_the_module` holds
the five paths as a literal in the test file, not derived from the module, the
candidate set or the child, and pins the count, uniqueness and the bytewise
sorted order the wire format depends on.

### BLOCKED-1 — resolved by amendment

Option (a) of three. `gate3_route_v2_ab_candidate.py` joins the allowlist in
both frozen copies: it holds `build_contract_manifest()` and
`build_candidate_set()`, so it is the module whose execution *is* the
reconstruction, and loading it from the pinned commit rather than calling the
present one is the difference between reconstructing history and re-running the
present. Option (b), re-implementing the composition in the trusted runner, was
already rejected because the copy would become the thing that decides what
history was; option (c), the parent importing a historical module, is what the
isolation table forbids outright.

Checked before amending rather than assumed: the module is in the retained
eleven-file candidate set at `8c044400…`, 7251 bytes. Had it not been,
`runtime_module_inventory` would raise `RUNTIME_MODULE_MISSING` and the
amendment would have been unimplementable rather than merely unauthorized.

The new entry sits in bytewise-sorted position, third of five. Not cosmetic:
`encode_stream` emits records in sorted path order and `e3` asserts the exact
byte sequence, so the tuple order and the wire order are one claim.

### BLOCKED-2 — resolved by amendment, in the other document

The amendment belongs to the historical evidence materialization design, now
revision 11, not to the M3-b design that proposed it. Step 9 states that
`_verify_source_commit_inputs` and `_verify_byte_preservation_attributes` are
not part of the reconstruction path and are not reimplemented on it.

The three readings were written into the amendment rather than left in the
proposing document: the parent comparing the live worktree is the original
function unchanged and fails today for the B-1 divergence; the parent comparing
materialized files to the same git blobs is a tautology, because M2 materialized
those bytes from those blobs and verified each digest through a held handle on
the way; supersession by the M1/M2 chain is the correct reading, and is a change
to the verification contract rather than a relocation.

What the amendment does **not** do is build the parent-side result object with
its two "not asserted" markers. It requires that the retirement be visible in
the result; constructing that object is M3-b-3's, and `f28` stays unwritten.

### BLOCKED-3 — written, and deliberately not closed

No authorization closes this one, because it asks for a design slice rather than
an amendment. The slice closes ownership per resource, the unwind matrix and
error translation, and specifies the sensitivity evidence.

**It does not close the layouts, and the reason is the finding.** The oracle
extractor reads official SDK headers out of a digest-pinned `.nupkg`; that
package is not in this environment and no Windows SDK include directory is
installed either — both checked, not assumed. A table of sizes and offsets
written from recollection would sit in the document indistinguishable from a
measured one, and an implementation gated against it would be gated against
somebody's memory. The blocker's own words are *measured rather than assumed*,
so writing them would have satisfied the sentence and defeated it. The slice
names the four steps that produce the artifact and stops.

Two things found by following the requirement to its end:

- **the surface is larger than the blocker said.** Eight calls and three kinds
  of handle becomes fourteen calls and four owned resources, because bounding
  what the child inherits requires `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`, and
  with it `STARTUPINFOEXW`, an attribute list and three more calls. The
  attribute list is not a handle, is not closed with `CloseHandle`, and is the
  only resource on the surface whose leak is silent;
- **the obvious shortcut does not work.** `bInheritHandles = FALSE` with the
  standard handles set in `STARTUPINFOW` produces a child with no usable stdin,
  because those fields are honoured only when inheritance is on.

Also settled: why a job object exists at all — closing the handles of a
suspended process leaves a suspended orphan holding the materialized root open,
which is then unremovable; the assignment window between `CreateProcessW` and
`AssignProcessToJobObject`, narrowed by `CREATE_SUSPENDED` and explicitly not
eliminated, with the stronger `PROC_THREAD_ATTRIBUTE_JOB_LIST` option named and
not taken; and `ResumeThread`'s failure value of `(DWORD)-1`, where a truthiness
check calls every success a failure. Twelve closed error codes replace three,
with timeout separated from wait failure because a timeout is a fact about the
child and a wait failure is a fact about the parent.

### Evidence

- BLOCKED-1: bootstrap `78e241e7…`, child `f929563c…`, bootstrap tests
  `57d1adfa…`, child tests `d764b812…`. Focused tests 178/178, one more than
  before, which is the new pin.
- BLOCKED-2: materialization design `5ed6fe76…`, M3-b design `c419260d…`.
- BLOCKED-3: slice `10af6bfa…`, M3-b design `a815c26b…`.
- Canonical precommit against each of the three states: exit 0, 201 passing.
- **No mutation evidence.** The 36-mutation battery behind `cfa2c1ec` was
  session-local and is not in the repository, so it could not be re-run against
  the widened allowlist.
- No CI evidence: no pull request has been opened for any of these commits.

### Not Claimed

- BLOCKED-1 authorizes a fifth module to be loaded. It loads nothing.
- BLOCKED-2 changes what a passing verification means and touches no code. The
  reconstruction does not perform the retired checks, and does not perform an
  equivalent of them; it relies on an earlier link having done so.
- BLOCKED-3 binds no symbol, starts no process, creates no job, and its layouts
  are unmeasured.
- `ACTIVE` is `False`, no availability predicate moved, nothing calls in, and no
  committed tranche executes historical code.
- Gate 3 remains `NON_SUCCESS`; the consumed pair is unchanged and unusable.

### Next Recommendation

Review the two amendments as amendments. Then take BLOCKED-3's remaining half —
the pinned package, the seven added types, the regenerated oracle — because
until that artifact exists, M3-b-2 has no layouts to be gated against and does
not begin. M3-b-3 is the tranche that is actually unblocked.

## 2026-08-19 — PR #76 merged: M3-b design, M3-b-1, and two authority amendments

Merged to `main` as `f802dba4`. Twelve non-merge commits, `62da7b6f` through
`8cde1a79`, base `5204cd18`. This is a delivery record, not a new review. The
two entries above cover the M3-b implementation and blocker reviews; the record
and cleanup decisions remain in their commit messages and canonical memory.

### What crossed into `main`

Two of the twelve change executable authority or the meaning of passing
verification, and both are now mainline rather than proposed:

- **`fa10dda8`** — `RUNTIME_MODULE_ALLOWLIST` is five modules. Executable
  authority is wider than it was, by `gate3_route_v2_ab_candidate.py`, and the
  literal pin outside the module is what makes a sixth require a visible edit.
- **`4ea55d3e`** — `_verify_source_commit_inputs` and
  `_verify_byte_preservation_attributes` are retired from the reconstruction
  path. What a passing verification means is narrower than it was.

The remaining five substantive commits are three design documents, the M3-b-1
implementation and its audit fix. Five of the twelve are record or cleanup.

### What merging did not do

**BLOCKED-3 is in `main` and still OPEN.** Merging the explicitly incomplete
slice did not close BLOCKED-3, and no authorization closes it either, because it
asked for a slice rather than an amendment. The committed layout oracle covers
eleven types and none of the process-control ones; those rows are missing and the
pinned SDK package needed to generate them is unavailable in this environment.
M3-b-2 does not begin until they exist.

Nothing else moved. `ACTIVE` is `False`, `handle_boundary_available()` is
`False`, no production path reaches any of it, and no committed tranche executes,
spawns, compiles or imports historical code. M4 is not started and B-1 remains
`PAUSED_BEHIND_M4`.

### Evidence

- CI on PR #76: **fourteen checks, twelve pass, two skipped, none failing** —
  including Full Test Suite (2m27s) and Phase Gate Verification (1m57s), which
  were the last two to finish. `mergeStateStatus = CLEAN` and `mergeable =
  MERGEABLE` were confirmed before the merge, not after.
- This is the first CI signal for the M3-b work in this twelve-commit range.
  PR #75 had already supplied CI for M3 and M3-a.
- The local feature branch was fast-forwarded onto `f802dba4`; it was not
  rebased and was not deleted, because M3-b-2, M3-b-3 and B-1 all still need it.
- Supersedes "No CI evidence: no pull request has been opened for these commits"
  in the two entries above; PR #76 supplied it.

### Not Claimed

- CI passing is evidence that the repository gate and the full suite accept this
  state. It is not evidence that the loader is right, that the two amendments
  were the correct decisions, or that the process-control design is sound; those
  rest on exact-digest review.
- Gate 3 remains `NON_SUCCESS`. The consumed A/B pair is unchanged and unusable.
- No historical execution, no process-control integration, no production wiring.

### Next Recommendation

BLOCKED-3's remaining half: the pinned package, the seven added types, the
regenerated oracle. It is the only thing standing between the merged design and
M3-b-2, and it is a bounded errand rather than a design question.

**Superseding the recommendation in the entry above**, which said M3-b-3 is the
tranche that is actually unblocked: that is true of authority and false of
sequence, and the two were conflated. The design is explicit — *"M3-b-1 has no
process and no execution; M3-b-2 has a process but runs fixtures; only M3-b-3
runs history"* — so M3-b-3's states 4 and 5 run inside the child M3-b-2 creates.
The order is BLOCKED-3's oracle rows, then M3-b-2, then M3-b-3, and it does not
admit reordering. Found by an independent review of the reconciliation diff, not
by the author of either entry.

## 2026-08-20 — BLOCKED-3 process-control layout/declaration exact review

### Review Inputs Checked

- `governance/REVIEW_CRITERIA.md`, `governance/AGENT.md`,
  `governance/TESTING.md`, `governance/ARCHITECTURE.md`, and
  `governance/NATIVE-INTEROP.md`.
- `docs/governance/gate3-m3b2-process-control-boundary-design-candidate-20260819.md`.
- Relevant prior-review and anti-pattern entries in `memory/04_review_log.md`
  and `memory/03_knowledge_base.md`.
- Exact four-file worktree diff at SHA-256 values `07491524...`, `fa3f4215...`,
  `562bf482...`, and `4ca79bd0...`; unrelated B-1 and runtime dirty files were
  not inspected.

### Decision Summary

**Verdict: `CHANGES_REQUESTED`. Risk: High.** The measured layouts, pins, pure
declarations, and independent fixtures agree, but one new comment gives the
future process-creation tranche the wrong `STARTUPINFOEXW.StartupInfo.cb` value.

### Governance Audit

- Architecture: pass within this slice. Seven declarations remain inside the
  native adapter; no symbol is bound, no call is made, and no availability or
  `ACTIVE` state moves.
- Native safety: layout checks pass; `_pack_ = 8` remains explicit. One blocking
  operational instruction is wrong and must be corrected before acceptance.
- Test integrity: the extractor fixture remains separate from the artifact and
  locks the added header bytes/digest and all eighteen layouts. Two explanatory
  arithmetic/count descriptions are inaccurate or stale.
- Thread safety: N/A; no thread is created or resumed in this slice.
- Baseline: stable for the scoped boundary and adjacent consumer suites; no full
  repository regression was run by this reviewer.

### Technical Findings

1. **BLOCKING — `STARTUPINFOEXW.StartupInfo.cb` guidance is reversed.**
   - Location: `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_native_boundary.py:496`.
   - Status: open.
   - Evidence: the new comment says to use `sizeof(STARTUPINFOW)` rather than
     `sizeof(STARTUPINFOEXW)`. Microsoft documents the opposite: the embedded
     `STARTUPINFO.cb` must be set to `sizeof(STARTUPINFOEX)` when using the
     extended structure.
   - Rule: `REVIEW_CRITERIA.md` §3.2 and `ARCHITECTURE.md` §1.1-1.2.
   - Required disposition: correct the comment before this declaration becomes
     authority for M3-b-2; the later implementation must use the extended size.

2. **WARNING — independent-evidence explanations contain stale counts and wrong arithmetic.**
   - Locations: `gate3_native_boundary.py:194,416`,
     `gate3_native_expected_layout_extract.py:12,155,194,254`, and
     `test_gate3_native_expected_layout_extract.py:11,225` under the same
     Gate 3 experiment directory.
   - Status: open.
   - Evidence: the closed inventory now has ten headers and eighteen target
     types, not nine/eleven. The basic-limit fields sum to 56 bytes and require
     two four-byte padding gaps, not 52 bytes or four padding locations. The
     recorded offsets and final size 64 are correct.
   - Rule: `TESTING.md` §3.2 and `REVIEW_CRITERIA.md` §3.3.
   - Required disposition: update the prose only; do not change the measured
     offsets, type-set gate, or artifact.

### Validation

- `D:\ai-governance-framework\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --basetemp <workspace-temp> artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/test_gate3_native_boundary.py artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/test_gate3_native_expected_layout_extract.py -q` — **318 passed**.
- The same runner against `test_gate3_historical_materialize.py` — **68 passed**.
- `git diff --check -- <four scoped files>` — clean.
- Reviewer-created pytest temp directories were removed after each run.

### Knowledge Base Alignment

- Anti-patterns checked: 2 — self-validating expected values; digests detached
  from the bytes they claim to bind.
- Regression notes checked: 1 — live worktree bytes must not be mistaken for a
  clean pinned baseline.
- Result: no recurrence in executable logic. The fixture remains independent
  and both digest pins match the current scoped bytes. No new durable
  anti-pattern was identified.

### Not Claimed / Next Recommendation

- The reviewer did not rerun extraction from the external `.nupkg`, full
  regression, canonical precommit, commit, push, or CI.
- `BLOCKED-3` remains open; `ACTIVE` and the availability predicate remain
  false, and M3-b-2 has not begun.
- Correct the two findings, recompute both pinned digests affected by the source
  edits, rerun the 318-case focused suite and 68-case adjacent suite, then
  resubmit the exact four-file digests for review.

### 2026-08-20 Resolution — committed as `fe44deb4`

The first review's inverted `STARTUPINFOEXW.cb` guidance and stale
count/padding prose were corrected, then a fresh-context Claude review found
three more prose defects in the same boundary file: one remaining
"nine-entry" count, the same rejected overbroad `STARTUPINFOW.cb` statement in
an earlier comment, and an incomplete standard-handle condition that omitted
`STARTF_USESTDHANDLES`. The second `cb` occurrence is treated as blocking under
the first review's standard; all three were corrected before commit.

The corrected comments now distinguish standalone `STARTUPINFOW` from embedded
`STARTUPINFOEXW`, require `STARTF_USESTDHANDLES` together with inheritable
handles and `bInheritHandles = TRUE`, and carry no remembered inventory count.
Microsoft's `STARTUPINFOW` and `STARTUPINFOEXW` documentation was the external
behavior source. No measured layout, extractor output, artifact value, type-set
gate, binding, call, or activation state changed in this remediation.

Validation at the committed bytes: the two focused native-layout files plus
the adjacent materializer suite reported 386 passed; canonical
`scripts/run-runtime-governance.sh --mode enforce` reported shared smoke pass
and 201 passed. The implementation commit is `fe44deb4` with four files,
617 insertions and 15 deletions. No push, CI, BLOCKED-3 closure, or M3-b-2 start
is claimed.

### 2026-08-20 Final Acceptance — BLOCKED-3 CLOSED

A fresh-context Claude reviewer verified that `fe44deb4` contains exactly the
four intended files at the delivered blob digests and returned `APPROVED`.
Independent layout derivation, artifact values, the deliberately separate test
fixture and `ctypes` all agree for the seven process-control types; the existing
eleven layouts remain byte-identical. The type-set equality gate remains 18/18,
all seven structures retain `_pack_ = 8`, and no bind, call or activation was
introduced. The author independently reproduced the canonical 201-test gate in
addition to the 386 scoped tests.

The human accepted the process-control design slice and `fe44deb4`. Both closure
conditions are therefore satisfied: the slice is accepted and the measured rows
exist. **BLOCKED-3 is CLOSED.** This supersedes only the earlier OPEN-status and
next-step statements; it does not rewrite their historical review context.
M3-b-2 is now the next implementation tranche, but has not begun and requires a
separately authorized bounded slice after the materialized-root transport is
resolved. No push or CI result is claimed. The branch is named
`feat/gate3-historical-materialization`, while `governance.yml` accepts push
events only for `main` and `feature/**`; pushing this checkpoint therefore adds
remote durability but does not produce CI evidence.

### 2026-08-20 Materialized-Root Transport — ACCEPTED

The owner accepted normative rev2 of
`gate3-m3b2-materialized-root-transport-design-candidate-20260820.md` at exact
SHA-256 `3c3955c0edfe4a370e99b46b272f6bce7a49e2acd2d1a90e39a36affaca0b065`
after fresh-context review returned `APPROVED` with zero findings. The review
independently reproduced the deterministic root leaf, checked extended Windows
path forms against `ntpath.normpath`, and verified the inner and outer bounds.

Rev2 resolved both prior review findings: it names
`MAX_LAUNCH_STREAM_BYTES = 34,703,786` separately from the existing inner
`DERIVED_MAX_STREAM_BYTES = 34,638,232`, and explains why the UTF-8 byte and
UTF-16 code-unit root limits are independently reachable. Acceptance amends
only M3's one-transport sentence and M3-b's stdin sentence: one `GATE3HL\0` v1
envelope now contains exactly one byte-identical M3-a frame plus the root.

The child validates envelope framing, root syntax and the deterministic leaf;
it does not independently verify the absolute base. The parent remains trusted
to bind that base to the live `MaterializedTree` authority. Acceptance resolves
the design dependency only. It does not authorize Python implementation,
M3-b-2 execution, push, PR or CI claims; `ACTIVE=False` and Gate 3 remains
`NON_SUCCESS`.

Provenance correction: normative rev2 was untracked when reviewed and was
overwritten by the acceptance edit before any commit preserved it. Therefore
`3c3955c0...` is an exact-digest record of the bytes the reviewer observed, not
a git-retrievable object, and the claimed post-review delta cannot be proven by
repository diff. The acceptance edit changed both the status block and the
“Acceptance and Authorization Boundary” section; describing it as metadata-only
was incorrect. The commit containing this correction is the first durable
boundary from which future accepted-design edits can be diffed.
<!-- memory_record_projection:review-log:921da1526cc6f0a6b0c204542a41441ea2b20c4a85f9635c4c767cf51f86e8f4 -->
### Canonical memory checkpoint — 2026-08-23-01

- Writer: `governance_tools.memory_record`
- Record identity: `921da1526cc6f0a6b0c204542a41441ea2b20c4a85f9635c4c767cf51f86e8f4`
- Commit binding: `a7f7c8019a4f7583f4f157335eafdb3c9ab55ad1` (bound)
- Record: PR #95 attempt-04 failed-evidence review recorded the disclosure finding and temporary PRIVATE containment. Bindings: pre-run commit 818d2fa6da8420573145e901217b42acffd513a8; evidence commit a7f7c8019a4f7583f4f157335eafdb3c9ab55ad1; terminal SHA-256 d90805c2bb28200e284e72243731a2a8e4f449b5463b1f52b1b5bdf8de9f8356 / 25817 bytes; refs/pull/95/head at a7f7c8019a4f7583f4f157335eafdb3c9ab55ad1 and refs/pull/95/merge at adc9e8abd7cda7eff95874a5155fb74ce112d936. The severe exposure is only the 1870-entry full-tree inventory introduced by a7f7c801; of the seven files in 818d2fa6, only validator-sidecar-probe-manifest.json carries private metadata. A separate, milder username/local-absolute-path and private-internal-subpath exposure predates PR #95 on main and is not remediated by purging PR #95. The repository is temporarily PRIVATE; GitHub Support sensitive-data removal has not been submitted. Finding 3 is PARTIALLY_RESOLVED_PENDING_COMMIT; this uncommitted memory projection is not an immutable anchor.
- Validation boundary: NOT CLAIMED: no new experiment or external mutation was performed; this record preserves the independently reviewed PR #95 bindings and containment state without claiming an immutable memory anchor
- Next action: Keep the repository PRIVATE; submit the scoped GitHub Support removal request separately; commit this memory checkpoint only under separate authorization before treating finding 3 as fully resolved.
- PLAN reconciliation: `not_applicable`

<!-- memory_record_projection:review-log:70f02f4a56d19a0bf6a15ad35da20ca5031ff99db70457bf82f26d430f7771ae -->
### Canonical memory checkpoint — 2026-08-23-05

- Writer: `governance_tools.memory_record`
- Record identity: `70f02f4a56d19a0bf6a15ad35da20ca5031ff99db70457bf82f26d430f7771ae`
- Commit binding: `08990fd3d3a0f6f082f20f3fbf563dc614b0c2ae` (bound)
- Record: Correction to the PR #95 checkpoint record identity 921da1526cc6f0a6b0c204542a41441ea2b20c4a85f9635c4c767cf51f86e8f4: that checkpoint was enabled by the canonical writer expansion committed as 08990fd3d3a0f6f082f20f3fbf563dc614b0c2ae, which added the fixed review-log and active-task-summary projection surfaces; the earlier record did not disclose this tool change. The earlier record commit binding a7f7c8019a4f7583f4f157335eafdb3c9ab55ad1 is within the pending GitHub Support sensitive-data-removal scope and may cease to resolve if that removal rewrites or purges the object. This correction does not replace the earlier PR #95 evidence facts or establish an immutable memory anchor. Findings 3 and 4 are PARTIALLY_RESOLVED_PENDING_COMMIT until this correction is committed.
- Validation boundary: NOT CLAIMED: this is an uncommitted corrective memory projection; it does not prove GitHub Support removal, immutable anchoring, or any new experiment result
- Next action: Review and commit the corrective review-log projection under a separate exact-scope checkpoint; keep the repository PRIVATE and handle the Support request separately.
- PLAN reconciliation: `not_applicable`

<!-- memory_record_projection:review-log:8f7d0de32e6f87b1524253630d9c615830dcefddce224d0fd419f643190858ca -->
### Canonical memory checkpoint — 2026-08-23-07

- Writer: `governance_tools.memory_record`
- Record identity: `8f7d0de32e6f87b1524253630d9c615830dcefddce224d0fd419f643190858ca`
- Commit binding: `08990fd3d3a0f6f082f20f3fbf563dc614b0c2ae` (bound)
- Record: Second provenance correction for PR #95: checkpoint record identity 921da1526cc6f0a6b0c204542a41441ea2b20c4a85f9635c4c767cf51f86e8f4 was produced by a pre-remediation, never-committed working-tree version of the projection surfaces. Commit 08990fd3d3a0f6f082f20f3fbf563dc614b0c2ae later preserved both the projection expansion and its remediation. When the earlier record was written, finding 1 was present: active-task summaries could contain reserved marker syntax and deduplication used an unanchored substring check. A post-hoc full-file inspection confirmed that the three projections existing before this correction were legitimate and that no forged marker was present; that observation does not retroactively grant the earlier record the protections implemented by 08990fd3. This appends to, and does not rewrite, record identities 921da1526cc6f0a6b0c204542a41441ea2b20c4a85f9635c4c767cf51f86e8f4 or 70f02f4a56d19a0bf6a15ad35da20ca5031ff99db70457bf82f26d430f7771ae. Finding 7 and findings 3 and 4 remain PARTIALLY_RESOLVED_PENDING_COMMIT until the PR #95 projection set is committed.
- Validation boundary: NOT CLAIMED: the no-forgery statement is a post-hoc inspection of the three projections that predated this correction; it is not an original write-time guarantee or an immutable memory anchor
- Next action: Submit the complete PR #95 projection set for exact-scope review, then stage only those projection blocks under separate authorization; exclude M3-b-2A and active-task changes.
- PLAN reconciliation: `not_applicable`
