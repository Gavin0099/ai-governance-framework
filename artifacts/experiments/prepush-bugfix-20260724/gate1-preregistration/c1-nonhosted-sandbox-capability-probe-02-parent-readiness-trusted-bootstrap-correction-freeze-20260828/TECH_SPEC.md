# Technical specification: parent-readiness trusted bootstrap

## Problem

The reviewed parent-readiness wrapper imports `execution_readiness` from the
working tree before it checks the execution commit or Git bindings. That
contradicts the predecessor manifest's `working_tree_code_trusted: false` and
`all_bindings_before_readiness_evidence: true` contract.

## Current repository truth

- PR #131 merged at `2615e1da701ac35d4b2f47861ff1546f2c2cae33`.
- The predecessor readiness and invocation-journal manifests remain immutable.
- Parent readiness, Probe-02, hosted requests, and Qualification-03 remain
  unauthorized and unexecuted under those freezes.
- The formal Probe-02 path already uses a streamed bootstrap; parent readiness
  did not yet have an equivalent trust root.

## Target outcome

One stdin-only bootstrap verifies every executable input from Git objects,
materializes only verified bytes outside the readiness exact-child boundary,
imports them without ambient module/path selection, removes staging, and only
then permits the existing readiness wrapper to run.

## Scope

- One new correction-freeze directory.
- One bootstrap, one manifest, documentation, and adversarial tests.
- Exact bindings to the PR #131 merge and both predecessor manifests.

## Non-goals

- No changes to predecessor freeze bytes.
- No readiness execution, Probe-02, hosted request, Qualification-03,
  randomization, producer, scorer, or arm execution.
- No new readiness semantics, receipt schema, or authority grant.
- No push or pull request in this slice.

## Affected surfaces

- New trusted bootstrap entrypoint.
- New disposable sibling staging path derived from the isolated checkout.
- Test-only synthetic Git, module-cache, path-injection, and failure fixtures.

## Boundary and API considerations

The bootstrap is infrastructure. It must not change readiness domain meaning.
Git and Python are pinned by path, bytes, and digest. The bootstrap replaces
the imported wrappers' Git adapter with its own pinned absolute adapter.
Working-tree and ambient module paths remain explicitly untrusted.

## Claim ceiling

This freeze can establish reviewable implementation bytes and synthetic trust-
boundary behavior. It cannot establish readiness PASS, filesystem readiness,
Probe-02 capability, sandbox qualification, or execution convergence.

## Failure paths and risk points

- Direct-file bootstrap launch must fail.
- Wrong commit, OID, bytes, digest, runtime, or inventory must fail before
  staging and before readiness code runs.
- Existing staging is drift and must fail closed.
- Import or cleanup failure must not run readiness or emit a receipt.
- `sys.modules`, `sys.path`, `PATH`, and Git replace objects must not select
  executable code.

## Evidence plan

- Focused unit and adversarial tests for every trust boundary above.
- Tests prove no sentinel/receipt action before complete binding.
- Fresh detached checkout test run.
- Canonical runtime-governance precommit gate.

## Implementation tranche

Implement only this directory, create one local commit, and stop for independent
review. A later repo-external authorization packet is a separate owner action.
