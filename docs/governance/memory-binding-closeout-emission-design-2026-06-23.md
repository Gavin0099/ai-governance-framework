# Memory Binding and Closeout Emission Design Candidate

Status:

```text
design-only candidate
no implementation
no schema/version bump
no runtime/enforcement change
no consuming-repo migration
```

## Problem

Current session-derived memory records carry governance signals that are easy to
over-read:

- `memory_binding: bound` currently means only that `commit` matches a hash-like
  regex in `governance_tools.memory_record`; it does not prove that the commit
  exists in the target repo.
- `commit` and `commit_hash` are duplicate fields in writer output.
- `test_evidence` is a prose string, which makes it easy to mistake summary
  text for structured evidence.
- canonical writer output and hand-written review notes can coexist in the same
  daily memory file, creating mixed-producer canonical surfaces.
- closeout / auto-promotion paths can emit repeated session records for the
  same task shape, diluting `promoted=True` into a per-session event rather than
  a durable per-task state.

This is a framework-level trust-signal problem, not a local consuming-repo
format problem. The writer and closeout paths live in this framework and affect
every repo that consumes it.

## Current repository truth

Observed from current source:

- `governance_tools/memory_record.py` defines `RECORD_FORMAT_VERSION = "1.0"`.
- `build_session_derived_record()` emits fixed fields including
  `commit`, `commit_hash`, `session_id`, `memory_binding`, `test_evidence`, and
  `next_step`.
- `commit_hash` is currently assigned the same value as `commit`.
- `memory_binding = "bound"` is currently assigned when `_REAL_HASH` matches
  the commit string.
- `_has_equivalent_session_derived_entry()` deduplicates same-day records using
  strict identity over `writer`, `commit_hash`, `test_evidence`, and `next_step`,
  while ignoring `session_id`.
- `governance_tools/memory_authority_guard.py` warns on non-canonical
  session-derived entries and old-format entries after the canonical writer
  cutoff, but historical debt remains warning evidence.
- `governance_tools/session_end_hook.py` surfaces `promoted` as part of
  session closeout summary state, so repeated closeouts can produce repeated
  promoted-looking observations.

## Target outcome

Make memory trust signals harder to overclaim by separating:

- syntactic hash shape from verified commit existence;
- prose summary from evidence references;
- canonical writer output from hand-written notes;
- per-session closeout events from per-task durable promotion state.

The target is a staged design path, not an immediate writer or closeout rewrite.

## Scope

In scope for this design candidate:

- describe the current binding semantics precisely;
- define candidate terminology for future binding fields;
- identify where hand-written notes should live relative to canonical memory;
- define closeout emission/idempotency design options;
- describe blast radius across consuming repos;
- propose the smallest meaningful implementation tranche.

## Non-goals

- no change to `governance_tools.memory_record`;
- no change to `record_format_version`;
- no change to `session_end_hook` or closeout emission behavior;
- no migration of historical memory records;
- no blocking behavior change;
- no CI, hook, or runtime enforcement change;
- no new proof claim that existing memory records are semantically correct.

## Affected surfaces

Potential future implementation would affect:

- `governance_tools/memory_record.py`;
- `governance_tools/memory_authority_guard.py`;
- `governance_tools/memory_workflow.py`;
- `governance_tools/session_end_hook.py`;
- `governance_tools/session_closeout_entry.py`;
- daily `memory/YYYY-MM-DD.md` files in this repo and consuming repos;
- closeout receipts and any tooling that parses `commit`, `commit_hash`,
  `memory_binding`, `test_evidence`, or `promoted`.

Because these are shared framework surfaces, this should be treated as
framework-wide governance behavior, not a single-repo cleanup.

## Boundary and API considerations

### Binding terminology

Do not silently strengthen the meaning of the existing `memory_binding` field.
Existing readers may already interpret `bound` as a weak shape signal. A future
change should add explicit fields rather than reinterpret old records.

Candidate fields:

```yaml
binding_format_valid: true | false
binding_target_exists: true | false | unknown
binding_target_type: git_commit | runtime_observation | external_reference | none
binding_resolution_error: <optional string>
```

Recommended interpretation:

- `binding_format_valid`: commit-like text passes format validation.
- `binding_target_exists`: the target was resolved in the local repo at write
  time or verification time.
- `binding_target_type`: records whether the binding is a source commit, runtime
  observation sentinel, or another explicit class.
- `memory_binding`: legacy field, kept for compatibility until a later
  migration decision.

### Evidence structure

`test_evidence` should not become a full ontology immediately. A narrow next
step is enough:

```yaml
evidence_refs:
  - type: command
    value: python -m ...
    result: pass
  - type: artifact
    value: path/to/artifact
  - type: reviewer_verdict
    value: ACCEPT
```

The prose `test_evidence` field can remain as a human summary while
`evidence_refs` becomes the parseable evidence entrypoint.

### Producer separation

Hand-written review notes should not masquerade as canonical
session-derived records. Future design options:

1. keep canonical daily memory restricted to `governance_tools.memory_record`;
2. put hand-written review notes under a separate typed surface;
3. provide a typed note writer if hand-written notes must stay in daily memory.

Do not solve this by allowing naked markdown records to share canonical status.

### Closeout emission semantics

Repeated closeout emissions are a behavior-policy issue, not a formatting issue.
Candidate options:

1. idempotency key: derive a closeout emission key from task intent, commit,
   outcome, and next step;
2. supersession: allow a newer record to mark an earlier same-task record as
   superseded rather than append another promoted-looking entry;
3. state-change emission: write auto-promoted memory only when task state
   changes materially;
4. advisory duplicate report first: add a detector before changing emission.

The design should avoid treating repeated `promoted=True` events as durable
per-task promotion state unless a task-level state model exists.

## Failure paths and risk points

- Reinterpreting `memory_binding: bound` would retroactively change the meaning
  of historical records.
- Bumping `record_format_version` without dual-reader support would break
  consuming repos.
- Adding structured evidence without migration guidance could create two
  competing evidence authorities.
- Closeout idempotency can accidentally suppress legitimate repeated sessions if
  the idempotency key is too coarse.
- Supersession can hide history if it mutates old records rather than appending
  explicit supersession observations.
- Enforcing new binding semantics too early could block repos with historical
  memory debt unrelated to the current change.

## Blast radius

This is cross-repo framework infrastructure. Any implementation must assume:

- existing consuming repos may contain writer v1.0 records;
- consuming repos may also contain hand-written daily memory records;
- pre-commit and push hooks may parse daily memory;
- closeout receipts may surface memory workflow summaries;
- reviewers may rely on existing `memory_binding` wording.

Compatibility requirement:

```text
future readers must accept v1.0 records and any new fields simultaneously
until an explicit migration is designed and reviewed.
```

## Evidence plan

Before implementation:

1. Add an audit-only scanner that reports:
   - non-hash `commit_hash` with `memory_binding: bound`;
   - hash-shaped commit values that do not resolve in the local repo;
   - old-format / hand-written records in daily memory;
   - repeated same-task closeout-like records;
   - repeated promoted-looking session records.
2. Run the scanner on this repo and at least one consuming repo sample.
3. Classify findings as warning evidence only.
4. Review false positives before any writer or closeout behavior change.

Implementation evidence, if later approved:

- focused tests for writer output compatibility;
- focused tests for v1.0 reader compatibility;
- fixtures for runtime-observation sentinel records;
- closeout duplicate/supersession fixtures;
- memory workflow guard behavior unchanged unless separately authorized.

## Implementation tranche recommendation

Recommended first tranche:

```text
audit-only memory binding and closeout emission scanner
```

Scope:

- read daily memory files;
- parse existing v1.0 records and old-format entries;
- report weak binding and duplicate emission signals;
- exit 0 by default;
- no writer changes;
- no schema bump;
- no closeout behavior change;
- no blocking.

Why first:

- It quantifies blast radius before changing trust semantics.
- It aligns with the framework posture of failure-driven governance.
- It avoids silently redefining `memory_binding`.
- It produces reviewer-facing data for deciding whether a stronger change is
  justified.

Deferred tranches:

1. add explicit binding fields while preserving v1.0 compatibility;
2. add structured `evidence_refs`;
3. add typed note writer or separate note surface;
4. design closeout idempotency/supersession;
5. consider blocking only after observed false-positive/false-negative behavior
   and migration evidence.

## Claim ceiling

This candidate can claim:

- the current weak binding and closeout-emission risks have been named;
- blast radius and staged options are documented;
- the recommended first tranche is audit-only.

This candidate cannot claim:

- memory binding semantics are fixed;
- closeout duplicate emission is fixed;
- evidence is structured;
- old hand-written records are migrated;
- consuming repos are compatible with a future schema;
- any enforcement or blocking has changed.
