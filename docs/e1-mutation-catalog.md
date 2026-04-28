# E1 — Mutation Catalog

> **Purpose**: Define critical governance failure modes to prove protection integrity.
> **Principle**: Validity before Expansion. **No mutation contract = No enforcement claim.**

---

## 1. Governance Mutation Catalog (Rule Removal/Bypass)
這些變異測試治理 **邏輯 (Logic)** 是否能被輕易拔除。

| Mutation / Scenario | Type | Expected Surface | Expected Violation Code | Protected Boundary |
| :--- | :--- | :--- | :--- | :--- |
| **Closeout Bypass** | Rule Mutation | `state_reconciliation_validator` | `phase_d_completed_without_reviewer_closeout_artifact` | `assess_phase_d_closeout` |
| **Precedence Bypass** | Rule Mutation | `release_surface_overview` | `authority_precedence_active_blocks_release` | `LIFECYCLE_PRECEDENCE` logic |
| **Confirmation Bypass** | Rule Mutation | `escalation_authority_writer` | `resolved_confirmed_requires_reviewer_confirmation` | `validate_prewrite_payload` |
| **Snapshot Multi-Root** | Rule Mutation | `feature_surface_snapshot` | `warning: multiple app route roots detected` | `candidate_app_roots` scan |

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
