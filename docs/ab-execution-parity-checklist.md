# A/B Execution Parity Checklist

## Purpose

Prevent false A/B conclusions caused by execution-environment drift.

This checklist is mandatory before any live A/B run (including Round 2B).

## Required Parity Conditions

All conditions must be `true` before execution starts:

1. Fresh session required:
- A and B must run from fresh session state.
- No prior conversation context may carry from A to B.

2. No prior memory carry-over:
- No hidden in-session memory reuse between A and B.
- If memory files are read, both groups must read the same set under same order.

3. Same tool access:
- Same tools enabled for A and B.
- No one-sided tool restrictions or grants.

4. Same file visibility:
- Same file tree visibility and permissions for A and B.
- No extra context files exposed to only one group.

5. Same repo snapshot hash:
- A and B must originate from the same source snapshot hash.

6. Same prompt hash:
- Prompt must match `docs/ab-fixed-prompts-lock.md`.
- Any mismatch = `protocol_drift`.

7. No reviewer hint injection:
- No extra hints, coaching, or nudges to only one group.

8. Same stop condition:
- Same stop rule for both groups (e.g., fixed task boundary).

9. Same timeout boundary:
- Same timeout budget for both groups.

## Required Parity Artifact

Before live execution, generate:

- `execution-parity.json`

Minimum fields:

```json
{
  "run_id": "string",
  "repo_name": "string",
  "fresh_session_required": true,
  "memory_carryover_absent": true,
  "tool_access_equal": true,
  "file_visibility_equal": true,
  "repo_snapshot_hash_equal": true,
  "prompt_hash_equal": true,
  "reviewer_hint_injection_absent": true,
  "stop_condition_equal": true,
  "timeout_boundary_equal": true,
  "parity_ok": true,
  "parity_notes": []
}
```

## Gate Rule

If any parity condition is `false`:

- mark run as `execution_parity_failed`
- do not claim live A/B behavior evidence
- downgrade to `not_claimable_due_to_execution_drift`
