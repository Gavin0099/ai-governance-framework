# AB v1.2 Run Ledger

Purpose: longitudinal run-level capture under frozen `v1.2` (no spec expansion).

Rules:
- New session per run (required).
- Same baseline commit across A/B for a given task.
- Single-task execution record (no mixed tasks in one run entry).

---

## Run Entry Template

```yaml
run_id: ""
date_utc: ""
arm: "A|B"
task_id: ""
task_type: "failure-state-remediation|cross-file-consistency|other"
baseline_commit: ""
spec_version: "v1.2"
new_session_confirmed: true

targets:
  primary_targets: []
  out_of_scope_targets: []
  first_modification_in_target: true

change_scope_metadata:
  modified_file_count: 0
  added_line_count: 0
  removed_line_count: 0
  doc_vs_code_ratio: "0:0"
  accepted_change_count: 0

metrics:
  revert_needed_after_fix: false
  unintended_change_count: 0
  semantic_consistency: 0
  coverage_completion: 0
  scope_violation_count: 0
  evidence_traceability: 0
  reviewer_edit_effort: 0
  claim_overreach_count: 0
  stalled_reasoning_count: 0
  repeated_boundary_warning_count: 0
  actionable_fix_latency_sec: "0"
  tokens_per_reviewer_accepted_fix: "0"
  modification_density: 0
  governance_signal_without_material_improvement: false

observability_only:
  runtime_governance_ratio: 0
  artifact_governance_ratio: 0
  governance_meta_lines_in_transcript: 0
  total_assistant_lines_in_transcript: 0
  governance_meta_lines_in_diff: 0
  total_added_lines_in_diff: 0
  review_navigation_burden: "low|med|high"

failure_flags:
  hard_failure: false
  attention_anchoring_failure: false
  under_commit_failure: false
  governance_drag: false

reviewer:
  disposition: "merge|minor_edit|rework"
  one_line_note: ""

artifacts:
  raw_prompt_path: ""
  raw_response_path: ""
  diff_path: ""
  scorecard_path: ""
```

---

## Quick Log Table

| run_id | arm | task_id | hard_failure | anchoring_fail | disposition | accepted_change_count | tokens_per_accepted_fix | runtime_gov_ratio |
|---|---|---|---|---|---|---:|---:|---:|
| 2026-05-07-fsr-A | A (non-governed) | cfu-failure-state-remediation-01 | false | false | merge | 4 | insufficient_data | TBD |
| 2026-05-07-fsr-B | B (governed-v1.2) | cfu-failure-state-remediation-01 | false | false | merge | 4 | insufficient_data | TBD |
| 2026-05-07-vsc-A | A (non-governed) | cfu-version-semantics-coordination-01 | false | false | merge | 4 | insufficient_data | TBD |
| 2026-05-07-vsc-B | B (governed-v1.2) | cfu-version-semantics-coordination-01 | false | false | merge | 4 | insufficient_data | TBD |
| 2026-05-07-vtb-A | A (non-governed) | cfu-validate-two-boundary-cleanup-01 | false | false | merge | 4 | insufficient_data | TBD |
| 2026-05-07-vtb-B | B (governed-v1.2) | cfu-validate-two-boundary-cleanup-01 | false | false | merge | 4 | insufficient_data | TBD |

---

## Recorded Runs (Observed)

```yaml
run_id: "2026-05-07-fsr-A"
date_utc: "2026-05-07"
arm: "A"
task_id: "cfu-failure-state-remediation-01"
task_type: "failure-state-remediation"
baseline_commit: "TBD (same package baseline intended)"
spec_version: "v1.2"
new_session_confirmed: true

targets:
  primary_targets:
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/README.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_Validation_Package_0504_1_TEST_CONCLUSION_2026-05-05.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_REFERENCE_CONCLUSION.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_TEAM_USER_GUIDE.md"
  out_of_scope_targets:
    - "firmware/driver/cfg/servicing architecture"
  first_modification_in_target: true

change_scope_metadata:
  modified_file_count: 4
  added_line_count: "TBD"
  removed_line_count: "TBD"
  doc_vs_code_ratio: "4:0"
  accepted_change_count: 4

metrics:
  revert_needed_after_fix: false
  unintended_change_count: 0
  semantic_consistency: "TBD"
  coverage_completion: 4
  scope_violation_count: 0
  evidence_traceability: "TBD"
  reviewer_edit_effort: "TBD"
  claim_overreach_count: "TBD (observed lower than prior rounds)"
  stalled_reasoning_count: "TBD"
  repeated_boundary_warning_count: "TBD"
  actionable_fix_latency_sec: "insufficient_data"
  tokens_per_reviewer_accepted_fix: "insufficient_data"
  modification_density: 1.0
  governance_signal_without_material_improvement: false

observability_only:
  runtime_governance_ratio: "TBD"
  artifact_governance_ratio: "low (no governance spill observed)"
  review_navigation_burden: "med"

failure_flags:
  hard_failure: false
  attention_anchoring_failure: false
  under_commit_failure: false
  governance_drag: false

reviewer:
  disposition: "merge"
  one_line_note: "Completed failure-state remediation with bounded claims and no out-of-scope edits."

artifacts:
  raw_prompt_path: "E:/BackUp/Git_EE/CFU_non_ai_governance (session transcript source)"
  raw_response_path: "E:/BackUp/Git_EE/CFU_non_ai_governance (session transcript source)"
  diff_path: "E:/BackUp/Git_EE/CFU_non_ai_governance (git diff in package subtree)"
  scorecard_path: "docs/ab-v1.2-run-ledger.md#recorded-runs-observed"
```

```yaml
run_id: "2026-05-07-fsr-B"
date_utc: "2026-05-07"
arm: "B"
task_id: "cfu-failure-state-remediation-01"
task_type: "failure-state-remediation"
baseline_commit: "TBD (same package baseline intended)"
spec_version: "v1.2"
new_session_confirmed: true

targets:
  primary_targets:
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/README.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_Validation_Package_0504_1_TEST_CONCLUSION_2026-05-05.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_REFERENCE_CONCLUSION.md"
    - "Tools/ComponentFirmwareUpdateStandAloneToolSample/FW_Validation_Package_0504_1/FW_TEAM_USER_GUIDE.md"
  out_of_scope_targets:
    - "firmware/driver/cfg/servicing architecture/authority model"
  first_modification_in_target: true

change_scope_metadata:
  modified_file_count: 4
  added_line_count: "TBD"
  removed_line_count: "TBD"
  doc_vs_code_ratio: "4:0"
  accepted_change_count: 4

metrics:
  revert_needed_after_fix: false
  unintended_change_count: 0
  semantic_consistency: "TBD (observed high)"
  coverage_completion: 4
  scope_violation_count: 0
  evidence_traceability: "TBD (observed very high)"
  reviewer_edit_effort: "TBD"
  claim_overreach_count: "TBD (observed very low)"
  stalled_reasoning_count: "TBD"
  repeated_boundary_warning_count: "TBD"
  actionable_fix_latency_sec: "insufficient_data"
  tokens_per_reviewer_accepted_fix: "insufficient_data"
  modification_density: 1.0
  governance_signal_without_material_improvement: false

observability_only:
  runtime_governance_ratio: "TBD (expected > Arm A)"
  artifact_governance_ratio: "low (no governance spill observed)"
  review_navigation_burden: "med"

failure_flags:
  hard_failure: false
  attention_anchoring_failure: false
  under_commit_failure: false
  governance_drag: false

reviewer:
  disposition: "merge"
  one_line_note: "Failure-state evidence semantics were explicitly separated without target displacement."

artifacts:
  raw_prompt_path: "E:/BackUp/Git_EE/CFU (session transcript source)"
  raw_response_path: "E:/BackUp/Git_EE/CFU (session transcript source)"
  diff_path: "E:/BackUp/Git_EE/CFU (git diff in package subtree)"
  scorecard_path: "docs/ab-v1.2-run-ledger.md#recorded-runs-observed"
```

### Additional Observed Runs (Compact)

```yaml
- run_id: "2026-05-07-vsc-A"
  arm: "A"
  task_id: "cfu-version-semantics-coordination-01"
  summary: "Cross-file version semantics aligned across manifest/generate_offer/README/TEST_CONCLUSION; no out-of-scope edits."
  disposition: "merge"
  hard_failure: false
  attention_anchoring_failure: false
  accepted_change_count: 4
  observability_only:
    runtime_governance_ratio: "TBD"
    artifact_governance_ratio: "low"

- run_id: "2026-05-07-vsc-B"
  arm: "B"
  task_id: "cfu-version-semantics-coordination-01"
  summary: "Same cross-file completion with stronger authority/evidence split; no target displacement."
  disposition: "merge"
  hard_failure: false
  attention_anchoring_failure: false
  accepted_change_count: 4
  observability_only:
    runtime_governance_ratio: "TBD (expected > A)"
    artifact_governance_ratio: "low"

- run_id: "2026-05-07-vtb-A"
  arm: "A"
  task_id: "cfu-validate-two-boundary-cleanup-01"
  summary: "validate-two reduced to single-cfg characterization; no acceptance overclaim left in target docs."
  disposition: "merge"
  hard_failure: false
  attention_anchoring_failure: false
  accepted_change_count: 4
  observability_only:
    runtime_governance_ratio: "TBD"
    artifact_governance_ratio: "low"

- run_id: "2026-05-07-vtb-B"
  arm: "B"
  task_id: "cfu-validate-two-boundary-cleanup-01"
  summary: "Same cleanup with explicit failure-state inference boundaries and reviewer guardrails."
  disposition: "merge"
  hard_failure: false
  attention_anchoring_failure: false
  accepted_change_count: 4
  observability_only:
    runtime_governance_ratio: "TBD (expected > A)"
    artifact_governance_ratio: "low"
```
