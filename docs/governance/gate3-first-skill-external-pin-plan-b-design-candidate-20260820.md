# Gate 3 first-Skill external-pin Plan B design candidate

Status: **CANDIDATE — CONDITIONAL-TRUST MODEL DECIDED, REVISION 6 NOT YET
REVIEWED OR ACCEPTED.**

The owner confirmed Route B on 2026-08-20: do not use a second natural person
as the external-pin authority.  Use an externally operated, independently
verifiable append-only transparency or timestamp surface instead.  No provider
is selected by this document, and no submission, account creation, integration,
rehearsal or counted run is authorized.

Revision 5 uses a conditional-trust model.  The external operator's actual
independence is a run-admission premise accepted before the run; it is not a
conclusion derived from the retained proof.  The design can prevent the
coordinator from selecting a provider after seeing the run by binding the
accepted provider profile into the frozen protocol contract, but no account,
signature, proof bundle or repository artifact can prove that the operator is
not secretly controlled by or colluding with the coordinator.

Revision 6 makes the provider admission root independent of the run contract,
closes the proof-bundle wire schema and assigns disjoint failure predicates to
an absent event-7 manifest reference, an invalid manifest, a missing component
and mismatched component bytes.  It still does not select a provider or supply
the future owner-accepted admission bytes; their absence remains a hard stop
before implementation.

## Claim boundary — first page, before mechanism

Route B can establish one proposition:

> If the operator selected before the run is actually independent of the
> coordinator, the exact retained primary and second scorer submissions were
> already bound into the comparison unit's externally pinned digest-chain head
> before the canonical mapping-release gate emitted the mapping-release event.

Operator independence is borne by the pre-run admission decision and is not
established by this design's evidence.  If the admitted operator is actually
controlled by the coordinator, the ordering claim fails and the retained
evidence cannot reveal that hidden control relationship.  A profile digest
pinned before the run proves pre-commitment to that profile, not independence.

The requirement that public retrieval use no coordinator credential is also a
capture-time adapter and operator-qualification premise.  Retained request and
response bytes can show what the adapter supplied and what the service
returned, but an offline verifier cannot prove that a transport, cache or
operator used no undisclosed credential.  Offline verification establishes
bundle consistency with the admitted public-retrieval policy, not anonymous
retrieval as an independently observed historical fact.

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
  requires the **final head digest**, after event 7 exists, to be copied into a
  reviewer/owner receipt or another separately controlled append-only surface.
  Route B adds a distinct pre-release obligation: event 6 must be externally
  pinned before event 7 may be appended.  Event 6 is not redefined as the final
  head, and satisfying the pre-release pin does not discharge the amendment's
  final-head receipt requirement.
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
  external pin and remains synthetic and non-counted.  Its exact retained
  protocol-contract bytes predate Route B and its seven-event chain includes
  `0007-mapping-released.json`; a future Route B verifier must continue to
  validate that legacy chain under its historical contract semantics rather
  than applying the new external-pin obligation merely because event 7 exists.
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
8. require every later `verify_chain(...)` call under the new Route B protocol
   contract that accepts event 7 to
   independently reconstruct and verify the same request and proof bundle,
   regardless of how the event file was created; and
9. copy the exact event-7 final-head digest into the reviewer/owner receipt or
   another separately controlled append-only surface before the comparison
   unit may be classified as retained and countable.

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

This is an admission rule, not a proof result.  The owner must select and
accept the operator and profile before the protocol contract is frozen.  The
retained evidence can later show which profile was selected and whether its
protocol proof verifies; it cannot establish the truth of the organizational
independence premise.

### Verifier

The verifier's first trust input is the exact pre-authority provider-admission
artifact identified by constants in the owner-accepted implementation bytes.
It then trusts only profile, policy and trust-material bytes whose identities
that artifact pins, plus exact local chain bytes and a complete proof bundle.
The expected admission or profile identity is never selected from a caller,
run contract, event 7 or the bundle.  Those surfaces carry only copies that
must match the pre-authority root.  The verifier does not trust a caller-
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

The accepted profile's digest must be stored in the new Route B protocol
contract before any event for the run is written.  The contract must also copy
the admitted provider-admission digest.  Because every event binds the exact
protocol-contract digest, this makes the already-admitted provider selection a
pre-run commitment.  The run contract is not the source of that authority: it
must match the independent admission root defined below.  The profile,
verification-policy and trust-root copies inside the proof bundle are retained
inputs that must match that root, not a source from which the expected value
may be invented.

An API that returns only a server-generated timestamp or receipt identifier is
not sufficient.  A surface whose history can be edited by the coordinator, or
whose proof can be verified only by asking the same live API to say `valid`, is
not sufficient.

### Pre-authority provider admission artifact

Provider qualification must create exactly one canonical admission artifact at
the fixed repository-relative locator
`artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/gate3-external-pin-provider-admission.v1.json`.
It is outside every comparison-unit evidence root and no runtime argument may
replace, redirect or override that locator.

The artifact is canonical UTF-8 JSON with no BOM, sorted keys, compact
separators and one trailing LF.  Its top-level object contains exactly:

| Field | Exact value or role |
| --- | --- |
| `schema` | literal `gate3-external-pin-provider-admission.v1` |
| `provider_profile` | one identity object for the accepted profile bytes |
| `offline_verifier` | one identity object for the independently reviewed verifier bytes |
| `verification_policy` | one identity object for the exact offline verification-policy bytes |
| `trust_material` | array of every trust-root, witness-root or consensus-validation component admitted by the profile |
| `bundle_component_contract` | array fixing the exact role cardinality permitted in a proof-bundle manifest |

Each identity object contains exactly `locator`, `sha256` and `byte_length`.
Each `trust_material` item contains exactly `role`, `ordinal`, `locator`,
`sha256` and `byte_length`.  Each `bundle_component_contract` item contains
exactly `role` and `count`.  All digests are 64 lowercase hexadecimal
characters; byte lengths and counts are non-negative JSON integers, not
strings or floats.  Duplicate JSON keys, unknown fields, unknown roles,
duplicate `(role, ordinal)` pairs, duplicate locators, non-contiguous ordinals
or a trust-material count inconsistent with the component contract make the
artifact invalid.

Admission-bound component locators are fixed ASCII repository-relative paths
beneath
`artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/provider-admission/`.
The same absolute-path, drive/UNC, backslash, colon, NUL, empty-segment, `.`,
`..`, symlink, junction and reparse-point prohibitions defined for bundle
components below apply before any admission component is read.  Every locator
is also named in the owner decision; no locator is synthesized from a run
field.  `trust_material` must contain at least one item.  Both admission arrays
are canonical: `trust_material` is sorted by ASCII `role` then numeric
`ordinal`, and `bundle_component_contract` contains every role in the closed
bundle vocabulary exactly once in ASCII role order.  Every admission
`trust_material` item uses the literal role `trust_material`; its profile-
specific meaning is carried by the separately hashed profile and policy, not by
an open-ended manifest role.

The separate provider-qualification owner decision must name all of the
following before implementation begins:

- the fixed admission locator above;
- the exact admission-artifact SHA-256, byte length and Git blob object ID;
- the owner-accepted repository commit containing those exact bytes;
- the exact SHA-256 and byte length of the profile, verifier, policy and every
  trust-material component bound by the artifact; and
- the implementation commit whose constants pin the admission locator,
  SHA-256 and byte length and whose verifier bytes match the admitted verifier
  identity.

`ADMITTED_PROVIDER_ADMISSION_LOCATOR`,
`ADMITTED_PROVIDER_ADMISSION_SHA256` and
`ADMITTED_PROVIDER_ADMISSION_BYTE_LENGTH` are therefore compile/source-time
constants in the owner-accepted implementation, not parameters.  Before a run
contract or event is parsed, the verifier reads the fixed artifact, checks its
exact identity against those constants, applies the closed-schema rules above,
then loads and hashes every bound component.  Only after that step may it
require the Route B contract's `provider_admission_sha256` and
`provider_profile_sha256` copies to match.  A caller, event 7 or bundle cannot
select a different authority by supplying a self-consistent profile and proof.

This bootstrap is deliberately acyclic.  The admitted `offline_verifier` bytes
must not contain the admission artifact digest or any of the three
`ADMITTED_PROVIDER_ADMISSION_*` constants.  A separate bootstrap module in the
owner-accepted implementation commit owns those constants, verifies and freezes
the admission/profile/policy/trust byte map, and then invokes the admitted pure
offline verifier with that already-verified map.  The artifact pins the pure
verifier; the owner decision pins the complete implementation commit.  An
implementation that embeds the admission digest inside the verifier bytes that
the admission artifact hashes is cyclic and invalid.

The admission artifact must not contain a comparison identity, request digest,
entry locator, proof digest, bundle-manifest identity or event digest.  It is a
pre-run authority root, not a receptacle for producer-derived values.  Until
the fixed artifact, exact identities, owner decision and pinning implementation
commit all exist, the result is `EXTERNAL_PIN_ADMISSION_INVALID` and no Route B
run contract may be admitted.

## Protocol version and legacy compatibility

The existing exact `gate3-protocol-contract-v1.json` bytes are a historical
authority for the retained 2026-07-29 rehearsal and must not be overwritten to
introduce Route B.  The earlier proposal to add the provider-profile digest to
that existing file is superseded by this compatibility requirement.  Route B
must mint a new versioned protocol contract whose closed external-pin section
contains at least the request schema, admitted
`provider_admission_sha256`, admitted `provider_profile_sha256`,
profile-bound trust-material digests and the literal activation policy
`required_for_mapping_release`.  Every copied identity must match the
pre-authority artifact; a self-consistent run contract is not independently
authoritative.

Each verifier invocation receives one exact contract path, loads its bytes and
requires every event's `contract_sha256` to match.  External-pin semantics are
activated only when that loaded, recognized contract version declares them;
the presence of `mapping_released` alone is not an activation signal.  Unknown
contract versions fail closed.  The legacy v1 verifier path continues to
validate the retained rehearsal as a local-chain-only, synthetic, non-counted
artifact and must not upgrade its claim.

The implementation tranche may add the smallest explicit version dispatch
needed for these two admitted contracts.  It may not rewrite v1 in place,
silently migrate existing event files or infer semantics from optional fields.

## Canonical pin request

The local request is canonical UTF-8 JSON with sorted keys, compact separators
and one trailing LF.  Its closed schema is
`gate3-external-ordering-pin-request.v1` and contains exactly:

| Field | Meaning |
| --- | --- |
| `schema` | literal schema name |
| `domain` | literal `gate3-first-skill-ordering-head-v1` |
| `chain_contract_sha256` | digest of the exact admitted versioned protocol-contract bytes loaded by `load_contract(...)` |
| `comparison_unit_sha256` | digest of the canonical comparison identity, not its raw label |
| `head_event` | literal `second_scorer_submitted` |
| `head_ordinal` | derived from pinned `EVENT_SEQUENCE`; current value `6` |
| `head_event_sha256` | digest of exact event-6 bytes |
| `mapping_commitment_sha256` | commitment copied from verified event 1 |
| `provider_admission_sha256` | digest copied from the independently pinned admission root, after the contract copy is matched to it |
| `provider_profile_sha256` | digest copied from the frozen Route B protocol contract, never selected from the bundle |

`chain_contract_sha256` is not a digest of the Python tuple or the amendment's
conceptual list.  It is the digest returned by `load_contract(...)` for the
exact admitted versioned contract bytes.  The Route B contract
must contain an `evidence_chain.event_order` exactly equal to the pinned runtime
`EVENT_SEQUENCE`; disagreement fails before request construction.  The JSON
file is the byte authority for `chain_contract_sha256`, while the pinned runtime
tuple is the ordinal authority.  Neither silently substitutes for the other.
The request's `provider_profile_sha256` must equal the value already present in
those frozen contract bytes, and both that value and
`provider_admission_sha256` must first match the pre-authority admission root.

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
provider admission + protocol contract + comparison identity + event 6
    -> canonical pin request -> submitted digest -> provider proof bundle
    -> event 7
```

The provider admission artifact and provider profile must not contain an
expected request digest, entry locator, proof digest, bundle-manifest digest or
event-7 digest.  The request must not contain any locator, proof, bundle or
event-7 value.  Any dependency pointing backward across that sequence is
invalid rather than resolved by iteration.

## Proof bundle

Pin finalization must capture complete bytes, not merely an entry ID.  The
closed local bundle manifest is
`gate3-external-ordering-proof-bundle.v1`.  It uses the same canonical JSON
encoding as the pin request and contains exactly these top-level fields:

| Field | Exact value or role |
| --- | --- |
| `schema` | literal `gate3-external-ordering-proof-bundle.v1` |
| `provider_admission_sha256` | digest of the pre-authority admission artifact |
| `provider_profile_sha256` | digest of its admitted profile component |
| `pin_request_sha256` | digest of the exact canonical request bytes |
| `stable_entry_locator` | locator in the exact canonical syntax admitted by the profile |
| `checkpoint_or_anchor_sha256` | digest of the single checkpoint/anchor component |
| `components` | ordered array of component identity objects |

Each component identity object contains exactly `role`, `ordinal`, `locator`,
`sha256` and `byte_length`.  `components` is sorted first by ASCII `role`, then
numeric `ordinal`; any other order is non-canonical.  The closed role vocabulary
is:

```text
pin_request
provider_submission_request
provider_submission_response
integrated_entry
inclusion_proof
checkpoint_or_anchor
provider_profile
verification_policy
public_retrieval_request
public_retrieval_response
trust_material
consistency_material
witness_material
consensus_material
provider_auxiliary_proof
```

The first ten roles occur exactly once with ordinal `0`; their admission-
artifact contract entries must therefore carry `count: 1`.  The pre-authority
admission artifact fixes the exact count of every remaining role; no producer,
request, event or manifest may change those counts.  Ordinals for every role
must be contiguous from `0` through `count - 1`.  Unknown or duplicate JSON
keys, unknown roles, duplicate `(role, ordinal)` pairs, duplicate locators,
missing ordinals, extra components or a role-count mismatch are invalid.

Every component locator is relative to the manifest's bundle directory and
must equal the derived ASCII form
`components/<role>-<ordinal>-<sha256>.bin`.  Absolute paths, URI syntax, drive
or UNC prefixes, backslashes, colon, NUL, empty segments, `.` or `..`, Unicode
lookalikes, symlinks, junctions and other reparse points are forbidden.  The
derived target must remain a strict regular-file descendant of the bundle
directory.  The event-7 manifest locator is not caller-selected; it must equal
`external-pin/<comparison_unit_sha256>/proof-bundle-manifest.v1.json` beneath
the comparison evidence root.

Opaque provider bytes remain opaque.  The manifest records their exact digests,
lengths and roles; it does not normalize or reserialize them.  Complete
inclusion paths, consistency data or provider-specific proof sequences are each
captured as opaque component bytes under the exact role counts admitted before
the run.

The producer snapshot rule is create-once components first and manifest last.
It captures each network request, response and derived proof component into one
immutable byte array, writes each derived component locator with create-new
semantics, re-reads that file exactly once, and computes the manifest digest and
length from that one in-memory copy.  Only after every required component is
present and matched may it create the canonical manifest once.  It must not
overwrite, merge or refill a component after manifest creation.

The verifier snapshot rule is manifest once, then every component once.  It
derives the manifest locator, reads the exact manifest bytes into memory once,
checks the event-7 digest and length, parses with duplicate-key rejection, and
validates the closed schema before opening components.  It then derives and
path-validates every component locator, rejects link/reparse traversal, reads
each regular file into memory once, and uses that same byte array for length,
digest and semantic proof verification.  No later path re-read may feed the
decision.  This captured manifest plus captured component byte map is the one
coherent verifier snapshot; later filesystem mutation cannot change the bytes
already used for the verdict.

The public retrieval must be possible using the stable entry locator and public
profile alone.  A successful read using cached submission credentials is not
evidence of third-party retrievability.  The adapter must retain the exact
public retrieval request and response and must be exercised without receiving
a coordinator credential.  This is sensitivity evidence for the adapter
boundary, not proof that no hidden credential existed below that boundary; the
claim limitation stated on the first page remains controlling.

## Producer and release-gate sequence

1. Verify the fixed pre-authority admission artifact and all profile, verifier,
   policy and trust-material bytes it binds; then require the frozen
   protocol-contract copies to match that authority and verify exact events
   1–6.
2. Require event 5 to bind the primary scorer source and event 6 to bind the
   second scorer source.  Require both files to match their retained digests and
   event 6's previous-event digest to bind the exact event-5 bytes.
3. Construct the canonical pin request from the verified chain.
4. Before the first network call, freeze a create-once submission-attempt
   record binding the request digest, provider-profile digest and any
   provider-defined idempotency key.  Submit its digest exactly once.  A later
   call may only finalize or retrieve the recorded stable operation, or replay
   the exact provider-defined idempotent operation when the admitted profile
   proves that such replay cannot create another logical entry.  It must never
   start a new append.  An ambiguous outcome without a resumable stable handle
   or admitted idempotent replay fails closed; a later submission attempt
   returns `EXTERNAL_PIN_ALREADY_USED`.
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
11. Compute the SHA-256 of the exact event-7 bytes and copy that final head
    digest into the reviewer/owner receipt or another separately controlled
    append-only surface.  Until that copy is retained and verifiable, the
    mapping is released but the comparison unit is not retained or countable.

Event 7 must bind the exact fields `proof_bundle_manifest_locator`,
`proof_bundle_manifest_sha256` and `proof_bundle_manifest_byte_length`, plus
the pin-request digest, provider-admission digest, provider-profile digest,
stable entry locator and checkpoint/anchor digest.  The manifest locator must
equal the derived fixed form above; no arbitrary path is admitted.  The mapping
artifact must not be published to the scorer-visible or public evidence surface
before this gate succeeds.  This is a canonical-release guarantee only; it does
not prove the coordinator lacked or never disclosed the mapping out of band.

### Verification-side obligation

The `verify_chain(...)` `mapping_released` branch is the authority for accepting
event 7 under the new Route B contract.  It must not trust pin-shaped fields
merely because they are present or because `release_mapping(...)` normally
writes them.  For every event-7 verification activated by that contract it
must:

1. verify events 1–6 and retain their exact bytes;
2. reconstruct the canonical pin request and compare its bytes and digest with
   both event 7 and the bundle manifest;
3. require event 7 to contain all three manifest-reference identity fields,
   derive the only allowed locator beneath the evidence root, and verify the
   exact manifest digest and byte length recorded in event 7;
4. parse the manifest under the closed schema, role-cardinality, canonicality,
   locator and coherent-snapshot rules above and load every required component;
5. independently load the fixed pre-authority admission artifact, verify it
   against the owner-accepted implementation constants, and require the
   contract, event 7, manifest, profile, policy and trust-material copies all to
   match it;
6. re-run offline inclusion/checkpoint/witness or consensus verification over
   the retained provider bytes; and
7. compare the verifier-derived locator and checkpoint/anchor digest with event
   7 before accepting `mapping_released`.

A caller boolean, a serialized `verified_pin`, or fields copied into a handmade
event file are not authority.  `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED` applies
only when a Route B event 7 omits one or more of its three required manifest-
reference identity fields.  Once all three fields exist, invalid manifest bytes
fail with `EXTERNAL_PIN_BUNDLE_MANIFEST_INVALID`; a manifest that has parsed and
passed the closed schema but references an absent required component fails with
`EXTERNAL_PIN_BUNDLE_INCOMPLETE`; present bytes whose digest or length differs
fail with `EXTERNAL_PIN_BUNDLE_COMPONENT_MISMATCH`.  These predicates are
disjoint.  Thus a handwritten event 7 cannot become valid by bypassing
`release_mapping(...)`.

This obligation is contract-versioned.  A legacy contract that does not
declare Route B is verified under its admitted historical semantics and is not
failed with `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED`.  Conversely, a Route B
event 7 cannot downgrade itself by omitting external-pin fields or presenting a
legacy contract digest.

Final-head receipt verification is a distinct countability check because its
subject is the event-7 digest and therefore cannot be embedded in event 7
without a cycle.  The countability check must verify the retained
reviewer/owner receipt or separately controlled append record against the exact
event-7 bytes.  A valid event-6 pin without that final-head record preserves
the release-order evidence but leaves the unit uncountable.

This future Route B condition intentionally differs from, but does not modify,
expand or supersede, the current C1 frozen D5 policy identified by the immutable
external cross-reference
`1ced27d08e0330ca5ebe21ed241f0074ec500958:artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/c1-d5-countability-amendment-20260826/d5-countability-policy.json`
(the referenced commit is not inherited through `007bd77a` ancestry):
`CURRENT_C1_FINAL_HEAD_RECEIPT_NOT_REQUIRED`,
`decision_scope=internal_skill_funding_only`,
`required_for_current_c1=false` and `absence_alone=NOT_A_FAILURE`.  That D5
policy remains limited to current C1 internal Skill-funding countability; this
candidate's final-head condition applies only to a future Route B and does not
become approved through this cross-reference.

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
| `EXTERNAL_PIN_ADMISSION_INVALID` | fixed admission artifact absent, identity-mismatched, malformed, not owner-pinned by the implementation, or inconsistent with its bound profile/verifier/policy/trust bytes |
| `EXTERNAL_PIN_PROFILE_INVALID` | profile absent, changed, unknown or unsupported |
| `EXTERNAL_PIN_REQUEST_MISMATCH` | reconstructed request or submitted digest differs |
| `EXTERNAL_PIN_ALREADY_USED` | a create-once submission-attempt record already exists and no admitted resume/idempotent operation applies |
| `EXTERNAL_PIN_SUBMISSION_FAILED` | submission fails before a stable locator exists |
| `EXTERNAL_PIN_NOT_FINAL` | timeout, pending or provider finality unknown |
| `EXTERNAL_PIN_UNAVAILABLE` | entry or proof cannot be retrieved before release |
| `EXTERNAL_PIN_PUBLIC_READ_REQUIRED` | retrieval needs coordinator credentials |
| `EXTERNAL_PIN_ENTRY_MISMATCH` | retrieved entry does not contain the submitted digest |
| `EXTERNAL_PIN_PROOF_INVALID` | inclusion, checkpoint, witness, consensus or signature verification fails |
| `EXTERNAL_PIN_CHECKPOINT_STALE` | checkpoint violates the admitted freshness/finality policy |
| `EXTERNAL_PIN_BUNDLE_MANIFEST_INVALID` | referenced manifest bytes fail identity, canonical serialization, closed-schema, role-cardinality or locator-safety validation |
| `EXTERNAL_PIN_BUNDLE_INCOMPLETE` | the manifest parsed and passed its closed schema, but a required referenced component file is absent or unreadable |
| `EXTERNAL_PIN_BUNDLE_COMPONENT_MISMATCH` | a referenced component exists but its exact byte length or SHA-256 does not match the valid manifest |
| `EXTERNAL_PIN_LATE` | mapping release or mapping publication already exists |
| `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED` | Route B event-7 construction or verification omits `proof_bundle_manifest_locator`, `proof_bundle_manifest_sha256` or `proof_bundle_manifest_byte_length` |
| `FINAL_HEAD_RECEIPT_REQUIRED` | Route B event 7 exists but its exact final-head digest is absent or invalid on the admitted receipt/surface |

Absence, timeout, DNS/TLS failure, rate limit, stale checkpoint, API drift,
unknown key state, malformed proof, mismatched bytes and ambiguous provider
status all refuse release.  There is no temporary release, offline override,
manual `PASS`, retrospective pin or “release now, attach proof later” path.
The final-head receipt is necessarily written after event 7 and is not a
retrospective substitute for the event-6 pre-release pin.  Failure to retain it
does not erase the released mapping; it prevents the comparison unit from
becoming countable.

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
- one new versioned Route B protocol contract while retaining the exact legacy
  v1 contract bytes;
- focused fixtures and mutation tests; and
- the smallest producer and verifier changes in
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/
  gate3_evidence_chain.py`: `release_mapping(...)` must construct event 7 only
  after proof, and `verify_chain(...)` must independently reject any event 7
  activated by the Route B contract whose request or proof cannot be
  reconstructed.  Focused tests cover both.

No shared `governance_tools`, runtime hook, CI workflow, schema registry,
production route, M3/M4 module or credential-bearing live runner belongs to the
first tranche.

## Boundary and API considerations

The provider adapter needs four conceptual operations:

```text
load_fixed_admission() -> verified_admission
submit(request_digest) -> stable_locator_or_pending_handle
finalize(locator_or_handle) -> raw_proof_components
retrieve_public(stable_locator) -> raw_retrieval_components
verify_offline(request_bytes, proof_bundle_snapshot) -> verified_pin
```

`load_fixed_admission()` is an internal bootstrap with no path, digest, profile
or trust-material argument.  The other operations consume only its frozen
internal result; no public operation accepts an admission/profile substitute.

The release gate accepts only an opaque `verified_pin` minted by the offline
verifier.  It has no boolean override and no API accepting a raw receipt ID,
timestamp, digest, URL or provider response as equivalent authority.

Network operations remain outside the deterministic chain verifier.  Retained
proof verification is offline and deterministic; provider qualification and
live submission are separate authority-bearing surfaces.

The reviewer/owner final-head receipt is downstream of event 7 and outside the
pin-request derivation.  It cannot feed any value back into event 7.  The
countability audit consumes it as a separate append-only record and compares it
to a freshly computed digest of the exact event-7 bytes.

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
- The admitted operator can be secretly controlled by or colluding with the
  coordinator.  The pre-run contract makes the selection visible and fixed but
  cannot reveal that hidden relationship; if the independence premise is
  false, the ordering claim is invalid.
- A capture can appear credential-free at the adapter API while a lower
  transport layer, cache or operator uses an undisclosed credential.  Offline
  proof verification does not detect that condition.
- Event 7 can be validly released after its event-6 pin while final-head receipt
  retention fails.  That chain is released but uncountable; the design does
  not pretend the event can be rolled back.

## Evidence plan

Before any live provider call, focused offline tests must demonstrate:

1. canonical request bytes and independent reconstruction from an event-6
   fixture;
2. `chain_contract_sha256` comes from exact admitted protocol-contract bytes,
   whose event order must equal pinned `EVENT_SEQUENCE`; the Route B contract
   contains the expected provider-admission and provider-profile digests before
   event 1, both match the fixed admission root pinned by the implementation,
   and the legacy v1 bytes remain unchanged;
3. the second-scorer ordinal is derived from pinned `EVENT_SEQUENCE`, current
   value 6, while the six-item conceptual prose is never used as an ordinal;
4. domain, contract, comparison, head, commitment, admission and profile
   mutations each change the submitted digest and fail verification;
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
9. a Route B event 7 missing any one of the manifest locator, SHA-256 or byte-
   length identity fields fails only with
   `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED`;
10. event 7 with all three reference fields but non-canonical, unknown-field,
    duplicate-key, duplicate-role, role-count or unsafe-locator manifest bytes
    fails only with `EXTERNAL_PIN_BUNDLE_MANIFEST_INVALID`;
11. a canonical manifest that has passed schema validation but whose required
    component file is absent fails only with
    `EXTERNAL_PIN_BUNDLE_INCOMPLETE`;
12. a present component with changed length or digest fails only with
    `EXTERNAL_PIN_BUNDLE_COMPONENT_MISMATCH`, and semantic verification consumes
    the same captured bytes rather than reopening its path;
13. a caller-selected admission path/digest, or a self-consistent contract,
    event 7 and bundle built around an unadmitted profile, fails with
    `EXTERNAL_PIN_ADMISSION_INVALID` before proof verification;
14. a handwritten event 7 carrying a complete valid bundle from another chain
    or comparison unit fails request reconstruction;
15. a raw receipt ID, caller boolean, serialized `verified_pin`, timestamp
    string, screenshot, cached response and local digest file are rejected;
16. valid inclusion/checkpoint/witness or consensus fixtures verify offline;
17. request, bundle path, bundle digest, entry, inclusion path, checkpoint,
    locator, trust root and profile mutations fail in `verify_chain(...)`;
18. public retrieval requiring submission credentials fails at the adapter
    boundary, while the test and claim text explicitly do not represent this
    as proof against hidden transport/cache credentials;
19. unavailable, pending, timed-out, stale, rate-limited and malformed responses
    all refuse mapping release;
20. mapping publication before proof returns `EXTERNAL_PIN_LATE` and cannot be
    repaired retrospectively;
21. retained proof still verifies with the network disabled;
22. missing long-term proof material degrades to
    `EXTERNAL_PIN_NOT_VERIFIABLE`, never success;
23. a second logical submission after the create-once attempt record returns
    `EXTERNAL_PIN_ALREADY_USED`; exact admitted resume/idempotent replay cannot
    create a second logical entry, and removal of that guard makes the
    sensitivity test fail;
24. the retained 2026-07-29 rehearsal verifies under its exact legacy v1
    contract and remains synthetic/non-counted, while the same event-7 shape
    under the Route B contract fails without its external bundle;
25. the exact event-7 digest matches the separately retained final-head receipt;
    missing or altered receipt bytes return `FINAL_HEAD_RECEIPT_REQUIRED` and
    leave the unit uncountable; and
26. claim tests reject `scorer_blind`, `independent_comparison`, bounded attempt
    count, complete unit selection, complete bundle discovery, absence of
    discarded/covert runs, population-level effect, `Gate3_pass` and
    Skill-effect conclusions derived from the pin, and reject any statement
    that the proof establishes operator independence or credential-free
    historical capture.

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
- operator independence has been established by the retained evidence;
- credential-free historical retrieval has been established by offline proof;
- historical Gate 2 has been repaired;
- a Gate 3 rehearsal or counted run is authorized;
- Gate 3 has started or the Bug Fix Skill is effective.

Acceptance of this design would authorize only the decision boundary, including
the conditional-trust premise, the narrow ordinal interpretation, the distinct
event-6 pin and event-7 final-head obligations, and versioned legacy
compatibility.  Provider selection, implementation, network use, rehearsal and
counted execution each require separate owner authorization.
