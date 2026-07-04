# Self-Governance Evidence Artifact Metadata Design

Status: DESIGN ONLY / REPORT ONLY
Date: 2026-07-04
Scope: R3 evidence truth beyond artifact existence

## DONE

DONE = the gap between artifact existence and evidence truth is documented,
with a checkable-property ladder, future report-only slice options, and claim
ceilings, without changing `memory_authority_guard`, tests, hook, CI, schema,
runtime, or gate policy behavior.

## Problem

`memory_authority_guard.run_guard` now warns when a success-style
`test_evidence` line lacks an existing artifact path. The catalog row
`Unverified Test Evidence` is correctly registered as
`REMEDIATED baseline (artifact provenance only, advisory)`.

The remaining gap is that artifact existence proves almost nothing about the
evidence itself:

- the file may be empty or unrelated to the claimed run;
- the file may be hand-written prose rather than tool output;
- the file may describe a different commit than the memory record anchors;
- the file may record a failing run while the prose claims success.

All four cases currently pass the guard without any warning, because the check
stops at `resolved path is a file inside the project root`.

## Current Baseline

Implemented surface (report-only, advisory):

- detector: `_test_evidence_provenance_violation` in
  `governance_tools/memory_authority_guard.py`;
- trigger: success-style `test_evidence:` line in a memory block;
- checks performed:
  - at least one token matching the `artifacts/...` path pattern is present,
    otherwise reason `test_evidence_success_claim_without_artifact`;
  - at least one such token resolves to an existing file inside the project
    root, otherwise reason `test_evidence_artifact_not_found`;
- surfaced violation code: `test_evidence_provenance_not_found`;
- contract: `docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md`;
- catalog row: `Unverified Test Evidence`, status
  `REMEDIATED baseline (artifact provenance only, advisory)`.

This design does not update the catalog because the current catalog status is
still accurate for what is implemented. It defines what the next slice could
check and where checking must stop.

## Threat Model

Adversarial pattern:

```yaml
memory_type: session
commit: <real merged commit>
test_evidence: "pytest tests/test_x.py PASS, artifacts/session/fake-run.md"
```

where `artifacts/session/fake-run.md` is an empty file created with one shell
command. The guard today reports no violation: the anchor binds, the artifact
path exists, and the success prose is accepted.

The cost of fabricating passing evidence is currently one `touch`-equivalent.

## Checkable Property Ladder

Properties a local, deterministic checker can verify, ordered by cost:

| Tier | Property | Current state |
| --- | --- | --- |
| 0 | artifact path exists inside project root | implemented (advisory) |
| 1 | artifact is under an allowed durable path (`artifacts/...`), not scratch or temp | partially implied by the path regex; no explicit allowlist policy |
| 2 | artifact contains structured metadata: command, exit code, timestamp, runner identity | not implemented |
| 3 | artifact `linked_commit` matches the memory record's bound commit anchor | not implemented |

Properties that remain out of scope for any local checker:

- semantic truth of the prose claim;
- whether the recorded command actually produced the recorded output;
- independent replay of external systems (CI, remote services);
- historical artifact backfill for pre-existing memory records.

Tier 2 and Tier 3 raise the cost of fabrication from `create a file` to
`author internally consistent structured metadata`. They do not eliminate
fabrication; a hostile writer can still fake every field. This boundary must
survive into every claim ceiling below.

## Design Principle

Do not convert evidence-existence checks into an evidence-truth claim.

Reason:

- a metadata check can only prove the artifact is well-formed and
  self-consistent, never that the run happened;
- automatic re-running of recorded commands would turn a report-only guard
  into an execution surface with its own safety and cost problems;
- historical memory debt (existing records without structured artifacts) would
  instantly flood a strict check with warnings, destroying signal.

The safer path is a structured evidence receipt shape first, presence and
consistency warnings second, enforcement only after a separate policy RFC
(R4) defines blocking ownership and backcompat.

## Future Slice Options

### Option A: Structured Evidence Receipt Shape

Define a report-only receipt format that tool wrappers can emit next to raw
output:

```yaml
receipt_schema: test_evidence_receipt.v0.1
status: report_only
command: <exact command line>
exit_code: <integer>
started_at: <ISO-8601>
finished_at: <ISO-8601>
runner: <tool or wrapper identity>
linked_commit: <full or short hash>
output_artifacts:
  - <raw output path under artifacts/>
cannot_claim:
  - semantic correctness of the tested behavior
```

Report-only comparison:

- if a success-style `test_evidence` references an artifact that parses as a
  receipt, verify required fields; emit
  `test_evidence_artifact_metadata_invalid` on failure;
- if the artifact exists but is not a receipt, emit at most
  `test_evidence_artifact_metadata_missing` — a documentation warning, not a
  block, because historical artifacts predate the shape;
- `exit_code != 0` paired with success prose emits
  `test_evidence_exit_code_contradicts_claim`.

Claim ceiling:

- can show the evidence artifact is structured and internally consistent;
- cannot prove the command ran or the output is genuine.

### Option B: Linked-Commit Consistency Check

Once receipts carry `linked_commit`, compare it against the memory record's
bound commit anchor:

- mismatch emits `test_evidence_linked_commit_mismatch`;
- missing `linked_commit` stays inside the Option A missing-metadata warning;
- resolution reuses the existing commit-anchor provenance logic rather than
  inventing a second git surface.

Claim ceiling:

- can show the evidence artifact points at the same commit the memory claims;
- cannot prove the evidence was produced at that commit.

### Option C: Durable Path Allowlist Policy

Make the implicit `artifacts/...` prefix an explicit policy: which roots count
as durable evidence locations, excluding scratch, temp, and ignored paths.

This is the smallest slice but the weakest:

- it only hardens Tier 1;
- it does not touch the fabrication cost problem;
- it risks false positives on legitimate non-standard layouts in external
  consumer repos.

Claim ceiling:

- can reject evidence parked in throwaway locations;
- cannot say anything about artifact content.

## Recommended Next Implementation Path

Prefer Option A first, then Option B as a follow-up inside the same receipt
shape. Option C should ride along only if external-consumer layouts are
audited first.

Reasoning:

- Option A creates the structured surface that every later check (B, and any
  R4 blocking candidate) depends on;
- it stays deterministic and machine-checkable, aligned with the R2 decision
  to prefer structured support over semantic classifiers;
- it can remain advisory while producing concrete mutation fixtures;
- historical debt is handled by design: missing receipts warn softly instead
  of failing.

## Mutation Contract Shape For Future Work

Scenario: `Fabricated Evidence Artifact Content`

Adversarial input:

- success-style `test_evidence` with an existing artifact path;
- the artifact is empty, unrelated, hand-written, or records a failing run;
- the memory record otherwise binds a valid commit anchor.

Current expected observation:

- `run_guard` reports no evidence violation;
- this layer is a `VULNERABLE baseline` behind the existence-only
  `REMEDIATED baseline` recorded in the catalog.

Future report-only target:

- with a receipt present, emit `test_evidence_artifact_metadata_invalid`,
  `test_evidence_exit_code_contradicts_claim`, or
  `test_evidence_linked_commit_mismatch` as applicable;
- without a receipt, emit only `test_evidence_artifact_metadata_missing`;
- no `PROTECTED` claim is allowed at any tier, because every field remains
  fabricatable by a hostile writer; the honest ceiling is
  `PARTIALLY REMEDIATED baseline (structured artifact metadata only, advisory)`.

## Non-Goals

This design does not:

- modify `memory_authority_guard.py` or any detector;
- add or change tests;
- add the receipt schema file or any schema;
- change hook, pre-push, CI, runtime, or gate policy behavior;
- re-run or replay any recorded command;
- validate the semantic truth of evidence prose;
- backfill or re-verify historical memory records;
- turn any warning into a block;
- update `docs/e1-mutation-catalog.md`;
- claim evidence content verification exists.

## Claim Ceiling

This design can claim:

- artifact existence checking is implemented and evidence-content checking is
  not;
- a structured evidence receipt is the preferred future report-only path;
- metadata checks raise fabrication cost but can never prove evidence truth;
- no enforcement behavior changed.

This design cannot claim:

- evidence content is verified;
- fabricated artifacts are detected;
- `test_evidence` semantics are `PROTECTED`;
- linked-commit consistency checking exists;
- red-team audit is fully fixed;
- Phase E enforcement is complete.
