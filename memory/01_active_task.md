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

## Next Steps

- Validate the local execution baseline before any USB-Hub contract integration work:
  run `pre_task_check.py`, `session_start.py`, and the test suite in a real Python environment.
- Treat current repository maturity as design-level confidence until CLI execution and adapter normalization are verified by local runs.
- After local validation, start Phase 1 of the USB-Hub integration plan with a manual firmware AI session and a `start_session.md` workflow.
- Prepare the integration path between `ai-governance-framework` and `USB-Hub-Firmware-Architecture-Contract` as a dual-repo layered model.
- Add `contract.yaml`-based domain plugin discovery so `session_start` and `post_task_check` can load external documents, rule packs, and validators without hardcoded repo coupling.
- Introduce a validator interface plus external rule-pack loading to support firmware-domain governance while keeping the framework repo focused on horizontal runtime governance.
- Deepen semantic verification, especially public API compatibility and architecture drift reasoning.
- Strengthen workflow interception coverage without over-expanding the runtime into a policy engine.
- Improve change-control artifact consumption so reviewer-facing outputs are easier to use in day-to-day development.

