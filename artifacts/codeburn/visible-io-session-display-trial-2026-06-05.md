# CodeBurn Visible I/O Session Display Trial

Date: 2026-06-05
Mode: real Codex transcript manual display trial

## Scope

Trial `CODEBURN_SHOW_VISIBLE_IO_SUM=1` against an existing Codex transcript to
verify whether `codeburn_session_display.py` can display `visible_io_token_sum`
in actual Codex log-shaped data.

## Input

Transcript:

```text
C:\Users\reiko\.codex\sessions\2026\06\03\rollout-2026-06-03T13-52-11-019e8c0a-0a22-7151-85ba-28d0731cc587.jsonl
```

Observed precheck:

```text
TOKEN_COUNT_LINES=1246
```

## Command

```powershell
$env:CODEBURN_SHOW_VISIBLE_IO_SUM='1'
python codeburn/phase1/codeburn_session_display.py --transcript C:\Users\reiko\.codex\sessions\2026\06\03\rollout-2026-06-03T13-52-11-019e8c0a-0a22-7151-85ba-28d0731cc587.jsonl --session-id real-codex-visible-io-trial --no-db
```

## Observed Output

```text
provider : codex
turns    : 1247
input    : 170.0M tokens (reconstructed)
output   : 486,329 tokens (reconstructed)
visible_io_token_sum: 170.5M | Class C observation-only
not billing truth | not efficiency | not cross-provider comparable
```

## Result

`visible_io_token_sum` visibility: PASS for manual session display with
`CODEBURN_SHOW_VISIBLE_IO_SUM=1`.

## Caveats

- This validates manual `codeburn_session_display.py --transcript` visibility,
  not Codex UI stop-hook rendering.
- The command used `--no-db`; rolling window ingestion was not part of this
  trial.
- The display text is Class C observation-only and does not claim billing truth,
  efficiency inference, token cost, or cross-provider comparability.
- One long display line can exceed the ASCII panel width. This is a formatting
  caveat only; no behavior change was made in this trial.

## Not Claimed

- Codex UI automatically displays the value.
- Stop-hook environment inheritance is verified.
- Billing truth.
- Efficiency inference.
- Cross-provider comparison.
- Token cost reduction.
- Schema or behavior changes.
