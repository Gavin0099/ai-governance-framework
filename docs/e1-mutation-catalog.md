# E1 — Mutation Catalog

> **Purpose**: Define critical governance failure modes to prove protection integrity.
> **Principle**: Validity before Expansion. **No mutation contract = No enforcement claim.**

---

## 1. Governance Mutation Catalog (Rule Removal/Bypass)
這些變異測試治理 **邏輯 (Logic)** 是否能被輕易拔除。

| Mutation / Scenario | Type | Expected Surface | Expected Violation Code | Protected Boundary | Phase 2 Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Closeout Bypass** | Rule Mutation | `state_reconciliation_validator` | `phase_d_completed_without_reviewer_closeout_artifact` | `assess_phase_d_closeout` | VULNERABLE (2026-05-12) |
| **Precedence Bypass** | Rule Mutation | `escalation_authority_writer` | `authority_precedence_active_blocks_release` | `lifecycle_effective_by_escalation` loop | VULNERABLE (2026-05-12) — partial redundancy noted ² |
| **Confirmation Bypass** | Rule Mutation | `lifecycle_transition_writer` ¹ | `resolved_confirmed_requires_reviewer_confirmation` | line 80–81 check | VULNERABLE (2026-05-12) |
| **Snapshot Multi-Root** | Rule Mutation | `feature_surface_snapshot` | `warning: multiple app route roots detected` | `candidate_app_roots` scan | VULNERABLE (2026-05-12) |

> ¹ Catalog originally listed `escalation_authority_writer`; corrected to `lifecycle_transition_writer`
> where the violation code is actually emitted (verified 2026-05-12).
>
> ² Precedence Bypass has **partial redundancy**: after removing the precedence loop check,
> `authority_state_active` from `validate_prewrite_payload` (line 239) remains as a secondary signal.
> Full bypass requires TWO mutations: (1) remove lines 590–593 in `escalation_authority_writer.py`,
> AND (2) remove line 239–240 in `validate_prewrite_payload`. Single-mutation survivability = VULNERABLE;
> two-mutation full-bypass is significantly harder.

---

## 2. Negative Fixture Catalog (Hostile Inputs)
這些測試系統對 **惡意/損壞資料 (Data)** 的抵禦能力。

| Scenario | Type | Expected Surface | Expected Violation Code | Protected Boundary |
| :--- | :--- | :--- | :--- | :--- |
| **Forged Artifact** | Negative Fixture | `escalation_authority_writer` | `payload_fingerprint_mismatch` | `_fingerprint` verification |
| **Untrusted Identity** | Negative Fixture | `escalation_authority_writer` | `untrusted_writer_identity` | `WRITER_ID` verification |
| **Missing Root Dir** | Negative Fixture | `assess_authority_directory` | `escalation_active_but_no_authority_artifacts` | `escalation_active` signal |
| **State Mismatch** | Negative Fixture | `state_reconciliation_validator` | `phase_d_completed_without_reviewer_closeout_artifact` | `PLAN.md` vs Artifact check |
| **Path Violation** | Negative Fixture | `escalation_authority_writer` | `authority_write_path_violation` | `default_authority_artifact_path` |
| **Linkage Failure** | Negative Fixture | `escalation_authority_writer` | `missing_or_invalid_provenance_linkage` | `linkage_fields_ok` check |

---

## 3. Exact Failure Contract (E1-C)
- **判定標準**：僅當系統回傳上述 **精確的 Violation Code** 時，該 Proof 始視為成功。
- **防止 False Positive**：若系統僅因 `Generic Error` 或 `Exception` 而失敗，不計入有效治理證明。

---

## 4. Maintenance & Closure Policy (E1-D)
- **No mutation contract = No enforcement claim**：
  - 任何新增的治理規則若未在此 Catalog 登記 Mutation/Fixture 及其對應的 Violation Code，視為「未受保護」狀態。
  - 此狀態下，不得在 `PLAN.md` 中宣稱該 Phase 已完成「Enforcement」。
- **Regression Monitoring**：
  - 定期執行 Proof Runner 驗證此 Catalog。
  - 任何 Mutation 存活 (Survive) 或 Failure Code 不匹配，視為 P0 治理回歸。

---

## 5. Phase 2 Execution Record (Real Rule Mutation — 2026-05-12)

Runner: `governance_tools/mutation_proof_runner_phase2.py`
Report: `artifacts/governance/mutation-proof-phase2-report-2026-05-12.json`
Tool: `git worktree` isolation — production code was NOT modified.

### Interpretation

All 3 Phase 2 scenarios returned **VULNERABLE** — meaning the targeted mutation survived.
This is **expected and correct**:

- Phase 1 (Safe Fixture Probe) proved: hostile DATA cannot fool the governance tools.
- Phase 2 (Real Rule Mutation) maps: which checks have NO cross-detection fallback
  if an attacker modifies the tool source code.

VULNERABLE in Phase 2 ≠ enforcement broken.
It means each of these checks is a single point of enforcement
with no redundant cross-check currently in place.

### Gap Summary (2026-05-12) — all 4 scenarios complete

| Scenario | Status | Gap / Note |
| :--- | :--- | :--- |
| Closeout Bypass | VULNERABLE | No cross-tool redundancy; removing check fully bypasses closeout gate |
| Confirmation Bypass | VULNERABLE | `lifecycle_transition_writer` is sole enforcement; no cross-catch |
| Snapshot Multi-Root | VULNERABLE | stderr warning has no structured output or secondary catch |
| Precedence Bypass | VULNERABLE (partial redundancy) | `authority_state_active` from `validate_prewrite_payload` survives as secondary signal; full bypass needs 2 mutations |

### Next Steps

1. Accept gaps as documented — no expansion without cross-check evidence.
2. Precedence Bypass has incidental partial redundancy (`authority_state_active`) — note-worthy but insufficient for PROTECTED claim without test coverage.
3. Add cross-check redundancy only when observable hostile replay evidence exists (per AGENT.md §11).
