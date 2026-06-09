# #17 Active Non-Canonical Writer Fixture

Date: 2026-06-09

## Purpose

Provide a controlled negative-path fixture for #17 memory authority threshold analysis.

The fixture simulates a post-phase-1 active-window old-format memory append using:

- `tests/fixtures/memory_authority/active_non_canonical_writer/memory/2026-06-09.md`

## Expected Guard Behavior

- `active_non_canonical_writer.count` must be greater than 0.
- Guard mode remains `warning`.
- CLI default remains report-only unless `--fail-on-active-non-canonical-writer` is explicitly provided.
- No hook, validator, schema, threshold, or blocking behavior changes are introduced.

## Claim Ceiling

CLAIMED:

- Controlled fixture coverage for active-window non-canonical writer detection.
- Negative-path structural evidence that the guard reports an active old-format writer.

NOT CLAIMED:

- Runtime enforcement.
- Blocking threshold readiness.
- Hook integration.
- Production active violation.
- Memory semantic correctness.
- Historical memory cleanup.
