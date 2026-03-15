# Active Task

## Current Focus

- Keep evolving the repository from evidence-aware runtime governance toward deeper semantic verification and lower-friction workflow embedding.
- Preserve the existing boundary: governance framework first, not a generic AI development platform.

## Current Status

- Runtime lifecycle is active across `session_start`, `pre_task_check`, `post_task_check`, and `session_end`.
- Proposal-time guidance is now part of startup context through `architecture_impact_estimator.py`, `change_proposal_builder.py`, and `session_start.py`.
- Review-facing change-control outputs now exist through `change_control_summary.py` and `change_control_index.py`.
- Shared smoke and CI flows now preserve startup handoff notes, JSON envelopes, and change-control artifacts.
- The recent CI regression in `runtime_hooks/smoke_test.py` was fixed by making human envelope rendering compatible with both shared envelopes and adapter envelopes.
- Local execution baseline is now verified on this workstation by using `AI_GOVERNANCE_PYTHON=C:\Users\daish\AppData\Local\Python\pythoncore-3.14-64\python.exe`.
- Shell entrypoints now have shared Python interpreter resolution via `scripts/lib/python.sh`, and can use `AI_GOVERNANCE_PYTHON` when PATH-based discovery is unavailable.
- Installed git hooks now resolve repo-root paths before loading shared shell helpers, avoiding broken sourcing after installation.
- `scripts/verify_phase_gates.sh` now passes locally, and `scripts/run-runtime-governance.sh --mode smoke` completes successfully with the same interpreter override.
- `contract.yaml`-based domain plugin discovery now exists for `pre_task_check`, `session_start`, and `post_task_check`, including external documents, rule roots, and validator metadata.
- A minimal `examples/usb-hub-contract/` sample now validates the dual-repo seam with `contract.yaml`, domain documents, behavior overrides, external rules, validator preflight, advisory validator execution, and firmware-focused payload extraction.
- USB-Hub advisory validation can now infer interrupt context from `diff_text`, unified diff snippets, and changed C file contents, not just manually supplied `isr_code`.
- The example now includes `post_task_check --checks-file` fixtures so the advisory validator path can be exercised through a file-based runtime entrypoint.
- Cross-repo git hooks can now write and reuse a framework-root pointer under `.git/hooks/ai-governance-framework-root`, so external contract repos can call back into `ai-governance-framework` instead of assuming the governance scripts live inside the target repo.
- Hook installation now has a dedicated verifier via `governance_tools/hook_install_validator.py`, so copied hooks and framework-root wiring can be checked without relying only on dry-run output.
- `scripts/install-hooks.sh` now behaves more like install-and-verify by default, automatically invoking `hook_install_validator.py` after a real install unless `--no-verify` is used.
- External repo onboarding now also has a single readiness entrypoint via `governance_tools/external_repo_readiness.py`, which summarizes hook state, PLAN freshness, and contract resolution/completeness in one report.
- External repo onboarding now also has a shell entrypoint via `scripts/onboard-external-repo.sh`, combining hook installation and readiness assessment into one flow.
- External repo onboarding now also includes a minimal governance smoke stage, so onboarding can fail when a contract resolves incorrectly or its rule roots do not actually power `session_start` / `pre_task_check`.
- External repo onboarding now also emits a JSON onboarding report, so readiness/smoke status can be tracked after the shell session instead of living only in terminal output.
- Onboarding artifacts now keep `latest + history + index`, so external repo setup state has a minimal audit trail rather than a single overwritten report.
- The framework repo can now build a cross-repo onboarding index, so multiple external contract repos can be reviewed together instead of one-by-one.
- `governance_auditor.py` can now optionally incorporate external onboarding state, so framework self-audits can surface external repo adoption drift as part of the same report.
- Cross-repo onboarding views now surface `top_issues`, so reviewer-facing outputs can point to the most urgent external repos instead of only listing raw status rows.
- Cross-repo onboarding `top_issues` now also carry suggested next commands, so reviewer-facing audit output is closer to directly actionable triage.
- External onboarding triage now explicitly points to the next remediation command, reducing the gap between audit output and operator action.
- Direct-script governance entrypoints under `governance_tools/` are now resilient when invoked as `python governance_tools/<tool>.py ...`, not only when imported as a package.
- The local/runtime CI path is back to green after restoring package bootstrap for `change_control_summary.py`, `change_control_index.py`, and related governance-tool entrypoints.
- The repo now includes a minimal external-adoption baseline:
  - `requirements.txt`
  - `start_session.md`
  - clarified example statuses for runnable demo vs walkthrough vs scaffold
- The onboarding path now also has a single executable verifier via `governance_tools/quickstart_smoke.py`, so quickstart docs map to a real smoke command instead of only a sequence of copy-paste steps.
- `scripts/verify_phase_gates.sh` now also exercises `quickstart_smoke.py` against the bundled USB-Hub example, so onboarding drift is covered by the same phase gates as the core runtime tools.
- GitHub Actions runtime/test jobs now install from repo root `requirements.txt` instead of separately installing only `pytest`, reducing drift between local onboarding docs and CI setup.
- The example inventory now has a dedicated readiness checker via `governance_tools/example_readiness.py`, and `verify_phase_gates.sh` also exercises it so example drift is part of the normal regression surface.
- `example_readiness.py` now does a deeper runnable-demo smoke when dependencies are present, including app-object and `/health` route checks; GitHub Actions uses `--strict-runtime` so CI validates runnable examples more strictly than local phase gates.
- The repo now also has explicit release-facing trust signals in-tree:
  - `docs/releases/v1.0.0-alpha.md`
  - `CHANGELOG.md`
  - synchronized `PLAN.md` / status docs for the current alpha stage
- GitLab CI now also mirrors the newer adoption baseline more closely: `requirements.txt`, phase gates, strict example readiness, and runtime governance enforcement are no longer GitHub-only.
- Release-facing trust signals are now partially machine-checked: `release_readiness.py` validates the current alpha note / changelog / README / status-doc alignment, and `verify_phase_gates.sh` now exercises it.
- `governance_auditor.py` can now also include release-facing readiness through `--release-version`, so constitution/runtime drift and release-doc drift can be reviewed in the same high-level audit surface.
- `scripts/verify_phase_gates.sh` now also runs `governance_auditor.py --release-version ...`, so the high-level self-audit path is part of the normal regression surface instead of remaining an optional manual check.
- High-level governance tools now also converge on reviewer-first `summary=...` human output, reducing formatting drift between runtime hooks, release checks, onboarding indexes, and the auditor.
- The repo now also has a single trust-signal entrypoint via `governance_tools/trust_signal_overview.py`, aggregating quickstart, example readiness, release readiness, and governance self-audit into one reviewer-facing overview.
- Release-facing trust signals now also include a dedicated `docs/releases/alpha-checklist.md`, and `release_readiness.py` verifies its presence and basic alignment.
- CI pipelines now also emit `trust_signal_overview.py` artifacts in human / JSON / Markdown forms, so the repo's high-level adoption/release posture can be reviewed or shared after the run instead of only during local CLI use.
- `docs/status/trust-signal-dashboard.md` now provides a stable in-repo landing page for those trust signals, and `release_readiness.py` verifies that this entrypoint remains present and aligned.
- `docs/status/README.md` now provides a stable index over the repo's status-facing pages, so release/status/trust-signal reading order is clearer for external readers.
- `governance_tools/trust_signal_snapshot.py` now provides a formal latest/history/index publishing path for trust signals, and both CI pipelines use it instead of manually stitching overview outputs.
- The trust-signal publisher now also supports `publish-status-dir`, so bundle generation and publish-style status pages can be emitted from the same command.
- Trust-signal snapshot outputs now also include manifest JSON, making it easier for future tooling to resolve the current published snapshot without inferring from filenames alone.

## Next Steps

- Persist the discovered Python path into local developer workflow setup so the interpreter override does not need to be rediscovered.
- Use the restored local execution baseline before any USB-Hub contract integration work.
- Extend the USB-Hub example into the real `USB-Hub-Firmware-Architecture-Contract` repository with its actual `start_session.md` / checklist content.
- Prepare the integration path between `ai-governance-framework` and `USB-Hub-Firmware-Architecture-Contract` as a dual-repo layered model.
- Promote the new advisory validator path into the real USB-Hub contract repo and refine payload shape from real firmware evidence and git patch needs.
- Extend the manual USB-Hub startup workflow around the new `contract.yaml` seam and `start_session.md` document handoff.
- Exercise the real USB-Hub advisory path against repo-native patch/evidence artifacts instead of example fixtures.
- Deepen semantic verification, especially public API compatibility and architecture drift reasoning.
- Strengthen workflow interception coverage without over-expanding the runtime into a policy engine, starting with more reliable external-repo hook installation and execution.
- Improve change-control artifact consumption so reviewer-facing outputs are easier to use in day-to-day development.
- Keep reducing adoption friction for first-time users by validating example runnable paths and keeping quickstart docs aligned with the actual local environment.
- Consider whether `quickstart_smoke.py` should eventually join CI or docs validation as a dedicated adoption-path regression check.
- Keep IC / EDA Python governance as an evaluated future domain fit, but only after validating a narrow contract-first slice such as Cocotb mapping, golden-model translation, or internal toolchain scripting.

