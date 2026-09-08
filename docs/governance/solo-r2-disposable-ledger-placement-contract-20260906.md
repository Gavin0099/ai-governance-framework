# Solo R2 disposable ledger placement and identity — candidate contract

Status: CANDIDATE / NOT OWNER ADOPTED / NO IMPLEMENTATION OR CREATION AUTHORITY.

## P01. Scope and source authority

This contract proposes one fixed placement and identity rule for the single
disposable mechanism-shakedown allocation. It is not a ledger registry or a
parameterized evaluation factory. Definition does not consume the allocation.

The allocation decision is committed at
`744ba9973f70bede1eb93137f12e1b8110b0e5c7`, path
`docs/governance/solo-r2-d2-allocation-owner-decision-20260906.json`,
2582 bytes, SHA-256
`8a7e8cd74d883a733a5df887923b5eccf31ffe2ed0ed462446f15ae1066192b6`,
Git blob `d61a8a1e447b6386c8f17bf61154f4d3f1e620bf`.
It preserves the existing replacement allocation and permits one additional
disposable evaluation with one dedicated ledger. It grants no creation authority.

The adopted amendment is at commit `a081eb1ff4fa91e4b9932b5a3164ad118d5ddba4`,
path `docs/governance/solo-r2-input-authority-schema-amendment-20260906.md`.
The exact schema identity is
`solo_attempt_ledger.v2.1@sha256:ced964f9166aa59a878faa3afdd96c19fe8accaf60a2788c4aaf5a8dbb4680ab`.
This candidate does not amend those bytes or supersede unresolved adoption gates.

## P02. Sole ledger placement

Repository: `ai-governance-framework`.
Bound local repository root: `D:/ai-governance-framework`.
Exact repository-relative ledger path:

`artifacts/evidence/solo-r2-disposable-mechanism-shakedown-20260906/attempt-ledger.v2.1.ndjson`

The absolute target is that path under the bound root; never derive it from CWD,
accept a caller-selected alternative or fall back to either existing v2 ledger.
Use existing repository/path containment and alias checks. Parent/alternate path,
symlink/reparse redirection, containment ambiguity or an occupied target refuses
creation. Do not overwrite or reset a prior run. Moving the repository is not
automatic authority to rebind this contract.

The original and replacement ledger paths are excluded from every disposable
creation/write operation. No third-path constant or runtime change is made by
this document. A read-only existence check during drafting found this proposed
ledger target absent; that observation does not replace the later creation check.

## P03. Evaluation identity rule

Current disposable evaluation ID: NOT GENERATED.
Only a later explicitly authorized creation operation may generate one fresh
UUIDv4 evaluation_id and a distinct fresh UUIDv4 genesis event_id, using the
adopted CSPRNG rule. Neither is derived from paths, time, task hashes, existing
evaluation IDs or the D2 decision digest. Reject collision with existing
evaluation IDs; do not regenerate silently or reuse an old ID.

The generated evaluation ID belongs only to this allocation and fixed ledger.
After publication it is immutable; restart is not permission for a new ID,
second ledger, second allocation or deletion/recreation. Existing target,
partial publication or mismatched identity requires a separate recovery decision.
No existing evaluation is resumed, replaced, migrated or rebound by this rule.

## P04. Genesis and exact-byte binding

Genesis uses the adopted v2.1 schema and the unchanged parent L02 key set:
`event_type=V2_GENESIS`, `event_seq=1`, fresh IDs from P03 and RFC3339 UTC time.
`adopted_schema_id` equals P01's full schema identity.
`adopted_protocol_sha256` is
`1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff`;
`adopted_contract_sha256` is
`3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea`.
Predecessor digest and legacy-disposition fields retain exact parent L02 values;
they describe historical provenance, not linkage to or reuse of the replacement
evaluation. No allocation/path/authority metadata is added to the closed genesis.

Serialize once as UTF-8 without BOM and with a terminating LF, using the adopted
ledger serialization constraints. Verify the stored first-line bytes and retain
their byte length and SHA-256 before any Pair creation. Hash stored bytes, not a
reserialized object; genesis digest remains the first-line digest after appends,
not the evolving whole-ledger digest.

Proposed fixed binding-evidence path:
`memory/evidence/solo-r2-disposable-mechanism-shakedown-20260906/genesis-binding.json`.
It is outside arm/scorer delivery. The authorized creation result must bind the
root, exact ledger path, generated evaluation/event IDs, exact genesis length/
digest, schema ID, frozen input authority digest, D2 committed decision identity
and the exact adopted placement-contract identity. This is binding evidence,
not another ledger, authority source or allocation. No such file is created now.

Before Pair creation, the controller must compare the ledger to the independently
retained expected creation binding, not populate expected values from the ledger
currently being checked. Missing binding, wrong path/ID/digest/schema, malformed
or additional genesis, or substituted input authority refuses admission. The
binding evidence cannot itself authorize Pair creation. Its exact identity must
be pinned by the later Pair authorization; no self-declared approval is accepted.

## P05. Allocation ceiling versus schema capacity

The adopted amendment preserves L02's `attempt_ceiling_total=14` and its seven
two-attempt slots. This candidate does not silently alter those schema values.
That structural capacity does not grant disposable use of A1-A6.

This allocation is restricted to one mechanism-shakedown Pair in `R2-SHAKEDOWN`,
with its two arm Attempts subject to the existing admission/exposure rules. The
disposable entrypoint must reject other slots even if a general schema validator
accepts them. No extra allocation or Pair retry follows automatically from failure.
The original replacement allocation remains intact and is not pooled with this
one. A different numerical genesis model would require a separate schema decision.

## P06. Frozen input and repository agreement

Input authority remains A03's exact committed record, SHA-256
`5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`.
The full schema identity already binds the amendment that fixes this record.
Pair/materializer consumers must verify its available bytes and objects; a
ledger path or matching caller strings cannot substitute for that verification.
Repository derives from `base_snapshot.source_repository`; both callers using
the same wrong repository must still be rejected. S1 pre-write archive validation,
post-materialization checks, S3 audit availability and S2 open observation remain
as adopted. Frozen inputs and their paths are not changed.

## P07. Intended checks and stop

Future focused synthetic tests must cover the sole allowed placement, occupied
target, wrong path/root/evaluation/schema/genesis/input authority, missing expected
binding, both callers using the same wrong repository, and rejection of A1-A6.
Verify both existing ledgers remain untouched. No production/qualification test
or real ledger operation is performed to prepare or review this candidate.

Claims remain NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY, with purpose
MECHANISM_SHAKEDOWN_ONLY. No Formal evidence, Grimm exposure or counted evidence.
Exact placement adoption, implementation/tests/review, and actual creation remain
separate steps. Stop at this candidate; no ID, directory, ledger, Pair, Attempt,
oracle run, scoring, unblinding, production change or push is authorized here.
