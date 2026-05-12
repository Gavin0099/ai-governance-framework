# AB Cost Backfill Completion Plan

- date: `2026-05-12`
- scope: close remaining true-missing cost metrics for:
  - `2026-05-07-vsc-A`
  - `2026-05-07-vsc-B`
  - `2026-05-07-vtb-A`
  - `2026-05-07-vtb-B`

## Current State

1. `docs/ab-v1.2-run-ledger.md` no longer has `TBD` in cost fields for these runs.
2. All four runs remain `insufficient_data` for:
   - `actionable_fix_latency_sec`
   - `tokens_per_reviewer_accepted_fix`
3. Source anchors exist only as path-level references (`CFU` / `CFU_non_ai_governance`), not scalar telemetry.

## Blocking Gap

No repo-local artifact currently stores per-run scalar values for those four run IDs.

## Required Inputs To Close

For each target run, provide:

1. raw transcript path containing the run interaction
2. timestamp evidence for:
   - run start
   - first reviewer-accepted material fix
3. token usage evidence from the same run source (or authoritative telemetry export)
4. accepted change count confirmation (`accepted_change_count=4` already present in ledger)

## Deterministic Fill Rules

1. `actionable_fix_latency_sec = first_accepted_fix_timestamp - run_start_timestamp`
2. `tokens_per_reviewer_accepted_fix = total_run_tokens / accepted_change_count`
3. rounding:
   - latency: integer seconds
   - tokens: integer (nearest)
4. capture metadata required:
   - `capture_method`
   - `confidence`
   - `evidence_anchor.prompt_or_log_path`
   - `evidence_anchor.anchor_excerpt`

## Completion Gate

All must pass:

1. backfill data file has no `insufficient_data` for those four runs
2. ledger quick log `tokens_per_accepted_fix` populated with numeric values
3. `python governance_tools/ab_cost_hygiene.py --write` returns `issue_count=0`
4. `python governance_tools/ab_cost_parity_audit.py` returns `total_missing_items=0`

## Boundary

Until scalar telemetry is provided, these four runs must remain observationally valid but cost-incomplete.
Do not infer or fabricate numeric values.

