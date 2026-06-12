# Reviewer Entrypoint

This is the shortest accurate path for an external reviewer to evaluate this
framework. Its goal is to reduce reviewer misreading, not to promote the
project. Every claim below is bounded by the canonical claim boundaries in
[`PLAN.md`](../PLAN.md) ("Active Claim Boundaries"); if this document and
PLAN.md ever disagree, PLAN.md wins.

## 1. What this framework claims

- **Contract-bound task execution.** Each governed task gets a contract
  (allowed scope, forbidden scope, required evidence, done definition)
  before execution, and a closeout receipt with explicit non-claims after.
- **Artifact-backed verification.** Completion claims must be supported by
  inspectable artifacts (test output, receipts, snapshots), not by the
  agent's own summary.
- **Fail-closed decision gate at a single enforcement point.** Unknown
  scope, missing evidence, or unclear authority blocks. The enforcement
  topology is single-point (E1-B Phase 2 finding); mutation protection is
  **not** claimed.
- **Selective CI enforcement for memory workflow.** CI blocks exactly one
  class: current-diff `active_non_canonical_writer`. Hooks are
  advisory-only. Historical memory debt is warning-only.
- **Fleet visibility as evidence, not judgment.** The fleet matrix and
  `required_verified` ratio are *freshness-window evidence* under an
  event-driven refresh policy — regenerated before rollout, release, or any
  external claim citing fleet state. The ratio is not a health score and
  idle-period decay is designed behavior.
- **Scope taxonomy by evidence duty.** Four repo scope sets (fleet,
  submodule consumer, F-7 consumer, external contract repo) are defined by
  what evidence each owes, not by location. Membership in one set implies
  nothing about the others.

## 2. What this framework does not claim

These are normative boundaries, not disclaimers:

- No AI semantic correctness guarantee.
- Not a security boundary: violations become visible, reviewable, and
  attributable; deliberate bypass is not prevented.
- No mutation protection and no multi-point enforcement topology.
- No continuous monitoring, no scheduler, no daemon, no automatic reviewer
  polling or handoff. Reviewer interaction is manual / resume-triggered.
- No fleet rollout completion. One external consumer (post-apply state)
  has been verified; that is single-target evidence, not generality.
- No automated PLAN reconciliation. The `plan_reconciliation` field is a
  per-record declaration, advisory-checked; it is not auto-sync.
- No copy-based consumer update support (classification pending; current
  ceiling: not solved).
- Test pass is not production safety; matrix-visible is not verified;
  observation records are not enforcement authority; a closeout receipt is
  not "governance complete".

## 3. What evidence is required before "done"

A completion claim in this repo is admissible only with all of:

1. **A bound canonical memory record** in `memory/YYYY-MM-DD.md`, written
   by `governance_tools.memory_record`, with commit hash, test evidence,
   and a `plan_reconciliation` declaration
   (`updated | not_applicable | deferred:<taxonomy-reason>`).
2. **Drift checker clean**: `governance_drift_checker` reports
   `severity=ok`, empty errors and warnings.
3. **Scoped diff**: the commit contains only the files the slice declared.
   Dirtied runtime ledgers are restored, not bundled.
4. **Test evidence at the right tier**: focused tests for the touched
   surface, recorded in the memory record — not "tests pass" in prose.
5. **Claim ceiling stated**: what the slice can claim and explicitly
   cannot claim, recorded in PLAN.md before or with the work.

If any of these is missing, the correct status is "not done", regardless of
how complete the work narrative sounds.

## 4. How to read advisory vs. enforcement

The README capability table carries a **Claim class** column. Read it
strictly:

| Claim class | Meaning | What a reviewer may infer |
|---|---|---|
| **Enforced** | Blocking behavior exists (gate / CI blocker) with the exact scope stated in its Notes | Violations *inside that scope* cannot land silently |
| **Advisory** | Reports and warns; never blocks | Presence of a warning is signal; absence of a warning proves nothing |
| **Observation** | Produces evidence/visibility only | Input for human judgment; never a gate result |
| **Cannot claim** | Designed or partial; not claimable | Treat as absent when evaluating guarantees |

Two common misreadings to avoid:

- **Advisory output is not enforcement evidence.** A hook that printed a
  warning did not "check" anything in the enforcement sense.
- **An Enforced row is enforced only for its stated scope.** Example: the
  memory-workflow CI blocker covers current-diff
  `active_non_canonical_writer` only — citing it as "memory workflow is
  enforced" is claim inflation.

## Where to verify, not trust

- [`PLAN.md`](../PLAN.md) — canonical claim boundaries and pending work.
- `memory/` — daily session-derived records binding claims to commits.
- `artifacts/session/` — latest fleet matrix snapshot (check
  `matrix_generated_at` before citing it).
- `tests/` — the enforcement claims above each have focused tests naming
  their scope (e.g. `tests/test_ci_memory_workflow_check.py`,
  `tests/test_governance_workflow_contract.py`).
