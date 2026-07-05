# E1 — Mutation Catalog

> **Purpose**: Define critical governance failure modes to prove protection integrity.
> **Principle**: Validity before Expansion. **No mutation contract = No enforcement claim.**

---

## 1. Governance Mutation Catalog (Rule Removal/Bypass)
這些變異測試治理 **邏輯 (Logic)** 是否能被輕易拔除。

| Mutation / Scenario | Type | Expected Surface | Expected Violation Code | Protected Boundary | Phase 2 Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Closeout Bypass** | Rule Mutation | `state_reconciliation_validator` | `phase_d_completed_without_reviewer_closeout_artifact` | `assess_phase_d_closeout` + secondary invariant | PROTECTED (2026-06-27) ³ |
| **Precedence Bypass** | Rule Mutation | `escalation_authority_writer` | `authority_precedence_active_blocks_release` | `lifecycle_effective_by_escalation` loop | VULNERABLE (2026-06-27) — partial redundancy noted ² |
| **Confirmation Bypass** | Rule Mutation | `lifecycle_transition_writer` ¹ | `resolved_confirmed_requires_reviewer_confirmation` | line 80–81 check + secondary invariant | PROTECTED (2026-06-27) |
| **Snapshot Multi-Root** | Rule Mutation | `feature_surface_snapshot` | `warning: multiple app route roots detected` | `candidate_app_roots` scan | VULNERABLE (2026-06-27) |

> ¹ Catalog originally listed `escalation_authority_writer`; corrected to `lifecycle_transition_writer`
> where the violation code is actually emitted (verified 2026-05-12).
>
> ² Precedence Bypass has **partial redundancy**: after removing the precedence loop check,
> `authority_state_active` from `validate_prewrite_payload` (line 239) remains as a secondary signal.
> Full bypass requires TWO mutations: (1) remove lines 590–593 in `escalation_authority_writer.py`,
> AND (2) remove line 239–240 in `validate_prewrite_payload`. Single-mutation survivability = VULNERABLE;
> two-mutation full-bypass is significantly harder.
>
> ³ Closeout Bypass canonical contract is `closeout_bypass` in
> `governance_tools/mutation_proof_runner_phase2.py`: mutate the closeout gate in
> `state_reconciliation_validator.py`, run a Phase D passed / missing reviewer
> closeout fixture, and require exact violation code
> `phase_d_completed_without_reviewer_closeout_artifact`. Wrapper-only checks of
> current canonical closeout behavior are regression helpers, not mutation proof.
> See `docs/governance/reviewer-closeout-gate-mutation-contract-2026-06-27.md`.

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

### Self-Governance Truth/Provenance Baselines (2026-07-04)

These entries document self-governance truth/provenance gaps and anchor
provenance remediation. Remaining `VULNERABLE` rows are report-only
baselines; they are not `PROTECTED` mutation proof evidence.

| Scenario | Type | Expected Surface | Current Observation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Fabricated Commit Anchor** | Negative Fixture | `memory_authority_guard._entry_is_bound` | fabricated 5–40 hex `commit` no longer binds when checked against a git worktree; real commit hashes still bind | REMEDIATED baseline |
| **Fabricated Session Anchor** | Negative Fixture | `memory_authority_guard._entry_is_bound` | arbitrary `session_id` no longer binds without runtime artifact provenance; `session_id` with canonical closeout/verdict/claim artifact still binds | REMEDIATED baseline |
| **Unverified Test Evidence** | Negative Fixture | `memory_authority_guard.run_guard` | success-style `test_evidence` without an existing `artifacts/...` path now reports `test_evidence_provenance_not_found`; artifact-backed evidence passes without that warning | REMEDIATED baseline (artifact provenance only, advisory) |
| **Fabricated Evidence Artifact Content** | Negative Fixture | `memory_authority_guard.run_guard` (daily files >= 2026-07-05) | existing artifacts behind success prose are checked for a `test_evidence_receipt.v0.1` shape: non-receipt artifacts report `test_evidence_artifact_metadata_missing`, malformed receipts report `test_evidence_artifact_metadata_invalid`, a receipt recording `exit_code != 0` reports `test_evidence_exit_code_contradicts_claim`, a valid receipt whose `linked_commit` disagrees with the entry's commit anchor reports `test_evidence_linked_commit_mismatch` (prefix match; `no_git_worktree` receipts and anchorless entries skip), and evidence whose existing artifacts are all gitignored reports `test_evidence_artifact_not_durable` (requires a worktree; receipts default to tracked `artifacts/evidence/`); pre-window files stay silent; every receipt field remains fabricatable by a hostile writer | PARTIALLY REMEDIATED baseline (structured artifact metadata + commit consistency + durability, advisory) |
| **Canonical Writer Bypass Via Non-Session Memory Type** | Negative Fixture | `memory_authority_guard.run_guard`; policy-backed `memory_workflow` / CI gates | raw guard default reports `session_like_non_session_memory_type`; gate consumers that load `governance/memory_blocking_policy.json` selectively block active-window B0 entries; clean `human-note`, pre-active history, and override-downgraded entries remain report-only | REMEDIATED baseline (raw guard report-only; policy-backed gates selectively block) |
| **Report-Only Ok Semantics With Unbound Warnings** | Negative Fixture | `memory_authority_guard.run_guard` | `ok=True` remains non-blocking, but warning results now expose `ok_meaning`, `authority_integrity_status=warnings_present`, and `not_claimed: memory_authority_clean` | REMEDIATED baseline (interpretation only, advisory) |

Contract: `docs/governance/self-governance-memory-truth-provenance-mutation-contract-2026-07-04.md`.

### Self-Governance Normalizer Alias-Miss Baselines (2026-07-04)

These entries document the runtime adapter normalizer alias-miss gap and its
advisory-visibility remediation. The remaining `VULNERABLE` row is a report-only
baseline; it is not `PROTECTED` mutation proof evidence.

| Scenario | Type | Expected Surface | Current Observation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Unmapped Gate-Relevant Key** | Negative Fixture | `shared_normalizer.normalize_payload` | gate-relevant keys under unrecognized names are still dropped from mapped fields but are now surfaced in `metadata.unmapped_gate_relevant_keys` | REMEDIATED baseline (advisory) |
| **Token-Scoped Detection Limit** | Negative Fixture | `shared_normalizer.detect_unmapped_gate_keys` | a gate-relevant value under a key containing none of the gate-relevant tokens is neither mapped nor surfaced | VULNERABLE baseline |

Contract: `docs/governance/self-governance-normalizer-alias-miss-mutation-contract-2026-07-04.md`.

### Self-Governance Claim-Label Baselines (2026-07-04)

These entries document a self-governance claim-label gap and its advisory
remediation. The remaining `VULNERABLE` row is a report-only baseline; it is
not `PROTECTED` mutation proof evidence.

| Scenario | Type | Expected Surface | Current Observation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Self-Labeled Bounded Claim** | Negative Fixture | `claim_enforcement_checker.evaluate` | strength markers under a restrained `claim_level` (bounded/parity) now flag `claim_label_understates_claim_text` and route to advisory `downgrade` + reviewer override; markerless strong wording still `allow` | REMEDIATED baseline (advisory) |
| **Markerless Strong Claim** | Negative Fixture | `claim_enforcement_checker.evaluate` | a strong claim phrased without any lexical strength marker self-labels `bounded` and still produces `enforcement_action: allow` | VULNERABLE baseline |

Contract: `docs/governance/self-governance-claim-label-mutation-contract-2026-07-04.md`.

### Self-Governance Authority-Precedence Baselines (2026-07-04)

This entry is a report-only `VULNERABLE` baseline. It documents that the
declared authority-document precedence is not runtime-enforced; the fix in this
slice is a claim-ceiling clarification only, not enforcement.

| Scenario | Type | Expected Surface | Current Observation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Unenforced Authority Precedence** | Negative Fixture | `authority_loader.resolve_conflict` / `session_start` | the canonical>reference>derived ranker has no runtime caller and `can_override`/`overridden_by` have no runtime decision consumer; runtime does load-filtering + human-only exclusion only, never precedence conflict resolution | VULNERABLE baseline |

Contract: `docs/governance/self-governance-authority-precedence-mutation-contract-2026-07-04.md`.

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

All 4 Phase 2 scenarios returned **VULNERABLE** — meaning the targeted mutation survived.
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

---

## 6. Phase 2 Current Evidence Refresh (Real Rule Mutation — 2026-06-27)

Runner: `governance_tools/mutation_proof_runner_phase2.py`
Report: `artifacts/governance/mutation-proof-phase2-report-2026-06-27.json`
Tool: `git worktree` isolation — production code was NOT modified.

### Current Interpretation

The 2026-06-27 rerun returned **2 PROTECTED / 2 VULNERABLE**.

- `closeout_bypass` is now **PROTECTED**: after the primary closeout gate is removed,
  the secondary invariant still emits the exact violation code
  `phase_d_completed_without_reviewer_closeout_artifact`.
- `confirmation_bypass` is now **PROTECTED**: after the primary
  reviewer-confirmation check is removed, the secondary invariant still emits
  the exact error code `resolved_confirmed_requires_reviewer_confirmation`.
- `snapshot_multiroot_bypass` and `precedence_bypass`
  remain **VULNERABLE** under the current runner evidence.

This refresh updates current evidence status only.
It does not claim full mutation enforcement, complete E1 protection, release readiness,
or that the remaining VULNERABLE scenarios are resolved.

### Current Gap Summary (2026-06-27)

| Scenario | Status | Evidence / Note |
| :--- | :--- | :--- |
| Closeout Bypass | PROTECTED | Expected violation `phase_d_completed_without_reviewer_closeout_artifact` observed after mutation; `mutation_survived=false`; cleanup verified |
| Confirmation Bypass | PROTECTED | Expected error `resolved_confirmed_requires_reviewer_confirmation` observed after mutation; `mutation_survived=false`; cleanup verified |
| Snapshot Multi-Root | VULNERABLE | Expected stderr warning absent; `mutation_survived=true`; cleanup verified |
| Precedence Bypass | VULNERABLE (partial redundancy) | Expected reason `authority_precedence_active_blocks_release` absent; secondary signals remain but do not satisfy this mutation contract; cleanup verified |
