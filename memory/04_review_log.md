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

