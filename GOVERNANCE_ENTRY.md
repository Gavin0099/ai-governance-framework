# GOVERNANCE_ENTRY.md

This file is the only valid starting point for governance adoption in this repository.

## Canonical Authority Declaration (Executable)

Canonical authority source for this repository:

- Primary authority repo: `Gavin0099/ai-governance-framework`
- Constitutional authority files:
  - `GOVERNANCE_ENTRY.md`
  - `AGENTS.md`
  - `PLAN.md`
  - `governance/PHASE_D_CLOSE_AUTHORITY.md`

Hard rule:

- No local file or derived output may override constitutional authority unless explicitly registered as a higher-authority constitutional artifact.

## Precedence Declaration (Highest -> Lowest)

1. Constitutional authority documents
2. Registered authority artifacts
3. Runtime governance outputs
4. Reviewer-visible advisory surfaces
5. README / local notes / examples
6. AI-generated summaries
7. "tests passed" statements

Hard rule:

- Lower-precedence signals must never override higher-precedence authority.

Enforcement scope (claim ceiling):

- This precedence is a reviewer- and agent-facing constitutional rule, not a
  machine-enforced runtime guarantee. At runtime, `session_start` only filters
  which governance documents load (by `audience` / `default_load`) and asserts
  that `human-only` documents are not loaded. It does not resolve conflicts
  between loaded documents by precedence: the authority ranker
  (`resolve_conflict`) and the `can_override` / `overridden_by` frontmatter
  fields have no runtime decision consumer and are advisory only.
- The separate decision-model `policy_precedence` (consumed in
  `runtime_hooks/core/post_task_check.py`) is a different axis — policy-type
  verdict precedence — and does not enforce this document hierarchy.
- Do not infer that a lower-precedence signal is mechanically blocked from
  overriding a higher one; today that rule is upheld by reviewer and agent
  discipline, not by a runtime gate. Registered as a report-only VULNERABLE
  baseline in `docs/e1-mutation-catalog.md`
  (`self_governance_authority_precedence`).

Before any governance claim, identify all five items:

1. Canonical authority source
2. Runtime enforcement path
3. Reviewer-visible evidence path
4. Closeout obligation
5. Memory promotion path

Do not infer governance state from:

- tests passed
- README presence
- AGENTS presence
- runtime hooks existence
- copied files

Evidence type separation is mandatory:

- Implementation evidence: unit/integration tests, functional behavior checks
- Governance evidence: pre-task gate, post-task advisory, reviewer-visible traces, session artifacts
- Authority evidence: canonical authority source, register/provenance, baseline alignment

Rule:

Implementation evidence alone must never be used to claim governance completion.

Fail-closed semantics:

- Presence is not proof.
- File existence does not imply adoption, enforcement, authority validity, reviewer readiness, or governance completion.
- Unknown governance state must resolve to `manual_review_required`, never `assume_valid`.

Pre-task forbidden inferences:

- Asking for "governance pull command" before authority source is identified
- Claiming governance completion from tests only
- Inferring authority from file existence

Violation handling:

- analysis blocked
- manual authority verification required

Closeout requirement:

Governance closeout must be machine-verifiable. Prose-only closeout is non-authoritative.

Minimum closeout payload shape (example):

```json
{
  "authority_source_verified": true,
  "runtime_path_executed": true,
  "pre_task_gate_observed": true,
  "post_task_advisory_visible": true,
  "reviewer_surface_present": true,
  "closeout_artifact_generated": true,
  "validation_dataset_updated": true,
  "governance_status": "manual_review_required"
}
```

Allowed `governance_status` values:

- `complete`
- `incomplete`
- `blocked`
- `void`
- `manual_review_required`
- `authority_unverified`
- `runtime_unverifiable`

## Explicit Non-Claims

This document does not claim:

- passing tests proves governance validity
- copied governance files imply adoption
- runtime hooks existence implies enforcement
- README governance sections imply authority alignment
- AI-generated summaries are authoritative
- machine-verifiable closeout alone proves reviewer approval

## Agent Prohibition

Agents are prohibited from self-declaring governance completion.
Final governance completion may only be declared by reviewer decision or a registered authority artifact path.
