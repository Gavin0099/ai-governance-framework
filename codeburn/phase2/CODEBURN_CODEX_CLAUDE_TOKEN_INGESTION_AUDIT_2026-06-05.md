# CodeBurn Codex / Claude Token Ingestion Audit

> Date: 2026-06-05
> Status: audit-only
> Scope: Codex and Claude Code token ingestion surfaces

## Audit Goal

Audit the current CodeBurn Codex and Claude Code ingestion surfaces for token
visibility and governance boundaries.

This audit does not change ingestion behavior, schema, reporting behavior,
comparability rules, or enforcement behavior.

## Claim Ceiling

CLAIMED:

- Current Codex and Claude Code token fields admitted by ingestion are
  enumerated.
- Current `total_tokens` handling is audited for Codex and Claude Code
  ingestion paths.
- Current cache / reasoning / billing-token folding boundaries are audited.
- Current cross-provider aggregation boundary is checked at the artifact and
  test-surface level.
- The audit confirms Class C / observation-only / non-billing /
  non-comparable semantics for current ingestion surfaces.

NOT CLAIMED:

- Billing truth.
- Provider token truth.
- Runtime interception.
- Real-time token observation.
- Complete log coverage.
- Cost estimation.
- Efficiency inference.
- Cross-provider token comparability.
- Cross-provider aggregation safety beyond searched current surfaces.
- New summary/reporting capability.
- Schema change.
- Validator or hook enforcement.

## Source Surfaces Reviewed

### Codex

- `codeburn/phase2/codex_log_ingestor.py`
- `codeburn/phase2/codeburn_codex_smoke.py`
- `codeburn/CODEBURN_CODEX_ARTIFACT_CONTRACT.md`
- `codeburn/CODEBURN_CODEX_INGESTOR_SPEC.md`
- `tests/test_codeburn_codex_smoke.py`
- `tests/test_codeburn_codex_negative.py`

### Claude Code

- `codeburn/phase2/claude_code_jsonl_ingestor.py`
- `codeburn/CODEBURN_CLAUDE_ARTIFACT_CONTRACT.md`
- `tests/test_claude_code_jsonl_ingestor.py`

### Shared Boundaries

- `codeburn/CODEBURN_CROSS_PROVIDER_COMPARABILITY_BOUNDARY.md`
- `codeburn/CODEBURN_TOKEN_OBSERVABILITY_CONSUMPTION_BOUNDARY.md`
- `codeburn/CODEBURN_ACQUISITION_SEMANTIC_FREEZE.md`

## Current Codex Ingestion Surface

Codex ingestion admits token evidence only from:

```text
record.type == "event_msg"
payload.type == "token_count"
payload.info.last_token_usage
```

Current admitted token fields:

| CodeBurn field | Source field | Semantics |
|---|---|---|
| `prompt_tokens` | `payload.info.last_token_usage.input_tokens` | log-visible input token observation |
| `completion_tokens` | `payload.info.last_token_usage.output_tokens` | log-visible output token observation |
| `total_tokens` | none | intentionally persisted as `NULL` |

Current handling:

- Missing `input_tokens` / `output_tokens` remains `NULL`, not `0`.
- Malformed token records are quarantined, not silently dropped.
- `total_token_usage.*` is not consumed as turn-scoped evidence.
- `reasoning_output_tokens` is not stored or folded into `completion_tokens`.
- `cached_input_tokens` is not stored or folded into prompt/completion totals.
- Provider is stored as `codex`, preserving provider identity.
- Provenance is Class C with `real_time_observed=0`,
  `analysis_safe_for_decision=0`, and `provider_truthfulness_assumed=0`.

## Current Claude Code Ingestion Surface

Claude Code ingestion admits token evidence only from:

```text
record.type == "assistant"
message.usage
```

Current admitted token fields:

| CodeBurn field | Source field | Semantics |
|---|---|---|
| `prompt_tokens` | `message.usage.input_tokens` | log-visible input token observation |
| `completion_tokens` | `message.usage.output_tokens` | log-visible output token observation |
| `total_tokens` | none | intentionally persisted as `NULL` |

Current handling:

- Non-assistant rows are skipped.
- Malformed assistant rows are quarantined.
- Missing `message.usage` fields remain `NULL`, not `0`.
- `cache_creation_input_tokens` is not currently persisted by the
  Phase 2 Claude Code JSONL ingestor.
- `cache_read_input_tokens` is not currently persisted by the
  Phase 2 Claude Code JSONL ingestor.
- `service_tier`, `inference_geo`, `model`, `cwd`, and client metadata are not
  stored as token evidence.
- Provider is stored as `claude-code`, distinct from legacy `claude` and
  distinct from `codex`.
- Provenance is Class C with `real_time_observed=0`,
  `analysis_safe_for_decision=0`, and `provider_truthfulness_assumed=0`.

## Total Tokens Audit

Current implementation does not compute or persist `total_tokens` for Codex or
Claude Code ingestion paths.

This is intentional. `prompt_tokens + completion_tokens` would only be a
visible I/O token sum. It would not be billing truth, provider-authoritative
total usage, efficiency evidence, or a cross-provider comparable value.

The safe future name, if a same-provider summary is added later, should avoid
`total_tokens`. Prefer:

```text
visible_io_token_sum
visible_io_token_sum_authority = observation_only
billing_truth = false
evidence_class = Class C
cross_provider_comparable = false
```

## Cache / Reasoning / Billing Folding Audit

Current Codex ingestion:

- does not fold `reasoning_output_tokens` into `completion_tokens`;
- does not store `reasoning_output_tokens`;
- does not store `cached_input_tokens`;
- does not store `total_token_usage.*`;
- does not compute billing totals.

Current Claude Code ingestion:

- does not store `cache_creation_input_tokens`;
- does not store `cache_read_input_tokens`;
- does not compute billing totals;
- does not store service tier or routing metadata as token evidence.

Note: `CODEBURN_CLAUDE_ARTIFACT_CONTRACT.md` documents cache token fields as
individually observable in Claude Code logs, but the current Phase 2 ingestor is
more conservative and does not persist those cache fields.

## Cross-Provider Aggregation Audit

Current CodeBurn contracts explicitly prohibit cross-provider token comparison
and cross-provider aggregation.

Current ingestion preserves provider labels:

- Codex rows use provider `codex`.
- Claude Code rows use provider `claude-code`.

Current relevant tests assert provider separation for Codex ingestion and
Class C provenance for Claude Code ingestion.

This audit did not find a Codex/Claude same-table summary that computes a
cross-provider total. This is a searched current-surface finding, not a complete
proof over all future queries or external consumers.

## Safe Interpretation

Codex:

- `prompt_tokens`: observed from log-visible `input_tokens`.
- `completion_tokens`: observed from log-visible `output_tokens`.
- `total_tokens`: intentionally absent.
- evidence class: Class C.
- billing truth: false.
- cross-provider comparable: false.

Claude Code:

- `prompt_tokens`: observed from `message.usage.input_tokens`.
- `completion_tokens`: observed from `message.usage.output_tokens`.
- `total_tokens`: intentionally absent.
- evidence class: Class C.
- billing truth: false.
- cross-provider comparable: false.

## Recommendation

Do not add a CodeBurn token summary until the summary contract explicitly
separates:

- same-provider observation;
- visible I/O token sum;
- evidence class;
- missing-field coverage;
- billing non-truth;
- no efficiency inference;
- no cross-provider comparison.

If implemented later, the next safe feature should be same-provider only and
should use `visible_io_token_sum`, not `total_tokens`.

