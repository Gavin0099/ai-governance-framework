# Slice 2: PR HEAD and reviewed commit identity

The PR #81 reconstruction found reviewed commit
`233430f1b71de34db6fde45916dec41eb150d278` followed by current PR HEAD
`64027f90ef7c1b4255e9b74503e0d97869bcf348`. Those identities must not qualify as
the same reviewed tree. `governance_tools/review_head_identity.py` adds that
comparison without changing Slice 1 or implementing finding/merge policy.

## Contract

`compare_review_heads(current_head, reviewed_head)` compares full 40-character,
nonzero hexadecimal SHA-1 values. Hexadecimal case is normalized. Abbreviations,
whitespace, missing values, and other invalid inputs remain unknown, even if
their strings or prefixes are identical. This tool is scoped to the SHA-1 IDs
in these GitHub cases; it does not resolve prefixes or support other formats.

| Identity input | MATCH | MERGE_READY |
| --- | --- | --- |
| Valid, different full SHAs | NO | NO |
| Missing, abbreviated, or invalid SHA | UNKNOWN | NO |
| Same valid full SHA | YES | NOT_EVALUATED |

`assess_review_head(snapshot, review_id)` consumes a raw GraphQL response of the
same shape used by Slice 1. It calls `assess_review_evidence(snapshot)` and
retains the unchanged result under `REVIEW_EVIDENCE`. It takes current HEAD from
`pullRequest.headRefOid` and reviewed HEAD from the explicitly selected review's
`commit.oid`. No external completeness result or boolean is accepted as proof.

The caller must specify one positive integer review database ID. Missing,
unknown, invalid, or duplicate selected IDs cannot qualify. The tool never
chooses the latest review or chooses a different review because ordering changes.
Choosing the required reviewer is outside this slice.

Identity remains independent of acquisition: matching identities can yield
`MATCH=YES` while insufficient Slice 1 evidence forces `MERGE_READY=NO`. A known
mismatch also remains visible when other evidence is incomplete. Complete
acquisition plus matching identities yields `MERGE_READY=NOT_EVALUATED`, never
`YES`. Neither completeness nor matching identities creates a finding count.

## Replay commands

From the repository root, historical PR #81 identity pair:

```powershell
python -m governance_tools.review_head_identity --current-head 64027f90ef7c1b4255e9b74503e0d97869bcf348 --reviewed-head 233430f1b71de34db6fde45916dec41eb150d278
```

Expected: `MATCH=NO`, `MERGE_READY=NO`, exit 2. These full SHAs come from the
existing `pr81_incomplete.json` reconstruction metadata. The original CLI
output is still incomplete; this pure identity replay does not fabricate a
complete PR #81 GraphQL snapshot. Passing that original fixture through the
snapshot entrypoint honestly returns `MATCH=UNKNOWN` with insufficient evidence.

Real PR #80 positive control, including the Slice 1 prerequisite:

```powershell
python -m governance_tools.review_head_identity --input tests/fixtures/review_evidence/pr80_complete.json --review-id 5181702419
```

Expected: complete acquisition, both SHAs equal to
`c3eab1c7aafbc56a6fb904dc653733afbfdd0024`, `MATCH=YES`,
`MERGE_READY=NOT_EVALUATED`, exit 0. PR #80 still contains its actual P2 finding.
Exit 0 means identity matched and, in snapshot mode, acquisition was complete;
it does not approve a merge. `--input -` accepts a raw GraphQL response on stdin.
The existing Slice 1 `--print-query` provides the read-only acquisition query.

## Scope and verification

Tests reuse both existing historical fixtures; altered-head, reordered-review,
and malformed-data tests are explicitly synthetic boundary cases. Run:

```powershell
python -m pytest -q tests/test_review_head_identity.py tests/test_review_evidence.py
```

The implementation is standalone and local. It does not fetch fresh GitHub
state, prove snapshot authenticity, prevent a HEAD change after the check,
resolve review threads, inspect P0/P1 disposition, or qualify CI test commits.
In particular, a CI merge-candidate SHA needs its own mapping and cannot be
treated as the PR HEAD merely by raw string equality. No Memory, skill-loading,
branch-protection, runtime-hook, or actual merge behavior is changed.
