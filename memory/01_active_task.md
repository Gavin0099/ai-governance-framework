<!-- ARCHIVED: active_task_20260321_172912.md (2026-03-21 17:29:12) -->
<!-- 完整歷史請查閱: archive/active_task_20260321_172912.md -->

> **[歸檔紀錄]** 2026-03-21 17:29:12 — 本檔案已歸檔至 `archive/active_task_20260321_172912.md`
> 歸檔原因: 記憶壓力 EMERGENCY（原始 135 行, 20455 字元）

---

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

---

## Next Steps

- Persist the discovered Python path into local developer workflow setup so the interpreter override does not need to be rediscovered.
- Use the restored local execution baseline before any USB-Hub contract integration work.
- Extend the USB-Hub example into the real `USB-Hub-Firmware-Architecture-Contract` repository with its actual `start_session.md` / checklist content.
- Prepare the integration path between `ai-governance-framework` and `USB-Hub-Firmware-Architecture-Contract` as a dual-repo layered model.
- Refine domain enforcement policy now that validator execution is closed, especially around which domain rule IDs should remain advisory versus move into `hard_stop_rules`.
- Extend the manual USB-Hub startup workflow around the new `contract.yaml` seam and `start_session.md` document handoff.
- Exercise the real USB-Hub advisory path against repo-native patch/evidence artifacts instead of example fixtures.
- Deepen semantic verification, especially public API compatibility and architecture drift reasoning.
- Strengthen workflow interception coverage without over-expanding the runtime into a policy engine, with git-hook / CI-gate hardening as the practical path and not IDE-native generation-time interception.
- Improve change-control artifact consumption so reviewer-facing outputs are easier to use in day-to-day development.
- Keep reducing adoption friction for first-time users by validating example runnable paths and keeping quickstart docs aligned with the actual local environment.
- Consider whether `quickstart_smoke.py` should eventually join CI or docs validation as a dedicated adoption-path regression check.
- Keep IC / EDA Python governance as an evaluated future domain fit, but only after validating a narrow contract-first slice such as Cocotb mapping, golden-model translation, or internal toolchain scripting.
- 2026-03-26 review: `ead27a1` needs follow-up because new reviewer-aid artifacts in `artifacts/workflow-entry/` do not match the minimum envelope enforced for recognizable workflow artifacts.
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
- [x] Promoted memory: SA Layer 1 all 3 checkpoints verified; scripts/plan_summary.py built (96.7% PLAN.md compression); compression provenance Phase 1 via session_start.py + session_end_hook.py + plan_summary.py; semantic boundaries釘住; RTK and Hermes analyzed (deferred)
