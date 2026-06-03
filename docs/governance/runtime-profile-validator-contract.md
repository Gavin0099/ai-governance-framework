# Runtime Profile Validator Contract v0.1

Status: machine-readable-ish contract documentation.

Validator:
- `governance_tools/runtime_profile_validator.py`

Fixture corpus:
- `tests/fixtures/runtime_profiles/`

## Purpose

This document records the current structural rule contract implemented by the
runtime profile validator and covered by the fixture corpus.

It is not a complete schema, not a JSON Schema, and not a runtime enforcement
policy. Its job is to make the validator's current behavior reviewable without
requiring reviewers to infer the contract only from Python code.

## Claim Ceiling

Claimed:
- current validator rule families are documented
- current validator error codes are documented
- current fixture coverage is mapped to rule families
- structural-only boundary is explicit

Not claimed:
- complete runtime profile schema
- formal JSON Schema compatibility
- semantic correctness
- runtime enforcement
- evidence truthfulness
- evidence relevance
- authority correctness
- OS sandbox correctness
- Hermes integration
- hook, pre-commit, or pre-push integration

## Accepted File Shape

The validator accepts YAML files parsed by `yaml.safe_load`.

Top-level document shape:
- must be a mapping/object
- directory mode scans `*.yaml` and `*.yml`
- explicit file mode validates the provided file path regardless of extension

The validator emits aggregate results:
- `ok`
- `total_files`
- `valid_files`
- `invalid_files`
- `path_errors`
- `results`

## Required Top-Level Fields

Current required top-level fields:
- `profile_id`
- `profile_version`
- `profile_authority`
- `claim_ceiling`
- `not_claimed`
- `surfaces`
- `evidence_refs`

Rule:
- field must exist
- field value must not be a placeholder

Placeholder values:
- empty string
- `none`
- `n/a`
- `see above`
- `tbd`

Error codes:
- `missing_required_field`
- `invalid_profile_shape`
- `invalid_yaml`

Fixture coverage:
- `valid_minimal.yaml`
- `valid_multi_surface.yaml`
- `invalid_missing_profile_authority.yaml`

## Claim Boundary Fields

`claim_ceiling`
- must be a non-empty list
- must not be placeholder-only

`not_claimed`
- must be a non-empty list
- must not be placeholder-only

Error codes:
- `missing_or_empty_list`
- `placeholder_only_claim_ceiling`
- `placeholder_only_not_claimed`

Fixture coverage:
- `valid_minimal.yaml`
- `valid_high_risk_with_downgrade.yaml`

## Surface Entries

`surfaces`
- must be a non-empty list
- each item must be a mapping/object

Current required surface fields:
- `id`
- `type`
- `boundary_class`
- `max_side_effect`
- `controls`
- `control_claim_ceiling`

`controls`
- must be a non-empty list

Error codes:
- `missing_or_empty_list`
- `invalid_surface_shape`
- `missing_required_surface_field`
- `missing_or_empty_controls`

Fixture coverage:
- `valid_minimal.yaml`
- `valid_multi_surface.yaml`
- `invalid_missing_surface_field.yaml`

## Evidence References

`evidence_refs`
- must be a non-empty list
- each item must be a mapping/object
- each non-placeholder evidence ref must include `command` or `artifact`
- each evidence ref must include `result`

Valid `result` values:
- `PASS`
- `FAIL`
- `NOT RUN`
- `NOT PRESENT`
- `NOT CLAIMED`

Error codes:
- `missing_or_empty_list`
- `invalid_evidence_ref_shape`
- `missing_command_or_artifact`
- `missing_or_invalid_result`

Fixture coverage:
- `valid_minimal.yaml`
- `valid_multi_surface.yaml`
- `invalid_placeholder_evidence.yaml`
- `invalid_missing_evidence_result.yaml`

Evidence refs are structural references only. They do not prove relevance,
truthfulness, source admissibility, or semantic support for the profile claim.

## High-Risk Runtime Wording

Current high-risk terms:
- `runtime enforced`
- `runtime enforcement`
- `sandboxed`
- `contained`
- `authority confirmed`
- `evidence validated`
- `behaviorally safe`
- `semantically verified`

Rule:
- if high-risk terms appear anywhere in the profile document, the profile must
  include downgrade language in `not_claimed` or `control_claim_ceiling`

Current downgrade terms:
- `not claimed`
- `no runtime enforcement`
- `not containment`
- `not trusted`
- `structural`
- `reviewer-facing`
- `heuristic`
- `requires os-level`
- `requires os boundary`

Error code:
- `high_risk_runtime_claim_without_downgrade`

Fixture coverage:
- `invalid_high_risk_without_downgrade.yaml`
- `valid_high_risk_with_downgrade.yaml`

This rule is wording-level only. It does not validate whether the downgrade is
semantically sufficient for every possible profile.

## Current Fixture Corpus Summary

Expected fixture corpus result for:

```powershell
python -m governance_tools.runtime_profile_validator tests/fixtures/runtime_profiles --format json
```

Expected aggregate:
- `ok=false`
- `total_files=8`
- `valid_files=3`
- `invalid_files=5`

Valid fixtures:
- `valid_minimal.yaml`
- `valid_multi_surface.yaml`
- `valid_high_risk_with_downgrade.yaml`

Invalid fixtures:
- `invalid_missing_profile_authority.yaml`
- `invalid_missing_surface_field.yaml`
- `invalid_placeholder_evidence.yaml`
- `invalid_missing_evidence_result.yaml`
- `invalid_high_risk_without_downgrade.yaml`

## Non-Goals

This contract does not define:
- a complete schema
- JSON Schema compatibility
- runtime profile semantics
- allowed taxonomy values for every field
- evidence admissibility
- evidence truthfulness
- authority correctness
- runtime containment
- Hermes compatibility
- advisory integration
- blocking hook or pre-push gate behavior
