# Post-run Observability Capture v0.1

- date: 2026-05-12
- status: draft-for-implementation
- scope: record-only observability capture

## Positioning

This surface is **observability capture**, not governance enforcement.

- record only
- provenance only
- comparability signaling only

## Goals

After each AI-governance run in any repo, automatically emit a traceable record so manual reminders are not required.

## Non-goals

- no KPI population
- no repo comparison
- no agent ranking
- no governance gate/checklist/validator expansion
- no governance effectiveness claim
- no model capability claim

## Required Record Fields

```yaml
run_id:
repo:
agent_lane:
task_pack:
started_at:
ended_at:
provider:
model:
token_source:
token_granularity:
prompt_tokens:
completion_tokens:
total_tokens:
duration_ms:
comparability_token:
comparability_duration:
comparability_change:
capture_status:
kpi_template_fill_allowed:
provenance_trace:
notes:
```

## Hard Rule: Untrusted Token Provenance

If token provenance is missing, unknown, estimated, scaffolded, or otherwise non-comparable:

- `comparability_token=0`
- `kpi_template_fill_allowed=false`

This must be set automatically by capture, without reviewer reminder.

## Capture Output Contract

Each run-end capture writes one append-only record with the required fields.
No post-capture interpretation is allowed in this surface.

## Phase-1 Rollout Order

1. Stabilize single-lane auto-capture in one repo.
2. Expand to three lanes (`chatgpt`, `claude`, `copilot`) with same task pack, same schema, same capture pipeline.
3. Compare capture quality only.

## Phase-1 Evaluation Metrics (Capture Quality Only)

- `schema_complete_rate`
- `provenance_complete_rate`
- `comparability_flag_correctness`
- `overclaim_rate`
- `missing_capture_rate`

## Explicit Boundary

Phase-1 metrics are for capture quality only.
They must not be interpreted as model-quality comparison, token-efficiency ranking, or governance effectiveness proof.

