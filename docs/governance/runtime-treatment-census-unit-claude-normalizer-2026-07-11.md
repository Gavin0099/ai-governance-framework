# Census Unit Review — Claude Code Normalizer (2026-07-11)

Unit: `runtime_hooks/adapters/claude_code/normalize_event.py`.

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition |
| --- | --- | --- | --- | --- |
| Known Claude Code consumer path, but no separate decision effect belongs to this wrapper. | Low: 22 LOC, one harness stamp. | Intentional 4-platform wrapper pattern; parity guard requires all behavior except metadata.harness to match. | Not user-facing. | `keep_observe` |

Evidence: pre/post adapters and smoke import this normalizer; parity tests pin
wrapper equivalence. This does not prove a real Claude session reached it today.
