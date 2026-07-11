# Runtime Treatment Census — Session-Index Cache Tranche 4 (2026-07-11)

Status: read-only assessment of the `session_end.py` session-index subfamily.
This document changes no writer, reader, ignore rule, artifact policy, or
closeout authority rule.

## Problem

The prior subfamily map identified `artifacts/session-index.ndjson` as a
non-authoritative cache worth checking. A reader inventory is required before
calling it noise, duplicate output, or a retirement candidate.

## Reader and authority map

| Surface | Relationship to session index | Decision effect evidence | Authority boundary |
| --- | --- | --- | --- |
| `runtime_hooks/core/session_end.py` | Append-only writer; write failure is non-fatal and `--no-ledger-write` can skip it. | Produces cache rows; no independent evidence that the write alone changed a current decision. | Explicitly non-authoritative. Canonical closeout remains the source of truth. |
| `scripts/build_review_projection.py` | Current tracked reader. It counts rows and marks missing/valid sessions in an advisory, non-canonical review projection. | **Decision-relevant, current execution unverified.** Its output can raise reviewer attention, but this tranche found no retained invocation showing a later decision changed because of it. | Declares `advisory_only` and `projection_non_canonical`; an empty/missing index yields `MISSING`, not a fabricated complete result. |
| `governance_tools/round_a_evaluator.py` | Historical tracked reader. It joins ledger entries to session IDs and can set an `expand_ready` rollout result. | **Observed historical use.** It is a genuine readiness-input path, but Round A is historical/frozen and no current use is established. | It evaluates consistency for that experiment; it is not a general closeout authority. |
| `runtime_hooks/core/_canonical_closeout_context.py`, `governance_tools/closeout_audit.py`, `session_start` contract | Deliberate non-readers. | N/A. Their refusal to read it protects the trust boundary. | They must use canonical closeout artifacts, never the cache as a source of truth. |

## Findings

1. **The session index is not readerless.** The earlier “reader absence”
   hypothesis is not reproduced: review projection and Round A evaluator both
   parse it.
2. **It is a cache, not a duplicate canonical closeout.** It carries only a
   compact scan row. Canonical closeouts retain the full validated artifact and
   remain the required authority for runtime/audit consumers.
3. **Its strongest observed effect is historical.** Round A used it as part of
   a rollout-readiness consistency check. That supports `keep_observe`, not a
   current, general decision-effect claim.
4. **Current review-projection value is unproven.** The projection code makes
   the cache human-scannable, but no retained current invocation or reviewer
   decision was found in this tranche.
5. **Documentation-state warning.** The 2026-06-09 dirty-isolation policy says
   Option B implementation is pending, while commit `ffd9609` and current
   `.gitignore` show the ledger was untracked/ignored on 2026-06-18. This is a
   documentation freshness issue, not evidence that writer/reader behavior is
   wrong; no correction is made here.

## Assessment

| Decision effect | Maintenance cost | Duplication | Human comprehensibility | Disposition candidate |
| --- | --- | --- | --- | --- |
| Observed historical input to Round A; current review-projection effect unverified. | Low writer, but policy/readers/docs have drift risk because the artifact is optional and ignored by default. | Not duplicate: cache rows intentionally summarize canonical closeouts, with authority separation. | Raw NDJSON is not operator-readable; the advisory projection is the human layer but its live use is unproven. | `keep_observe`: retain cache semantics and authority prohibition. Do not retire until the review-projection current-use question and Round A historical status are separately dispositioned. |

## Claim ceiling

This tranche does not prove the session index is needed today, that it is safe
to remove, that review projection changes decisions, or that the stale policy
text can be corrected without a separate documentation slice. It does not alter
F-7, closeout correctness, runtime ledger handling, or canonical authority.
