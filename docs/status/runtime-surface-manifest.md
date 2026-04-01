# Runtime Surface Manifest

- generated_at: `2026-04-01T05:50:06.713972Z`
- repo_commit: `5ca7464f203661e9e62f7500a74557f753e44d51`
- signal_posture: `soft-enforcement`

## Adapter Inventory

| Adapter | Events | Normalizer | Runner |
|---|---|---|---|
| `claude_code` | `pre_task, post_task, normalize_event` | `runtime_hooks/adapters/claude_code/normalize_event.py` | `runtime_hooks/adapters/shared_adapter_runner.py` |
| `codex` | `pre_task, post_task, normalize_event` | `runtime_hooks/adapters/codex/normalize_event.py` | `runtime_hooks/adapters/shared_adapter_runner.py` |
| `gemini` | `pre_task, post_task, normalize_event` | `runtime_hooks/adapters/gemini/normalize_event.py` | `runtime_hooks/adapters/shared_adapter_runner.py` |

## Runtime Entrypoints

| Entrypoint | Category | Path | Primary Output |
|---|---|---|---|
| `session_start` | `runtime-startup` | `runtime_hooks/core/session_start.py` | startup context envelope |
| `pre_task_check` | `runtime-gate` | `runtime_hooks/core/pre_task_check.py` | pre-task decision envelope |
| `post_task_check` | `runtime-gate` | `runtime_hooks/core/post_task_check.py` | post-task validation envelope |
| `session_end` | `runtime-close` | `runtime_hooks/core/session_end.py` | runtime close envelope |
| `dispatcher` | `shared-dispatch` | `runtime_hooks/dispatcher.py` | event routing envelope |
| `smoke_test` | `runtime-smoke` | `runtime_hooks/smoke_test.py` | smoke execution summary |
| `run_runtime_governance` | `shared-enforcement` | `scripts/run-runtime-governance.sh` | hook-or-ci execution status |

## Governance Tool Entries

| Tool | Category | Human Track | Agent Track | Produces Artifact |
|---|---|---|---|---|
| `adopt_governance` | `adoption` | `True` | `True` | `True` |
| `governance_drift_checker` | `drift` | `True` | `True` | `True` |
| `quickstart_smoke` | `smoke` | `True` | `True` | `True` |
| `runtime_enforcement_smoke` | `smoke` | `False` | `True` | `True` |
| `reviewer_handoff_summary` | `reviewer-handoff` | `True` | `True` | `True` |
| `trust_signal_overview` | `release-surface` | `True` | `True` | `True` |

## Evidence Surfaces

| Surface | Producer | Artifact Type | Human Auditable |
|---|---|---|---|
| `runtime_verdict_artifact` | `session_end` | `runtime-verdict` | `True` |
| `runtime_trace_artifact` | `session_end` | `runtime-trace` | `True` |
| `reviewer_handoff_summary` | `reviewer_handoff_summary` | `reviewer-handoff` | `True` |
| `quickstart_smoke_terminal_output` | `quickstart_smoke` | `smoke-terminal-output` | `True` |
| `governance_drift_checker_output` | `governance_drift_checker` | `drift-structured-output` | `True` |

## Authority Surfaces

| Surface | Declared Source | Can Change Verdict |
|---|---|---|
| `governance_authority_table` | `governance/AUTHORITY.md` | `False` |
| `runtime_decision_model` | `governance/governance_decision_model.v2.6.json` | `True` |
| `decision_boundary_model` | `docs/decision-boundary-layer.md` | `False` |
| `agent_adoption_boundary` | `docs/beta-gate/agent-adoption-pass-criteria.md` | `False` |

## Consistency Signals

- unknown_surfaces: `0`
- orphan_surfaces: `0`
- evidence_surface_mismatch: `0`
