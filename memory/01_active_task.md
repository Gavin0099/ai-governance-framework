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
- Keep IC / EDA Python governance as an evaluated future domain fit, but only after validating a narrow contract-first slice such as Cocotb mapping, golden-model translation, or internal toolchain scripting.

