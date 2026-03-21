# AGENTS.md
<!-- governance-baseline: overridable -->
<!-- baseline_version: 1.0.0 -->
<!-- This file is repo-specific. Edit freely. -->
<!-- DO NOT edit AGENTS.base.md — it is a protected framework file. -->

This file extends `AGENTS.base.md`.
All rules in `AGENTS.base.md` are non-negotiable and apply to this repo unconditionally.

Add repo-specific rules below. Leave sections empty if not yet needed —
populate them as incidents, decisions, or domain requirements emerge.

---

## Repo-Specific Risk Levels
<!-- governance:key=risk_levels -->

<!-- Define what makes a change HIGH / MEDIUM / LOW risk in this repo. -->
<!-- Example:
- HIGH: any change to auth, payment, or data migration paths
- MEDIUM: adding a new API endpoint or external dependency
- LOW: documentation, config comments, test-only changes
-->

## Must-Test Paths
<!-- governance:key=must_test_paths -->

<!-- List modules or code paths that require tests before merge. -->
<!-- Example:
- src/auth/       any change here needs integration tests
- src/migrations/ schema changes need a rollback test
-->

## L1 → L2 Escalation Triggers
<!-- governance:key=escalation_triggers -->

<!-- When does this repo's work need the full L2 evidence checklist? -->
<!-- Example:
- Changing shared database schema
- Modifying public API contracts
- Any change touching >3 modules simultaneously
-->

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->

<!-- Add restrictions beyond the framework baseline. -->
<!-- Example:
- Do not write directly to the production database from tests
- Do not commit .env files even if .gitignored
-->
