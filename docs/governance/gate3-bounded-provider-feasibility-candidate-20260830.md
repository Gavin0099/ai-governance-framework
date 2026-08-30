# Gate 3 bounded provider feasibility — candidate 1

Status: `FAIL / STOP / NOT_ADOPTED`

Date: 2026-08-30

## 1. Authority and claim boundary

This read-only research artifact evaluates whether at least one member of a
closed, owner-approved provider/surface universe shows sufficient feasibility
for a later bounded implementation decision. It creates no capability and
authorizes no implementation, account, credential, submission, publication,
rehearsal, counted execution or push.

Frozen predicate authority:

- commit `6501d90f52c5e372fc049da34b3210fd01245fb4`
- blob `cb7b9ce25d7776b5924450a81388e7219511d871`
- SHA-256 `8e67c8740e9ec0036b9bae391b2f44decf0889b432d8b790112b1f96e2a07f2b`
- 43 `HIST-*` / 20 `FUT-*` / 63 total

Release-Order mechanism reference:

- commit `d3b28213513589cfec8b95edd4965cd631052449`
- blob `58dadf63f69fefd153c1cbecb3e5df6fc1c83bfd`
- SHA-256 `e010197852f491824c4cfd8ecad93821f661b67a353690e356522c4c6dd6b9bd`
- stable anchors: `## 5. Acceptance Predicate` and
  `## 7. Capability Failure Matrix`

The provider documentation is evidence about documented capability, not direct
proof that a Gate 3 predicate is satisfied. Inference and unknowns remain
explicit. No provider limitation may weaken or create a frozen predicate.

## 2. Owner-approved bounded candidate universe

The following set was frozen before substantive evaluation. It is the complete
search universe for this slice:

| ID | Provider / surface | Exact evaluation boundary |
| --- | --- | --- |
| `C1` | Sigstore public Rekor transparency-log surface | Provider-native public Rekor log capability only; PIN and authoritative RELEASE would have to use the same log surface. |
| `C2` | Microsoft Azure Confidential Ledger | One provider-native ledger instance and its native transaction receipt / verification surface only. |
| `C3` | GitHub immutable releases | One repository release namespace, immutable-release protection and provider-native verification evidence only. |

Excluded from this slice:

- any fourth provider or surface;
- cross-provider bridges or composite protocols;
- self-hosted logs;
- custom blockchains or smart contracts;
- a new external authority or replacement infrastructure;
- changing a candidate after a failure.

A failure of all three establishes only that this frozen universe has no
qualifying candidate. It does not prove universal provider nonexistence.

## 3. Cheapest-first prefilter

Gate A asks whether official provider-native evidence establishes the mandatory
authenticated predecessor/non-membership property used by the accepted
Release-Order mechanism:

> For comparison unit `U`, an independently verifiable proof establishes the
> pre-PIN state `State[U]=EMPTY`, rather than merely proving inclusion of a PIN or
> RELEASE observation.

The accepted design states that an inclusion-only append-only log fails its
acceptance items 4, 10 and 11. Therefore:

- `SATISFIED` requires affirmative official evidence for authenticated
  key/state absence or an equivalent provider-native proof with the same
  decision effect;
- inclusion, existence, immutability, transaction commitment or consistency
  evidence alone is insufficient;
- absence of sufficient official evidence is `UNRESOLVED`, not a claim of
  mathematical impossibility;
- because Gate A is mandatory, `UNRESOLVED` cannot support feasibility `PASS`.

Only a Gate A survivor proceeds to Gate B (independent principal) and the full
63-row mapping. If all three stop at Gate A, this slice terminates `FAIL / STOP`
without researching later gates.

## 4. Gate A evidence and disposition

Research date: 2026-08-30. Only official provider documentation and API
references were used. No account, credential, API call to a provider, network
submission or publication was performed.

### 4.1 `C1` — Sigstore public Rekor

Documented capability:

- Sigstore describes Rekor as an immutable transparency log. Its official
  overview says clients query inclusion proofs, verify log integrity and
  retrieve existing entries; auditors check append-only consistency.
- The official CLI documentation defines `verify` as verification of an
  inclusion proof, `get` as retrieval by index/UUID, `loginfo` as signed-tree-head
  verification and `search` as a Redis lookup by artifact, key or SHA.

Official evidence:

- [Rekor overview](https://docs.sigstore.dev/logging/overview/), anchors
  `Usage and installation` and `Auditing the Public Instance`.
- [Rekor CLI](https://docs.sigstore.dev/logging/cli/), anchors
  `Verify Proof of Entry`, `Get Entry`, `Log Info` and `Search`.

Independently verifiable boundary:

- An inclusion proof authenticates that a supplied entry is in the tree.
- A signed tree head and consistency audit authenticate the append-only log
  history.
- The documented search operation does not return a cryptographic proof that
  the search index is complete or that a comparison-unit key was absent at a
  specified signed tree head. An empty search result is therefore an observation,
  not authenticated `State[U]=EMPTY` evidence.

Gate A disposition: **`UNRESOLVED`**. The reviewed provider-native evidence is
inclusion/consistency evidence. It does not establish the mandatory authenticated
non-membership predecessor proof. This is not a claim that Rekor is
mathematically incapable of supporting every possible custom protocol.

### 4.2 `C2` — Microsoft Azure Confidential Ledger

Documented capability:

- Microsoft describes Azure Confidential Ledger as a customer-managed,
  append-only ledger. Each transaction has a receipt used to verify transaction
  integrity.
- The receipt documentation defines the proof as a Merkle path for the leaf of
  a corresponding committed write transaction, followed by verification of the
  signed Merkle root and signing-node certificate chain.
- The receipt leaf commits `writeSetDigest`, hashed `commitEvidence` and
  `claimsDigest`. Optional application claims can be revealed and their digest
  recomputed offline; this authenticates the exact claim bytes attached during
  the write transaction.
- The data-plane `Get Receipt` API takes a transaction ID and returns the receipt
  for the write at that transaction ID.
- Preview user-defined functions can perform conditional checks and atomic
  ledger-table operations inside the ledger trust boundary, but their official
  documentation does not define a provider-native receipt that independently
  proves the UDF read a particular comparison-unit key as absent in the
  predecessor state.

Official evidence:

- [Azure Confidential Ledger overview](https://learn.microsoft.com/en-us/azure/confidential-ledger/overview),
  anchors `Key features`, `Data storage` and `Terminology`.
- [Verify write transaction receipts](https://learn.microsoft.com/en-us/azure/confidential-ledger/verify-write-transaction-receipts),
  anchors `Receipt verification steps`, `Leaf node computation`,
  `Root node computation` and `Verify application claims digest`.
- [Azure Confidential Ledger write transaction receipts](https://learn.microsoft.com/en-us/azure/confidential-ledger/write-transaction-receipts),
  anchors `Write transaction receipt content` and `Application claims`.
- [Get Receipt REST API](https://learn.microsoft.com/en-us/rest/api/data-plane/confidentialledger/get-receipt/get-receipt?view=rest-data-plane-confidentialledger-2022-05-13),
  API version `2022-05-13`.
- [Simple user-defined functions](https://learn.microsoft.com/en-us/azure/confidential-ledger/user-defined-functions),
  preview API `2024-12-09-preview`, anchors `Use cases`, `Transaction hooks` and
  `Considerations`.

Independently verifiable boundary:

- The documented receipt authenticates inclusion/commitment and integrity of a
  write transaction.
- The reviewed receipt schema exposes the write-set digest, commit evidence,
  claims digest, Merkle proof, root, signature and certificate-chain material.
  Revealed application claims can be verified as the exact claim bytes committed
  to that transaction, but a signed claim that says "U was absent" authenticates
  the statement, not the underlying predecessor read set or key non-membership.
- The official verification procedure does not bind an absence claim to a
  frozen UDF code identity, prove that this code executed the asserted read, or
  expose a provider-native non-membership witness for `U` at the predecessor
  root.
- Treating custom UDF behavior as the missing proof would require a new protocol
  for code identity, predecessor read semantics and receipt binding. This slice
  cannot invent that infrastructure, and documented atomic execution alone is
  not independent proof of the required absence predicate.

Gate A disposition: **`UNRESOLVED`**. Transaction inclusion is documented;
authenticated predecessor key absence is not established by the reviewed native
receipt/verification surface. This does not assert mathematical impossibility.

### 4.3 `C3` — GitHub immutable releases

Documented capability:

- GitHub says an immutable release locks its tag to a commit and protects release
  assets after publication. Publication also generates a cryptographically
  verifiable release attestation containing the tag, commit SHA and assets.
- GitHub documents `gh release verify RELEASE-TAG` as verification that a named
  release exists and is immutable, and `gh release verify-asset` as verification
  that a local artifact matches a release asset.
- GitHub also prevents reuse of an immutable release's tag after repository
  deletion/recreation, but this is post-publication protection for an existing
  immutable release, not an authenticated proof of pre-PIN absence.

Official evidence:

- [Immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases),
  anchor `What immutable releases protect`.
- [Verifying the integrity of a release](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity),
  anchor `Verifying immutable releases and local artifacts`.

Independently verifiable boundary:

- The release attestation and verification commands authenticate an existing
  release and its immutable contents.
- The reviewed official evidence does not provide a signed predecessor-state
  root plus non-membership witness proving that the comparison-unit release/tag
  had never existed before PIN. A missing release response or empty listing is
  an observation, not the required authenticated absence proof.

Gate A disposition: **`UNRESOLVED`**. Existence and post-publication
immutability are documented; authenticated pre-PIN non-membership is not. This
does not assert mathematical impossibility.

## 5. Terminal result

**`FAIL / STOP`** for the frozen candidate universe.

| Candidate | Gate A | Gate B / remaining predicates | Candidate result |
| --- | --- | --- | --- |
| `C1` Rekor | `UNRESOLVED` | Not evaluated; Gate A did not survive | `FAIL` |
| `C2` Azure Confidential Ledger | `UNRESOLVED` | Not evaluated; Gate A did not survive | `FAIL` |
| `C3` GitHub immutable releases | `UNRESOLVED` | Not evaluated; Gate A did not survive | `FAIL` |

Gate A is a mandatory acceptance property. Under the owner-frozen rule, a
mandatory `UNRESOLVED` cannot support `PASS`; because no candidate survives,
principal independence and the remaining register mappings are intentionally
not researched.

This result establishes only:

> No candidate in the three-member frozen universe has sufficient official,
> provider-native evidence to establish Gate A feasibility.

It does not establish that no qualifying provider exists outside this universe.
The universe is not reopened here, and no replacement provider, surface,
infrastructure or protocol is proposed.

## 6. Nonclaims

This artifact does not establish universal provider impossibility,
implementation readiness, Gate 2 process integrity, counted evidence or Gate 3
success. It does not authorize a new provider search, implementation, rehearsal
or counted execution. The provider-feasibility result for this frozen universe
is negative only within the exact evidence and candidate boundaries above.
