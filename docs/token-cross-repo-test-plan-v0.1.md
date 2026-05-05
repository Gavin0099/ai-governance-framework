# Token Cross-Repo Test Plan v0.1

## Purpose
Use current framework baseline to validate token observability status in other repos without changing decision/gating behavior.

## Scope
- In scope:
  - `token_count` presence and values
  - `token_trust` fields (`token_source_summary`, `token_observability_level`, `provenance_warning`)
  - non-decision boundary flags
- Out of scope:
  - full regression
  - authority integration
  - token-based enforcement / budget stop

## Required Boundary (must stay true)
- `decision_usage_allowed = false`
- `analysis_safe_for_decision = false`
- token fields are observational only

## Per-Repo Test Steps
For each target repo:

1. Run one real or controlled CodeBurn session that generates report artifacts.
2. Generate analyze/report output with current framework version.
3. Record and verify fields:
   - `token_count.prompt_tokens`
   - `token_count.completion_tokens`
   - `token_count.total_tokens`
   - `token_trust.token_source_summary`
   - `token_trust.token_observability_level`
   - `token_trust.provenance_warning`
   - `decision_usage_allowed`
   - `analysis_safe_for_decision`
4. Classify result:
   - `pass`: fields present and boundary flags remain false
   - `degraded`: fields present but trust/provenance unexpected
   - `blocked`: no valid output or runtime execution failed

## Expected Interpretations
- `step_level` means granularity is fine enough for per-step visibility.
- `mixed(provider, estimated)` is valid if provenance warning is present.
- `provenance_warning = mixed_sources` is expected for mixed source runs.
- No warning does not imply authority for decision usage.

## Report Template
Use this block per repo:

```yaml
repo: <repo-name>
date: <YYYY-MM-DD>
distribution_slice_validation: pass|degraded|blocked
token_count:
  prompt_tokens: <int|null>
  completion_tokens: <int|null>
  total_tokens: <int|null>
token_trust:
  token_source_summary: <provider|estimated|mixed(... )|unknown>
  token_observability_level: <none|coarse|step_level>
  provenance_warning: <mixed_sources|provenance_unverified|null>
decision_usage_allowed: false
analysis_safe_for_decision: false
notes: <short finding>
```

## Closeout Rule
Cross-repo test closeout is valid only for token observability/distribution slice.
It must not be interpreted as full system correctness or full regression coverage.
