# Solo Attempt Ledger v2 — Schema and Implementation Contract

Status: **CANDIDATE / NOT ADOPTED / NO IMPLEMENTATION OR EXECUTION AUTHORITY**

Normative design source: `docs/governance/solo-ledger-anonymization-revision-2-solo-profile-20260831.md`, SHA-256 `e0cd3d4fca39c37c9baad8b0ef2b976cdff910ce997b95c6b241e644e4178741`.

Sibling locators (paths and titles only; not identity bindings):

- Study semantics: `docs/governance/solo-engineering-skill-evaluation-protocol-revision-2-20260831.md`, **Solo Engineering Skill Evaluation Protocol — Revision 2**, normative §§1–8 (“Purpose and authority”–“Size and non-goals”).
- Operations: `docs/governance/solo-evaluation-execution-contract-revision-2-20260831.md`, **Solo Evaluation Execution Contract — Revision 2**, normative §§3–11 (“Runtime and budget”–“R2 shakedown procedure”).

A later owner-adoption record must bind all three exact path/title/SHA-256/blob/commit identities. This document specifies v2 data and interfaces; it cannot change study semantics or operational authority.

## 1. Scope and claim ceiling

This contract defines prospective files, closed schemas and fail-closed interfaces. It creates no ledger or package, generates no ID, mutates no Pair, seals/unseals nothing and authorizes no implementation, adoption, execution, scoring, cleanup, commit or push.

## 2. Files and identities

**L01.** Public v2 path is `artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson`; schema version is `solo_attempt_ledger.v2`. Each line is one UTF-8, no-BOM, LF-terminated JSON object. The predecessor `artifacts/evidence/solo-evaluation-20260831/attempt-ledger.ndjson`, schema `solo_attempt_ledger.v1`, remains immutable at SHA-256 `596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab`; v2 never migrates, rewrites or appends to it. Sealed controller packages and blind scoring bundles use controller-configured paths outside the public ledger; sealed state must also remain outside every Git worktree and materialization root.

## 3. Genesis

**L02.** The first and only genesis line has `event_seq=1`, `event_type="V2_GENESIS"`, and exactly these keys:

```text
schema_version, event_seq, event_type, event_id, timestamp_utc,
evaluation_id, predecessor_digest,
adopted_protocol_sha256, adopted_contract_sha256, adopted_schema_id,
legacy_pair_id, legacy_pair_state_at_v1, legacy_pair_attempts_used,
legacy_pair_disposition,
attempt_ceiling_total, attempt_ceiling_breakdown
```

Required values are:

- `schema_version="solo_attempt_ledger.v2"`;
- `predecessor_digest="596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab"`;
- `adopted_protocol_sha256` and `adopted_contract_sha256`: exact identities from the owner-adoption record;
- `adopted_schema_id="solo_attempt_ledger.v2@sha256:<adopted-schema-contract-sha256>"`;
- `legacy_pair_id="solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040"`;
- `legacy_pair_state_at_v1="PAIR_CREATED"`, `legacy_pair_attempts_used=0`, `legacy_pair_disposition="PRE_ATTEMPT_TERMINATION"`;
- `attempt_ceiling_total=14`;
- `attempt_ceiling_breakdown={"R2-SHAKEDOWN":2,"A1":2,"A2":2,"A3":2,"A4":2,"A5":2,"A6":2}`.

`event_id` and `evaluation_id` are fresh UUIDv4 values; `timestamp_utc` is RFC 3339 UTC. Genesis may be created only after adoption and implementation authority. No later event may alter the legacy disposition or raise either ceiling.

## 4. Event model

**L03.** Every non-genesis event has exactly the common keys `schema_version,event_seq,event_type,event_id,timestamp_utc,pair_id,slot` plus the event-specific keys below. `schema_version` is exact; `event_seq` increments by one; `event_id` is unique UUIDv4; timestamp is RFC 3339 UTC. `pair_id` is an immutable opaque string, except it may be `null` for a failure before Pair creation. `slot` is one of `R2-SHAKEDOWN,A1,A2,A3,A4,A5,A6`.

| `event_type` | Exact additional keys | Constraints |
|---|---|---|
| `PAIR_CREATED` | `category,repository,frozen_identities` | Pair-level; new immutable Pair ID |
| `PRE_ATTEMPT_INFRA_FAILURE` | `category,repository,admission_result` | Pair-level; no handle consumed |
| `ATTEMPT_ADMITTED` | `attempt_handle,attempt_state,admission_result` | state `ADMITTED` |
| `ADMITTED_NOT_EXPOSED` | `attempt_handle,attempt_state,admission_result` | terminal state `ADMITTED_NOT_EXPOSED` |
| `TASK_EXPOSED` | `attempt_handle,attempt_state,admission_result` | state `TASK_EXPOSED`; begins consumption |
| `EXECUTION_TERMINAL` | `attempt_handle,attempt_state,correctness_result,cost_metrics` | state `TERMINAL` |
| `CONTROLLER_STATE_SEALED` | `sealed_package_digest,score_count` | Pair-level; final `SCORING_BOUND`; `score_count=0` |
| `SCORING_RECORDED` | `sealed_package_digest,score_count` | Pair-level; `score_count=2` |
| `PREMATURE_UNBLINDING` | `sealed_package_digest,score_count` | Pair-level terminal STOP; mapping absent |
| `UNBLINDING_RECORDED` | `sealed_package_digest,score_count` | Pair-level; `score_count=2` |

Per handle, valid transitions are `ATTEMPT_ADMITTED -> TASK_EXPOSED -> EXECUTION_TERMINAL` or `ATTEMPT_ADMITTED -> ADMITTED_NOT_EXPOSED`. After both Pair handles are terminal: `CONTROLLER_STATE_SEALED -> SCORING_RECORDED -> UNBLINDING_RECORDED`; `PREMATURE_UNBLINDING` may terminate after final state sealing but before complete scoring. Duplicate IDs, sequence gaps, invalid transitions, rewrite attempts or append/fsync failure are `LEDGER_FAILURE / STOP`. Earlier lines are never changed or deleted.

## 5. Public schema

**L04.** Outside genesis, the union of permitted public keys is closed:

```text
schema_version, event_seq, event_type, event_id, timestamp_utc,
pair_id, slot, category, repository,
attempt_handle, attempt_state,
frozen_identities, admission_result,
correctness_result, cost_metrics,
sealed_package_digest, score_count
```

No arbitrary metadata or unlisted event/key is accepted. Composite fields are closed, allow no free text and no nesting beyond their one object level:

| Composite | Closed keys and values |
|---|---|
| `frozen_identities` | required strings `protocol_sha256,contract_sha256,schema_id,qualification_record_sha256,historical_base_commit,historical_fix_commit,oracle_blob_sha256` |
| `admission_result` | `status` in `ADMITTED,REFUSED,FAIL_CLOSED`; `preflight_ids` array of frozen string IDs; `task_exposure_state` in `NONE,EXPOSED` |
| `correctness_result` | `oracle_status` in `PASS,FAIL,NOT_RUN`; non-negative integer `required_case_count,passed_case_count`; `regression_status` in `NONE,PRESENT,NOT_EVALUATED`; `scope_status` in `WITHIN_SCOPE,VIOLATION,NOT_EVALUATED` |
| `cost_metrics` | any available subset of `elapsed_ms,tokens_total,tool_calls,review_rounds`, each a non-negative integer; at least `elapsed_ms` and `tool_calls` required |

Unavailable optional cost values are omitted from public `cost_metrics`; controller evidence may retain literal `UNAVAILABLE`. A field is not made public merely because its name resembles an allowed field.

**L05.** Before and after unblinding, the lifecycle ledger never contains `CONTROL`, `TREATMENT`, arm identity, `treatment_state`, Skill identity, scoring label/presentation key, realized order, first/second markers, controller entropy/key/salt, output provenance, or any deterministic surrogate of them. Before unblinding, every public value must remain unchanged when only the hidden arm assignment/order is permuted while the same opaque attempt outcomes are held fixed. No event may contain both `attempt_handle` and `sealed_package_digest`; scoring/controller events are Pair-level and contain neither `attempt_handle` nor `attempt_state`.

**L06.** `historical_base_commit` and `historical_fix_commit` are benchmark-level frozen selection identities and are identical under both arm permutations. They never identify an Attempt. Before unblinding, no public event or scoring bundle may carry an attempt-output commit, tree, blob, diff, patch, branch/ref, output hash, filesystem path or equivalent Git/provenance join key. Attempt-output references exist only inside encrypted `sealed_controller_state`. The public lifecycle ledger does not publish them after unblinding either.

## 6. Opaque identities

**L07.** `attempt_handle`, scoring label/presentation key, and realized arm identity/order are independent domains. For a handle or label, read 32 OS-CSPRNG bytes and return lowercase hex of `SHA-256(UTF8(domain_tag) || 0x00 || random)`, where the exact tags are `solo-r2-attempt-handle-v1` and `solo-r2-scoring-label-v1`. The generator accepts only tag and random bytes; its code path must not read or derive from arm, treatment state, realized order, `event_seq`, timestamp, Pair ID, slot/parity or a counter. Collision within an evaluation is `OPAQUE_ID_COLLISION / STOP`; no replacement is generated. Source/AST inspection against this admitted input set is normative evidence whenever generator bytes change. Sampling is regression evidence only and never proof of independence.

## 7. Blind scoring bundle

**L08.** Scoring preparation starts only after both Pair outputs are terminal. Presentation order is drawn independently of execution order. `blind_scoring_bundle` contains no lifecycle ledger, handle, sequence, timestamp, controller metadata, output hash/path/commit, first/second marker, arm/Skill state or other join key. Scoring events expose only Pair ownership, sealed-package digest and count; the scorer's strongest public inference is that the bundle belongs to the Pair already assigned.

**L09.** A scorer-visible bundle is one JSON object with exactly:

```text
schema_version, artifact_type, evaluation_id, pair_id, slot,
rubric_id, presentation_order, outputs
```

`schema_version="solo_blind_scoring_bundle.v2"`; `artifact_type="blind_scoring_bundle"`; `presentation_order` is an array of exactly two distinct scoring labels; `outputs` is an array of exactly two objects, each with exactly `presentation_key,output_payload`, where each key occurs once and `output_payload` is the identity-stripped scorer-visible UTF-8 content required by the frozen rubric. `rubric_id` is a frozen string identity. No extra package or output field is permitted.

Before encryption, `sealed_controller_state` is one object with exactly:

```text
schema_version, artifact_type, evaluation_id, pair_id, slot, state_phase,
realized_order, order_entropy, attempt_bindings, scoring_bindings,
presentation_order, attempt_output_refs
```

`schema_version="solo_sealed_controller_state.v2"`; `artifact_type="sealed_controller_state"`; `realized_order` is one permutation of `["CONTROL","TREATMENT"]`; and `order_entropy` is the 32-byte CSPRNG input encoded as padded RFC 4648 Base64. `state_phase` and array cardinalities are closed:

| Phase | `attempt_bindings` | `scoring_bindings`, `presentation_order`, `attempt_output_refs` |
|---|---|---|
| `ORDER_FROZEN` | empty | empty |
| `ATTEMPT_BOUND` | one or two `{attempt_handle,arm}` objects | empty |
| `SCORING_BOUND` | exactly two `{attempt_handle,arm}` objects | exactly two `{scoring_label,attempt_handle}` objects, the same two labels in presentation order, and two `{attempt_handle,output_ref}` objects |

The candidate `pair_id`, realized order and entropy are immutable across phases. Before each public admission and before scoring, the controller writes a complete next-phase state and reseals it with a fresh nonce; no plaintext overwrite is permitted. Only the final `SCORING_BOUND` digest is published. Earlier encrypted controller copies may be retained controller-only but form no claimed provenance chain. No plaintext state or bundle is committed to Git or emitted to ordinary stdout/stderr.

## 8. Sealed package

**L10.** Seal every controller-state phase with AES-256-GCM from one maintained cryptographic library, a 256-bit controller key, fresh 96-bit OS-CSPRNG nonce per operation and 128-bit authentication tag. AAD is a sorted-key JSON object containing exactly `artifact_type,evaluation_id,pair_id,slot,schema_version,protocol_sha256,contract_sha256`; `artifact_type` must be `sealed_controller_state`. The implementation stores and reuses the exact UTF-8 AAD bytes for authentication and verifies the parsed closed field set/bindings before opening; this contract defines no cross-implementation canonical-JSON or Unicode protocol.

The sealed envelope has exactly `package_schema,artifact_type,key_id,nonce_b64,aad_utf8_b64,ciphertext_b64,tag_b64`; `package_schema="solo_aead_package.v2"`; `artifact_type="sealed_controller_state"`; Base64 uses RFC 4648 with padding. `key_id` is `solo-r2-<32 lowercase hex>`, generated once from 128 CSPRNG bits when the evaluation key is created, unrelated to key bytes and immutable for that key. SHA-256 is computed over the exact stored sealed-envelope bytes and published as `sealed_package_digest`; no plaintext/controller-state digest or separate low-entropy commitment is published. RNG/library failure is `SEALING_FAILURE / STOP`. A durable nonce registry, cross-restart uniqueness proof and ciphertext provenance subsystem are deliberately not claimed.

## 9. Key custody

**L11.** The controller key location is an explicitly configured absolute path outside all Git worktrees, governance/consumer repositories and materialization roots; it is never derived from CWD. Key bytes and plaintext state never enter the ledger, package metadata, Git, logs, prompts, scoring/execution roots or inherited child environment. Only controller key tooling may read them, and its stdout/stderr is restricted to a frozen safe-verifier whitelist. Execution cannot read key, state or bundle; scoring can read only `blind_scoring_bundle`. Missing/relative/repository-resident/unreadable key, identifier mismatch, access ambiguity or integrity failure is `KEY_CUSTODY_FAILURE / STOP`, with no fallback key, prompt, reconstruction or unsealed path. `owner_authorization_identity` is audit metadata, never authority proof.

## 10. Unblinding

**L12.** Unblinding is a separate controller-only operation after `SCORING_RECORDED` and separate authorization. It verifies the public digest and envelope type, resolves the authorized key by immutable `key_id`, authenticates using the stored exact AAD bytes, checks parsed evaluation/Pair/slot/schema/protocol/contract bindings, decrypts, validates the closed plaintext schema, then resolves scoring label to Attempt to arm. Wrong key, corrupt ciphertext/tag, wrong binding, missing state/key or incomplete scoring fails closed without plaintext output. A premature request appends only Pair-level `PREMATURE_UNBLINDING`; successful opening appends Pair-level `UNBLINDING_RECORDED`, neither carrying the mapping. Arm-attributed analytic results may be published only by a separately authorized result artifact; plaintext mapping and attempt-output provenance never enter the lifecycle ledger or ordinary stdout/stderr.

## 11. Conformance gates

**L13.** Before v2 genesis or R2-SHAKEDOWN, all applicable checks must pass:

1. v1 predecessor bytes and SHA-256 are unchanged; v2 path is distinct and absent until authorized creation.
2. Closed-schema validation rejects every unknown event, key, composite key, enum, transition, sequence gap and forbidden nesting.
3. Generator source/AST inspection proves the admitted input set for attempt/scoring IDs and order; same-hidden-permutation sampling is regression-only.
4. A public-join test over protocol, contract, raw v2 ledger, scorer bundle and Git-visible commitment cannot recover CONTROL/TREATMENT or link a scoring label to an Attempt.
5. Sentinel controller plaintext has zero occurrences in Git-visible objects, ledger, stdout/stderr and execution/scoring contexts; the checker reports counts without printing matches.
6. Bundle validation rejects every lifecycle/Git join field and requires exactly two independently ordered outputs.
7. Wrong key, ciphertext/tag corruption, wrong evaluation/Pair/artifact binding and premature unblinding each fail closed and reveal no mapping.
8. Successful authenticated opening recovers the expected synthetic mapping only after both scores exist.
9. Raw public event projection contains no arm/order/Skill/scoring identity; outcome fields remain attached only to independent opaque handles.

Failure is `V2_CONFORMANCE_FAILURE / STOP`. Once these gates and the protocol's shakedown criteria pass, missing Formal-grade hardening is a documented limitation, not a reason to expand this Solo design.
