# CodeBurn Same-Provider Visible I/O Token Sum Contract

> Date: 2026-06-05
> Status: implemented as opt-in `codeburn_report.py` exposure
> Scope: Codex and Claude Code same-provider token observation summaries

## Purpose

Define the only currently acceptable summary shape for CodeBurn Codex and
Claude Code log-visible token observations.

This contract exists to prevent a future summary from reintroducing
`total_tokens`, billing truth, efficiency inference, or Claude-vs-Codex
comparison through naming or aggregation pressure.

## Claim Ceiling

CLAIMED:

- A same-provider summary contract is defined for CodeBurn Codex and
  Claude Code summaries.
- The safe derived field name is `visible_io_token_sum`, not `total_tokens`.
- Summary semantics are constrained to Class C, observation-only, non-billing,
  same-provider context.
- Cross-provider aggregation and comparison remain prohibited.
- `codeburn_report.py` may expose this summary only through explicit
  `--visible-io-provider codex|claude-code` opt-in.
- `codeburn_session_display.py` may expose the Codex visible I/O sum only when
  `CODEBURN_SHOW_VISIBLE_IO_SUM=1`; this display uses Chinese-friendly labels
  for user readability while preserving the same claim ceiling.

NOT CLAIMED:

- Schema change.
- Default report output change.
- Automatic summary output.
- Default session display output change.
- Validator or hook enforcement.
- Billing truth.
- Provider-authoritative token truth.
- Complete log coverage.
- Cost estimation.
- Efficiency inference.
- Cross-provider comparability.
- Runtime or real-time token observation.

## Permitted Summary Field

The only permitted derived visible-token sum name is:

```text
visible_io_token_sum
```

Definition:

```text
visible_io_token_sum = prompt_tokens + completion_tokens
```

This field may be computed only when both operands are present as integers in
the same provider scope.

If either operand is missing, the derived field must be `NULL` / absent with an
explicit missing-field reason. Missing token fields must not be treated as `0`.

## Required Companion Fields

Any same-provider summary that includes `visible_io_token_sum` must also
include equivalent companion metadata:

```text
provider
evidence_class = Class C
acquisition_mode = session_log_ingestion
visible_io_token_sum_authority = observation_only
billing_truth = false
decision_usage_allowed = false
analysis_safe_for_decision = false
cross_provider_comparable = false
efficiency_inference_allowed = false
missing_field_policy = null_not_zero
```

The exact storage shape may differ, but these semantics must be visible to the
reviewer in the summary output or its contract-bound artifact.

## Provider Scope

Permitted scopes:

- Codex-only summaries over rows where `provider = "codex"`.
- Claude Code-only summaries over rows where `provider = "claude-code"`.

Forbidden scopes:

- Codex + Claude Code combined summaries.
- Provider-agnostic token totals.
- Cross-provider averages, medians, percentiles, rankings, or trends.
- Any query that groups multiple providers into one token value.

## Naming Rules

Forbidden names for this derived value:

- `total_tokens`
- `total_token_usage`
- `session_total_tokens`
- `billing_tokens`
- `cost_tokens`
- `provider_total`
- `combined_tokens`
- `normalized_tokens`
- `equivalent_tokens`

Required wording:

- Use `visible I/O token sum`.
- Say `Class C observation only`.
- Say `not billing truth`.
- Say `not cross-provider comparable`.

## Missing-Field Rules

Correct:

```text
prompt_tokens = NULL
completion_tokens = 42
visible_io_token_sum = NULL
missing_field_reason = prompt_tokens_missing
```

Incorrect:

```text
prompt_tokens = NULL
completion_tokens = 42
visible_io_token_sum = 42
```

Reason: `NULL` means not present in the log artifact. It does not mean zero
usage.

## Cache / Reasoning / Billing Rules

The following fields must not be folded into `visible_io_token_sum`:

- Codex `reasoning_output_tokens`.
- Codex `cached_input_tokens`.
- Codex `total_token_usage.*`.
- Claude Code `cache_creation_input_tokens`.
- Claude Code `cache_read_input_tokens`.
- Service tier, model, routing, billing, or cost metadata.

If a future feature wants cache-aware or billing-aware summaries, it requires a
separate contract and must not reuse `visible_io_token_sum`.

## Allowed Example

```text
provider: codex
evidence_class: Class C
summary_scope: same_provider_session_log_observation
prompt_tokens_observed: 1200
completion_tokens_observed: 300
visible_io_token_sum: 1500
visible_io_token_sum_authority: observation_only
billing_truth: false
cross_provider_comparable: false
efficiency_inference_allowed: false
```

## Forbidden Examples

```text
Claude used 2000 total tokens and Codex used 1500 total tokens.
Codex is more token-efficient.
Codex used fewer tokens than Claude.
Total provider token cost: 1500.
```

These statements violate the CodeBurn consumption and comparability boundaries.

## Implementation / Exposure Gate

Before any new exposure or consumer of this summary contract, add tests proving:

- `visible_io_token_sum` is computed only for same-provider rows.
- missing prompt/completion fields keep the sum `NULL` / absent.
- `total_tokens` remains unset for Codex and Claude Code ingestion paths.
- cache, reasoning, and billing fields are not folded into the sum.
- no cross-provider rollup query is introduced.
- output includes the required companion semantics.

Current permitted exposure:

```powershell
python codeburn/phase1/codeburn_report.py --db <db> --session-id <session> --format json --visible-io-provider codex
python codeburn/phase1/codeburn_report.py --db <db> --session-id <session> --format json --visible-io-provider claude-code
$env:CODEBURN_SHOW_VISIBLE_IO_SUM = "1"
python codeburn/phase1/codeburn_session_display.py --transcript <codex-session.jsonl>
```

Default report output remains unchanged unless `--visible-io-provider` is
explicitly provided. Default session display output remains unchanged unless
`CODEBURN_SHOW_VISIBLE_IO_SUM=1` is set.

Codex session display wording:

```text
回合數: <n>
輸入: <n> tokens (重建值)
輸出: <n> tokens (重建值)
可見 I/O token 加總: <n> | Class C 觀測值
不是帳單真值 | 不是效率指標 | 不可跨 provider 比較
```
