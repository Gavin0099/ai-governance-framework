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

- Deepen semantic verification, especially public API compatibility and architecture drift reasoning.
- Strengthen workflow interception coverage without over-expanding the runtime into a policy engine.
- Improve change-control artifact consumption so reviewer-facing outputs are easier to use in day-to-day development.

