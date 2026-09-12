# Slice 1: incomplete review evidence cannot produce a finding-count claim

The observed PR #81 failure was a successful `gh pr view 81 --comments`
read being reported as zero findings even though inline findings were not
retrieved. `Completed`, `Commented`, exit code 0, and boilerplate describing a
thumbs-up reaction do not establish a finding count.

`governance_tools/review_evidence.py` checks raw GitHub GraphQL acquisition
results and guards an optional explicit content assessment. It is a standalone
tool: no agent reporting path, closeout hook, CI workflow, or merge command calls
it automatically. Its guarantee applies to its own output when invoked.

## Output contract

| Acquisition | Explicit content assessment | REVIEW_COMPLETENESS | FINDINGS | MERGE_READY |
| --- | --- | --- | --- | --- |
| Missing, partial, errored, or unsubmitted | Any, including zero | INSUFFICIENT | UNKNOWN | NO |
| Complete | Absent or invalid | COMPLETE | UNKNOWN | NOT_EVALUATED |
| Complete | Valid and bound to the input snapshot | COMPLETE | Supplied count | NOT_EVALUATED |

`COMPLETE` means the supplied response includes all submitted reviews, issue
comments, review threads, and each thread's comments visible to the acquisition
account. Every connection needs an explicit matching `totalCount`, terminal
`hasNextPage=false`, bodies, source identities, and no duplicate/null nodes.
GraphQL partial errors fail the check even if some data was returned. A fully
retrieved empty review list does not establish a submitted review.

Completeness does not verify server authenticity, current freshness, invisible
drafts, or the semantic correctness of a caller's count. It does not determine
whether a review is the desired reviewer or qualifies the current HEAD. The
query is deliberately bounded to 100 nodes per connection; larger connections
are reported insufficient, not silently truncated or automatically paginated.

No finding count is inferred from prose, badges, reactions, review status, or
the number of comments. A supplied assessment must contain `snapshot_sha256`
matching the tool's output, a nonempty `source` identifying the explicit content
judgment, and `findings` as a nonnegative integer (booleans are rejected).
The digest is SHA-256 of the entire parsed JSON serialized as UTF-8 with sorted
keys, compact separators, and unescaped Unicode. Array order is preserved.
Changing a body or any other snapshot data invalidates that assessment binding.
Binding proves which input the judgment refers to; it does not prove the
judgment was correct or that a human actually performed it.

The next slices will assess HEAD identity and blocking finding disposition.
This tool does neither and never returns `MERGE_READY=YES`. Test-SHA mapping,
merge controls, skill loading, Memory, and context compression are excluded.

## Replay and acquisition

Run from the repository root:

```powershell
python -m governance_tools.review_evidence --input tests/fixtures/review_evidence/pr81_incomplete.json
python -m governance_tools.review_evidence --input tests/fixtures/review_evidence/pr80_complete.json
```

PR #81 returns insufficient/unknown/no and exit 2. PR #80 returns
complete/unknown/not-evaluated and exit 0 without an assessment. Exit 0 means
the acquisition and supplied assessment-input checks passed, not merge approval.
An invalid assessment keeps the finding count unknown and returns exit 2.

The read-only query can also be used with an authenticated GitHub CLI:

```powershell
$query = python -m governance_tools.review_evidence --print-query
gh api graphql -f query="$query" -f owner=Gavin0099 -f name=ruiyi-life-map -F number=80 | python -m governance_tools.review_evidence
```

After inspecting all bodies in a saved snapshot, pass a separately authored
assessment using `--assessment path/to/assessment.json`. Its object fields are
`snapshot_sha256`, `source`, and `findings`. The tool outputs the accepted source
alongside the count. Tests explicitly assess PR #80 as one finding; a synthetic
empty-inline case checks that an explicit zero may be preserved after complete
acquisition. The synthetic case is not evidence about a historical PR.

## Fixture provenance

- `pr81_incomplete.json`: exact UTF-8 historical tool output embedded under
  `provenance.stdout`, from Antigravity conversation
  `c5c29ff7-8edd-478e-adea-ed86a3c6fcc3`, step 1524 at
  2026-09-12 03:51:46 UTC. Original output SHA-256:
  `ce6be224146eaf7b1b69a0fe5eca6ab5cb68bf9531e9a8f320541ea8e2c6e831`.
  Surrounding identity metadata comes from the event reconstruction. This is
  expressly a CLI-output record, not fabricated complete GraphQL evidence.
  It carries reviewed SHA `233430f1b71de34db6fde45916dec41eb150d278` and
  current HEAD `64027f90ef7c1b4255e9b74503e0d97869bcf348`.
  [PR #81 review](https://github.com/Gavin0099/ruiyi-life-map/pull/81#pullrequestreview-5185092363).
- `pr80_complete.json`: raw GitHub GraphQL data fetched on 2026-09-12.
  The capture includes additional author/ID/resolution fields beyond the minimal
  acquisition query. Each of the four connections has one node, matching
  `totalCount=1`, and `hasNextPage=false`. Review 5181702419 is COMMENTED on
  `c3eab1c7aafbc56a6fb904dc653733afbfdd0024`; inline comment 3991812364 is
  the one P2 finding. It is a complete-acquisition positive control, not a
  zero-finding or merge-qualification positive control.
  [PR #80 finding](https://github.com/Gavin0099/ruiyi-life-map/pull/80#discussion_r3991812364).

Validation is limited to `tests/test_review_evidence.py`: historical replay,
the real positive control, missing/partial/error paths, explicit empty data,
assessment provenance, and CLI behavior. No global validator behavior changes.
