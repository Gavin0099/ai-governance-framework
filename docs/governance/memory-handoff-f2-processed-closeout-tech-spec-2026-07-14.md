# Memory Handoff F2 Processed-Closeout Check Tech Spec

Status: REVIEW ONLY / DESIGN ONLY
Date: 2026-07-14
Local label: memory-handoff F2 (not the unrelated F2 labels used by other governance documents)

## DONE

DONE = define one report-only check that determines whether the current
`artifacts/session-closeout.txt` has a later, matching canonical closeout
receipt and reports `closeout_handoff_complete=false` when it does not; do not
implement the check, change runtime behavior, or modify a consumer.

## Problem

A session may write `artifacts/session-closeout.txt` and stop before invoking
`governance_tools.session_closeout_entry`. The technical work and the plain-text
closeout then exist, but no canonical receipt proves that the closeout pipeline
processed that version of the file or evaluated its memory handoff.

The observed driver handoff failure had this shape: the closeout text existed
and was newer than the latest relevant receipt evidence, while no matching
driver-session receipt or trigger row was present. The later canonical memory
write was corrective, not evidence that the original closeout invocation ran.

F1 hardened `memory_record` against blank `test_evidence`. F1 does not detect or
repair this separate F2 invocation omission.

## Current Repository Truth

1. `governance_tools/session_closeout_entry.py` is the canonical closeout
   entrypoint. It writes both trigger evidence and
   `artifacts/runtime/closeout-receipts/closeout_receipt_*.json`.
2. Receipt schema 1.3 currently includes at least:
   - `timestamp`;
   - `entrypoint`;
   - `exit_code`;
   - `closeout_artifact_path`;
   - `checksum_of_cleaned_path`;
   - `memory_eligibility_evaluated`;
   - `memory_write_required`;
   - `memory_write_performed`;
   - `memory_write_claim_verified`.
3. `_latest_receipt_checksum()` returns the newest non-empty checksum from the
   receipt directory. It does not filter by artifact path or entrypoint and
   therefore is not sufficient for this check.
4. `manage_agent_closeout.py` reads receipt fields for synthetic-smoke
   compliance, but it is an installer/verification surface rather than a
   general repository handoff report.
5. `governance/MEMORY_PROTOCOL.md` describes receipt presence as evidence that
   workflow state was observed; receipt presence alone does not prove memory
   completion.
6. No current tool emits `closeout_handoff_complete` or compares the current
   closeout file modification time with a path-matched canonical receipt.
7. The observed driver failure is session-local evidence. No tracked failure
   matrix or original driver receipt exists in this repository; the original
   driver-session receipt result was `NOT PRESENT`.

Proposal-time tooling classified this as a `common,python` candidate. No
architecture-impact preview was needed for this design because the recommended
tranche adds a standalone reader and does not change shared runtime entrypoints.

## Target Outcome

Provide a deterministic read-only command that answers:

> Has the current closeout file been processed by a successful canonical
> closeout receipt, and is the recorded memory handoff outcome internally
> complete?

The result must be machine-readable and understandable without decoding the
receipt schema manually.

## Scope

- Read the configured closeout artifact, defaulting to
  `artifacts/session-closeout.txt` under `--project-root`.
- Read existing `closeout_receipt_*.json` files.
- Match receipts to the exact resolved closeout path and canonical entrypoint.
- Select the latest valid matching receipt deterministically.
- Compare receipt timestamp, current file modification time, and SHA-256.
- Evaluate the receipt's existing memory eligibility/write outcome.
- Emit JSON and human output.
- Return a non-blocking process result for every report finding.

## Non-Goals

- No automatic memory write or correction.
- No automatic invocation of `session_closeout_entry`.
- No receipt, trigger, candidate, ledger, PLAN, or memory file creation.
- No hook, closeout pipeline, gate, CI, or blocking-policy change.
- No schema change and no new receipt field.
- No edit to `governance_tools/session_end_hook.py`,
  `governance_tools/session_closeout_entry.py`, or
  `runtime_hooks/core/session_end.py`.
- No consumer modification, onboarding, F-7 update, commit, or push.
- No claim that a fresh receipt proves technical correctness, evidence truth,
  daily-memory semantic quality, or framework correctness.
- No attempt to solve F3-F6 from the memory-handoff failure matrix.

## Affected Surfaces

Recommended first implementation tranche:

- new `governance_tools/processed_closeout_check.py`;
- new `tests/test_processed_closeout_check.py`.

Documentation updates beyond this tracked tech spec are deferred until the
command behavior is reviewed. Existing closeout writers and schemas are inputs,
not modification targets.

## Boundary and API Considerations

### Read-only boundary

The checker must not call the closeout entrypoint or any helper that writes
artifacts. It may use hashing, JSON parsing, path normalization, timestamp
parsing, and formatting only. Running the checker twice against unchanged files
must leave `git status` and filesystem contents unchanged.

### Receipt matching

A receipt is a candidate only when all of the following are true:

1. the JSON object parses;
2. `entrypoint == "governance_tools.session_closeout_entry"`;
3. `closeout_artifact_path`, after platform-aware normalization and resolution,
   equals the configured closeout path;
4. `timestamp` is a timezone-aware ISO-8601 value;
5. the schema version is explicitly supported by the implementation.

The initial supported set should be the repository-evidenced receipt schemas
`1.1`, `1.2`, and `1.3`. Schema 1.1 introduced
`memory_write_claim_verified`; schema 1.0 lacks that positive-evidence field and
must not produce `true`. Adding another version requires a focused compatibility
test, not permissive acceptance of unknown schemas.

Do not reuse `_latest_receipt_checksum()` as the matcher. Its directory-global
selection can pair a closeout file with a receipt for another artifact.

### Latest receipt selection

Select the valid candidate with the greatest payload `timestamp`; use normalized
receipt path as a deterministic tie-breaker. Filename and filesystem mtime are
diagnostic only and must not outrank the receipt payload timestamp.

Malformed, unsupported, or unrelated receipts do not count as matching. Their
counts should remain visible in diagnostics so a positive result cannot hide
that parsing was degraded.

### Completion predicate

`closeout_handoff_complete=true` only when every condition below is true:

1. the closeout file exists and is a regular file;
2. a valid matching receipt exists;
3. receipt `exit_code == 0`;
4. receipt timestamp is greater than or equal to the closeout file mtime;
5. receipt `checksum_of_cleaned_path` equals the current file SHA-256;
6. `memory_eligibility_evaluated == true`;
7. either memory was not required, or both
   `memory_write_performed == true` and
   `memory_write_claim_verified == true`.

Every other observed state reports `closeout_handoff_complete=false` with one
primary `reason_code` and supporting diagnostics. This is deliberately
conservative: `false` means the checker lacks complete positive evidence, not
that the technical session work was lost.

### Reason codes

Initial fixed vocabulary:

- `closeout_artifact_not_present`;
- `closeout_artifact_not_regular_file`;
- `matching_receipt_not_present`;
- `matching_receipt_failed`;
- `closeout_newer_than_receipt`;
- `closeout_checksum_mismatch`;
- `memory_eligibility_not_evaluated`;
- `required_memory_write_not_performed`;
- `memory_write_claim_not_verified`;
- `closeout_handoff_complete`.

Malformed and unsupported receipt counts are diagnostics, not alternate primary
reason codes unless no valid matching receipt remains.

### Output contract

Minimum JSON fields:

```json
{
  "report_only": true,
  "closeout_handoff_complete": false,
  "reason_code": "closeout_newer_than_receipt",
  "project_root": "<resolved path>",
  "closeout_artifact_path": "<resolved path>",
  "closeout_exists": true,
  "closeout_mtime_utc": "<ISO-8601>",
  "closeout_sha256": "<hex>",
  "matching_receipt_path": "<resolved path or empty>",
  "matching_receipt_timestamp_utc": "<ISO-8601 or empty>",
  "matching_receipt_schema_version": "1.3",
  "receipt_exit_code": 0,
  "checksum_matches": false,
  "memory_eligibility_evaluated": true,
  "memory_write_required": true,
  "memory_write_performed": false,
  "memory_write_claim_verified": true,
  "ignored_malformed_receipt_count": 0,
  "ignored_unsupported_receipt_count": 0
}
```

Human output must begin with one plain-language line:

- complete: `Closeout handoff is complete for the current closeout file.`
- incomplete: `Closeout handoff is not complete: <plain reason>.`

Raw fields follow the plain-language conclusion for independent rechecking.

### Exit codes

- `0`: report generated, including every incomplete finding;
- `1`: checker itself could not complete because of an unexpected runtime/I/O
  error;
- `2`: invalid CLI usage.

An incomplete handoff must not return non-zero. This preserves report-only,
non-blocking behavior.

## Failure Paths and Risk Points

1. **Receipt from another artifact**: path matching prevents a global-latest
   checksum from producing a false positive.
2. **Closeout edited after processing**: mtime or checksum mismatch produces
   `false`.
3. **Identical content rewritten later**: newer mtime still produces `false`;
   checksum equality alone is insufficient because invocation after the rewrite
   was not observed.
4. **Receipt timestamp missing or timezone-naive**: receipt is invalid for
   freshness selection and remains visible in diagnostics.
5. **Malformed newest receipt**: it cannot erase an older valid receipt, but the
   malformed count must be shown.
6. **Windows path case and separator differences**: matching must use
   platform-aware normalized resolved paths, not raw strings.
7. **Copied files or clock changes**: mtime is a local freshness signal, not
   authorship or causal proof. The checksum and receipt outcome checks reduce,
   but do not eliminate, this evidence limitation.
8. **Receipt says write performed without verified claim**: result remains
   `false`; self-report alone is insufficient.
9. **No closeout file**: result is `false` with
   `closeout_artifact_not_present`; human output must explain that there is no
   closeout handoff to verify, not imply that product work failed.
10. **Unexpected permission error**: checker returns `1` and must not create a
    replacement artifact or silently downgrade to a positive result.

## Evidence Plan

Focused tests must cover:

1. no closeout file -> `false`, reason `closeout_artifact_not_present`, exit 0;
2. closeout file with no receipts -> `false`, exit 0;
3. unrelated receipt path -> ignored, no false positive;
4. non-canonical entrypoint -> ignored;
5. matching receipt older than closeout -> `false`,
   `closeout_newer_than_receipt`;
6. newer matching receipt with changed content -> `false`, checksum mismatch;
7. successful current receipt, no memory write required -> `true`;
8. required memory write not performed -> `false`;
9. performed but unverified memory claim -> `false`;
10. required, performed, and verified -> `true`;
11. malformed and unsupported receipts remain visible in diagnostics;
12. payload timestamp, not filename or receipt-file mtime, selects latest;
13. Windows-equivalent path spelling matches on Windows;
14. two consecutive runs produce identical output aside from no volatile field
    and create no files;
15. human output leads with the plain-language conclusion;
16. JSON output contains the minimum contract fields;
17. invalid CLI usage exits 2; incomplete findings exit 0.

Scope-matched validation for the future implementation:

```powershell
python -m pytest tests/test_processed_closeout_check.py -q
python -m governance_tools.processed_closeout_check --project-root . --format json
git diff --check
```

The existing `tests/test_agent_closeout_receipt.py` should be run as a related
regression check because the new reader depends on its receipt shape. A full
repository regression is not part of this first tranche unless later required
by the commit boundary.

## Claim Ceiling

This tech spec claims only:

- the observed F2 failure shape is distinct from F1 blank evidence;
- current receipt fields are sufficient to design a read-only local check;
- the proposed matching, freshness, outcome, and evidence boundaries;
- the recommended smallest implementation tranche.

It does not claim:

- the checker exists or has run;
- the driver handoff is repaired;
- closeout invocation is guaranteed;
- memory is automatically updated;
- any gate blocks incomplete handoff;
- a fresh receipt proves technical correctness or framework correctness;
- consumers have adopted the checker.

## Implementation Tranche Recommendation

If this spec is approved, authorize exactly one implementation tranche:

```text
DONE = add a standalone report-only processed-closeout checker and focused tests;
when the current closeout file is newer than the latest valid path-matched
canonical receipt, emit closeout_handoff_complete=false and exit 0;
do not write artifacts or memory, do not invoke closeout, and do not change
hooks, schemas, gates, consumers, or blocking behavior.
```

Allowed files:

- `governance_tools/processed_closeout_check.py` (new);
- `tests/test_processed_closeout_check.py` (new).

Commit and push require separate authorization.
