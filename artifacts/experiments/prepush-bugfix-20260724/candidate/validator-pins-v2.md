# Validator Pins v2 — versions, configs, commands (PRODUCER-SAFE) — CANDIDATE

Status: **CANDIDATE, pending owner re-sign.** Supersedes `validator-pins.md`
(sha256 `6ea4b3226a3f54dce265ad27a67209b9d803b27d690cc4d899d20fff9a7f2d5f`) only
if and when the owner re-signs these exact bytes. The frozen v1 file is NOT
edited and stays byte-stable.

Producer-safe: tool versions, configs, and commands only. No root-cause hint, no
expected result, no diagnosis.

## Required versions (exact, pinned)

| Validator | Required version | Applied to |
|---|---|---|
| shellcheck | 0.10.0 | scripts/hooks/pre-push |
| ruff | 0.6.9 | governance_tools/version_bump_guard.py |
| mypy | 1.11.2 | governance_tools/version_bump_guard.py |

## Frozen configs

shellcheck: default checks, severity=style, `--shell=bash`, no disabled rules.

ruff: line-length 100, target-version py312, lint select `E,F,W,I,B`.

mypy: python_version 3.12, warn_unused_ignores, warn_return_any,
no_implicit_optional.

## Commands (v2 — the config is now carried ON the command line)

v1 documented commands that did not apply the frozen ruff config, so the frozen
config and the executed behavior disagreed. In v2 every setting above is passed
explicitly, so the command IS the config. `--no-cache` is required because the
producer workspace may be mounted read-only, and a cache-init abort is not a
validator result.

```
shellcheck --shell=bash --severity=style scripts/hooks/pre-push

ruff check --no-cache --line-length 100 --target-version py312 \
    --select E,F,W,I,B governance_tools/version_bump_guard.py

mypy --no-incremental --python-version 3.12 --warn-unused-ignores \
    --warn-return-any --no-implicit-optional governance_tools/version_bump_guard.py
```

## Roles (mechanics only)

- Treatment-time (Arm D only): run the three commands on the changed files before
  Arm D commits; Arm D may act on the output. A/B/C never receive it.
- Post-hoc scoring: after all four outputs are committed and blinded, the blind
  scorer runs the identical commands across A/B/C/D (uniform-oracle rule).
  Results are never fed back to producers.
