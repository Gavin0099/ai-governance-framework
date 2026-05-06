# Token Observability Test Plan

Date: 2026-05-06  
Owner: AI Governance Framework / Repo Integrator

## 1) Objective

Validate token observability behavior across multiple repos with sufficient run volume, and verify:

- token fields are always present in output shape
- null/unknown behavior is explicit when token source is unavailable
- decision boundary remains unchanged (`decision_usage_allowed=false`)

This plan is observability-only, not a release authority gate.

## 2) Repo Scope

Recommended 3–4 repos:

- `CFU`
- `cli`
- `meiandraybook`
- Optional control group: one repo with no governance history

## 3) Entry Command (Canonical)

Use one canonical entry for comparability:

```powershell
python -m governance_tools.external_repo_onboarding_report --format json
```

Optional secondary sample (non-canonical, supplementary only):

```powershell
python -m governance_tools.external_repo_smoke --format json
```

## 4) Run Volume Requirement

Minimum valid sample window:

- per repo: at least `10` runs (target `20`)
- duration: at least `3` days (target `7`)
- include mixed task contexts (simple checks / modification flows / failure paths)

If minimum is not reached, mark result as `insufficient_sample`.

## 5) Artifact Storage

Store raw JSON without modification:

```text
artifacts/token-observability/<repo>/<YYYY-MM-DD>/<run-id>/
  onboarding.json
  smoke.json                # optional
  meta.json                 # optional: command, timestamp, operator, note
```

Example:

```text
artifacts/token-observability/cli/2026-05-06/run-001/onboarding.json
```

## 6) Canonical Fields To Observe

Primary fields (from `onboarding.json -> smoke.token_summary`):

- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `token_source_summary`
- `token_observability_level`
- `provenance_warning`
- `decision_usage_allowed`

## 7) Field Mapping Rules

Use this normalization order:

1. `smoke.token_summary.<field>`
2. `smoke.post_task_cases[*].token_summary.<field>` (first `ok=true` case, else first case)
3. fallback default:
   - tokens = `null`
   - source = `unknown`
   - observability = `none`
   - provenance_warning = `not_provided_by_smoke`
   - decision_usage_allowed = `false`

## 8) Pass / Watch Criteria

### Pass (observability shape)

- all runs include normalized token summary fields
- missing-token scenarios are explicit (`null/unknown/none`)
- `decision_usage_allowed` remains `false` in all runs

### Watch (non-blocking)

- high ratio of `unknown/none` over long window
- unstable output shape between repos
- repeated compatibility warnings that suppress smoke success

### Fail (pipeline quality)

- required token fields missing after normalization
- `decision_usage_allowed` becomes non-false unexpectedly
- raw artifact missing or overwritten

## 9) Daily Execution Procedure

For each repo each day:

1. run onboarding json command
2. save raw output to dated run folder
3. record one-line note (task context / expected token source)
4. do not rewrite raw artifact

## 10) Cross-Run Aggregation (After Window Completes)

Aggregate per repo:

- total runs
- `% total_tokens == null`
- distribution of `token_source_summary`
- distribution of `token_observability_level`
- `% decision_usage_allowed == false` (must be 100%)
- warning/error co-occurrence with token unknown

Recommended output:

```text
docs/payload-audit/token-observability-cross-run-summary-<YYYY-MM-DD>.md
```

## 11) Aggregation Table Template

```md
| repo | runs | total_tokens_null_pct | source_provider_pct | source_unknown_pct | obs_none_pct | decision_usage_allowed_false_pct | notes |
|------|------|-----------------------|---------------------|--------------------|-------------|-----------------------------------|-------|
| CFU  | 20   | 85%                   | 15%                 | 85%                | 85%         | 100%                              | ...   |
```

## 12) Non-Claims

- This plan does not prove model quality or cost efficiency.
- This plan does not authorize governance decisions from token fields.
- This plan does not replace release/readiness authority contracts.

