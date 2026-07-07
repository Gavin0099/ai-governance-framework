# Consumer Fixture Runner v0.1 Design - 2026-07-07

Status: proposal/design-only
Scope: report-only fixture execution contract for consumer/domain-contract repos

## Problem

`test_signal_quality_audit` can now report that validator fixtures and runner
scripts exist, but it intentionally cannot claim that any validator was executed
against those fixtures. That leaves the original consumer-test-quality question
partly unanswered: a repo can have pass/fail fixture files and still have no
evidence that the validator actually catches the failing case.

The missing layer is a small, report-only fixture runner contract that executes
declared domain validators against manifest-declared fixtures and compares the
observed validator result with the fixture's expected result.

## Current Repository Truth

Existing surfaces to reuse:

- `governance_tools/domain_validator_loader.py`
  - discovers declared validators from `contract.yaml`;
  - loads `DomainValidator` implementations;
  - executes validators through `run_domain_validators()`;
  - builds runtime payload envelopes through `build_domain_validation_payload()`.
- `governance_tools/validator_interface.py`
  - defines `DomainValidator.validate(payload) -> ValidatorResult`;
  - exposes `ValidatorResult.ok`, `rule_ids`, `violations`, `warnings`,
    `evidence_summary`, and `metadata`.
- `governance_tools/test_signal_quality_audit.py`
  - parses `fixture_manifest.json`;
  - associates fixtures to validators using `expected_ok`, `expected_rule_ids`,
    and safe alias fallback;
  - reports fixture runner presence only, with an explicit cannot-claim that
    runner scripts were not executed.
- `examples/multi-validator-contract/fixtures/fixture_manifest.json`
  - provides manifest entries with `file`, `expected_ok`,
    `expected_rule_ids`, and `description`.

This design does not start implementation. It defines the smallest contract a
future implementation can use without creating another validator-loader stack.

## Target Outcome

Define a report-only runner v0.1 that can answer:

```text
For each manifest fixture and each matching validator, did the observed
ValidatorResult.ok match expected_ok?
```

The output is evidence for fixture execution only. It is not proof that:

- the fixture expectation is domain-truth correct;
- the validator is semantically complete;
- the test suite is industry-grade;
- CI, hooks, or readiness gates enforce this result.

## Input Contract

Required inputs:

1. Repo root.
2. `contract.yaml` discoverable from the repo root, or an explicit
   `--contract` path.
3. `contract.yaml.validators` containing at least one validator path.
4. At least one `fixture_manifest.json` entry with:
   - `file`: path relative to the manifest directory;
   - `expected_ok`: boolean;
   - `expected_rule_ids`: list of rule IDs, recommended for unambiguous
     validator routing.

Optional input fields:

- `description`: reviewer-facing fixture purpose.
- `payload_mode`: future extension point. v0.1 defaults to checks-payload mode.
- `validator`: future explicit validator name/path override. v0.1 should prefer
  `expected_rule_ids` and only use alias fallback when no rule IDs exist.

Out-of-scope manifest features for v0.1:

- multiple expected outcomes per validator;
- expected violation-code equality;
- mutation score thresholds;
- fixture generation;
- consumer-repo repair.

## Fixture Payload Shape

v0.1 should treat each fixture file as a checks payload.

Recommended payload construction:

1. Load fixture JSON as `checks`.
2. Call `build_domain_validation_payload()` with:
   - `checks=<fixture_json>`;
   - `response_text=""`;
   - `fields={}`;
   - `resolved_rules=<expected_rule_ids or validator rule_ids>`;
   - `domain_contract=<loaded contract>`;
   - `contract_file=<contract path>`.
3. Preserve raw fixture content under `checks` so existing validators can read
   their current fields without a new schema.

Non-JSON fixtures should produce `fixture_load_error` in v0.1, not attempt
custom parsing.

## Validator Routing

Routing order:

1. `expected_rule_ids` intersection with validator `rule_ids`.
2. Explicit future `validator` field if introduced later.
3. Safe alias fallback reused from `test_signal_quality_audit`.

Ambiguity handling:

- no matching validator: `fixture_unmatched`;
- multiple matching validators:
  - if `expected_rule_ids` matches multiple validators, run all matched
    validators and report all observations;
  - if alias fallback matches multiple validators, mark
    `ambiguous_fixture_validator_match` and do not count the fixture as
    executed evidence for pass/fail coverage.

This keeps the existing false-green protection: ambiguous evidence must not be
counted as a fixture pair or runner pass.

## Result Schema

Suggested top-level shape:

```json
{
  "schema": "consumer_fixture_runner.v0.1",
  "status": "report_only",
  "repo_root": "<path>",
  "contract_path": "<path>",
  "overall_status": "all_expected | mismatch | error | no_fixtures | no_validators",
  "fixtures_total": 0,
  "observations_total": 0,
  "matched_expectations": 0,
  "mismatched_expectations": 0,
  "errors": [],
  "warnings": [],
  "observations": [],
  "cannot_claim": []
}
```

Per-observation shape:

```json
{
  "fixture": "fixtures/example_violation.checks.json",
  "manifest": "fixtures/fixture_manifest.json",
  "validator": "refactor_evidence_validator",
  "validator_path": "validators/refactor_evidence_validator.py",
  "expected_ok": false,
  "observed_ok": false,
  "matched": true,
  "rule_ids": ["refactor"],
  "violations": [],
  "warnings": [],
  "evidence_summary": "",
  "metadata": {}
}
```

Recommended `overall_status` meanings:

- `all_expected`: every executable observation matched `expected_ok`;
- `mismatch`: at least one observation ran and disagreed with `expected_ok`;
- `error`: validator load, fixture load, or validator execution error occurred;
- `no_fixtures`: no usable manifest fixtures were found;
- `no_validators`: no executable validators were found.

`all_expected` is not a readiness or industry-grade claim. It only means the
declared validator outputs matched the declared fixture expectations.

## Fail And Error Semantics

The runner is report-only:

- exit code should remain `0` for completed reports, including expectation
  mismatches;
- malformed CLI usage or unreadable repo root may exit non-zero;
- mismatch must be visible through `overall_status=mismatch` and observation
  rows, not through a gate;
- validation errors should be structured under `errors` and `warnings`;
- output must include `cannot_claim`.

Required cannot-claim entries:

- fixture expectations are domain truth;
- validators are semantically complete;
- test suite is industry-grade;
- CI, hook, readiness, or release gates enforce this result;
- mutation resistance is proven.

## Relationship To Existing Audit

`test_signal_quality_audit` and the future runner should stay separate:

- `test_signal_quality_audit`: shape and weak-signal visibility.
- `consumer_fixture_runner`: execution evidence for manifest fixtures.

The audit may later consume runner output as an optional evidence ref, but v0.1
should not couple the tools. This avoids turning a diagnostic scanner into a
fixture execution harness and keeps report-only boundaries clear.

## Dogfood Targets For Later Implementation

Initial implementation should be dogfooded read-only against:

1. `examples/multi-validator-contract`
   - Uses `fixture_manifest.json` with pass/fail fixtures for multiple
     validators.
2. `examples/usb-hub-contract`
   - Exercises a simple domain validator surface with hardware-adjacent
     fixture expectations.
3. `examples/nextjs-byok-contract`
   - Has an existing ad hoc `run_validators.py`; useful to compare framework
     runner output against repo-local runner behavior without replacing it.

External consumer repos such as kernel-driver, PCIe, or USB-Hub firmware
contracts should remain later dogfood targets after the framework example
surface works.

## Evidence Plan For Implementation Slice

The first implementation tranche should include:

- synthetic unit tests for:
  - matching `expected_ok=true`;
  - matching `expected_ok=false`;
  - mismatch visibility;
  - missing validator;
  - invalid fixture JSON;
  - ambiguous alias fallback not counted as pass;
  - `expected_rule_ids` routing to one validator among many.
- read-only dogfood on the three framework example repos above;
- `git diff --check`;
- no hook, CI, F-7, updater, or readiness integration.

## Boundary And API Considerations

Use `domain_validator_loader` as the only validator execution path. Do not add a
second dynamic import mechanism unless current helpers prove insufficient.

Keep CLI/API minimal:

```text
python -m governance_tools.consumer_fixture_runner --repo <repo> --format json
python -m governance_tools.consumer_fixture_runner --repo <repo> --contract <path> --format human
```

The future module name is a proposal. Implementation review may rename it, but
the behavior contract should remain stable.

## Claim Ceiling

This design can claim:

- the report-only fixture-runner contract is specified;
- the intended input, routing, result schema, and non-claims are defined;
- existing repository helper surfaces to reuse are identified.

This design cannot claim:

- any fixture was executed;
- any validator catches real defects;
- any consumer repo has industry-grade tests;
- readiness, F-7, hook, CI, release, or enforcement behavior changed;
- the correct implementation module name is final.
