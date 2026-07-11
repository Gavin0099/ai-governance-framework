# Census Unit Review — Claude Code Post-Task Adapter (2026-07-11)

Unit: `runtime_hooks/adapters/claude_code/post_task.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| No independent effect: CLI wrapper routes Claude-normalized post-task payloads into the shared runner, where response/evidence contract checks occur. | Low: 21 LOC; event/harness arguments must remain exact. | Intentional platform/event wrapper pattern, not duplicate contract logic. | Not user-facing. | `keep_observe` |

Evidence: shared runner import, documented native smoke fixture, and adapter
structural coverage. This does not prove a current Claude post-task hook run.
