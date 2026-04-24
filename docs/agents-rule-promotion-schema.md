# AGENTS Rule Promotion Schema

This document defines the minimal machine-readable contract for `AGENTS.md`
candidate-rule promotion.

It exists to enforce promotion discipline before any runtime extraction or
automatic drafting surface is added.

## Scope

This schema covers three things only:

- candidate identity
- candidate-to-section mapping
- reviewer promotion ledger

It does not define extraction logic, scoring logic, or automatic mutation.

## Candidate Types

Allowed `candidate_type` values:

- `must_test_path`
- `forbidden_behavior`
- `escalation_trigger`
- `risk_level_boundary`

v0.1 does not allow freeform candidate classes.

## Section Mapping

Candidate types map to `AGENTS.md` section keys as follows:

- `must_test_path` -> `must_test_paths`
- `forbidden_behavior` -> `forbidden_behaviors`
- `escalation_trigger` -> `escalation_triggers`
- `risk_level_boundary` -> `risk_levels`

This mapping is fixed so reviewers can reconstruct where a promoted rule belongs.

## Candidate Identity

Each candidate must have a stable `candidate_id` derived from:

- `candidate_type`
- `normalized_candidate`

The normalized form exists to reduce duplicate phrasing drift.

`candidate_id` hash source is strictly:

- `candidate_type`
- canonical `normalized_candidate`

It must not include:

- `human_candidate`
- `review_note`
- wording variants
- reviewer text

Example:

```json
{
  "candidate_id": "must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
  "candidate_type": "must_test_path",
  "section_key": "must_test_paths",
  "normalized_candidate": "runtime_hooks/core/pre_task_check.py",
  "human_candidate": "runtime_hooks/core/pre_task_check.py",
  "evidence_count": 5,
  "evidence_window_days": 14,
  "observed_from": [
    "post_task_check",
    "reviewer_escalation"
  ],
  "repo_specificity": "high",
  "status": "needs_human_review",
  "first_seen_at": "2026-04-24T10:00:00Z",
  "last_seen_at": "2026-04-24T12:00:00Z",
  "evidence_refs": [
    "session:end:2026-04-24:abc123"
  ]
}
```

## Candidate Constraints

Required candidate fields:

- `candidate_id`
- `candidate_type`
- `section_key`
- `normalized_candidate`
- `human_candidate`
- `evidence_count`
- `evidence_window_days`
- `observed_from`
- `repo_specificity`
- `repo_specificity_basis`
- `status`

Rules:

- `evidence_count >= 1`
- `evidence_window_days >= 1`
- `observed_from` must not be empty
- `repo_specificity` must be one of `low|medium|high`
- `status` must be one of `observed|needs_human_review|rejected`

`promoted` is intentionally not a candidate status.

Promotion authority lives in the reviewer ledger, not in the candidate artifact.

## Canonicalization Contract

v0.1 intentionally narrows canonicalization instead of pretending generic semantic
normalization is solved.

- `must_test_path` -> canonical path-like value only
- `forbidden_behavior` -> normalized imperative phrase
- `escalation_trigger` -> normalized trigger phrase
- `risk_level_boundary` -> normalized risk-boundary phrase

If a source cannot be reduced to one of these forms deterministically, it is not
yet a valid v0.1 promotion candidate.

## Repo Specificity Contract

`repo_specificity` alone is too subjective, so every candidate must also include
`repo_specificity_basis`.

Allowed basis values:

- `real_path`
- `real_command`
- `irreversible_boundary`
- `concrete_side_effect`
- `generic_only`

Rule:

- `repo_specificity=high` requires at least one concrete basis value other than `generic_only`

## Promotion Ledger

Candidate artifact alone is not promotion.

Reviewer decisions must leave a separate ledger entry:

```json
{
  "candidate_id": "must_test_path:runtime_hooks/core/pre_task_check.py:2b51b5c328ef",
  "promotion_decision": "approved",
  "approved_by": "reviewer",
  "review_source": "pr_review",
  "review_ref": "review:thread:42",
  "approved_at": "2026-04-24T13:00:00Z",
  "target_section": "must_test_paths",
  "evidence_refs": [
    "session:end:2026-04-24:abc123",
    "review:thread:42"
  ],
  "review_note": "Repeated evidence and repo-local path specificity are sufficient.",
  "agents_patch_status": "proposed"
}
```

Allowed `promotion_decision` values:

- `approved`
- `rejected`
- `needs_revision`

Allowed `agents_patch_status` values:

- `not_proposed`
- `proposed`
- `landed`

Rules:

- `approved` requires non-empty `evidence_refs`
- `rejected` and `needs_revision` require `review_note`
- `target_section` must match a canonical AGENTS section key
- `review_source` and `review_ref` are required so approval is auditable

## Negative Memory

Rejected or revision-requested candidates must remain visible as ledgered
history. The goal is to stop generic or low-value rules from repeatedly
resurfacing as if they were new evidence-backed proposals.

Minimum suppression contract for `rejected` decisions:

- `suppress_resurfacing_days`
- `suppression_until`
- `resurfacing_condition`

v0.1 rule:

- rejected candidates are suppressed for a bounded window
- resurfacing is only allowed when evidence materially changes

## Authority Boundary

This schema does not grant promotion authority to AI.

AI may:

- construct candidate objects
- normalize identity
- draft ledger-ready proposals

AI may not:

- declare a rule promoted
- write `reviewer_verified` as fact without explicit reviewer action
- mutate canonical governance truth silently
