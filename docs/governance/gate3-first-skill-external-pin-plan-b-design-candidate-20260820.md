# Gate 3 first-Skill external-pin Plan B design candidate

Status: **CANDIDATE — ROUTE B CONFIRMED, DESIGN NOT YET ACCEPTED.**

The owner confirmed Route B on 2026-08-20: do not use a second natural person
as the external-pin authority.  Use an externally operated, independently
verifiable append-only transparency or timestamp surface instead.  No provider
is selected by this document, and no submission, account creation, integration,
rehearsal or counted run is authorized.

## Claim boundary — first page, before mechanism

Route B can establish one proposition:

> The exact retained primary and second scorer submissions were already bound
> into the comparison unit's digest-chain head before the canonical mapping
> release gate emitted the mapping-release event.

Route B does **not** establish scorer blindness.  The coordinator creates the
mapping commitment and retains the nonce until release, so the coordinator
knows the mapping throughout.  An external timestamp proves prior existence of
bytes; it does not prove that the coordinator, a scorer, a model or another
actor lacked the mapping or did not communicate out of band.

It also does not establish that two scorer contexts are independent.  Their
distinct context identifiers and declarations remain retained context evidence,
not cryptographic proof that one scorer did not copy another score.

Route B also does not establish how many attempts were made.  A coordinator can
discard an unfavourable local run and pin only a later run; a membership proof
for the retained run cannot reveal an entry that was never submitted.  The
membership and consistency proofs required below do not provide cryptographic
completeness for an arbitrary search query, and this repository establishes no
provider that adds that property.  Attempt bounding is therefore excluded
rather than represented by a mechanism that proves less than its name.  It
requires a separate provider-feasibility decision and is not part of this
ordering design.

Route B does not establish study-population or reporting completeness.  Several
comparison units can each have a valid ordering pin while a coordinator presents
only a favourable subset.  Nor does a verifier know that every proof bundle was
supplied: it can validate a bundle it receives, but the external membership
proof does not enumerate coordinator-retained bundles that were omitted.  The
maximum claim is therefore per-presented-unit ordering, not unbiased unit
selection, complete evidence discovery or a population-level effect estimate.

Therefore Route B is sufficient for the specific ordering defect inherited
from Gate 2, and insufficient to make the comparison unit independently trusted
in every respect.  Historical Gate 2 remains `NOT_ESTABLISHED`; this design
cannot repair that run retrospectively.

## Problem

The current Gate 3 ordering chain is create-once only inside a coordinator-
controlled filesystem.  It detects missing, reordered and altered retained
events, but the same actor can coherently delete and rebuild the complete local
chain.  A local final-head digest, another local file, same-agent memory or a
caller-supplied receipt merely lets one coordinator-controlled value vouch for
another.

The chain needs one authority outside that control boundary.  Because no
qualifying second natural-person authority is established for this repository,
Route B delegates only the prior-existence assertion to an external operator
whose append-only surface can be verified without coordinator authority.

## Current repository truth

- `PLAN.md` records Gate 2 process integrity as `NOT_ESTABLISHED` because the
  retained evidence cannot independently prove scorer submission before mapping
  release.
- `docs/governance/gate3-preregistration-amendment-v1-candidate-20260729.md`
  requires the final pre-release chain head to reach a separately controlled
  append-only surface.
- `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/
  gate3_evidence_chain.py` already implements the local chain and release
  function.  Its exact `EVENT_SEQUENCE` contains **seven events**, not six:

  1. `randomization_committed`;
  2. first `outcome_sealed`;
  3. second `outcome_sealed`;
  4. `blind_set_closed`;
  5. `primary_scorer_submitted`;
  6. `second_scorer_submitted`;
  7. `mapping_released`.

  The accepted preregistration amendment's six-item list is a conceptual stage
  list: it compresses the two distinct `outcome_sealed` records into one item.
  It is therefore not an ordinal authority.  For exact event ordinals, the
  pinned `EVENT_SEQUENCE` bytes in `gate3_evidence_chain.py` are the sole
  normative source.  Implementations must derive the ordinal by locating the
  unique `second_scorer_submitted` entry in that pinned sequence; its current
  derived value is 6.  Route B pins that event and gates the following
  `mapping_released` event, currently 7; it does not add or renumber a local
  chain event.

  Acceptance of this design carries that narrow interpretive amendment to the
  preregistration amendment.  Until owner acceptance, the six-item authority
  prose and seven-event runtime sequence remain a blocking mismatch; an
  implementation may not choose either ordinal by convention.

- Each `submit_scorer(...)` call appends one submission path and digest.  Event
  5 directly binds the primary scorer source; event 6 directly binds the second
  scorer source and transitively binds event 5 through
  `previous_event_sha256`.
- The current `verify_chain(...)` `mapping_released` branch verifies mapping,
  randomization and scorer-event digests only.  It does not resolve, reconstruct
  or verify an external pin.  The current runtime is therefore not compliant
  with this candidate merely because a producer-side release gate is proposed.

- The 2026-07-29 rehearsal proves local mechanics only.  It has no qualifying
  external pin and remains synthetic and non-counted.
- No external transparency/timestamp provider, provider profile, trust root or
  verification adapter is currently selected or admitted.

## Target outcome

Define a service-neutral contract under which a future implementation can:

1. reconstruct and verify events 1 through 6;
2. derive one domain-separated request from the exact event-6 bytes and frozen
   protocol-contract bytes;
3. submit only that request digest to a qualified external surface;
4. wait for the provider's defined integrated/final state;
5. retrieve the entry and complete inclusion proof through a public read path
   requiring no coordinator-held secret;
6. verify the retained proof offline against pinned trust material; and
7. only then permit event 7 to publish the mapping and nonce; and
8. require every later `verify_chain(...)` call that accepts event 7 to
   independently reconstruct and verify the same request and proof bundle,
   regardless of how the event file was created.

The output is a durable proof bundle that another actor can verify without the
submission credential and, after initial capture, without the provider API.

## Scope

- External operator and authority requirements.
- Provider-profile admission requirements without selecting a provider.
- Canonical pin-request encoding and privacy projection.
- Submission, integration, public retrieval and offline verification sequence.
- Mapping-release gate inputs and fail-closed outcomes.
- Proof retention and long-term claim degradation.
- Evidence required before one non-counted rehearsal may be requested.

## Non-goals

- Selecting, enrolling in or contacting a provider.
- Creating credentials, accounts, billing, network permissions or secrets.
- Implementing or modifying `gate3_evidence_chain.py`.
- Adding a generic transparency-log framework, shared runtime hook, CI gate,
  schema registry or repository-wide timestamp service.
- Proving scorer blindness, scorer independence, human identity, mapping
  secrecy, absence of out-of-band disclosure, lack of collusion, attempt count,
  absence of discarded runs or absence of covert/unregistered runs.
- Repairing or reclassifying historical Gate 2 evidence.
- Authorizing the local ordering-chain implementation, a rehearsal, a counted
  pair, natural-bug selection or Skill promotion.
- Changing M3-b-2A, M3-b-2B, M3-b-3 or M4.  Historical materialization and
  first-Skill external pinning are separate work lines.

## Authority model

### Coordinator

The coordinator may construct and submit a pin request.  It may not control the
operator's signing/checkpoint keys, delete or rewrite integrated entries,
replace checkpoints, alter the admitted verification policy, or require a
coordinator secret for another actor to retrieve the entry.

Submission permission is not authority over the surface.  A public service may
allow anyone to append while reserving integration, checkpoint and history
control to the external operator.

### External operator

The operator is an organization or service authority outside the coordinator's
control.  It controls integration and the keys or consensus mechanism that make
the retained checkpoint independently verifiable.  A second account, process,
agent or service instance ultimately controlled by the coordinator is
inadmissible.

### Verifier

The verifier trusts only the admitted provider profile, retained trust material,
exact local chain bytes and complete proof bundle.  It does not trust a caller-
supplied boolean, receipt ID, timestamp string, web screenshot, local cache or
provider success message.

## Provider qualification profile

Before implementation, one exact provider profile must be independently
reviewed and owner-accepted.  It must pin:

- operator legal/service identity and protocol version;
- submission endpoint and public retrieval endpoint origins;
- digest algorithm and exact submitted-value encoding;
- integration/finality definition and maximum wait policy;
- stable entry locator syntax;
- complete inclusion-proof format;
- signed checkpoint, witnessed checkpoint or consensus-anchor format;
- offline verification algorithm and implementation identity;
- trust-root or consensus-validation bytes;
- key rotation, revocation and algorithm-deprecation interpretation;
- public retrieval authentication policy, which must require no coordinator
  credential; and
- privacy statement for submitted digest and retained locator metadata.

An API that returns only a server-generated timestamp or receipt identifier is
not sufficient.  A surface whose history can be edited by the coordinator, or
whose proof can be verified only by asking the same live API to say `valid`, is
not sufficient.

## Canonical pin request

The local request is canonical UTF-8 JSON with sorted keys, compact separators
and one trailing LF.  Its closed schema is
`gate3-external-ordering-pin-request.v1` and contains exactly:

| Field | Meaning |
| --- | --- |
| `schema` | literal schema name |
| `domain` | literal `gate3-first-skill-ordering-head-v1` |
| `chain_contract_sha256` | digest of exact `gate3-protocol-contract-v1.json` bytes loaded by `load_contract(...)` |
| `comparison_unit_sha256` | digest of the canonical comparison identity, not its raw label |
| `head_event` | literal `second_scorer_submitted` |
| `head_ordinal` | derived from pinned `EVENT_SEQUENCE`; current value `6` |
| `head_event_sha256` | digest of exact event-6 bytes |
| `mapping_commitment_sha256` | commitment copied from verified event 1 |
| `provider_profile_sha256` | digest of the admitted provider profile |

`chain_contract_sha256` is not a digest of the Python tuple or the amendment's
conceptual list.  It is the digest returned by `load_contract(...)` for the
exact admitted `candidate/gate3-protocol-contract-v1.json` bytes.  That JSON
must contain an `evidence_chain.event_order` exactly equal to the pinned runtime
`EVENT_SEQUENCE`; disagreement fails before request construction.  The JSON
file is the byte authority for `chain_contract_sha256`, while the pinned runtime
tuple is the ordinal authority.  Neither silently substitutes for the other.

`comparison_unit_sha256` is the SHA-256 of canonical
`gate3-comparison-unit-identity.v1` JSON containing exactly `schema`, `task_id`,
`pair_id`, `repeat_index` and `study_kind`, all copied from the verified
randomization record.  The same canonical-JSON rules apply.

The submitted value is
`sha256(canonical_pin_request_bytes).hexdigest()`, encoded exactly as the
provider profile requires.  The external surface receives no task text, path,
repository name, treatment mapping, nonce, scorer identity, model identity,
score, prompt, credential or raw event bytes.

Domain separation prevents a digest created for another protocol from being
relabelled as a Gate 3 ordering pin.  The verifier recomputes every field from
retained source bytes; no digest-shaped caller input is accepted as authority.

The derivation is acyclic and has one direction:

```text
protocol contract + comparison identity + event 6 + provider profile
    -> canonical pin request -> submitted digest -> provider proof bundle
    -> event 7
```

The provider profile must not contain an expected request digest, entry locator,
proof digest, bundle-manifest digest or event-7 digest.  The request must not
contain any locator, proof, bundle or event-7 value.  Any dependency pointing
backward across that sequence is invalid rather than resolved by iteration.

## Proof bundle

Pin finalization must capture complete bytes, not merely an entry ID.  The
closed local bundle manifest is
`gate3-external-ordering-proof-bundle.v1` and binds the SHA-256 and byte length
of every retained component:

- canonical pin-request bytes;
- exact provider submission bytes;
- exact submission response bytes;
- integrated entry bytes;
- complete inclusion path or equivalent proof;
- signed/witnessed checkpoint or consensus anchor;
- any required consistency or witness material;
- admitted provider-profile bytes;
- trust-root/verification-policy bytes; and
- a second exact retrieval response obtained through the public read path.

Opaque provider bytes remain opaque.  The canonical manifest records their
digests and roles; it does not normalize or reserialize them.

The public retrieval must be possible using the stable entry locator and public
profile alone.  A successful read using cached submission credentials is not
evidence of third-party retrievability.

## Producer and release-gate sequence

1. Verify the frozen protocol-contract bytes and exact events 1–6.
2. Require event 5 to bind the primary scorer source and event 6 to bind the
   second scorer source.  Require both files to match their retained digests and
   event 6's previous-event digest to bind the exact event-5 bytes.
3. Construct the canonical pin request from the verified chain.
4. Submit its digest.  After a stable locator or pending handle is returned,
   later calls may only finalize or retrieve that same operation.  If the
   submission outcome is ambiguous before such a handle exists, fail closed
   under `EXTERNAL_PIN_SUBMISSION_FAILED`; do not issue a blind second submit.
5. Wait until the provider profile's integrated/final state.  Pending is not
   success.
6. Retrieve the entry and complete proof through the public read path without a
   coordinator secret.
7. Verify the proof offline against the pinned profile, trust material and
   signed/witnessed checkpoint or consensus anchor.
8. Freeze the proof bundle create-once under the comparison evidence root.
9. Re-run local event 1–6 and contract verification and reconstruct the same
   pin request.
10. Only then may `release_mapping(...)` validate the mapping/nonce commitment
    and append event 7.

Event 7 must bind a proof-bundle path beneath the evidence root, its manifest
digest, pin-request digest, provider-profile digest, stable entry locator and
checkpoint/anchor digest.  The mapping artifact must not be published to the
scorer-visible or public evidence surface before this gate succeeds.  This is a
canonical-release guarantee only; it does not prove the coordinator lacked or
never disclosed the mapping out of band.

### Verification-side obligation

The `verify_chain(...)` `mapping_released` branch is the authority for accepting
event 7.  It must not trust pin-shaped fields merely because they are present or
because `release_mapping(...)` normally writes them.  For every event-7
verification it must:

1. verify events 1–6 and retain their exact bytes;
2. reconstruct the canonical pin request and compare its bytes and digest with
   both event 7 and the bundle manifest;
3. resolve the proof-bundle path beneath the evidence root and verify the exact
   manifest digest recorded in event 7;
4. independently load the admitted provider profile and verify its digest;
5. re-run offline inclusion/checkpoint/witness or consensus verification over
   the retained provider bytes; and
6. compare the verifier-derived locator and checkpoint/anchor digest with event
   7 before accepting `mapping_released`.

A caller boolean, a serialized `verified_pin`, or fields copied into a handmade
event file are not authority.  Missing bundle fields or bytes fail with
`MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED`; present but mismatched or invalid
material fails under the corresponding closed external-pin code.  Thus a
handwritten event 7 cannot become valid by bypassing `release_mapping(...)`.

## Time and ordering semantics

The trusted statement is relative ordering, not precise wall-clock time:

1. the external operator integrated the request digest into the retained
   checkpoint/anchor;
2. that request binds exact event-6 bytes and therefore both retained scorer
   submissions through the previous-digest chain; and
3. the canonical release gate appended event 7 only after verifying that proof.

Provider timestamps may be retained, but no local timestamp comparison can
substitute for inclusion and gate sequence.  Clock skew, timezone text and file
mtime never decide validity.

## Fail-closed errors and refusal conditions

The future adapter must expose closed error codes and no provider response body,
path, credential or submitted value in exceptions.  At minimum:

| Code | Refusal |
| --- | --- |
| `EXTERNAL_PIN_PROFILE_INVALID` | profile absent, changed, unknown or unsupported |
| `EXTERNAL_PIN_REQUEST_MISMATCH` | reconstructed request or submitted digest differs |
| `EXTERNAL_PIN_SUBMISSION_FAILED` | submission fails before a stable locator exists |
| `EXTERNAL_PIN_NOT_FINAL` | timeout, pending or provider finality unknown |
| `EXTERNAL_PIN_UNAVAILABLE` | entry or proof cannot be retrieved before release |
| `EXTERNAL_PIN_PUBLIC_READ_REQUIRED` | retrieval needs coordinator credentials |
| `EXTERNAL_PIN_ENTRY_MISMATCH` | retrieved entry does not contain the submitted digest |
| `EXTERNAL_PIN_PROOF_INVALID` | inclusion, checkpoint, witness, consensus or signature verification fails |
| `EXTERNAL_PIN_CHECKPOINT_STALE` | checkpoint violates the admitted freshness/finality policy |
| `EXTERNAL_PIN_BUNDLE_INCOMPLETE` | any required raw component is absent |
| `EXTERNAL_PIN_LATE` | mapping release or mapping publication already exists |
| `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED` | event-7 construction or verification lacks the required bundle |

Absence, timeout, DNS/TLS failure, rate limit, stale checkpoint, API drift,
unknown key state, malformed proof, mismatched bytes and ambiguous provider
status all refuse release.  There is no temporary release, offline override,
manual `PASS`, retrospective pin or “release now, attach proof later” path.

## Long-term verification and service disappearance

The complete inclusion proof, checkpoint/anchor, trust material and verifier
policy are captured at pin time because an entry locator is not durable proof.

If the provider later disappears but the retained bundle still verifies
offline, the maximum claim becomes:

> `HISTORICAL_EXTERNAL_PIN_VERIFIED_OFFLINE` — these bytes verify as included
> under the retained provider profile and checkpoint/anchor accepted at pin
> time.

That status does not claim current provider availability, current public
retrievability, present-day key standing, continued log operation or absence of
operator equivocation beyond the retained witness/consistency evidence.

If required algorithms, trust material or proof bytes are missing or no longer
verifiable, the status is `EXTERNAL_PIN_NOT_VERIFIABLE`; the comparison unit is
not countable under a current audit.  A later migration may add a new pin for
future durability, but it cannot replace the original proof or retroactively
make an invalid release valid.

## Affected surfaces

This candidate changes only this design file.  A later implementation would be
limited initially to:

- one experiment-local provider adapter/profile module;
- one independent offline proof verifier;
- focused fixtures and mutation tests; and
- the smallest producer and verifier changes in
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/
  gate3_evidence_chain.py`: `release_mapping(...)` must construct event 7 only
  after proof, and `verify_chain(...)` must independently reject any event 7
  whose request or proof cannot be reconstructed.  Focused tests cover both.

No shared `governance_tools`, runtime hook, CI workflow, schema registry,
production route, M3/M4 module or credential-bearing live runner belongs to the
first tranche.

## Boundary and API considerations

The provider adapter needs four conceptual operations:

```text
submit(request_digest, admitted_profile) -> stable_locator_or_pending_handle
finalize(locator_or_handle, admitted_profile) -> raw_proof_components
retrieve_public(stable_locator, admitted_profile) -> raw_retrieval_components
verify_offline(request_bytes, proof_bundle, admitted_profile) -> verified_pin
```

The release gate accepts only an opaque `verified_pin` minted by the offline
verifier.  It has no boolean override and no API accepting a raw receipt ID,
timestamp, digest, URL or provider response as equivalent authority.

Network operations remain outside the deterministic chain verifier.  Retained
proof verification is offline and deterministic; provider qualification and
live submission are separate authority-bearing surfaces.

## Failure paths and risks

- A service can be externally operated yet fail the public-retrieval condition.
- A signed receipt can prove operator attestation without proving append-only
  inclusion; the admitted profile must require the stronger proof.
- One checkpoint can prove inclusion while providing weak non-equivocation;
  witness/consistency requirements must be explicit in the provider profile.
- Provider key rotation or API changes can make a live lookup disagree with a
  still-valid historical proof; the two claims must remain separate.
- Publishing a digest can still correlate runs if another party knows the
  preimage.  Domain separation and digest-only submission reduce disclosure but
  do not provide information-theoretic privacy.
- The coordinator can know or disclose the mapping before release.  Route B
  does not detect that behavior and must never be cited as scorer-blindness
  evidence.
- A complete local proof bundle can be deleted by the coordinator.  Its absence
  makes the unit uncountable; the external entry does not excuse missing local
  binding material.
- A valid pin proves ordering for the retained chain only.  It cannot reveal a
  discarded or covert chain that was never submitted, and it must never be
  cited as attempt-count or selection-bias evidence.
- A verifier sees only supplied evidence roots and bundles.  Validating every
  supplied unit does not prove that the coordinator disclosed every eligible,
  authorized, attempted or successfully pinned unit.

## Evidence plan

Before any live provider call, focused offline tests must demonstrate:

1. canonical request bytes and independent reconstruction from an event-6
   fixture;
2. `chain_contract_sha256` comes from exact admitted protocol-contract bytes,
   whose event order must equal pinned `EVENT_SEQUENCE`;
3. the second-scorer ordinal is derived from pinned `EVENT_SEQUENCE`, current
   value 6, while the six-item conceptual prose is never used as an ordinal;
4. domain, contract, comparison, head, commitment and profile mutations each
   change the submitted digest and fail verification;
5. any provider-profile/request field that introduces a backward dependency in
   the documented derivation is rejected;
6. event 5, truncated event 6 and either changed scorer source fail before
   submission; event 6 directly binds only the second source and transitively
   binds the primary source through event 5;
7. after a pin exists, rebuilding or changing the local chain reconstructs a
   different request and fails event-7 verification; no test claims a coherent
   pre-pin rebuild is detectable;
8. event 7 cannot be accepted without verifier-reconstructed request bytes and
   successful offline proof verification;
9. a handwritten event 7 with plausible pin-shaped fields but no bundle fails
   with `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED`;
10. a handwritten event 7 carrying a complete valid bundle from another chain
    or comparison unit fails request reconstruction;
11. a raw receipt ID, caller boolean, serialized `verified_pin`, timestamp
    string, screenshot, cached response and local digest file are rejected;
12. valid inclusion/checkpoint/witness or consensus fixtures verify offline;
13. request, bundle path, bundle digest, entry, inclusion path, checkpoint,
    locator, trust root and profile mutations fail in `verify_chain(...)`;
14. public retrieval requiring submission credentials fails;
15. unavailable, pending, timed-out, stale, rate-limited and malformed responses
    all refuse mapping release;
16. mapping publication before proof returns `EXTERNAL_PIN_LATE` and cannot be
    repaired retrospectively;
17. retained proof still verifies with the network disabled;
18. missing long-term proof material degrades to
    `EXTERNAL_PIN_NOT_VERIFIABLE`, never success; and
19. claim tests reject `scorer_blind`, `independent_comparison`, bounded attempt
    count, complete unit selection, complete bundle discovery, absence of
    discarded/covert runs, population-level effect, `Gate3_pass` and
    Skill-effect conclusions derived from the pin.

An independent fixture verifier must be written from the admitted provider
profile rather than sharing parser/normalization code with the producer.

Only after those tests, provider-profile review and separate owner
authorization may one live non-counted qualification call be proposed.  That
call tests provider integration and public retrieval only; it is not the
ordering-chain rehearsal and is not Gate 3 evidence.

## Implementation tranche recommendation

No ordering-chain implementation is recommended from this candidate alone.
The next bounded tranche is provider qualification:

1. compare candidate services against every provider-profile requirement;
2. select one exact service and protocol version through owner decision;
3. retain official proof-format/trust-root references and one non-secret static
   proof fixture; and
4. demonstrate offline verification and unauthenticated public retrieval using
   fixture or documented public data, without submitting a Gate 3 pin.

If no provider meets the complete inclusion, public retrieval, independence and
offline longevity requirements, Route B returns `STOP`; the local ordering
chain remains insufficient and no rehearsal or counted pair is authorized.

Attempt-bounding feasibility is not bundled into that qualification tranche.
If separately funded, it begins with a provider-capability audit for a dedicated
single-tenant log or verifiable map with cryptographic query completeness.  Its
default result is `STOP` unless such a surface is demonstrated; no ordering
implementation budget may be silently spent on constructing one.

## Claim ceiling

This candidate may claim only that Route B's proposed authority, protocol,
failure behavior, retention requirements and evidence plan are explicit.  It
may not claim that:

- a provider has been selected, qualified, contacted or remains available;
- an external pin, proof bundle, verifier or release gate exists;
- the ordering property has been established for any comparison unit;
- attempt count is bounded, all attempts were observed, or no discarded,
  covert or unregistered run occurred;
- the reported units are the complete eligible, authorized, attempted or
  successfully pinned study population;
- every existing proof bundle was supplied to the verifier, or selective
  disclosure did not occur;
- scorer blindness or scorer independence has been established;
- historical Gate 2 has been repaired;
- a Gate 3 rehearsal or counted run is authorized;
- Gate 3 has started or the Bug Fix Skill is effective.

Acceptance of this design would authorize only the decision boundary, including
the narrow ordinal interpretation.  Provider selection, implementation,
network use, rehearsal and counted execution each require separate owner
authorization.
