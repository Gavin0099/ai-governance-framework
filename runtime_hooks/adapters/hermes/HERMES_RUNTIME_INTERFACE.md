# Hermes Adapter — Accepted-Input Interface

> **This is the accepted-input interface for the Hermes adapter.
> It is NOT a verified specification of any external Hermes runtime.**
>
> "Hermes" here is a runtime *class* (a long-running, Hermes-like agent runtime),
> not a specific public project. The name is overloaded (healthcare frameworks,
> Lean/math agents, CQL engines, …). This doc defines what *we accept as input*;
> a real runtime's native payload is mapped to this shape in
> `normalize_event.py`. Governance policy stays in `runtime_hooks/core/*`.

A conforming runtime emits one structured-JSON event per hook point
(`session_start`, `pre_task`, `post_task`). The adapter (`normalize_event.py`)
reshapes it into the shared runtime event contract
(`runtime_hooks/event_schema.json`) via `shared_normalizer`; the core hooks then
do scope / evidence / claim governance.

## Field layers

### 1. Adapter-supplied (the runtime does NOT emit this)
- `event_type` — set by the adapter entrypoint (`pre_task.py` / `post_task.py` /
  session-start path), not read from the payload.

### 2. Accepted-input hard requirement
- **`post_task`: `output_file` (or `response_file`)** — the normalized
  `post_task` event must carry `response_file` to comply with
  `event_schema.json`. `output_file` is mapped to `response_file` by
  `shared_normalizer`.
  - Precision: `shared_adapter_runner.py` does **not** validate against
    `event_schema.json`, so a missing `response_file` does **not** hard-crash the
    runner. The cost is *contract non-compliance* and a **weakened post-task
    evidence / claim check** (`_post_task_contract_required` reads it via
    `.get()`), i.e. the post-task result can no longer be backed by the AI
    response artifact. So it is "required for contract compliance + evidence
    quality", not "required to avoid an exception".

### 3. Strongly recommended (omitting falls back to defaults → weaker classification)
Each below has a default; omitting it does not break execution, but the task is
then governed under a generic default that may misclassify it.

| field | default if omitted | why emit it |
|---|---|---|
| `project_root` | `"."` | correct repo targeting |
| `risk` | `"medium"` | drives oversight/claim ceiling |
| `oversight` | `"review-required"` | governance posture |
| `memory_mode` | `"candidate"` | memory promotion behavior |
| `task` | `null` | task text for scope/contract |
| `run_id` / `session_id` | `null` | trace + memory binding strength |
| `rules` | `[]` | applicable rule packs |
| `checks_file` | (absent) | post-task evidence when available |

## Accepted field aliases (from `shared_normalizer.py`)
A runtime may use any of these names per canonical field:

| canonical | accepted aliases |
|---|---|
| `project_root` | `project_root`, `cwd`, `workspace`, `repo_root` |
| `plan_path` | `plan_path`, `plan` |
| `task` | `task`, `prompt`, `request`, `goal`, `title` |
| `rules` | `rules`, `rule_packs`, `active_rules` |
| `risk` | `risk`, `risk_level` |
| `oversight` | `oversight`, `oversight_mode` |
| `memory_mode` | `memory_mode`, `memory` |
| `response_file` | `response_file`, `output_file`, `assistant_response_path`, `transcript_path`, `result_file` |
| `checks_file` | `checks_file`, `checks_path`, `evidence_file`, `evidence_path` |
| `impact_before_files` | `impact_before_files`, `impact_before` |
| `impact_after_files` | `impact_after_files`, `impact_after` |
| snapshot flag | `create_snapshot`, `snapshot`, `emit_snapshot` |
| summary | `snapshot_summary`, `summary` |
| `session_id` | `session_id`, `conversation_id`, `run_id` |
| native event name | `hook_event_name`, `event`, `event_name` |
| `contract` | `contract`, `contract_file` |

## Minimal compliant examples
See `runtime_hooks/examples/hermes/{session_start,pre_task,post_task}.native.json`
— labeled accepted-input contract fixtures (not verified Hermes payloads).

## When a real Hermes runtime arrives
- If its native field names are within the aliases above → no adapter change.
- If they differ → add the remap in `normalize_event.py` only.
- `runtime_hooks/core/*` (governance policy) stays unchanged either way — the
  runtime is a governed *executor*, not a second governance layer.

## Claim ceiling
- Accepted-input interface only; not a verified external Hermes spec.
- No enforcement claim; the adapter reshapes payloads, it does not gate tools.
- Runner does not schema-validate; contract compliance is the runtime's duty.
