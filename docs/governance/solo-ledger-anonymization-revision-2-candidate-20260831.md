# Solo Evaluation Ledger Anonymization — Revision 2 Candidate

Status: **DESIGN ONLY / NOT ADOPTED / NO EXECUTION AUTHORITY**

Date: 2026-08-31

This candidate closes the four blocking findings raised against Revision 1 and
specifies the corrections required before any Attempt ID may be created. It
authorizes no execution, Pair creation, scoring, unblinding, commit or push.

## 1. Superseded authority

Adoption of this candidate requires three new exact identities. Until all three
exist, no Attempt may be admitted.

| Artifact | Current identity | Disposition on adoption |
|---|---|---|
| Solo protocol | `solo-engineering-skill-evaluation-protocol-candidate-20260830.md`, blob `cfb2624622d3c3ae56998091265cf8a396d9530a` | superseded; new exact identity required |
| Execution contract | `solo-evaluation-execution-contract-20260831.md`, blob `ed624166e2a7dbe7b7e1c006543edf9688ff5f42` | superseded; new exact identity required |
| Ledger schema | `solo_attempt_ledger.v1` | frozen historical; `v2` required |

The clauses that make Revision 1 insufficient are exact and cited:

- Protocol line 98: `Pair 0 cannot be replaced or repeated.`
- Contract line 125: `Order is deterministic and alternating; it cannot change
  after this freeze`, followed by a public Slot/First/Second table.
- Contract line 203: `slot, category, repository, arm` recorded as frozen
  Pair/arm bindings.
- Contract line 205: `execution_contract` recorded as including `order and
  scoring label`.

Public arm order plus attempt chronology is sufficient to derive the mapping.
Removing plaintext mapping alone does not close this.

## 2. Legacy Pair 0 termination

Legacy Pair `solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040` currently stands at
`PAIR_CREATED` with zero Attempt IDs. Its present state is unchanged by this
candidate.

**Proposed disposition on adoption:** permanent termination at
`PRE_ATTEMPT_TERMINATION`. Because it consumed zero Attempt IDs, the fourteen
initiated-attempt budget is unaffected by that termination.

The v1 ledger, SHA-256
`596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab`, and the
controller-mapping disclosure remain immutable historical evidence. No event is
appended to v1, and no record in it is rewritten or migrated.

Termination is not replacement and not retry. The protocol clause forbidding
replacement or repetition of Pair 0 is satisfied by ending that Pair, not by
continuing it under new bytes.

## 3. R2 shakedown slot

The corrected shakedown is a new revision-bound slot, `R2-SHAKEDOWN`, with a new
Pair ID minted under v2. It inherits nothing from legacy Pair 0: no handle, no
scoring label, no arm order, no controller state, no partial admission.

R2-SHAKEDOWN is excluded from analytic comparison on the same terms the previous
shakedown was. Its purpose is to exercise the corrected anonymization, sealing
and unblinding path end to end. Legacy Pair 0 can no longer serve this purpose
because its own mapping is public in repository history.

## 4. Public ledger v2

Canonical repo-relative path:
`artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson`.

The superseded v1 canonical path
`artifacts/evidence/solo-evaluation-20260831/attempt-ledger.ndjson` is retained
unchanged as immutable historical evidence. The two files coexist in the same
evidence directory; no tool may write to the v1 path after adoption.

Schema: `solo_attempt_ledger.v2`. Genesis is a `V2_GENESIS` event at `event_seq`
1 whose closed key set is exactly:

```text
schema_version            "solo_attempt_ledger.v2"
event_seq                 1
event_type                "V2_GENESIS"
event_id                  opaque id
timestamp_utc             RFC 3339 UTC
evaluation_id             opaque id, minted once, binds every v2 event
predecessor_digest        SHA-256 of the v1 ledger bytes
adopted_protocol_sha256   SHA-256 of the adopted protocol
adopted_contract_sha256   SHA-256 of the adopted execution contract
adopted_schema_id         "solo_attempt_ledger.v2"
legacy_pair_id            "solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040"
legacy_pair_state_at_v1   "PAIR_CREATED"
legacy_pair_attempts_used 0
legacy_pair_disposition   "PRE_ATTEMPT_TERMINATION"
attempt_ceiling_total     14
attempt_ceiling_breakdown {"R2-SHAKEDOWN": 2, "A1": 2, "A2": 2, "A3": 2,
                           "A4": 2, "A5": 2, "A6": 2}
```

No other key may appear in `V2_GENESIS`. The genesis event is the durable
authority for the legacy termination and for the fourteen-attempt ceiling; no
later event may raise the ceiling.

The public projection is closed. Only these fields may appear:

```text
schema_version, event_seq, event_type, event_id, timestamp_utc,
pair_id, slot, category, repository,
attempt_handle, attempt_state,
frozen_identities, admission_result,
correctness_result, cost_metrics,
sealed_package_digest, score_count
```

The following are prohibited in v2 at any point before unblinding:

```text
arm, treatment_state, skill identity, scoring label,
first/second markers, order fields,
any field whose value differs between the two arm permutations
```

### 4.1 Closed composite fields

Composite fields are closed. Arbitrary metadata is prohibited, and any key not
listed is a schema violation that fails closed. Nested objects beyond one level
are prohibited outright, so no arm identity can be hidden in a deeper structure.

```text
frozen_identities   { protocol_sha256, contract_sha256, schema_id,
                      qualification_record_sha256, base_commit, fix_commit,
                      oracle_blob_sha256 }
                    all values are lowercase hex or literal commit ids

admission_result    { status, preflight_ids, task_exposure_state }
                    status in {ADMITTED, REFUSED, FAIL_CLOSED}
                    preflight_ids is an array of frozen string ids
                    task_exposure_state in {NONE, EXPOSED}

correctness_result  { oracle_status, required_case_count, passed_case_count,
                      regression_status, scope_status }
                    oracle_status in {PASS, FAIL, NOT_RUN}
                    regression_status in {NONE, PRESENT, NOT_EVALUATED}
                    scope_status in {WITHIN_SCOPE, VIOLATION, NOT_EVALUATED}
                    counts are non-negative integers

cost_metrics        { elapsed_ms, tokens_total, tool_calls, review_rounds }
                    all non-negative integers
```

Every value above is a scalar, a fixed-vocabulary enum, or an array of frozen
string ids. None of them may carry free text.

### 4.2 Time-independence

`event_seq` and `timestamp_utc` remain public because lifecycle auditing needs
them. Their presence is safe only if nothing else lets an observer align them to
arms. Therefore:

- `attempt_handle` is drawn from a CSPRNG under a domain separation tag distinct
  from label assignment and from arm ordering. It is not derived from
  `event_seq`, `timestamp_utc`, `pair_id`, slot parity, or any counter.
- Arm order for each pair is generated per pair under its own domain tag and is
  sealed, not published. The public Slot/First/Second table of the superseded
  contract is not carried forward.
- Attempt lifecycle events are emitted so that neither the handles nor the order
  of emission distinguishes the arms.

Time-independence rests on structural rules, not on sampling. Sampling cannot
demonstrate that a generator never reads a forbidden input; only the generator's
admitted input set can.

**Normative rule R1 — generator input exclusion.** The opaque identifier
generator accepts exactly two inputs: CSPRNG output and a constant domain
separation tag. It MUST NOT accept, read, import, or otherwise obtain `arm`,
`treatment_state`, arm order, `event_seq`, `timestamp_utc`, `pair_id`, slot
parity, any counter, or any value derived from them. Conformance is established
by inspecting the generator's signature and body against this admitted input
set, and is re-established whenever the generator bytes change.

**Normative rule R2 — commitment secrecy.** `sealed_package_digest` is a SHA-256
over ciphertext produced by AES-256-GCM under a secret controller key with a
fresh CSPRNG nonce per sealing operation. Secrecy of the permutation follows
from those frozen conditions together with the prohibition on publishing any
plaintext digest. It is not asserted by a test.

**Regression tests (necessary, not sufficient).** For a fixed pair, generate the
public projection under both arm permutations and assert:

1. **Schema equality.** The field name set, ordering, and types are identical.
2. **Non-opaque invariance.** Every field that is neither an opaque identifier
   nor a cryptographic commitment has an identical value. This covers
   `schema_version`, `event_seq`, `event_type`, `pair_id`, `slot`, `category`,
   `repository`, `attempt_state`, `frozen_identities`, `admission_result`,
   `correctness_result`, `cost_metrics` and `score_count`.
3. **Repeat-seal divergence.** Sealing the same plaintext twice yields different
   `sealed_package_digest` values, confirming the nonce is fresh per operation.

These tests catch regressions against R1 and R2. They do not replace them.
Failing R1, R2, or any regression test fails closed.

## 5. Scoring receipt separation

Two distinct sealed artifact types exist. They are never conflated, and the
prohibitions in Section 7 apply to the controller type only.

| Artifact | Readable by | Contents |
|---|---|---|
| `blind_scoring_bundle` | scoring context | the two arm outputs under opaque presentation keys, and the frozen rubric |
| `sealed_controller_state` | controller only | label-to-arm mapping, per-pair arm order, handle-to-arm binding |

`blind_scoring_bundle` must not contain `attempt_handle`, `event_seq`,
`timestamp_utc`, output hashes, filesystem paths, commit references, or
first/second markers. Its presentation keys are drawn under their own domain
separation tag and are unlinkable to `attempt_handle` without
`sealed_controller_state`.

**No equality join.** A scoring context holds the `blind_scoring_bundle` and can
therefore compute its digest. If that digest appeared on an event that also
carried `attempt_handle`, the scorer could join its bundle to a specific attempt.
That join is closed as follows:

- Scoring events are **pair-level only**. A scoring event MUST NOT carry
  `attempt_handle`, `attempt_state`, or any attempt-level field.
- `sealed_package_digest` on a scoring event is the digest of the
  `blind_scoring_bundle` and appears **only** on pair-level scoring events.
- `sealed_package_digest` on a controller event is the digest of the
  `sealed_controller_state` and appears **only** on pair-level controller
  events, which likewise carry no `attempt_handle`.
- No event carries both `attempt_handle` and `sealed_package_digest`.

The strongest inference available to a scorer is therefore "this bundle belongs
to this pair", which the scorer already knows. Public v2 never records a scoring
label or a presentation key.

## 6. Sealed controller artifact and single cryptographic scheme

Exactly one scheme is admitted. Alternatives are not retained.

```text
AEAD:              AES-256-GCM
Key:               256-bit, controller-only
Tag:               128-bit (16 bytes) exactly; shorter tags are rejected
Nonce:             96-bit (12 bytes), CSPRNG, unique per sealing operation
Plaintext:         canonical JSON per the profile below
Package:           canonical JSON with exactly the keys
                   {version, key_id, nonce, ciphertext, tag}
                   nonce/ciphertext/tag are base64 (RFC 4648 §4, padded)
                   version is the integer 2
Public commitment: SHA-256 over the sealed package bytes only
```

**AAD encoding.** The AAD is a length-prefixed concatenation, not a bare join,
so that no component boundary is ambiguous:

```text
AAD = LP(artifact_type) || LP(evaluation_id) || LP(pair_id) || LP(slot)
      || LP(schema_version) || LP(protocol_identity) || LP(contract_identity)
      || LP(genesis_event_id)

LP(s) = uint32_be(byte_length(utf8(s))) || utf8(s)
```

`evaluation_id` and `genesis_event_id` are taken from the `V2_GENESIS` event.
Binding both means a package sealed under one evaluation, or under a different
v2 genesis, fails authentication rather than being silently accepted. This is
what makes shakedown gate 3 mechanically true rather than asserted.

Components appear in exactly this order. `artifact_type` is the literal
`sealed_controller_state` or `blind_scoring_bundle`, which prevents a package of
one type being accepted as the other. `protocol_identity` and
`contract_identity` are the lowercase hex SHA-256 of the adopted protocol and
execution contract respectively.

**`key_id`.** Format `solo-r2-<32 lowercase hex>`. The hex is a 128-bit CSPRNG
value generated once at key creation and stored with the key. It identifies the
key for retrieval and audit; it is not derived from the key and cannot be used
to reconstruct it. A package whose `key_id` does not match the retrieved key is
`KEY_CUSTODY_FAILURE / STOP`.

**Canonical JSON profile.** Applies to both the sealed plaintext and the package
envelope, so that the same logical content always produces the same bytes:

```text
encoding      UTF-8, no BOM
object keys   sorted by Unicode code point, ascending; duplicates prohibited
whitespace    none between tokens
strings       shortest valid escaping; only \" \\ \b \f \n \r \t and \uXXXX
              for code points below 0x20; no other escapes; no \/ escape
numbers       integers only, no leading zeros, no plus sign, no exponent,
              no fractional part; floating point is prohibited
booleans/null lowercase literals
top level     object; no trailing newline inside the sealed bytes
```

**Nonce discipline.** Nonces are generated per sealing operation from a CSPRNG
and are never reused under the same key. A persistent controller-only record of
issued nonces is maintained alongside the key. Before sealing, the candidate
nonce is checked against that record; a collision is `NONCE_COLLISION / STOP`
and the operation is not retried with the same key. If the nonce record is
missing, unreadable, or inconsistent with the sealed packages present, sealing
fails closed as `NONCE_STATE_FAILURE / STOP` rather than proceeding on the
assumption that a fresh random nonce is safe. Key rotation, not nonce reuse, is
the response to an exhausted or untrustworthy nonce record.

No plaintext mapping digest is published. No separate plaintext salt commitment
is published. Because the sealed package contains a random nonce, the commitment
over ciphertext is already hiding, so the two-permutation guessing attack
against a plaintext digest does not apply.

The sealed plaintext contains the label-to-arm mapping, the per-pair arm order,
and the handle-to-arm binding.

## 7. Key custody

- The key lives in controller-only secret storage outside the repository working
  tree and outside any materialization root. Its location is resolved from an
  explicit absolute path, never from the current working directory.
- The key is never written to the repository, the ledger, any sealed package,
  any log, or any process environment inherited by a child process.
- Execution contexts and scoring contexts are denied key access and denied read
  access to `sealed_controller_state`. The scoring context is granted read access
  to `blind_scoring_bundle` only; the execution context is granted neither.
- All tooling that touches the key redacts stdout and stderr to the safe
  verifier whitelist.
- Missing, ambiguous, unreadable, or integrity-failing key material is
  `KEY_CUSTODY_FAILURE / STOP`. It never falls back to an alternative key, an
  unsealed path, or an interactive prompt.
- `owner_authorization_identity` is audit metadata only. It is not an authority
  proof and never gates decryption on its own.

## 8. Unblinding

Unblinding is a separate authorized step after all scoring for a pair is
complete and recorded. It requires the sealed package, the key, and an explicit
revision-bound owner authorization. Premature unblinding attempts are
`PREMATURE_UNBLINDING / STOP` and are recorded in the public ledger without
revealing the mapping.

## 9. Shakedown gates

R2-SHAKEDOWN may not be declared complete unless all of the following fail
closed, each with recorded evidence:

1. wrong key supplied to unblinding;
2. ciphertext corruption, tag mismatch, or truncated package;
3. package bound to a different pair, evaluation, or schema version;
4. partial or missing scoring at unblinding time;
5. premature unblinding before scoring completion;
6. sentinel leakage: a known sentinel value placed in the sealed plaintext must
   not appear in the public ledger, Git objects, stdout, stderr, any execution
   context, or any scoring context.

Gate 6 is checked by counting sentinel occurrences and asserting zero. The check
must never print a match.

## 10. Claim ceiling

This candidate establishes a corrected design only. It does not create the v2
ledger, mint any Pair or Attempt ID, seal or unseal anything, execute any arm,
or authorize scoring. Adoption requires independent review of this exact
identity followed by the three superseding identities in Section 1.
