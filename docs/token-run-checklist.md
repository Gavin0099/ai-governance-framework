# Token Run Checklist

Use this checklist before/after each token observability run.

## Before Run

1. Confirm repo target and date window.
2. Use governed entrypoint (bridge):
```powershell
python -m governance_tools.governed_prompt_bridge --provider <chatgpt|claude|gemini> ...
```
3. Ensure artifact root is enabled (do not use `--no-artifact`).

## Per Run (Minimum Record)

Record these 5 items:

1. `repo`
2. `timestamp`
3. `task_type` (short label)
4. token fields:
   - `total_tokens`
   - `token_source_summary`
   - `token_observability_level`
   - `decision_usage_allowed`
5. `artifact_path` (raw JSON path)

## Artifact Location

Store/verify raw JSON under:

```text
artifacts/runtime/injection/<YYYY-MM-DD>/<timestamp>-<provider>.json
```

## End-of-Day Check

1. No missing artifact paths.
2. `decision_usage_allowed` remains `false` for all runs.
3. If `total_tokens=null`, ensure source/observability is explicit (`unknown` / `none`).

## References

- `docs/token-observability-test-plan.md`
- `docs/governed-prompt-usage.md`

