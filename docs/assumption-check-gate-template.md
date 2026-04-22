# Assumption Check Gate Template

Use this as a pre-implementation prompt prefix.

## Required Gate

```text
[Assumption Check - Must Complete First]

Before proposing implementation changes, complete all items:

1) List the key assumptions in the request.
2) List at least two alternative root causes (must be different layers).
3) List current evidence supporting the original assumption.
4) If evidence is insufficient, list required information instead of editing.
5) If this is an unverified assumption, rewrite the task as validation steps.

Only after all five are complete, propose code changes.
```

## Structured Output (Advisory)

Put this at the start of the response:

```json
{
  "assumptions": ["..."],
  "alternative_causes": ["...", "..."],
  "evidence": ["..."],
  "action_decision": "proceed | need_more_info | reframe"
}
```

Notes:
- `need_more_info` or `reframe` means do not jump directly to implementation.
- This layer is workflow-level and advisory. It is not a governance core gate.
