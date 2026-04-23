# Precondition Gate Effectiveness Check

- Date: 2026-04-23
- Cases: 4
- Passed: 2
- Failed: 2

## Case Results

- missing_reset_codegen (missing reset, with codegen intent): mode=allow_draft_with_assumptions missing=[] forbidden=[] passed=False
- missing_handshake_codegen (missing handshake, with codegen intent): mode=allow_draft_with_assumptions missing=[] forbidden=[] passed=False
- ready_for_codegen (reset + handshake present, allow-codegen): mode=allow_draft_with_assumptions missing=[] forbidden=[] passed=True
- analysis_task_missing_preconditions (non-codegen analysis task with missing preconditions): mode=allow_analysis_only missing=['missing_interface_or_handshake_definition'] forbidden=['claim_interface_correctness_codegen'] passed=True

## Artifacts

- JSON: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\precondition_effectiveness\2026-04-23\precondition_effectiveness.json`
- Report: `E:\BackUp\Git_EE\ai-governance-framework\artifacts\precondition_effectiveness\2026-04-23\precondition_effectiveness_report.md`
