# Solo R2 disposable input authority binding — implementation proposal

Status: PROPOSED; no schema adoption, implementation, Pair or execution claim.

## Problem

The frozen disposable input model differs from the production model. A successful
Pair write must not describe one input while materialization uses another.
This proposal is limited to eliminating that mismatch for the disposable slice.

## Current repository truth

- `governance_tools/solo_r2_pair_creation.py:50` stores fixed experiment identities;
  `:581` writes them into the Pair event.
- `governance_tools/solo_attempt_ledger_v2.py:125` defines a closed identity set;
  `:307` validates it. The adopted schema contract L04 requires these exact keys.
- `governance_tools/solo_r2_attempt_materialization.py:830` exports an entire
  fixed commit; `:843` checks a fixed hidden-oracle blob.
- `governance_tools/solo_r2_attempt_execution.py:82` compares Pair event identities
  with the caller's mapping. That comparison does not establish that the
  materializer consumed the same authority.
- The frozen disposable authority is already committed at
  `d4d8e0f6b41d7c1837edd70f77214212d99ae372`, path
  `artifacts/experiments/solo-r2-disposable-input-definition-20260906/input-authority.owner-adopted.json`.
  Observed worktree bytes: 7719; SHA-256:
  `5c9fd7d1ed813b60ac13b6f5b495ed60da503817298af988412346682c1190bb`.
  Implementation must independently compare the committed blob, not trust this
  prose or a matching worktree path.
- Its source commit is `695863d1922c7b03a7672d3471160e5514945f95`; snapshot tree
  is `81b97b79e32e977d716754aef514930835a2f2b2`. Reference repair is a file blob,
  not a historical fix commit. Qualification remains preparation evidence only.

## Target outcome

DONE = one verified frozen authority supplies Pair identity, materialization and
pre-Attempt equality checks; synthetic integration tests reject substitution
before admission and prove exact exported file bytes. No real Pair is created.

## Scope and single source

Use the existing committed owner-adopted JSON as the sole input description.
`ExperimentInputAuthority` is an immutable parsed view, not a second manifest,
new owner decision, copied set of constants or generic experiment registry.
Resolve its exact commit/path/blob/byte-length/SHA-256 through the existing pinned
Git/repository infrastructure. Reject ambiguity, duplicate JSON keys, wrong object
types or identity mismatches. Do not execute the JSON's arbitrary command text.

The view exposes task, reused rubric, snapshot, oracle, reference repair and
qualification evidence identities. Resolve and validate these from committed
objects. Keep reference repair typed as a blob; no synthetic historical-fix claim.
Qualification evidence is verified by identity and binding, not rerun or promoted
into execution permission. Adoption flags do not authorize Pair/Attempt actions.

## Boundary and API considerations

1. A narrow Git adapter loads exact committed bytes; pure validation creates the
   immutable authority view. Missing authority has no default to the old constants.
2. Pair creation accepts that verified view and records its digest reference.
   Production must not take an independently supplied input identity mapping.
   Derive the Pair event's `repository` from the verified authority's
   `base_snapshot.source_repository` (`ai-governance-framework` for this input).
   Pre-Attempt validation derives its expected repository from that same view;
   matching two caller-supplied labels is insufficient. Verify the configured
   RepositoryBinding resolves the committed objects; the label alone is not
   repository provenance. Do not retain the `Bookstore-Scraper` constant on this
   path. This consumes an existing frozen field and requires no authority edit.
3. The public ledger carries only the arm-independent authority digest alongside
   protocol/contract/schema identities. Paths and evaluator bytes stay outside it.
   The resolver's locator is controller configuration, checked against that digest.
   Trade-off: the ledger alone no longer describes the Base/oracle selection.
   External input audit requires access to the exact authority bytes and referenced
   committed objects; the digest alone cannot resolve them. This is an audit
   dependency, not authority-publication authorization or a confidentiality proof
   (the authority already exists in local Git).
4. Materializer consumes the same view, resolves commit plus subtree to the frozen
   tree, exports with the frozen LF-preserving Git configuration, then verifies
   the exact path set and every byte identity before returning evidence. Reject
   whole-repository fallback, extra/missing files, links and changed content.
   Validate archive member paths, types and payload identities before writing
   into an arm-readable leaf; rejection after exposure would be too late.
   Retain the post-export verification as well. Use `oracle.git_blob_oid` for
   the existing Git-blob SHA-1 leakage check, per-object `sha256` for content
   verification, and SHA-256 of exact authority bytes for the ledger reference.
   Treatment packet handling stays unchanged. Hash the bytes actually exported
   and used; never interchange blob OIDs and raw-content SHA-256.
5. Materialization evidence carries the authority digest. The existing
   pre-Attempt coordinator requires equality with the Pair-bound digest before
   granting its validation result. No lifecycle transition is added or reordered.
6. Verified task/rubric/oracle byte access must come from the same view. This slice
   exposes and tests that binding; it does not claim the actual prompt, scorer or
   oracle execution used those bytes until a separately authorized execution
   integration demonstrates it. Full production admission remains unclaimed.

## Schema decision requiring exact adoption

Do not silently add keys or change meanings under the adopted Ledger v2 identity.
Propose a prospective, explicitly versioned identity-reference schema profile:
`frozen_identities` has exactly `protocol_sha256`, `contract_sha256`, `schema_id`,
`input_authority_sha256`. Its contract must bind the resolver and equality rules
above. The exact new schema ID/digest is assigned only after its text is reviewed
and adopted; this spec assigns none.

Keep historical v2 validation unchanged. Do not migrate, rewrite, rebind or append
to existing ledgers. A future new ledger/genesis must select the adopted profile
explicitly and requires separate authorization. Do not accept either field shape
indiscriminately under the old schema ID. State-machine and anonymity rules remain
unchanged; an authority digest must remain identical under arm permutation.

## Affected surfaces

Expected implementation allowlist (not changes made by this proposal):

- New `governance_tools/solo_r2_input_authority.py`: immutable view and validation.
- `governance_tools/solo_r2_pair_creation.py`: explicit authority input.
- `governance_tools/solo_attempt_ledger_v2.py`: explicitly versioned validation only.
- `governance_tools/solo_r2_attempt_materialization.py`: exact subtree export and evidence.
- `governance_tools/solo_r2_attempt_execution.py`: Pair/materialization equality.
- Direct tests for those modules and a new synthetic binding integration test.
- A prospective schema amendment document, required PLAN and canonical memory notes.

If wiring requires another production consumer, identify its concrete dependency
before extending this allowlist. Existing unrelated dirty files are excluded.

## Non-goals

No frozen-input changes, new qualification run, orphan history, forbidden-path
feature, historical Fix consumer, wrapper generalization, lifecycle redesign,
encryption/scoring redesign, platform expansion, Formal Gate 3 or infrastructure
hardening. No real ledger mutation, Pair, Attempt, child execution, unblinding,
commit or push by this proposal. No automatic migration of Grimm bindings.

## Failure paths and evidence plan

- Normal: load committed disposable authority, resolve all identities, export only
  the two frozen files; compare against independent frozen expected identities.
- Substitute any task/rubric/oracle/reference/qualification object: reject.
- Keep commit fixed but select the wrong subtree, or change LF to CRLF: reject.
- Select the snapshot parent containing evaluator siblings: reject before any
  evaluator bytes reach an arm-readable leaf, not merely after extraction.
- Supply matching but wrong `Bookstore-Scraper` labels to both callers: reject
  against the verified authority's `base_snapshot.source_repository`.
- Pair digest A with materialization digest B: reject before admission result.
- Missing authority, changed digest, duplicate keys, extra export path or wrong
  Git object type: reject without falling back to old experiment constants.
- Old schema accepts only its unchanged shape; new profile rejects old/mixed shapes.
- Permuting hidden arm assignment leaves public input reference unchanged.
- Run direct affected tests and synthetic integration only. Do not rerun the
  frozen Base/reference oracle qualification or real runtime boundary probes.

Architecture preview was attempted with the expected surfaces; the estimator
cannot read the not-yet-created module and returned FileNotFoundError. No preview
PASS is claimed. ADR-0001 concerns native Gate 3 directory handles; this proposal
does not amend that boundary. Manual dependency inspection informed this scope.

## Review dispositions and deferred observations

The supplied review is technical input, not schema adoption or execution authority.
Its unavailable governance-context notice is not treated as a formal verdict.

- S1: sibling evaluator placement is confirmed. Do not relocate frozen artifacts.
  The frozen commit/subtree paths already define the boundary; moving current
  files would not change that historical tree, and changing the frozen locator
  would violate this slice. Arbitrarily selecting a broader ancestor can defeat
  directory separation too. Require the pre-write archive checks and negative
  case above. These are proposed controls, not observed isolation evidence.
- S2 (`P2`, deferred evaluator-integrity observation): `oracle.py` imports the
  evaluated module in its own process before `unittest.main`. Evaluated code can
  interfere with test execution or reporting; an oracle success exit alone is
  not proof of evaluator integrity against adversarial output. This slice does
  not isolate that process or certify adversarial robustness. Record the limit
  now for the later owner execution decision; P2 is a proposed disposition, not
  owner risk acceptance or permission to execute. Revisit if malicious/interfering
  output is observed or stronger evaluator-integrity claims are needed. Do not
  edit the frozen oracle; any future change requires separate authority and a
  prospective identity. Pre-Pair timing is not blanket permission to change it.
- S3: audit self-sufficiency loss is explicit in the public-reference API above.
  No new disclosure mechanism or publication is authorized here.
- S4: fixed by specifying derivation from an existing frozen source_repository
  field and a negative test. No input re-freeze is needed for this correction.
- Existing deferred items stay unchanged: wrapper observation coupling and the
  declared-but-unconsumed historical Fix constant remain P2 / POST-GATE3.

## Claim ceiling and next implementation tranche

This document defines a proposed implementation scope and intended evidence only.
It does not establish compatibility, conformance, production admission, task
exposure or Skill effectiveness. Frozen input status remains unchanged.

Next: review/adopt the narrow prospective schema amendment and implement the
allowlisted binding path with synthetic tests. Stop at verified binding evidence;
remaining P07, production execution wiring, Pair creation and execution retain
their separate authority boundaries.
