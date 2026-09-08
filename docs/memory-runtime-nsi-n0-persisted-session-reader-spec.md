# Memory Runtime NSI-N0 Feasibility And Representation Decision

Status: delivered and accepted non-authoritative technical feasibility
decision; not a reader specification, governance authority, or implementation.

Delivery: PR #147; exact reviewed head
`f1530182d65c4cbd4ab24bfd75e6e5af0ce343fc`; merge commit
`10044277b99e68973130d23ce97697418de59d21`.

## Question

Can a completely new Agent session, without prior chat history, reconstruct and
safely trust the current bounded `active_task` state using only persisted
repository state?

NSI-N0 answers that feasibility question. It does not define the complete
reader grammar or authorize implementation.

## Evidence Base

The following facts were observed at merged main
`73cf59bdb0f71ca155093715e6b6b8ee00bc7062`:

- `memory_pipeline.active_task_round_trip.round_trip_active_task()` requires a
  caller-supplied record, summary, and authority observation.
- `memory_pipeline.active_task_supersession.select_current_active_task()` and
  `supersede_active_task()` likewise require caller-supplied predecessor data
  and, for supersession, successor data plus authority.
- Repository callers of those entrypoints are limited to implementation,
  specifications, and tests. No natural session-start caller exists.
- Logical `active_task`, resolved through `memory_pipeline.memory_layout`,
  persists a summary and canonical record identity.
- Logical `review_log`, also resolved through `memory_layout`, persists enough
  canonical checkpoint fields to reconstruct a candidate record and verify it
  by recomputing `build_record_identity()` and the public renderer bytes.
- No merged persisted surface carries the complete content-bound M-1 authority
  observation required by R0/R1.
- No merged persisted artifact provides a commit-stable, independently
  comparable identity for the current qualified human-instruction state.
- The current `active_task` surface contains historical Gate 3-era projections,
  no R1 supersession relation, and no qualified R1 milestone projection from
  which a real Session A/B pilot can begin.

These observations establish that existing persisted surfaces can reconstruct
record plus summary data, but cannot establish that an earlier resolved
authority decision remains fresh in a later session.

## Feasibility Result

`RESOLVED_NATURAL_SESSION_REPLAY = BLOCKED`

A fresh session cannot safely produce resolved current context from the present
repository state. It must not fill the missing authority-freshness evidence from
chat history, timestamps, filename order, newest text, PLAN ordering, commit
existence, writer identity, or semantic guessing.

The blocked result is intentional fail-closed behavior. It is not evidence that
R0 or R1 is incorrect; those components remain caller-admitted primitives and
were not designed to discover their own authority inputs.

## Authority-Freshness Findings

### `current_human_instruction`

The repository has no independently comparable persisted identity for the
current qualified human-instruction state. An earlier attachment that recorded
`current_human_instruction` therefore cannot be replayed as resolved in a fresh
session.

Without separately authorized freshness evidence, the only safe disposition is
`unassessable` with zero context.

### `approved_change`

Repository HEAD equality is necessary evidence that the committed repository
state has not changed, but it is not sufficient evidence that no later
qualified human instruction exists outside Git.

A pre-write HEAD is also self-invalidating: committing an attachment changes
HEAD, so equality with the value observed before that append cannot survive the
attachment-containing commit.

Any future representation must both:

- survive and validate the attachment-containing committed state; and
- provide source-compatible, mechanically comparable evidence covering later
  qualified human instructions.

No such representation is defined or authorized by NSI-N0.

### Existing non-resolved observations

An observation already carrying `reviewer_required`, `disputed`,
`insufficient_authority`, or `unassessable` remains non-resolved. File presence,
HEAD equality, or attachment existence must never upgrade it.

## Representation Decision

NSI-N0 does not introduce an instruction ledger, new logical memory surface,
manifest, database, schema, or public Runtime result format.

The next candidate work, if separately authorized, is one minimal technical
spike answering only:

> What is the smallest persisted, independently comparable freshness evidence
> that can classify Session B as same, changed, or unverifiable relative to the
> authority state admitted in Session A?

The spike must not assume that Git HEAD alone proves human-instruction
freshness. It may conclude that no safe bounded representation is currently
available. A failed spike is a valid result.

Reader implementation, attachment grammar, current-selection cardinality,
historical precedence, standalone-v2 admission, and R1 edge-selection behavior
remain deferred until this prerequisite exists. They are not acceptance
criteria for this feasibility decision.

## Scope

- the current repository's bounded `active_task` R0/R1 primitives;
- persisted record and summary reconstruction feasibility;
- cross-session M-1 authority-freshness feasibility; and
- identification of the smallest next unanswered representation question.

## Non-Goals

- no reader, adapter, attachment writer, or session-start integration;
- no reader grammar, selection state machine, or public API;
- no new authority policy or independent proof of human approval;
- no bootstrap, migration, historical rewrite, or Session A/B pilot;
- no RAG, semantic retrieval, longer lineage, graph engine, merge semantics,
  deletion, expiry, concurrency, rollback, or crash atomicity;
- no Runtime, writer, `memory_layout.py`, hook, CI, gate, blocker, or enforcement
  change; and
- no claim that Natural Session Integration is implemented or qualified.

## Acceptance

NSI-N0 is complete because this delivered two-file decision records all of the
following without promising an implementation-ready reader grammar:

1. existing persisted surfaces can reconstruct record plus summary;
2. current repository state cannot mechanically prove cross-session authority
   freshness;
3. resolved Natural Session replay is therefore blocked and yields zero
   context;
4. `current_human_instruction` cannot be replayed as resolved without an
   independently comparable persisted identity;
5. `approved_change` cannot be replayed as resolved from HEAD equality alone;
   and
6. the only next candidate is a separately authorized minimal
   freshness-representation spike.

Acceptance requires exact-head independent review with no unresolved P0/P1,
green scope-matched checks, reviewed-head preservation, and separate owner merge
authorization.

## Claim Ceiling

This decision may claim only that current merged repository evidence supports
record-plus-summary reconstruction but does not support resolved cross-session
authority replay.

It does not claim that a reader, freshness representation, authority attachment,
bootstrap, pilot, RAG system, or Natural Session Integration implementation
exists. It does not authorize any subsequent implementation or merge.
