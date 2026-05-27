# Reason Code Registry (Gate-Consumed Governance State)

Status: baseline registry (no taxonomy expansion)
Scope: document currently used codes in gate-consumed structured artifacts.

## Rules

- This registry only records codes already observed in current artifacts/config.
- No hierarchy, scoring model, or semantic expansion is introduced here.
- `status_code` and `reason_code` are listed separately where applicable.

## Registry

| code | type | short meaning | current usage location |
|---|---|---|---|
| `test_result_artifact_absent` | reason_code | test-result artifact missing at session boundary | `artifacts/runtime/canonical-audit-log.jsonl` (`signals[]`) |
| `production_fix_required` | reason_code | blocking action requiring production fix | `governance/gate_policy.yaml` (`blocking_actions[]`) |
| `block_if_count_exceeds` | policy_mode_code | unknown-treatment mode: block when unknown count exceeds threshold | `governance/gate_policy.yaml` (`unknown_treatment.mode`) |
| `no_eligibility_trigger` | reason_code | memory write not required because no eligibility trigger fired | `artifacts/runtime/closeout-receipts/*.json` (`memory_eligibility_reason`) |
| `repo_state_or_session_closeout_present` | reason_code | memory write required due to repo/session closeout state | `artifacts/runtime/closeout-receipts/*.json` (`memory_eligibility_reason`) |
| `NON_COMPLIANT` | status_code | closeout evidence/status non-compliant classification | closeout compliance outputs and downstream governance interpretation surfaces |

## Non-Registry Notes

- `.governance/expected_dirty.json` currently uses free-text `reason` plus `expires_at`.
- Current matrix/gate logic consumes dirty explainability and TTL validity; it does not consume a coded reason token from this file.
- Therefore, no `expected_dirty` reason code is registered in this baseline.

