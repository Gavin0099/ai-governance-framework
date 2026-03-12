# Runtime Event Contract

This contract defines the shared payload shape that all harness adapters should normalize to before calling runtime governance core logic.

The goal is portability:

- Claude Code
- Codex
- Gemini
- future harnesses

must all map their native hook/event payloads into the same structure.

## Pre-Task Event

```json
{
  "event_type": "pre_task",
  "project_root": ".",
  "task": "Runtime governance",
  "rules": ["common", "python"],
  "risk": "medium",
  "oversight": "review-required",
  "memory_mode": "candidate",
  "response_file": null,
  "metadata": {
    "harness": "codex",
    "session_id": "2026-03-12-01"
  }
}
```

Required fields:

- `event_type`
- `project_root`
- `rules`
- `risk`
- `oversight`
- `memory_mode`

## Post-Task Event

```json
{
  "event_type": "post_task",
  "project_root": ".",
  "task": "Runtime governance",
  "rules": ["common", "python"],
  "risk": "medium",
  "oversight": "review-required",
  "memory_mode": "candidate",
  "response_file": "ai_response.txt",
  "create_snapshot": true,
  "snapshot_summary": "Candidate memory from task output",
  "metadata": {
    "harness": "gemini",
    "session_id": "2026-03-12-01"
  }
}
```

Required fields:

- `event_type`
- `project_root`
- `risk`
- `oversight`
- `memory_mode`

Additional rule:

- `response_file` is required for `post_task` unless the adapter provides response text directly through another wrapper layer.

## Adapter Rule

Adapters may transform native payloads into this shape, but they must not reinterpret governance policy.
