# P1-F Proposal: Plan-Reconciliation Enforcement Decision

Status: decision record. Option B was owner-approved and implemented at
`c06014c4`; Option C remains deferred.

## Problem

The canonical memory writer currently accepts an omitted
`--plan-reconciliation` argument, writes `not_declared`, and emits advisory
text. The four-week P1-E observation confirms that this omission path is used.
It does **not** establish a semantic PLAN-touch false-negative rate, a false
positive rate, or a causal effect of advisory output.

The decision is therefore narrower than “make governance stricter”:

> Which enforcement boundary, if any, should apply to future canonical memory
> writes: advisory-only, a writer input requirement, or a current-diff
> completion blocker?

## Current Repository Truth

- Since `c06014c4`, `governance_tools/memory_record.py` requires an explicit
  `--plan-reconciliation` value and rejects omission with exit 2 before a
  memory record is appended. Malformed supplied values remain input errors.
- `scripts/hooks/pre-push` reports missing declarations as advisory-only.
- `governance_tools/memory_workflow.py --fail-on-blocker` has selective
  blocking machinery, but missing `plan_reconciliation` is not currently a
  blocker candidate.
- `governance_tools/deferred_debt_report.py` is deliberately observation-only
  and does not infer whether a Git diff semantically touched `PLAN.md`.
- P1-E's final manifest is
  `docs/governance/p1e-plan-touch-manifest-2026-07-11.md`: it supports an
  observed omission signal, but withdraws the earlier ungrounded 10.5% FN
  claim.
- Proposal-time tooling classified either candidate as medium risk with
  review-required oversight and architecture-review evidence.

## Decision Boundary

Each option names a distinct enforcement boundary. Only Option B is
implemented; its focused mutation and rollback receipts are retained under
`artifacts/evidence/test-results/`. Option C still requires its own decision,
mutation contract, and rollback path.

## Options

### A. Advisory only

Continue to permit omitted declarations and record `not_declared` with
advisory output.

This was the historical behavior. It is not the selected boundary.

### B. Canonical writer requires an explicit declaration

Change the canonical writer so omission of `--plan-reconciliation` is rejected
before a memory record is appended. Valid values remain `updated`,
`not_applicable`, or `deferred:<taxonomy-reason>`.

Benefits:

- Targets the observed omission point directly.
- Has a small, local affected surface.
- Does not infer semantic PLAN-touch from a diff.

Limits:

- Covers canonical-writer use only; it cannot prove a declaration is true.
- Does not retrofit history or prevent a non-canonical direct edit.
- Is a write-time input contract, not a current-diff completion blocker.

This is the owner-selected and implemented boundary. It is a write-time input
contract, not proof that a supplied declaration is truthful.

### C. Make missing declarations a current-diff completion blocker

Extend the guard / memory-workflow / hook path so a current memory diff with a
missing declaration blocks the selected completion or push path.

Benefits:

- Covers the completion path rather than one CLI invocation.

Risks:

- Requires exact current-diff semantics, hook coverage, and bypass behavior.
- Changes what qualifies as a legal completion claim across multiple surfaces.
- Has a larger rollback and false-positive burden.

## Recommended First Implementation Tranche

The owner selected **Option B**: explicit canonical-writer declaration
requirement. Keep **Option C** deferred until a separate current-diff mutation
contract and false-positive test corpus exist.

This decision is a scope and risk judgment, not evidence that Option B
will improve user behavior or PLAN correctness.

## Scope

The implemented Option-B slice was limited to:

- `governance_tools/memory_record.py`
- `tests/test_memory_record.py`
- narrowly affected canonical-writer documentation / help text
- a dedicated mutation receipt proving omission fails before append

## Non-Goals

- No automatic PLAN synchronization.
- No semantic verification that `updated` is truthful.
- No history rewrite or reclassification of existing `not_declared` records.
- No hook, CI, pre-push, session-end, schema, or current-diff blocker change.
- No enforcement on direct/non-canonical writers beyond existing guard policy.
- No claim that advisory mode caused the observed pattern.

## Boundary and API Considerations

- Existing valid value normalization and deferred-reason taxonomy remain the
  input contract.
- The owner chose immediate mandatory declaration for canonical writer calls;
  no opt-in strict mode was introduced.
- The rejected call must append no memory entry and return a documented
  non-zero input-error exit code.
- The proposal must not silently convert any historical warning into a blocker.

## Failure Paths and Rollback

- Missing argument: reject before append; error must explain accepted values.
- Invalid deferred reason: retain existing rejection behavior.
- Writer unavailable or bypassed: existing authority guard remains a separate
  diagnostic path; this proposal must not claim coverage of it.
- Rollback: revert the narrowly scoped writer contract commit and restore the
  prior advisory behavior. No memory records are rewritten as part of rollback.

## Evidence Plan

Before implementation, freeze a mutation contract covering at least:

1. missing argument returns the chosen input-error code and writes no record;
2. each valid declaration writes exactly one canonical record;
3. invalid and vacuous deferred values still write no record;
4. legacy record parsing remains observation-compatible;
5. current `memory_workflow --check --run-guard` behavior is unchanged unless
   separately authorized;
6. a rollback replay proves the prior advisory path can be restored without
   rewriting memory history.

The expected architecture evidence is an impact review of the selected option;
the proposal-time preview is medium risk / review-required.

## Claim Ceiling

This document records the Option-B decision and its bounded implementation. It
does not claim that supplied declarations are truthful, that PLAN drift is
prevented, or that a current-diff blocker exists.

## Future Owner Decision

Option B is complete. A future, separate decision may authorize or reject
Option C; it must not be inferred from the Option-B implementation.
