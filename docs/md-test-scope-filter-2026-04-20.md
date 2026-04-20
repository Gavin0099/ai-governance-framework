# MD Test Scope Filter (2026-04-20)

Purpose: separate broad discovery scans from closure-grade markdown evidence.

This filter exists because whole-repo markdown scans can correctly surface
contamination risk while still being too broad to support closure decisions.
Closure evidence must be scoped to decision-proximal, repo-owned markdown
surfaces that can influence agent or human action.

## Scan Classes

### Discovery Scan

Use discovery scans to find likely contamination hotspots.

Discovery scans may include broad repo content, historical artifacts, generated
outputs, dependency docs, copied framework content, and temporary test files.

Discovery results are valid triage signals. They are not closure evidence.

Allowed conclusion:

- elevated triage risk
- candidate target surfaces
- exclusion candidates for closure reruns

Not allowed:

- close a repo from discovery results
- fail closure solely because vendored, generated, archived, or historical files
  produced directional classifications
- update after-state rerun boards without a closure-grade target set

### Closure-Grade Scan

Use closure-grade scans to decide whether remediation is complete.

Closure-grade scans must use a bounded target list and must report the target
set, include rationale, exclude rationale, fixture availability, warnings, and
per-target classification.

Closure eligibility requires:

- clean pass
- noise pass
- `directional_synthesis = no`
- `residual_decision_lean = no`
- `actionability_source = fact_fields`
- aggregate computed over the closure target set only

## Include Surface Rules

Include repo-owned markdown that is decision-proximal or authority-bearing.

Recommended include patterns:

- root `AGENTS.md`, `AGENTS.base.md`, `README.md`, `PLAN.md`, `STATUS.md`
- root `WORKFLOW.md`, `CHECKLIST*.md`, `FACT_INTAKE*.md`
- root `VALIDATION_REQUIREMENTS.md`, `SOURCE_INVENTORY.md`
- repo-owned `governance/*.md`
- repo-owned `governance/rules/**/*.md`
- operational runbooks, release/readiness docs, handoff docs, reviewer docs,
  architecture contracts, and active checklists under `docs/`
- the current MD test report only when validating report language itself

For Enumd, include generated knowledge outputs only when the generated output is
the product surface under test. Do not include the entire generated knowledge
history by default.

## Exclude Surface Rules

Exclude surfaces that are not current decision authorities unless the test
explicitly targets them.

Default exclusions:

- `node_modules/`
- `.venv/`
- `.pytest_cache/`
- transient `pytest-cache-files-*`
- vendored or copied framework trees such as `.ai-governance-framework/`,
  `ai-governance-framework/`, and `ai-governance-framework-stale/`
- historical artifact histories such as `artifacts/**/history/**`
- published old snapshots unless the publication surface is currently used
- temporary test folders and `_tmp_*` outputs
- baselines used only as fixture material
- caches and package-manager output
- memory archives and historical daily logs unless memory is the target surface
- generated knowledge waves unless the generated output is the tested product
  surface

## Warning Handling

Warnings are recorded separately from pass/fail classification.

Examples:

- `post_task_ok=None`: fixture gap; closure is not proven
- stale `PLAN.md`: planning hygiene issue; rerun after update if PLAN is in
  closure scope
- missing language pack: environment coverage gap; do not reinterpret semantic
  results as stronger than the enabled pack set supports
- domain checks such as `dispatch_compliant=false` or `dpc_compliant=false`:
  real engineering evidence gap; do not collapse into markdown wording status

## Broad Aggregate Rule

If a broad discovery scan reports `repo_classification=elevated`, treat it as an
open triage signal.

Do not copy that aggregate into closure status unless the same result is
reproduced on the closure-grade target set.

## Required Closure Evidence Record

Each closure rerun must record:

- repo name
- commit or version tested
- target files
- include rationale
- exclude rationale
- clean fixture id
- noise fixture id
- fixture availability
- warnings
- per-target clean/noise classification
- aggregate over included targets only
- conclusion: `pass`, `fail`, or `insufficient_validation`
