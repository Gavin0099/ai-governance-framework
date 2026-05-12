# AB Cost Parity Gap Report

- source: `docs/ab-v1.2-run-ledger.md`
- task_count: `3`
- total_missing_items: `8`

## Task Gap Summary

| task_id | run_count | quick_log_rows | missing_items |
|---|---:|---:|---:|
| cfu-failure-state-remediation-01 | 2 | 2 | 0 |
| cfu-validate-two-boundary-cleanup-01 | 2 | 2 | 4 |
| cfu-version-semantics-coordination-01 | 2 | 2 | 4 |

## Detailed Missing Fields

### cfu-failure-state-remediation-01


### cfu-validate-two-boundary-cleanup-01

- run `2026-05-07-vtb-A` (A): missing `actionable_fix_latency_sec, tokens_per_reviewer_accepted_fix`
- run `2026-05-07-vtb-B` (B): missing `actionable_fix_latency_sec, tokens_per_reviewer_accepted_fix`

### cfu-version-semantics-coordination-01

- run `2026-05-07-vsc-A` (A): missing `actionable_fix_latency_sec, tokens_per_reviewer_accepted_fix`
- run `2026-05-07-vsc-B` (B): missing `actionable_fix_latency_sec, tokens_per_reviewer_accepted_fix`
