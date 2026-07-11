# Census Unit Review — Claude Code Pre-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/claude_code/pre_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI entrypoint delegates Claude-normalized pre-task events to the shared runner. | Low: 21 LOC; correctness depends on preserved harness/event arguments. | Intentional platform/event wrapper pattern, not duplicate policy. | Not user-facing. | `keep_observe` |

Evidence: imports Claude normalizer and shared adapter runner; adapter structural
tests pin every platform/event wrapper's shared-entrypoint reference. This does
not prove current Claude hook installation.
