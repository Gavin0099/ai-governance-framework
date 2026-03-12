# Runtime Governance Update

This update adds the first runtime governance slice to the framework.

## Contract Schema

The machine-readable `[Governance Contract]` now includes:

- `RULES`
- `RISK`
- `OVERSIGHT`
- `MEMORY_MODE`

Example:

```text
[Governance Contract]
LANG        = C++
LEVEL       = L2
SCOPE       = feature
PLAN        = Phase B / Sprint 2 / Runtime governance
LOADED      = SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT, ARCHITECTURE
CONTEXT     = runtime-layer -> hook enforcement; NOT: full agent platform
PRESSURE    = SAFE (42/200)
RULES       = common,python
RISK        = medium
OVERSIGHT   = review-required
MEMORY_MODE = candidate
```

## State Generator

`governance_tools/state_generator.py` now accepts runtime inputs:

```bash
python governance_tools/state_generator.py \
  --rules common,python \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate
```

## Hooks

Pre-task check:

```bash
python runtime_hooks/core/pre_task_check.py \
  --rules common,python \
  --risk high \
  --oversight review-required
```

Post-task check:

```bash
python runtime_hooks/core/post_task_check.py \
  --file ai_response.txt \
  --risk medium \
  --oversight review-required
```

## Notes

- Runtime hook logic lives under `runtime_hooks/core/`.
- Tool-specific adapters live under `runtime_hooks/adapters/`.
- Existing README and prompt examples should be migrated to this schema next.
