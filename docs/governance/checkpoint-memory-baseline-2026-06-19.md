# Checkpoint-Memory Advisory Baseline 2026-06-19

Status: advisory frozen baseline. Not enforced.

Source command:

```powershell
.\.venv\Scripts\python.exe -m governance_tools.checkpoint_memory_audit --project-root . --last 5 --format json
```

Source HEAD: `9fad7ec`

Machine-readable baseline:
`artifacts/governance/checkpoint-memory-baseline-2026-06-19.json`

## Purpose

Freeze the current checkpoint-memory audit findings so future reviews can
distinguish known baseline debt / expected noise from new drift.

This is the measurement/baseline step between:

```text
visibility audit -> interpretation contract -> baseline -> later FP/stability measurement -> possible blocker
```

It does not change the audit tool, commit-memory binding contract, hook, CI, or
enforcement behavior.

## Baseline Summary

| Code | Count | Disposition |
|---|---:|---|
| `commit_without_memory` | 3 | expected noise |
| `stale_no_commit_memory` | 3 | baseline debt |
| `unreceipted_validation` | 38 | baseline debt |
| `rollup_memory_divergence` | 0 | none |
| `consumer_uninstalled` | 0 | none |

Total findings frozen: 44.

Current blocker count: 0.

## Disposition Rules Applied

Interpretation comes from
`docs/governance/commit-memory-binding-contract.md`.

### `commit_without_memory`

The three current findings are memory commits:

- `9fad7ec99cb1`
- `69baf56f6a90`
- `78135b7b9bf2`

Disposition: expected advisory noise.

Reason: memory commits do not require downstream memory records; otherwise the
workflow creates infinite regress.

### `stale_no_commit_memory`

The three current findings are original `WORKTREE` records:

- `2026-06-19.md:4` -> corrective binding exists for `ea08820`
- `2026-06-19.md:16` -> corrective binding exists for `a2ccce7`
- `2026-06-19.md:28` -> corrective binding exists for `a2ccce7`

Disposition: baseline debt.

Reason: the repo uses corrective records rather than rewriting historical memory.
The detector still sees the original placeholders, but the reconciliation is now
recorded.

### `unreceipted_validation`

The 38 findings are frozen as historical advisory debt. This baseline does not
validate, rewrite, or clear them.

Future slices may separately define:

- a historical-debt cleanup plan;
- a stricter receipt-path definition;
- a new-drift-only comparison mode.

None of those are part of this baseline.

## Claim Ceiling

```yaml
claim_ceiling:
  - advisory frozen baseline only
  - machine-readable snapshot plus reviewer summary
  - no tool behavior change
  - no hook, CI, blocker, or enforcement
not_claimed:
  - historical unreceipted_validation debt resolved
  - false-positive rate measured
  - taxonomy stability across N windows
  - governed executor non-bypassability
  - any change to checkpoint_memory_audit output semantics
```
