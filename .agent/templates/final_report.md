# Final Report

## allowed_actions

- summarize completed approved scope
- list changed files
- report validation that was run or not run
- state risks and cannot-claim items

## forbidden_actions

- commit
- push
- run destructive commands
- claim selected tests passed means production ready
- claim unvalidated semantic correctness
- omit machine `not_claimed`, `claim_ceiling`, authority, or evidence data
- infer trust claims from compact rendering or structural `PASS`

## rendering_policy

- Keep the complete machine envelope as the canonical retained record.
- Treat the human report as a projection that may select, reorder, or translate
  recorded values but may not create or upgrade claims.
- Use compact rendering by default when the task is complete and its evidence
  and claim boundary can be projected honestly. Add one `注意：` line for
  dirty state, high-risk scope, or a decision-relevant limitation when that is
  sufficient to preserve the boundary.
- The compact `注意：` line is only for that decision-relevant limitation. Do
  not put test commands, test counts, diagnostics, or general worktree status
  in it; put those under a separate `驗證：` section after the preface or in
  the machine `evidence_refs`.
- Use expanded rendering only when the explicit full-evidence request,
  `owner_decision_required`, or `failed_or_partial` applies. The last category
  includes unavailable or conflicting required validation, an unavailable
  canonical record, or a claim/next-action boundary that cannot be projected.
- F-7 terminal results remain an expanded-report exception: relay the complete
  adoption summary required by `governance/F7_FULL_UPDATE.md` and preserve its
  unavailable-summary fallback when applicable.
- Use the same event/session identifier, retained envelope reference, and
  decision-context snapshot for preservation and rendering checks.
- The identifier, retained reference, preservation check, and decision-context
  snapshot are operational inputs or optional rendering metadata. They do not
  create new required envelope fields, validator checks, evidence-admissibility
  rules, claim-ceiling semantics, or gate conditions. `NOT RUN` is not a compact
  success signal.
- `owner_decision_required`, trigger IDs, and expanded trigger details are
  rendering predicates or optional operational metadata only. They are not new
  required machine fields, validator rules, evidence-admissibility rules,
  claim-ceiling behavior, or runtime gates.

## required_output

- compact_human_result: Result, Reason, and Next step in the session language
- canonical_machine_record: complete event envelope retained separately
- expanded_details: required only when an expansion trigger applies

## claim_ceiling

- may_claim:
  - completed scope and explicit validation evidence listed in the report
- must_not_claim:
  - production readiness from selected tests
  - semantic correctness without human review
  - full regression safety without full regression evidence

## canonical_machine_record

Existing canonical envelope values (preserve the current contract; add no
required fields):

- mode:
- mode_source:
- task:
- task_authority:
- scope:
- done:
- claim_ceiling:
- not_claimed:
- evidence_refs:
- risk:
- next_action:

Optional operational rendering metadata:

- event/session identifier:
- retained envelope reference:
- preservation check: PASS | FAIL | NOT RUN — include the check or source
- commands, artifacts, receipts, and reviewer sources remain in `evidence_refs`
  in source order.
- rendering trigger IDs and decision-context snapshot, when recorded:

## human_approval_gate

- required_before:
  - commit
  - push
  - destructive action
  - scope expansion

## compact_human_rendering

1. Result: <what is complete>
2. Reason: <the directly linked evidence and claim boundary>
3. Next step: <one concrete action, or a complete sentence saying none is needed>
4. 注意：<one decision-relevant limitation, when applicable>

## expanded_details

Include this section only when a contract trigger applies:

- 一般展開條件：`full_evidence_request`（要求完整證據）、
  `owner_decision_required`（需要負責人決定）、`failed_or_partial`（失敗或只完成一部分）；
- F-7 terminal adoption-summary relay is a dedicated expanded exception.

- primary expansion trigger ID:
- additional trigger IDs, once each in contract priority order:
- owner decision required and the reply or action that resolves it, when applicable:
- capability increased:
- changed files:
- validation:
  - structural:
  - build:
  - semantic:
  - behavioral:
  - ext evidence:
- risk:
  - scope drift:
  - claim inflation:
  - evidence maturity:
- incidental cleanup:
- governance surface change:
- remaining blocker:
- Cannot claim this session:
  - <every decision-relevant item not validated, verified, proven, or authorized>

## human_language

- Use the current session language for prose and labels.
- Keep English only for exact paths, commands, commits, APIs, schema fields,
  fixed machine tokens, and trigger IDs; do not use English conceptual labels
  when the session language has a clear equivalent.
- When an exact token is shown, add its plain-language meaning once.
- In Chinese, render `NOT CLEAN` as `工作樹仍不乾淨` unless the exact token is
  needed, then write `NOT CLEAN`（工作樹不乾淨）.
- Keep `注意：` for one decision-relevant limitation only. Put commands, test
  counts, diagnostics, and general status under `驗證：` or `evidence_refs`.
- Commands must be runnable from the repository root and retain full paths such
  as `tests/test_response_envelope_validator.py`.
- File links must use the actual workspace-relative path and verified 1-based
  line number; never invent or reuse a stale line reference.
- Every progress update must contain a new discovery, root-cause convergence,
  or plan change. Omit updates that only narrate routine commands, searches, or
  repeated validation; there is no hard maximum number of updates.

## required_scope_summary

- git diff --name-only:
- git diff --stat:
- implementation summary:
- tests not run:
- risks:

## token_discipline

- prefer_artifact_refs: true
- compact_human_lines: 3
- expanded_only_on_contract_trigger: true
- preserve_machine_record: true
- do_not_restate_full_task_history: true
