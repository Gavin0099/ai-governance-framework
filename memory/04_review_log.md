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

