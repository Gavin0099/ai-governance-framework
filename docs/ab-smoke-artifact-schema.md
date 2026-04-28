# A/B Smoke Artifact Schema

## Purpose

Define the minimum machine-readable artifact structure for A/B smoke runs.

Without schema, "artifact exists" is not sufficient for reviewer judgment.

## Scope

This schema defines minimum required fields only.
Additional fields are allowed, but required fields must remain stable.

## Task Artifact Schema (`task-01.json`, `task-02.json`, `task-03.json`, `task-04.json`)

```json
{
  "run_id": "string",
  "repo_name": "string",
  "group": "A|B",
  "task_id": "task-01|task-02|task-03|task-04",
  "prompt_hash": "string",
  "agent_response_summary": "string",
  "actions_taken": [],
  "files_modified": [],
  "tests_run": [],
  "governance_findings": [],
  "pass": false,
  "failure_codes": [],
  "claim_boundary": "string"
}
```

### Field Notes

- `prompt_hash`: hash of fixed prompt text to prevent post-hoc prompt drift.
- `actions_taken`: normalized action list (`read`, `edit`, `test`, `push`, `reject`, `escalate`...).
- `governance_findings`: structured findings, not prose-only.
- `failure_codes`: stable failure taxonomy keys.
- `claim_boundary`: explicit limitation statement for this task result.

## Summary Artifact Schema (`summary.json`)

```json
{
  "run_id": "string",
  "repo_name": "string",
  "baseline_classification": "baseline_invalid|baseline_degraded|baseline_directional_only|clean",
  "comparison_allowed": true,
  "conclusion_strength": "do_not_compare|compare_with_caution|directional_observation_only|comparative_smoke_result_allowed",
  "group_a_results": {},
  "group_b_results": {},
  "observed_delta": [],
  "run_protocol_violation": false,
  "final_claim": "string"
}
```

### Field Notes

- `baseline_classification`, `comparison_allowed`, `conclusion_strength` must align with `ab_baseline_validator.py`.
- `group_a_results` and `group_b_results` should contain per-task pass/fail and failure codes.
- `observed_delta` records behavior-level differences only (not benchmark claims).
- `run_protocol_violation=true` forces downgrade of `final_claim`.

## Minimal Validation Rules

1. Required keys must exist.
2. `group` must be `A` or `B`.
3. `task_id` must be one of fixed tasks.
4. If `pass=false`, `failure_codes` must be non-empty.
5. If `run_protocol_violation=true`, `final_claim` must include protocol-drift downgrade wording.

## Claim Boundary Rule

Artifact validity means:

- "run evidence is structurally complete"

It does not mean:

- "governance effectiveness is proven statistically"
- "production readiness is established"
