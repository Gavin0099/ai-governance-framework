# Runtime Adapter Contract

The runtime governance layer is harness-agnostic.

`runtime_hooks/core/` contains governance decisions.
`runtime_hooks/adapters/` contains harness-specific wrappers only.

## Required rule

Adapters must not embed governance policy.

They may only:

- map harness event payloads into CLI arguments or Python function inputs
- normalize native payloads into the shared shape defined by `event_contract.md` / `event_schema.json`
- read harness-specific input locations
- forward results back to the harness in its expected format

They must not:

- redefine risk rules
- redefine oversight rules
- bypass contract validation
- bypass memory-mode restrictions

## Current adapter families

- `claude_code/`
- `copilot/`
- `codex/`
- `gemini/`
- `hermes/`

## Minimum adapter surface

Each harness should expose wrappers for:

- `pre_task`
- `post_task`
- `normalize_event`

Future optional wrappers:

- `pre_compact`

The `copilot/lifecycle.py` wrapper is the bounded exception that currently
handles `session_start` and `session_end` lifecycle payloads. It normalizes
VS Code and GitHub Copilot field names, then delegates to the canonical session
envelope and session-end implementations without embedding governance policy.

## Shared payload contract

Adapters should target the shared runtime event shape documented in:

- `runtime_hooks/event_contract.md`
- `runtime_hooks/event_schema.json`
