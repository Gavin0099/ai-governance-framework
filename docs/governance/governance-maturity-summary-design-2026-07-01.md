---
status: design-only
authority: reference
scope: report-only presentation layer
created: 2026-07-01
---

# Governance Maturity Summary Design

## Purpose

Consuming repositories can look partially governed because they have an
`AGENTS.md`, daily memory, copied governance docs, or a hook. Those surfaces do
not prove full AI Governance adoption.

This note defines a derived, report-only `governance_maturity_summary`
presentation layer that makes the current adoption surface visible to the
repository operator without creating a new authority model.

The summary must be built from existing diagnostic signals. It must not define
a fourth adoption taxonomy, must not write a committed status receipt, and must
not change gates, hooks, readiness, repair, update, or final status behavior.

## Problem

The framework already has diagnostics, but they are not surfaced consistently to
the repositories that need them most.

- `adoption_doctor.py` reports topology and static completeness.
- `agents_calibration_maturity.py` reports whether `AGENTS.md` is repo-specific.
- `external_repo_readiness.py` reports hooks, framework version, contract, and
  governance drift details.
- `governance_repo_matrix.ps1` summarizes fleet-level candidate and verified
  status.

However, copy-based repositories do not have a meaningful F-7 backend. In
`f7_full_update.py`, `copy_based_consumer` falls through to the generic
`no F-7 apply backend` result. If the summary is only added to F-7 output, the
copy-based users most likely to over-read adoption will not see it.

## Design Constraints

- Report-only and non-blocking.
- No new adoption taxonomy.
- No committed `AI_GOVERNANCE_ADOPTION_STATUS.md` receipt.
- No mutation, repair, install, fetch, hook, CI, gate, or enforcement behavior.
- Preserve `runtime_capable=not_checked` explicitly instead of omitting it.
- Prefer Python signal sources for Python callers. Do not make Python F-7 depend
  on PowerShell matrix execution.
- Treat signal disagreement as a finding, not as an implicit winner-takes-all
  decision.

## Output Points

### 1. `adopt_governance.py`

Use this output point for copy-based and thin adoption users.

The existing adoption boundary output already tells users that copy-based
adoption is audit-surface readiness, not runtime self-contained governance.
The maturity summary should extend that same report-only message.

Recommended placement:

- after `_print_adoption_boundary(repo_root, framework_root)`;
- in `--check-env` or help text only as a pointer, not as a full summary;
- no behavior change to copy/stage/refresh/drift logic.

### 2. `f7_full_update.py`

Use this output point for submodule and external-contract update paths.

The summary should be included in the stage report as additional diagnostic
context. It must not change `final_status`, `ok`, or any apply/dry-run outcome.

Recommended placement:

- `full_update_stage_report["governance_maturity_summary"]`;
- emit in JSON output and human formatting;
- keep existing stage names and semantics unchanged.

## Proposed Schema

```yaml
governance_maturity_summary:
  report_only: true
  framework_topology:
    value: copy_based | repo_owned_framework_path | submodule_consumer | unknown
    source: adoption_doctor.adoption_class
  static_self_contained:
    value: yes | no
    source: adoption_doctor.self_contained
  runtime_capable:
    value: not_checked
    source: adoption_doctor.runtime_capable
  hook_config_framework_root:
    value: inside_repo | external | absent
    source: adoption_doctor.hook_config_framework_root
  framework_pin_freshness:
    value: not_applicable | current_vs_local_tracking | behind_local_tracking | ahead_or_diverged_vs_local_tracking | unknown
    source: adoption_doctor.submodule_pin
  agents_calibration:
    value: scaffold_only | generic_filled | repo_specific_minimal | reviewer_verified
    source: agents_calibration_maturity.status
  repo_specific_rules_present:
    value: true | false
    source: agents_calibration_maturity.status
  domain_contract_present:
    value: true | false | not_checked
    source: domain_contract_loader.resolve_domain_contract
  validator_surface_present:
    value: true | false | not_checked
    source: domain_contract_loader.load_domain_contract.validators
  memory_workflow_surface:
    value: canonical_writer_detected | daily_only | not_checked | unknown
    source: memory_workflow / hook/readiness surfaces
  missing_surfaces: []
  signal_conflicts: []
  claim_ceiling:
    value: governance_assisted | repo_specific_assisted | static_self_contained_not_runtime_verified
  cannot_claim: []
```

## Signal Mapping

| Summary field | Existing source | Notes |
|---|---|---|
| `framework_topology` | `adoption_doctor.adoption_class` | Installation topology only. Do not use as maturity tier. |
| `static_self_contained` | `adoption_doctor.self_contained` | Static file presence only; not runtime smoke. |
| `runtime_capable` | `adoption_doctor.runtime_capable` | Must remain explicit as `not_checked` until a no-write smoke probe exists. |
| `hook_config_framework_root` | `adoption_doctor.hook_config_framework_root` | Surfaces inside/external/absent hook root. |
| `framework_pin_freshness` | `adoption_doctor.submodule_pin` | Local tracking comparison only; `current_vs_local_tracking` must not be shortened to `current`. |
| `agents_calibration` | `agents_calibration_maturity.status` | Measures whether `AGENTS.md` contains repo-specific rules. |
| `repo_specific_rules_present` | derived from `agents_calibration` | True only for `repo_specific_minimal` or `reviewer_verified`. |
| `domain_contract_present` | `domain_contract_loader.resolve_domain_contract` | Contract found and resolvable, not domain correctness. |
| `validator_surface_present` | `domain_contract_loader.load_domain_contract` | Validators declared and present, not executed. |
| `memory_workflow_surface` | `memory_workflow` plus existing hook/readiness signals | Must not imply complete memory consolidation. |
| `missing_surfaces` | derived | Human-readable list of absent surfaces. |
| `signal_conflicts` | derived | Report disagreements across sources. |
| `claim_ceiling` | derived | Maximum safe wording for the current surface. |
| `cannot_claim` | derived | Explicit non-claims for the current surface. |

## Conflict Handling

The summary must not silently choose one diagnostic result when sources
disagree. It should report the disagreement.

Example:

```yaml
signal_conflicts:
  - field: hooks
    sources:
      adoption_doctor: hook_config_framework_root=external
      readiness: hooks_ready=true
    action: manual_review_required
```

Conflict reporting is advisory. It should not block F-7, adopt, hooks, or CI.

## Python Versus PowerShell Boundary

`governance_repo_matrix.ps1` is a fleet presentation and trend tool. It should
not become a runtime dependency for Python F-7 or adopt output.

Python callers should use Python signal sources directly:

- `adoption_doctor.py` for topology, static self-contained, hook-root state, and
  runtime-capable non-check.
- `agents_calibration_maturity.py` for repo-specific instruction maturity.
- `external_repo_readiness.py` for hooks, framework version, contract, drift,
  and readiness surfaces where appropriate.
- `domain_contract_loader.py` for contract and validator existence.
- `memory_workflow.py` and existing hook/readiness helpers for memory workflow
  surface reporting.

The PowerShell matrix can consume the same future helper later, but it should
not be the helper's only source of truth.

## Claim Ceiling Examples

### Copy-Based Adoption

```text
claim_ceiling: governance_assisted
cannot_claim:
- runtime self-contained governance
- hooks enforce this repo's workflow
- repo-specific rules are present
- framework pin freshness applies
- domain correctness is validated
- memory fully reflects all commits
```

### Repo-Owned Framework Path

```text
claim_ceiling: static_self_contained_not_runtime_verified
cannot_claim:
- hooks are installed
- framework pin is fresh
- framework pin matches the true remote head
- runtime smoke passed
- full test suite passed
- domain validators passed
```

### Repo-Specific Rules Present

```text
claim_ceiling: repo_specific_assisted
cannot_claim:
- validator-backed domain correctness
- memory consolidation completeness
- release readiness
- CI or pre-push enforcement unless separately observed
```

## Non-Claims

This design note does not:

- implement `governance_maturity_summary`;
- add a new adoption class taxonomy;
- add a committed status receipt;
- change `adopt_governance.py`;
- change `f7_full_update.py`;
- change `external_repo_readiness.py`;
- change PowerShell matrix behavior;
- change hooks, CI, gates, runtime, memory writer behavior, or enforcement;
- prove any consuming repository is fully governed.

## Recommended Implementation Shape

Implement a shared helper after review:

```text
governance_tools/governance_maturity_summary.py
```

The helper should produce both dict and human rendering functions. Initial
callers should be:

1. `adopt_governance.py`, after the existing adoption boundary output.
2. `f7_full_update.py`, inside the report-only stage report.

Keep the helper report-only and deterministic. It should inspect local files
and local git metadata only through existing diagnostics, and it should not
repair or mutate the consuming repository.
