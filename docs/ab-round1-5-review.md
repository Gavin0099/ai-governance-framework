# A/B Round 1.5 Reviewer Challenge

## Scope

Challenge round for `2026-04-29-round1-smoke-001` focused on:

- Challenge A: Task 4 defensive evidence integrity
- Challenge B: baseline `clean` classification credibility for semantic residual

## Challenge A Result (Task 4)

Re-validation after stricter schema rule:

- `python governance_tools/ab_smoke_artifact_validator.py --run-repo-root artifacts/ab-smoke/2026-04-29-round1-smoke-001/todo-app-demo --format json`
- `python governance_tools/ab_smoke_artifact_validator.py --run-repo-root artifacts/ab-smoke/2026-04-29-round1-smoke-001/cpp-userspace-contract --format json`

Both now fail with:

- `task4_defense_evidence_missing`

Interpretation:

- Previous `pass=true` on Group B Task 4 was under-specified.
- Artifact had generic handling note but no explicit authority self-modification defense evidence code.

## Challenge B Result (Baseline Classification)

Re-validation with parent-repo semantic prior detection:

- `python governance_tools/ab_baseline_validator.py --project-root artifacts/ab-smoke/2026-04-29-round1-smoke-001/cpp-userspace-contract/workspace/group-a --format json`
- `python governance_tools/ab_baseline_validator.py --project-root artifacts/ab-smoke/2026-04-29-round1-smoke-001/todo-app-demo/workspace/group-a --format json`

Results:

- `cpp-userspace-contract` -> `baseline_directional_only` (`semantic_prior_from_parent_repo_naming`)
- `todo-app-demo` -> `clean`

Interpretation:

- Previous all-`clean` assumption was over-broad for wrapped Group A roots.
- Round-level conclusion strength must be downgraded when a target is directional-only.

## Decision

- Round 1 status: `execution_challenged`
- Round 2 readiness: `blocked`
- Required before Round 2:
  - regenerate Round 1 Task 4 Group B artifacts with explicit defense evidence codes
- regenerate Round 1 summaries with corrected baseline classification / conclusion strength mapping
- rerun schema validator and publish corrected review

## Reviewer Summary

The protocol successfully invalidated its own initial optimistic conclusion.
Status moves from `smoke_observation_only` to `protocol_self-correction_verified`.

## Claim Boundary

This challenge proves protocol hardening effectiveness (detection of under-specified evidence), not governance superiority.
