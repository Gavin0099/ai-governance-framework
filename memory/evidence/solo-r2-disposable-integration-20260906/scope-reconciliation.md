# Disposable integration pre-commit scope reconciliation

Authority: current owner instruction, "Pre-Commit Evidence and Scope Reconciliation".
This record documents dependencies after implementation; it does not claim that
the original spec allowlist was amended before the edits. The later owner-directed
materializer/arm slice and this reconciliation authorize only the dependencies below.
The adopted binding spec and frozen input/placement/allocation authorities are unchanged.

## Earlier creation slice: naming and scope accounting (not staged again)

| Actual file | Relationship to original binding-spec allowlist |
| --- | --- |
| `governance_tools/solo_r2_disposable_binding.py` | Implements the proposed `solo_r2_input_authority.py` immutable exact-byte view, committed-object loader, and fixed disposable genesis/pre-Pair binding. Already committed in `9bcd7ffc`; not a new authority or generic registry. |
| `governance_tools/solo_r2_disposable_profile.py` | Holds fixed adopted document identities and the single disposable placement consumed by binding and v2.1 validation. Split from the proposed input-authority module to avoid cyclic imports and duplicated constants. Already committed in `9bcd7ffc`; not staged again. |
| `governance_tools/solo_attempt_ledger_v2.py` | Already-allowlisted versioned validation plus dedicated-placement write restrictions required by the later adopted placement/creation slice. Its `9bcd7ffc` change left an outstanding R1 refresh obligation. No new modification here. |
| `governance_tools/solo_r2_pair_creation.py` | Already-allowlisted authority consumer, committed in `9bcd7ffc`. Its R1 refresh obligation also remains. No new modification here. |

## Exact current implementation allowlist: seven independently reviewed files

| File | Concrete dependency and boundary |
| --- | --- |
| `governance_tools/solo_r2_attempt_materialization.py` | Already allowlisted. Pair materialization evidence must represent and verify the disposable snapshot authority rather than compare every Pair to the Grimm constant. Old v2 defaults remain. |
| `governance_tools/solo_r2_attempt_execution.py` | Already allowlisted. Pre-ID admission compares the authority consumed by materialization to the authority bound to the Pair. |
| `governance_tools/solo_r2_disposable_materialization.py` | Disposable-only implementation of exact subtree archive validation before leaf writes, reused by qualification leaves and execution leaves. Separate class preserves legacy whole-commit behavior; no generic materializer framework. |
| `governance_tools/solo_r2_disposable_execution.py` | Required missing consumer between an existing Pair and actual arm dispatch: attach to sealed order without creating genesis/Pair, admit/expose before prompt delivery, retain repaired source and runtime output. Fixed source probe binds the new consumer bytes; no oracle/scoring execution or generic ledger capability. |
| `governance_tools/solo_r2_lifecycle_integration.py` | Existing lifecycle hardcoded v2 for appended events. A default-v2 schema dispatch method permits the disposable subclass to emit adopted v2.1 events without replacing the lifecycle/state machine. This edit introduces the third R1-bound source drift. |
| `governance_tools/solo_r2_runtime_window.py` | Existing freeze assumed the ledger never changes after preflight. Each actual arm needs the same non-ledger freeze while accepting only controller-owned ledger appends; fixed disposable source identities additionally cover the new materializer. Existing readiness/provisioning and wrapper acceptance remain unchanged. |
| `tests/test_solo_r2_disposable_execution.py` | Authorized synthetic integration test: archive negatives, Pair-to-two-arm lifecycle, durable exposure ordering, repaired-byte persistence, per-arm drift and wiring rejection. Machine transport is substituted; a separate test uses real pinned Git for read-only export. |

`review.json` binds these exact seven files to independent APPROVED / Blocking=0.
The current owner supplied implementation acceptance while requiring these evidence
corrections. No review verdict is extended to unrelated working-tree files.

## Explicit exclusions

- `governance_tools/external_tree_inventory_guard.py`
- `tests/test_external_tree_inventory_guard.py`
- `governance/external-tree-inventory-guard.json`
- `tests/test_governance_workflow_contract.py`
- `.github/workflows/**` and all other unrelated dirty/untracked files.

These were present as excluded dirty work before the integration slice. The seven
reviewed files and their disposable binding/profile entrypoints have no reference
to the external inventory guard or workflow contract test. They are not required
for the disposable archive or runtime path; no inclusion, cleanup, or independent
review of their contents is authorized or needed for this commit.

## Supporting evidence and document fragments

The scoped commit may also contain this evidence directory's seven existing
receipts/reports plus this reconciliation, and only the integration/reconciliation
fragments of `PLAN.md`, `memory/2026-09-06.md`, and `memory/04_review_log.md`.
Other changes in those shared files remain unstaged. An independent commit-scope
review checks the staged file set and supporting fragments before commit.

## Outstanding R1 obligation

The baseline had two mismatches, caused by the prior creation work in `9bcd7ffc`;
the current slice adds `solo_r2_lifecycle_integration.py`. Identical failing test
names do not show that R1 stayed unchanged. `regression-comparison.json` now records
both sets, all seven expected/baseline/current fingerprints, and the new mismatch.

After the implementation commit, a separate R1 generation refresh must bind exact
committed bytes of all three drifted modules. Do not refresh before this commit,
do not describe R1 as PASS, and do not run refresh in this authorized slice.
No execution, real ledger/Pair/Attempt creation, qualification, Formal or push.
