# Self-Governance Red-Team Remaining Slice Plan

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-04
Scope: red-team remaining-item inventory and next-slice split

## DONE

DONE = self-governance red-team remaining gaps are inventoried and split into
bounded follow-up slices without changing blocking, hook, CI, schema, or gate
policy behavior.

## Purpose

This note separates three different questions that were previously easy to mix:

1. What did the red-team audit already force into visible, reviewable form?
2. Which gaps remain true `VULNERABLE baseline` items?
3. Which future changes would cross from report-only visibility into
   enforcement policy and therefore require a new mutation contract / policy
   decision before implementation?

This document does not change any runtime behavior. It is a planning artifact
for the next governance slices.

## Current Red-Team State

### Memory anchor / evidence surface

The memory lane is now substantially hardened as report-only visibility:

| Red-team item | Current state | Claim ceiling |
| --- | --- | --- |
| A: fabricated commit anchor | fabricated 5-40 hex `commit` no longer binds inside a git worktree unless the object resolves | `REMEDIATED baseline`; report-only provenance check |
| A: fabricated `session_id` anchor | arbitrary `session_id` no longer binds without runtime artifact provenance | `REMEDIATED baseline`; report-only provenance check |
| C: success-style `test_evidence` with no artifact | emits `test_evidence_provenance_not_found` warning | `REMEDIATED baseline`; artifact existence only, not evidence truth |
| B: canonical writer bypass via non-session `memory_type` | active-window session-shaped non-session entries emit `session_like_non_session_memory_type` | `REMEDIATED baseline`; advisory only |
| F: `run_guard ok=True` ambiguity | result now exposes `ok_meaning`, `authority_integrity_status`, `report_only_violation_codes`, `not_claimed`, and `claim_ceiling` | `REMEDIATED baseline`; interpretation only |

Remaining boundary: these fixes make suspicious memory claims visible and
regression-testable. They do not prove the prose content is true, re-run tests,
or make warnings blocking.

### Claim-label surface

The claim-label lane is partially hardened:

| Red-team item | Current state | Claim ceiling |
| --- | --- | --- |
| D: self-labeled bounded claim with lexical strength markers | emits `claim_label_understates_claim_text` and advisory `downgrade` | `REMEDIATED baseline`; lexical proxy only |
| D: markerless strong claim | still returns `enforcement_action: allow` when the strong wording avoids known markers | `VULNERABLE baseline` |

Remaining boundary: the checker still cannot compare actual semantic claim
strength against the caller-supplied `claim_level`, nor can it verify that
evidence supports the final claim.

### Review ritual surface

The original audit also identified the commit-pair review ritual as honor-system
only. Current state:

- A final report can say a narrow review happened.
- No report-only contract currently proves a review artifact exists.
- No gate validates review verdict, reviewer identity, or reviewed commit pair.

This is still an open design gap. It should not be turned into blocking until
the artifact shape, mutation scenario, and claim boundary are defined.

## Remaining Gaps

### R1: Review occurrence provenance

Problem: `review passed` can be written as prose without a review artifact,
verdict, reviewer identity, or reviewed commit range.

Minimum report-only slice:

- define a review-occurrence artifact shape;
- document a mutation scenario where the final report claims review occurred
  but no artifact exists;
- add advisory detection only if the report has machine-readable review claims.

Non-goals:

- no mandatory reviewer gate;
- no blocking pre-commit / pre-push behavior;
- no claim that a review artifact proves review quality.

Suggested status after slice: `VULNERABLE baseline` or
`PARTIALLY REMEDIATED baseline (artifact presence only, advisory)`.

### R2: Markerless claim semantic drift

Problem: `claim_enforcement_checker` can catch known strength markers, but a
strong claim can be phrased without marker words and still self-label as
`bounded`.

Minimum design slice:

- keep this separate from memory authority;
- decide whether the next step is another lexical proxy, a structured
  precondition requirement, or a true semantic-vs-label review surface;
- document the mutation contract before changing enforcement.

Non-goals:

- no broad language model classifier hidden behind an enforcement claim;
- no blocking semantic claim gate without a mutation contract;
- no `PROTECTED` claim while markerless examples remain undetected.

Suggested status after slice: keep `Markerless Strong Claim` as
`VULNERABLE baseline` unless a concrete detector exists.

### R3: Evidence truth beyond artifact existence

Problem: `test_evidence` now warns when success prose lacks an artifact path, but
artifact existence does not prove the command ran, passed, or corresponds to the
claimed commit.

Minimum design slice:

- define which evidence properties are checkable locally:
  - artifact path exists;
  - artifact is under an allowed durable path;
  - artifact contains command / exit code / timestamp / linked commit fields;
  - linked commit matches the memory record.
- define which properties remain out of scope:
  - semantic truth of prose;
  - independent replay of external systems;
  - historical artifact backfill.

Non-goals:

- no automatic test re-run;
- no full evidence ontology;
- no blocker until historical debt and portability are handled.

Suggested status after slice: `PARTIALLY REMEDIATED baseline (structured
artifact metadata only, advisory)` if metadata checks are added; otherwise
remain design-only.

### R4: Blocking policy for memory authority warnings

Problem: `run_guard` still returns `ok=True`, `enforcement_action: allow`, and
empty `blocking_violation_codes`. This is intentional Phase 1 behavior, but a
future blocker would be a policy change rather than a small detector tweak.

Minimum policy slice before implementation:

- choose the smallest candidate blocking class, likely active-window
  `session_like_non_session_memory_type` or newly-created fabricated anchors,
  not historical `unbound_memory`;
- define backcompat treatment for existing memory debt;
- define hook / pre-push / CI ownership;
- add mutation contract proving the blocker survives the expected bypass;
- document escape hatch and reviewer override semantics.

Non-goals:

- no direct upgrade of all `unbound_memory` warnings to blockers;
- no retroactive de-verification of historical memory without a migration plan;
- no enforcement claim from `ok=True` or warning counts alone.

Suggested status after slice: policy RFC / design decision first, code second.

## Recommended Order

1. R1 review occurrence provenance, report-only design.
2. R2 markerless claim semantic drift, contract design.
3. R3 evidence artifact metadata design.
4. R4 blocking policy RFC, only after R1-R3 define what evidence can be trusted.

Reasoning: R1 and R2 are still pure self-governance truth gaps. R3 decides how
far evidence can be mechanically checked. R4 changes enforcement semantics, so
it should wait until the earlier surfaces have mutation contracts and claim
ceilings.

## Cannot Claim

This document cannot claim:

- red-team audit fully fixed;
- semantic truth or provenance enforcement implemented;
- `test_evidence` content verified;
- review occurrence or review quality verified;
- markerless strong claim detection fixed;
- `unbound_memory` or other memory warnings made blocking;
- Phase E enforcement complete;
- any `PROTECTED` mutation proof added.

## Evidence Read For This Split

- `governance/REVIEW_CRITERIA.md`
- `docs/e1-mutation-catalog.md`
- `docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md`
- `docs/governance/self-governance-claim-label-mutation-contract-2026-07-04.md`
- `governance/MEMORY_AUTHORITY_CONTRACT.md`
- `governance_tools/memory_authority_guard.py`
- `memory/04_review_log.md`
- `memory/03_knowledge_base.md`
