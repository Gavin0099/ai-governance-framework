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
  summary plus one canonical record identity on logical `active_task`, whose
  current canonical filename is `01_active_task.md`.
- `render_review_log_projection()` persists a canonical checkpoint on logical
  `review_log`, whose current canonical filename is `04_review_log.md`: writer,
  session id, identity, commit binding, record text,
  test boundary, next action, PLAN reconciliation, and memory binding. Together
  with the writer-owned fixed record type and format version, that checkpoint
  can reconstruct a candidate canonical record and verify it by re-rendering
  exact bytes and recomputing `build_record_identity()`.
- The `active_task` and `review_log` resolver keys are already declared by
  `memory_pipeline.memory_layout`; a session reader must use those exact keys
  and must not hard-code their consumer filenames.
- M-1 classifies daily records as event/provenance history, PLAN plus an approved
  change as work ordering, `01` as a reviewed current-state projection, and
  `04` as append-only review history. Canonical storage alone does not create
  current authority.
- A repository search found no persisted instance of the R0 fields
  `requested_record_identity`, `resolved_record_identity`, and
  `authorized_projection_sha256`, or the R1 predecessor/successor identity and
  digest authority binding. Those fields currently exist only in technical
  specifications and executable tests.
- No merged persisted artifact provides a commit-stable, independently
  comparable identity for the current qualified human-instruction state. A
  pre-write repository HEAD changes when the attachment is committed, while the
  resulting HEAD still cannot prove that no later unpersisted qualified human
  instruction exists.
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
   logical `active_task` and `review_log` through `memory_layout`;
2. reconstructs the exact canonical record or bounded v1/v2 records;
3. joins each record to the exact summary and projection digest by record
   identity;
4. obtains exactly one matching persisted, previously admitted M-1 observation
   attachment from logical `review_log`;
5. reconstructs and validates the attachment fields already consumed by R0/R1,
   without treating the attachment or its anchor as independent proof of
   authority; and
6. runs the reconstructed inputs through one internal snapshot-consuming
   selection core that preserves the existing R0/R1 validation semantics,
   returning context only when that core establishes one current record.

The reader does not receive a record, summary, target identity, or authority
observation from chat. The only caller input is the canonical project root and
the bounded logical-name request.

## Scope

- one repository worktree root admitted by the caller;
- logical `active_task` only;
- the existing R0 v1-only shape and R1 two-version, one-edge shape only;
- resolver key `active_task` as the summary, projection-identity, and
  supersession-relation source;
- resolver key `review_log` as the canonical-record-checkpoint and persisted
  observation-attachment source;
- exact record-identity and public-renderer digest joins;
- exact replay of previously admitted authority-source and source-anchor fields,
  without an independent approval-provenance claim;
- a source-compatible, independently comparable authority-freshness gate that
  downgrades unverifiable resolved replay to `unassessable`;
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
- no modification of `build_record_identity()`, R0/R1 public behavior or
  validation semantics, or `memory_layout.py`; a behavior-preserving extraction
  of an internal snapshot-consuming selection core is allowed only in N1;
- no natural Session A/B pilot, v1 bootstrap, migration, or historical rewrite;
- no instruction ledger or new instruction-freshness representation;
- no longer lineage, graph engine, concurrency, rollback, crash atomicity,
  deletion, expiry, semantic retrieval, or RAG; and
- no claim that an approved change grants authority beyond its recorded scope.

## Persisted Source Model

### Summary and supersession state: logical `active_task`

The reader reuses the exact projection and relation grammars already accepted by
R0/R1. It may tolerate unrelated well-formed historical projections and
relations, but malformed structured lines fail closed.

The active-task snapshot supplies:

- projection summary bytes;
- canonical record identity;
- the SHA-256 input through the public active-task renderer bytes; and
- for the R1 shape, the predecessor/successor identity and digest pairs carried
  by the one exact supersession relation.

### Canonical record: logical `review_log`

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

### Authority observation: one minimal attachment on logical `review_log`

Current merged surfaces do not persist the content-bound M-1 observation needed
by R0/R1. The next implementation tranche therefore needs one minimal
append-only observation attachment on the existing logical `review_log`
surface. This is an attachment to the existing review surface, not a second
memory database or a new logical surface.

The attachment must carry the already-defined M-1 vocabulary and the exact
content binding needed by the selected bounded shape. It is a persisted replay
record of an already-admitted M-1 observation; neither its writer nor its later
reader may create or independently prove authority merely by storing or finding
it:

- for R0 base current: query class, logical name, requested/resolved record
  identity, projection digest, resolution state, projection status, review
  status, reviewer-authority state, anchor state, latest-transition coverage,
  later-change state, coverage-boundary state, authority source, and source
  anchor;
- for R1 superseded current: decision, query class, logical name,
  predecessor/successor identities and projection digests, resolution state,
  projection status, review status, reviewer-authority state, anchor state,
  latest-transition coverage, later-change state, coverage-boundary state,
  authority source, and source anchor; and
- for a non-resolved observation: the same requested endpoint identity and
  digest binding for its bounded R0 or R1 shape, the applicable M-1 predicate
  states, and exactly one of `reviewer_required`, `disputed`,
  `insufficient_authority`, or `unassessable`.

A resolved attachment must also carry a source-compatible, commit-stable
freshness observation. A pre-write repository HEAD is not admissible because
committing the attachment necessarily changes it and would immediately make the
new record appear stale. Any future `approved_change` freshness representation
must survive and validate the attachment-containing commit, while also avoiding
the inference that Git state proves no later unpersisted qualified human
instruction exists. NSI-N0 does not define that representation. A
`current_human_instruction` attachment has no cross-session comparable identity
in the current repository and therefore cannot be replayed as resolved.

NSI-N0 does not add a schema file or freeze a public result API. N1 must choose
the smallest exact, strict-UTF-8, line-framed representation on `review_log`
that can carry those existing fields. The representation must be independently
parseable, reject unknown or duplicate required fields, and be reproduced
byte-for-byte in tests before it is used. Encoding design remains part of N1's
reviewed implementation diff, not an authority created by this document.

For cross-session reconstruction, an unrecorded `current_human_instruction` is
not replayable. A resolved attachment must have been persisted by a separately
authorized Session A action and must reproduce the exact authority-source,
source-anchor, and freshness fields admitted in that action. Session B verifies
endpoint, content, eligibility, field-shape, and mechanically comparable
freshness continuity before selection. A pre-write HEAD, a mismatched freshness
anchor, or an anchor that cannot validate the attachment-containing committed
state is `unassessable`. Even a future commit-stable repository anchor remains
insufficient unless source-compatible evidence mechanically establishes
freshness across qualified human instructions. The reader does not independently
prove that a human or approved change possessed authority, and it does not infer
approval from commit existence, PLAN ordering, writer identity, or memory
presence. A workflow that requires fresh authority qualification or proof must
remain non-resolved until a qualified source is admitted outside this reader.

The current repository therefore cannot mechanically preserve `resolved` for
either authority source across sessions: `current_human_instruction` has no
comparable persisted identity, and no commit-stable `approved_change` freshness
anchor both validates the attachment-containing commit and covers later
qualified instructions. NSI-N0 records this feasibility blocker. It does not
authorize the missing instruction-freshness representation or claim that N1 can
produce resolved context before such evidence is separately authorized and
available.

## Deterministic Join And Selection

The reader uses this order:

1. Validate the canonical project root and Git worktree marker using the R0/R1
   root boundary, and snapshot the repository HEAD that identifies this
   persisted observation state exactly once.
2. Resolve `active_task` and `review_log` once through `memory_layout`; snapshot
   each resolved path, existence state, and exact bytes once.
3. Strict-decode and independently parse both snapshots. Subsequent decisions
   use only those immutable snapshots.
4. Parse all well-formed observation attachments. Structurally valid unrelated
   history is allowed only where the supported bounded shape supplies a
   structural selector; the base shape does not guess that an additional
   complete projection/checkpoint join is unrelated.
5. Classify the bounded persisted shape before selecting current eligibility.
   A v1-only shape contains exactly one complete projection/checkpoint join and
   no supersession-edge candidate; only in that shape is exactly one joined
   base attachment eligible. A second complete projection/checkpoint join makes
   the base shape unsupported because persisted state cannot distinguish
   unrelated history from an incomplete v2 without semantic guessing.
   In an R1 shape, exactly one joined edge attachment controls the disposition;
   at most one well-formed base attachment bound exactly to its predecessor may
   remain as historical evidence and is excluded from current eligibility. The
   presence of any v2 or edge candidate forbids fallback to the predecessor
   base attachment, including when the edge is partial or non-resolved.
6. Select the controlling attachment whose endpoint and content bindings join
   exactly and whose recorded M-1 fields are complete for their stated
   resolution. Preserve
   authority-source and source-anchor values exactly; do not upgrade them based
   on anchor existence. Do not use timestamp, line order, filename order, or
   newest text.
7. Apply the authority-freshness gate. Preserve an attachment that is already
   non-resolved. For a resolved attachment, require source-compatible,
   independently comparable freshness evidence. Reject a pre-write HEAD as
   self-invalidating across the attachment commit. Any mismatch, inability to
   validate the attachment-containing committed state, or inability to
   establish complete freshness yields `unassessable` with zero context; a Git
   anchor alone never establishes the absence of a later unpersisted qualified
   human instruction. A persisted
   `current_human_instruction` cannot remain resolved without independently
   comparable persisted instruction-state evidence.
8. Join each selected attachment to exactly one canonical checkpoint and exactly
   one exact active-task projection per bound identity.
9. Recompute record identity, public-renderer bytes, and projection digest.
10. Require exactly one supported bounded disposition:
   - exactly one joined v1 record plus one resolved base attachment, no second
     complete projection/checkpoint join, and no supersession-edge candidate;
     or
   - one v1, one v2, one exact v1-to-v2 relation, and one resolved supersession
     attachment bound to both endpoints; or
   - exactly one joined base or edge attachment carrying one of the four M-1
     non-resolved states, in which case preserve that state with zero context.
     A non-resolved edge may describe the admitted v1/v2 partial state without
     a completed relation, but both referenced endpoint projections and
     checkpoints must still join exactly; or
   - no observation attachment after otherwise valid structural parsing, which
     deterministically returns `insufficient_authority` with zero context.
11. Construct the existing R0/R1 caller input from the verified snapshots and
   pass it to the shared internal snapshot-selection core. Do not call the
   current live-reading/writing R0/R1 entrypoints after the snapshots are taken.
12. Emit only the selector's canonical current context. v1 contributes zero
    context after a valid supersession.

The reader does not accept a caller-selected target identity. Exactly-one
eligibility must emerge from persisted content-bound observation attachments.
Two eligible base attachments or a second complete projection/checkpoint join
in a v1-only shape, more than one base attachment bound to the R1 predecessor,
two competing edge attachments, multiple
controlling non-resolved attachments for the same bounded request, or any
unsupported shape is ambiguous and fails closed. One exact predecessor base
attachment beside the controlling R1 edge is historical, not a second eligible
current attachment.

## Boundary And API Considerations

NSI-N0 defines one reader responsibility, not a full session harness. N1 may
expose one internal function or CLI entrypoint, but its caller may provide only
the canonical project root and logical `active_task` request. It must not expose
record, summary, identity, digest, or authority override parameters that recreate
the current caller-driven gap.

The existing caller-facing R0/R1 functions do not accept an immutable surface
snapshot: they resolve and read again, and the R0 round-trip path may write. N1
must therefore extract or add one pure internal selection core that accepts the
already parsed snapshot plus reconstructed inputs. Existing R0/R1 entrypoints
must delegate to or remain behaviorally equivalent to that core, with parity
tests for their accepted and fail-closed cases. This is an internal reuse
boundary, not a new public Runtime API.

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
- **Missing authority observation:** structurally valid content without a
  matching persisted observation attachment returns `insufficient_authority`
  with zero context; it does not synthesize a resolved observation.
- **Duplicate or conflicting authority:** more than one attachment is eligible
  for the same base or edge, or attachments select competing current records;
  fail closed as ambiguity.
- **Stale authority observation:** an attachment already records incomplete
  latest-evidence/transition coverage, or competing persisted observations make
  its applicability ambiguous; preserve the recorded non-resolved state when
  exactly one attachment applies, otherwise fail closed with zero context. The
  reader does not semantically discover unrecorded external transitions.
- **Freshness mismatch or uncertainty:** an originally resolved attachment with
  a pre-write HEAD, a freshness mismatch, an anchor that cannot validate the
  attachment-containing commit, or incomplete source-compatible freshness
  becomes `unassessable` with zero context. Git identity alone never upgrades or
  preserves resolved state. An attachment already carrying a non-resolved M-1
  disposition keeps that exact disposition.
- **Malformed structured data:** invalid UTF-8, framing, marker, attachment, or
  required-field shape raises `ValueError` before context rendering.
- **Partial R1 state:** a second complete projection/checkpoint join in the base
  shape, including v1 plus v2 without the exact relation, produces zero context.
  A historical predecessor base attachment cannot restore v1 context, and the
  session reader never performs relation-only recovery.
- **Implicit authority:** PLAN text, daily `next_step`, Git ancestry, canonical
  writer identity, or file presence alone must never be promoted into a resolved
  attachment.
- **Unreplayable authority:** missing or malformed authority-source and
  source-anchor fields cannot resolve current state. Well-formed fields are
  replayed as a previously admitted observation, not treated as cryptographic,
  legal, or independently revalidated approval proof.
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
insufficient for chat-free authority-observation reconstruction, and that one
bounded reader can join existing logical `active_task` and `review_log` data
plus one minimal persisted observation attachment on `review_log`.

It does not claim that the reader, attachment writer, instruction-freshness
representation, session integration, bootstrap, qualification, or two-session
pilot exists. It does not establish
authority, repair current memory, make the existing Gate 3 projection current,
or authorize RAG or later lifecycle work.

## Evidence Plan

N1 focused tests must demonstrate:

1. if a later separately authorized source-compatible freshness representation
   exists, one canonical v1 checkpoint, projection, resolved base attachment,
   and independently comparable freshness observation joins to the exact R0
   input and returns v1 once;
2. under the same explicit precondition, one canonical v1/v2 pair, one exact
   relation, resolved supersession attachment, and independently comparable
   freshness observation joins to the exact R1 input and returns only v2;
3. in an edge-selected R1 shape, unrelated well-formed historical checkpoints,
   projections, relations, and attachments do not change the target result; in
   the base shape, a second complete projection/checkpoint join yields zero
   context because no persisted structural selector proves it unrelated;
4. a missing observation attachment returns `insufficient_authority` with zero
   context, while a missing or duplicate checkpoint/projection or a duplicate
   observation attachment fails closed with `ValueError`;
5. identity, digest, public-renderer, endpoint, M-1 eligibility, or source-anchor
   mismatch fails closed;
6. a self-invalidating pre-write HEAD, an anchor that does not validate the
   attachment-containing commit, a Git anchor without evidence covering later
   qualified human instructions, and a replayed
   `current_human_instruction` without independently comparable persisted
   instruction-state evidence each yield `unassessable` with zero context;
7. one exactly joined non-resolved base or edge attachment preserves its M-1
   state with zero context, including a partial v1/v2 edge shape, while
   duplicate or conflicting non-resolved attachments fail closed;
8. malformed UTF-8, framing, marker, or attachment fails closed;
9. partial v1-plus-v2 state yields zero context and performs no repair;
10. one exact predecessor base attachment retained beside a controlling R1 edge
    is historical and does not compete with the edge; a resolved edge selects
    only v2 when freshness is otherwise established, while a partial or
    non-resolved edge yields zero context and never falls back to v1;
11. dependency calls, resolver outputs, paths, and bytes are snapshotted once and
   not re-read during selection;
12. direct calls to current live-reading/writing R0/R1 entrypoints are absent
    after the reader snapshots, while parity tests show the shared internal
    selection core preserves their bounded validation semantics;
13. no record, summary, identity, digest, or authority input can be supplied by
    the session caller; and
14. adjacent R0, R1, memory-layout, and canonical-writer tests remain green.

Spec-only validation is limited to scope census, link/token consistency,
`git diff --check`, PLAN freshness, and independent two-file technical review.
Passing those checks proves specification coherence only, not reader behavior.

## Implementation Tranche Recommendation

After this exact specification is accepted, authorize one NSI-N1 reader/adapter
tranche that:

- adds the smallest exact observation-attachment grammar to logical
  `review_log`;
- rejects pre-write HEAD equality as a freshness anchor and does not invent an
  attachment-containing-commit or instruction-state representation;
- appends it only through a bounded canonical helper;
- parses existing canonical checkpoints plus the new attachment;
- joins logical `active_task` and `review_log` snapshots into existing R0/R1
  selector inputs;
- extracts or adds one internal pure snapshot-selection core while preserving
  existing R0/R1 public behavior and validation semantics; and
- provides one internal persisted-session reader entrypoint.

NSI-N1 must not bootstrap current v1 or run the Session A/B pilot. Those actions
remain separate because they mutate canonical memory and test a later live
integration boundary. Without a separately authorized and available
instruction-freshness representation, N1 may implement structural joins and
non-resolved outcomes but must not claim either positive resolved case or
Natural Session Integration success.
