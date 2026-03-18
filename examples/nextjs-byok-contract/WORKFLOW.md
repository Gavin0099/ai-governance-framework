# Next.js BYOK Contract Workflow

## Why PLAN.md goes stale (and why it matters)

When an AI coding session starts without running `session_start.py`, the
governance framework has no way to know that:

- the current phase in PLAN.md is outdated
- migration numbers no longer match what has been executed
- architectural decisions recorded last week have since changed

All five issues discovered in the Next.js/BYOK audit (unused TS import,
BYOK cost leak, missing rate limit, stale PLAN.md, missing settings nav)
were the result of work continuing without a session-start governance check.

---

## Stage 1 — Manual bootstrap (immediate, zero setup)

Run before starting any coding session:

```powershell
$AI_GOV = "D:\ai-governance-framework"

python $AI_GOV\runtime_hooks\core\session_start.py `
  --project-root . `
  --plan PLAN.md `
  --rules common `
  --risk medium `
  --oversight review-required `
  --contract examples/nextjs-byok-contract/contract.yaml `
  --format human
```

Expected output:

```
[session_start]
plan_freshness=FRESH          ← PLAN.md is up to date
validator_preflight_ok=True   ← both BYOK validators loaded
domain_contract=nextjs-byok
...
```

If `plan_freshness=STALE` or `plan_freshness=CRITICAL`, update PLAN.md
before touching architecture-adjacent code.

---

## Stage 2 — Automatic via Claude Code hooks

Add this to `.claude/settings.json` in the project root.  Claude Code will
run `check_session.py` on every new conversation, before any tool call.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python examples/nextjs-byok-contract/hooks/check_session.py"
          }
        ]
      }
    ]
  }
}
```

`check_session.py` (see `hooks/check_session.py`) outputs a one-line
summary to stdout.  Claude Code injects it as context before the first
tool call.  If PLAN.md is CRITICAL, it prepends a hard warning.

---

## Stage 3 — CI gate (GitHub Actions)

Add `.github/workflows/byok-governance.yml` to run the validators on every PR:

```yaml
name: BYOK governance check

on: [pull_request]

jobs:
  byok-validators:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run BYOK validators
        run: |
          python examples/nextjs-byok-contract/run_validators.py \
            examples/nextjs-byok-contract/fixtures/ --json \
            > fixture_results.json || true

      - name: Summarise results
        run: |
          python - <<'PY'
          import json, sys
          data = json.load(open("fixture_results.json"))
          violations = [
            r
            for f in data["fixtures"]
            for r in f.get("results", [])
            if not r["ok"]
          ]
          for v in violations:
            for msg in v["violations"]:
              print(f"::warning::{msg}")
          PY

      - name: Plan freshness check
        run: |
          python D:/ai-governance-framework/governance_tools/plan_freshness.py \
            --plan PLAN.md --threshold 7 --format human
```

---

## Stage 4 — Pre-task check against changed files

Before AI modifies any ingest or API route, run:

```powershell
python $AI_GOV\runtime_hooks\core\pre_task_check.py `
  --project-root . `
  --rules common `
  --risk medium `
  --oversight review-required `
  --contract examples/nextjs-byok-contract/contract.yaml `
  --format human
```

---

## Stage 5 — Post-task validation

After AI produces a diff, run the validators against the changed file's
source to surface BYOK and rate-limit violations before commit:

```powershell
# Example: validate a changed ingest route
python examples/nextjs-byok-contract/run_validators.py `
  path/to/your/payload.checks.json --json
```

The payload must contain `file_path` and `source_code` keys.

---

## What each stage catches

| Issue | Stage 1 | Stage 2 | Stage 3 | Stage 4/5 |
|-------|---------|---------|---------|-----------|
| Stale PLAN.md | ✅ | ✅ auto | ✅ | ✅ |
| BYOK cost leak | — | — | ✅ fixture | ✅ validator |
| Missing rate limit | — | — | ✅ fixture | ✅ validator |
| TS compile error | — | — | (tsc step) | (build evidence) |
| Settings nav gap | — | — | — | review |

Stages build on each other — Stage 2 + 3 together catch everything except
UX gaps which require code review.
