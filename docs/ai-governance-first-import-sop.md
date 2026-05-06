# AI Governance First Import SOP

Date: 2026-05-06

## Objective

Provide a repeatable process for first-time AI governance import into a consuming repo that has no complete governance baseline yet.

## Scope Boundary

- In scope: governance scaffold import, runtime/governance validation, report artifact.
- Out of scope: domain business logic changes (for example firmware/driver/protocol code).

## Execution Context (Mandatory)

Unless otherwise stated:

- `adopt_governance.py` commands are executed from `ai-governance-framework` repo root.
- validation commands are executed from consuming repo root after adoption.

If command context is ambiguous, stop and print current working directory before continuing.

## Minimum Viable Governance Baseline (MVGB)

First import is not considered complete unless all of the following are present and meaningful:

- `AGENTS.md` is repo-specific and not generic placeholder-only content.
- `.governance/version_manifest.yaml` exists and is syntactically valid.
- `governance/framework.lock.json` exists and records framework source/release/commit.

## Procedure

1. Clone and prepare
- clone framework and consuming repo in the same workspace
- confirm target repo root and Python interpreter

2. Preflight with dry-run
- run:
```powershell
python governance_tools/adopt_governance.py --target <repo> --dry-run
```
- review planned file actions before writing

3. Execute adoption
- run:
```powershell
python governance_tools/adopt_governance.py --target <repo>
```

4. Resolve common first-import gaps
- ensure these files exist and are valid:
  - `.governance/version_manifest.yaml`
  - `governance/framework.lock.json`
  - `governance/gate_policy.yaml`
- ensure `AGENTS.md` is not left as generic placeholder-only content
- treat these as MVGB requirements, not optional improvements

5. Validate runtime/governance path
- run:
```powershell
python quickstart_smoke.py
python runtime_hooks/core/session_start.py --project-root . --plan-path PLAN.md --task "governance import validation" --rules common --risk low --oversight review-required --memory-mode candidate --format json
python runtime_hooks/core/pre_task_check.py --project-root . --task-text "governance import validation" --rules common --risk low --oversight review-required --memory-mode candidate --format json
python -m governance_tools.external_repo_readiness --format json
python -m governance_tools.governance_version_check --project-root . --format json
```

6. Optional but recommended
- install git hooks (`pre-commit`, `pre-push`)
- run onboarding report:
```powershell
python -m governance_tools.external_repo_onboarding_report --format json
```

6.1 One-command validation runner (recommended)
- run:
```powershell
python governance_tools/run_first_import_validation.py --repo-root .
```
- output file (default):
  - `AI_Governance_First_Import_Validation_<YYYYMMDD>.md`

7. Produce evidence report
- write one markdown report in consuming repo root, for example:
  - `AI_Governance_Import_Test_Report_<YYYYMMDD>.md`
- include:
  - imported framework version and commit
  - files added/updated for governance
  - command list + pass/fail summary
  - blocking vs non-blocking warnings

## Success Criteria

- `external_repo_readiness.ready = true`
- quickstart smoke passes
- session_start and pre_task_check pass without controlled refusal
- governance version check is compatible
- evidence report exists and includes exact command outputs or explicit artifact paths
- imported framework commit is explicitly recorded in the report

## Known Non-Blocking Warnings

- framework-side `expansion_boundary` warning
- hooks not installed (readiness may still be true)

## Fail-Fast Indicators

- `version_compatibility_unsupported`
- controlled refusal from `session_start` due to missing version manifest
- missing framework lock causing framework version state to be unknown/outdated
- `AGENTS.md` remains generic placeholder-only after adoption
