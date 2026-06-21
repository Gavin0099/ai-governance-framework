# CI Enforcement Claim Ceiling

Status: advisory claim-boundary document
Scope: `.github/workflows/governance.yml`
Last checked: 2026-06-21 against current repository HEAD

## Purpose

This document states what the repository's current CI workflow can and cannot
claim as an enforcement surface. It is a documentation-only boundary record.
It does not change GitHub Actions behavior, local hooks, branch protection,
runtime adapters, or governance policy.

## What Runs Where

The `Governance Check` workflow is triggered by:

- `push` to `main` and `feature/**` when relevant paths change, including
  `.github/workflows/governance.yml`, `governance/**`, `governance_tools/**`,
  `runtime_hooks/**`, `scripts/**`, `tests/**`, `examples/**`, `PLAN.md`,
  `memory/**`, and `triage/**`.
- `pull_request` to `main` for the same path set.
- manual `workflow_dispatch`.

On `push`, the workflow runs after the pushed commit already exists on the
remote branch. These checks are detection/accountability on the pushed state,
not pre-push prevention.

Current push-visible jobs include:

- `memory-workflow-selective` / `Memory Workflow Selective Blocker`, which runs
  `governance_tools.ci_memory_workflow_check` over the event's base/head range.
- `plan-freshness` / `PLAN.md Freshness`, which exits non-zero only for
  `CRITICAL` or `ERROR` plan freshness and emits warnings for `STALE`.
- `memory-pressure` / `Memory Pressure`, marked `continue-on-error: true`.
- `doc-drift` / `Documentation Drift`, marked `continue-on-error: true`.
- `interception-ledger-check` / `Interception Ledger Check`, run with
  `--warn-only`.

The following jobs are explicitly not run on `push` because they use
`if: github.event_name != 'push'`:

- `phase-gates` / `Phase Gate Verification`
- `reviewer-policy-gate` / `Reviewer Handoff Policy Gate`
- `runtime-enforcement` / `Runtime Governance Enforcement`
- `violation-triage-gate` / `Violation Triage Gate`

One step in `memory-workflow-selective` also branches on
`github.event_name == 'pull_request'` to choose pull-request base/head SHAs.
That branch changes range selection only; it does not make push execution
prevention-grade.

## Claim Ceiling

The current workflow supports these claims:

- CI provides reviewer-facing accountability and detection for selected
  governance, runtime, test, memory, plan, and triage surfaces.
- Push-triggered checks can detect issues after the commit has reached the
  remote branch.
- Pull-request runs exercise a stronger set of jobs than push runs because the
  four PR-only jobs above are enabled outside `push`.
- Local hooks, runtime adapters, and smoke runners are accountability surfaces:
  they normalize events, surface evidence, and report failures. They are not
  runtime sandboxes and do not physically prevent every tool action.

Prevention-grade claims require infrastructure outside this file, such as
required pull-request checks, branch protection on protected branches, or
server-side policy. This repository file records the in-repo workflow shape; it
does not verify GitHub repository settings.

## Cannot Claim

This repository cannot claim from the workflow file alone that:

- Governance enforcement is non-bypassable.
- Direct pushes to `main` are prevented.
- GitHub branch protection or required status checks are enabled.
- Local hooks are installed for every contributor or agent runtime.
- Runtime adapters prevent arbitrary tool execution.
- Smoke tests or adapter tests are a security boundary.
- The workflow proves framework correctness or semantic correctness.

## Review Rule

When describing this repository's CI/governance posture, use:

- "post-facto detection/accountability" for push-triggered checks;
- "stronger PR coverage" for pull-request checks;
- "prevention only when required checks and branch protection are verified" for
  non-bypassability claims.

Do not describe the current CI surface as prevention-grade unless branch
protection / required-check configuration has been independently verified and
recorded.
