# Memory Runtime R0 Exact Round-Trip Technical Specification

Status: IMPLEMENTATION-READINESS CANDIDATE; NON-AUTHORITATIVE TECHNICAL
SPECIFICATION

Program: Memory Runtime
Milestone: R0

## Authority Boundary

This document is an implementation-driving engineering specification. It is
not a canonical governance authority, is not registered in
`governance/AUTHORITY.md`, and does not become an agent-loading requirement or
an enforcement source when merged. It records the expected behavior for a
separately authorized implementation tranche.

Implementation-readiness acceptance is a delivery decision, not governance
activation. A concrete observed runtime failure may later justify the smallest
necessary failure-driven governance rule, but this specification does not
pre-authorize that promotion.

## Problem

The repository has a canonical session-derived memory writer, a logical memory
surface resolver, and bounded MRCSP detectors. It does not have one runtime
slice proving that one caller-authorized active-task record can be written,
retrieved from the same logical surface, and rendered into context without
identity substitution, content substitution, silent omission, or injection.

The missing capability is an exact round trip. It is not semantic retrieval,
RAG, lifecycle automation, or a policy for deciding what deserves memory.

## Current Repository Truth

- `governance_tools.memory_record.append_projection_with_outcome()` is the
  canonical writer for the active-task summary projection. It returns the
  writer-owned path, status, and record identity.
- `governance_tools.memory_record.build_record_identity()` defines the stable
  identity used by canonical same-day deduplication. Its identity class is not
  universal and R0 must not redefine or broaden it.
- `governance_tools.memory_record.render_active_task_projection()` is the
  public renderer used by that writer. It owns summary normalization and the
  exact marker format.
- The active-task writer currently targets `memory/01_active_task.md` directly.
  Readers are separately required by
  `governance/MEMORY_SURFACE_AUTHORITY_CONTRACT.md` to resolve logical surfaces
  through `memory_pipeline.memory_layout` rather than require a hard-coded
  consumer filename.
- `memory_pipeline.memory_layout.resolve_memory_file()` currently resolves
  logical `active_task` to the configured alias table.
- MRCSP M1b-3 reports one bounded caller-admitted missing-surface observation.
  A clean M1b-3 report contains no request-binding path or logical name and is
  therefore not proof that a particular R0 request surface exists.
- The M-1 authority contract defines `resolved`, `reviewer_required`,
  `disputed`, `insufficient_authority`, and `unassessable`. R0 does not
  re-evaluate or collapse those semantics.
- No merged runtime reader or context renderer currently establishes the R0
  round-trip invariant.

## Target Outcome

Define one smallest vertical slice for exactly one caller-authorized canonical
session-derived record and logical `active_task` surface:

```text
caller-authorized canonical record and summary
  -> canonical active-task writer
  -> writer outcome identity and path
  -> logical-surface resolution and exact persisted-byte retrieval
  -> verbatim context line with the same provenance identity
```

The future implementation may report `resolved` only after the canonical
writer returns an allowed successful outcome and every identity, path, byte,
cardinality, and caller-admitted authority precondition below is satisfied from
bounded local snapshots.

## Normative R0 Contract

<!-- memory-runtime-r0-contract:begin -->
```json
{
  "contract_version": "memory-runtime-r0-exact-round-trip.v0.1",
  "logical_name": "active_task",
  "writer": "governance_tools.memory_record.append_projection_with_outcome",
  "writer_surface": "SURFACE_ACTIVE_TASK_SUMMARY",
  "identity_source": "governance_tools.memory_record.build_record_identity",
  "expected_line_source": "governance_tools.memory_record.render_active_task_projection",
  "resolver": "memory_pipeline.memory_layout.resolve_memory_file",
  "rendering": "verbatim_retrieved_projection_line",
  "non_target_candidate_policy": "ignore_if_structurally_valid",
  "allowed_write_statuses": ["written", "already_present"],
  "resolution_states": [
    "resolved",
    "reviewer_required",
    "disputed",
    "insufficient_authority",
    "unassessable"
  ],
  "m1_observation_binding": {
    "query_class": "current_progress",
    "logical_name": "active_task",
    "requested_record_identity": "must_equal_caller_authorized_record_identity",
    "resolved_record_identity": "must_equal_writer_outcome_identity_when_resolved"
  },
  "failure_mode": "fail_closed",
  "mrcsp_composition": "caller_admitted_observation_only_no_detector_call",
  "implementation_authorized": false
}
```
<!-- memory-runtime-r0-contract:end -->

### Admission And Authority Boundary

R0 receives a caller-authorized canonical record, caller-supplied active-task
summary, project root, memory root, exact logical name, and caller-admitted M-1
resolution observation. Authorization must already exist outside R0. R0 may
validate the supplied evidence shape and continuity, but it does not decide:

- whether the information deserves storage;
- who has authority to write or review it;
- whether privacy, retention, or deletion policy permits it; or
- whether an M-1 non-resolved state should be upgraded.

The caller-admitted observation must be carried in an R0 binding envelope whose
`query_class` is exactly `current_progress`, whose `logical_name` is exactly
`active_task`, and whose `requested_record_identity` equals the
caller-authorized canonical record identity. A `resolved` observation must also
name a `resolved_record_identity` equal to the canonical writer outcome
identity. Missing or mismatched binding fields fail closed with `ValueError`
and zero rendering. This envelope binds the supplied observation to this R0
request; it does not implement, reinterpret, or broaden M-1 resolution.

Only a correctly bound caller-admitted `resolved` observation may continue to
context rendering. Correctly bound `reviewer_required`, `disputed`,
`insufficient_authority`, and `unassessable` states must be returned unchanged
with zero rendered records. They are not ordinary exceptions and must not be
collapsed into `ValueError`.

### Writer And Identity Continuity

R0 must call the canonical writer and consume its public outcome. It must not
copy `_RECORD_IDENTITY_FIELDS`, implement a second deduplication rule, or treat
the current record identity as a universal identity.

For the single admitted record:

```text
caller-authorized canonical record identity
  = canonical writer outcome identity
  = persisted projection marker identity
  = retrieved projection marker identity
  = context-rendering provenance identity
```

The caller-authorized canonical record identity must equal
`build_record_identity(record)` before the writer is invoked. The returned
status must be exactly `MEMORY_WRITE_STATUS_WRITTEN` or
`MEMORY_WRITE_STATUS_ALREADY_PRESENT`. Any other status or identity mismatch
fails closed.

Writer idempotence does not establish content continuity. In particular,
`already_present` for the same identity cannot hide a different summary.

### Content Continuity

R0 must obtain the writer-owned expected line only through:

```python
render_active_task_projection(record, summary=caller_supplied_summary)
```

It must not call or copy private summary-normalization helpers. The UTF-8 bytes
of that public renderer's return value must equal the one persisted projection
line selected for the expected identity, the retrieved line bytes, and the
verbatim context line bytes. A same-identity line with different summary bytes
fails closed even when the writer reports `already_present`.

### Logical Path Continuity And Snapshot Boundary

After the authorized writer call and before retrieval, R0 snapshots each of
the following exactly once:

1. the writer outcome, including `path`, `status`, and `record_identity`;
2. the resolver callable and its returned path for the caller-admitted
   `memory_root` and exact logical `active_task` name;
3. equality of the writer outcome path and resolved path;
4. the resolved path existence state;
5. the resolved file bytes;
6. strict UTF-8 decode of that byte buffer; and
7. the parsed active-task projection candidates and expected-identity
   cardinality derived from that decoded snapshot.

Subsequent decisions and output use only those local snapshots. R0 must not
hard-code `01_active_task.md`. If the writer outcome path and resolver path do
not match, R0 fails closed before retrieval and never reports `resolved`. The
authorized write may already have occurred; R0 does not roll it back, delete
it, or claim the mismatch is repaired.

A missing or non-directory memory root, unknown logical name, absent resolved
surface, path mismatch, invalid input type, ordinary writer/resolver/read/decode
exception, or changed/invalid snapshot fails closed with `ValueError`. A
missing logical surface is never interpreted as a legitimate empty result.

### Independent Fail-Closed Retrieval Grammar

The reader must validate persisted bytes independently. It cannot assume the
file was produced only by the current writer because the file may be older or
manually edited.

For every projection-looking active-task line, the bounded structural grammar
requires:

1. strict UTF-8 decoding with no replacement fallback;
2. one record on exactly one LF-terminated line;
3. the exact `- ` line prefix;
4. one non-empty summary with no leading or trailing whitespace;
5. no `memory_record_projection:`, `<!--`, or `-->` token inside the summary;
6. exactly one terminal marker;
7. exact surface token `active-task-summary`;
8. exactly one lowercase 64-hex identity in that marker.

A structurally valid candidate carrying another identity is a permitted
historical non-target record and is ignored for target selection. Its presence
is not corruption. A projection-looking line that fails the structural grammar
cannot be safely excluded as the target and therefore fails closed.

After structural validation, there must be exactly one candidate for the
expected identity, and that target line must be byte-equal to the public writer
renderer's expected line. Zero target candidates, multiple target candidates,
or a target content mismatch fails closed. Unrelated non-projection Markdown
may remain outside this bounded grammar and is not interpreted by R0.

### Set Completeness

Let `E` be the set containing the one caller-authorized record that the
canonical writer accepted and the exact reader retrieved in this invocation.
R0 must establish both:

```text
set(context-rendered record identities) = set(E identities)
count(context-rendered records) = |E|
```

This prevents silent drop, injection, and duplicate rendering. Equality for
the records that survived is not sufficient if an eligible record disappeared
or an unadmitted record entered context.

### MRCSP M1b-3 Composition

R0 uses composition B: it may consume a caller-admitted M1b-3 observation, but
must not call the M1b-3 detector.

- A missing-surface finding is consumable only when its `logical_name` and
  `resolved_path` exactly match the R0 request and local resolver snapshot.
- A clean M1b-3 report is advisory only because its top-level bytes do not bind
  it to one request surface.
- Presence and content remain determined by R0's exact path and byte snapshots.
- M1b-3 findings do not authorize creation, repair, scanning, or mutation.

## Scope

- one caller-authorized canonical session-derived record;
- logical `active_task` only;
- the existing canonical active-task writer and its public identity and render
  functions;
- exact logical-path comparison, bounded byte retrieval, independent grammar,
  and verbatim one-line context rendering;
- preservation of caller-admitted M-1 resolution states;
- optional consumption of one caller-admitted M1b-3 observation without
  detector invocation; and
- deterministic, closed-schema result bytes for unchanged inputs and snapshots.

## Non-Goals

- no implementation in this specification tranche;
- no decision about what to remember and no authority-policy creation;
- no writer redesign, writer path change, identity redesign, or dedup redesign;
- no atomic-write, crash-safety, partial-write recovery, or transactional
  durability claim for the existing writer;
- no MRCSP detector integration, invocation, scanning, or repository-wide
  completeness claim;
- no semantic retrieval, ranking, embeddings, vector database, RAG, LLM
  selection, or query expansion;
- no Markdown meaning extraction beyond the bounded projection-line grammar;
- no update, supersession, merge, freshness, conflict resolution, retention,
  expiry, delete, repair, or rollback;
- no schema, hook, CI, gate, blocker, enforcement, or Gate 3 change; and
- no Memory Runtime R1 or later tranche.

## Affected Surfaces

This specification changes only the R0 technical specification, its PLAN
candidate, and document-contract tests. A separately authorized
implementation is expected to add one reader/runtime module and focused tests;
the exact implementation paths remain intentionally unfrozen until that
tranche begins.

The existing `governance_tools/memory_record.py`,
`memory_pipeline/memory_layout.py`, MRCSP detectors, memory files, runtime
hooks, schemas, and CI workflows are read-only dependencies for this spec.

## Boundary And API Considerations

- Public dependencies are limited to `append_projection_with_outcome()`,
  `build_record_identity()`, `render_active_task_projection()`, public surface
  and status constants, and `resolve_memory_file()`.
- Private writer helpers and `_RECORD_IDENTITY_FIELDS` are not R0 APIs.
- The writer-path/resolver-path asymmetry is checked, not normalized or hidden.
- Exact retrieval does not imply current-state authority; the supplied M-1
  resolution observation remains a separate, request-bound input and result
  field.
- Result serialization must be deterministic UTF-8 JSON with sorted keys,
  compact separators, and one trailing LF. It must contain no timestamp,
  absolute machine path, reviewer identity, or ambient filesystem scan result.

## Failure Paths And Risk Points

- treating same-day dedup identity as universal semantic identity;
- treating a successful verified round trip as proof that an interrupted writer
  cannot leave partial bytes;
- treating `already_present` as proof that persisted summary bytes match;
- reading the writer's hard-coded path instead of the logical resolver result;
- accepting an alias-table drift that makes writer and reader target different
  files;
- trusting current-writer validation instead of independently parsing
  persisted bytes;
- treating a well-formed historical non-target identity as corruption;
- treating a clean unbound M1b-3 report as request-specific proof;
- accepting an M-1 observation bound to another query, logical surface, or
  record identity;
- converting a missing surface into an empty context;
- preserving identity equality while silently dropping the record; and
- treating verbatim retrieval as freshness, truth, supersession, or semantic
  relevance.

## Evidence Plan

<!-- memory-runtime-r0-evidence-cases:begin -->
```json
[
  "exact_written_round_trip",
  "exact_already_present_round_trip_without_duplicate",
  "same_identity_different_summary_fails_closed",
  "writer_resolver_path_mismatch_fails_closed",
  "missing_or_non_directory_root_fails_closed",
  "unknown_logical_name_fails_closed",
  "missing_surface_is_not_empty_result",
  "invalid_argument_types_fail_closed",
  "ordinary_dependency_exceptions_fail_closed",
  "invalid_utf8_fails_closed",
  "target_zero_multiple_or_malformed_marker_fails_closed",
  "well_formed_non_target_identities_are_ignored",
  "caller_record_identity_mismatch_fails_closed",
  "writer_outcome_identity_mismatch_fails_closed",
  "unexpected_writer_status_fails_closed",
  "m1_non_resolved_states_preserved_without_rendering",
  "m1_observation_subject_mismatch_fails_closed",
  "m1b3_detector_is_not_called",
  "m1b3_finding_requires_logical_name_and_path_match",
  "clean_m1b3_report_is_advisory_only",
  "surrounding_summary_whitespace_uses_public_renderer_normalization",
  "reserved_projection_tokens_fail_at_writer_boundary",
  "no_silent_drop_injection_or_duplicate_render",
  "single_snapshot_dependency_counts",
  "unchanged_input_and_snapshot_produce_byte_identical_json"
]
```
<!-- memory-runtime-r0-evidence-cases:end -->

Specification tests freeze the contract structure, current public dependency
names, M-1 state preservation, composition B, evidence-case inventory,
non-authoritative placement, and non-goals. They prove document consistency
only.

The future implementation tranche must turn every listed case into executable
behavioral tests and retain the existing memory writer, layout, MRCSP, authority
metadata, and governance tests. Passing those tests would prove only the
bounded exact round trip under tested snapshots.

## Claim Ceiling

This specification may claim only a reviewable proposed technical contract
for one caller-authorized canonical active-task record to preserve writer-owned
identity and exact projection-line bytes through bounded retrieval and verbatim
context rendering.

It does not claim that runtime behavior exists, that MRCSP is integrated into
runtime, that a write is semantically correct or currently authoritative, that
memory is complete or fresh, or that retrieval is intelligent. It does not
authorize RAG, update, supersession, deletion, enforcement, Memory Runtime R1,
or any Gate 3 change.

## Implementation Tranche Recommendation

After this specification receives exact-head technical approval with no
unresolved P0/P1, green required checks, reviewed-head preservation, and merge,
it is accepted as implementation-ready. The next separately authorized tranche
should implement only the one active-task exact round trip and the evidence
cases above. Stop after that vertical slice. Do not add semantic retrieval,
additional logical surfaces, or lifecycle mutation in the same tranche.
