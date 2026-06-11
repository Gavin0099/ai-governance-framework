# Implementation Packet

## identity

- task_id:
- status: DONE | PARTIAL | BLOCKED

## allowed_actions

- report changed files
- summarize diff
- report validation results
- provide patch path or inline diff
- report git status short

## forbidden_actions

- modify files outside approved scope
- omit changed files
- omit validation failures
- commit
- push
- claim selected tests passed means production ready

## changes

- changed_files:
- diff_summary:

## validation

| Command | Result | Notes |
| --- | --- | --- |
|  | NOT RUN |  |

## required_output

- task_id
- status
- changed_files
- diff_summary
- validation
- patch_path_or_inline_diff
- risks
- not_claimed
- git_status_short

## patch

- patch_path:

```diff

```

## risks

-

## not_claimed

- production readiness
- semantic correctness without review
- full regression safety without full regression evidence
- push allowed

## claim_ceiling

- may_claim:
  - implementation status for the approved scope
  - changed files listed in this packet
  - exact validation results listed in this packet
- must_not_claim:
  - production readiness from selected tests
  - semantic correctness without review
  - full regression safety without full regression evidence
  - commit allowed
  - push allowed

## human_approval_gate

- required_before:
  - modifying files outside approved scope
  - changing enforcement/schema/runtime behavior
  - running destructive commands
  - committing
  - pushing

## git_status_short

```text
git_status_short:
```

## selected_test_limitation

Selected tests passed does not mean production ready.

## token_discipline

- max_implementation_packet_words: 500
- prefer_patch_path: true
- prefer_artifact_path: true
- paste_full_diff: false
- paste_full_file_contents: false
- inline_diff_allowed: false_by_default
- inline_diff_exception: explicit_user_request_only
- expanded_evidence_allowed_when:
  - patch_path_missing
  - artifact_unreadable
  - reviewer_requests_specific_context
