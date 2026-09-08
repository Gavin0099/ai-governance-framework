# Governance Runtime Output Misroute Incident — 2026-08-30

## Status

```text
PRESERVED / NOT RECONCILED
```

This incident record preserves exact recovery material for two governance
closeout executions whose output root resolved to a qualification temporary
directory. It does not modify the canonical runtime ledgers or memory.

## Incident identity

- Session: `31bf9f05-6c1d-4ec5-a7fd-9a26d7a6d4c2`
- Misplaced source root: `.qualification_tmp/solo-20260830`
- Affected closeout times: approximately `2026-08-30T21:07+08:00` and
  `2026-08-30T21:12+08:00`
- Root writer resumed at approximately `2026-08-30T21:16+08:00`
- Preserved files: 20
- Preserved source bytes: 594,080
- Source manifest SHA-256:
  `349e850c3d1da706bea89f521cbb4c603254cfbe367e25cc5c201c0b758ebeed`
- Recovery archive SHA-256:
  `bc03423c22dfa52aacd8c20bea3170aa796f6b8f41b730ed484678a8d5670869`

The authoritative per-file identities are in
`artifacts/evidence/runtime-output-misroute-20260830/MANIFEST.json`.

## Confirmed scope

The incident was local, not a permanent post-19:33 runtime outage. The two
misplaced executions created records below the temporary root, after which a
later closeout wrote to the repository root again.

Unique or non-duplicated recovery material includes:

- two closeout receipt files absent from the root receipt directory;
- two records in each of six append-log surfaces that are not exact root-log
  duplicates; and
- memory record identity
  `0733740a5e63d8735ce014c180264e79e455df644c47ae07fe8707f280ebb229`,
  which is absent from the root daily memory file.

The misplaced CodeBurn database must not be merged. It contains 1,010 `steps`
rows with distinct generated `step_id` values, but all 507 unique semantic row
forms are already present in the root database. Blind ingestion would duplicate
existing information.

Single-state candidate, summary, trace, verdict, closeout, and advisory files
also must not overwrite their root counterparts. Some root counterparts were
subsequently regenerated and represent a later runtime state.

## Root cause and prior authority

This incident is a recurrence of the evidence-substrate drift documented in
`docs/governance/artifact-write-boundary-2026-06-23.md`.

The owner-ratified contract from that document remains controlling:

> Canonical artifact root is an explicit contract, not an ambient cwd-derived
> property.

The current runtime still permits `--project-root` to default to `.` and has
legacy command wiring that explicitly passes `--project-root .`. When such a
closeout runs with a nested working directory, the canonical output root moves
with ambient process state.

The durable fix is not automatic Git-root inference. Callers must provide the
intended absolute project root; writers must normalize and validate it and fail
closed when it is absent or invalid. Git or framework markers may validate a
supplied root but may not silently choose the governance authority root.

## Operational prohibition and containment

Until root binding is implemented and verified:

- do not delete or modify `.qualification_tmp/solo-20260830`;
- do not merge, append, or ingest the preserved files into root runtime state;
- do not use the misplaced database as an ingest source;
- launch qualification harnesses with the framework repository root as the
  process working directory; and
- stop if a closeout receipt resolves its output path below a nested working
  directory.

This working-directory containment is temporary. It does not close the already
ratified root-binding implementation debt.

## Archive verification

The archive was extracted into an independent system temporary root. All 20
extracted files matched their source files byte for byte and matched the
manifest byte counts and SHA-256 values. The archive contained no additional
files, and the verification temporary root was removed afterward.

## Recovery boundary

Historical reconciliation requires a separate owner-authorized slice after the
writer root-binding fix. That slice must determine, by surface, whether a
record should be appended through a canonical writer, represented by a recovery
receipt, retained only as forensic evidence, or excluded as a semantic
duplicate.

## Claim ceiling

This checkpoint proves only that the exact misplaced bytes have a durable,
independently verifiable recovery copy. It does not prove that canonical logs
have been repaired, that memory has been reconciled, that the root-binding bug
has been fixed, or that Solo qualification may resume.
