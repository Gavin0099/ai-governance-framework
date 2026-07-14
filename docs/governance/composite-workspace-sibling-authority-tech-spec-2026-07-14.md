# Composite Workspace Sibling Governance Authority — Review-Only Tech Spec

Status: independently reviewed and approved; first report-only tranche
implemented at `6e4e5439`; no F-7 expansion authority

Case boundary: `E2-CONSUMER-03`, the eToken System ART multi-root workspace,
is the sole evidence case used by this specification.

## Review and Implementation Disposition

The authority model and the report-only first tranche were independently
reviewed and approved. Commit `6e4e5439` implemented the bounded census as
`governance_tools/composite_workspace_census.py` with focused coverage in
`tests/test_composite_workspace_census.py`.

The implementation accepts one explicit coordinator root plus an explicit
sibling allowlist, reports each Git repository independently, and leaves every
valid repository's membership `unratified`. It does not read a workspace file
as authority, invoke F-7, write consumer repositories, create membership
artifacts, commit, or push.

An isolated run against the three eToken repositories produced the four-line
human summary and parseable JSON expected by this specification. Its per-repo
governance gaps agreed with the existing `E2-CONSUMER-03` evidence packet, and
the original consumer repositories remained unchanged and clean. The raw live
census JSON was not retained as a durable tracked receipt, so this disposition
records the reviewed result without claiming future byte-for-byte replay.

This checkpoint closes only the report-only census tranche. Bilateral
membership, workspace authority, sibling mutation, aggregate F-7 execution,
and workspace-wide completion remain unimplemented and unapproved.

## Problem

The eToken operator uses one IDE workspace and one AI-agent task across three
independent Git repositories:

- `etoken-system-art` — workspace coordinator, framework submodule, PLAN, and
  project memory;
- `etoken-server-art` — sibling product repository;
- `etoken-client-art` — sibling product repository.

Current F-7 successfully updates the coordinator repository, but it accepts one
`repo_root`, installs repo-local AGENTS and hooks only there, and computes
`full_update_completed` only from that repository's stages. The server and
client repositories remain separate Git roots without repo-local AGENTS,
hooks, contracts, or readiness.

The unresolved authority question is not whether the three repositories are
used together. That operating fact is established for this case. The question
is whether and how a workspace coordinator may declare, inspect, or update
sibling repositories without silently escalating one repository's governance
authority across independent Git trust boundaries.

## Current Repository Truth

### Framework behavior

1. `governance_tools.f7_full_update.run_f7_full_update()` receives one
   `repo_root` and classifies that root before selecting a backend.
2. For a submodule consumer, F-7 passes that same root to
   `update_governance_submodule()`.
3. `_refresh_repo_local_instructions()` writes `AGENTS.base.md` and `AGENTS.md`
   beneath that root only.
4. `_ensure_hook_advisory()` resolves that root's Git common directory and
   installs hooks there only.
5. `governance/F7_FULL_UPDATE.md` defines implemented automation for one
   `submodule_consumer`; it does not claim coverage for all repo roles.
6. `docs/ADOPTION_MODEL.md` requires consumer classification before tooling
   expansion and permits `full_update_completed` only for a specific update
   with bound evidence.
7. No current tracked authority model defines a composite workspace or grants
   one repository authority over sibling Git roots.

### eToken case evidence

The tracked evidence packet is
`docs/governance/e2-composite-workspace-evidence-2026-07-14.md`.

Observed facts:

- `eToken_System_ART.code-workspace` names the coordinator, server, and client
  repositories.
- The workspace file also names an absent `../etoken_dongle` path. This proves
  the IDE workspace is useful discovery evidence but is not reliable authority.
- The user reports using one AI-agent task across all three repositories and
  treating `etoken-system-art` as the shared governance and memory center.
- An isolated canonical F-7 update moved the coordinator framework pointer from
  `f278172a` to GitLab `486bda76`.
- The apply receipt durably fingerprints remote freshness, before/after
  framework commits, and `update_status=updated`.
- The original full F-7 stdout containing `full_update_completed` and the
  post-apply `already_current` output was observed in-session but was not
  preserved as a durable tracked JSON artifact. Future composite evidence must
  retain raw command output rather than relying only on a receipt summary.
- After the isolated update, server and client readiness remained `ready=false`
  with no AGENTS, hooks, PLAN, contract, or known framework version.
- The original three consumer repositories remained unchanged and clean.

### Current conclusion

The existing `full_update_completed` vocabulary is repo-local. It is valid for
the coordinator's F-7 workflow and cannot be promoted to a workspace-wide
completion claim.

## Target Outcome

Define a reviewable authority model in which:

1. each Git repository remains sovereign over its instructions, hooks,
   contract, dirty state, commits, and pushes;
2. a workspace coordinator may enumerate candidate sibling repositories but
   cannot govern or mutate them by discovery alone;
3. workspace membership requires explicit, durable, bilateral authority before
   any future mutating orchestration;
4. repo-local F-7 completion and workspace aggregate status remain distinct;
5. missing or unratified siblings are visible without invalidating an otherwise
   valid repo-local F-7 result;
6. a future implementation can start report-only and prove its classification
   behavior before any F-7 expansion.

## Scope

This specification defines:

- repo, workspace, sibling, and F-7 authority boundaries;
- the evidence status of IDE workspace discovery;
- candidate authority models and their disposition;
- repo-local versus workspace aggregate completion semantics;
- memory, PLAN, contract, hook, commit, and push boundaries;
- failure paths for a future report-only audit and later orchestrator;
- one smallest recommended implementation tranche.

## Non-Goals

This specification does not:

- modify F-7, updater, runtime, hooks, schemas, or validators;
- create a composite-workspace manifest or parser;
- write AGENTS, hooks, contracts, PLAN, or memory into any eToken repository;
- run another consumer update;
- commit or push consumer changes;
- define IDE-wide or user-profile authority;
- make `.code-workspace` files governance authority;
- claim workspace-wide adoption, enforcement, or completion;
- generalize from eToken to fleet-wide prevalence or effectiveness;
- solve multi-repository atomic commit, rollback, or release coordination.

## Authority Model

### Authority layers

| Layer | May declare | May inspect | May mutate | Cannot imply |
| --- | --- | --- | --- | --- |
| Repository authority | Its own AGENTS, contract, hooks, PLAN/memory policy, and update intent | Its own tracked and local state | Its own root after normal dirty-state and user-authority checks | Authority over sibling Git roots |
| Workspace discovery | Candidate paths opened together by an IDE/workspace file or explicit CLI list | Existence, Git-root identity, and report-only readiness | Nothing | Membership, consent, enforcement, or update authority |
| Workspace coordinator | Desired membership and coordination intent in a future tracked declaration | Declared candidates and their separately reported states | Its own repository only | Permission to write siblings |
| Sibling opt-in | Acceptance of a coordinator/workspace identity in a future repo-owned artifact | Its own membership and delegated coordination fields | Its own repository, or an explicitly authorized orchestrator acting under the same user request | Transfer of commit/push authority or waiver of repo-local checks |
| F-7 repo execution | Update intent for one classified `repo_root` | One repo's pointer, instruction, memory, hook, normalization, and adoption stages | That repo only | Workspace-wide completion |
| Future workspace orchestrator | An explicit set of opted-in member repos for one invocation | Per-member F-7/readiness results | Sequential per-repo calls only after explicit allowlist and preflight | Atomicity, implicit rollback, or automatic commit/push |

### Bilateral membership rule

A coordinator declaration alone is insufficient. A future mutating workspace
workflow requires both:

1. a tracked coordinator-side membership declaration with stable workspace and
   member identifiers; and
2. a tracked sibling-side opt-in that references the same workspace identity
   and coordinator repository.

Until both exist and validate, a sibling is `discovered_candidate`, not
`governed_member`.

The exact artifact names and schema are intentionally deferred. Choosing them
changes trust structure and requires a separately reviewed schema/design slice.

### Path and identity rule

Membership identity must use repository identity plus a reviewed remote or
other durable repository identifier. A relative filesystem path alone is not
authority because it may be stale, redirected, duplicated, symlinked, or point
to a different checkout.

Discovery must resolve and report:

- absolute candidate path;
- Git toplevel;
- repository identity/remote evidence when available;
- current HEAD;
- clean/dirty/staged state;
- whether coordinator declaration and sibling opt-in agree.

Discovery must not follow a path outside the explicit operator-provided search
boundary or mutate a candidate while its identity is unresolved.

## Surface-Specific Boundaries

### AGENTS authority

- An AGENTS file governs its own directory tree according to the active agent's
  instruction-resolution rules.
- A coordinator AGENTS file does not automatically govern sibling directories.
- References to sibling repositories in prose are coordination context, not
  executable authority.
- A future orchestrator may install/refresh sibling AGENTS only after bilateral
  membership, explicit invocation scope, and that sibling's dirty-state checks.

### Hooks

- Hooks are Git-repository-local machine state.
- Each sibling requires its own hook installation and validation.
- Coordinator hook success cannot satisfy a sibling hook stage.
- A workspace aggregate may report per-member hook status but cannot average
  missing hooks into an overall success.

### Domain contracts and validators

- A contract applies only where its authority and resolution path are explicit.
- A coordinator contract cannot silently validate sibling product semantics.
- Shared external contracts remain possible, but each sibling must explicitly
  reference or adopt them.
- Validator success is always reported per member and per declared contract.

### PLAN and memory

- A coordinator may hold a shared workspace roadmap and cross-repo coordination
  memory.
- Shared memory must name the repository and commit to which an operational
  record applies.
- Shared workspace memory does not prove sibling-local writer coverage,
  freshness, hooks, or evidence admissibility.
- A sibling may explicitly delegate coordination records to the coordinator in
  a future opt-in contract, but commit/push evidence and repo-specific risk
  decisions remain attributable to the sibling repository.

### Commit and push

- Workspace membership never grants commit or push authority.
- Each repository preserves its own requested commit/push intent.
- A future workspace operation must report per-member commit and push status.
- Partial multi-repo completion is not atomic and must be disclosed; automatic
  rollback is not assumed.

## F-7 Completion Semantics

### Repo-local status

`full_update_completed` remains unchanged and means:

> Every required F-7 stage for the explicitly invoked repository root returned
> an eligible state for that specific update.

Future reporting should pair it with an explicit scope such as
`completion_scope=repo` before any composite-workspace feature is introduced.
This is a presentation clarification, not a status-value change proposed by
this slice.

### Workspace aggregate status

A future workspace surface must use a separate aggregate axis rather than
reusing `full_update_completed`.

Candidate report-only values:

| Aggregate value | Meaning |
| --- | --- |
| `not_declared` | Candidate siblings were discovered, but no ratified workspace membership exists. |
| `partially_declared` | Coordinator and sibling declarations do not cover the same member set. |
| `declared_unverified` | Bilateral membership exists, but one or more members were not checked. |
| `partially_verified` | At least one member was checked successfully and at least one is missing, failed, blocked, or unverified. |
| `all_members_verified` | Every declared member has a separate eligible repo-local result for the same bounded invocation. |
| `blocked` | Aggregate execution was explicitly requested and cannot safely continue. |

These are proposed semantics only. They are not schema, runtime output, or
implemented vocabulary.

### Warning versus blocker

- When F-7 is invoked for one repository, discovered siblings are advisory.
  Their absence or lack of opt-in must not retroactively invalidate that
  repository's valid F-7 result.
- When an operator explicitly requests a workspace-wide check, unratified or
  unchecked siblings prevent `all_members_verified` and produce a partial or
  unverified aggregate.
- When an operator explicitly requests workspace-wide mutation, unresolved
  identity, missing bilateral opt-in, staged work, dirty governance surfaces,
  or an unsafe member path is a blocker for that member and for an aggregate
  success claim.

## Candidate Models

| Candidate | Description | Decision | Reason |
| --- | --- | --- | --- |
| IDE workspace as authority | Treat `.code-workspace` membership as permission to govern siblings. | Reject | IDE-specific, stale entries observed, no sibling consent, path-only identity. |
| Coordinator-only authority | Let the governance center write every named sibling. | Reject | Cross-repo authority escalation and commit/push ambiguity. |
| Independent repos only | Keep F-7 per repo and provide no workspace visibility. | Safe fallback | Preserves trust boundaries but leaves the observed operator model invisible. |
| Bilateral opt-in plus per-repo execution | Coordinator declares members; each sibling opts in; orchestration calls repo-local checks separately. | Recommended target model | Preserves sovereignty while supporting one workspace view. |
| Recursive F-7 | Extend current F-7 to discover and mutate siblings directly. | Reject as first tranche | Mixes discovery, authority, writes, partial failure, and aggregate claims before the authority model is proven. |

## Boundary and API Considerations

Potential future surfaces, not authorized by this spec:

- a report-only composite workspace census/audit entrypoint;
- a tracked coordinator declaration and sibling opt-in artifact;
- a validator for bilateral membership and repository identity;
- a separate workspace orchestration layer that invokes existing repo-local
  F-7 rather than making F-7 recursively discover siblings;
- a workspace aggregate report distinct from the current F-7 result;
- durable raw-output evidence for each member invocation.

The existing `run_f7_full_update(repo_root=...)` API should remain repo-local in
the recommended model. A later orchestrator would call it once per authorized
member and preserve each result separately.

## Failure Paths and Risk Points

| Failure | Required posture |
| --- | --- |
| Stale workspace entry | Report candidate missing; never infer membership or failure of a valid repo-local update. |
| Duplicate or similarly named checkout | Resolve Git identity and HEAD; do not use display name as identity. |
| Symlink/path escape | Refuse paths outside the explicit boundary unless separately authorized. |
| Coordinator declaration without sibling opt-in | Report `discovered_candidate` or partial declaration; no write. |
| Sibling opt-in references wrong coordinator | Fail membership validation; no write. |
| Dirty or staged sibling | Block mutation for that sibling; preserve other repos; report partial aggregate. |
| Different framework remotes/targets | Report per-member targets; never flatten to one workspace version claim. |
| Mid-sequence failure | Stop subsequent mutation by default; disclose completed members; do not claim atomic rollback. |
| Hook install succeeds only in coordinator | Repo-local coordinator success; aggregate remains partial. |
| Shared memory lacks repo/commit binding | Treat as coordination narrative, not member evidence. |
| Raw F-7 stdout not retained | Downgrade independently reproducible completion evidence; retain receipt and observed state separately. |
| Commit or push not explicitly requested | Do neither, even when all member checks pass. |

## Evidence Plan

### Report-only classification fixtures

The first implementation must use isolated fixtures covering:

1. coordinator plus two valid sibling Git repositories;
2. one stale/missing workspace path matching the observed eToken dongle entry;
3. duplicate repository names at different paths;
4. coordinator-only declaration;
5. bilateral declaration match and mismatch;
6. dirty and staged sibling states;
7. symlink/path escape;
8. a sibling without AGENTS, hooks, PLAN, or contract;
9. different member framework targets/remotes;
10. deterministic member ordering.

### Required assertions

- discovery never grants mutation authority;
- `.code-workspace` evidence remains advisory;
- each repo-local result retains its own status and evidence;
- coordinator success does not turn sibling missing surfaces green;
- aggregate output cannot report `all_members_verified` while any member is
  undeclared, unchecked, blocked, or failed;
- no product, hook, AGENTS, contract, PLAN, memory, commit, or push mutation
  occurs in the report-only tranche;
- output includes a clear cannot-claim list;
- raw JSON/stdout evidence is durably retained when later used to support a
  completion claim.

### Real-case validation

After fixture tests and independent review, run the report-only audit against
isolated clones of the three eToken repositories. Do not modify or push the
original consumer repositories. Compare the output with the tracked
`E2-CONSUMER-03` packet and preserve any disagreement rather than rewriting the
evidence packet to match the tool.

## Affected Surfaces

The original review-only slice added only this document. The subsequently
approved first implementation tranche added:

- `governance_tools/composite_workspace_census.py`;
- `tests/test_composite_workspace_census.py`;

Possible later, separately reviewed surfaces remain:

- adoption-role documentation;
- optionally, a later separately reviewed declaration schema and validator;
- optionally, a later workspace orchestrator and aggregate reporting contract.

The current F-7 implementation, updater, runtime, schemas, and consumer repos
are not affected by this slice.

## Claim Ceiling

This specification may claim:

- current F-7 behavior is repo-root scoped;
- eToken demonstrates one composite operating model and an observed sibling
  coverage gap;
- IDE workspace membership is insufficient governance authority;
- bilateral opt-in plus per-repo execution is the recommended target model;
- the report-only census tranche exists at `6e4e5439` and was exercised against
  isolated eToken repositories without modifying the originals.

This specification cannot claim:

- composite workspace governance exists;
- bilateral membership artifacts or schemas exist;
- F-7 supports or updates sibling repositories;
- the census grants membership or governance authority;
- eToken server/client are governed members;
- workspace-wide adoption, hooks, runtime, validator, memory, CI, commit, or
  push enforcement;
- the full bilateral authority architecture has been behaviorally validated;
- the census reduced operator effort or improved comprehension in normal use;
- one eToken case proves general fleet demand or effectiveness.

## First Implementation Tranche - Completed

The approved first tranche was completed by `6e4e5439`. F-7 was not expanded.

Implemented tranche:

> Add a report-only composite workspace census/audit that accepts an explicit
> coordinator root plus an explicit candidate-root allowlist, resolves each Git
> identity, reports current repo-local governance/readiness state, and labels
> every member `unratified` until a separately approved bilateral authority
> artifact exists.

Constraints for that tranche:

- no automatic `.code-workspace` authority;
- no sibling writes;
- no F-7 invocation or status changes;
- no new membership schema yet;
- deterministic JSON and human output;
- explicit evidence and cannot-claim fields;
- eToken isolated clones as the only real-case validation after fixtures pass.

Only after G4 usage observation demonstrates that the census is useful in
normal work, and the owner separately approves a bilateral declaration model,
should a schema/validator slice be proposed. A workspace orchestrator should be
considered after that. The repo-local F-7 core remains unchanged unless
independent evidence shows that orchestration cannot safely live above it.

## Review Decision and Disposition

1. Repo sovereignty outranks workspace convenience: **accepted**.
2. `.code-workspace` is discovery-only evidence: **accepted**.
3. Bilateral opt-in is the minimum authority for future sibling writes:
   **accepted as a design boundary; not implemented**.
4. `full_update_completed` remains repo-local; any future aggregate workspace
   status must remain distinct: **accepted**.
5. The report-only census/audit was approved and completed at `6e4e5439`;
   F-7 expansion remains deferred.
