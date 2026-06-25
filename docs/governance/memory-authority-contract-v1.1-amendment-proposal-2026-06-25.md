# MEMORY_AUTHORITY_CONTRACT v1.1.0 Amendment Proposal

Date: 2026-06-25
Status: proposal-only
Scope: design-only amendment plan
Runtime behavior change: no
Tooling change: no
Enforcement change: no

## Problem

`governance/MEMORY_AUTHORITY_CONTRACT.md` is still version `1.0.0` from
2026-04-30. It describes early Phase 1 memory authority semantics built around
old daily bullet entries such as `- what changed:` plus `commit hash` and
`session_id` anchors.

Current repository practice has moved beyond that contract:

- session-derived memory is now written by `governance_tools.memory_record`;
- canonical records include `memory_type`, `record_format_version`, `writer`,
  `commit`, `commit_hash`, `session_id`, `memory_binding`, `test_evidence`,
  `next_step`, and `plan_reconciliation`;
- the memory authority guard detects `non_canonical_writer`, including
  old-format entries after the canonical-writer cutoff;
- `memory_workflow` reports `active_non_canonical_writer`, warning counts,
  blockers, and `completion_claim_allowed`;
- runtime observations may intentionally use non-source sentinels such as
  `runtime-observation-no-source-commit`, which should be represented as
  `memory_binding: unbound` rather than treated as source-bound evidence.

The result is an authority contract drift: the operational tools enforce and
report newer concepts that the active contract does not name.

This is not yet an enforcement failure. It is a contract/readability risk: future
agents can read the active contract and incorrectly believe old-format memory
entries remain acceptable for new session-derived memory.

## Current Repository Truth

Observed files and facts:

- `governance/MEMORY_AUTHORITY_CONTRACT.md`
  - Version `1.0.0`.
  - Status says Phase 1 warning mode, non-blocking.
  - Session-derived memory section describes bullet entries starting with
    `- what changed:` and requires `commit hash` or `session_id`.
  - Violation table lists `unbound_memory`, `structural_memory_auto_write`,
    `private_memory_cited`, and `missing_canonical_memory`.
  - Section 5 requires any contract change to create a new version with name,
    rationale, evidence, and updated violation semantics table.

- `governance/MEMORY_PROTOCOL.md`
  - Requires all new session-derived memory entries to use
    `governance_tools.memory_record`.
  - Prohibits direct markdown append in `- what changed:` or `- what_changed:`
    format.
  - Requires `python -m governance_tools.memory_workflow --check --repo .`
    before claiming completion for memory edits.
  - Describes `--run-guard`, `--fail-on-blocker`, advisory hook behavior, and
    closeout receipt memory workflow surfaces.

- `governance_tools/memory_record.py`
  - Emits `writer: governance_tools.memory_record`.
  - Emits `record_format_version: 1.0`.
  - Emits both `commit` and `commit_hash` with the same value.
  - Computes `memory_binding = "bound"` only when the commit string matches a
    hash-like regex; otherwise it writes `unbound`.

- `governance_tools/memory_authority_guard.py`
  - Keeps `unbound_memory` as warning evidence.
  - Detects session-derived records not written by the canonical writer as
    `non_canonical_writer`.
  - Treats old-format entries in daily files dated on or after 2026-05-01 as
    `non_canonical_writer`.
  - Tracks active non-canonical writer violations from the active window
    beginning 2026-06-02.
  - Provides optional `--fail-on-active-non-canonical-writer` behavior.

- `governance_tools/memory_workflow.py`
  - Classifies memory diffs as governed memory tasks.
  - Summarizes `non_canonical_writer`, `active_non_canonical_writer`,
    `missing_canonical_memory`, and `unbound_memory`.
  - Computes `completion_claim_allowed` from whether the guard ran and whether
    current blockers exist.
  - Keeps historical warning debt distinct from current blocker candidates.

- `PLAN.md`
  - Already claims canonical writer, active-window guard summary, dispatcher
    routing, and opt-in blocker path.
  - Explicitly does not claim historical memory debt cleanup or full memory
    workflow enforcement.

## Target Outcome

Produce a future `MEMORY_AUTHORITY_CONTRACT.md` v1.1.0 amendment that aligns the
contract text with current memory writer, guard, and workflow semantics without
changing runtime/tool behavior.

The amendment should make the contract answer these questions accurately:

1. What is the canonical format for new session-derived memory?
2. What makes a record source-bound versus observation-only/unbound?
3. Which violation codes exist today?
4. Which violation codes are historical warning evidence versus active blocker
   candidates?
5. What does `completion_claim_allowed` mean and not mean?
6. What is explicitly not proven by a memory record being present, bound, or
   canonical-writer formatted?

## Scope

In scope for the eventual v1.1.0 contract amendment:

- bump contract version from `1.0.0` to `1.1.0`;
- add an amendment summary with name, rationale, and evidence;
- update session-derived memory format from old bullet style to canonical writer
  record shape;
- document `writer`, `record_format_version`, `commit`, `commit_hash`,
  `session_id`, `memory_binding`, `test_evidence`, `next_step`, and
  `plan_reconciliation`;
- document source-bound versus runtime-observation/unbound records;
- update the violation semantics table to include `non_canonical_writer`,
  `old_format_entry_after_canonical_writer_cutoff`, and
  `active_non_canonical_writer` behavior;
- document that historical `unbound_memory` and historical
  `non_canonical_writer` remain warning evidence unless a separate cleanup or
  enforcement slice is approved;
- align wording with `MEMORY_PROTOCOL.md` and current tool behavior.

## Non-Goals

Not in scope:

- changing `governance_tools.memory_record` schema;
- changing `memory_authority_guard.py` behavior;
- changing `memory_workflow.py` behavior;
- changing hook, CI, pre-push, closeout, or enforcement behavior;
- cleaning historical `unbound_memory=229` or `non_canonical_writer=86` debt;
- backfilling old memory files;
- redefining `memory_binding: bound` as proof that a commit was validated beyond
  the writer's current hash-like-string rule;
- changing CodeBurn, Hermes, task-cost, or authority-loader surfaces;
- claiming semantic correctness of memory contents.

## Affected Surfaces

Primary affected surface for the future amendment:

- `governance/MEMORY_AUTHORITY_CONTRACT.md`

Reference surfaces to cite or compare, but not modify in the first amendment:

- `governance/MEMORY_PROTOCOL.md`
- `governance_tools/memory_record.py`
- `governance_tools/memory_authority_guard.py`
- `governance_tools/memory_workflow.py`
- `PLAN.md`

No runtime hook, validator, schema, CI, or enforcement file should be touched in
the v1.1.0 contract text amendment.

## Boundary and API Considerations

This is an authority text alignment, not an API change.

However, the contract is a governance authority document. Wording changes can
change how future agents interpret memory validity. The amendment must therefore
be conservative:

- describe current tool behavior rather than inventing new behavior;
- distinguish writer format validity from factual correctness;
- distinguish source-bound records from runtime-observation records;
- keep historical debt warning-only unless separately approved;
- avoid implying that canonical writer output proves review acceptance, remote
  push, semantic correctness, or enforcement.

A key boundary: `memory_binding: bound` currently means the writer saw a
hash-like commit string. It does not, by itself, prove the commit exists on a
remote, that the diff was reviewed, or that the memory claim is true.

## Claim Ceiling

This proposal may claim:

- the current active contract is stale relative to current memory writer/guard
  practice;
- a v1.1.0 contract amendment is the appropriate next documentation slice;
- the proposed amendment would align contract text with existing observed tool
  behavior if implemented and reviewed.

This proposal must not claim:

- the contract has already been amended;
- memory validation behavior changed;
- enforcement behavior changed;
- historical memory debt was cleaned;
- canonical writer output proves semantic correctness;
- `memory_binding: bound` proves remote push or review acceptance;
- task-cost or CodeBurn measurement improved.

## Failure Paths or Risk Points

1. Silent contract edit
   - Risk: modifying `MEMORY_AUTHORITY_CONTRACT.md` without a version bump and
     amendment rationale violates the contract's own Section 5.
   - Mitigation: v1.1.0 amendment section must be explicit.

2. Format validity inflated into truth
   - Risk: readers treat canonical writer format as proof the memory claim is
     true.
   - Mitigation: add explicit non-claim language: canonical writer format is an
     admissibility/traceability signal, not semantic correctness.

3. Bound inflated into verified
   - Risk: readers treat `memory_binding: bound` as proof the commit exists on
     both remotes or was reviewed.
   - Mitigation: define bound as current writer binding signal only; require
     separate evidence for review/push/remote alignment.

4. Historical debt accidentally upgraded
   - Risk: adding active-window language makes old `unbound_memory` or old
     `non_canonical_writer` appear newly blocking.
   - Mitigation: preserve historical debt as warning evidence unless another
     approved slice changes enforcement.

5. Observation-only records misclassified as invalid
   - Risk: runtime observations using `runtime-observation-no-source-commit` are
     read as malformed because they are unbound.
   - Mitigation: define observation-only unbound records as valid when they are
     explicit about runtime-state scope and non-source binding.

6. Contract amendment expands into tooling
   - Risk: v1.1.0 text work grows into guard changes, cleanup, or enforcement.
   - Mitigation: keep first tranche docs-only.

## Evidence Plan

For the eventual amendment implementation:

1. Diff-scope validation
   - Verify only `governance/MEMORY_AUTHORITY_CONTRACT.md` changes in the source
     commit.

2. Text consistency review
   - Compare amended sections against:
     - `governance/MEMORY_PROTOCOL.md`
     - `governance_tools/memory_record.py`
     - `governance_tools/memory_authority_guard.py`
     - `governance_tools/memory_workflow.py`

3. Memory workflow check after memory record
   - If a canonical memory entry is written for the amendment commit, run:
     `python -m governance_tools.memory_workflow --check --repo . --run-guard`

4. No behavior validation required for docs-only amendment
   - Do not run broad tests unless the amendment touches tooling.
   - If tooling is touched, that is a separate slice and requires focused tests.

## Implementation Tranche Recommendation

Recommended next tranche:

- Implement v1.1.0 as a docs-only amendment to
  `governance/MEMORY_AUTHORITY_CONTRACT.md`.
- Do not touch tooling.
- Do not clean historical memory debt.
- Commit the contract amendment separately.
- Write canonical memory bound to the contract amendment commit.
- Review before push.

Deferred options, not commitments:

- Add a report-only checker that compares contract-listed violation codes with
  `memory_authority_guard.py` output codes.
- Add focused docs tests if the contract becomes machine-parsed in the future.
- Revisit enforcement thresholds only after observed false-positive /
  false-negative evidence supports it.

## Not Claimed By This Proposal

- No contract amendment has been applied.
- No memory writer schema changed.
- No memory guard behavior changed.
- No hook, CI, closeout, or pre-push behavior changed.
- No historical memory debt was cleaned.
- No task-cost metric was improved.
- No CodeBurn integration exists.
