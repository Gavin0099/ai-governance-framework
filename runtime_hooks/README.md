# Runtime Hooks

This directory contains the runtime governance layer.

Core hooks:

- `core/pre_task_check.py`
- `core/post_task_check.py`

Adapters:

- `adapters/claude_code/pre_task.py`
- `adapters/claude_code/post_task.py`
- `adapters/claude_code/normalize_event.py`
- `adapters/codex/pre_task.py`
- `adapters/codex/post_task.py`
- `adapters/codex/normalize_event.py`
- `adapters/gemini/pre_task.py`
- `adapters/gemini/post_task.py`
- `adapters/gemini/normalize_event.py`

Design rule:

- Keep tool-specific event mapping in adapters.
- Keep governance decisions in `core/`.
- Keep adapter behavior aligned with `ADAPTER_CONTRACT.md`.

Shared payload contract:

- `event_contract.md`
- `event_schema.json`

Normalization flow:

- native harness payload
- `adapters/<harness>/normalize_event.py`
- shared event shape
- `core/pre_task_check.py` or `core/post_task_check.py`

Dispatcher:

- `dispatcher.py` routes a shared event JSON payload directly to `pre_task_check` or `post_task_check`
- `smoke_test.py` runs documented native example payloads end-to-end

Examples:

- `examples/claude_code/*.native.json`
- `examples/codex/*.native.json`
- `examples/gemini/*.native.json`
- `examples/shared/*.shared.json`
