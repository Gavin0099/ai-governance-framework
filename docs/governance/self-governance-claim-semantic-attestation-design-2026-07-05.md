# Self-Governance Claim Semantic Attestation Design

Status: PARTIALLY IMPLEMENTED / REPORT ONLY
Date: 2026-07-05
Scope: R2 Option B reviewer / agent semantic-boundary attestation

## DONE

DONE = the R2 Option B claim semantic attestation receipt is designed and the
inline `claim_enforcement_checker` detector emits report-only warnings. A manual
producer / caller workflow can emit durable
`artifacts/evidence/claim-attestations/*.json` receipts. This does not change
hooks, CI, schemas, runtime, gate policy, or blocking behavior.

## Problem

R2 Option A made structured `claim_support` visible to
`claim_enforcement_checker.evaluate`: if a caller declares support weaker than
the published `claim_level`, the checker can emit report-only support warnings.

That still does not show that a reviewer or agent actually inspected the final
claim wording against the evidence boundary. A final report can say "reviewed"
or imply semantic alignment without leaving a durable artifact that records:

- the claim text reviewed;
- the evidence refs considered;
- the support level the reviewer believed was justified;
- residual risks and cannot-claim boundaries;
- whether the claim was aligned, overstated, or unclear.

The problem is reviewable semantic-boundary occurrence, not semantic truth.

## Current Repository Truth

Observed surfaces for this design:

- `governance_tools/claim_enforcement_checker.py` emits report-only
  `claim_support` reasons and accepts inline `claim_semantic_attestation`
  payloads.
- `governance_tools/claim_semantic_attestation_writer.py` emits durable
  `claim_semantic_attestation.v0.1` receipts under
  `artifacts/evidence/claim-attestations/` and self-validates the receipt shape
  with the checker validator.
- `docs/governance/self-governance-markerless-claim-semantic-drift-design-2026-07-04.md`
  names Option B as the reviewer semantic-attestation follow-up.
- `docs/governance/self-governance-f2-valid-disable-attestation-design-2026-07-05.md`
  and `docs/governance/self-governance-f4-override-attestation-design-2026-07-05.md`
  establish the local receipt-family convention:
  `receipt_schema`, `reason`, `linked_commit`, and `cannot_claim`, with
  validity meaning shape/provenance only.
- `docs/governance/self-governance-review-occurrence-provenance-design-2026-07-04.md`
  establishes the same boundary for review receipts: occurrence evidence is
  not proof of review quality or independence.
- `PLAN.md` states that this repository is not a machine-authoritative semantic
  advisory system and that mutation/enforcement claims require explicit
  contracts.

No current final-report, review, hook, CI, or gate workflow produces this
receipt automatically. No current checker path reads a receipt from an artifact
path; callers must pass the parsed receipt inline to
`claim_enforcement_checker.evaluate`.

## Target Outcome

Define one report-only receipt shape and inline checker warnings:

- `claim_semantic_attestation_missing`
- `claim_semantic_attestation_invalid`
- `claim_semantic_attestation_overstated`
- `claim_semantic_attestation_unclear`

These are visible through `report_only_reasons` without changing
`semantic_drift_risk`, `enforcement_action`, reviewer override, hooks, CI, or
blocking behavior.

## Producer / Caller Workflow

Manual receipt production is available through:

```text
python -m governance_tools.claim_semantic_attestation_writer \
  --reviewed-claim "<final report claim text>" \
  --reviewed-claim-level bounded \
  --attested-support-level bounded \
  --attestation-result aligned \
  --evidence-ref "<command, artifact, or source>" \
  --attested-by "<reviewer-or-agent-id>"
```

Default output:

```text
artifacts/evidence/claim-attestations/claim-attestation-<utc>.json
```

The writer:

- records the current git `HEAD` only when `--project-root` itself is a git
  worktree root;
- refuses to write outside the project root;
- validates the produced receipt with
  `validate_claim_semantic_attestation_receipt`;
- prints the durable receipt path for the caller to paste into a final report,
  review note, or a structured checker payload.

This is a caller workflow, not automatic final-report adoption. A caller still
has to decide which claim is being attested and whether to pass the parsed
receipt inline to the checker.

## Receipt Shape

Suggested artifact root:

```text
artifacts/evidence/claim-attestations/
```

Suggested receipt:

```json
{
  "receipt_schema": "claim_semantic_attestation.v0.1",
  "status": "report_only",
  "reviewed_claim": "final claim text or stable digest",
  "reviewed_claim_level": "bounded",
  "evidence_refs": [
    "pytest tests/test_self_governance_claim_label_mutation_contract.py"
  ],
  "attested_support_level": "bounded",
  "attestation_result": "aligned",
  "attested_by": "reviewer or agent identity string",
  "linked_commit": "commit hash of the reviewed change",
  "scope_boundaries": [
    "current repository diff only"
  ],
  "residual_risks": [
    "external repos not verified"
  ],
  "cannot_claim": [
    "receipt does not prove the reviewer was correct",
    "receipt does not prove evidence truth",
    "receipt does not prove semantic correctness of the claim"
  ]
}
```

Required fields in the first detector:

- `receipt_schema == claim_semantic_attestation.v0.1`
- `status == report_only`
- `reviewed_claim` non-empty string
- `reviewed_claim_level` in `bounded | parity | strong | unbounded`
- `attested_support_level` in `bounded | parity | strong | unbounded`
- `attestation_result` in `aligned | overstated | unclear`
- `evidence_refs` non-empty list of strings
- `attested_by` non-empty string
- `linked_commit` is a stable 7-40 character hex commit hash; if `project_root`
  is supplied to the checker, it must resolve to a git commit object
- `cannot_claim` non-empty list of strings

Optional but recommended fields:

- `scope_boundaries`
- `residual_risks`
- `reviewed_claim_digest`

## Detector Semantics

The detector should be structured-input only. It should not parse arbitrary
prose such as "review passed".

Implemented payload fields for `claim_enforcement_checker.evaluate`:

```yaml
semantic_review_claimed: true | false
claim_semantic_attestation:
  <inline receipt object or parsed receipt artifact>
```

Report-only behavior:

- if `semantic_review_claimed: true` and no attestation receipt is supplied,
  emit `claim_semantic_attestation_missing`;
- if a supplied receipt is malformed, schema-mismatched, or has invalid enum /
  evidence fields, emit `claim_semantic_attestation_invalid`;
- if `attestation_result: overstated`, emit
  `claim_semantic_attestation_overstated`;
- if `attestation_result: unclear`, emit
  `claim_semantic_attestation_unclear`;
- if `attestation_result: aligned`, emit no attestation warning.
- if `linked_commit` is a moving ref such as `HEAD` instead of a hex commit,
  emit `claim_semantic_attestation_invalid`.

All of these stay in `report_only_reasons`. They must not set
`semantic_drift_risk`, must not change `enforcement_action`, and must not
create a blocker.

## Boundary And API Considerations

This is an honor-system attestation surface:

- the same agent can still write the claim and the receipt;
- `attested_by` is a string, not identity proof;
- `linked_commit` proves at most that the inline receipt points to a stable
  hex commit, and to a real commit only when `project_root` is supplied;
- `aligned` means "someone recorded alignment", not "the claim is true";
- an attestation can be stale if the final claim is edited after the receipt.

The future implementation should avoid a global schema migration. The receipt
family is intentionally local and versioned per surface.

## Failure Paths And Risk Points

1. Claim inflation through the word "attestation":
   The receipt must be described as review evidence, not proof of semantic
   correctness.
2. Broad prose parsing:
   Parsing ordinary final-report prose would create unstable false positives
   and false negatives. First slice should require structured fields.
3. Stale receipt:
   If `reviewed_claim` no longer matches the final claim or digest, the detector
   should warn in a later tranche. This implementation does not detect stale
   receipts.
4. Evidence laundering:
   The receipt can cite evidence refs that do not truly support the claim. This
   remains outside machine verification.
5. Duplicate authority:
   This receipt must not become a parallel approval authority for push, memory,
   closeout, or release.

## Fixture Expectations

Report-only fixture expectations are pinned in
`tests/test_self_governance_claim_semantic_attestation_fixtures.py`.

Expected warning codes:

- `claim_semantic_attestation_missing`
- `claim_semantic_attestation_invalid`
- `claim_semantic_attestation_overstated`
- `claim_semantic_attestation_unclear`

The fixtures also assert the non-blocking invariant:

- `enforcement_action` remains `allow`;
- `semantic_drift_risk` remains `false`;
- warnings are emitted only through `report_only_reasons`.

## Non-Goals

- No hook, CI, schema, runtime, or gate policy change.
- No LLM semantic classifier.
- No parsing of arbitrary final-report prose.
- No artifact-path reader.
- No automatic final-report, review, closeout, hook, CI, or gate producer.
- No proof that the reviewer was independent or correct.
- No proof that cited evidence supports the final claim.
- No blocker promotion.
- No `PROTECTED` mutation-proof claim.

## Claim Ceiling

This design can claim:

- the R2 Option B receipt shape and warning targets are defined;
- inline payload detection exists for missing, invalid, overstated, and
  unclear semantic-attestation states;
- a manual producer / caller workflow can emit durable
  `claim_semantic_attestation.v0.1` receipts under
  `artifacts/evidence/claim-attestations/`;
- behavior remains report-only.

This design cannot claim:

- claim semantic attestation artifact-path reading exists;
- final reports or review workflows automatically produce claim semantic
  attestations;
- markerless strong claims are fixed;
- evidence truth or semantic correctness is verified;
- reviewer authority or independence is proven;
- enforcement behavior changed;
- red-team audit is fully fixed;
- Phase E enforcement is complete.

## Recommended Implementation Tranche

Next implementation tranche:

1. decide whether the response-envelope / review workflow should call the
   producer automatically, or keep receipt production manual;
2. add artifact-path reading only after the caller contract is stable;
3. keep every warning in `report_only_reasons`;
4. do not wire hooks, CI, or blocking until a separate
   policy slice explicitly asks for those behaviors.
