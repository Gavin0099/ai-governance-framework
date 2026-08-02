# Gate 3 Codex Route — Simplification Specification

Status: **draft for independent review**. Not signed, not promoted, not
authorized. This document changes no runtime behavior.

Written 2026-08-02 after canary v6 failed at `packet_build` and Gate 3 was
paused with counted execution at zero.

## Problem

Six authorized live attempts produced six failures. Four stopped because a
different pinned expectation did not match the observed Codex rollout:

| Run | Failure | Kind |
|---|---|---|
| v1 | cleanup residue | setup |
| v2 | rollout must contain one `world_state` | pinned expectation |
| v3 | `route_prepare`, zero sessions | setup |
| v4 | arm A source parse | pinned expectation (wrapper) |
| v5 | arm B source parse | pinned expectation (wrapper) |
| v6 | `originator` differs from frozen context | pinned expectation (context) |

The current route uses literal equality for fields with different scientific
roles. Some values define the experiment, some are environment values that
must remain stable, some need only be balanced within a pair, and some are
arm-specific paths that must be normalized before comparison. Treating all of
them as preparation-time literals creates independent failure paths without
necessarily protecting the comparison.

The correction is not to weaken fail-closed behavior. It is to state the
property each field must protect and enforce that property at the correct
time scope.

## Current repository truth

This specification is based on the following current entrypoints in
`gate3_codex_live_canary.py`:

- `CONTEXT_META_EXPECTED` and `CONTEXT_TURN_EXPECTED` define the current
  literal context expectations.
- `_route_prepare` records the context contract, candidate manifest,
  launcher and pair-runner implementation digests, model/build identity and
  producer Git identity.
- `parse_rollout` validates context before it scans tool-call wrappers. A
  context mismatch therefore prevents the current wrapper census from being
  reached.
- `_normalised_context_view` replaces the expected workspace with the generic
  `WORKSPACE` token for context identity comparison.
- `context_identity` currently includes acceptance policy, base/developer
  instructions, machine context, session metadata, turn context and
  `world_state`.

Canary v6 is retained as a privacy-safe negative result. It does not establish
wrapper conformance because parsing stopped at context identity first. The
runtime error named `originator`, but that exact cause is operator-observed and
cannot be reconstructed from the public receipt.

## Target outcome

Produce a reviewable contract for a future calibration collector and future
route admission in which:

1. every currently consumed identity or validity field has an explicit
   disposition and comparison time scope;
2. the collector can observe all context fields and all wrapper shapes emitted
   in its one session without turning those observations into admission;
3. public evidence is built from a closed, typed allowlist rather than from
   arbitrary observed values; and
4. no value observed during a counted run can become an anchor for that run or
   experiment.

## Scope

This specification covers:

- context and implementation identity consumed by the current Codex live
  route;
- the distinction between study-frozen, calibration-frozen, pair-equal,
  normalized and observational values;
- the non-admitting calibration collector boundary;
- the private/public evidence boundary for calibration; and
- the smallest future implementation tranche.

## Non-goals

This specification does **not**:

- classify `originator` or resolve whether `source` moves with it;
- authorize a calibration session or a pair;
- change a signed contract, candidate manifest, runtime, parser or verifier;
- claim that a probe predicts a later pair will pass;
- make a model-effect claim or begin counted Gate 3 execution; or
- replace the Codex live route with a different producer channel.

## Classification model

Disposition and comparison time scope are separate. Every field below has one
disposition and an explicit scope.

### A. Study-frozen

A literal selected from an authority source other than calibration, such as
the study design, signed candidate or implementation commit. It is signed
before any counted run and must match every session in the experiment.
Differing means a different experiment. Fail closed.

### B. Calibration-frozen

A value learned from an independently authorized, non-counted calibration
session. The owner must explicitly accept it, write it into preregistration and
sign it before any counted run. It then behaves as a literal across the entire
experiment, including when its scientific role is validity-critical. Fail
closed.

This is not merely “cross-arm equal.” It prevents a value from drifting between
pairs after calibration.

### C. Pair-equal

No experiment-wide literal is pinned. Both arms in the same pair must carry
the same canonical value. The value may change between pairs only where the
field’s row explicitly permits it. Every observed value is recorded. Fail
closed on within-pair inequality.

### D. Normalized then compared

Raw values necessarily differ by arm. A signed normalization algorithm first
maps them to a canonical representation, after which the row specifies whether
the result is study-frozen, calibration-frozen or pair-equal. Any unrecognized
path form or normalization collision fails closed.

### E. Observational

The value is recorded through a typed public projection but is not used as an
experimental equality control. Structural integrity requirements may still
apply: for example session IDs must be non-empty and distinct, and timestamps
must be parseable and ordered. The exact values do not decide admission.

### O. Open ruling

The field is inventoried but deliberately unclassified. An open ruling blocks
formal admission changes, candidate rebuilding, pair authorization and counted
execution. It does not block the offline collector or the exact-one calibration
authorization whose evidence is required to resolve the ruling. It is never a
permissive default.

## Complete field coverage

### Study and implementation identity

| Field or artifact | Disposition / scope | Reason |
|---|---|---|
| model | A / experiment | Different model, different experiment. |
| `comp_hash` / model build | A / experiment | Pins the producer build. |
| CLI version | A / experiment | Pins the tool surface. |
| reasoning / effort | A / experiment | Directly shapes producer behavior. |
| model provider | A / experiment | A different provider may imply a different route even under the same model alias. |
| baseline commit and bundle | A / experiment | Starting state. |
| task packet and exact prompt | A / experiment | Task identity. |
| treatment packet and mapping contract | A / experiment | Studied factor. |
| permissions, budget and authorization class | A / experiment | Capability and cost envelope. |
| harness contract and scorer rubric | A / experiment | Measurement instrument. |
| acceptance-policy digest | A / experiment | Defines what the route admits. |
| candidate-manifest identity | A / experiment | Pins the signed preregistration bytes. |
| implementation commit and four-file identity | A / experiment | Pins the committed canary, pair runner, session launcher and focused-test bytes as one verified implementation object. |
| harness implementation digest | A / experiment | Separately binds the live-canary entrypoint published in the summary. |
| launcher implementation digest | A / experiment | Pins session construction. |
| pair-runner implementation digest | A / experiment | Pins pair execution. |
| tests implementation digest | A / experiment | Pins the focused verification surface published with the route. |
| sanitizer schema and rules digest | A / experiment | Defines which private bytes may enter public evidence and how paths are replaced. |
| normalization tokens and replacement-rule identity | A / experiment | Pins `WORKSPACE`, arm public tokens and the exact normalization/sanitization transform; changing them changes identity comparison. |
| route-plan, summary and evidence schema identities | A / experiment | Prevents artifacts produced under a different structural contract from being accepted. |
| credential contract and credential-receipt schema identity | A / experiment | Pins the auth route, cleanup/publication boundary and privacy-safe credential evidence shape without retaining credential material. |
| baseline Git identity | A / experiment | Pins deterministic authorship of the baseline commit independently of the producer output identity. |
| producer Git identity | A / experiment | Pins deterministic synthetic commit attribution. |
| credential auth route | A / experiment | A different auth surface may change session behavior. Credential material itself is never evidence. |

### Session metadata

| Field | Disposition / scope | Reason |
|---|---|---|
| `history_mode` | B / experiment | Behavior-relevant environment value; calibrate, approve, then freeze. |
| `model_provider` | A / experiment | Same authority as the study-level provider row above. |
| `originator` | O | May identify an execution or instruction surface; requires the ruling below. |
| `source` | O | Must be ruled together with `originator`. |
| `thread_source` | B / experiment | May affect conversation construction; calibrate and freeze. |
| session-meta `cwd` | D → pair-equal after normalization | Raw arm paths differ; both must reduce to the signed generic workspace token. |
| session ID | E | Must be non-empty, internally consistent and distinct across arms; exact value is identity only. |
| CLI version | A / experiment | Duplicate observation of the study-frozen CLI identity. |

### Context envelope and record structure

These rows classify list cardinality and ordering separately from the payload
fields above. No full-list equality check may silently choose their scope.

| Envelope or record structure | Disposition / scope | Reason |
|---|---|---|
| session-meta presence and session-ID consistency | A / structural invariant | At least one record is required; all records in one rollout must name the same non-empty session identity. |
| session-meta record count and order | C / pair | Both arms must expose the same count and canonical record ordering; the count may vary between separately authorized pairs and is recorded. |
| turn-context presence | A / structural invariant | At least one turn-context record is required. |
| turn-context record count and order | C / pair | Both arms must expose the same count and canonical order; the published route retains `turn_count`. |
| machine-context message cardinality | A / structural invariant | Exactly one machine-context envelope is required; zero or multiple envelopes fail closed. |
| task-prompt user-message cardinality | A / structural invariant | Exactly one byte-exact frozen task prompt is required and no unmatched user message is allowed. |
| event user-message list | A / structural invariant | The event projection must be exactly the singleton frozen task prompt in canonical order. |
| base-instruction record presence | A / structural invariant | Every session-meta record must carry base instructions; absence fails closed. |
| base-instruction record count and order | C / pair, then B content anchor | Both arms must expose the same canonical list structure; normalized content digests are separately calibration-frozen under the instruction row below. |
| developer-instruction record presence | A / structural invariant | At least one developer-instruction record is required. |
| developer-instruction record count and order | C / pair, then B content anchor | Both arms must expose the same canonical list structure; normalized content digests are separately calibration-frozen. |

### Turn and collaboration context

| Field | Disposition / scope | Reason |
|---|---|---|
| model, `comp_hash`, effort | A / experiment | Duplicate observations of study-frozen producer identity. |
| `approval_policy` | A / experiment | Capability boundary. |
| `approvals_reviewer` | A / experiment | Approval authority affects unattended execution. |
| `permission_profile` | A / experiment | Capability boundary. |
| `sandbox_policy` | A / experiment | Capability boundary. |
| `multi_agent_version` | B / experiment | Changes orchestration semantics; calibrate and freeze. |
| `personality` | B / experiment | Behavior-relevant producer setting; calibrate and freeze. |
| `summary` | B / experiment | May change retained conversational state; calibrate and freeze. |
| `realtime_active` | B / experiment | May change external-state access; calibrate and freeze. |
| `timezone` | B / experiment | Changes date interpretation; calibrate and freeze. |
| `current_date` | C / pair | It enters model context, so it is not identity-only. It must match within a pair but may change between pairs run on different dates. |
| `collaboration_mode.mode` | A / experiment | Changes orchestration behavior. |
| collaboration model and reasoning settings | A / experiment | Must repeat the study-frozen model and reasoning identity. |
| collaboration developer-instruction setting | A / experiment | Presence or absence changes the instruction surface. |
| turn `cwd` and `workspace_roots` | D → pair-equal after normalization | Raw arm paths differ; normalized structure and cardinality must match. |

### Machine context and instructions

| Field or content | Disposition / scope | Reason |
|---|---|---|
| machine `cwd` and `workspace_roots` | D → pair-equal after normalization | Same workspace rule as turn context. |
| machine `current_date` | C / pair | Must equal the turn date and match within the pair. |
| machine `timezone` | B / experiment | Must repeat the calibration-frozen timezone. |
| machine `shell` | A / experiment | The frozen command grammar is PowerShell-specific. |
| machine `permission_profile_type` | A / experiment | Duplicate capability-boundary observation. |
| machine `file_system_type` | A / experiment | Filesystem capability boundary. |
| base instructions | D then B / experiment | Normalize workspace paths, hash exact UTF-8 bytes, approve the digest after calibration, then freeze it. Never publish instruction text. |
| developer instructions | D then B / experiment | Same rule as base instructions. |
| paths inside any instruction or context string | D | Only the exact arm workspace may map to `WORKSPACE`; unknown absolute/device paths fail public projection. |

### World state and wrapper surface

| Field or structure | Disposition / scope | Reason |
|---|---|---|
| `world_state` envelope rules | A / experiment | Exactly one `full=true`; all remaining payloads must be legal object states. These are parser invariants, not learned values. |
| normalized `world_state` payload | D → C / pair | Remove only signed arm-path differences, then require within-pair equality. It may vary between pairs and must be recorded. |
| wrapper admission grammar and accepted tool families | A / experiment | Part of the acceptance-policy digest. |
| wrapper shapes emitted by calibration | E | Census of what one session emitted; absence is not proof that another shape cannot appear. |
| timestamps | E | Must be parseable and preserve ordering; exact values are not comparison controls. |

## Open rulings

1. **`originator`.** If it denotes a different execution surface or different
   instruction source, it is validity-critical. Because the literal used by
   this redesign would be learned from calibration, its disposition is B, not
   A; the owner records the validity rationale when accepting the B anchor. If
   it is only a label, the owner may still choose B for experiment-wide drift
   detection or E if there is evidence that the value cannot affect behavior.
   The calibration evidence exposes its exact value only to the private
   decision artifact, alongside the normalized base-instruction digest.

2. **`source`.** Rule on it together with `originator`; it may describe the
   same execution-surface distinction.

3. **Codex live route.** Simplification does not make the channel cheap. A
   different producer channel would change the research question from “does
   the Skill help real Codex?” and is a separate study decision.

An open ruling blocks changes to formal admission, candidate rebuilding, pair
authorization and counted execution. It does **not** block the offline
collector implementation or the single calibration probe whose evidence is
needed to resolve the ruling.

## Counted-run anchoring prohibition

A value observed during a counted run must never become the anchor for that
run or experiment. All B anchors come from a separately authorized calibration
session, are explicitly accepted by the owner, and enter signed preregistration
before counted execution.

A C value is compared only under its predeclared within-pair rule. Observing it
does not create a new experiment-wide anchor.

## Non-admitting calibration collector

The future probe uses one non-counted session. It requires a separate owner
authorization: `non_counted_codex_calibration_probe_only`, exactly one session,
no replacement. It uses real credentials and is not free merely because it is
not a pair.

The offline collector is **not** `parse_rollout` in a permissive mode. It is a
separate entrypoint with no admission return value and no ability to publish a
success or scorer packet.

It must:

1. load the rollout structurally and record a fixed-vocabulary status for each
   missing or malformed envelope;
2. collect every allowlisted context field without stopping at the first
   mismatch;
3. census every tool-call wrapper emitted in that session even when context
   differs from the current frozen contract;
4. never interpret a collected wrapper as accepted;
5. retain only fixed wrapper classifications, field-name census and counts —
   never command, arguments, path, raw payload or raw output; and
6. build no outcome, scorer packet or success packet.

Collector success means only that this one rollout was structurally observed.
It does not prove wrapper conformance, future emission coverage or pair
admissibility.

## Evidence and privacy contract

### Private decision artifact

The exact observed values needed for the `originator` and `source` rulings are
written only to a current-user-only temporary artifact outside the repository.
It may also contain normalized instruction digests, never instruction text,
credentials, credential digests, commands, arguments, paths or raw rollout.
It is deleted after the owner records the ruling or when the probe fails.

The public receipt must not contain the private artifact path, bytes or digest.

### Public receipt

The public schema is closed. Adding a field requires schema review; unknown
observed fields are represented only by an aggregate count and are never
projected by name or value.

Allowed projections are:

| Public field class | Allowed representation |
|---|---|
| authorization and invocation count | fixed vocabulary and bounded integers |
| cleanup status and residue class | existing fixed vocabulary; no paths |
| model / CLI / component identity already public in signed route | exact signed value |
| boolean context fields | JSON boolean |
| approved enum context fields | value from a field-specific allowlist with bounded UTF-8 length |
| instruction identity | SHA-256 of normalized UTF-8 bytes only |
| path-bearing context | signed token and structural counts only |
| `world_state` | raw/object/full/state counts and fixed parse status only |
| wrappers | fixed wrapper class, tool family, ordinal/count and parse status only |
| open-ruling fields | presence, JSON type and bounded length bucket only; no value or digest |

The receipt contains no arbitrary string projection. `_privacy_violations` is
an additional refusal layer, not the publication authority. Canonical JSON is
assembled in memory, privacy-checked, then create-once published atomically.
Cleanup failure makes the receipt non-scoreable and prevents any success
artifact publication.

## Affected surfaces for a future implementation

Likely affected surfaces, not changes authorized by this document:

- `gate3_codex_live_canary.py`: calibration orchestration, collector, private
  decision artifact and public receipt builder;
- focused tests for structural collection, field coverage, publication
  allowlist, privacy mutations, atomic failure receipt and cleanup;
- the signed Gate 3 amendment and candidate manifest, but only after field
  rulings and independent review; and
- PLAN/memory only at a real phase transition, not during this draft slice.

Formal admission must continue to use the signed `parse_rollout` contract. The
collector must not be imported as an acceptance predicate.

## Boundary and API considerations

- Collector output and admission output are different schemas and types.
- The collector has no “accepted” boolean and no success-packet API.
- Every context field consumed by admission must appear in the coverage table;
  an unclassified new field causes implementation review failure rather than
  defaulting to E.
- Normalization rules are signed implementation identity. Adding a path form
  changes the policy digest.
- Calibration authorization does not authorize a pair. Pair authorization
  remains separate and counted execution remains separately gated.

## Failure paths and risk points

- A collector that reuses admission control flow may stop at the first context
  mismatch and repeat v6.
- Publishing arbitrary observed strings may disclose local or proprietary
  context even when a pattern scanner reports no violation.
- Treating pair-equal values as calibration-frozen can make multi-day pairs
  expire; treating calibration-frozen values as pair-equal can allow harness
  drift.
- A single probe cannot cover wrapper shapes it did not emit.
- Owner selection of B anchors after counted output exists would invalidate
  preregistration.
- Normalization collisions can hide real arm differences and must fail closed.

## Evidence plan

For this documentation slice:

- compare every current context/identity read point listed under “Current
  repository truth” against the coverage tables;
- run `git diff --check`;
- confirm only this specification changed; and
- obtain independent semantic review.

For the first future implementation tranche, before any live session:

- synthetic 0/1/multiple/malformed context records;
- synthetic context mismatch followed by valid and invalid wrappers, proving
  collection continues without admission;
- unknown-field, arbitrary-string, path, command and credential privacy
  mutations;
- canonical and create-once public receipt tests;
- private artifact cleanup on success and every failure stage; and
- a test proving collector output cannot be passed to success-packet
  publication.

## Implementation tranche recommendation

The smallest future tranche is **offline only**:

> Implement the non-admitting collector and closed public projection against
> synthetic rollout fixtures; do not install the CLI, read credentials, start
> a session, modify formal admission or rebuild the signed candidate.

Only after that tranche passes focused tests, governance validation and
independent review may the owner consider authorizing exactly one calibration
session. The required order after offline approval is:

1. owner grants exact-one, no-replacement calibration authorization;
2. the probe produces the private decision artifact and privacy-safe public
   receipt;
3. the owner rules on `originator` and `source` from the private evidence;
4. the accepted anchors and rationales enter a new admission amendment;
5. independent review, exact-byte signature and canonical promotion complete;
6. only then may a separate pair authorization be considered.

## Claim ceiling

This specification may claim only a proposed classification, complete current
field inventory, proposed privacy boundary and recommended offline tranche. It
does not claim that any behavior is implemented or enforced.

## Cannot claim

- That this specification is independently approved, signed or promoted.
- That the collector, schema or privacy boundary exists in runtime.
- That a calibration session is authorized.
- That `originator` or `source` has been classified.
- That one probe covers future wrappers or predicts a pair will pass.
- That Gate 3 may resume or counted execution is anything other than zero.
