# P1-F Proposal: Plan-Reconciliation Enforcement Decision

Status: proposal only; owner decision required before implementation.

## Problem

The canonical memory writer currently accepts an omitted
`--plan-reconciliation` argument, writes `not_declared`, and emits advisory
text. The four-week P1-E observation confirms that this omission path is used.
It does **not** establish a semantic PLAN-touch false-negative rate, a false
positive rate, or a causal effect of advisory output.

The decision is therefore narrower than “make governance stricter”:

> Should future canonical memory writes require an explicit reconciliation
> declaration at write time, or should missing declarations instead become a
> current-diff completion blocker?

## Current Repository Truth

- `governance_tools/memory_record.py` normalizes an omitted value to
  `not_declared` and writes it successfully; malformed supplied values already
  exit with an input error.
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

## Target Outcome

An owner-approved, reversible P1-F implementation decision with one explicit
enforcement boundary, a mutation contract, and a rollback path. This proposal
does not select or implement that boundary.

## Options

### A. Require an explicit writer argument

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

### B. Make missing declarations a current-diff completion blocker

Extend the guard / memory-workflow / hook path so a current memory diff with a
missing declaration blocks the selected completion or push path.

Benefits:

- Covers the completion path rather than one CLI invocation.

Risks:

- Requires exact current-diff semantics, hook coverage, and bypass behavior.
- Changes what qualifies as a legal completion claim across multiple surfaces.
- Has a larger rollback and false-positive burden.

## Recommended First Implementation Tranche

If the owner elects to implement P1-F, prefer **Option A only** as the first
tranche: explicit canonical-writer declaration requirement. Keep Option B
deferred until a separate current-diff mutation contract and false-positive
test corpus exist.

This recommendation is a scope and risk judgment, not evidence that Option A
will improve user behavior or PLAN correctness.

## Scope

For a future Option-A implementation slice only:

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
- The owner must choose whether the requirement is immediately mandatory for
  all canonical writer calls or introduced as an explicit opt-in strict mode.
  This is an authority and compatibility decision, not an implementation
  detail.
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

This document proposes alternatives and an evidence plan only. It does not
claim that any blocker exists, that the writer is changed, that declarations
are truthful, that PLAN drift is prevented, or that P1-F is authorized.

## Owner Decision Required

Choose one:

1. Keep advisory mode; close P1-F without implementation.
2. Authorize a separate Option-A mutation-contract slice.
3. Authorize a separate Option-B current-diff blocker design slice.
