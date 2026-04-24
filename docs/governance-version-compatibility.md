# Governance Version Compatibility

This document defines the semantics of the governance version compatibility
check and the boundaries of what each verdict means.

## Why This Exists

When a repo adopts a version of the AI Governance Framework and later the
framework is updated, there is a risk that the repo continues to declare
governance as "active" while operating against an outdated layout.

The version compatibility check makes this drift visible before it causes
silent governance gaps.

## Two Manifests, One Check

The check compares two files:

**Framework side** — `governance/runtime/required_versions.yaml`

Defines the minimum version each governance component must be at.
This is maintained by the framework authors.
Bump a required version here only when a real breaking change was introduced.

**Repo side** — `.governance/version_manifest.yaml`

Declares which governance component versions are actually installed in the
consuming repo.
This must be updated manually or via a migration script — never auto-generated
from runtime state.

## Verdict Values

### `compatible`

All version requirements are met.
All runtime features are enabled.

`compatible` does NOT mean governance is configured correctly.
It means the version contract is satisfied.

### `compatible_with_degradation`

Extended features are disabled because their version requirements are not met.
Core runtime (pre_task_check, post_task_check) still runs.

The session can start.
An advisory signal is written to indicate which features are inactive.

### `migration_required`

One or more core features are disabled.
Core governance cannot run at full capability.

New-version features must not activate.
The session may continue in analysis-only or legacy mode, but must not claim
that full governance is active.

### `unsupported`

The repo's `.governance/version_manifest.yaml` is missing or unreadable.

The repo cannot claim governance is active.
Runtime must not start in governance mode.
Human intervention is required.

`unsupported` is not a Python crash — it is a controlled runtime refusal.

## Feature Tiers

Features are divided into two tiers in `required_versions.yaml`:

**core** — Disabling any core feature makes the verdict `migration_required`.
Current core features: `pre_task_check`, `post_task_check`.

**extended** — Disabling extended features makes the verdict
`compatible_with_degradation`.
Current extended features: `canonical_closeout`, `session_index`,
`agents_rule_candidates`, `decision_context_bridge`.

## Feature Matrix Is Single Source of Truth

`governance/runtime/required_versions.yaml` is the only place that defines
which features require which version constraints.

Session-start behavior (what to enable, what to block) must be derived from
the feature matrix output — not from independent hardcoded logic.

If the feature matrix says `canonical_closeout` is disabled, session-start
must not activate it, regardless of any other configuration.

## Authority Boundary

The version check tool:

- reads manifests
- compares versions
- emits a verdict
- writes `artifacts/governance/version_compatibility.json`

It does NOT:

- migrate governance layouts
- mutate any governance state
- auto-approve or auto-upgrade anything

Migration requires explicit human or scripted action.

## Updating `.governance/version_manifest.yaml`

Update this file when:

- A migration script has been run and verified
- A new governance component version has been deliberately adopted
- The layout has been reviewed and tested

Do not update this file speculatively.
The manifest must reflect what is actually installed, not what is intended.

## Artifact

Every run writes `artifacts/governance/version_compatibility.json`.

Minimum shape:

```json
{
  "schema_version": "1.0",
  "checked_at": "2026-04-24T00:00:00Z",
  "repo_manifest_found": true,
  "framework_version": "0.4.0",
  "verdict": "compatible",
  "checks": [],
  "enabled_runtime_features": [],
  "disabled_runtime_features": [],
  "missing_migrations": []
}
```

The artifact is reviewer-visible and should be committed or stored as evidence
of the version state at check time.
