# Session-binding retryable state machine — tech spec (2026-08-06)

> Status: **Tranche 1 implemented 2026-08-06 (structural axis only); not
> committed, not pushed.** Owner approved Option A and the review approved the
> structural-only scope. Tranches 1b / 2 / 3 remain unstarted.
> Baseline: `main = 0e99bd18`. All code references verified against this commit.
> **Revision 4.** Changes from r3: probed `candidate_generated_at_missing`
> (the last unmeasured structural row) and removed an evidence-plan command that
> was neither runnable as written nor relevant to this change.
> r3 changes retained: corrected Option A cost premise (the canonical writer
> already de-duplicates), attempt artifact withdrawn as unadmitted telemetry,
> error-path summary limited to probed rows.

## Problem

`run_session_end` treats a **recoverable** session-binding rejection as a
**terminal** event. When binding fails, the run still writes the canonical
closeout *and* the closeout completion marker, and the completion marker is
what makes a session id permanently unusable.

### Error-path inventory — five probed, one derived

Produced by a throwaway probe on `0e99bd18` (since removed). `MARKER` is the
consumption record; `retry` re-runs the **same** session id after correcting
the input.

| case | binding status | axis | `ok` | canonical | **MARKER** | daily memory | retry outcome | source |
|---|---|---|---|---|---|---|---|---|
| no envelope | `session_envelope_missing` | structural | True | written | **written** | `written` | `already_consumed` | probed |
| no candidate | `session_candidate_missing` | structural | True | written | **written** | `already_present` | `already_consumed` | probed |
| candidate owns another id | `session_candidate_mismatch` | structural | True | written | **written** | `already_present` | `already_consumed` | probed |
| candidate predates start | `candidate_before_session_start` | structural | True | written | **written** | `already_present` | `already_consumed` | probed |
| success control | `valid` | structural | True | written | written | `written` | `already_consumed` | probed |
| missing `generated_at` | `candidate_generated_at_missing` | structural | True | written | **written** | `written` | `already_consumed` | probed |
| second run of a consumed id | `already_consumed` | structural | — | not written | not written | not attempted | terminal | probed via the retry column |
| closeout text ≠ candidate | `session_candidate_content_mismatch` | **content (hook only)** | — | — | **written** | — | `already_consumed` | **derived**, probe required before Tranche 1b |

**Summary limited to what was probed:** all **five** structural rejection modes
were probed, and all five consume the session id, write the completion marker,
and report `ok=True` at the library layer; the same id then returns
`already_consumed` forever. The structural axis is therefore fully measured.
The remaining failure mode — `session_candidate_content_mismatch` on the content
axis — is derived from the call chain and must be probed before Tranche 1b, the
tranche that depends on it.

The `daily memory` column shows the canonical writer's de-duplication in action
— see the Option A analysis below. Revision 2 dismissed these values as a probe
artifact; that was wrong. They are real evidence.

### Code path

Line numbers in this subsection are **baseline `0e99bd18`, i.e. the defect as it
stood before Tranche 1**. They are deliberately not re-pointed at the current
tree, because the point of the subsection is what the code looked like when the
defect was diagnosed. Post-change locations: `write_canonical_closeout` is now
at `session_end.py:1258` and the guarded `write_closeout_completion_marker` at
`session_end.py:1347`.

All unguarded by binding validity:

- [runtime_hooks/core/session_end.py#L982](../runtime_hooks/core/session_end.py#L982)
  — binding failure appends a warning and downgrades the decision, then
  **falls through**.
- [runtime_hooks/core/session_end.py#L1243](../runtime_hooks/core/session_end.py#L1243)
  — `write_canonical_closeout(...)`.
- [runtime_hooks/core/session_end.py#L1307](../runtime_hooks/core/session_end.py#L1307)
  — `write_closeout_completion_marker(...)`, the consumption record.

There is no `binding_valid` guard anywhere after line 1200.

### The eighth failure mode — a second binding axis the library cannot see

There are **two** binding axes, assessed in different places:

| axis | assessed by | statuses |
|---|---|---|
| structural | `assess_session_closeout_binding` in the library | the seven in the table above |
| **content** | `_assess_candidate_content_binding` in the **hook only** | `session_candidate_content_mismatch` |

The content axis is defined at
[governance_tools/session_end_hook.py#L1810](../governance_tools/session_end_hook.py#L1810)
and returns `session_candidate_content_mismatch` with a `mismatched_fields`
list ([#L1838](../governance_tools/session_end_hook.py#L1838)). It runs at
[#L1936](../governance_tools/session_end_hook.py#L1936) **only when the
structural binding is already valid**.

The consequence, derived by reading the call chain (**not probed** — see the
evidence plan):

1. Hook detects the content mismatch, sets `pre_binding_status`, and builds a
   fail-closed classification at
   [#L1945](../governance_tools/session_end_hook.py#L1945).
2. Hook nonetheless calls `run_session_end` at
   [#L1995](../governance_tools/session_end_hook.py#L1995).
3. The library re-assesses **only the structural axis**, which is `valid`, so
   `binding_valid` is `True`, the full success path runs, and the completion
   marker is written.

**This defeats the Tranche 1 guard as originally scoped.** Guarding on the
library's own binding status cannot help a case the library classifies as valid.

### Why this is a defect and not a policy choice

The framework already distinguishes "attempt" from "consumption" — for a
*different* failure class.
[tests/test_runtime_session_end.py#L83](../tests/test_runtime_session_end.py#L83)
pins exactly the desired invariant: when artifact emission fails, the canonical
closeout exists but the completion marker does **not**, and re-running the same
session id succeeds. The test is even named `retry-after-partial-emission`.

Binding rejection does not get that treatment. The framework's own remediation
guidance encodes the workaround:

> "Create a fresh session envelope and session-bound closeout candidate before
> ending the session."
> — [governance_tools/session_end_hook.py#L777](../governance_tools/session_end_hook.py#L777)

That guidance is why the observed consumer cost is real rather than theoretical:
the Zephyr adoption log burned roughly five session ids in sequence, each cycle
costing a fresh envelope, a fresh candidate, and another agent round.

### Layer difference

- **Hook layer**: the pre-check pulls `ok` down via
  `closeout_status = STALE_OR_MISMATCHED`, so the operator is told something
  failed — and the id is consumed anyway.
- **Library layer**: `ok=True` on every probed rejection.

## Target outcome

A session id is consumed **only** when a closeout actually succeeded. A
recoverable binding rejection leaves the id reusable.

Binding rejection remains **fail-closed**: nothing promoted, no snapshot, no
completion claimed. Retryable is not permissive.

## Owner decision — resolved: Option A, approved 2026-08-06

> **Decision:** the owner explicitly approved **Option A** on 2026-08-06.
> Binding rejections continue to write the daily memory record; no pinned test
> changes and no memory-authority behavior changes enter Tranche 1.
> The analysis that led to this decision is retained below.


[tests/test_runtime_session_end.py#L181](../tests/test_runtime_session_end.py#L181)
pins that a binding rejection **writes a `FAIL_CLOSED_CLOSEOUT_STALE_OR_MISMATCHED`
record into canonical daily memory**.

### Corrected cost analysis — the writer already de-duplicates

Revision 2 claimed each retry appends another near-identical record. That was
wrong. Verified on `0e99bd18`:

- `_RECORD_IDENTITY_FIELDS` is
  `(record_format_version, memory_type, writer, commit_hash, test_evidence, next_step)`
  — [governance_tools/memory_record.py#L54](../governance_tools/memory_record.py#L54).
  It contains **neither `session_id` nor `what_changed`**.
- An equivalent record returns `already_present` instead of appending —
  [#L220](../governance_tools/memory_record.py#L220).
- Focused test `test_outcome_distinguishes_written_from_already_present`
  asserts identical `record_identity` → `ALREADY_PRESENT`: **2 passed**.
- The probe table above shows `already_present` on three of five rejections,
  which is this mechanism, observed.

**Actual cost:** retries on the same day, same commit, with the same
`test_evidence` and `next_step` de-duplicate to a single record. A new record
appears only when the day, the commit, or the failure evidence / next step
actually changes — which is information worth keeping.

| option | behavior | cost after correction |
|---|---|---|
| **A (recommended)** | keep writing the memory record per attempt | no test change, no memory-authority change; real noise is **lower than r2 stated** because equivalent same-day retries de-duplicate |
| B | attempt evidence only; canonical memory on terminal states | changes a pinned test **and** memory-authority behavior, to solve noise that largely does not occur |
| C | memory on first rejection per id, then suppress | most logic, most edge cases, duplicates what the writer already does |

**Recommendation: A.** It keeps Tranche 1 free of any memory-authority change,
and the de-duplication the writer already performs handles the noise case that
motivated B and C.

**Resolved:** the owner selected A explicitly on 2026-08-06. Tranche 1 is no
longer blocked on this question; it now waits only on the final short review.

The tests at [#L551](../tests/test_runtime_session_end.py#L551) and
[#L571](../tests/test_runtime_session_end.py#L571) drive
`observed_closeout_status` (closeout-text axis) and are **not** affected by this
choice. Only the binding-axis assertion at `#L181` is.

## Scope

1. Classify each structural binding status as terminal or recoverable.
2. On a recoverable rejection, do not write the completion marker.
3. Regression tests pinning retryability, mirroring the partial-emission test.

That is the whole of Tranche 1. Nothing is added.

Classification (from
[runtime_hooks/core/_canonical_closeout.py#L201](../runtime_hooks/core/_canonical_closeout.py#L201)):

| status | class |
|---|---|
| `valid` | terminal — consume |
| `already_consumed` | terminal — no side effects |
| `session_envelope_missing` | recoverable |
| `session_candidate_missing` | recoverable |
| `session_candidate_mismatch` | recoverable |
| `candidate_generated_at_missing` | recoverable |
| `candidate_before_session_start` | recoverable |
| `session_candidate_content_mismatch` | recoverable — **content axis, out of Tranche 1** |

## Non-goals

- **Not** changing `already_consumed` semantics. Consume-once stays.
- **Not** changing the closeout *text* evaluation axis (`closeout_status`).
- **Not** changing gate policy, `hook_coverage_tier`, or any gate verdict.
- **Not** making binding advisory. Fail-closed is retained.
- **Not** an early return — that would discard the fail-closed record the
  framework currently produces.
- **Not** adding any new artifact, schema, telemetry, or CLI. See below.
- **Not** touching consumer repos or re-pinning any submodule.
- **Not** claiming this improves agent behavior or delivery outcomes; posture
  remains audit-first per
  [governance/ARCHITECTURE.md#L54](../governance/ARCHITECTURE.md#L54).

## Withdrawn from this spec: the per-attempt diagnostic artifact

Revision 2 proposed `artifacts/runtime/closeout-attempts/<session_id>/*.json`
with a data contract. **Withdrawn.** Reasons, in order of weight:

1. **No admission evidence.** The canonical closeout, verdict artifact, trace
   artifact, and daily memory record already survive a rejected attempt. No
   observed failure shows that the absence of a separate per-attempt JSON caused
   a wrong decision. Adding it would be new telemetry justified by anticipated
   rather than observed need — exactly what the tool admission stop rule at
   [memory/00_long_term.md#L282](../memory/00_long_term.md#L282) excludes.
2. **The proposed contract was internally unsafe.** A 6-hex suffix is ~16.7M
   combinations, not collision-proof; and `.tmp` + `replace()` on a colliding
   `attempt_id` silently **overwrites**, contradicting the same contract's
   "append-only, never overwritten".
3. **"Durable" was unqualified and wrong.** `artifacts/runtime/` is git-ignored
   (`git check-ignore` matches `**/artifacts/runtime/`), so such files are
   repo-local runtime evidence only and never reach a commit.

If rejection history is later observed to be lost in a way that changes a real
decision, that becomes its own admission case with its own spec. It would then
need exclusive-create (`O_EXCL`) plus collision retry rather than
`replace()`, and must declare local-only durability explicitly.

## Affected surfaces

| surface | tranche | change |
|---|---|---|
| `runtime_hooks/core/session_end.py` | 1 | terminal-state decision computed once; completion-marker write guarded |
| `runtime_hooks/core/_canonical_closeout.py` | 1 | status→class map |
| `tests/test_runtime_session_end.py` | 1 | new retryability regression |
| `governance_tools/session_end_hook.py` | 1b | pass content-axis classification down |

Untouched: gate policy loading, artifact ingestion, claim enforcement, memory
authority guard, census, evidence roots, and the artifact tree.

## Boundary and API considerations

- **Return-shape change is additive, and scoped to enforcement mode.** The new
  `session_binding.class` key is written **only when `enforce_session_binding`
  is true**; it removes nothing. Non-enforcing callers keep a byte-identical
  payload (`status` = `not_enforced`, `session_id`) with no `class` key at all —
  `not_enforced` is a sentinel, not a rejection, so no class literal describes
  it and classifying it would falsely report `recoverable`. Pinned by
  `test_non_enforced_session_binding_payload_is_unchanged`. Status strings are
  unchanged, so `processed_closeout_check` and the hook's `already_consumed`
  branch keep working.
- **`ok` semantics at the library layer** — every probed rejection returns
  `ok=True`. Changing that is correct but alters a library contract; Tranche 3.
- **Consumption record remains a single authority.** The completion marker stays
  the only thing meaning "consumed".
- **Pre-existing weakness, deliberately not fixed:**
  [`_read_valid_closeout_completion`](../runtime_hooks/core/_canonical_closeout.py#L450)
  returns `None` when any listed required artifact no longer exists — deleting
  artifacts silently un-consumes a session. Separate authority question.

## Failure paths and risk points

1. **Early return would lose fail-closed evidence.** Returning at line 982 would
   skip the verdict artifact, trace artifact, and daily memory record. Correct
   shape: one terminal-state decision computed early, with only the *marker
   write* guarded.
2. **Silent non-consumption is the inverse failure.** Too broad a guard and
   consume-once is lost. [tests#L312](../tests/test_runtime_session_end.py#L312)
   must keep passing **unmodified**.
3. **The eighth mode can produce a false "fixed" claim.** Mitigated by the DONE
   narrowing below.
4. **Concurrency unchanged.** The marker write is already atomic. No new race is
   introduced and none is fixed.

## Risk and authority per tranche

Repo rule: any change to `governance_tools/session_end_hook.py` is **HIGH**
([AGENTS.md#L262](../AGENTS.md#L262)). `runtime_hooks/core/session_end.py` is not
named in that list.

| tranche | files | risk | authority | must-test surface |
|---|---|---|---|---|
| 1 | `session_end.py`, `_canonical_closeout.py`, tests | MEDIUM (estimator, provisional) | owner approval of the memory option | `test_runtime_session_end.py` full file; consume-once test unmodified |
| 1b | + `session_end_hook.py` | **HIGH** per AGENTS.md#L262 | explicit owner approval; **separate review verdict, not merged with T1** | hook closeout/gate suite + Tranche 1 surface |
| 2 | memory-record policy | MEDIUM–HIGH (memory authority) | owner decision A/B/C | memory authority guard, daily memory tests |
| 3 | `ok` semantics + unify both assessments | **HIGH** | own spec and review | full runtime + hook suites |

Estimator output for Tranche 1 (provisional — touched files are this spec's own
estimate, not a measured diff):

```
recommended_risk=medium
recommended_oversight=review-required
concerns=error-path-coverage-required
required_evidence=architecture-review,regression-evidence,interface-stability-evidence,
                  cleanup-or-rollback-evidence,error-path-inventory,error-behavior-diff
```

## Evidence plan

**Prerequisite probes:**

| gap | probe | state |
|---|---|---|
| `candidate_generated_at_missing` behavior | library-level probe mirroring the other rows | **done** — result in the inventory above; behaves identically to the other four |
| `session_candidate_content_mismatch` behavior | **hook-level end-to-end** probe | **outstanding** — baseline for the HIGH-risk 1b pass-down; required before 1b is designed, not required for Tranche 1 |

**Implementation evidence:**

| claim | command |
|---|---|
| existing behavior unbroken | `python -X utf8 -m pytest tests/test_runtime_session_end.py -q --basetemp .tmp_sb` (baseline: 31 passed) |
| retryability restored | new test mirroring `test_failed_artifact_emission_does_not_mark_session_consumed` |
| consume-once intact | `test_session_end_consumes_each_bound_session_once` passes **unmodified** |
| memory behavior unchanged | `python -X utf8 -m pytest tests/test_memory_record.py -q` (dedupe baseline: 2 passed on the focused selection) |
| fail-closed regression | `python -X utf8 -m governance_tools.canonical_closeout_fail_closed_regression` — **module form is required**; the script path form raises `ModuleNotFoundError: runtime_hooks`, and a `PYTHONPATH=.` prefix fixes that only in Git Bash (PowerShell, this repo's default shell, rejects it). The module form is shell-neutral and exits 0 |
| runtime gate | `scripts/run-runtime-governance.sh --mode enforce` (Git Bash) |
| error-behavior diff | re-run the inventory probe; diff against the table above |

Deliberately **not** listed: `claim_enforcement_receipt_writer.py`. Revision 3
included it as a "durable receipt" row. It requires `--session-id` and fails
bare, and what it writes is a CE-1B claim-enforcement receipt, which cannot
evidence that a structural binding rejection became retryable. Adding an
unrelated receipt to this evidence plan would blur the same claim ceiling the
withdrawn attempt artifact was blurring.

### Error-behavior diff — measured after Tranche 1

Same probe shape as the inventory above, re-run against the implemented change.
`MARKER` is sampled **after the rejecting run and before any retry**.

| status | class | canonical | **MARKER** | retry outcome |
|---|---|---|---|---|
| `session_envelope_missing` | recoverable | written | **not written** | still `session_envelope_missing` — the retry corrected only the candidate, never created an envelope; correct |
| `session_candidate_missing` | recoverable | written | **not written** | **`valid`** |
| `session_candidate_mismatch` | recoverable | written | **not written** | **`valid`** |
| `candidate_generated_at_missing` | recoverable | written | **not written** | **`valid`** |
| `candidate_before_session_start` | recoverable | written | **not written** | **`valid`** |
| `valid` | terminal | written | written | `already_consumed` — consume-once intact |

Before the change every one of these rows wrote the marker and returned
`already_consumed` on retry. Attempt evidence is unchanged: the canonical
closeout is still written in every case, and the daily memory record still
follows Option A.

Claim ceiling: PASS proves the state machine behaves as specified **in this
repo's tests**. It does not prove reduced consumer cost — that needs a replay in
a real consumer (Zephyr is the originating case) per the consumer-driven loop in
[memory/00_long_term.md#L225](../memory/00_long_term.md#L225).

## Implementation tranche recommendation

**Tranche 1 — owner-approved on the memory question; awaiting final review**

- Status→class map in `_canonical_closeout`, with exactly the two class
  literals defined in the classification table: `terminal` and `recoverable`.
- Guard `write_closeout_completion_marker` on the existing `binding_valid`,
  whose definition is already
  `not enforce_session_binding or binding_status == "valid"`. The class map is
  reported in the result payload; it is **not** the marker condition. Using
  `binding_valid` keeps non-enforcing callers behaving exactly as today.
- Nothing else changes — no new artifact, no memory change (option A).
- New regression test for retry-after-binding-rejection.

**DONE for Tranche 1 is explicitly narrowed to the structural axis.** It must be
reported as "structural binding rejections are retryable", never as "binding
rejections are retryable". Content-axis sessions still burn ids until 1b.

**Tranche 1b — content-axis pass-down (HIGH, separate review verdict)**

Carry the hook's content classification into the library. Requires the
hook-level probe above as its baseline. Must not share a review verdict with
Tranche 1.

**Tranche 2 — memory policy.** Only if a consumer replay shows real noise the
existing de-duplication does not handle.

**Tranche 3 — `ok` semantics and single source of truth.** Own spec, own review.

Do not bundle tranches. Tranche 1 is reviewable in isolation and reversible.
