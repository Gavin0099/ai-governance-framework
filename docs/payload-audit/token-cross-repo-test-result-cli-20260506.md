# Token Cross-Repo Test Result ¡X cli (2026-05-06)

> Plan ref: docs/token-cross-repo-test-plan-v0.1.md
> Session: e9223354-dcab-4b16-80f8-b069deaef224
> DB: codeburn/phase1/examples/token_cross_repo_cli_20260506.db

## Result Block

~~~yaml
repo: cli
date: 2026-05-06
distribution_slice_validation: pass
token_count:
  prompt_tokens: 120
  completion_tokens: 45
  total_tokens: 375
token_trust:
  token_source_summary: estimated
  token_observability_level: step_level
  provenance_warning: provenance_unverified
decision_usage_allowed: false
analysis_safe_for_decision: false
notes: controlled estimated-token session; boundary flags remain non-decisional
~~~

## Analyze Evidence

- step_count: 2
- token_observability_level: step_level
- decision_usage_allowed: false
- analysis_safe_for_decision: false

## Boundary Verification

| Flag | Value | Required |
|---|---|---|
| decision_usage_allowed | false | false |
| analysis_safe_for_decision | false | false |
| governance_decision_usage_allowed | false | false |
| operational_guard_usage_allowed | false | false |

## Closeout Note

This result confirms token observability/distribution slice only.
It does not constitute full regression coverage or full system correctness validation.
