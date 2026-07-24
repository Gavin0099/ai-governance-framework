# Validator Pins — versions, configs, commands (PRODUCER-SAFE)

This file is producer-safe: it contains only tool versions, configs, and the
commands to run them. It contains **no** root-cause hint, no expected result,
and no diagnosis. The expected-signal reasoning lives in a separate
designer/scorer-only file that producers never receive.

None of these validators is installed in the design environment; they are frozen
as **environment requirements** the run must install exactly. A run whose
validator versions do not match is INVALID (not merely lower-scored).

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

## Commands

```
shellcheck --shell=bash --severity=style scripts/hooks/pre-push
ruff check governance_tools/version_bump_guard.py
mypy governance_tools/version_bump_guard.py
```

## Roles (mechanics only)

- Treatment-time (Arm D only): run the three commands on the changed files before
  Arm D commits; Arm D may act on the output. A/B/C never receive it.
- Post-hoc scoring: after all four outputs are committed and blinded, the blind
  scorer runs the identical commands across A/B/C/D (uniform-oracle rule).
  Results are never fed back to producers.
