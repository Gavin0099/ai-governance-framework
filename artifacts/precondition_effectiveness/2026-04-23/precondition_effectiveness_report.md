# Precondition Gate Effectiveness Check

- Date: 2026-04-23
- Cases: 4
- Passed: 4
- Failed: 0

## Case Results

- missing_reset_codegen (missing reset, with codegen intent): mode=allow_draft_with_assumptions missing=['missing_reset_definition'] forbidden=['claim_reset_safe_codegen'] passed=True
- missing_handshake_codegen (missing handshake, with codegen intent): mode=allow_analysis_only missing=['missing_interface_or_handshake_definition'] forbidden=['claim_interface_correctness_codegen'] passed=True
- ready_for_codegen (reset + handshake present, allow-codegen): mode=allow_draft_with_assumptions missing=[] forbidden=[] passed=True
- analysis_task_missing_preconditions (non-codegen analysis task with missing preconditions): mode=allow_analysis_only missing=['missing_interface_or_handshake_definition'] forbidden=['claim_interface_correctness_codegen'] passed=True

## Artifacts

- JSON: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\precondition_effectiveness\2026-04-23\precondition_effectiveness.json`
- Report: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\precondition_effectiveness\2026-04-23\precondition_effectiveness_report.md`
