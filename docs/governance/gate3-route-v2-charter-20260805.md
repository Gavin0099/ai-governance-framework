# Gate 3 Route v2 Charter — Supported Evidence Acquisition First

Status: `CANDIDATE — PENDING INDEPENDENT SEMANTIC REVIEW`

Date: 2026-08-05

## Problem

Gate 3 v1 proved that a producer process can exit successfully while the
experiment still has no admissible evidence. The final v1 canary invoked two
non-counted sessions and both processes exited zero, but packet construction
stopped before rollout parsing because the route could not obtain exactly one
rollout from an internal `CODEX_HOME/sessions/**/*.jsonl` layout.

The retained failure receipt could not establish whether v9 produced zero, one
or multiple rollout files, stored the evidence elsewhere, or encountered a
timing issue. A later zero-session probe excluded only one narrow hypothesis:
the isolated login-status operation did not itself create a sessions JSONL
artifact. It did not reconstruct the deleted v9 runtime.

The v2 problem is therefore not “parse another rollout format.” It is:

> Establish a supported, process-boundary evidence interface whose success and
> failure paths both remain observable before private cleanup.

## Current Repository Truth

1. Gate 3 v1 is closed and counted execution remains zero. The canonical
   closeout and attribution boundary are recorded in `PLAN.md` under “Gate 3
   v1 Live Route Final Closeout” and “Gate 3 v1 Login-Status Contamination
   Attribution Closeout.”
2. The v1 acquisition helper
   `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3_codex_live_canary.py::_single_rollout`
   searches `CODEX_HOME/sessions/**/*.jsonl` and requires exactly one file.
3. In the v1 orchestrator, `failure_stage` becomes `packet_build` before
   `_single_rollout()` runs. Rollout diagnostics are populated only after
   acquisition succeeds, while the private runtime is deleted in `finally`.
   The retained v9 evidence therefore cannot distinguish acquisition
   cardinality, alternate location or timing failure.
4. The approved privacy-safe probe receipt at
   `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/evidence-live-canary/gate3-v1-login-status-contamination-probe-20260805/probe-receipt.json`
   records `sessions_jsonl_cardinality=zero` and `cleanup=PASS` for the isolated
   login-status operation only.
5. The official Codex command reference documents these non-interactive
   interfaces:
   - `codex exec --json` writes newline-delimited JSON events to stdout, one per
     state change.
   - `--output-last-message <path>` writes the assistant's final message to a
     caller-selected file for downstream scripting.
   - `--output-schema <path>` supplies a JSON Schema for the expected final
     response.
   - `--ephemeral` runs without persisting session rollout files to disk.
   The same reference recommends pairing `--json` with
   `--output-last-message` in CI.
6. OpenAI's Codex structured-output cookbook also documents
   `codex exec ... --output-schema <schema-file>` as the CLI form for a
   schema-constrained final response.
7. These official pages establish that the interfaces are documented today;
   they do not establish that pinned Codex CLI 0.146.0 has the same flags,
   exact event vocabulary or failure semantics. A future zero-session help
   preflight must establish flag availability for the exact pinned executable
   before any session authority is requested.

Official sources:

- [Codex developer commands — `codex exec`](https://learn.chatgpt.com/docs/developer-commands#codex-exec)
- [Codex structured outputs cookbook](https://developers.openai.com/cookbook/examples/codex/build_code_review_with_codex_sdk#codex-structured-outputs)

## Target Outcome

Produce a v2 route design in which one synthetic, non-scoring invocation can be
observed from action through independently verified packet without reading any
Codex session-storage directory. Every attempted run must attempt to publish a
privacy-safe, non-success observation seal before private cleanup. A run has a
durable seal only when privacy validation and create-once publication both
succeed; pre-seal failures remain externally detected no-admissible-evidence
terminals. After cleanup, a separate create-once final receipt pins any durable
seal and records success or failure using the actual cleanup result.

This charter does not authorize or implement that route. It defines the entry
contract for the first implementation tranche.

## Lowest-Layer Justification

The observed v1 failure is below Prompt, Context, Harness, Loop and Graph
semantics: the producer processes completed, but the harness could not acquire
the evidence needed to determine what happened. A prompt, Skill, agent role,
retry loop or orchestration graph cannot repair a missing process-boundary
observable after the private runtime has been deleted.

Therefore the lowest adequate repair is Layer 0 — evidence acquisition at the
`codex exec` process boundary. No higher-layer Gate 3 work is admissible until
this boundary works independently.

## Layer 0 Evidence-Acquisition Contract

### Supported inputs

The proposed route may depend only on caller-controlled process inputs and
officially documented command surfaces:

- exact executable identity and CLI version;
- exact prompt bytes delivered through stdin;
- exact output-schema bytes;
- explicit workspace and permission configuration;
- `--ephemeral` so v2 does not require saved-session discovery;
- `--json` stdout capture;
- `--output-last-message` to a caller-selected private path; and
- `--output-schema` to constrain the final response.

The route must not read, count, parse or infer evidence from
`CODEX_HOME/sessions`, rollout filenames, app databases, hidden thread stores
or another undocumented persistence layout.

### Observation seal, cleanup and final receipt

The orchestrator must use three ordered phases:

1. **Pre-cleanup observation seal.** Atomically publish a durable,
   privacy-safe, explicitly non-success seal outside the cleanup target. The
   pinned pre-cleanup content validator must first read the raw stdout and
   final-message artifacts, validate them against the pinned transport/schema
   rules, and emit a privacy-safe attestation binding their exact identities,
   the schema and validator identities, and closed validation results. The seal
   pins that attestation and every acquired private artifact identity and
   records `cleanup=PENDING` and `decision=PENDING`. An in-memory object alone
   is not a seal.
2. **Cleanup attempt.** Attempt private cleanup and determine its actual result
   without rewriting the seal.
3. **Final decision receipt.** Atomically publish a separate create-once
   success or negative receipt that pins the exact seal and records the cleanup
   result. For a route-result path, keep the recovery locator until final
   publication succeeds and the cleanup target has confirmed zero residue; only
   then remove the locator and verify its absence. For a no-admissible-evidence
   terminal, no route receipt is fabricated: after bounded publication/recovery
   retries are exhausted, a durable external launcher terminal record plus
   independently confirmed cleanup-target zero residue authorizes locator
   removal and absence verification. Success is admissible only when cleanup
   passed, an admissible final receipt exists and the locator is absent.

The pre-cleanup seal must distinguish, per attempted invocation:

- process launch attempted or not attempted;
- exit classification: zero, non-zero, signal/termination or unavailable;
- stdout capture: absent, empty, non-empty or capture-failed;
- stdout NDJSON parse: not attempted, valid, invalid or incomplete;
- final-message artifact: absent, empty, non-empty or read-failed;
- final-response schema validation: not attempted, pass or fail;
- workspace outcome capture: not attempted, pass or fail;
- workspace expected-outcome validation: not attempted, pass or fail; and
- packet assembly: not attempted, pass or fail.

Public evidence may contain only closed vocabulary, counts, boolean outcomes,
schema versions, implementation identities and privacy-approved content
identities that pass the existing privacy policy. The first tranche uses only
synthetic content whose exact identities are approved for the validator
attestation; this does not authorize publishing live model-content digests.
Raw stdout, stderr, prompts, model content, credentials and private paths remain
private and are cleanup targets after the observation seal is durable. Cleanup
failure must be visible in the final negative receipt and must prevent a success
packet.

If either seal publication or final-receipt publication fails, the external
launcher must detect the missing create-once object and classify the run as
having no admissible final evidence. A failed publication channel cannot be
required to publish a receipt describing its own failure. The separate launcher
terminal record records only the external terminal class and recovery result; it
is not a route receipt and cannot make the run admissible.

Unknown status, unknown event shape or an unclassified failure must remain
`unattributable`; the writer must not infer a layer from the source-code line
that raised the exception.

### Success requirements

A Layer 0 success requires all of the following:

1. exactly one authorized synthetic invocation;
2. process exit zero;
3. stdout capture is non-empty, contains at least one JSON value and every
   retained non-empty line is valid JSON;
4. before cleanup, the pinned content validator confirms that stdout meets the
   transport rules and the final-message bytes parse against the pinned output
   schema, then emits the privacy-safe attestation described above;
5. the action fixture pins the baseline and expected workspace outcome, the
   observed workspace outcome is captured, and independent expected-outcome
   validation passes;
6. the packet binds the action receipt, content-validator attestation,
   stdout-event capture identity, final-message identity, expected-outcome
   identity, observed workspace outcome and verifier identity;
7. the non-success observation seal is durably published before cleanup;
8. private cleanup passes;
9. the final create-once success receipt is published after cleanup and pins
   the exact observation seal;
10. the recovery locator is removed and zero private residue is verified; and
11. an offline verifier reconstructs attestation linkage and the packet decision
    from independently loaded retained artifacts and rejects success while any
    recovery locator exists.

After raw cleanup, the offline verifier cannot independently parse deleted
stdout or re-run final-message schema validation. It proves that the pinned
pre-cleanup validator attested to exact artifact identities and closed results,
and that the seal, cleanup result and final decision are mutually consistent.
It must not elevate that linkage proof into a claim that deleted content was
revalidated offline.

Exit zero alone is never Layer 0 success. Valid NDJSON alone is never proof of
task completion. A schema-valid final message alone is never proof that the
workspace action occurred.

### Failure requirements

Every modeled producer, acquisition, post-seal validation or cleanup failure
for which seal privacy validation succeeds and the seal publication channel
works must first have a durable non-success observation seal, then attempt
cleanup, then publish a final privacy-safe negative receipt that pins the seal
and actual cleanup result. The receipt preserves the last completed observation
stage and closed failure classification without retaining raw content.

Seal privacy-validation failure and seal-publication failure occur before a
durable seal exists. They are external no-admissible-evidence terminals: cleanup
is still attempted, no success or final route receipt is claimed, and the
external launcher records the missing seal through its own invocation result.
Content-attestation privacy/publication failure follows the same rule.

A crash between seal publication and final receipt remains externally
detectable as a durable pending seal with no final decision. It is not a
success. Before starting the synthetic child, the external launcher must create
a current-user-only recovery locator outside the child cleanup target and must
validate its exact closed schema, ACL, privacy, authorization/run identity and
confinement before launch. Locator creation or validation failure forbids child
launch.

The cleanup target must be derived independently from the authorized run ID
under a fixed user-Temp root; an arbitrary path stored in the locator must never
redirect cleanup. The reconciler must fail closed on locator mutation or
identity mismatch and must handle an orphaned locator with no seal after a
launcher crash by performing the same bounded cleanup. It keeps the locator
through cleanup and final-receipt publication. It removes the locator only after
final publication succeeds and the cleanup target has confirmed zero residue.
If cleanup fails, it may publish an immutable final negative receipt recording
that failure, but it retains the locator for bounded idempotent recovery until a
later zero-residue confirmation. If final publication fails, the locator also
remains while bounded publication/recovery retries are pending. Once those
retries are exhausted, the no-admissible-evidence closeout requires a durable
external launcher terminal record and independently confirmed cleanup-target
zero residue before locator removal; the absent final receipt remains proof of
non-admission. Locator removal failure is visible cleanup residue, forbids
success/promotion and remains eligible for bounded retry. The offline verifier
must reject success while a locator exists.

Partial locator creation or validation failure must remove any locator artifact
and verify its absence before external terminal closeout. It must never launch
the child or create an admissible route result.

A fixture is not promotable unless recovery reaches zero residue. A missing
seal or missing final receipt caused by publication failure is an externally
detected no-admissible-evidence terminal; the failed channel is not assumed to
have reported itself.

Failures in one evidence source must not suppress collection of already
available independent sources. For example, a missing final-message artifact
must not erase process exit classification or stdout capture status.

## Action → Observation → Verification → Claim Chain

| Stage | Required v2 object | What it may prove | What it cannot prove alone |
| --- | --- | --- | --- |
| Action | Pinned invocation receipt | What executable, inputs and policy were requested | That the process completed or obeyed the request |
| Observation | Pinned pre-cleanup content-validator attestation plus durable non-success seal binding exit classification, stdout/final-message identities and workspace capture | What crossed each caller-controlled boundary and what the pinned validator reported before cleanup | Independent revalidation of deleted raw content or agreement with the pinned expected workspace outcome |
| Verification | Offline reconstruction of attestation linkage, expected-outcome validation, cleanup and decision from independently loaded retained artifacts | Artifact/attestation identity, workspace binding and decision consistency | Independent NDJSON/schema revalidation after raw cleanup, or Model/Skill effectiveness beyond the synthetic task |
| Claim | Post-cleanup create-once success or negative receipt pinning the seal | Only the verified Layer 0 outcome and its claim ceiling | Counted Gate 3 result, treatment effect or route-wide reliability |

No stage may be skipped. A downstream object must pin the exact identity of
every upstream object it relies on.

## Scope

This charter covers only:

- supported Codex process outputs as the v2 evidence boundary;
- observation-before-cleanup semantics;
- a synthetic single-invocation packet and offline verifier;
- privacy-safe positive and negative receipts; and
- promotion gates before any live or counted work.

## Non-Goals

- No change to Gate 3 v1 or `_single_rollout()`.
- No change to existing preregistration, route-admission or scorer manifests.
- No A/B pair, treatment comparison, blind scoring or counted execution.
- No new failure taxonomy, FGCR schema, hook, rule pack or five-layer Gate.
- No prompt, Skill, Context, Loop or Graph optimization.
- No inference that current official documentation proves pinned 0.146.0
  behavior.
- No dependence on app-server, SDK or cloud surfaces in the first tranche.
- No runtime/schema implementation in this charter slice.

## Affected Surfaces

Current charter slice:

- this document only.

Potential first implementation tranche, subject to separate approval:

- a new isolated `gate3-route-v2` runtime namespace;
- synthetic fixtures for process stdout, final-message and workspace outcome;
- a packet builder and offline verifier; and
- focused mutation tests.

Existing v1 runtime, signed manifests, evidence and history remain immutable.

## Boundary and API Considerations

1. **Documented does not mean version-pinned.** The exact CLI executable must
   pass a zero-session help/version preflight for all required flags.
2. **NDJSON is a transport, not a stable semantic schema.** Until official
   documentation or pinned source establishes an event contract, v2 may rely
   on JSON-line well-formedness and closed observations only. The pinned
   pre-cleanup content validator performs that check and attests to the exact
   synthetic artifact identities; the post-cleanup verifier checks the
   attestation chain rather than pretending to parse deleted bytes. V2 must not
   infer task semantics from undocumented event field names.
3. **Final response is not workspace truth.** `--output-schema` and
   `--output-last-message` constrain/capture a producer statement; workspace
   receipts independently establish action results.
4. **Ephemeral is intentional.** v2 must not require a saved rollout as a
   fallback. If supported output capture fails, the route fails visibly.
5. **No post-result anchoring.** Exact schemas, CLI identity, verifier bytes
   and claim rules must be reviewed before any live result is observed.

## Failure Paths and Risk Points

- Required flags absent from pinned CLI: `NO-GO`; do not request a session.
- CLI starts but stdout capture fails: publish a non-success seal, attempt
  cleanup, then publish a final negative receipt.
- Stdout capture is empty: negative receipt, never vacuous JSON success.
- Exit zero but final message is absent or invalid: negative receipt, not
  success.
- Final message passes schema but workspace evidence disagrees: negative
  receipt with `cross_boundary_mismatch`.
- NDJSON contains unknown event fields: retain only structural census privately;
  do not widen acceptance during the run.
- Observation-seal privacy validation fails: do not publish the seal or any
  success; the external launcher records a pre-seal no-admissible-evidence
  terminal and cleanup is still attempted.
- The content validator cannot run, or its attestation fails privacy validation
  or create-once publication: treat it as a pre-seal no-admissible-evidence
  terminal; do not replace the missing attestation with unbound booleans.
- Recovery-locator creation, ACL, schema, privacy or confinement validation
  fails: do not launch the child, remove/verify absence of any partial locator
  artifact, and do not claim an admissible route result.
- A locator is missing its seal after a launcher crash: derive the cleanup
  target independently from the authorized run ID and perform bounded orphan
  recovery; never trust a locator-supplied arbitrary path.
- A locator is mutated or its identity differs: fail closed, do not redirect
  cleanup and do not admit success.
- Cleanup fails: success is forbidden, residue status remains visible, an
  immutable final negative receipt may be published, and the locator remains
  until bounded recovery later confirms zero residue.
- A crash occurs after the seal but before cleanup/final publication: the
  external launcher/reconciler uses its protected recovery locator to perform
  idempotent cleanup and publish a final negative receipt when possible; it
  removes the locator only after the cleanup target confirms zero residue.
- Final-receipt publication fails: no admissible final result exists; do not
  claim that the failed channel published its own failure. Retain the locator
  while bounded retries remain; after exhaustion, use only the external
  no-admissible terminal closeout described above.
- Locator removal fails: classify it as cleanup residue, forbid success and
  promotion, and retain bounded reconciliation authority.
- Offline verifier cannot rebuild the decision: packet is invalid.
- Synthetic vertical slice needs an undocumented session store: v2 design is
  rejected rather than patched upward.

## Evidence Plan

The first implementation tranche must provide:

1. zero-session CLI help/version evidence for required documented flags;
2. synthetic success fixture with one invocation, non-empty valid stdout
   NDJSON, a schema-valid final message, a pinned expected workspace outcome,
   successful workspace capture, a pinned pre-cleanup validator attestation and
   successful expected-outcome validation;
3. synthetic failures for launch failure, non-zero exit, missing/empty/invalid
   stdout, missing/invalid final message, workspace capture failure, expected
   workspace disagreement, content-validator/attestation failure, seal
   privacy-validation failure, seal-publication failure, cleanup failure and
   final-receipt publication failure;
4. crash fixtures between seal and cleanup and between cleanup and final
   publication, proving a pending seal can never be read as success and that
   external recovery cleanup reaches zero residue;
5. locator fixtures for creation failure, ACL-validation failure, orphaned
   locator without a seal, locator mutation/identity mismatch and locator
   removal failure, plus cleanup failure followed by successful negative
   publication, proving none can launch an unauthorized child, redirect cleanup
   or admit success and that the locator remains until later zero-residue
   recovery; pre-seal attestation/seal failures, orphan-without-seal and
   exhausted final-publication failure must additionally prove durable external
   terminal recording followed by zero private/locator residue without a
   fabricated route receipt;
6. mutation tests proving that omission, content alteration, identity mismatch,
   reordered or duplicated evidence, attestation substitution and unknown
   classifications fail;
7. privacy tests proving public seals/receipts contain no raw content,
   credentials or private paths;
8. offline verification from a fresh temporary root, including rejection while
   any recovery locator remains; and
9. independent review before any real Codex invocation is requested.

No session count, A/B result or scorer outcome is part of this evidence plan.

## Single-Invocation Synthetic Non-Scoring Vertical Slice

The first tranche models exactly one invocation using a synthetic runner; it
does not invoke `codex exec`, a model or a session. A separate zero-session
`--version` and `exec --help` preflight may invoke the pinned executable only to
confirm the documented flags before any session authority is requested.

Flow:

```text
pinned action fixture
  -> synthetic process result
  -> stdout NDJSON + final-message + workspace observations
  -> pinned pre-cleanup content-validator attestation
  -> durable privacy-safe non-success observation seal
     -> zero-residue path: cleanup passes
        -> post-cleanup create-once final receipt
        -> locator removal and zero-residue verification
        -> independent offline verification
     -> cleanup-failure path: immutable final negative receipt
        -> locator retained for bounded recovery
        -> zero-residue confirmation, then locator removal
        -> independent offline verification; decision remains failure
     -> crash path: external pending-seal reconciliation
        -> idempotent recovery cleanup
        -> final negative receipt when publication works
        -> locator removal only after publication and zero residue
        -> independent offline verification
     -> no-admissible-evidence path: bounded retries exhausted
        -> durable external launcher terminal record
        -> independently confirmed cleanup-target zero residue
        -> locator removal and absence verification
        -> no route receipt; missing seal/final remains non-admission
```

DONE for that future tranche:

> Every synthetic one-invocation run attempts to durably seal its acquired
> observations before cleanup. Every seal-valid or post-seal path then
> atomically publishes either a complete, independently verifiable non-scoring
> success receipt or a privacy-safe negative receipt after cleanup. Pre-seal
> validation/publication failures remain externally detected
> no-admissible-evidence terminals; crashes between phases remain recoverable,
> recovery reaches zero private residue, post-cleanup verification stays within
> attestation linkage rather than claiming to revalidate deleted raw content,
> external terminal closeout never fabricates a route receipt, and no test or
> implementation reads a Codex session persistence directory.

Passing this tranche authorizes nothing further. A real single-session canary
would require a separate reviewed contract, clean execution boundary and exact
session authorization.

## Implementation Tranche Recommendation

Recommend exactly one future tranche: implement the synthetic vertical slice
above in a new isolated namespace. Do not integrate A/B, scoring, credential
seeding or existing v1 admission logic.

If the pinned CLI lacks the documented flags, or if the synthetic route cannot
durably seal acquired observations before cleanup and publish a final negative
receipt after cleanup without consulting undocumented storage, stop v2 and
revisit the research channel rather than adding another diagnostic layer.

## Claim Ceiling

This charter claims only:

- current v1 acquisition limitations observed in repository code/evidence;
- currently documented Codex CLI output surfaces;
- a proposed Layer 0 contract;
- intended evidence and failure handling; and
- one recommended synthetic implementation tranche.

It does not claim:

- pinned CLI 0.146.0 supports every documented flag;
- Codex event fields are stable;
- the proposed route is implemented or safe;
- a session has run;
- a scorer packet exists;
- Gate 3 has restarted; or
- Skill/model effectiveness has been measured.

## Promotion Gates

Before any real Codex invocation is requested, all must be true:

1. this charter receives independent semantic approval;
2. the synthetic tranche is implemented and independently reviewed;
3. required flags are confirmed from the exact pinned executable without
   starting a session;
4. success and every modeled post-seal failure durably publish a non-success
   observation seal before cleanup, and a separate final receipt after cleanup;
   seal privacy-validation, seal-publication and final-publication failures
   remain externally detectable as missing admissible objects;
5. the seal pins a pre-cleanup content-validator attestation binding exact
   synthetic raw identities, pinned schema/verifier identities and closed
   results; post-cleanup verification makes no raw-revalidation claim;
6. crash-between-phase and empty-stdout cases fail closed;
7. external reconciliation of every pending-seal crash fixture reaches zero
   private residue;
8. locator creation/ACL failure, orphan, mutation/identity mismatch, final
   publication failure and removal failure fixtures all fail closed without
   launching an unauthorized child, redirecting cleanup or admitting success;
9. cleanup-failure fixtures retain the locator after negative publication until
   later zero-residue recovery, while the immutable decision remains failure;
10. pre-seal failures, orphan-without-seal and exhausted publication failures
    end with a durable external terminal record, independently confirmed zero
    cleanup-target residue and locator absence, while no route receipt is
    fabricated;
11. partial locator creation/validation failures remove and verify absence of
    any locator artifact before external closeout;
12. public privacy and zero-residue cleanup pass, including locator absence;
13. the owner signs the exact v2 contract bytes; and
14. the owner separately authorizes the exact session count and forbids
   replacement.

Counted execution additionally requires natural-bug/resource admission and an
independent Gate 3 start authority. None exists from this charter.
