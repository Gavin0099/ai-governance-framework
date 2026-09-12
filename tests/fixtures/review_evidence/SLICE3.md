# Slice 3: unresolved P0/P1 predicate

`governance_tools/review_blocking_findings.py` adds one predicate after Slice 1
acquisition completeness and Slice 2 selected-review HEAD identity. It directly
calls Slice 2 on the same raw snapshot; it never accepts external prerequisite
flags. No merge command, hook, CI policy, Memory, or skill is changed.

## Assessment authority and coverage

The input is an explicit caller assessment, not an automatically inferred list
of findings. The tool checks binding, source coverage, field validity, and the
P0/P1 predicate. It does not prove that the caller classified the text correctly
or actually fixed a defect. A caller who mislabels a real P1 as NON_FINDING or
P2 can still make a semantically wrong assessment pass; this slice does not
claim independent semantic detection. GitHub thread resolution metadata alone
does not establish defect resolution.

An assessment JSON object contains:

- `snapshot_sha256`: Slice 1's digest of the full snapshot.
- `review_id`: the exact positive integer review database ID selected in Slice 2.
- `source`: the named source of the explicit content/disposition judgment.
- `sources`: exactly one classification for every acquired body. Keys are
  `review:<databaseId>`, `issue_comment:<databaseId>`, and
  `inline_comment:<databaseId>`. Include all reviews, including earlier reviews;
  selecting a matching review does not discard older open findings.

Each source explicitly specifies `classification: NON_FINDING` with no finding
data, or `classification: FINDINGS` and a nonempty `findings` list. No default
NON_FINDING classification is generated. Omitted, duplicate, unknown, or empty
FINDINGS entries fail qualification.

Each finding has a unique nonempty `id`, `severity: P0|P1|P2|P3`, and
`disposition: UNRESOLVED|RESOLVED|UNKNOWN`. A RESOLVED P0/P1 also needs a nonempty
`resolution_evidence` reference supplied by the assessor. Reference correctness,
authority, and real resolution are not validated by this predicate. The binding
ensures the assessment refers to this snapshot, not that its judgment is true.

The accepted assessment source is returned with its counts. These counts are
**counts of caller-assessed unresolved findings**, not independently verified
defect counts. Slice 1's own `FINDINGS=UNKNOWN` is retained without upgrading it.

## Result contract

| Condition | BLOCKING_GATE | P0/P1 counts | MERGE_READY |
| --- | --- | --- | --- |
| Acquisition incomplete or HEAD not matched | UNKNOWN | UNKNOWN | NO |
| Missing/invalid/unbound assessment or source coverage | UNKNOWN | UNKNOWN | NO |
| Unknown P0/P1 disposition or missing resolution reference | UNKNOWN | UNKNOWN | NO |
| Valid assessment with at least one unresolved P0/P1 | BLOCKED | Caller-assessed counts | NO |
| Valid assessment without unresolved P0/P1 | PASS | 0 / 0 | NOT_EVALUATED |

P2/P3 do not block this predicate, including an explicitly UNKNOWN disposition.
An invalid severity is unknown because it could be blocking. Missing/invalid
required fields also remain unknown. A resolved GitHub thread alone never clears
a P1; an explicit assessor resolution judgment and reference are still required.

No branch returns `MERGE_READY=YES`. PASS and CLI exit 0 qualify only this local
predicate over the supplied assessment. Unknown/blocked results return exit 2.
Required test execution, reviewer qualification, live-state freshness, and
atomic merge protection remain outside scope.

## Real and synthetic replay evidence

- `pr81_complete.json` is a raw GitHub GraphQL response acquired on 2026-09-12,
  with every connection and nested comments fully returned. Actual HEAD is
  `64027f90ef7c1b4255e9b74503e0d97869bcf348`; review 5185092363 remains on
  `233430f1b71de34db6fde45916dec41eb150d278`. Its three inline comments contain
  P1 3994999882 and P2 3994999888 / 3994999891. All threads have `isResolved=false`
  in this acquired snapshot; that does not reconstruct the resolution state at
  merge time. The earlier `pr81_incomplete.json` is kept intact.
- `pr81_assessment.json` explicitly classifies these source bodies and marks
  the three findings unresolved. It is manually authored test input, not a
  GitHub-produced severity/disposition ledger. Actual PR #81 still stops at
  the mismatched HEAD and cannot receive qualified P0/P1 counts.
- `synthetic_exact_head_pr81()` in `tests/test_review_blocking_findings.py`
  separately changes a copy's HEAD to the reviewed SHA, labels the copy
  SYNTHETIC, and binds an assessment to that copy. It carries the real P1 body
  into an explicitly counterfactual same-HEAD case to exercise BLOCKED. It is
  not evidence that PR #81 historically had matching final HEAD and review.
- The existing `pr80_complete.json` plus new `pr80_assessment.json` is the real
  completeness/identity positive control with one caller-assessed unresolved
  P2 and no P0/P1. Its generic review and summary are explicitly NON_FINDING.
  It passes this predicate without receiving merge approval.

## Run locally

From the repository root, the actual stale-head PR #81 case (exit 2):

```powershell
python -m governance_tools.review_blocking_findings --input tests/fixtures/review_evidence/pr81_complete.json --review-id 5185092363 --assessment tests/fixtures/review_evidence/pr81_assessment.json
```

The PR #80 positive control (exit 0):

```powershell
python -m governance_tools.review_blocking_findings --input tests/fixtures/review_evidence/pr80_complete.json --review-id 5181702419 --assessment tests/fixtures/review_evidence/pr80_assessment.json
```

Without `--assessment`, a matching complete snapshot remains UNKNOWN. The CLI
checks acquisition and identity before reading the assessment file, so a missing
ledger cannot obscure an already failed prerequisite. `--input -` accepts stdin.

The known P1 predicate, unknown/invalid states, exhaustive coverage, prior
reviews, resolved-thread boundary, and CLI error paths are covered by:

```powershell
python -m pytest -q tests/test_review_blocking_findings.py tests/test_review_head_identity.py tests/test_review_evidence.py
```
