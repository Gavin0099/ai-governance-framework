# Assumption Layer Experiment Boundary (2026-04-23)

## Purpose

Restore boundary clarity between baseline governance behavior and ongoing decision-policy experiments.

## Baseline (Mainline)

- `runtime_hooks/core/pre_task_check.py` defaults to `enforcement_profile=advisory_mainline`.
- Evidence integrity gate remains observable, but gate failures are advisory warnings (non-blocking) on baseline path.
- Decision policy candidate pruning is disabled on baseline path.

## Experimental Sandbox

- Opt-in profile: `enforcement_profile=experimental_enforced`.
- In this profile only:
  - evidence-integrity gate failures are blocking errors
  - decision-policy candidate pruning is enabled

## Evaluation Rule

- Do not promote experimental enforcement behavior to baseline based on single-run score improvements.
- Promotion requires repeated arm-separable evidence and an explicit docs update that changes baseline posture.
