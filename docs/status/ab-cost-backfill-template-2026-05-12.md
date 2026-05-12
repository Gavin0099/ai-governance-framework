# AB Cost Backfill Template (v1.2)

- date: `2026-05-12`
- source_ledger: `docs/ab-v1.2-run-ledger.md`
- target_gap_report: `docs/status/ab-cost-parity-gap-2026-05-12.md`
- purpose: fill true-missing A/B cost fields with evidence-linked values

## Target Runs (Current Gap)

1. `2026-05-07-vsc-A`
2. `2026-05-07-vsc-B`
3. `2026-05-07-vtb-A`
4. `2026-05-07-vtb-B`

## Required Fields Per Run

1. `actionable_fix_latency_sec` (integer seconds)
2. `tokens_per_reviewer_accepted_fix` (integer)
3. `evidence_anchor.prompt_or_log_path` (path)
4. `evidence_anchor.anchor_excerpt` (short quote or line-id)
5. `captured_by` (`human|agent`)
6. `capture_method` (`direct_measurement|reconstructed_with_note`)
7. `confidence` (`high|medium|low`)

## Backfill Record Format

```yaml
- run_id: "2026-05-07-vsc-A"
  actionable_fix_latency_sec: null
  tokens_per_reviewer_accepted_fix: null
  evidence_anchor:
    prompt_or_log_path: ""
    anchor_excerpt: ""
  captured_by: ""
  capture_method: ""
  confidence: ""
  note: ""
```

## Acceptance Gate

All must pass:

1. every target run has non-null values for both cost fields
2. every target run has non-empty evidence anchor path/excerpt
3. reconstructed values include `capture_method=reconstructed_with_note` and `confidence != high`
4. after ledger update, `python governance_tools/ab_cost_parity_audit.py` returns `total_missing_items=0`
5. after ledger update, `python governance_tools/ab_cost_hygiene.py --write` reports `issue_count=0`

## Update Procedure

1. fill records in `docs/status/ab-cost-backfill-data-2026-05-12.yaml`
2. apply values into `docs/ab-v1.2-run-ledger.md`:
   - quick log `tokens_per_accepted_fix`
   - compact run blocks / run records `actionable_fix_latency_sec`, `tokens_per_reviewer_accepted_fix`
3. rerun parity/hygiene tools
4. append close note in daily memory and push

