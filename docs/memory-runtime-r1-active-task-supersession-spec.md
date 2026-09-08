# Memory Runtime R1 Active-Task Supersession Technical Specification

Status: **NON-AUTHORITATIVE TECHNICAL SPECIFICATION CANDIDATE**

This document guides one future implementation slice. It is not registered in
`governance/AUTHORITY.md`, does not create policy, and does not authorize RAG or
any implementation beyond a separately reviewed R1 tranche.

## Problem

R0 proves that one caller-authorized `active_task` projection can be written,
resolved, read, verified, and rendered exactly. It deliberately fails closed
when the same record identity is paired with different projection content.

R0 does not answer what happens when an active task legitimately changes. A new
version must not silently overwrite the old bytes, inherit an authority decision
for different content, or leave retrieval guessing which version is current.

R1 therefore addresses one question only:

> How can one new `active_task` record explicitly supersede one previous record
> while preserving both versions and rendering only the unique current version?

This specification is an owner-authorized product-capability design slice. Its
evidence basis is the observed repository limitation described below: current
code has no persisted supersession relation or current-version selector. It does
not claim that an unsafe Runtime failure has already occurred, and it does not
add a governance surface. The repository's failure-driven governance rule would
apply only to a separately proposed governance control, not to this explicitly
non-authoritative working specification.

## Current Repository Truth

At immutable base `34586db22abc9c9c816012ac6a1fe90d93050236`:

- `memory_pipeline.active_task_round_trip.round_trip_active_task()` implements
  the bounded R0 write-resolve-read-verify-render path.
- `governance_tools.memory_record.build_record_identity()` remains the existing
  writer-owned same-day deduplication identity. R1 must not redefine it.
- `render_active_task_projection()` owns active-task summary normalization and
  canonical projection bytes.
- `append_projection_with_outcome()` can append a projection whose record
  identity is new, but the active-task projection grammar does not persist a
  supersession relationship.
- `memory_pipeline.memory_layout.resolve_memory_file()` resolves the logical
  `active_task` surface. R1 needs no new logical surface or alias.
- `governance_tools.memory_identity.classify_record_attempt()` provides a pure
  fail-closed rule for same-event correction. Its event/record v2 identities
  describe session-closeout records, not an `active_task` lineage, and it has no
  filesystem writer. R1 may reuse the invariant shape, not conflate the identity
  classes or claim runtime integration.
- R0 bounded qualification passed on the base above with no known reproducible
  unresolved P0/P1. R0 is frozen unless a new reproducible failure is observed.

No current repository code persists an active-task supersession edge or selects
the current member of an active-task version lineage.

## Target Outcome

For exactly two caller-admitted, caller-authorized active-task records with
distinct canonical record identities:

```text
v1 projection --explicit append-only relation--> v2 projection
```

R1 must establish all of the following from one bounded filesystem snapshot:

1. both projection versions remain present and byte-verifiable;
2. exactly one valid relation states that v2 supersedes v1;
3. v1 is retained as history and contributes zero current-context records;
4. v2 is the unique current record and contributes exactly one canonical LF
   context record; and
5. retrying the same v2 plus the same relation is idempotent.

Before supersession, exactly one verified v1 with no admitted v2 projection and
no relation involving either admitted endpoint remains the R0 base current. Once
the admitted v2 projection exists, only the unique exact v1-to-v2 relation can
establish a current record. Any partial or ambiguous supersession state has no
current record and produces zero context.

The relation does not make content authoritative by itself. One externally
authorized supersession decision must already exist and must bind the decision,
logical surface, both endpoint identities, and both exact projection digests as
defined below.

## Minimal Supersession Model

### Version References

R1 does not introduce a replacement identity algorithm. One exact active-task
version is referenced by the pair:

```text
(record_identity, projection_sha256)
```

- `record_identity` is the existing value produced by
  `governance_tools.memory_record.build_record_identity()`.
- `projection_sha256` is lowercase SHA-256 of the exact strict-UTF-8 bytes
  returned by `render_active_task_projection()` for that record and summary.

The two records must have distinct record identities. Same identity with
different content remains an R0 content mismatch and fails closed; R1 must not
reinterpret it as supersession.

### Supersession Authorization

R1 consumes exactly one caller-admitted semantic authorization observation; it
does not decide who may authorize supersession. The observation is usable only
when all of these semantic predicates hold:

- the decision is exactly `supersede`;
- the logical name is exactly `active_task` and the question class is exactly
  `current_progress`;
- the predecessor reference equals the exact v1 `(record_identity,
  projection_sha256)` pair;
- the successor reference equals the exact v2 `(record_identity,
  projection_sha256)` pair;
- the authority source is a current human instruction or approved change under
  the existing M-1 reader rules;
- the M-1 resolution state is `resolved`, including current projection status,
  authority-qualified reviewed status, traceable latest-evidence and latest-
  transition coverage, no unreconciled later qualified change, and a coverage
  boundary determinable without semantic guessing; and
- one traceable source anchor identifies the external authorization evidence.

R1 validates equality and the admitted resolved disposition; it does not
re-perform reviewer qualification, infer missing coverage, or create authority.
An admitted `reviewer_required`, `disputed`, `insufficient_authority`, or
`unassessable` disposition remains non-resolved and produces zero context. A
missing, malformed, non-string, unsupported, multiply supplied, unexpectedly
different, or endpoint-mismatched semantic value fails closed with `ValueError`
before either writer. Legacy observations that do not bind the exact decision
and both endpoint pairs may remain historical data but cannot authorize R1.

These are semantic requirements, not a frozen mapping, JSON, dataclass, CLI, or
public Runtime result schema. The implementation tranche may choose a private
transport shape, but it must prove every predicate above and reject ambiguous
input rather than silently supplying defaults.

### Persisted Relation

The implementation tranche may add one public renderer/writer for a relation
line on the existing logical `active_task` surface. It must not change the
existing projection renderer, identity builder, alias table, or R0 grammar.

The persisted line is one ASCII-compatible Markdown comment with canonical LF
output and four lowercase SHA-256 fields in this order:

```text
<!-- memory_runtime_supersession:active-task-summary:<v1_record_identity>:<v1_projection_sha256>:<v2_record_identity>:<v2_projection_sha256> -->
```

LF and CRLF are the only accepted persisted framing. A relation-looking line
that is malformed, truncated, self-referential, contains an unsupported line
boundary, or carries non-lowercase/non-SHA-256 fields fails closed.

The namespace intentionally differs from `memory_record_projection:` so the
frozen R0 parser continues to ignore a structurally separate relation line as
ordinary non-projection data.

### Current Selection

The first R1 slice supports one admitted base record and exactly one admitted
two-node lineage with one edge:

```text
v1 -> v2
```

Every bounded snapshot has exactly one of these dispositions:

```text
BASE_CURRENT
  exactly one verified v1
  + no admitted v2 projection
  + no relation involving v1 or v2
  -> v1 is current and renders exactly once

SUPERSEDED_CURRENT
  exactly one verified v1
  + exactly one verified v2
  + exactly one authorized v1-to-v2 relation
  + no other relation involving v1 or v2
  -> v2 is current and renders exactly once; v1 renders zero times

INVALID_OR_AMBIGUOUS
  every other admitted or relation-looking state
  -> no current record, zero context, fail closed
```

For `SUPERSEDED_CURRENT`, after validating the full snapshot:

- v1 must exist exactly once with the authorized v1 digest;
- v2 must exist exactly once with the authorized v2 digest;
- the exact v1-to-v2 relation must exist exactly once;
- no other relation may name v1 or v2 as an endpoint;
- v1 must have one outgoing edge and no incoming edge;
- v2 must have one incoming edge and no outgoing edge; and
- current selection is the unique sink, v2.

Missing endpoints, duplicate relations, a fork, a merge, a cycle, a self-edge,
reversed endpoints, or any additional edge involving the admitted lineage fails
closed with zero context. Longer chains are deferred rather than guessed.

An admitted v2 projection without the unique exact edge is an incomplete
supersession state, not a reason to continue rendering v1. It is
`INVALID_OR_AMBIGUOUS` and fails closed with zero context. R1 does not repair or
complete that partial state during retrieval.

Structurally valid projections and relations that are disconnected from the
admitted v1/v2 lineage may remain as historical non-target data. Malformed
supersession-looking data cannot be safely excluded and fails closed.

### Mutation Boundary

The future implementation must capture the pre-write surface bytes once as a
local immutable snapshot. Before either writer is invoked, it must validate the
entire admitted projection and relation surface from that snapshot, including:

- the same absolute/canonical root boundary already established by R0;
- accepted LF/CRLF framing and exact grammar for every projection-looking or
  supersession-looking line;
- distinct canonical v1/v2 record identities;
- exact v1/v2 public-renderer bytes and digests;
- one caller-admitted supersession authorization binding all four endpoint
  fields;
- endpoint presence, relation cardinality, and every relation involving v1 or
  v2; and
- classification as either `BASE_CURRENT` or the exact already-complete
  `SUPERSEDED_CURRENT` requested by the caller, or as the one narrowly
  recoverable partial state defined below.

`BASE_CURRENT` permits the bounded mutation below. The exact already-complete
`SUPERSEDED_CURRENT` is an idempotent success with zero writer invocations.
The only recoverable partial state contains exactly one verified v1, exactly one
verified v2, no relation involving either endpoint, and exactly one currently
M-1-resolved supersession authorization that satisfies the semantic predicates
above and binds those persisted endpoint pairs exactly. It has no current record
and produces zero context, but an explicit currently authorized retry may invoke
only the relation writer to append the missing exact edge. The projection writer
must not run during this retry. Any malformed line, endpoint mismatch, digest
mismatch, duplicate, conflicting relation, non-resolved authorization, or
authorization that does not bind those exact endpoints makes the state
non-recoverable.

The failed first invocation does not persist an authorization-observation
identity, so R1 cannot and does not claim that the retry observation is
byte-identical to the first one. Recovery authority is established from the
single current M-1-resolved observation supplied to the retry, not by guessing
or reconstructing an unpersisted prior observation.
`INVALID_OR_AMBIGUOUS`, or any root, framing, grammar, identity, digest,
authority, endpoint, or cardinality failure discoverable from the pre-write
snapshot, raises `ValueError` before either writer is invoked and leaves the
persisted bytes unchanged.

The smallest safe write order is:

1. append or confirm the v2 projection through the existing canonical writer;
2. append or confirm the exact supersession relation through the new bounded
   relation writer; and
3. read one final snapshot and verify the complete two-node lineage before
   rendering v2.

If step 1 succeeds and step 2 fails for a reason not discoverable from the
validated pre-write snapshot, the unmatched v2 projection is retained with no
current record and zero context. It can progress only through the explicit
relation-only retry above after revalidating one fresh immutable snapshot and
one currently M-1-resolved authorization bound to the persisted endpoint pairs.
A relation whose v2 endpoint is absent also fails closed. R1 does not delete,
roll back, automatically repair, or claim general transactional recovery.

## Scope

- logical `active_task` only;
- exactly two distinct canonical record identities;
- exactly one explicit append-only supersession edge;
- exact endpoint content binding through public-renderer SHA-256 digests;
- deterministic unique-current selection after complete snapshot validation;
- v1 historical retention and zero v1 current-context rendering; and
- idempotent retry of the exact v2 projection and exact relation; and
- one explicit currently authorized, relation-only retry after v2 succeeded and
  relation append failed.

## Non-Goals

- no Runtime implementation in this specification tranche;
- no change to `build_record_identity()` or its field set;
- no change to `memory_layout.py`, aliases, or logical surfaces;
- no mutation or deletion of v1;
- no chain longer than one edge, fork, merge, cycle repair, or conflict
  resolution platform;
- no automatic decision that two records describe the same logical task;
- no authority-policy creation or automatic supersession approval;
- no result transport schema or public Runtime API freeze;
- no atomic multi-write transaction, rollback, general crash recovery, locking,
  or concurrency qualification beyond the one exact relation-only retry;
- no expiry, deletion, compaction, migration, or historical backfill;
- no semantic retrieval, embeddings, ranking, RAG, LLM call, or context-budget
  policy; and
- no hook, CI, gate, blocker, enforcement, Gate 3, or governance-authority
  change.

## Affected Surfaces

This specification slice changes only:

- `docs/memory-runtime-r1-active-task-supersession-spec.md`; and
- the adjacent R1 candidate entry in `PLAN.md`.

A separately authorized implementation is expected to consider:

- a new bounded relation renderer/writer in
  `governance_tools.memory_record` without changing existing public semantics;
- a new `memory_pipeline` R1 module for snapshot validation and current
  selection;
- focused tests in a new R1 test file; and
- a short `memory_pipeline/README.md` entry.

Those implementation surfaces are provisional, not authorized by this spec.

## Boundary And API Considerations

- Existing R0 public behavior and regression coverage remain unchanged.
- The new relation line is persisted representation, not a Runtime response
  object. R1 does not define JSON, CLI, dataclass, or API transport shape.
- R1 must not import private writer normalization helpers or copy the writer's
  record-identity field list.
- A caller-admitted supersession authorization is evidence supplied to R1; R1
  validates its exact semantic disposition and binding but does not decide who
  may issue it or redefine M-1 qualification.
- Selection authority and relevance ranking are separate. Supersession decides
  which versions are eligible as current; a future retriever may rank only
  records that have already passed that eligibility boundary.

## RAG Reference Boundary

The RAG work in `Gavin0099/uvm-agent-lab` was inspected at committed
`origin/main` `dcb2d02b2dc18d2c102cfc959eb91aa597ef1380` without reading its dirty
working-tree copy.

Transferable patterns for a future, separately authorized RAG slice are:

- `GovernedChunk` keeps content identity and source provenance attached to each
  retrieved unit;
- corpus/source scope is a hard eligibility filter before scoring, not a
  reranking hint;
- deterministic BM25 sorting uses score and then stable chunk identity;
- empty or out-of-scope evidence produces abstention instead of fabricated
  support;
- the model receives only bounded retrieved evidence; and
- citations are reconstructed from retrieved governed records rather than
  generated by the model.

R1 may borrow only the first architectural separation:

```text
supersession/current-state eligibility -> later retrieval/ranking
```

It must not copy USB-specific scopes, BM25 parameters, corpus-lock schema,
question classifiers, response objects, prompts, local-model integration, or
retrieval metrics. The `uvm-agent-lab` code is reference evidence, not authority
for this repository.

## Failure Paths And Risk Points

- Reusing the same record identity for changed content would replay authority
  across payloads; fail closed instead.
- Persisting only endpoint identities would allow a relation to be replayed
  against changed bytes; bind both endpoint digests.
- Writing the relation before v2 could make a missing successor look current;
  write/confirm v2 first.
- Treating newest file order or timestamp as current would bypass explicit
  supersession; after the v1-only base case, current selection must come only
  from the validated edge.
- Continuing to render v1 after the admitted v2 projection exists without its
  exact edge would hide an incomplete mutation; emit zero context instead.
- Detecting malformed or conflicting persisted relations only after appending
  v2 would mutate before failure; validate the complete pre-write snapshot
  before either writer invocation.
- Rejecting every exact v1-plus-v2 partial state would make one ordinary relation
  writer failure permanently unrecoverable; permit only a relation-only retry
  carrying one currently M-1-resolved authorization bound to the persisted
  endpoint pairs, while continuing to render zero context until it succeeds.
- Ignoring malformed relation-looking lines would create a fail-open parser
  bypass.
- Reusing `memory_identity.py` identities as active-task identities would merge
  different claim classes.
- Calling semantic ranking before current-state filtering could retrieve v1;
  future RAG must consume only R1-eligible current records.

## Evidence Plan

The future implementation must minimally cover:

1. v1 only remains current before supersession;
2. v1 plus authorized v2 and one exact relation renders v2 exactly once;
3. v1 remains byte-present and contributes zero current context;
4. exact retry of an already-complete supersession invokes neither writer and
   adds neither a projection nor a relation duplicate;
5. same identity plus changed content fails closed under the R0 rule;
6. mismatched endpoint identity or digest fails before either writer;
7. missing v1, missing v2, reversed edge, self-edge, duplicate edge, fork,
   merge, cycle, and additional lineage edge fail closed;
8. malformed or conflicting pre-write relation state fails with both writer
   call counts at zero and persisted bytes unchanged, even when a valid edge is
   also present;
9. a v2 projection left without a relation gives neither v1 nor v2 current
   status and renders zero context;
10. exactly one currently M-1-resolved authorization bound to the persisted
    endpoint pairs may recover that state by invoking only the relation writer,
    after which v2 renders exactly once;
11. a non-resolved, multiply supplied, endpoint-mismatched, or malformed current
    authorization, an identity/digest mismatch, malformed line, or conflicting
    relation makes the partial state non-recoverable with both writer call
    counts at zero and bytes unchanged;
12. resolved authorization binds `supersede`, `current_progress`, `active_task`,
    both exact endpoint pairs, M-1 resolved eligibility, and a source anchor;
13. non-resolved M-1 dispositions produce zero context, while malformed,
    ambiguous, legacy-unbound, or multiply supplied authorization fails closed;
14. a relation whose v2 projection is absent fails closed;
15. unrelated structurally valid historical lineages do not affect selection;
16. root validation fails before either writer is invoked; and
17. unchanged inputs and filesystem snapshot produce the same selected identity
    and canonical context bytes.

Validation should run the new R1 focused tests together with the existing R0
and canonical-writer suites. Full RAG, crash, performance, and adversarial
filesystem matrices are not part of this tranche.

## Claim Ceiling

This candidate specifies one two-version, one-edge, caller-authorized
`active_task` supersession, one exact relation-only retry, and
unique-current-selection behavior. It does not claim the behavior exists, is
enforced, is generally crash-safe, is production-qualified, or generalizes to
longer lineages or other memory surfaces. It does not claim RAG, semantic
retrieval, deletion, expiry, concurrency safety, or authority policy.

## Implementation Tranche Recommendation

After exact-head review accepts this specification with no unresolved P0/P1,
the next separately authorized tranche should implement only:

```text
append/confirm distinct v2 projection
-> append/confirm one exact v1-to-v2 relation
-> on an exactly bound, currently authorized partial retry, append only the missing relation
-> validate one two-node snapshot
-> render v2 once and v1 zero times
```

Stop after that vertical slice. Longer chains and RAG require their own observed
need, specification, authorization, and evidence.
