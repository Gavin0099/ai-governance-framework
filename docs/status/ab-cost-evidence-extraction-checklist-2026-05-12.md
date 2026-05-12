# AB Cost Evidence Extraction Checklist

- date: `2026-05-12`
- scope: fill scalar cost values for:
  - `2026-05-07-vsc-A`
  - `2026-05-07-vsc-B`
  - `2026-05-07-vtb-A`
  - `2026-05-07-vtb-B`

## Required Inputs Per Run

1. run start timestamp (`t0`)
2. first reviewer-accepted material fix timestamp (`t1`)
3. total token usage in same run (`tokens_total`)
4. accepted change count (ledger baseline currently `4`)

## Extraction Steps

1. open source transcript/log for run
2. locate first assistant action that produced reviewer-accepted material change
3. record `t0`, `t1`, and token source evidence
4. compute:
   - `actionable_fix_latency_sec = t1 - t0`
   - `tokens_per_reviewer_accepted_fix = round(tokens_total / accepted_change_count)`
5. update `docs/status/ab-cost-backfill-data-2026-05-12.yaml`
6. run backfill apply:
   - `python governance_tools/ab_cost_backfill_apply.py --write`
7. validate:
   - `python governance_tools/ab_cost_hygiene.py --write`
   - `python governance_tools/ab_cost_parity_audit.py`

## Evidence Discipline

1. no inferred values without explicit source anchor
2. if any scalar cannot be proven, keep `insufficient_data`
3. `capture_method=reconstructed_with_note` cannot use `confidence=high`

