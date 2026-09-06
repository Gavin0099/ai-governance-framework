# Solo R2 v2.1 unavailable cost representation amendment candidate

Status: CANDIDATE / NOT REVIEWED / NOT OWNER ADOPTED.
No implementation, terminal append, retry, execution, commit or push authority.

## C01. Problem, current truth and target outcome

An exposed disposable Attempt failed in the harness after a legal file_change
was rejected by the launcher catalog. Its initiated consumption is already
durable; its terminal record is missing. The original elapsed measurement was
not persisted. Zero or a reconstructed duration would assert evidence we lack.
The target is an honest terminal representation for metrics whose measurement
or persistence was preempted by a harness exception, without cost imputation.

Read sources at HEAD a313c01abf5c9d03e3efd6b98a59be285aa37e91:
- governance_tools/solo_attempt_ledger_v2.py: _EVENT_EXTRA_KEYS,
  _REQUIRED_COST_KEYS and _validate_cost_metrics require elapsed_ms/tool_calls
  and non-negative integers, with no terminal failure-class field.
- governance_tools/solo_r2_lifecycle_integration.py: record_terminal,
  prepare_scoring and admission require the existing lifecycle transitions.
- governance_tools/solo_r2_disposable_profile.py binds the adopted v2.1 profile.
- docs/governance/solo-evaluation-execution-contract-revision-2-20260831.md:
  E08 consumption, E09 failure classes/no retry, E10 cost evidence.
- memory/evidence/solo-r2-disposable-launcher-20260906/post-exposure-failure-review.json
  retains the earlier diagnosis and its incomplete historical terminalization.

Observed public ledger prefix SHA-256:
ee51b11bdaa746e6cb338ca6245029563de858653b5062bfeab9ca1c83faf0da.
Four events: V2_GENESIS, PAIR_CREATED, ATTEMPT_ADMITTED, TASK_EXPOSED.
One initiated Attempt is counted. This observation is not an append permission.
Trace inspection was restricted to keys/types, usage and tool inventory, not
arm narrative, patch contents or sealed arm/order information.

## C02. Parent identities and amendment dispatch

Parent v2 ledger schema SHA-256:
d64d9f881a07947b363ef12d2c53e8628dcd4b4dabbf89ba3cbd42f4131d01bb.
Parent protocol SHA-256:
1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff.
Parent execution contract SHA-256:
3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea.
Adopted v2.1 input amendment SHA-256:
ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab.
Its committed locator is a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4:
docs/governance/solo-r2-input-authority-schema-amendment-20260906.md.

Proposed supplemental profile: solo_r2_v2_1_unavailable_cost.v1.
Its exact identity is that name followed by @sha256: and the digest of this
document's separately adopted exact bytes, resolved outside this document.
Owner adoption must explicitly authorize this supplemental interpretation for
the already-existing dedicated disposable ledger, binding its fixed path,
evaluation identity, genesis digest and adoption-time prefix digest. Adoption
must preserve the prior schema_id, genesis, Pair identities and all old bytes.
This is an explicit post-exposure representation amendment, not a claim that
the original preregistration already permitted the new representation.

Only a verified exact owner-adoption record and resolvable adopted amendment
bytes enable supplemental dispatch. A caller flag, event digest alone, document
title, worktree candidate or a self-declared adoption is insufficient.
The adoption record must retain its owner-instruction provenance and limits;
it is not an independently witnessed signature. Its exact identity and locator
must be pinned in the reviewed implementation before any real append.

The ledger schema_version remains solo_attempt_ledger.v2.1. Original numeric
terminal shapes keep their meaning. Supplemental terminals explicitly carry
cost_amendment_sha256, so consumers cannot silently reinterpret the old schema.
Unaware consumers reject the new shape; no fallback or stripping is allowed.
Parent v2 accepts neither the new keys nor sentinel values; its validation is
unchanged. No amendment of original/replacement v2 ledgers is authorized.

E10 already adopts literal UNAVAILABLE for controller evidence; this amendment
extends that existing convention to public v2.1 records for the cases in C03.
For this v2.1 disposable profile only, it narrows E10's public cost representation
and the inherited numeric-only terminal cost rule; all other parent execution-
contract requirements remain unchanged. The owner-adoption record must state
this limited E10 change explicitly. It does not
change what any metric measures, retroactively assert budget compliance, or
modify oracle/correctness/scoring definitions after results.

## C03. Closed terminal representation and eligibility

Existing common fields, EXECUTION_TERMINAL transition, attempt_state=TERMINAL,
correctness_result keys and required cost keys remain required.
The supplemental terminal adds exactly these three keys:
- cost_amendment_sha256: SHA-256 of separately adopted exact amendment bytes.
- terminal_classification: exactly HARNESS_FAILURE.
- unavailable_cost_reasons: nonempty object mapping unavailable metric names
  to exactly MEASUREMENT_PREEMPTED_BY_EXCEPTION.

cost_metrics retains only elapsed_ms, tool_calls, tokens_total, review_rounds;
elapsed_ms and tool_calls remain present. Each present value is a non-negative
integer excluding booleans, or the exact string UNAVAILABLE. The reason-map
key set must equal precisely the sentinel-valued cost key set. All-numeric
terminals use the original shape without supplemental keys. Missing required
metrics, nulls, floats, negative numbers, other strings, unknown keys/reasons,
empty reason maps, reasons attached to integers and partial extensions reject.

Exception eligibility requires controller evidence that a harness exception
interrupted measurement completion or persistence and that the metric cannot
be recovered from retained authoritative observations. An exception or label
alone does not prove absence. Available evidence must be consumed; discarding
it, skipping capture, or preferring a sentinel over a known value is forbidden.
AGENT_FAILURE, SUCCESS and UNCLASSIFIED do not qualify for this extension.
Unknown classification remains unresolved/STOP, not promoted to HARNESS_FAILURE.

The rule applies to the class of interrupted measurements, not a hard-coded
Attempt, digest, seven-call trace or elapsed_ms-only exception. Optional metrics
remain optional as before. Preserve exposed token components in controller
evidence under E10. If an adopted aggregation rule exists and its inputs are
available, record the resulting tokens_total; do not suppress a known total.
Without an adopted aggregation rule, C05 permits omission of that optional
aggregate while retaining all components and the omission reason.
Generic telemetry gaps or unavailable provider features are not covered by
MEASUREMENT_PREEMPTED_BY_EXCEPTION.

Controller-only evidence must bind the ledger prefix, Attempt, retained source
identities, metric extraction and unavailability diagnosis. Public records may
contain only the enum and metrics above, not traces, paths, exception prose,
output references, arm labels or order. Ledger validation proves the declared
shape, not factual unavailability; the reviewed producer must verify evidence.
External factual audit requires separately authorized access to that evidence.

## C04. Honest consumption and correctness boundaries

UNAVAILABLE never becomes zero, an estimated number, a dropped zero-weight
sample or an implicitly passing cost/budget check. Totals, averages, deltas,
ratios and comparisons depending on an unavailable metric propagate UNAVAILABLE.
Known independent metrics may be reported individually with completeness stated.
Unsupported downstream consumers stop rather than coercing or excluding values.
The implementation review must identify actual consumers; this candidate does
not claim downstream handling already exists or authorize new reporting systems.

HARNESS_FAILURE is execution classification, not evidence that the solution is
incorrect or correct. Preserve independent correctness fields honestly: without
oracle execution use NOT_RUN, retain the frozen required-case count, record no
passed cases, and keep unevaluated regression/scope as NOT_EVALUATED. Zero
recorded passed cases does not assert that all cases were executed and failed.
Terminalization does not imply report readiness, successful result sealing,
blind scoring admissibility or a complete A/B result.

## C05. Historical applicability and optional token aggregate

For the observed failure, tool_calls=7 is supported by six command_execution
events and one file_change. elapsed_ms is UNAVAILABLE: retained trace keys have
no time fields and original monotonic timing is lost. Do not use file mtimes,
the 1800-second limit, token counts, event counts or a rerun to manufacture it.

Retained turn.completed usage contains exact observations:
input_tokens=119407; cached_input_tokens=101248; cache_write_input_tokens=0;
output_tokens=2422; reasoning_output_tokens=807.
These raw component counts are available; no adopted aggregation rule has been
established for this total. Preserve every component, including the observed
cache_write_input_tokens=0, in controller evidence. Omit optional tokens_total
from the public terminal and record NO_ADOPTED_AGGREGATION_RULE as its omission
reason in controller evidence, not as a new public field or exception reason.
This omission does not block terminalization. It neither marks the available
components UNAVAILABLE nor invents an aggregate. Do not estimate, sum overlapping
components, or research provider semantics as a prerequisite to this closure.
The total must be resolved before emission only when an adopted aggregation
rule exists; if it yields an available value, C03 requires that value.
An omitted aggregate is not zero and cannot support numeric cost comparisons.

Historical append requires a separate exact owner authorization after adoption,
implementation, tests and review. It must bind the existing ledger/genesis/Pair,
target exposed handle, exact unchanged prefix and proposed terminal content.
Append exactly once through the durable validated ledger path, retaining the
prefix byte-for-byte. Recheck prefix/state immediately before append. On any
uncertain write/fsync result, inspect state; do not blindly append a duplicate.
Terminal timestamp is the actual append time, never a guessed execution end.
No deleted/replaced events, trace rewriting, count reset or exposure rollback.

Historical closure must not synthesize a lost live controller object, resume
execution, or pretend the missing formal output sealing is complete. Preserve
controller custody and existing raw outputs. Any later sealing requires its
own evidence of valid retained output custody; a terminal line is insufficient.
Neither remaining slot capacity nor TERMINAL grants retry/replacement. No new
Pair may bypass E09/E12. Attempt #2 remains separately undecided and unauthorized.
The owner-adoption record must state: this disposable mechanism-shakedown
evaluation does not constitute or replace the E12 qualification shakedown,
and does not authorize A1-A6 progression.

## C06. Affected surfaces, evidence plan and implementation tranche

Current slice allowlist: this candidate and canonical memory/evidence only.
Proposed later minimal implementation surfaces and direct dependencies:
- solo_attempt_ledger_v2.py: v2.1-only supplemental shape validation/dispatch.
- solo_r2_disposable_profile.py and solo_r2_disposable_binding.py: exact adopted
  supplemental authority resolution without rebinding the existing genesis.
- solo_r2_lifecycle_integration.py: preserve the terminal extension through its
  existing append boundary, keeping numeric v2 behavior and single-terminal rules.
- solo_r2_disposable_execution.py: evidence-backed failure metrics/classification;
  reuse the already-written failure fix rather than restarting that engineering.
- Direct tests for those consumers; additional consumers require a demonstrated
  dependency before expanding the implementation allowlist.

Positive evidence must show a synthetic exposed harness failure with one lost
measurement, available metrics preserved, exactly one terminal and unchanged
initiated count. Exercise another metric lost to the same exception class to
prove the rule is not keyed to this historical Attempt. Preserve numeric v2
and v2.1 behavior. Negative evidence must cover every C03 shape/type/class/reason
rejection, available-but-marked-unavailable evidence, missing/wrong adoption,
wrong ledger/genesis/prefix/amendment binding, duplicate terminal, and attempted
numeric coercion or comparison of UNAVAILABLE. Verify uncertainty on append
does not authorize retry, and public output stays arm/order invariant.
Verify optional tokens_total omission with retained components and
NO_ADOPTED_AGGREGATION_RULE does not block terminalization, while suppression
of a known total under an adopted aggregation rule is rejected.

The proposal-time same-source architecture preview reported medium risk and
review-required. It is only an affected-surface preview, not validation of an
unwritten diff. No runtime tests or qualification rerun are required to draft.

R1 baseline correction: commit 0a01efe2e0752db953523cca8995b0172b09fb1f
refreshed the prior integration. All seven current _SOURCE_BINDINGS hashes
were independently recomputed and match. This is a fingerprint observation,
not a new full R1 conformance run. A later committed bound-module change creates
a NEW refresh obligation, to be completed against final committed bytes in a
separate refresh commit; do not describe the previously cleared debt as unpaid.

## C07. Claim ceiling, non-goals and stop

Claim ceiling: candidate representation, observed current facts and proposed
validation only; NON_COUNTED / SOLO_CONTROLLED / MECHANISM_SHAKEDOWN_ONLY.
No claim of accepted amendment, implemented enforcement, terminal completion,
Skill effectiveness, Formal/counted evidence or production execution readiness.
No allocation/placement redesign, frozen-input edits, new ledger/Pair, retry,
generic cost/error framework, durable resume, R1 refresh, pressure cleanup,
oracle/scoring/unblinding, qualification rerun, commit or push in this slice.

Sequence: exact candidate review -> separate exact owner adoption/local commit
-> separately authorized minimal implementation/tests/review -> separately
authorized historical terminal append. Stop now at candidate identity delivery.
Open prerequisites: owner adoption/activation binding, implementation conformance
and exact historical append authority. Provider token semantics are not an
additional closure prerequisite under the C05 optional-aggregate omission.
