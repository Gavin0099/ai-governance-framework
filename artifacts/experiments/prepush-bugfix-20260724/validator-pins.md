# Validator Pins — Arm D treatment-time + post-hoc scoring

None of these validators are installed in the design environment; they are frozen
as **environment requirements** the run must install exactly. A run whose
validator versions do not match is INVALID (not merely lower-scored). Expected
signal on this defect is **null** (F3): an "ignore-stdin" logic error is not a
shell/type/lint smell.

## Required versions (exact, pinned)

| Validator | Required version | Applied to |
|---|---|---|
| shellcheck | 0.10.0 | scripts/hooks/pre-push |
| ruff | 0.6.9 | governance_tools/version_bump_guard.py |
| mypy | 1.11.2 | governance_tools/version_bump_guard.py |

## Frozen configs

shellcheck: default checks, severity=style, `--shell=bash`, no disabled rules.

ruff config (frozen literal):
```
line-length = 100
target-version = "py312"
lint.select = ["E", "F", "W", "I", "B"]
```

mypy config (frozen literal):
```
python_version = 3.12
warn_unused_ignores = True
warn_return_any = True
no_implicit_optional = True
```

## Roles

- Treatment-time (Arm D only): run the three validators on the changed files
  before Arm D commits; Arm D may act on the output. A/B/C never receive it.
- Post-hoc scoring: after all four outputs are committed and blinded, the blind
  scorer runs the identical pinned validators across A/B/C/D (uniform-oracle
  rule). Results measure residual findings and are never fed back to producers.
