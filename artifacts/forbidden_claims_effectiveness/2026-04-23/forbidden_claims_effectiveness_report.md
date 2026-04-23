# Forbidden Claims Effectiveness Check

- Date: 2026-04-23
- Cases: 4
- Passed: 4
- Failed: 0

## Case Results

- missing_reset_codegen_claim_boundary (missing reset -> must forbid reset-correctness codegen claim): forbidden=['claim_reset_safe_codegen'] passed=True
- missing_handshake_codegen_claim_boundary (missing handshake -> must forbid interface-correctness codegen claim): forbidden=['claim_interface_correctness_codegen'] passed=True
- preconditions_satisfied_no_false_positive (preconditions satisfied -> forbidden claims should be empty): forbidden=[] passed=True
- analysis_task_missing_preconditions_claim_boundary (analysis-only task still exposes claim-boundary when handshake missing): forbidden=['claim_interface_correctness_codegen'] passed=True

## Artifacts

- JSON: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\forbidden_claims_effectiveness\2026-04-23\forbidden_claims_effectiveness.json`
- Report: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\forbidden_claims_effectiveness\2026-04-23\forbidden_claims_effectiveness_report.md`
