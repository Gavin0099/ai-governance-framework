# Solo R2 disposable input authority — schema amendment candidate

Status: CANDIDATE / NOT OWNER ADOPTED / NO IMPLEMENTATION OR EXECUTION AUTHORITY.

## A01. Scope and authority

This is a prospective, disposable-shakedown-only amendment to the exact R2 set
adopted in `solo-evaluation-revision-2-owner-adoption-20260831.md`. The parent
ledger schema digest (SHA-256) is
`d64d9f881a07947b363ef12d2c53e8628dcd4b4dabbf89ba3cbd42f4131d01bb`.
The distinct parent field bindings are:

- `protocol_sha256` = `1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff`.
- `contract_sha256` = `3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea`
  (execution contract, not ledger schema).

After separate exact-byte owner adoption, this amendment overrides only the
input representation and schema dispatch identified below. All other parent
protocol, execution and ledger constraints continue to apply. No authority
exists merely because a document calls itself adopted or carries a digest.

For this synthetic disposable input only, P07's historical Base/Fix selection is
represented by the frozen snapshot commit/subtree and typed reference-repair
artifact. This does not assert a historical fix exists or change counted tasks.
All other P07 prerequisites remain required and unproven by input qualification.

## A02. Version dispatch and historical preservation

Prospective public ledger `schema_version`: `solo_attempt_ledger.v2.1`.
Prospective `adopted_schema_id` in genesis and `schema_id` in Pair identities:
`solo_attempt_ledger.v2.1@sha256:<SHA-256 of exact adopted amendment bytes>`.
The digest is resolved externally after adoption; it is not embedded in this
document. An adoption record must bind this amendment and the exact parent set.

Only an explicitly authorized new ledger may use this profile. Genesis and
events must agree on v2.1 and the adopted amendment identity; mixed versions,
unknown profiles and fallback to v2 are rejected. Parent genesis/event shapes,
ceilings, sequencing, anonymity and lifecycle transitions otherwise stay intact.
This neither creates a genesis nor grants reuse of an existing evaluation ID.
Historical v2 validators and bytes remain unchanged; no existing ledger is
migrated, rewritten, rebound or appended to under this amendment.

OPEN PREREQUISITE: disposable ledger placement and evaluation allocation require
a separate owner decision. This amendment does not authorize a new evaluation_id
or a third ledger, does not supersede the one-replacement-evaluation decision,
and does not authorize migration or rebinding of either existing ledger.
No usable disposable v2.1 ledger is established by adopting this amendment.
Placement, allocation and any required exception to that prior owner decision
must be resolved before production work that introduces such a ledger or any
disposable Pair creation. Do not solve this prerequisite by adding a path constant
or treating schema adoption as evaluation/ledger creation authority.

## A03. Authority-record version without changing frozen bytes

Authority-record interpretation profile: `solo_r2_disposable_input_authority.v1`.
This is an external profile assigned by this amendment, not a field claimed to
exist in the frozen JSON. The admitted JSON has no embedded schema version.
The v2.1 profile selects this interpretation explicitly; no format inference or
fallback from arbitrary unversioned JSON is permitted.

Its sole admitted record locator and exact identity are:

- Commit: `d4d8e0f6b41d7c1837edd70f77214212d99ae372`.
- Path: `artifacts/experiments/solo-r2-disposable-input-definition-20260906/input-authority.owner-adopted.json`.
- Git blob OID: `e25109c8ec03964043af18657c143f2807eb4764`.
- Bytes: `7719`.
- SHA-256: `5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`.

Resolve that committed blob, verify all identities before parsing, and reject
duplicate JSON keys, missing required values or wrong types. Never add a version
field to the record, reserialize it to compute its identity, or substitute its
worktree path. Exact-byte admission fixes its complete field set; this profile
does not accept other manifests with a merely similar shape.

## A04. Single input description and exact objects

An immutable parsed `ExperimentInputAuthority` is a view of A03, not another
manifest or an independent set of input constants. The following frozen fields
are normative references; consumers must not replace their values:

| Material | Record field | Required verification |
| --- | --- | --- |
| Task | `task_prompt` | commit/path resolves a blob; bytes, SHA-256 and Git blob OID agree |
| Rubric | `rubric` | same exact-blob checks; agrees with `rubric_reuse.adopted_source` bytes and declared rubric version |
| Snapshot | `base_snapshot` | commit is a commit; subdirectory resolves the exact tree_oid; files describe the complete exported inventory |
| Oracle | `oracle` | exact committed blob, byte length, SHA-256 and blob OID |
| Reference repair | `reference_repair` | exact blob checks; remains a repair artifact, never relabeled historical_fix_commit |
| Qualification | `qualification` | exact blob checks and its bindings to the same snapshot/oracle/repair and required cases |

For qualification's omitted commit, use A03's enclosing commit only; do not
infer HEAD or a mutable branch. Nested source_candidate and rubric provenance
references retain their own frozen commits. Missing/unavailable committed objects
or contradictory bindings cause refusal. No qualification is rerun by resolution.
The material identities live only in the frozen record; this table does not
introduce alternate values or authority over those bytes.

## A05. Public reference and repository derivation

Under v2.1, `frozen_identities` has exactly four required string keys:
`protocol_sha256`, `contract_sha256`, `schema_id`, `input_authority_sha256`.
The first two equal the adopted parent protocol and execution contract digests;
schema_id equals A02; input_authority_sha256 equals A03's SHA-256. Unknown, mixed
or legacy seven-key forms are rejected in v2.1; v2 does not accept this new form.

`PAIR_CREATED.repository` must be derived directly from the verified
`base_snapshot.source_repository`: `ai-governance-framework` for this record.
Pair creation and the pre-Attempt consumer must use this same derivation, never
independent caller labels. Reject even when both callers supply the identical
wrong label. Verify the controller's configured RepositoryBinding resolves the
frozen committed objects; a repository name alone proves no provenance.

## A06. Availability and disclosure limit

The controller must obtain and verify A03's exact authority bytes and referenced
objects before Pair validation and materialization. A digest without resolvable
bytes is insufficient: refuse, with no old-constant or reconstructed-record fallback.
Public audit is not self-contained in the ledger: an auditor needs the authority
bytes and referenced objects to resolve Base/oracle selection. Their availability
is an audit prerequisite, not permission to expose evaluator data to an arm or
scorer or to publish new artifacts. A digest alone is not confidentiality proof.
Public references remain identical under hidden arm/order permutation.

## A07. Pre-write and post-materialization verification

Resolve the exact commit/subdirectory to the frozen tree before export. Construct
only the prescribed subtree export with command-local `core.autocrlf=false`;
do not execute arbitrary `archive_argv` text or fall back to a parent/whole repo.
Validate the complete archive member set, safe relative paths, regular-file types
and payload identities before writing any payload into an arm-readable workspace.
Reject duplicate members, traversal/absolute paths, links, extra/missing files,
the parent directory export and byte mismatches before such writes occur.

After materialization, independently verify the exact file inventory and bytes
actually supplied to the arm. Refuse on drift, including line-ending conversion.
The oracle leakage check consumes `oracle.git_blob_oid` (Git blob SHA-1); content
checks consume each object's SHA-256; ledger references hash exact authority bytes.
These hash domains are not interchangeable. Evaluator artifacts never enter the
arm snapshot. Preserve existing treatment packet checks and isolation constraints.

## A08. Consumer agreement and remaining admission

Materialization evidence carries the A03 authority digest. The pre-Attempt
coordinator compares it with the Pair-bound digest and verifies A05's repository
derivation before granting validation. Digest equality without verified material
bytes is insufficient. Failure must precede admission/handle generation.
Task/rubric/oracle access must come from this verified view; providing an accessor
does not prove eventual execution consumed it. Actual execution integration and
the rest of P07/readiness remain separately required. Existing false authorization
flags and `production_admission_compatible=false` in the frozen record are
historical freeze-stage limits; this amendment never rewrites or flips them.
Later admission, if authorized, requires separate evidence bound to this record.

## A09. S2 open observation

Status: OBSERVATION / NOT OWNER-ACCEPTED / NOT YET PROVEN BLOCKER.
The frozen oracle imports evaluated code within its own process. Such code can
interfere with evaluator behavior/reporting; a success exit alone does not prove
adversarial evaluator integrity. Record this before any Pair decision. This
amendment neither accepts the risk nor mandates process splitting, IPC, a service
or oracle redesign. During later binding/execution review, escalate if a concrete
path is shown to violate the required oracle-independence/contamination boundary.
No later result may silently upgrade this observation into a robustness claim.

## A10. Required conformance evidence and stop

Future implementation must test exact committed resolution and exact two-file
export, changed identities, unresolved authority bytes, wrong subtree/parent,
pre-write rejection, post-write drift, wrong object types, duplicate keys, mixed
schema forms, Pair/materializer digest mismatch, and identical-but-wrong caller
repository labels. Retain unchanged v2 regression and public permutation checks.
Use synthetic fixtures; this amendment review does not run production or repeat
Base/reference qualification. Test success is not implementation review or owner
adoption. Claims remain NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY.

STOP after candidate exact-byte review. Owner adoption must name these exact
bytes; a later scoped commit and implementation require their own authorization.
No Pair, Attempt, real ledger mutation, child/oracle execution, scoring, unblinding,
push, frozen-input change, Grimm allocation change or Formal Gate 3 work is granted.
