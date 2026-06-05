# CodeBurn Codex Gap Coverage Calibration (Mainline) - 2026-05-28

Scope: Phase 2 Codex ingest calibration only.

Out of scope in this run:
- L0 manual ingest changes
- Copilot ingest changes
- authority upgrade

Boundary unchanged:
- analysis_safe_for_decision=false
- decision_usage_allowed=false

## Commands Run

```powershell
$env:PYTHONPATH='e:\BackUp\Git_EE\ai-governance-framework'
python codeburn/phase2/codeburn_codex_smoke.py --artifact codeburn/phase2/examples/<fixture>.jsonl --db artifacts/codex_mainline_<fixture>.db --session-id codex-mainline-<fixture> --json
```

## Fixture List

- codex_gap_empty_session.jsonl
- codex_gap_corrupted_jsonl.jsonl
- codex_gap_missing_rate_limits.jsonl
- codex_gap_malformed_rate_limits.jsonl
- codex_gap_missing_token_stats.jsonl
- codex_gap_multi_session_mix.jsonl
- codex_gap_old_new_mixture.jsonl

## Result Per Fixture

| Fixture | Exit | accepted (processed) | skipped | quarantined | failed | unsupported | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| codex_gap_empty_session.jsonl | 0 | 0 | 1 | 0 | 0 | 0 | skip-only behavior |
| codex_gap_corrupted_jsonl.jsonl | 0 | 1 | 0 | 1 | 0 | 0 | parse failure quarantined |
| codex_gap_missing_rate_limits.jsonl | 0 | 1 | 0 | 0 | 0 | 0 | admitted |
| codex_gap_malformed_rate_limits.jsonl | 0 | 1 | 0 | 0 | 0 | 0 | admitted |
| codex_gap_missing_token_stats.jsonl | 0 | 1 | 0 | 0 | 0 | 0 | admitted_with_warning=1 |
| codex_gap_multi_session_mix.jsonl | 0 | 2 | 2 | 0 | 0 | 0 | mixed accepted+skipped |
| codex_gap_old_new_mixture.jsonl | 0 | 2 | 0 | 0 | 0 | 0 | old/new mix admitted |

## Coverage Gaps (Updated)

1. `rate_limits` field-level validation is not enforced in current Codex ingest path.
2. Missing token stats are admitted as analysis evidence with warning semantics (`admitted_with_warning`), not quarantined.
3. These results establish fixture-bounded behavior, not provider-wide completeness claims.

## Capability Matrix Update (Codex Mainline)

| Capability | Evidence command | Result | Tested coverage | Coverage gap | Allowed analysis-only claim | Forbidden decision claim | Decision authority | Blocker / gap |
| ---------- | ---------------- | ------ | --------------- | ------------ | --------------------------- | ------------------------ | ------------------ | ------------- |
| Codex gap coverage calibration via existing ingest path | `codeburn_codex_smoke.py --artifact codeburn/phase2/examples/codex_gap_*.jsonl --json` | Pass for all listed fixtures (exit 0) | accepted/skipped/quarantined outcomes are deterministic for empty/corrupted/missing-rate-limits/malformed-rate-limits/missing-token-stats/multi-session/old-new fixtures | no field-level `rate_limits` validation; missing token stats remains warning-level admission | Codex local artifact ingest supports bounded analysis-only evidence behavior for tested fixtures | budget gate, billing truth, cost enforcement, agent ranking, any decision-authoritative claim | none | known gap remains deferred; no authority change |

