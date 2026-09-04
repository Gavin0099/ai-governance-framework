# Memory Runtime NSI-N0 Persisted Session Reader Technical Specification

Status: implementation-driving technical specification candidate; not a
governance authority and not an implementation.

## Problem

R0 can verify one caller-admitted canonical `active_task` record, and R1 can
select the current member of one caller-admitted two-version supersession edge.
Neither primitive discovers its own inputs. A fresh Agent session still has to
receive the record, summary, and authority observation from chat or another
caller before it can invoke them.

That prevents a genuine natural-session test. Supplying an out-of-band handoff
packet would only prove that a human can reconstruct the inputs, not that a new
session can recover current work from persisted repository state.

NSI-N0 answers one question:

> How can one completely new session deterministically reconstruct the complete
> bounded R0/R1 `active_task` input from persisted repository state, without
> prior chat history or semantic guessing?

## Current Repository Truth

The following statements were observed at merged main
`73cf59bdb0f71ca155093715e6b6b8ee00bc7062`:

- `memory_pipeline.active_task_round_trip.round_trip_active_task()` requires a
  caller-supplied record, summary, and authority observation.
- `memory_pipeline.active_task_supersession.select_current_active_task()` and
  `supersede_active_task()` require caller-supplied predecessor inputs and, for
  the superseded shape, successor inputs and a content-bound authority
  observation.
- Repository callers of those entrypoints are limited to their implementation,
  technical specifications, and tests. No natural session-start caller exists.
- `governance_tools.memory_record.render_active_task_projection()` persists one
  summary plus one canonical record identity on logical `01_active_task`.
- `render_review_log_projection()` persists a canonical checkpoint on logical
  `04_review_log`: writer, session id, identity, commit binding, record text,
  test boundary, next action, PLAN reconciliation, and memory binding. Together
  with the writer-owned fixed record type and format version, that checkpoint
  can reconstruct a candidate canonical record and verify it by re-rendering
  exact bytes and recomputing `build_record_identity()`.
- Logical `01_active_task` and `04_review_log` are already resolved through
  `memory_pipeline.memory_layout`; a session reader must not hard-code their
  consumer filenames.
- M-1 classifies daily records as event/provenance history, PLAN plus an approved
  change as work ordering, `01` as a reviewed current-state projection, and
  `04` as append-only review history. Canonical storage alone does not create
  current authority.
- A repository search found no persisted instance of the R0 fields
  `requested_record_identity`, `resolved_record_identity`, and
  `authorized_projection_sha256`, or the R1 predecessor/successor identity and
  digest authority binding. Those fields currently exist only in technical
  specifications and executable tests.
- The current `memory/01_active_task.md` contains four historical Gate 3-era
  projections and no `memory_runtime_supersession:` relation. It contains no R1
  milestone projection from which this pilot could start.

The existing surfaces are therefore sufficient to reconstruct a record and its
summary, but not sufficient to reconstruct the authority observation required
by R0/R1. Treating PLAN prose, a daily `next_step`, a Git commit, or a canonical
writer marker as implicit authority would violate M-1.

## Target Outcome

One persisted-session reader responsibility is defined for logical
`active_task`. Given only a caller-admitted canonical repository root, it:

1. snapshots the canonical Git worktree identity, then resolves and snapshots
   the logical `01_active_task` and `04_review_log` surfaces;
2. reconstructs the exact canonical record or bounded v1/v2 records;
3. joins each record to the exact summary and projection digest by record
   identity;
4. obtains exactly one matching persisted M-1 authority attachment from logical
   `04_review_log`;
5. validates the attachment's exact endpoint, eligibility, and source-anchor
   bindings from the same repository snapshot, without treating mere anchor
   existence as proof of authority; and
6. invokes the existing R0/R1 selector with reconstructed inputs, returning
   context only when that selector establishes one current record.

The reader does not receive a record, summary, target identity, or authority
observation from chat. The only caller input is the canonical project root and
the bounded logical-name request.

## Scope

- one repository worktree root admitted by the caller;
- logical `active_task` only;
- the existing R0 v1-only shape and R1 two-version, one-edge shape only;
- logical `01_active_task` as the summary, projection-identity, and
  supersession-relation source;
- logical `04_review_log` as the canonical-record-checkpoint and persisted
  authority-attachment source;
- exact record-identity and public-renderer digest joins;
- committed approved-change authority anchors that can be checked from the same
  repository state;
- preserved M-1 non-resolved outcomes with zero context; and
- one future minimal reader/adapter implementation tranche.

## Non-Goals

- no implementation in NSI-N0;
- no Runtime, writer, hook, CI, gate, blocker, or enforcement change;
- no new logical memory surface, top-level manifest, database, or formal schema
  file;
- no use of current chat, prior task context, or a human-supplied handoff packet
  as reconstruction input;
- no directory-wide semantic scan, timestamp/latest-text selection, fuzzy join,
  or authority inference;
- no modification of `build_record_identity()`, R0/R1 semantics, or
  `memory_layout.py`;
- no natural Session A/B pilot, v1 bootstrap, migration, or historical rewrite;
- no longer lineage, graph engine, concurrency, rollback, crash atomicity,
  deletion, expiry, semantic retrieval, or RAG; and
- no claim that an approved change grants authority beyond its recorded scope.

## Persisted Source Model

### Summary and supersession state: logical `01_active_task`

The reader reuses the exact projection and relation grammars already accepted by
R0/R1. It may tolerate unrelated well-formed historical projections and
relations, but malformed structured lines fail closed.

The active-task snapshot supplies:

- projection summary bytes;
- canonical record identity;
- the SHA-256 input through the public active-task renderer bytes; and
- for the R1 shape, the predecessor/successor identity and digest pairs carried
  by the one exact supersession relation.

### Canonical record: logical `04_review_log`

For every admitted active-task identity, the reader requires exactly one
matching canonical checkpoint. It reconstructs the candidate record using only
checkpoint fields plus writer-owned fixed constants, then requires all of the
following:

- recomputed `build_record_identity(record)` equals the joined identity;
- `render_review_log_projection(record)` reproduces the exact checkpoint bytes;
- `render_active_task_projection(record, summary=summary)` reproduces the exact
  active-task projection bytes; and
- the SHA-256 of those exact active-task bytes equals the bound projection
  digest.

Daily memory remains event history and is not scanned to select current state.
It may corroborate an anchor during human review, but it is not an NSI-N0 join
source.

### Authority: one minimal attachment on logical `04_review_log`

Current merged surfaces do not persist the content-bound M-1 observation needed
by R0/R1. The next implementation tranche therefore needs one minimal
append-only authority attachment on the existing logical `04_review_log`
surface. This is an attachment to the existing review surface, not a second
memory database or a new logical surface.

The attachment must carry the already-defined M-1 vocabulary and the exact
content binding needed by the selected bounded shape. It is a persisted record
of an already-admitted M-1 decision; neither its writer nor its later reader may
create authority merely by storing or finding it:

- for R0 base current: query class, logical name, requested/resolved record
  identity, projection digest, resolution state, projection status, review
  status, reviewer-authority state, anchor state, latest-transition coverage,
  later-change state, coverage-boundary state, authority source, and source
  anchor;
- for R1 superseded current: decision, query class, logical name,
  predecessor/successor identities and projection digests, resolution state,
  eligibility state, authority source, and source anchor; and
- for a non-resolved observation: the same requested endpoint identity and
  digest binding for its bounded R0 or R1 shape, the applicable M-1 predicate
  states, and exactly one of `reviewer_required`, `disputed`,
  `insufficient_authority`, or `unassessable`.

NSI-N0 does not add a schema file or freeze a public result API. N1 must choose
the smallest exact, strict-UTF-8, line-framed representation on `04_review_log`
that can carry those existing fields. The representation must be independently
parseable, reject unknown or duplicate required fields, and be reproduced
byte-for-byte in tests before it is used. Encoding design remains part of N1's
reviewed implementation diff, not an authority created by this document.

For cross-session reconstruction, an unrecorded `current_human_instruction` is
not replayable. A resolved attachment must have been persisted by a separately
authorized Session A action and must bind the exact approved-change source it
records. Session B verifies that the explicit anchor resolves to the pinned
repository evidence and that all content and eligibility bindings still match;
it does not independently prove the human's legal identity, and it does not
infer approval from commit existence, PLAN ordering, writer identity, or memory
presence. If the source cannot be replayed within that claim ceiling, the
attachment cannot resolve current state.

## Deterministic Join And Selection

The reader uses this order:

1. Validate the canonical project root and Git worktree marker using the R0/R1
   root boundary, and snapshot the repository HEAD used for source-anchor
   checks exactly once.
2. Resolve logical `01_active_task` and `04_review_log` once through
   `memory_layout`; snapshot each resolved path, existence state, and exact bytes
   once.
3. Strict-decode and independently parse both snapshots. Subsequent decisions
   use only those immutable snapshots.
4. Parse all well-formed authority attachments. Structurally valid unrelated
   history is allowed.
5. Select attachments whose explicit source anchors resolve to their exact
   pinned repository evidence and whose recorded M-1 eligibility predicates are
   complete. Anchor existence alone is insufficient. Do not use timestamp,
   line order, filename order, or newest text.
6. Join each selected attachment to exactly one canonical checkpoint and exactly
   one exact active-task projection per bound identity.
7. Recompute record identity, public-renderer bytes, and projection digest.
8. Require exactly one supported bounded disposition:
   - one v1 record plus one resolved base attachment and no admitted
     supersession relation; or
   - one v1, one v2, one exact v1-to-v2 relation, and one resolved supersession
     attachment bound to both endpoints.
9. Construct the existing R0/R1 caller input from the verified snapshots and
   call the existing selector.
10. Emit only the selector's canonical current context. v1 contributes zero
    context after a valid supersession.

The reader does not accept a caller-selected target identity. Exactly-one
eligibility must emerge from persisted content-bound authority attachments. Two
eligible base attachments, two competing edge attachments, or any unsupported
shape is ambiguous and fails closed.

## Boundary And API Considerations

NSI-N0 defines one reader responsibility, not a full session harness. N1 may
expose one internal function or CLI entrypoint, but its caller may provide only
the canonical project root and logical `active_task` request. It must not expose
record, summary, identity, digest, or authority override parameters that recreate
the current caller-driven gap.

The semantic outcomes remain:

- resolved base current with one canonical context;
- resolved superseded current with one canonical v2 context;
- one preserved M-1 non-resolved disposition with zero context; or
- structural/identity/content failure through `ValueError` with zero context.

The transport object, JSON shape, exit-code mapping, and public API stability are
deferred. No serialized result-byte promise is made here.

## Failure Paths And Risk Points

- **Missing checkpoint:** an active projection has no exact `04` canonical
  checkpoint; fail closed with zero context.
- **Duplicate checkpoint:** more than one checkpoint claims the joined identity;
  fail closed rather than selecting by order.
- **Identity mismatch:** reconstructed fields do not reproduce the marker
  identity; fail closed.
- **Content mismatch:** public-renderer bytes or projection digest differ; fail
  closed.
- **Missing authority:** structurally valid content without a matching persisted
  authority attachment cannot resolve current state; return an appropriate M-1
  non-resolved disposition with zero context.
- **Duplicate or conflicting authority:** more than one attachment is eligible
  for the same base or edge, or attachments select competing current records;
  fail closed as ambiguity.
- **Stale authority:** the explicit source anchor does not cover the pinned
  approved change or a later recorded substantive transition remains
  unreconciled; preserve `reviewer_required`, `disputed`,
  `insufficient_authority`, or `unassessable` with zero context.
- **Malformed structured data:** invalid UTF-8, framing, marker, attachment, or
  required-field shape raises `ValueError` before context rendering.
- **Partial R1 state:** v1 plus v2 without the exact relation produces zero
  context. The session reader never performs relation-only recovery.
- **Implicit authority:** PLAN text, daily `next_step`, Git ancestry, canonical
  writer identity, or file presence alone must never be promoted into a resolved
  attachment.
- **Unreplayable authority:** an attachment that merely says an owner or reviewer
  approved something, without an exact persisted source binding, cannot resolve
  current state. NSI-N0 does not claim cryptographic or legal identity proof.
- **Second database:** adding a new session-state JSON/manifest or copying full
  records into another surface is outside the recommended N1 tranche.

## P2 Disposition

The missing R1 milestone projection is reclassified from a non-blocking delivery
finding to `OBSERVED_NSI_BLOCKER / REOPENED`. A real Session A cannot start from
a qualified current v1 until the later bootstrap step creates one canonical
record, matching `01` projection, `04` checkpoint, and persisted authority
attachment through an owner-authorized path.

The following remain carried forward and do not enter NSI-N0:

- daily-only versus multi-surface record-identity consistency; and
- the PLAN header's unchanged `2026-09-02` freshness date.

## Claim Ceiling

This specification may claim only that current merged repository evidence is
insufficient for chat-free authority reconstruction, and that one bounded
reader can join existing logical `01` and `04` data plus one minimal persisted
authority attachment on `04`.

It does not claim that the reader, attachment writer, session integration,
bootstrap, qualification, or two-session pilot exists. It does not establish
authority, repair current memory, make the existing Gate 3 projection current,
or authorize RAG or later lifecycle work.

## Evidence Plan

N1 focused tests must demonstrate:

1. one canonical v1 checkpoint, projection, and resolved base attachment joins
   to the exact R0 input and returns v1 once;
2. one canonical v1/v2 pair, one exact relation, and one resolved supersession
   attachment joins to the exact R1 input and returns only v2;
3. unrelated well-formed historical checkpoints, projections, relations, and
   attachments do not change the target result;
4. missing or duplicate checkpoint, projection, or authority attachment yields
   zero context and the specified non-resolved or `ValueError` outcome;
5. identity, digest, public-renderer, endpoint, M-1 eligibility, or source-anchor
   mismatch fails closed;
6. stale but structurally valid authority preserves the correct M-1
   non-resolved state with zero context;
7. malformed UTF-8, framing, marker, or attachment fails closed;
8. partial v1-plus-v2 state yields zero context and performs no repair;
9. dependency calls, resolver outputs, paths, and bytes are snapshotted once and
   not re-read during selection;
10. no record, summary, identity, digest, or authority input can be supplied by
    the session caller; and
11. adjacent R0, R1, memory-layout, and canonical-writer tests remain green.

Spec-only validation is limited to scope census, link/token consistency,
`git diff --check`, PLAN freshness, and independent two-file technical review.
Passing those checks proves specification coherence only, not reader behavior.

## Implementation Tranche Recommendation

After this exact specification is accepted, authorize one NSI-N1 reader/adapter
tranche that:

- adds the smallest exact authority-attachment grammar to logical
  `04_review_log`;
- appends it only through a bounded canonical helper;
- parses existing canonical checkpoints plus the new attachment;
- joins logical `01` and `04` snapshots into existing R0/R1 selector inputs; and
- provides one internal persisted-session reader entrypoint.

NSI-N1 must not bootstrap current v1 or run the Session A/B pilot. Those actions
remain separate because they mutate canonical memory and test a later live
integration boundary.
