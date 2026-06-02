# Claim Enforcement Evidence Policy

Status: provisional boundary note

## Purpose

This note records the current evidence boundary for
`artifacts/claim-enforcement/` without changing tracking behavior.

It exists to stop agents from guessing whether session-scoped
claim-enforcement artifacts are disposable runtime noise or formal
governance evidence.

## Current Categories

### 1. Stable baseline and test evidence

The following category is treated as stable tracked evidence:

- `artifacts/claim-enforcement/checker-tests/*`

This includes checker inputs, expected outputs, and test reports used to
verify deterministic claim-enforcement behavior.

### 2. Session-scoped claim-enforcement evidence

The following categories contain session-scoped evidence packets:

- `artifacts/claim-enforcement/session-*/claim-enforcement-check.json`
- `artifacts/claim-enforcement/<session-id>/claim-enforcement-check.json`

`<session-id>` may be timestamp-shaped or UUID-shaped. These directories are
the same artifact class when they contain `claim-enforcement-check.json`.

## Repo Consumption

These session-scoped artifacts are not disposable by assumption. Repo tooling
currently consumes them.

Known consumers:

- `governance_tools/runtime_completeness_audit.py`
- `governance_tools/closeout_audit.py`

Current runtime completeness logic expects:

- `artifacts/claim-enforcement/<session_id>/claim-enforcement-check.json`

Current closeout audit logic recursively scans claim-enforcement check files to
derive aggregate governance signals such as count, drift, downgrade, block,
and override metrics.

## Historical Tracking State

Historical tracking is mixed.

Observed state:

- checker-test baseline evidence is tracked
- many historical session-scoped claim-enforcement packets are tracked
- newer session-scoped claim-enforcement packets may remain untracked

This means the repository currently does not have a finalized version-control
policy for all session-scoped claim-enforcement evidence.

## Interim Rule

Until policy is finalized:

- new session-scoped claim-enforcement packets must not be automatically
  committed
- new session-scoped claim-enforcement packets must not be automatically
  ignored
- agents must not delete claim-enforcement session evidence as if it were
  ordinary runtime trash

Any change to claim-enforcement evidence tracking must be an explicit policy
decision, not a side effect of dirty-tree cleanup.

## Future Policy Decision Required

Future governance work must choose one of these models:

1. archival evidence model
2. promoted-only evidence model
3. external archive plus tracked summary/index model

This note does not decide between them.

## Non-Decisions

This note does not declare:

- that all session evidence must be committed
- that all session evidence must be ignored
- that current historical tracking is correct
- that `session-index.ndjson` should remain tracked
- that any migration should happen now
