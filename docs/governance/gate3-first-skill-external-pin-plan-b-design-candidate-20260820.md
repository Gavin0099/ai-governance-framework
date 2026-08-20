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

A single post-scoring pin would not establish how many attempts were made.  A
coordinator could discard an unfavourable local run, rebuild the chain and pin
a different digest; opaque external digests would not let a verifier discover
that selection.  This design therefore requires a searchable, two-phase
registration for every **authorized comparison identity**, plus a complete
query of a campaign-dedicated provider namespace.  That mechanism can establish
the number of registered attempts under the admitted namespace and expose a new
tag invented after an unfavourable result.  It still cannot prove that no
covert, off-system or unauthorized run occurred outside that namespace.

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

  `attempt_open` is an external preregistration action completed before local
  event 1.  It is not an eighth chain event and does not alter
  `EVENT_SEQUENCE`.
- The 2026-07-29 rehearsal proves local mechanics only.  It has no qualifying
  external pin and remains synthetic and non-counted.
- No external transparency/timestamp provider, provider profile, trust root or
  verification adapter is currently selected or admitted.

## Target outcome

Define a service-neutral contract under which a future implementation can:

1. freeze the closed set of canonical comparison identities in one accepted run
   authorization;
2. derive a stable domain-separated attempt tag from that identity;
3. before event 1, randomization or any outcome production, integrate one
   searchable `attempt_open` entry into a qualified external surface;
4. reconstruct and verify events 1 through 6, then integrate one searchable
   `scoring_head` entry for the same attempt tag;
5. query the campaign-dedicated provider namespace and require exactly the
   authorized tags and phase entries, with no duplicate, unknown tag or
   additional entry;
6. retrieve both entries and complete inclusion proofs through a public read
   path requiring no coordinator-held secret;
7. verify the retained proofs offline against pinned trust material; and
8. only then permit event 7 to publish the mapping and nonce.

The output is a durable proof bundle that another actor can verify without the
submission credential and, after initial capture, without the provider API.

## Scope

- External operator and authority requirements.
- Provider-profile admission requirements without selecting a provider.
- Canonical comparison identity, attempt-tag and two-phase request encoding.
- Searchability, namespace admission and the explicit privacy trade-off.
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
  secrecy, absence of out-of-band disclosure, lack of collusion or absence of
  covert/unregistered runs.
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
coordinator secret for another actor to retrieve entries or complete queries.

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
- one campaign-dedicated provider namespace, the accepted run-authorization
  digest bound to it, and the submission identity authorized to append within
  it;
- digest algorithm and exact submitted-value encoding;
- exact query semantics and a cryptographically verifiable completeness or
  non-omission proof for every integrated entry in that namespace, including
  tag-filtered and whole-namespace views, without coordinator credentials;
- integration/finality definition and maximum wait policy;
- stable entry locator syntax;
- complete inclusion-proof format;
- signed checkpoint, witnessed checkpoint or consensus-anchor format;
- offline verification algorithm and implementation identity;
- trust-root or consensus-validation bytes;
- key rotation, revocation and algorithm-deprecation interpretation;
- public retrieval authentication policy, which must require no coordinator
  credential; and
- privacy statement for visible namespace/phase/tag fields, request digests and
  retained locator metadata.

An API that returns only a server-generated timestamp or receipt identifier is
not sufficient.  A surface whose history can be edited by the coordinator,
whose namespace query can omit integrated entries without cryptographic
detection, or whose proof can be verified only by asking the same live API to
say `valid`, is not sufficient.

## Canonical identity, attempt tag and pin requests

The accepted run authorization freezes a closed set of comparison identities
before any `attempt_open`, event 1 or producer execution.  Its canonical
`gate3-comparison-unit-identity.v1` UTF-8 JSON contains exactly `schema`,
`task_id`, `pair_id`, `repeat_index` and `study_kind`, with sorted keys, compact
separators and one trailing LF.  The authorization binds the sorted list of all
identity digests and attempt tags plus the campaign-dedicated provider
namespace.  Each randomization record must carry its authorized identity.
Relabelling a completed or abandoned run by changing any identity field is
forbidden.  Adding, replacing or removing an identity after the first open
invalidates the campaign; it cannot be repaired by a later authorization.

The authorization itself is canonical UTF-8 JSON under the closed schema
`gate3-first-skill-run-authorization.v1`, using the same sorted-key, compact-
separator and trailing-LF rules.  It contains exactly `schema`,
`provider_namespace`, `provider_profile_sha256`, `chain_contract_sha256` and
`comparison_identities`.  The last field is the complete array of canonical
comparison-identity objects sorted by their derived attempt tag.  The accepted
authorization bytes are immutable; every phase request carries their digest.

The stable searchable tag is:

```text
sha256(b"gate3-first-skill-attempt-v1\0" +
       canonical_comparison_identity_bytes).hexdigest()
```

The NUL byte is part of the domain separator.  `comparison_unit_sha256` remains
the SHA-256 of the same canonical identity bytes.  The two values intentionally
have different domains and must not be substituted for one another.

Each phase request is canonical UTF-8 JSON under the closed schema
`gate3-external-ordering-pin-request.v2` and contains exactly:

| Field | Meaning |
| --- | --- |
| `schema` | literal schema name |
| `domain` | literal `gate3-first-skill-ordering-pin-v2` |
| `phase` | literal `attempt_open` or `scoring_head` |
| `attempt_tag` | stable domain-separated tag above |
| `chain_contract_sha256` | digest of the exact admitted ordering contract |
| `comparison_unit_sha256` | digest of the canonical comparison identity |
| `run_authorization_sha256` | digest of the accepted authorization that froze this identity |
| `head_event` | JSON `null` for open; `second_scorer_submitted` for scoring head |
| `head_ordinal` | JSON `null` for open; derived from pinned `EVENT_SEQUENCE`, currently 6, for scoring head |
| `head_event_sha256` | JSON `null` for open; digest of exact event-6 bytes for scoring head |
| `mapping_commitment_sha256` | JSON `null` for open; commitment copied from verified event 1 for scoring head |
| `provider_profile_sha256` | digest of the admitted provider profile |

The bytes submitted to the provider are canonical
`gate3-external-ordering-log-entry.v1` UTF-8 JSON containing exactly `schema`,
the admitted `namespace`, `phase`, `attempt_tag` and
`pin_request_sha256 = sha256(canonical_pin_request_bytes).hexdigest()`.  The
phase and tag are deliberately visible and queryable; the request contents
remain digest-bound rather than disclosed.

The external surface receives no task text, path, repository name, treatment
mapping, nonce, scorer identity, model identity, score, prompt, credential or
raw event bytes.  Nevertheless, a party that knows or can enumerate the
comparison-identity preimage can correlate entries.  Acceptance explicitly
chooses same-unit searchability and attempt-count auditability over unlinkability
for these tags; digesting the identity does not make low-entropy identifiers
secret.

Domain separation prevents bytes created for another protocol or phase from
being relabelled as a Gate 3 ordering pin.  The verifier recomputes every field
from retained authorization and chain bytes; no digest-shaped caller input is
accepted as authority.

## Proof bundle

Pin finalization must capture complete bytes, not merely an entry ID.  The
closed local bundle manifest is
`gate3-external-ordering-proof-bundle.v2` and binds the SHA-256 and byte length
of every retained component:

- accepted run-authorization and canonical comparison-identity bytes;
- both canonical phase-request byte strings;
- both exact provider submission byte strings and responses;
- both integrated entries;
- tag-specific and whole-namespace query responses plus completeness/non-
  omission proofs for the full entry sets at release time;
- complete inclusion paths or equivalent proofs for both entries;
- signed/witnessed checkpoints or consensus anchors;
- any required consistency or witness material connecting those checkpoints;
- admitted provider-profile bytes;
- trust-root/verification-policy bytes; and
- a second exact retrieval response obtained through the public read path.

Opaque provider bytes remain opaque.  The canonical manifest records their
digests and roles; it does not normalize or reserialize them.

The public retrieval and namespace/tag query must be possible using stable
entry locators and the public profile alone.  A successful read or query using
cached submission credentials is not evidence of third-party retrievability.

## Producer and release-gate sequence

1. Verify the accepted run authorization, frozen comparison identity and chain
   contract before event 1 or any producer executes.
2. Derive the attempt tag.  Query the whole campaign namespace.  Require no
   entry for that tag and require every existing entry to describe a previously
   verified authorized attempt; before the campaign's first open, the namespace
   must be empty.
3. Construct and submit exactly one `attempt_open` entry.  Wait for finality,
   retrieve it publicly and verify its proof offline.  An integrated open
   consumes that authorized identity even if the run later aborts.
4. Only after the verified open, execute and verify events 1–6.  Require event
   6 to bind both scorer submission source files and require those files to
   match retained digests.
5. Construct and submit exactly one `scoring_head` entry for the same attempt
   tag.  A retry may only poll or retrieve the same provider entry; it may not
   create a second logical entry under a different request.
6. Wait for finality, retrieve the scoring-head entry publicly and verify its
   proof offline against the pinned profile and trust material.
7. Query the campaign namespace through the public read path, both by current
   tag and without a tag filter.  Require no unknown tag, exactly one
   `attempt_open` for every started authorized identity, at most one
   `scoring_head` for each open, exactly one scoring head for the unit being
   released, no unknown phase, and request digests equal to independently
   reconstructed requests.  An authorized identity with no open is not an
   attempt; an open without a scoring head is a visible abandoned attempt.
8. Freeze the two-entry proof bundle create-once under the comparison evidence
   root.
9. Re-run local event 1–6 verification, reconstruct both requests and repeat
   both complete namespace queries.
10. Only then may `release_mapping(...)` validate the mapping/nonce commitment
    and append event 7.

Event 7 must bind the proof-bundle manifest digest, both pin-request digests,
both stable entry locators, provider-profile digest, attempt tag, namespace and
checkpoint/anchor digests.  The mapping artifact must not be published to the
scorer-visible or public evidence surface before this gate succeeds.  This is a
canonical registered-attempt and release guarantee only; it does not prove the
coordinator lacked or never disclosed the mapping out of band, or that no
unregistered execution occurred.

## Time and ordering semantics

The trusted statement is relative ordering, not precise wall-clock time:

1. the external operator integrated the open request digest into the retained
   checkpoint/anchor before event 1, randomization or outcome production began;
2. the operator later integrated the scoring-head request, which binds exact
   event-6 bytes and therefore both retained scorer submissions through the
   previous-digest chain;
3. the public queries returned exactly those two registered entries for the
   frozen attempt tag and no unknown tag or phase in the campaign namespace;
4. the canonical release gate appended event 7 only after verifying both proofs
   and that complete query result.

Provider timestamps may be retained, but no local timestamp comparison can
substitute for inclusion and gate sequence.  Clock skew, timezone text and file
mtime never decide validity.

## Fail-closed errors and refusal conditions

The future adapter must expose closed error codes and no provider response body,
path, credential or submitted value in exceptions.  At minimum:

| Code | Refusal |
| --- | --- |
| `EXTERNAL_PIN_PROFILE_INVALID` | profile absent, changed, unknown or unsupported |
| `EXTERNAL_PIN_IDENTITY_NOT_AUTHORIZED` | identity is not in accepted run authorization |
| `EXTERNAL_PIN_ATTEMPT_TAG_MISMATCH` | derived tag, namespace or submitted searchable fields differ |
| `EXTERNAL_PIN_REQUEST_MISMATCH` | reconstructed phase request or submitted digest differs |
| `EXTERNAL_PIN_SUBMISSION_FAILED` | submission fails before a stable locator exists |
| `EXTERNAL_PIN_NOT_FINAL` | timeout, pending or provider finality unknown |
| `EXTERNAL_PIN_UNAVAILABLE` | entry or proof cannot be retrieved before release |
| `EXTERNAL_PIN_PUBLIC_READ_REQUIRED` | retrieval needs coordinator credentials |
| `EXTERNAL_PIN_ENTRY_MISMATCH` | retrieved entry does not contain the submitted digest |
| `EXTERNAL_PIN_PROOF_INVALID` | inclusion, checkpoint, witness, consensus or signature verification fails |
| `EXTERNAL_PIN_CHECKPOINT_STALE` | checkpoint violates the admitted freshness/finality policy |
| `EXTERNAL_PIN_BUNDLE_INCOMPLETE` | any required raw component is absent |
| `EXTERNAL_PIN_OPEN_ALREADY_EXISTS` | current tag has an entry before open, or has duplicate opens |
| `EXTERNAL_PIN_OPEN_REQUIRED` | scoring-head submission is attempted without one verified open entry |
| `EXTERNAL_PIN_SCORING_HEAD_ALREADY_EXISTS` | more than one scoring-head entry exists for the tag |
| `EXTERNAL_PIN_ENTRY_SET_INVALID` | query is incomplete, unknown, duplicated or inconsistent with authorization |
| `EXTERNAL_PIN_NAMESPACE_MISMATCH` | entry or query is outside the admitted namespace/submission identity |
| `EXTERNAL_PIN_LATE` | mapping release or mapping publication already exists |
| `MAPPING_RELEASE_EXTERNAL_PIN_REQUIRED` | release is attempted without a verified bundle |

Absence, timeout, DNS/TLS failure, rate limit, stale checkpoint, API drift,
unknown key state, malformed proof, mismatched bytes and ambiguous provider
status all refuse release.  There is no temporary release, offline override,
manual `PASS`, retrospective pin or “release now, attach proof later” path.
An abandoned `attempt_open` remains consumed and publicly discoverable; it may
not be deleted, relabelled or reused.  Continuing requires a separately
authorized comparison identity, not an increment invented after observing the
abandoned or completed result.

## Long-term verification and service disappearance

Both complete inclusion proofs, their checkpoint/anchor and consistency
material, the complete tag and whole-namespace query responses, trust material
and verifier policy are captured before release because entry locators are not
durable proof.

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
- the smallest release-gate change in
  `artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/
  gate3_evidence_chain.py` plus its focused tests.

No shared `governance_tools`, runtime hook, CI workflow, schema registry,
production route, M3/M4 module or credential-bearing live runner belongs to the
first tranche.

## Boundary and API considerations

The provider adapter needs five conceptual operations:

```text
submit(log_entry_bytes, admitted_profile) -> stable_locator_or_pending_handle
finalize(locator_or_handle, admitted_profile) -> raw_proof_components
retrieve_public(stable_locator, admitted_profile) -> raw_retrieval_components
query_public(namespace, optional_attempt_tag, admitted_profile) -> raw_entry_set_and_completeness_proof
verify_offline(identity, phase_requests, proof_bundle, admitted_profile) -> verified_attempt
```

The release gate accepts only an opaque `verified_attempt` minted by the offline
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
  preimage.  The stable attempt tag makes same-unit entries deliberately
  linkable and potentially dictionary-searchable.  Domain separation and
  digest-bound request contents reduce disclosure but do not provide secrecy or
  information-theoretic privacy.
- A public append surface can permit third-party tag squatting or duplicate
  griefing.  Provider qualification must bind accepted entries to the admitted
  namespace and submission identity while leaving history and public retrieval
  under the external operator's control.
- The coordinator can know or disclose the mapping before release.  Route B
  does not detect that behavior and must never be cited as scorer-blindness
  evidence.
- A complete local proof bundle can be deleted by the coordinator.  Its absence
  makes the unit uncountable; the external entry does not excuse missing local
  binding material.
- The registered-attempt query cannot reveal covert runs that never used the
  admitted namespace.  No evidence or prose may turn the registered count into
  an assertion that all executions were observed.

## Evidence plan

Before any live provider call, focused offline tests must demonstrate:

1. canonical identity, attempt-tag, open-request, scoring-head-request and log-
   entry bytes, independently reconstructed from authorization and chain
   fixtures;
2. the scoring-head ordinal is derived from pinned `EVENT_SEQUENCE`, current
   value 6, while the six-item conceptual prose is never used as an ordinal;
3. identity, domain, phase, contract, head, commitment, namespace and profile
   mutations each change the appropriate bytes and fail verification;
4. event 1 or outcome production before a verified open, a scoring head without
   one verified open, and a second open or scoring head for the same tag are
   rejected;
5. an abandoned open remains discoverable and prevents reuse or relabelling of
   that authorized identity;
6. event 5, truncated event 6, changed scorer source and rebuilt local chain
   fail before scoring-head submission;
7. event 7 cannot be appended without a verifier-minted `verified_attempt` and
   a fresh complete namespace/tag query;
8. a raw receipt ID, caller boolean, timestamp string, screenshot, cached
   response and local digest file are rejected;
9. valid two-entry inclusion/checkpoint/witness or consensus fixtures verify
   offline, including consistency between their anchors;
10. either entry, inclusion path, checkpoint, trust root, query response or
    profile mutation fails;
11. public retrieval or tag query requiring submission credentials fails;
12. unavailable, pending, timed-out, stale, rate-limited and malformed responses
    all refuse mapping release;
13. a query omitting an entry, returning an unknown tag/phase, crossing
    namespaces, duplicating a phase or disagreeing with the authorized identity
    set is refused;
14. mapping publication before proof returns `EXTERNAL_PIN_LATE` and cannot be
    repaired retrospectively;
15. both retained proofs still verify with the network disabled;
16. missing long-term proof material degrades to
    `EXTERNAL_PIN_NOT_VERIFIABLE`, never success; and
17. claim tests reject `scorer_blind`, `independent_comparison`, absence of
    covert runs, `Gate3_pass` and Skill-effect conclusions derived from the pin.

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

## Claim ceiling

This candidate may claim only that Route B's proposed authority, protocol,
failure behavior, retention requirements and evidence plan are explicit.  It
may not claim that:

- a provider has been selected, qualified, contacted or remains available;
- an external pin, proof bundle, verifier or release gate exists;
- the ordering property has been established for any comparison unit;
- all attempts have been observed, or no covert/unregistered run occurred;
- scorer blindness or scorer independence has been established;
- historical Gate 2 has been repaired;
- a Gate 3 rehearsal or counted run is authorized;
- Gate 3 has started or the Bug Fix Skill is effective.

Acceptance of this design would authorize only the decision boundary, including
the narrow ordinal interpretation and the deliberate searchability/privacy
trade-off.  Provider selection, implementation, network use, rehearsal and
counted execution each require separate owner authorization.
