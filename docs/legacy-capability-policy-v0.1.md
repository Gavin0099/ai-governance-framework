# Legacy Capability Policy v0.1

`legacy_only` is a capability-bounded runtime mode.
It is not a warning-only continuation path.

This policy applies when session start receives:

- `verdict = migration_required`
- `status = degraded`
- `mode = legacy_only`

## Allowed Features

- `core_pre_task_check`
- `core_post_task_check`
- `basic_version_compatibility_artifact_write`

## Disabled Features

Disabled features must be taken directly from:

- `version_compatibility.disabled_runtime_features`

At minimum, `legacy_only` must not load:

- `decision_context_bridge`
- `canonical_closeout`
- `session_index`
- feature-gated runtime extensions

## Artifact Write Policy

Allowed:

- `artifacts/governance/version_compatibility.json`

Disallowed:

- canonical closeout artifacts
- session index artifacts
- decision context bridge artifacts
- feature-gated runtime extension artifacts

## Human Surface Requirements

Human-readable output must include:

- `status=degraded`
- `mode=legacy_only`
- `reason=version_compatibility_migration_required`
- `legacy_only_boundary=feature_gated_runtime_extensions_not_loaded`
- disabled runtime feature visibility

## No-Reinference Rule

`legacy_only` feature allow/deny decisions must come from
`version_compatibility.enabled_runtime_features` and
`version_compatibility.disabled_runtime_features` only.

`session_start` and downstream consumers must not re-infer capabilities.
