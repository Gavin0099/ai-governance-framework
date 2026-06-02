---
name: runtime-smoke
description: Validate runtime governance entrypoints for this repository or an external contract repo. Use when Codex needs to run or interpret quickstart smoke, session_start smoke, dispatcher replay, shared runtime wrapper smoke, or contract-aware runtime validation without doing the full reviewer-handoff or release flow.
---

# Runtime Smoke

Use this skill for fast runtime validation and triage.

## Workflow

1. Pick the narrowest smoke entrypoint that answers the question.
2. Start with `quickstart_smoke.py` for onboarding-path validation.
3. Use `runtime_hooks/smoke_test.py` for direct runtime event replay.
4. Use `runtime_hooks/dispatcher.py` when the shared-event JSON path matters.
5. Use `scripts/run-runtime-governance.sh --mode smoke` when validating the shell wrapper path.
6. If a smoke path fails, separate:
   - contract resolution failure
   - PLAN freshness failure
   - rule-root or validator loading failure
   - shared wrapper / path override failure

## Commands

Read `references/commands.md` for the standard smoke commands.

## Gotchas

Read `references/gotchas.md` before interpreting failures or changing smoke coverage.

## Output Expectations

- State which smoke entrypoint was used.
- Report whether the failure is repo-local, contract-local, or wrapper-path-specific.
- Prefer one smallest reproducer command when handing off.
