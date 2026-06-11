# Review Report

## identity

- task_id:
- review_mode: read_only_patch_review

## allowed_actions

- read approved packets
- read in-scope patch or diff
- identify findings, scope drift, claim inflation, and evidence gaps
- recommend a decision

## forbidden_actions

- edit files
- commit
- push
- inspect unrelated dirty files without approval
- claim selected tests passed means production ready
- treat Reviewer ACCEPT as DONE or push allowed

## reviewed_scope

- files:
- receipts:
- diff source:

## required_output

- task_id
- verdict
- findings
- approval_gate_assessment
- claim_ceiling_assessment
- selected_test_limitation
- risks
- next_recommended_step

## findings

| Severity | File | Issue | Recommendation |
| --- | --- | --- | --- |
|  |  |  |  |

## approval_gate_assessment

- scope expansion detected: yes | no | unknown
- human approval required: yes | no
- approval evidence:

## claim_ceiling_assessment

- stated claim ceiling:
- supported by evidence: yes | partial | no
- claim inflation detected:

## selected_test_limitation

Selected tests passed does not mean production ready. Any wording that implies otherwise is a review finding.

## verdict

- pass | changes requested | blocked

## claim_ceiling

- may_claim:
  - reviewed evidence supports or does not support candidate_for_commit
- must_not_claim:
  - DONE from Reviewer ACCEPT
  - push allowed from Reviewer ACCEPT
  - production readiness from selected tests

## human_approval_gate

- required_before:
  - expanding review scope
  - editing files
  - committing
  - pushing
  - inspecting unrelated dirty files

## risks

- scope drift:
- claim inflation:
- evidence maturity:

## next_recommended_step

-

## token_discipline

- max_review_report_words: 800
- prefer_patch_path: true
- cite_findings_not_full_history: true
- paste_full_diff: false
- expanded_context_required_only_for_blockers: true
