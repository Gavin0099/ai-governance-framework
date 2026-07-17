# Validator Delegation Census — Plan (v0.2)

- Branch: `wip/gavinwu/validator-delegation-census`
- Canonical source: `gitlab/main`
- Fresh fetch performed: 2026-07-17
- Base commit: `e2436bcb84a5b15e0a7bd3824a7c8d2d158ca633`
- Base observation: 197 tracked Python modules under `governance_tools/`
- Status: plan reconciled — census **尚未執行**
- Authority: owner-approved plan-only reconciliation on 2026-07-17

The base observation is evidence for this plan revision, not a permanent
hard-coded population. The census execution must fetch again and pin the then
current `gitlab/main`; if that commit differs, all counts and references must be
regenerated before any row is classified.

## DONE

在 fresh-fetched、固定的 GitLab main commit 上，產出一份完整、可重現、
唯讀且 claim-bounded 的 `governance_tools/*.py` delegation census：

1. population equals the sorted tracked Python paths read from the pinned Git
   tree;
2. every row records path, observed callers, supported claims, diagnostic
   category, external candidate if any, adoption blockers, evidence references,
   and zero or more maintenance-queue cross-references;
3. two independent runs against the same base produce the same normalized
   payload hash;
4. no queue schema, runtime, provider harness, gate, tool implementation, or
   claim semantics changes are made.

## Execution preflight and tree-bound method

Run from a clean disposable checkout or worktree. The current working tree must
never define the census population or evidence.

```powershell
git fetch gitlab main
$base = (git rev-parse gitlab/main).Trim()
$population = git ls-tree -r --name-only $base -- governance_tools |
  Where-Object { $_ -like '*.py' } |
  Sort-Object
```

Tree-bound evidence commands:

- population and path existence: `git ls-tree -r --name-only $base -- governance_tools`;
- file contents: `git show "${base}:<repo-relative-path>"`;
- tracked caller search: `git grep -n <pattern> $base -- .`;
- history is not evidence for the base unless explicitly labeled historical;
- `git ls-files`, filesystem recursion, untracked files, working-tree line
  numbers, and current-index results are forbidden as base evidence.

Before producing rows, record:

- full `base_commit`;
- fetched ref name and fetch timestamp;
- population query and sorted population count;
- maintenance queue path and its blob id at the same base;
- method version `validator-delegation-census-plan.v0.2`.

## Canonical artifact contract

Output path:

`docs/governance/validator-delegation-census.v0.1.json`

Top-level fields:

| Field | Requirement |
| --- | --- |
| `schema_version` | exact value `validator_delegation_census.v0.1` |
| `generated_at` | UTC timestamp; excluded from normalized payload hash |
| `base_ref` | exact value `gitlab/main` |
| `base_commit` | full 40-character commit hash |
| `method_version` | exact value `validator-delegation-census-plan.v0.2` |
| `population_query` | exact tree-bound command description |
| `population_count` | computed from the pinned Git tree, never manually entered |
| `coverage` | expected/emitted/missing/extra/duplicate path counts and lists |
| `claim_ceiling` | exact claim limits defined below |
| `rows` | sorted ascending by repo-relative `path` |
| `normalized_payload_sha256` | SHA-256 over canonical UTF-8 JSON excluding `generated_at` and this hash field |

Canonical JSON normalization uses UTF-8, LF, recursively sorted object keys,
stable array ordering, and no insignificant whitespace. Two independent runs
against the same base must produce the same `normalized_payload_sha256`.

## Row contract

| Field | Requirement |
| --- | --- |
| `path` | unique repo-relative path from the pinned population |
| `callers` | array of observed static callers; each item has `surface`, `relation`, and `evidence_refs` |
| `caller_search_status` | `observed` / `no_static_match` / `insufficient_evidence` |
| `claims_supported` | array; use explicit `unknown` when no admissible claim mapping is found |
| `category` | primary diagnostic category |
| `secondary_categories` | zero or more additional diagnostic categories |
| `category_basis` | evidence-based reason; required for every category |
| `external_candidate` | candidate name or `null`; never an adoption decision |
| `adoption_blockers` | per-candidate GitLab/Windows assessment or explicit `unknown` values |
| `evidence_refs` | resolvable base-bound references using `git:<commit>:<path>:<line>` or recorded command evidence |
| `queue_refs` | array of zero or more `{source, defense, match_basis}` objects |

Allowed category values:

- `delegable`
- `adapter_shrink`
- `governance_semantic`
- `retire_candidate`
- `insufficient_evidence`

Use `insufficient_evidence` instead of forcing a substantive classification.
Mixed-responsibility modules keep one evidence-supported primary category and
may use `secondary_categories`; this does not authorize splitting or retiring
the module.

## Caller search boundary

Caller discovery must search the entire pinned repository tree, including
runtime hooks, CI definitions, skills, docs containing executable commands,
registries, tests, and other tools. Search patterns and zero-hit results must be
recorded as evidence.

Static search has known blind spots: dynamic import, reflection, subprocess
command construction, generated files, consumer-repo invocation, external CI,
and untracked local automation. Therefore:

- `no_static_match` does not mean unused;
- no module may become `retire_candidate` from a zero-hit grep alone;
- unresolved dynamic or external use must be `insufficient_evidence`.

## Maintenance queue cross-reference

The queue at the pinned base has 101 entries with fields including `defense` and
`source`; it has no entry `id`. The census does not alter that schema.

`queue_refs` is zero-to-many. Each reference stores:

- `source`: exact queue entry source;
- `defense`: exact queue entry defense;
- `match_basis`: `exact_path`, `exact_tool_name`, `curated_group`, or
  `manual_evidence`.

Do not use fuzzy name matching as a unique join. A queue entry may cover several
modules, and one module may relate to several entries. Each relation requires a
base-bound evidence reference.

## GitLab adoption-blocker dimensions

Evaluate each external candidate independently against the primary environment:
self-hosted GitLab EE plus Windows local development. GitHub Actions is not the
target execution environment.

| Dimension | Required question |
| --- | --- |
| execution location | Windows local hook, `.gitlab-ci.yml`, or both? |
| runner OS | Windows, Linux, both, or `unknown`? |
| license | usable for private self-hosted GitLab under verified terms? |
| ecosystem alignment | available through verified GitLab SAST/component surfaces? |
| offline/internal network | external registry or image dependency; vendoring option? |
| version pinning | immutable version/ref/image digest available? |
| evidence binding | which base-present commit/job/runtime identifiers bind the result? |

Do not carry post-base capabilities into the census. Receipt schema 1.4 exists
at this v0.2 base, but any later base must re-resolve the actual receipt and
runtime-profile surfaces from that Git tree. GitLab tier and runner OS remain
`unknown` until directly verified.

## Acceptance checks

The census is acceptable only when all checks pass:

1. emitted `path` set equals the pinned `git ls-tree` population exactly;
2. `path` values are unique, sorted, and resolve through `git show` at base;
3. all required row fields are present; unknown facts use explicit `unknown`,
   `null`, empty arrays, or `insufficient_evidence` according to the contract;
4. every non-unknown classification and queue relation has a resolvable
   evidence reference;
5. coverage reports zero missing, extra, and duplicate paths;
6. two independent runs produce the same normalized payload SHA-256;
7. artifact `base_commit` equals the fetched and reviewed commit;
8. `git diff --check` passes for the artifact;
9. reviewer confirms the artifact stays within the claim ceiling.

## Claim ceiling

This census is a fixed-repository-snapshot, reviewer-assist diagnostic only.

It may claim:

- which tracked modules existed at the pinned base;
- which static callers and claim relationships were observed in that tree;
- which diagnostic categories and external candidates were supported by the
  recorded evidence.

It cannot claim:

- that `no_static_match` means a module is unused;
- that a module is safe to retire, replace, merge, or delegate;
- that an external candidate is licensed, installable, secure, cost-effective,
  or suitable without separate verification;
- that GitLab tier, runner OS, network policy, or consumer-repo use is known when
  not directly evidenced;
- that framework governance, runtime behavior, claim semantics, or tool quality
  is correct;
- that findings generalize beyond the pinned framework snapshot;
- that any implementation, provider harness, adoption, migration, or release is
  authorized.

## Review provenance and v0.2 dispositions

The normative contract is this checked-in plan text; inaccessible chat or
attachment content is not required to reconstruct it. The owner approved the
v0.2 reconciliation on 2026-07-17 after a review and an isolated read-only
recheck produced these reproducible dispositions:

| Review issue | v0.2 disposition |
| --- | --- |
| hard-coded population was wrong | count comes from pinned `git ls-tree`; observed v0.2 base count is 197 |
| old local base lagged GitLab | fresh fetch and full GitLab commit pin required |
| queue entry id did not exist | replaced by zero-to-many `queue_refs[{source, defense, match_basis}]` |
| post-base receipt surface was cited | all surfaces must resolve at the selected base |
| reproducibility was undefined | canonical artifact, normalization, set equality, and two-run hash checks defined |
| claim ceiling was missing | explicit positive and negative claim boundaries added |
| category enum forced certainty | `insufficient_evidence` and secondary categories added |
| review authority was not durable | dispositions and verification method embedded here |

## Out of scope

- executing the census in this plan-reconciliation slice;
- modifying maintenance queue schema or entries;
- modifying runtime, hooks, gate, claim semantics, or existing tools;
- implementing a provider harness, adapter, migration, or external tool;
- changing `public_api_diff_checker` or drawing consumer-repo conclusions;
- committing, merging, or pushing this plan without separate authorization.
