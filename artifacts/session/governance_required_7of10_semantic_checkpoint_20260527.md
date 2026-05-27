# Required 7/10 Semantic Checkpoint

- date: 2026-05-27
- snapshot: `artifacts/session/governance_repo_matrix_snapshot_20260527_095343.json`
- baseline: required verified `7/10`
- structural readiness: `10/10`
- evidence freshness window: `7 days`

## Why This Checkpoint Exists

This checkpoint freezes the semantic correction that distinguishes:
- structural readiness (candidate-or-above)
- evidence freshness (verified status under fail-closed window)

Without this split, `verified ratio` alone can produce misleading saw-tooth trends
(`10 -> 0 -> 10`) that look like governance instability while structure remains intact.

## Frozen Semantic Decisions

1. **Window width is explicit and configurable**
- `GOV_MATRIX_EVIDENCE_WINDOW_DAYS`
- default: `7`
- lower bound: `1`

2. **Trend now tracks structural and freshness dimensions**
- `required_verified`
- `candidate_or_above`
- `freshness_blocked_count`
- `evidence_window_days`

3. **Closeout maintenance semantics are fixed**
- `closeout_maintenance_mode = event-driven+stale-warning`
- meaning:
  - refresh evidence on real workflow boundaries (commit/push/session-end)
  - surface stale evidence as warning/blocker
  - avoid cron-only unconditional auto-stamping

## Interpretation at This Point

- `7/10 verified` with `10/10 structural readiness` is a healthy state.
- Remaining gap is freshness/head alignment on specific repos, not schema weakness.
- Contract/schema/metric authority remains fail-closed and unchanged.

