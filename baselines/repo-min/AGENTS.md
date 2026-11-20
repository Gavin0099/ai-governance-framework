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

- For check intent, verify only; do not update the framework pointer.
- For update intent, including "幫我更新最新版 AI Governance", invoke
  `governance_tools.f7_full_update`; a pointer update alone is not full F-7.
- Before acting, read `governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md` and
  `governance/F7_FULL_UPDATE.md` from installed documents or the
  active, pinned framework checkout. They own evidence, stages, manual-update vocabulary,
  report templates and examples. Missing instructions or evidence mean
  `not_verified` / `blocked`; never claim completion or fabricate table rows.
- Relay the actual adoption table for every terminal F-7 result. If unavailable,
  report `human_readable_adoption_summary: NOT REPORTED` with the reason,
  `update_report_complete=false`, and `completion_claim_allowed=false`.
- Response envelope contract version: v0.8; follow
  `governance/RESPONSE_ENVELOPE_CONTRACT.md` for reporting and
  `governance/TESTING.md` for non-trivial testing decisions.

## AI Governance Memory Workflow Router
<!-- governance:key=memory_workflow -->

- Before claiming completion for any change touching `memory/**`, run `python -m governance_tools.memory_workflow --check --repo .`.
- For memory completion claims, run `python -m governance_tools.memory_workflow --check --repo . --run-guard` and report blockers before claiming DONE.
- Use the canonical memory writer (`memory_record`) for session-derived records (daily, review log, active-task summary); do not hand-edit them. A root-caused bug-fix gotcha may be written directly to `memory/03_knowledge_base.md` (or the adopted alias) only as a `CANDIDATE / UNREVIEWED` entry with root cause, fix, fix commit and test evidence, paired with a canonical daily record for the same fix commit; it never claims promotion or `Approved by`.
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
