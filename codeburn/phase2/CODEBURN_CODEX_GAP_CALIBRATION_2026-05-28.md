# CodeBurn Codex Coverage Gap Calibration (2026-05-28)

Scope: coverage calibration only (no authority upgrade, no feature expansion).

Authority boundary unchanged:
- analysis_safe_for_decision=false
- decision_usage_allowed=false

## Commands

- Baseline pass command
  - `$env:PYTHONPATH='e:\BackUp\Git_EE\ai-governance-framework'; python codeburn/phase2/codeburn_codex_smoke.py --artifact codeburn/phase2/examples/codex_smoke_fixture.jsonl --db artifacts/codeburn_codex_smoke.db --session-id codex-calibration-20260528 --json`
- Gap calibration command pattern
  - `$env:PYTHONPATH='e:\BackUp\Git_EE\ai-governance-framework'; python codeburn/phase2/codeburn_codex_smoke.py --artifact codeburn/phase2/examples/<fixture>.jsonl --db artifacts/smoke_<fixture>.db --session-id codex-gap-<fixture> --json`

## Fixture List And Result

| Fixture | Intent | Smoke exit | processed | skipped | quarantined | admitted_with_warning | Notes |
|---|---|---:|---:|---:|---:|---|
| codex_gap_empty_session.jsonl | empty session | 0 | 0 | 1 | 0 | 0 | expected skip-only behavior |
| codex_gap_corrupted_jsonl.jsonl | corrupted JSONL | 0 | 1 | 0 | 1 | 0 | malformed line quarantined |
| codex_gap_missing_rate_limits.jsonl | missing rate_limits | 0 | 1 | 0 | 0 | 0 | admitted; rate_limits currently not validated |
| codex_gap_malformed_rate_limits.jsonl | malformed rate_limits | 0 | 1 | 0 | 0 | 0 | admitted; malformed rate_limits currently not validated |
| codex_gap_missing_token_stats.jsonl | missing token stats | 0 | 1 | 0 | 0 | 1 | admitted_with_warning (incomplete token fields) |
| codex_gap_multi_session_mix.jsonl | multiple sessions in one artifact | 0 | 2 | 2 | 0 | 0 | two token_count admitted; two session_meta skipped |
| codex_gap_old_new_mixture.jsonl | old/new session mixture | 0 | 2 | 0 | 0 | 0 | both token_count admitted |

## Calibration Interpretation

- Existing Codex ingest path remains operational for observation evidence collection in tested fixtures.
- Smoke harness now separates:
  - common invariants (authority/provenance/total_tokens/sqlite surface)
  - baseline-only numeric invariant assertions
  - fixture-specific assertions by fixture intent
- `missing_token_stats` is explicitly surfaced as `admitted_with_warning_records`.
- `missing_rate_limits` / `malformed_rate_limits` are currently admitted by design and recorded as known coverage gaps (no field-level validation yet).

## Updated Coverage Matrix (Codex)

| Capability | Evidence command | Result | Tested coverage | Coverage gap | Allowed analysis-only claim | Forbidden decision claim | Decision authority | Blocker / gap |
| ---------- | ---------------- | ------ | --------------- | ------------ | --------------------------- | ------------------------ | ------------------ | ------------- |
| Codex ingest baseline smoke | `codeburn_codex_smoke.py --artifact ...codex_smoke_fixture.jsonl` | Pass (exit 0) | accepted/skip/quarantine/provenance/authority-flag checks | none for baseline fixture | Baseline fixture path smoke-verified for analysis-only evidence collection | any decision-authoritative claim | none | none |
| Codex gap fixture calibration via existing smoke harness | `codeburn_codex_smoke.py --artifact ...codex_gap_*.jsonl` | Pass (exit 0 for all listed gap fixtures) | empty/corrupted/missing-rate-limits/malformed-rate-limits/missing-token-stats/multi-session-mix/old-new-mix observed with fixture assertions | no field-level validation for `rate_limits`; `missing_token_stats` admitted-with-warning only | Ingest behavior is observable and bounded for tested fixture cases; still analysis-only | cost/budget gate, billing truth, efficiency ranking, decision authority | none | known gap: `rate_limits` validation deferred (not in this calibration scope) |

## Recommendation

- recommendation: limited proceed
- reason: calibration achieved with explicit coverage evidence and explicit harness limitation; authority boundary preserved.
- README wording change in this step: no
