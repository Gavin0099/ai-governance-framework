# Gate 3 Actual Capture Adapter Design Candidate

Status: merged design-only candidate under remediation; not accepted or implemented

Date: 2026-08-13

Scope: future Codex `exec --json` stdout capture adapter and privacy-safe public
lifecycle projection

## Problem

The consumed Gate 3 pair ended `NON_SUCCESS`: both arms exited zero, no final
message was captured, and the calibrated workspace remained unchanged. The
committed public evidence can establish task-execution failure, but it cannot
separate a complete CLI event lifecycle from an adapter/capture failure because
the raw NDJSON event types were not published.

The repository now has an independently approved synthetic classifier and a
synthetic retained-evidence integration. It does not yet define how a future
real Codex process adapter may read private `exec --json` stdout and emit only
the content-free lifecycle facts needed by that classifier. Without a narrow
adapter contract, a later implementation could leak message, reasoning, tool,
path, identifier or usage data; silently accept a changed CLI event vocabulary;
or overstate an `agent_message` event as proof of a final model completion.

This candidate defines that missing boundary. It does not authorize execution.

## Current Repository Truth

1. `gate3_route_v2_codex.py` pins `codex-cli 0.146.0` and invokes
   `codex exec --json --ephemeral --output-last-message ...` through
   `CodexExecRunner`.
2. `_run_contained` captures child stdout and stderr as private bytes, enforces a
   timeout, terminates the process tree and returns only after `communicate()`
   has completed.
3. `CodexExecRunner.__call__` currently observes process exit, reads the final
   output path and reads the calibrated workspace. It does not parse stdout
   lifecycle events.
4. `gate3_final_message_diagnostic.py` has a synthetic closed projection over
   `turn.started`, `item.started`, `item.completed`, `turn.completed` and
   `turn.failed`. Its synthetic raw fixtures deliberately omit real message,
   reasoning and tool content.
5. `gate3_final_message_diagnostic_integration.py` implements retained
   lifecycle fixtures, create-once publication, seal/cleanup/receipt chains,
   route and external recovery profiles, a privacy verifier, and fail-closed
   crash/TOCTOU behavior. It is synthetic and offline only.
6. The accepted integration design permits only content-free public markers and
   the positive claim `CAPTURED_BYTE_SET_RECONSTRUCTED`. It forbids public live
   content, user-controlled private bytes and digests of those bytes.
7. Current official Codex material describes the `exec --json` envelope family
   as `thread.started`, `turn.started`, `item.*`, `turn.completed`,
   `turn.failed` and `error`. It also shows that `agent_message` content can be
   emitted without a phase that distinguishes commentary from final answer.
   This material is corroborating context, not the pinned 0.146.0 wire
   authority. The future adapter must use reviewed retained conformance fixtures
   for the exact pinned command contract.
8. GitHub MR #52 merged the Gate 3 branch head `4f18556421124cc31f9db54a8b7aceb13cc5efe7`
   into `origin/main` through merge commit
   `a1ac299928f52c51a69aafe996f23cb1bfcf8c4e`. That merge carried this
   design-only candidate into mainline history but did not accept its semantics
   or authorize implementation. Independent review of merged candidate digest
   `b67109816a2631ef0499775b4e86e42afc277b25118c5a6995a2b239fcd1cd76`
   requested the bounded remediation recorded in this revision.

## Target Outcome

Produce a reviewable contract for a future adapter that:

1. receives private stdout bytes only from the exact contained process result;
2. validates a pinned NDJSON envelope contract;
3. discards all content-bearing fields without serializing, hashing or logging
   them;
4. emits a canonical content-free lifecycle projection plus a closed capture
   result;
5. binds that result into the existing pre-cleanup seal and final receipt chain;
6. fails closed on incomplete capture, unknown top-level lifecycle semantics,
   malformed framing, contract drift, publication collision or crash; and
7. never upgrades an observed event into a model-effect or final-answer claim.

## DONE Condition for a Later Offline Implementation Tranche

`DONE = Using retained synthetic and reviewed conformance fixtures only, the
actual-capture adapter core converts the pinned Codex NDJSON envelope subset into
the canonical privacy-safe lifecycle projection; malformed, incomplete,
unknown, content-leaking, crash and publication-collision cases fail closed in
focused offline tests.`

This DONE condition is a recommendation, not current implementation authority.

## Scope

### In scope for this candidate

- Exact component and data-flow boundaries.
- A pinned raw-envelope admission contract.
- Private parsing and public projection rules.
- Public schemas and closed result codes.
- Binding to the existing observation seal, cleanup and receipt sequence.
- Crash, TOCTOU, privacy and mutation-sensitive evidence plans.
- One smallest offline implementation tranche.
- Branch/MR sequencing guidance.

### Explicit non-goals and prohibitions

- No credentials or credential reads.
- No Codex executable invocation, model call or network call.
- No preflight or zero-session probe.
- No live execution, counted execution or non-counted execution.
- No reuse, retry, replacement, repair or reinterpretation of the consumed pair.
- No reading or deriving facts from the three unrelated untracked evidence
  paths in the workspace.
- No modification of `gate3_route_v2_codex.py`, live runners, manifests, owner
  pins, promotion state, evidence commits, `PLAN.md` or memory in this slice.
- No implementation, staging, commit, push or MR creation without separate
  authorization.
- No storage of raw stdout/stderr, prompts, final message content, reasoning,
  tool arguments/results, environment values, credentials, paths, thread IDs,
  item IDs, model IDs, token usage or timestamps in public evidence.
- No raw-private-byte digest, because such a digest can become a correlation or
  dictionary oracle.
- No claim that an `agent_message` event is the model's final answer.
- No treatment, Skill, model, adapter, CLI, task or framework effectiveness
  inference.

## Architecture and Responsibility Boundaries

| Component | Layer | Responsibility | Must not do |
| --- | --- | --- | --- |
| contained process runner | Infrastructure | execute the already-authorized exact command and return private stdout/stderr plus closed process disposition | parse or publish diagnostic semantics |
| raw-envelope parser | Adapter/ACL | validate private NDJSON framing and extract only admitted discriminants | retain, hash, log or return content-bearing fields |
| lifecycle projector | Application/pure | map admitted discriminants to canonical content-free markers | read files, launch processes or infer model intent |
| capture publisher | Infrastructure | create-once publish contract, authorization, result and projection bytes | retry, overwrite or synthesize missing results |
| diagnostic classifier | Domain/pure | combine internally linked adapter reports with existing public axes under the claim ceiling | inspect private bytes or infer unobserved effects |
| retained-package verifier | Application/pure plus read-only adapter | reconstruct canonical public bytes, links, profiles and privacy rules | authenticate the original private stdout or execution environment |

The raw-envelope parser is an Anti-Corruption Layer. Codex wire objects are an
external, versioned model containing private and unstable fields. Domain code
must receive only the stable public marker vocabulary.

## Proposed Data Flow

```text
exact contained process result
        |
        | private stdout bytes; stderr never parsed
        v
raw-envelope parser / privacy ACL
        |
        | admitted discriminants only
        v
pure lifecycle projector
        |
        | canonical content-free projection
        v
create-once capture result + pre-cleanup observation seal
        |
        v
existing cleanup -> receipt -> finalization chain
```

Raw stdout exists only in the private process result and parser call frame. The
design does not claim secure erasure from managed memory. It requires that no
raw stream, raw line, raw object, exception rendering, digest or substring be
written to retained/public artifacts or normal logs.

## Exact Command and Contract Binding

The future capture authorization must bind:

- exact executable SHA-256 from a separately authorized fresh receipt;
- exact command-contract SHA-256;
- exact adapter source SHA-256;
- exact raw-envelope-contract SHA-256;
- exact lifecycle-projector SHA-256;
- exact public schema SHA-256 values;
- action SHA-256 and arm token from the future action descriptor; and
- `capture_ordinal = 1`, `retry = false`, `replacement = false`.

This design does not supply or measure those future live values. A mismatch is
`CAPTURE_CONTRACT_MISMATCH`, and the process must not be launched under that
authorization.

## Raw NDJSON Admission Contract

### Framing

- Input is non-empty bytes returned as stdout by the exact contained process.
- UTF-8 decoding is strict.
- Each event is one JSON object terminated by exactly one LF; CRLF, empty lines,
  a missing terminal LF, a JSON array/scalar, trailing bytes or concatenated
  objects are rejected.
- A fixed per-line byte ceiling and fixed total-byte ceiling are contract
  values. The candidate recommends 1 MiB per line and 32 MiB total for offline
  implementation, subject to independent review before acceptance.
- Parse errors expose only a closed code and zero-based line ordinal. They must
  not expose the line, byte offset, decoder message or exception text.

### Top-level event admission

The initial contract recognizes only:

| Private envelope `type` | Public marker | Required private discriminant |
| --- | --- | --- |
| `thread.started` | `thread_started` | none; thread identifier ignored |
| `turn.started` | `turn_started` | none |
| `item.started` | `item_started` | `item.type` |
| `item.updated` | `item_updated` | `item.type` |
| `item.completed` | `item_completed` | `item.type` |
| `turn.completed` | `turn_completed` | none; usage ignored |
| `turn.failed` | `turn_failed` | none; error content ignored |
| `error` | `stream_error` | none; error content ignored |

Additional top-level fields are private and ignored after the required
discriminants are type-checked. An unknown top-level `type` can alter lifecycle
semantics and therefore produces `UNKNOWN_EVENT_TYPE`; its value is never
published. There is no ignore-unknown forward-compatibility mode.

### Item-type admission

The parser recognizes the exact private item type `agent_message`. It projects
that value as public `item_marker = agent_message`. Every other non-empty string
is projected only as `item_marker = other`; the original value is never
published or hashed.

To prevent a future renamed agent-message type from becoming a false negative,
any `other` item makes the agent-message-presence axis `INDETERMINATE` unless
the exact item type is present in a separately reviewed, adapter-contract-bound
non-message allowlist. The allowlist values are implementation-contract bytes,
not dynamically learned from live data. This candidate intentionally does not
claim that the current repository contains a sufficient pinned-0.146.0
conformance fixture to populate that allowlist.

### Content-bearing fields

The adapter may inspect only:

- top-level `type`; and
- `item.type` for `item.started`, `item.updated` and `item.completed`.

Every other field is opaque private content. In particular, the adapter must not
copy or transform `text`, `message`, `reasoning`, `command`, `arguments`,
`output`, `result`, `diff`, `path`, `thread_id`, `id`, `usage`, `model`, URL or
MCP data.

## Lifecycle Projection Contract

### Public marker entry

Each entry has exactly:

```json
{"item_marker":"agent_message|other|none","marker":"closed_marker","ordinal":0}
```

Rules:

- `ordinal` is an exact non-boolean integer, zero-based and contiguous.
- `item_marker` is `none` for non-item events.
- Marker and item-marker vocabularies are closed.
- No identifier, content, raw-byte/message/token/usage count, raw byte size,
  duration or timestamp is included. The number of entries and their contiguous
  ordinals necessarily disclose lifecycle event cardinality; that limited
  structural metadata is explicitly admitted by the privacy contract below.
- Canonical JSON is UTF-8, sorted keys, compact separators and one trailing LF.

### Complete lifecycle

A projection is `COMPLETE` only when all are true:

1. exactly one `thread_started` is first;
2. exactly one `turn_started` follows it;
3. zero or more item markers follow the turn start;
4. exactly one of `turn_completed`, `turn_failed` or `stream_error` is the final
   event marker;
5. the contained process result reports stdout EOF and reader completion;
6. process disposition is present and closed;
7. the projection and result are create-once published and reopened
   byte-identically before the observation seal; and
8. no privacy, framing, contract or publication failure occurred.

Duplicate starts, events after terminal, multiple terminals, terminal absence,
stdout read failure or a missing EOF are never normalized. They produce a
closed non-complete result.

### Public projection document

`lifecycle-projection.json` has exactly:

- `action_sha256`
- `adapter_contract_sha256`
- `command_contract_sha256`
- `entries`
- `projector_sha256`
- `raw_retention` fixed to `NONE`
- `schema` fixed to
  `gate3-route-v2.actual-lifecycle-projection.v1`

It does not contain a raw-stream digest.

## Capture Authorization and Result

Before any future process launch, the publisher must durably create-once write
and reopen `capture-authorization.json`. It contains exactly:

- the contract/source/schema/action bindings listed above;
- `capture_ordinal = 1`;
- `retry = false`;
- `replacement = false`; and
- schema `gate3-route-v2.capture-authorization.v1`.

After contained execution returns, exactly one `capture-result.json` may be
published. It contains exactly:

- `authorization_sha256`;
- `process_result_sha256`, referring to a content-free closed process result;
- `projection_sha256` or `NONE`;
- `status`;
- `failure_code`;
- `schema = gate3-route-v2.capture-result.v1`.

Closed status/failure rows are:

| Status | Failure code | Projection |
| --- | --- | --- |
| `COMPLETE` | `NONE` | required |
| `INCOMPLETE` | `LIFECYCLE_INCOMPLETE` | forbidden |
| `INVALID` | `FRAMING_INVALID` | forbidden |
| `INVALID` | `UTF8_INVALID` | forbidden |
| `INVALID` | `JSON_INVALID` | forbidden |
| `INVALID` | `UNKNOWN_EVENT_TYPE` | forbidden |
| `INVALID` | `ITEM_DISCRIMINANT_INVALID` | forbidden |
| `INVALID` | `SIZE_LIMIT_EXCEEDED` | forbidden |
| `UNAVAILABLE` | `STDOUT_READ_FAILED` | forbidden |
| `UNAVAILABLE` | `CAPTURE_CONTRACT_MISMATCH` | forbidden |
| `UNAVAILABLE` | `PRIVACY_VALIDATION_FAILED` | forbidden |
| `UNAVAILABLE` | `PUBLICATION_FAILED` | forbidden |

Unknown status/code combinations fail verification. Authorization without a
result is permanently `CAPTURE_RESULT_UNKNOWN`. It may not be filled in after
restart, retried, replaced or inferred from final-path or workspace state.

The capture result is an adapter-produced public attestation. Its internal
links do not independently prove that the projected markers correspond to the
private stdout bytes returned by the claimed executable.

## Binding to the Existing Evidence Chain

For a future route package, the pre-cleanup observation seal must bind exact
bytes and SHA-256 values for:

- capture authorization;
- capture result;
- lifecycle projection when and only when status is `COMPLETE`;
- content-free process result;
- final-output lifecycle observation;
- task-workspace observation;
- adapter/contract/schema source bytes; and
- the existing action descriptor.

Cleanup cannot start until all required capture bytes have been reopened and
the seal is durably published. A non-complete capture may still produce a
negative diagnostic receipt, but classification of turn or agent-message
presence must be `INDETERMINATE`. Cleanup eligibility remains governed by the
accepted integration design and is not weakened here.

External recovery profiles must retain authorization, any result that was
durably published, every public transition record and the exact pre-cleanup
seal when one exists. They must not recreate a missing result or projection.

The public verifier may establish only that these retained public artifacts are
canonical, create-once, digest-linked and mutually consistent under the proposed
contract. Because raw stdout and any raw-stream digest are intentionally absent,
the verifier cannot independently establish correspondence between the private
stdout and the adapter-reported projection, executable provenance, or lifecycle
event truth.

## Diagnostic Semantics and Claim Ceiling

The adapter supplies reported discriminants, not independently verified
observations or causes.

| Internally linked adapter report | Maximum adapter-reported diagnostic statement |
| --- | --- |
| capture non-complete | `ADAPTER_CAPTURE_FAILURE` or `INDETERMINATE` |
| complete lifecycle, `turn_completed`, admitted completed `agent_message`, final path never created | `CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED_WITH_AGENT_MESSAGE_EVENT` |
| complete lifecycle, `turn_completed`, no admitted completed `agent_message`, no unknown item types | `TURN_COMPLETED_WITHOUT_AGENT_MESSAGE_EVENT` |
| `turn_failed` or `stream_error` | closed turn/stream failure observation only |
| workspace unchanged from calibrated baseline | `TASK_EXECUTION_FAILURE` under the existing classifier contract |
| multiple applicable observations | `MULTIPLE_FAILURES`; no causal ordering inferred |

Even in the second row, `agent_message` does not prove that a final answer was
produced, because the exec JSON event does not reliably expose a final-answer
phase. The public statement must not use `MODEL_COMPLETION_CONFIRMED`,
`FINAL_ANSWER_PRODUCED` or equivalent wording.

Every table row is conditioned on an internally consistent public attestation
chain. The corresponding diagnostic token means that the adapter reported the
listed discriminants under the proposed contract; it does not mean an
independent observer verified the private stream or that the report corresponds
to bytes emitted by the claimed executable. The strongest positive verifier
claim is `PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED`.

This design may claim only that a proposed adapter contract can preserve
content-free, adapter-reported event discriminants for later internal-link
verification. It cannot claim that:

- any adapter, schema or verifier is implemented;
- raw private stdout is independently reconstructable;
- adapter-reported markers independently correspond to private stdout;
- captured bytes came from the claimed executable;
- the CLI event stream is complete outside the pinned contract;
- a model produced or failed to produce a final answer;
- Gate 3 succeeded;
- treatment or Skill effectiveness is known; or
- the consumed pair can be revisited.

## Privacy Contract

### Publicly permitted

- fixed schema and contract tokens;
- SHA-256 of reviewed static source/schema/contract bytes;
- SHA-256 of canonical public artifacts;
- closed status, failure, process, marker and item-marker tokens;
- contiguous event ordinals and the lifecycle event cardinality necessarily
  disclosed by the number of projection entries;
- action and arm bindings already admitted by the future public contract; and
- fixed `raw_retention = NONE`.

### Publicly forbidden

- raw stdout/stderr or any substring;
- digest, length or entropy summary of raw stdout/stderr;
- prompt or response content;
- agent-message or reasoning text;
- tool names, arguments, results or command output;
- file paths, diffs or file contents;
- thread, turn or item identifiers;
- model identity, token usage, timing or performance fields;
- environment or credential data;
- exception messages derived from private parsing; and
- unknown raw type/item values.

Lifecycle event cardinality is admitted only to reconstruct ordering and the
closed lifecycle shape. It can still correlate otherwise separate runs, so the
public contract must not combine it with identifiers, timestamps, durations,
raw sizes, message/token/usage counts or other high-entropy run metadata. Event
cardinality is not evidence of semantic truth, task progress, model output or
executable provenance.

Privacy validation is deny-by-default and recursive. Unknown keys, string
values outside closed token sets, non-canonical bytes, extra artifacts or a
forbidden digest/length field fail closed.

## Failure Precedence

When multiple failures occur, the retained result uses this precedence:

1. `CAPTURE_CONTRACT_MISMATCH` before launch;
2. authorization/publication collision;
3. stdout read unavailable;
4. size/framing/UTF-8/JSON invalid;
5. unknown top-level event or invalid item discriminant;
6. incomplete lifecycle;
7. privacy validation failure;
8. projection/result publication failure.

Lower-precedence observations may be retained as closed boolean flags only when
the schema explicitly admits them. They cannot replace the primary code or
upgrade classification.

## Crash, TOCTOU and Fail-Closed Plan

Required cases for a later implementation:

1. crash before capture authorization: no launch authorization exists;
2. crash after authorization but before process result: permanent
   `CAPTURE_RESULT_UNKNOWN`, no retry;
3. crash after private stdout return but before result publication: raw bytes
   are not durable, result remains unknown, no replay from memory or workspace;
4. crash after projection publication but before capture result: orphan
   projection is inadmissible and cannot be adopted by a later result;
5. crash after result but before observation seal: external recovery retains
   exact published bytes; no new projection/result is created;
6. projection/result create-once collision: fail closed without overwrite;
7. adapter source/schema/contract replacement between authorization and parse:
   digest recheck fails before parse;
8. public artifact mutation between reopen and seal: seal fails;
9. mutation after seal: final verifier rejects digest/tree mismatch;
10. stdout object containing secrets in ignored fields: no secret, secret
    substring, raw digest or raw length appears in projection, error or logs;
11. parser exception containing raw content: exception is converted to a closed
    code without rendering the exception;
12. unknown event after an apparently valid terminal: entire capture invalid;
13. extra bytes or event after terminal: entire capture invalid;
14. timeout or forced tree termination: process axis records failure; lifecycle
    is complete only if its independent contract is satisfied and cannot
    override process failure; and
15. verifier receives a valid projection with missing authorization/result,
    wrong action, wrong contract digest or contradictory status: fail closed.

## Evidence and Mutation Plan

### Retained fixture families

All fixtures are synthetic or reviewed conformance fixtures containing no live
user/model content:

- complete turn with one admitted completed agent-message event;
- complete turn with admitted non-message items only;
- turn failure;
- stream error;
- mixed admitted item types;
- unknown top-level event;
- unknown item type causing an indeterminate agent-message axis;
- malformed UTF-8, JSON and NDJSON framing;
- missing/duplicate start or terminal;
- event after terminal;
- per-line and total-size boundaries;
- private secret canaries in every ignored content position; and
- each crash/publication transition listed above.

Expected public projection bytes must be retained independently. Tests must not
generate expected projections by calling the parser or projector under test.

### Required mutation sensitivity

Focused tests must fail when any of these mutations is introduced:

- unknown top-level events are ignored;
- `other` item types are treated as evidence that no agent message occurred;
- `agent_message` is treated as final-answer proof;
- raw text, raw digest, raw length or exception text is published;
- event ordinals are non-contiguous;
- a terminal need not be last;
- a missing EOF is accepted;
- authorization/result/action/contract links are not checked;
- result status/code/projection rows are not bidirectionally enforced;
- create-once collision overwrites;
- authorization without result is retried or reconstructed;
- an orphan projection is adopted after restart;
- cleanup begins before the capture result and observation seal reopen
  byte-identically; or
- an external recovery profile omits an existing capture transition.

### Focused validation recommendation

The later implementation tranche should run only its new adapter test file plus
the existing diagnostic and diagnostic-integration suites. It must not run a
real CLI, preflight or live command. The canonical repository gate remains a
separate commit-boundary check when commit authority is later granted.

## Affected Surfaces if Later Implemented

Recommended new files:

- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/gate3_final_message_actual_capture.py`
- `artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/test_gate3_final_message_actual_capture.py`

Potential deferred integration surfaces, not part of the first implementation
tranche:

- `gate3_route_v2_codex.py` to invoke the reviewed adapter after contained
  execution and before final-output/workspace evidence is sealed;
- `gate3_final_message_diagnostic_integration.py` to add exact capture artifacts
  to route/external profiles; and
- their focused tests.

No live-runner modification belongs in the first tranche.

## Recommended Next Implementation Tranche

After independent exact-digest approval and separate owner authorization,
implement only the pure/private parser ACL, pure projector, closed public
schemas, in-memory/create-once synthetic publisher behavior and focused offline
tests in the two new files above. Use retained synthetic and reviewed
conformance fixtures only.

Do not wire the adapter into `CodexExecRunner` in that tranche. Runtime wiring
is a later separately reviewed decision because it changes a trusted process
boundary and would require a new exact command/capture contract.

## Post-Merge Review and Mainline State

GitHub MR #52 is already merged into `main` at merge commit
`a1ac299928f52c51a69aafe996f23cb1bfcf8c4e`. The merge resolved branch
integration only: it did not accept this candidate, authorize implementation,
or upgrade any Gate 3 claim.

The bounded post-merge sequence is now:

1. remediate only the two blocking review findings and stale MR wording;
2. compute a new exact candidate digest;
3. independently review those exact bytes read-only;
4. separately decide whether to accept and commit the revised candidate; and
5. only after separate owner authorization, begin the recommended offline
   implementation tranche from current mainline history.

This revision authorizes no implementation, credentials, preflight, live
execution, old-pair reuse, retry, replacement, commit or push.

## Review Questions

An independent reviewer should answer:

1. Does the adapter observe only discriminants needed by the classifier?
2. Can any raw/private content, digest, length or exception text reach public
   evidence?
3. Are unknown lifecycle semantics and unknown item semantics handled without
   false-negative upgrade?
4. Is `agent_message` kept below final-answer/model-completion proof?
5. Are capture authorization, result, projection and seal links non-circular
   and create-once?
6. Are crash states permanent and non-retryable where raw bytes are unavailable?
7. Can cleanup begin only after exact capture bytes are sealed?
8. Do route and external recovery profiles retain every emitted public
   transition without reconstructing missing results?
9. Is the first implementation tranche offline, minimal and independent of the
   live runner?
10. Does any post-merge implementation remain subject to separate owner
    authorization after exact-digest candidate acceptance?

## External Reference Boundary

The following official OpenAI sources were consulted only to identify current
wire-shape and claim-boundary risks:

- `https://github.com/openai/codex/issues/31088`
- `https://github.com/openai/codex/issues/30190`
- `https://github.com/openai/codex/blob/main/codex-rs/exec/src/lib.rs`

They do not replace pinned-version retained conformance fixtures, an exact
command contract, independent review or future authorization.
