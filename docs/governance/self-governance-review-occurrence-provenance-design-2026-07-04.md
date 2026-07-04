# Self-Governance Review Occurrence Provenance Design

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-04
Scope: R1 review occurrence provenance

## DONE

DONE = review occurrence provenance is designed as a report-only evidence
surface, including candidate artifact shape, mutation baseline, non-goals, and
claim ceiling, without changing blocking, hook, CI, schema, runtime, or gate
policy behavior.

## Problem

The red-team audit identified a review ritual gap:

- an agent can write `review passed` or `scoped diff review completed` as prose;
- no artifact is required to prove a review occurrence happened;
- no report-only surface records reviewed commit range, reviewed files,
  reviewer identity, verdict, or evidence checked;
- no gate distinguishes an actual review artifact from a final-report claim.

This is an occurrence / provenance gap, not a review-quality validator gap. A
review artifact can show that a review was recorded. It cannot prove the review
was correct, independent, or sufficient.

## Authority Boundary

This design is deliberately below enforcement authority:

- It does not change `governance/PHASE_D_CLOSE_AUTHORITY.md`.
- It does not create a Phase D closeout artifact.
- It does not authorize push, memory write, cross-repo write, closeout, or
  runtime policy change.
- It does not make review mandatory for every commit.
- It does not make missing review occurrence blocking.

`REVIEW_RECEIPT` in `docs/governance/operator-prompt-playbook-2026-06-26.md`
already states that review receipts are evidence, not authority. This design
keeps that boundary and only proposes a more auditable occurrence surface.

## Candidate Artifact

Candidate path convention:

```text
artifacts/review-occurrence/review-occurrence-<YYYYMMDDTHHMMSSZ>.json
```

Candidate schema shape:

```yaml
receipt_schema: review_occurrence_receipt.v0.1
receipt_type: review_occurrence
status: report_only
writer_id: <tool or agent that serialized the receipt>
written_at: <timestamp>
review_task: <short task label>
review_mode: scoped_diff | commit_pair | artifact | state
reviewed_scope:
  files:
    - <repo-relative path>
  commit_range:
    base: <commit or null>
    head: <commit or null>
  artifact_refs:
    - <repo-relative path>
reviewer:
  actor_type: human | agent | tool
  reviewer_id: <non-empty identifier>
  independence_claim: declared | not_declared | not_applicable
verdict: APPROVED | CHANGES_REQUESTED | ESCALATED | NOT_REVIEWED
findings:
  blocking: <count>
  warnings: <count>
  suggestions: <count>
evidence_checked:
  - kind: command | artifact | source
    ref: <command, path, or source label>
    result: PASS | FAIL | NOT RUN | NOT PRESENT | NOT CLAIMED
claim_ceiling:
  - <what this receipt can support>
cannot_claim:
  - <what this receipt cannot support>
push_gate: allowed | not_allowed | not_applicable
push_gate_meaning: evidence_only_not_authority
```

Required semantics:

- `status: report_only` means the receipt is observation evidence only.
- `verdict` records the reviewer's stated outcome; it is not independently
  proven by the receipt.
- `evidence_checked` must name actual commands, artifacts, or source refs. A
  value like `checked=yes` is not sufficient evidence.
- `push_gate` mirrors reviewer advice only. It cannot authorize push by itself.
- `reviewer.actor_type: agent` is allowed for agent review evidence, but it is
  not a human authority act and cannot satisfy Phase D closeout requirements.

## Mutation Baseline

Scenario: `Unreceipted Review Claim`

Adversarial input:

- final report claims `scoped diff review passed`;
- no `review_occurrence_receipt.v0.1` artifact exists;
- no `REVIEW_RECEIPT` block or equivalent structured review evidence is linked;
- commit / push recommendation relies on the prose claim.

Current expected observation:

- no existing repo gate detects this as a structured violation;
- the claim can pass as ordinary prose;
- this remains a `VULNERABLE baseline`.

Future report-only observation target:

- if a final envelope contains a machine-readable review claim such as
  `review_claim: occurred`, `review_verdict: APPROVED`, or
  `review_receipt_ref`, an advisory checker may warn when the referenced
  receipt is missing or malformed;
- prose-only review claims should not be parsed as enforcement input in the
  first implementation slice, because broad prose parsing would blur claim
  boundaries.

Suggested warning code:

```text
review_occurrence_receipt_missing
```

Suggested malformed-artifact warning code:

```text
review_occurrence_receipt_invalid
```

Both codes must remain report-only unless a later policy RFC explicitly changes
their enforcement status.

## Non-Goals

This design does not:

- implement the receipt writer;
- implement an advisory checker;
- update hooks, pre-push, CI, schemas, runtime hooks, or gate policy;
- require all reviews to produce receipts;
- validate review correctness or reviewer independence;
- turn `APPROVED` into action authority;
- replace `PHASE_D_CLOSE_AUTHORITY`;
- add or claim `PROTECTED` mutation proof.

## Evidence Plan For A Future Implementation Slice

Minimum focused validation, if this design is implemented later:

- fixture with a machine-readable review claim and missing receipt emits
  `review_occurrence_receipt_missing`;
- fixture with a malformed receipt emits `review_occurrence_receipt_invalid`;
- fixture with a valid report-only receipt emits no missing/malformed warning;
- fixture with prose-only `review passed` remains outside the first detector's
  enforcement input, and the non-claim is documented.

The implementation slice should not run broad governance gates unless it touches
runtime, hook, CI, schema, or shared policy code.

## Relationship To Existing Surfaces

| Surface | Relationship |
| --- | --- |
| `REVIEW_RECEIPT` prompt pattern | Source for evidence-only semantics and receipt fields |
| `PHASE_D_CLOSE_AUTHORITY.md` | Higher-authority closeout contract; this design cannot satisfy it |
| `reviewer-closeout-gate-mutation-contract-2026-06-27.md` | Different surface: Phase D closeout gate mutation proof |
| `self-governance-red-team-remaining-slices-2026-07-04.md` | Parent remaining-slice inventory that prioritizes R1 |

## Claim Ceiling

This design can support:

- review occurrence provenance has a candidate report-only artifact shape;
- the unreceipted review-claim gap is documented as a `VULNERABLE baseline`;
- future advisory detection should key off structured review claims, not broad
  prose parsing;
- no enforcement behavior changed.

This design cannot claim:

- review occurrence is currently verified;
- review quality, independence, or correctness can be verified;
- push, memory write, closeout, or cross-repo action is authorized;
- Phase D closeout authority is satisfied;
- red-team audit is fully fixed;
- Phase E enforcement is complete;
- any `PROTECTED` mutation proof has been added.
