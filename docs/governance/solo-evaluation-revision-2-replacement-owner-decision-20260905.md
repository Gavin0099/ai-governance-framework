# Solo Evaluation Revision 2 — One-Replacement Owner Decision Candidate

Status: **CANDIDATE / NOT ADOPTED / NO IMPLEMENTATION OR EXECUTION AUTHORITY**

Date: 2026-09-05

Scope: one replacement `R2-SHAKEDOWN` evaluation under the existing adopted
Solo Evaluation Revision 2 claim boundary

## 1. Problem and current state

The current Solo R2 evaluation
`2fc5fd9b-9283-4d45-8c6a-ed6e2eb525e5` has one `R2-SHAKEDOWN` Pair,
`346df3b9-4637-4187-a59e-52863bb8b172`, at `CREATED` with zero admitted or
initiated Attempts. Its public ledger remains the two-event file at
`artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson`,
SHA-256 `a1d77c1d0a9a245c0208c3cdd59f15a45ca54d2032f6a91e84c12ab4cf68c32f`.

The creation-time independent authority for that Pair's
`sealed_package_digest` is unavailable after a bounded read-only recovery
search. Recomputing a digest from the present package would prove only present
integrity, not that the package is the controller-order package created for the
Pair. Execution authorization for that Pair therefore remains blocked.

The current implementation also has one fixed public v2 ledger path. Bootstrap
rejects that path when it already exists, and Pair creation reads the same path
and exact genesis binding. A replacement evaluation cannot be created in place
under the current namespace.

## 2. Proposed owner decision

If adopted, this decision permits **exactly one** replacement Solo R2
evaluation and exactly one replacement `R2-SHAKEDOWN` Pair, subject to separate
implementation, creation and execution authorizations.

This candidate is revision-bound to these existing adopted decisions:

- `docs/governance/gate3-formal-solo-route-split-owner-decision-20260830.md`,
  commit `ea46e4018b266d63ff0597ab4109d02b360b7b91`, blob
  `c2a2241ed550979824ea6e51a00fd2acc8e3782f`, SHA-256
  `ae29a84498d8f339ac6fb18f4eaa1d1685aca4445d6c584af74fc87191eff4bf`;
- `docs/governance/solo-evaluation-revision-2-owner-adoption-20260831.md`,
  commit `662d5520b67b6acdd0bd714cf0f9ce6889b0233a`, blob
  `23fdbd6e28589f8b6ae43004f801b2bf8bd5560e`, SHA-256
  `6bf8eed7b4b585db08e0a7f0668ecc67aee41ff63a901095b8aec488c17caf66`.

The replacement remains bound to the exact Solo Evaluation Revision 2
authority set adopted on 2026-08-31. It does not change the protocol, execution
contract, ledger event semantics, experiment inputs, attempt ceiling, failure
rules, blinding workflow or shakedown criteria.

No second replacement, third evaluation, retry, further shakedown or analytic
Pair is permitted by this decision. Any such action requires another explicit
revision-bound owner decision.

## 3. Evidence route and claim ceiling

The replacement evaluation remains:

```text
NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY
```

Its only permitted use is the owner's personal workflow decision described by
adopted P01. It is excluded from Formal Gate 3 counted evidence, Formal Gate 3
validity evidence, prior-evidence repair, effect estimation, provider research
and any claim of general Skill effectiveness.

The creation-time digest record defined below is `OWNER_ATTESTED`. It is not a
genuinely independent principal, does not satisfy the Formal Gate 3 external-pin
requirement, and does not reopen or alter the adopted Formal/Solo route split.

## 4. Namespace and custody isolation

The one replacement evaluation must use the distinct public ledger path:

```text
artifacts/evidence/solo-evaluation-r2-replacement-20260905/attempt-ledger.v2.ndjson
```

The path and its temporary publication path must both be absent before
bootstrap. The existing ledger and every byte of its history remain unchanged.

The replacement must also use:

- a newly generated controller key at an explicit, previously absent absolute
  path outside every Git worktree and all governance, consumer,
  materialization, execution and scoring roots;
- a distinct, empty controller root outside those roots and disjoint from the
  existing evaluation's controller root and key location;
- a fresh evaluation UUID, Pair UUID, controller order entropy and sealed
  package. No key, package, Pair identity, order, nonce, handle or private root
  from the existing evaluation may be reused.

The key path and controller root remain owner-supplied custody locations. Their
private absolute values are not published in the public ledger, ordinary
stdout/stderr, execution context, scoring context or this decision artifact.

## 5. Creation-time sealed-package commitment

For the replacement Pair, Pair creation must atomically create and read back an
owner-side durable commitment record after the sealed `ORDER_FROZEN` package is
created and before `PAIR_CREATED` is appended. The record must bind exactly:

```text
record_schema
evaluation_id
pair_id
slot
sealed_package_digest
created_at_utc
authority_class
```

`record_schema="solo_r2_owner_commitment.v1"`;
`slot="R2-SHAKEDOWN"`; `sealed_package_digest` is the lowercase SHA-256 of the
exact sealed-envelope bytes; and
`authority_class="OWNER_ATTESTED_CREATION_TIME_COMMITMENT"`.

The record location is an explicit owner-controlled absolute path outside the
sealed-package directory, all Git worktrees and all materialization, execution
and scoring roots. The target and its temporary publication path must be absent
before creation. Failure to create, flush, read back or revalidate the exact
record stops before `PAIR_CREATED`; there is no fallback to terminal output,
memory, operator recollection, a caller-supplied execution-time digest or a
digest recomputed from the package later.

The record contains no controller key, key path, realized order, entropy,
plaintext state, arm identity or other mapping material. It is controller/owner
custody only and is not published in the lifecycle ledger before the existing
ledger contract permits `sealed_package_digest` publication.

## 6. Existing evaluation disposition

The current evaluation and Pair remain exactly as they are:

```text
evaluation phase: active ledger with Pair at CREATED
admitted Attempts: 0
initiated Attempts: 0
execution authorization: blocked
```

No `PRE_ATTEMPT_INFRA_FAILURE` is appended. Terminally stopping the current
ledger would not create a replacement namespace or supply the new
revision-bound authority required by P11 and E12. Leaving it unchanged preserves
the possibility that its original creation-time digest record is recovered
later, while granting no authority to execute, resume, reuse or alter it.

## 7. Later authorization boundaries

Adoption of this candidate would establish only the one-replacement policy and
its required boundaries. It would not itself authorize:

- edits to bootstrap, ledger, Pair-creation, controller, runtime-window or R1
  production code;
- creation of a key, genesis, commitment record, sealed package, Pair or
  Attempt;
- package or key access, task/oracle exposure, network activity, sandbox
  provisioning, arm execution, scoring or unblinding;
- mutation or termination of the existing evaluation;
- PLAN or memory changes, cleanup, staging, commit or push.

A later implementation slice must be limited to the new fixed ledger namespace,
the one-replacement identity bindings and the create-once owner commitment
write. A later creation slice must stop after publishing the replacement Pair
and verifying the commitment, ledger and zero-Attempt state. Execution remains
a separate owner-authorized decision.

## 8. Candidate claim ceiling

This file is a review candidate only. It creates no authority until the owner
adopts this exact identity. It does not show that the replacement namespace is
implemented, that custody controls pass, that a commitment exists, that runtime
qualification succeeds, that an Attempt is ready, or that Gate 3 is complete.
