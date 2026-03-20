# Runtime Failure-Mode Progress - 2026-03-20

## Summary

The repository now has its first execution-layer failure-mode slice.

This is not yet a full runtime fault-injection harness, but it is no longer
just a control-plane claim. The runtime now contains machine-readable handling
for five concrete failure-mode categories:

- `missing_required_evidence`
- `invalid_evidence_schema`
- `policy_conflict`
- `illegal_override`
- `runtime_failure`

It also has a first minimal replay check for determinism.

## What Is Now Real

### 1. Failure-Mode Contract

The repository now has an explicit failure-mode test contract:

- `docs/failure-mode-test-plan.md`
- `governance/failure_mode_test_matrix.v0.1.json`
- `tests/test_failure_mode_test_matrix.py`

This establishes the first machine-readable break-test scope instead of leaving
failure handling as an implied future task.

### 2. Runtime Evidence Failure Handling

`runtime_hooks/core/post_task_check.py` now performs machine-readable
classification for:

- missing required runtime evidence
- invalid `public_api_diff` schema

Current verdict impact behavior:

- missing required runtime evidence -> `escalate`
- invalid runtime evidence schema -> `stop`

The runtime output now includes:

- `evidence_violations`
- `evidence_violation_count` in human-readable output

### 3. Runtime Policy Conflict Handling

`runtime_hooks/core/post_task_check.py` now reads the v2.6 policy precedence
matrix and classifies:

- precedence conflicts that require runtime resolution
- forbidden overrides that should be treated as illegal

Current verdict impact behavior:

- precedence conflict -> `escalate`
- illegal override -> `stop`

The runtime output now includes:

- `policy_violations`
- `policy_violation_count` in human-readable output

### 4. Runtime Failure Fail-Closed Path

`runtime_hooks/core/session_end.py` now has a controlled fail-closed runtime
failure path for artifact emission.

When a forced runtime failure is injected:

- the hook does not crash outward as the only outcome
- the result is collapsed to `decision = RUNTIME_FAILURE`
- policy is collapsed to `STOP`
- a `runtime-failure-trace` artifact is emitted

This is the repository's first concrete execution-layer implementation of the
v2.6 `runtime_failure` violation model.

### 5. Minimal Determinism Replay

The first determinism slice is now present:

- `post_task_check` replay test verifies stable errors, warnings, and violation
  classification for identical policy/evidence input
- `session_end` replay test verifies stable decision/policy/result bundles for
  identical input
- runtime trace/verdict artifacts now include `policy_ref.runtime_version`

This directly supports the v2.6 requirement that the runtime version be part of
the traceable decision surface.

## What Was Verified

The following focused checks were executed:

- `pytest -q tests/test_failure_mode_test_matrix.py`
- `pytest -q tests/test_runtime_post_task_check.py -k "missing_required_runtime_evidence"`
- `pytest -q tests/test_runtime_post_task_check.py -k "missing_required_runtime_evidence or invalid_public_api_diff_schema"`
- `pytest -q tests/test_runtime_post_task_check.py -k "policy_conflict_from_precedence_matrix or illegal_policy_override"`
- `python -m py_compile runtime_hooks/core/session_end.py`
- `pytest -q tests/test_runtime_session_end.py -k "forced_runtime_failure"`
- `pytest -q tests/test_runtime_post_task_check.py -k "replay_is_deterministic"`
- `pytest -q tests/test_runtime_session_end.py -k "replay_preserves_verdict"`

Environment note:

- this machine still emits `.pytest_cache` warnings
- some broader `pytest` paths still encounter temp-directory permission issues
- the focused tests above are still valid and passed

## Maturity Reading

This update improves the runtime execution layer, but does not justify calling
the system `1.0`.

The most accurate reading after this slice is still:

- control plane: strong
- integration seam: stronger and more explicit
- execution layer: now materially better than pure alpha draft state
- failure-mode coverage: first real slice, still incomplete

In practical terms:

- the repository now has the beginning of a trustworthy runtime failure model
- it still does not have a full replay harness, async determinism guarantees,
  or broad fault-injection coverage

## Remaining Gaps

The largest remaining gaps after this update are:

- `hard_stop_rules` still exist as contract metadata, but runtime now treats them as policy input instead of a direct validator-side outcome switch
- the runtime does not yet evaluate all verdict paths directly from the v2.6
  decision model JSON
- replay coverage is still synchronous and narrow
- human override replay is not yet modeled as a first-class deterministic path
- async evidence arrival and re-evaluation drift are not yet stress-tested

## Bottom Line

The repository has now crossed an important line:

it no longer only describes failure handling, it executes a first runtime slice
of it.

That is meaningful progress, but it is still best understood as:

- `decision model stabilized`
- `runtime transition in progress`
- `failure-mode execution started, not completed`
