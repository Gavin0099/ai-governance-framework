# AGENTS.md
<!-- governance-baseline: overridable -->
<!-- baseline_version: 1.0.0 -->
<!-- This file is repo-specific. Edit freely. -->
<!-- DO NOT edit AGENTS.base.md — it is a protected framework file. -->

This file extends `AGENTS.base.md`.
All rules in `AGENTS.base.md` are non-negotiable and apply to this repo unconditionally.

Add repo-specific rules below.
Fill in each section below, or write `N/A` if the section is not applicable to this repo.

Quick start:

1. Start with the top 1-3 risky paths in this repo, not a full policy rewrite.
2. If you already have a checklist / runbook / test convention, copy that wording here instead of inventing new terms.
3. If a section truly does not apply, keep `N/A` and move on.

---

## AI Governance Update Intent Rule

This is the ALWAYS-READ F-7 routing and truthfulness boundary. The complete
work instructions, result vocabulary, evidence shapes, stage details and
reporting examples live in the canonical pinned framework documents:
- `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`
- `governance/F7_FULL_UPDATE.md`
- `governance/RESPONSE_ENVELOPE_CONTRACT.md`

Resolve these against the consumer's installed governance documents or the
active, pinned framework checkout (which may be a submodule). Do not consult
an unrelated version and assume it matches the current consumer. For F-7
updates, load the canonical update and F-7 documents before acting or
claiming completion. Missing instructions or unverified evidence mean
`not_verified` / `blocked`, **not** `updated` or `already_current`.
On-demand documents cannot authorize commit, push, release or destructive
work that the current Owner has not authorized.

### AI Governance Check Vs Update Intent

- For `check` intent (e.g., 「檢查 AI Governance 是否最新」), verify only.
  Never update the framework pointer.
- For `update` intent (e.g., 「幫我更新最新版 AI Governance」 or
  "Update AI Governance to latest"), invoke
  `governance_tools.f7_full_update` as the primary orchestrator.
  The submodule updater alone is only one stage, not complete F-7.
  Do not repeat a request for authorization already granted within the
  approved scope; stop only for a real blocker or an Owner-gated action.

Never claim `already_current` solely from `AGENTS.md` unchanged,
`AGENTS.base.md` unchanged, clean parent git status, parent
`HEAD == origin/main`, or `git pull --ff-only`. A defensible
submodule status requires the actual governance submodule path,
nested framework HEAD, target approved framework HEAD, and governed
updater dry-run result. `update_available` is not a completed update.

Full technical shape and terminal report definitions must come from the
canonical docs above. Status line (never fabricate values):

```text
AI Governance update check: <already_current | update_available | updated | manual_update | destructive_manual_update | not_submodule_consumer | not_verified>
```

This baseline is a propagated, managed consumer instruction copy of the
canonical manual-update reporting vocabulary in
`governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`. The canonical file is the
authority; this compact copy is an execution entrypoint, not another status
definition. `manual_update` and `destructive_manual_update` are truthful
fallbacks for pointer/lock/checkout changes without the governed F-7 path,
**never** evidence for completed/latest/full adoption. Disclose discarded
modified and untracked paths before claiming destructive cleanup; obtain
Owner authorization before discarding anything. If a parent repo commit
was not created, report `parent repo commit: NOT CREATED`.

Manual update conclusion template:

```text
AI Governance update check: manual_update
ai_governance_update_result: REPORTED
framework_update_status: manual_update
governance maturity summary: <RUN | NOT RUN | NOT AVAILABLE>
adoption_status: <from maturity summary | unknown>
human_readable_adoption_summary: <REPORTED | NOT REPORTED>
reason: governed updater/F-7 was not used
claim boundary: manual pointer/lock/checkout changes may be reported; do not claim completed/latest/full adoption
```

Destructive manual update conclusion template:

```text
AI Governance update check: destructive_manual_update
ai_governance_update_result: REPORTED
framework_update_status: destructive_manual_update
discarded_modified_paths: <list | none reported>
discarded_untracked_paths: <list | none reported>
governance maturity summary: <RUN | NOT RUN | NOT AVAILABLE>
human_readable_adoption_summary: <REPORTED | NOT REPORTED>
claim boundary: destructive local cleanup occurred; do not claim completed/latest/full adoption
```

### Response Envelope Boundary

- Response envelope contract version: v0.8. Compact human responses are the default.
- Failed/partial work and owner decisions may remain compact if the
  blocker, ability to proceed, risk, claim boundary and Owner choice are clear.
  Expand when canonical evidence is unavailable, an explanation cannot be
  preserved briefly, or full evidence is requested.
- Keep all raw fields in canonical evidence; use plain-language meanings for
  decision-relevant status tokens.
- For review, diagnosis and concepts, use Engineering Explanation
  without forcing an irrelevant next action.
- For completion or partial-completion F-7 reports, retain the first three
  non-empty lines as 結果 / 原因 / 下一步 (translated in other session
  languages). Explain local completion, commit/push/merge state and important
  unverified behavior in plain language before the complete adoption table;
  suggested actions do not grant
authorization.

If the session only updates `AGENTS.md` or other local instruction files,
mark governance framework status `not_verified` and do not claim a complete
update. The examples below remain an explicit negative/positive boundary.

Invalid conclusion:

```text
AGENTS.md was updated and the parent repo is up to date, so AI Governance is current.
```

Valid partial conclusion:

```text
結果：這次只更新了指令文件，尚不能確認治理框架更新完成；沒有建立提交，上傳與合併狀態未確認。
原因：治理框架的版本與導入狀態尚未檢查。
下一步：先檢查框架版本及導入狀態，再判定是否需要更新；不因此取得更新或上傳授權。

AI Governance update check: not_verified
governance submodule path: NOT CHECKED
nested governance HEAD: NOT CHECKED
target framework HEAD: NOT CHECKED
dry-run: NOT RUN
update mode: NOT CLAIMED
parent repo commit: NOT CREATED
governance maturity summary: NOT RUN
user-facing adoption status: NOT REPORTED
human_readable_adoption_summary: NOT REPORTED
```

For every F-7 terminal result, relay actual
`[human_readable_adoption_summary]` rows as a TABLE. A clean build,
`adoption_doctor: findings 0` or a pointer update is no substitute.
If the real table cannot be produced or relayed, report
`human_readable_adoption_summary: NOT REPORTED` and the reason;
also set `update_report_complete=false` and
`completion_claim_allowed=false`. Never fabricate rows or claim complete
adoption. Report completeness is separate from update success.

### Test Quality Expectations

Non-trivial changes require evidence beyond happy-path-only tests:
bug regressions where feasible, independently sourced expected results,
and validator pass/fail cases. Mock-only success and
`test_signal_quality_audit` are not proof of correctness or enforcement.
Read the detailed `governance/TESTING.md` for testing decisions.

### F-7 Full Update Semantics

F-7 has six necessary stages: framework pointer, repo-local instructions,
memory writer coverage, hook/validator coverage, existing memory
normalization status, and user-facing maturity/adoption report. A raw
submodule pointer update alone is `partially_updated`, not completed.

`full_update_completed` is permitted only when every required stage is
actually verified as updated, already_current, verified, completed or
not_applicable. Missing, needed, blocked or not_verified surfaces are NOT
complete. Read `governance/F7_FULL_UPDATE.md` for the layered status
fields and the exact final adoption report. Successful structural checks
do not prove real-session hook execution or that legacy memory was
normalized.


## AI Governance Memory Workflow Router
<!-- governance:key=memory_workflow -->

- Before claiming completion for any change touching `memory/**`, run `python -m governance_tools.memory_workflow --check --repo .`.
- For memory completion claims, run `python -m governance_tools.memory_workflow --check --repo . --run-guard` and report blockers before claiming DONE.
- Use the canonical memory writer for session-derived memory; do not edit memory records as ordinary markdown.
- Canonical writer signal: `governance_tools.memory_record` / `memory_record.py`.

## Repo-Specific Risk Levels
<!-- governance:key=risk_levels -->

<!-- Define what makes a change HIGH / MEDIUM / LOW risk in this repo.
Example:
- HIGH: any change to auth, payment, or data migration paths
- MEDIUM: adding a new API endpoint or external dependency
- LOW: documentation, config comments, test-only changes

Prompt yourself:
- What changes in this repo can corrupt state, break compatibility, or cause production downtime?
- What changes are review-heavy but still reversible?
- What changes are safe enough to keep in a fast path?
-->

N/A

## Must-Test Paths
<!-- governance:key=must_test_paths -->

<!-- List modules or code paths that require tests before merge.
Example:
- src/auth/       any change here needs integration tests
- src/migrations/ schema changes need a rollback test

Prompt yourself:
- Which files or directories would you never want changed without a test?
- Which paths are easy to break with static changes alone?
- Which user-visible or hardware-facing flows need explicit coverage?
-->

N/A

## L1 → L2 Escalation Triggers
<!-- governance:key=escalation_triggers -->

<!-- When does this repo's work need the full L2 evidence checklist?
Example:
- Changing shared database schema
- Modifying public API contracts
- Any change touching >3 modules simultaneously

Prompt yourself:
- What kinds of changes cross system boundaries?
- What changes would require a reviewer to ask for stronger evidence than normal?
- What changes become risky mainly because they are broad, not because they touch one file?
-->

N/A

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->

<!-- Add restrictions beyond the framework baseline.
Example:
- Do not write directly to the production database from tests
- Do not commit .env files even if .gitignored

Prompt yourself:
- What are the easy-to-make mistakes that are specific to this repo?
- Are there tool, environment, hardware, or deployment actions that should never happen casually?
- What "cleanup" or "shortcut" behaviors have already caused pain here?
-->

N/A
