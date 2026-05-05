# Token Cross-Repo Test Result — Enumd (2026-05-05)

> Plan ref: `docs/token-cross-repo-test-plan-v0.1.md`
> Framework version: latest (post-commit 288521a)
> Session: `be5290a7-3514-4155-bc75-87cd76f243ff`
> DB: `codeburn/phase1/examples/enumd_cross_repo_test_20260505.db`

---

## Result Block

```yaml
repo: Enumd
date: 2026-05-05
distribution_slice_validation: pass
token_count:
  prompt_tokens: null
  completion_tokens: null
  total_tokens: null
token_trust:
  token_source_summary: unknown
  token_observability_level: none
  provenance_warning: provenance_unverified
decision_usage_allowed: false
analysis_safe_for_decision: false
notes: >
  Controlled session (local provider, token_source=unknown, no token counts passed).
  All token_count values are null and observability_level=none — expected outcome
  for local/no-telemetry steps. All boundary constraints hold.
  Repo does not satisfy controlled-exposure target criteria (all-unknown token source,
  no mixed/estimated provenance signal); consistent with controlled-exposure guide note
  that unknown-only repos provide limited signal for the observation window.
```

---

## Step Run

| Field | Value |
|-------|-------|
| Step kind | `test` |
| Command | `python scripts/check-mapping-spec-compliance.py` |
| Exit code | 0 |
| Duration | 1056 ms |
| Token source | `unknown` |
| Changed files | 0 |

---

## Boundary Verification

| Flag | Value | Required |
|------|-------|----------|
| `decision_usage_allowed` | `false` | `false` ✓ |
| `analysis_safe_for_decision` | `false` | `false` ✓ |
| `governance_decision_usage_allowed` | `false` | `false` ✓ |
| `operational_guard_usage_allowed` | `false` | `false` ✓ |

---

## Structural Field Check

| Field | Present | Value |
|-------|---------|-------|
| `token_count.prompt_tokens` | ✓ | null |
| `token_count.completion_tokens` | ✓ | null |
| `token_count.total_tokens` | ✓ | null |
| `token_trust.token_source_summary` | ✓ | `unknown` |
| `token_trust.token_observability_level` | ✓ | `none` |
| `token_trust.provenance_warning` | ✓ | `provenance_unverified` |

All required keys structurally present → `distribution_slice_validation: pass`.

---

## Closeout Note

This result confirms token observability/distribution slice only.
It does not constitute full regression coverage or system correctness validation for Enumd.
Per plan closeout rule: cross-repo test closeout is valid only for token observability/distribution slice.
