# A/B Live Execution Capture Contract

## Purpose

Define the minimum evidence chain for real A/B agent-behavior comparison.

This contract separates:

- replayable artifact fixture generation
- live agent behavior execution evidence

## A/B Execution Model

For each target repository:

1. Use the same repo snapshot for Group A and Group B.
2. Group A: remove/disable governance surfaces (sanitized baseline).
3. Group B: keep/enable governance surfaces.
4. Use the same locked prompt text for both groups.
5. Capture raw execution traces before producing task artifacts.

## Required Live-Capture Files (Per Task)

- `raw_prompt.txt`
- `raw_agent_response.md`
- `actions.log`
- `files_changed.txt`
- `tests.log`
- `validator-output.json`
- `task-result.json`

## Required Run-Level Files

- `group-a/baseline-validator.json`
- `group-b/baseline-validator.json` (optional if policy only requires A baseline)
- `summary.json`
- `schema-validation.json`
- `capture-manifest.json` (lists all captured raw files and checksums)

## Claim Rules

If raw live-capture files are missing:

- run may be marked as `fixture_replay_only`
- run must not claim `live_agent_behavior_reproducible`

If raw live-capture files are complete and prompt lock verified:

- run may claim `live_agent_behavior_observed` (not superiority proof)

## Boundary

This contract improves observability and replay auditability.
It does not by itself establish benchmark superiority or statistical proof.
