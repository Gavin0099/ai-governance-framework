# Review Packet

## identity

- task_id:
- review_mode: read_only_patch_review

## allowed_actions

- read task packet
- read implementation packet
- read patch or inline diff
- produce read-only review findings
- recommend a decision

## forbidden_actions

- edit files
- commit
- push
- inspect unrelated dirty files without approval
- claim selected tests passed means production ready
- treat Reviewer ACCEPT as DONE or push allowed

## inputs

- task_packet:
- implementation_packet:
- patch_path:
- git_status_short:

## review_scope

- files:
- diff source:
- non-goals:

## hard_rules

- Review only the provided patch and approved scope.
- Do not edit files.
- Do not commit.
- Do not push.
- Do not inspect unrelated dirty files without approval.
- Flag any claim that selected tests passed means production ready.
- Reviewer ACCEPT only means candidate_for_commit. It does not mean DONE and does not mean push allowed.

## required_output

- task_id
- verdict: ACCEPT | CHANGES_REQUESTED | BLOCKED
- findings ordered by severity
- scope drift assessment
- claim ceiling assessment
- validation adequacy
- unsafe claims to avoid
- recommended decision

## claim_ceiling

Review output states whether the patch is acceptable as a commit candidate. It does not authorize commit, push, deployment, or production readiness.

## human_approval_gate

- required_before:
  - expanding review scope
  - editing files
  - committing
  - pushing
  - inspecting unrelated dirty files

## token_discipline

- max_review_packet_words: 300
- max_review_result_words: 800
- prefer_patch_path: true
- prefer_artifact_path: true
- paste_full_diff: false
- paste_full_file_contents: false
- reviewer_should_request_expanded_context_only_when:
  - patch_path_missing
  - artifact_unreadable
  - evidence_insufficient_for_verdict
