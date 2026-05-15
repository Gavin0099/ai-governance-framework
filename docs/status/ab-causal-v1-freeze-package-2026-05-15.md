# AB Causal Governance v1 Freeze Package (2026-05-15)

As-of: 2026-05-15  
Scope: runtime authority boundary evidence freeze after r45.4b + r46 + r47.

## Phase State

| phase | status | meaning |
|---|---|---|
| r45.4b | authority boundary closure | negative-path deny matrix is reproducible and reason-coded |
| r46 | topology-tagged transferability | transfer smoke passes under fixed-rule constraints |
| r47 | holdout reproducibility | holdout seeds/scenarios pass with same deny semantics |
| v1 freeze | observation phase | no governance capability expansion; drift observation only |

## Canonical Evidence Set

- r45.4b status: `ab-causal-r454b-policy-negative-smoke-status-2026-05-15.md`
- r46 status: `ab-causal-r46-cross-repo-topology-tagged-transfer-smoke-status-2026-05-15.md`
- r46 checkpoint: `ab-causal-r46-cross-repo-topology-tagged-transfer-smoke-checkpoint-2026-05-15.json`
- r47 status: `ab-causal-r47-holdout-transfer-validation-status-2026-05-15.md`
- r47 checkpoint: `ab-causal-r47-holdout-transfer-validation-checkpoint-2026-05-15.json`

Note: the files above are produced in the execution repo (`gl_electron_tool`) and referenced here as canonical freeze evidence.

## Runtime Contract Boundary (Frozen)

1. Fixed-rule constraint: policy/override/reason-code semantics unchanged during freeze.
2. No new override authority.
3. No reason-code mutation.
4. Topology metadata is non-authoritative and must not flip verdicts.
5. Fail-closed invariant remains mandatory.

## Deny-Path Matrix (Frozen)

- `tamper_without_hash_update` => `POLICY_ARTIFACT_UNTRUSTED`
- `retained_decision_mismatch_with_correct_hash` => `POLICY_ARTIFACT_UNTRUSTED`
- `scenario_id_mismatch` => `PRECHECK_OVERRIDE_PRESET_MISMATCH`
- `block_bucket_override_attempt` => `PRECHECK_OVERRIDE_POLICY_BLOCKED`

## Claim Boundary (Frozen)

Allowed claim:

`Governance effect is now observable under defined conditions, with verified negative-path reproducibility and topology-tagged transfer evidence.`

Disallowed claim:

- "governance is universally effective"
- "generalized robustness confirmed for all task topologies"

## Observation-Only Period Contract

Allowed during freeze:

- new seeds
- new topology tags
- limited new scenarios for drift probing

Disallowed during freeze:

- new rules
- new override paths
- reason-code semantic changes
- deny-path logic changes

## Exit Criteria For v1 Freeze

1. Drift observation window completed without contract violations.
2. Deny-path reason-code matrix remains stable.
3. Fail-closed behavior remains stable under holdout replay.
4. Any proposal to change rules must open v2 lineage (not patch v1 in place).
