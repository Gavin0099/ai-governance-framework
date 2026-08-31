# Solo Evaluation Ledger Anonymization — Revision 2, Solo Profile

Status: **DESIGN ONLY / NOT ADOPTED / NO EXECUTION AUTHORITY**

Date: 2026-08-31

This is the adoption candidate. It is cut from the full reference design
`solo-ledger-anonymization-revision-2-candidate-20260831.md`, SHA-256
`f9815202d15d3b4bb9c77136088fb8be623bb2700f83cf7c79c875038ed7d339`, which is
retained unchanged as reference only and is not adopted.

The threat this design addresses is **controller operating error contaminating
blind scoring**. It is not third-party adversarial cryptography. Items belonging
to the latter are recorded as limitations in Section 8 rather than specified.

## 1. Superseded authority

Adoption requires three new exact identities. Until all three exist, no Attempt
may be admitted.

| Artifact | Current blob | Disposition |
|---|---|---|
| Solo protocol | `cfb2624622d3c3ae56998091265cf8a396d9530a` | superseded |
| Execution contract | `ed624166e2a7dbe7b7e1c006543edf9688ff5f42` | superseded |
| Ledger schema `solo_attempt_ledger.v1` | — | frozen historical; `v2` required |

Revision 1 was insufficient because contract line 125 publishes a deterministic
alternating arm order and lines 203/205 record `arm`, `order` and `scoring
label`. Public order plus attempt chronology derives the mapping, so removing
plaintext mapping alone does not close it.

## 2. Legacy Pair 0 and R2 shakedown

Legacy Pair `solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040` currently stands at
`PAIR_CREATED` with zero Attempt IDs. **Proposed disposition on adoption:**
permanent termination at `PRE_ATTEMPT_TERMINATION`. Termination is not
replacement and not retry.

The corrected shakedown is a new slot `R2-SHAKEDOWN` with a new Pair ID minted
under v2, inheriting no handle, label, order or controller state. It is excluded
from analytic comparison.

The v1 ledger and the Pair 0 disclosure remain immutable. No event is appended
to v1 and no record in it is rewritten.

## 3. Public ledger v2

Canonical path
`artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson`.
Schema `solo_attempt_ledger.v2`. The v1 path is retained and never written to
after adoption.

`V2_GENESIS` at `event_seq` 1 has exactly this closed key set:

```text
schema_version, event_seq, event_type, event_id, timestamp_utc,
evaluation_id, predecessor_digest,
adopted_protocol_sha256, adopted_contract_sha256, adopted_schema_id,
legacy_pair_id, legacy_pair_state_at_v1, legacy_pair_attempts_used,
legacy_pair_disposition,
attempt_ceiling_total, attempt_ceiling_breakdown
```

`attempt_ceiling_total` is `14`; `attempt_ceiling_breakdown` is
`{"R2-SHAKEDOWN":2,"A1":2,"A2":2,"A3":2,"A4":2,"A5":2,"A6":2}`. Genesis is the
durable authority for the legacy termination and the ceiling. No later event may
raise the ceiling.

Public events use only these fields:

```text
schema_version, event_seq, event_type, event_id, timestamp_utc,
pair_id, slot, category, repository,
attempt_handle, attempt_state,
frozen_identities, admission_result,
correctness_result, cost_metrics,
sealed_package_digest, score_count
```

Prohibited at any point before unblinding: `arm`, `treatment_state`, Skill
identity, scoring label, first/second markers, order fields, and any field whose
value differs between the two arm permutations.

### 3.1 Closed composite fields

Composite fields are closed; arbitrary metadata is prohibited; nesting beyond one
level is prohibited. Every value is a scalar, a fixed-vocabulary enum, or an
array of frozen string ids. No free text.

```text
frozen_identities   protocol_sha256, contract_sha256, schema_id,
                    qualification_record_sha256,
                    historical_base_commit, historical_fix_commit,
                    oracle_blob_sha256

admission_result    status in {ADMITTED, REFUSED, FAIL_CLOSED}
                    preflight_ids (array of frozen ids)
                    task_exposure_state in {NONE, EXPOSED}

correctness_result  oracle_status in {PASS, FAIL, NOT_RUN}
                    required_case_count, passed_case_count (integers)
                    regression_status in {NONE, PRESENT, NOT_EVALUATED}
                    scope_status in {WITHIN_SCOPE, VIOLATION, NOT_EVALUATED}

cost_metrics        elapsed_ms, tokens_total, tool_calls, review_rounds
                    (non-negative integers)
```

**Pair invariance of `frozen_identities`.** `historical_base_commit` and
`historical_fix_commit` are the Base and historical Fix commits of the task,
taken verbatim from the frozen selection state. They describe the benchmark, not
any attempt. Their values are identical under both arm permutations.

**Attempt-output commits are prohibited in the public ledger.** No commit id,
tree id, blob id, diff, patch, or branch reference that identifies the output of
an attempt may appear in any public v2 event before unblinding. Such references
live only in `sealed_controller_state`. A commit produced by an arm is
attempt-level data and reading it from Git would identify the arm, so publishing
it would defeat every other control in this design.

Three identifier domains are generated independently under distinct domain
separation tags: `attempt_handle`, `scoring_label`, and arm identity/order.

**Structural rule.** The opaque identifier generator accepts exactly two inputs:
CSPRNG output and a constant domain tag. It must not accept, read or derive from
`arm`, `treatment_state`, arm order, `event_seq`, `timestamp_utc`, `pair_id`,
slot parity, or any counter. Conformance is established by inspecting the
generator against this admitted input set whenever its bytes change.

Sampling comparisons are regression evidence only. They cannot demonstrate input
exclusion and must not be reported as proof of independence.

**Join prohibition.** Scoring and controller events are pair-level only and carry
no `attempt_handle` or `attempt_state`. No event carries both `attempt_handle`
and `sealed_package_digest`. The strongest inference available to a scorer is
"this bundle belongs to this pair", which it already knows.

The `blind_scoring_bundle` contains the two arm outputs under opaque presentation
keys plus the frozen rubric. It contains no `attempt_handle`, `event_seq`,
`timestamp_utc`, output hash, filesystem path, commit reference, or first/second
marker.

## 5. Sealed controller state

```text
AEAD    AES-256-GCM from a maintained cryptographic library, 128-bit tag,
        256-bit controller-only key, 96-bit CSPRNG nonce per operation
AAD     a JSON object with sorted keys containing exactly
        artifact_type, evaluation_id, pair_id, slot, schema_version,
        protocol_sha256, contract_sha256
key_id  solo-r2-<32 lowercase hex>, 128-bit CSPRNG, generated at key creation
digest  SHA-256 over the sealed package bytes only
```

`artifact_type` in the AAD prevents a `blind_scoring_bundle` being accepted where
`sealed_controller_state` is expected. `evaluation_id` prevents packages from a
different evaluation authenticating. No plaintext mapping digest is published.

The sealed plaintext holds the label-to-arm mapping, the per-pair arm order, and
the handle-to-arm binding.

## 6. Isolation

- The key lives in controller-only storage outside the repository working tree
  and outside any materialization root, resolved from an explicit absolute path,
  never from the current working directory.
- The key is never written to the repository, the ledger, any package, any log,
  or any environment inherited by a child process.
- Execution contexts are denied the key, `sealed_controller_state`, and
  `blind_scoring_bundle`. Scoring contexts are denied the key and
  `sealed_controller_state`, and are granted `blind_scoring_bundle` only.
- Tooling that touches the key redacts stdout and stderr to the safe verifier
  whitelist.
- Missing, unreadable or integrity-failing key material is
  `KEY_CUSTODY_FAILURE / STOP`, with no fallback key, unsealed path, or prompt.
- `owner_authorization_identity` is audit metadata, never an authority proof.

Unblinding is a separate authorized step after all scoring for a pair is
recorded. Premature attempts are `PREMATURE_UNBLINDING / STOP`, recorded without
revealing the mapping.

## 7. Shakedown criteria

R2-SHAKEDOWN is complete only when all five fail closed with recorded evidence:

1. wrong key supplied to unblinding;
2. ciphertext corruption or tag mismatch;
3. package bound to a different evaluation, pair, or artifact type;
4. unblinding attempted before scoring is complete;
5. sentinel leakage: a sentinel placed in the sealed plaintext does not appear in
   the public ledger, Git objects, stdout, stderr, any execution context, or any
   scoring context.

Criterion 5 is checked by counting occurrences and asserting zero. The check
never prints a match.

## 8. Limitations

Deliberately not specified, and not claimed:

- durable nonce registry and cross-restart uniqueness proof;
- a custom byte-level JSON or Unicode serialization protocol;
- ciphertext provenance machinery;
- statistical proof of cryptographic indistinguishability;
- any threat model extending beyond a solo controller who holds the key.

**Controller limitation.** This design reduces the risk of the controller
accidentally seeing the mapping. It does not prevent a controller who
deliberately retrieves the key, reads sealed state, or otherwise contaminates the
process. Solo evaluation remains `NON_COUNTED / SOLO_CONTROLLED /
DECISION_SUPPORT_ONLY`.

## 9. Stop condition

Once this profile passes the five shakedown criteria, governance design expansion
stops. Further cryptographic hardening is reopened only on demonstration that
`CONTROL`/`TREATMENT` can actually be recovered from published data. Absence of a
hardening measure is not itself a reason to reopen.

## 10. Claim ceiling

This candidate creates no v2 ledger, mints no Pair or Attempt ID, seals or
unseals nothing, executes no arm, and authorizes no scoring. Adoption requires
review of this exact identity followed by the three superseding identities in
Section 1.
