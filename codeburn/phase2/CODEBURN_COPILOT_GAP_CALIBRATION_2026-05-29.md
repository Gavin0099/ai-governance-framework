# CodeBurn Copilot Coverage Gap Calibration (2026-05-29)

Scope: coverage calibration only (no authority upgrade, no feature expansion).
Mirror methodology: same fixture-driven approach used for Codex gap calibration (2026-05-28).

Authority boundary unchanged:
- analysis_safe_for_decision=false
- decision_usage_allowed=false
- completions_excluded=1 (schema-enforced on every row)

## Commands

- Baseline pass command
  - `$env:PYTHONPATH='e:\BackUp\Git_EE\ai-governance-framework'; python codeburn/phase2/codeburn_copilot_smoke.py --csv codeburn/phase2/examples/copilot_smoke_fixture.csv --db artifacts/codeburn_copilot_smoke.db --json`
- Gap calibration command pattern
  - `$env:PYTHONPATH='e:\BackUp\Git_EE\ai-governance-framework'; python codeburn/phase2/codeburn_copilot_smoke.py --csv codeburn/phase2/examples/<fixture>.csv --db artifacts/smoke_<fixture>.db --json`

## Fixture List And Result

| Fixture | Intent | Smoke exit | processed_rows | inserted_events | skipped_duplicates | quarantined_rows | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| copilot_gap_empty.csv | header only, no data rows | 0 | 0 | 0 | 0 | 0 | expected zero-event behavior |
| copilot_gap_all_quarantined.csv | all rows invalid (negative aic / empty login / non-numeric aic) | 0 | 3 | 0 | 0 | 3 | all 3 rows quarantined; ingest still operational |
| copilot_gap_missing_model_col.csv | required column `model` absent from CSV | 0 | 0 | 0 | 0 | 0 | **coverage gap**: early return with result.errors; smoke output identical to empty — missing-column state is not surfaced |
| copilot_gap_negative_aic.csv | mixed valid + negative aic_quantity row | 0 | 3 | 2 | 0 | 1 | negative row quarantined; valid rows admitted |
| copilot_gap_date_format_variation.csv | date in MM/DD/YYYY format | 0 | 2 | 2 | 0 | 0 | dates normalized to YYYY-MM-DD; admitted |
| copilot_gap_multi_model_mix.csv | multiple users, multiple models, multiple dates | 0 | 5 | 5 | 0 | 0 | all admitted; cross-model aggregation boundary still enforced at query layer |
| copilot_gap_duplicate_rows.csv | same (date, user, model) row appears twice | 0 | 3 | 2 | 1 | 0 | duplicate correctly skipped; dedup is operational |

## Key Observations

### Observation 1 — missing_required_column is silent in smoke output
- `copilot_gap_missing_model_col` produces `processed_rows=0, inserted_events=0, quarantined_rows=0`.
- This is **identical** to `copilot_gap_empty`.
- The ingestor returns early with `result.errors` populated but the smoke harness does not expose
  `result.errors` in its JSON output.
- This is a known coverage gap: a CSV with missing required columns is indistinguishable from an
  empty file in the current smoke summary contract.
- Mitigation: deferred (no immediate fix planned); error state is observable by inspecting
  `CopilotIngestResult.errors` directly.

### Observation 2 — date format normalization is operational
- MM/DD/YYYY input in `copilot_gap_date_format_variation` is correctly normalized to YYYY-MM-DD.
- Not a gap; behavior is as designed.

### Observation 3 — all_quarantined case exits 0
- `copilot_gap_all_quarantined` exits 0 with `inserted_events=0` and `quarantined_rows=3`.
- The smoke harness considers this a pass (authority flags vacuously true when no events).
- This is consistent with Codex behavior (corrupted JSONL also exits 0).
- Not a gap; intended behavior.

### Observation 4 — CP-2 cross-model boundary not testable at ingest level
- The ingestor correctly admits rows for multiple models independently (multi_model_mix: 5/5 admitted).
- The CP-2 aggregation-forbidden constraint applies at the query/analysis layer, not the ingest layer.
- The smoke harness cannot test CP-2 compliance — this is a known architectural gap in smoke coverage.

## Coverage Gap Summary

| Gap | Severity | Status |
|---|---|---|
| missing_required_column not surfaced in smoke JSON output | LOW | Deferred — observable via CopilotIngestResult.errors; no smoke contract change planned |
| CP-2 aggregation guard not smoke-testable | LOW | Deferred — query-layer constraint; out of scope for ingest smoke |

## Updated Coverage Matrix (Copilot)

| Capability | Evidence command | Result | Tested coverage | Coverage gap | Allowed analysis-only claim | Forbidden decision claim | Decision authority | Blocker / gap |
| ---------- | ---------------- | ------ | --------------- | ------------ | --------------------------- | ------------------------ | ------------------ | ------------- |
| Copilot ingest baseline smoke | `codeburn_copilot_smoke.py --csv ...copilot_smoke_fixture.csv` | Pass (exit 0) | accepted/skip/quarantine/provenance/authority-flag/completions-excluded checks | none for baseline fixture | Baseline fixture path smoke-verified for analysis-only evidence collection | any decision-authoritative claim | none | none |
| Copilot gap fixture calibration | `codeburn_copilot_smoke.py --csv ...copilot_gap_*.csv` | Pass (exit 0 for all 7 gap fixtures) | empty / all-quarantined / missing-column / negative-aic / date-format-variation / multi-model-mix / duplicate-rows observed with fixture assertions | missing_required_column not surfaced as warning in smoke output; CP-2 not testable at ingest layer | Ingest behavior is observable and bounded for tested fixture cases; still analysis-only | cost/budget gate, billing truth, efficiency ranking, decision authority | none | known gap: missing_required_column silent in smoke summary (deferred); CP-2 aggregation guard is query-layer only |

## Recommendation

- recommendation: limited proceed
- reason: calibration achieved with explicit coverage evidence and explicit harness limitation; authority boundary preserved; all 7 fixtures exit 0.
- README wording change in this step: no
- Parity with Codex calibration: achieved (7 fixtures, same exit-0 pass pattern, coverage gaps explicitly recorded)
