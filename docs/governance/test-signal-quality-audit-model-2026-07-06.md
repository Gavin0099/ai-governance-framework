# Test Signal Quality Audit Model

Status: PROPOSAL / DESIGN ONLY
Date: 2026-07-06
Scope: consumer-repo test-signal quality audit model

## DONE

DONE = design an AI Governance test-signal quality audit model for consumer
repos. The design maps existing testing doctrine into report-only audit
signals that can later be used by consumer-repo review, onboarding, or
contract-authoring workflows.

This document does not implement a scanner, validator, gate, hook, CI check, or
consumer-repo repair.

## Problem

Consumer repos can appear "tested" while their tests provide weak engineering
signal. Common weak patterns include:

- expected values copied from production logic;
- happy-path-only coverage;
- mock-only assertions that prove a collaborator was called but not that an
  observable behavior happened;
- missing negative, boundary, and failure-path cases;
- nondeterministic tests hidden behind sleeps, wall-clock time, or unseeded
  randomness;
- legacy refactor tests that do not establish a known-good baseline;
- validators without fixture-backed expected results.

The framework already documents many of these expectations in `TESTING.md`, but
there is no consumer-facing audit model that summarizes whether a repo's test
suite is behavior-protective or merely coverage-shaped.

The problem is test-signal quality visibility, not automatic proof that a test
suite meets industry standards.

## Current Repository Truth

Observed framework surfaces:

- `governance/TESTING.md` already requires invalid input, boundary values, and
  failure paths for L1+ work, and treats L2 work as needing normal path,
  failure path, boundary input, and invalid input unless explicitly
  non-applicable.
- `governance/TESTING.md` section 3.2 requires independent expected values
  from specs, fixed examples, invariants, or independent fixtures. Tests that
  derive expected values from production logic must be labeled
  characterization or weak coverage.
- `governance/TESTING.md` section 3.3 defines mutation thinking and examples
  such as boundary flips, reversed conditions, removed guards, and off-by-one
  loop bounds.
- `governance/TESTING.md` sections 7.1 through 7.4 cover assertion strength,
  mock-only weakness, determinism, trust-boundary tests, and behavior-source
  requirements.
- `governance_tools/external_repo_readiness.py` surfaces contract presence,
  document completeness, and validator file presence, but it does not assess
  whether validators have negative fixtures or independent expected results.
- `governance_tools/governance_auditor.py` treats `governance/TESTING.md` as a
  required governance document, but it does not audit consumer test-suite
  quality.
- `governance_tools/adopt_governance.py` can ensure consumer `contract.yaml`
  references `governance/TESTING.md` and `governance/ARCHITECTURE.md`, but it
  does not create or evaluate test-quality evidence.
- `.agents/skills/domain-contract-authoring/SKILL.md` asks contract authors to
  include a validator path or placeholder and to validate the contract, but it
  does not require a negative fixture or expected-result fixture suite.

This design does not claim that any named consumer repo has been fully audited.
External repo observations are motivation only until a dedicated repo-specific
audit produces evidence.

## Target Outcome

Define a report-only model that can classify test evidence into quality
signals:

- oracle independence;
- mutation and boundary resistance;
- deterministic execution;
- negative and failure-path coverage;
- fixture expected-result discipline;
- mock-only warning;
- legacy characterization baseline;
- contract validator fixture expectations.

The model should let a reviewer say:

- "this repo has tests, but they are mostly weak signal";
- "this contract validator has positive fixtures but no should-fail cases";
- "this legacy refactor has characterization evidence but not behavior proof";
- "this test suite has independent oracles for the critical paths reviewed".

## Scope

In scope for the model:

- report-only scoring or classification vocabulary;
- evidence fields a future tool could collect;
- how to map `TESTING.md` doctrine into machine-readable or reviewer-readable
  findings;
- minimum fixture expectations for domain-contract validators;
- guidance for consuming repos, legacy repos, and contract repos;
- one smallest implementation tranche recommendation.

Out of scope for this design:

- implementation;
- enforcement;
- CI or hook behavior;
- validator rewrites;
- modifying any consumer repo;
- declaring any consumer repo industry-grade;
- declaring test coverage sufficient;
- semantic proof that a test truly protects behavior.

## Proposed Signal Model

### 1. Oracle Independence

Question: Does the test expected value come from an independent source?

Positive evidence:

- spec table, protocol document, or fixed example;
- independently authored fixture;
- explicit invariant;
- captured known-good output with provenance;
- reviewer-provided acceptance criteria.

Warning signals:

- expected value computed by calling production code;
- expected value generated by reimplementing the same production algorithm in
  the test;
- assertion compares a value to itself or to a transformation with no
  independent source;
- test claims behavior proof while the only source is current implementation.

Suggested statuses:

- `independent_oracle_present`
- `characterization_only`
- `production_derived_expected_value`
- `oracle_source_missing`

### 2. Mutation And Boundary Resistance

Question: Would a reasonable defect make the test fail?

Positive evidence:

- tests for `>` versus `>=` boundary flips;
- off-by-one boundaries;
- removed guard clause cases;
- reversed condition cases;
- invalid enum, missing field, malformed input, or forbidden state;
- should-fail fixtures for validators.

Warning signals:

- happy-path-only assertions on critical logic;
- no negative cases for a parser, validator, policy, contract, or claim
  checker;
- no boundary cases around ranges, counts, lengths, status codes, or ordering;
- mutation-sensitive area covered only by smoke tests.

Suggested statuses:

- `mutation_sensitive_cases_present`
- `boundary_cases_present`
- `negative_cases_missing`
- `happy_path_only`

### 3. Determinism

Question: Can the test produce the same result without uncontrolled external
state?

Positive evidence:

- seeded random or deterministic replay;
- fake clock or injected time source;
- in-process fake server or recorded fixture;
- explicit temp path isolation;
- no dependency on test ordering.

Warning signals:

- raw `sleep()` used as synchronization;
- wall-clock assertions without injected clock;
- unseeded randomness;
- live API, hardware, network, or credential dependency without a mock harness;
- reliance on pre-existing local files.

Suggested statuses:

- `deterministic_harness_present`
- `external_dependency_isolated`
- `time_or_random_uncontrolled`
- `live_dependency_without_harness`

### 4. Mock-Only Warning

Question: Does the test verify observable behavior, or only an internal call?

Positive evidence:

- output value, emitted artifact, persisted state, status transition, or
  externally visible side effect is asserted;
- collaborator call assertion is paired with observable behavior.

Warning signals:

- only `assert_called_once` or equivalent;
- no assertion on output, error, state, or artifact;
- mock verifies implementation shape rather than behavior.

Suggested statuses:

- `observable_behavior_asserted`
- `mock_only_weak_signal`

### 5. Legacy Characterization Baseline

Question: For legacy refactors, does the test establish a known-good baseline
before claiming safety?

Positive evidence:

- baseline commit or rollback point identified;
- canonical toolchain and build command named;
- baseline build result and modified build result recorded;
- characterization test captures current known-good behavior before refactor;
- changed behavior is labeled intentionally changed, not silently accepted.

Warning signals:

- refactor claimed safe without baseline build evidence;
- failing baseline hidden by new tests;
- characterization test used as behavior proof without source-of-truth
  statement;
- legacy warnings worsened without disclosure.

Suggested statuses:

- `legacy_baseline_established`
- `characterization_baseline_present`
- `baseline_unverified`
- `characterization_misclaimed_as_behavior_proof`

### 6. Contract Validator Fixture Expectations

Question: Does a domain-contract validator have fixture-backed expected
results?

Minimum expectation for each non-placeholder validator:

- at least one positive fixture that should pass;
- at least one negative fixture that should fail;
- expected result artifact or explicit expected error code;
- fixture path listed in the contract or validator docs;
- focused test that executes the validator against the fixtures;
- claim ceiling distinguishing validator shape from domain truth.

Warning signals:

- validator path exists but has no fixture tests;
- only positive fixtures;
- expected results produced by the validator under test;
- fixture expected output not committed or not reviewable;
- placeholder validator not labeled as placeholder.

Suggested statuses:

- `validator_fixture_pair_present`
- `positive_only_validator_fixture`
- `validator_without_fixture_harness`
- `placeholder_validator_declared`
- `placeholder_validator_unlabeled`

## Output Shape

A future tool or reviewer summary should avoid a single "test quality pass"
boolean. Suggested report shape:

```text
[test_signal_quality]
overall_status = partial | weak | unknown | strong_candidate
oracle_independence = independent_oracle_present | characterization_only | production_derived_expected_value | unknown
mutation_boundary = mutation_sensitive_cases_present | boundary_cases_present | negative_cases_missing | happy_path_only | unknown
determinism = deterministic_harness_present | external_dependency_isolated | time_or_random_uncontrolled | unknown
mock_signal = observable_behavior_asserted | mock_only_weak_signal | unknown
legacy_baseline = legacy_baseline_established | characterization_baseline_present | baseline_unverified | not_applicable | unknown
contract_validator_fixtures = validator_fixture_pair_present | positive_only_validator_fixture | validator_without_fixture_harness | not_applicable | unknown
cannot_claim = [...]
```

Recommended user-facing language:

```text
Test coverage exists, but test-signal quality is report-only. This summary
does not prove the repo is industry-grade. It highlights whether the reviewed
tests use independent oracles, negative cases, deterministic harnesses, and
fixture-backed validator expectations.
```

## Failure Paths And Risk Points

1. False confidence through scoring:
   A numeric score would invite threshold gaming. Prefer explicit status fields
   and cannot-claim boundaries.
2. Static regex overreach:
   Lexical detection can flag `assert_called_once` or `sleep`, but cannot prove
   a test is weak. Early implementation should be report-only with evidence
   refs.
3. Domain mismatch:
   Web scraping, C++ legacy refactor, USB protocol contracts, and kernel driver
   contracts need different evidence mixes. The model must allow
   `not_applicable`.
4. Fixture laundering:
   A fixture can be committed and still encode the wrong expectation. Fixture
   presence is not domain truth.
5. Contract placeholder confusion:
   A placeholder validator is acceptable only when clearly labeled. Unlabeled
   placeholders create false readiness.
6. Consumer-repo drift:
   A consumer repo may improve or regress after an audit. Any report is a
   point-in-time observation.

## Evidence Plan

For the design note itself:

- scope check: only this document changes;
- ASCII / trailing whitespace check;
- `git diff --check`.

For a future implementation tranche:

- unit fixtures with small synthetic repos:
  - production-derived expected value warning;
  - mock-only warning;
  - deterministic fake-clock positive case;
  - sleep / unseeded-random warning;
  - contract validator with positive and negative fixtures;
  - placeholder validator declared versus unlabeled;
  - legacy characterization baseline present versus missing.
- no consumer repo mutation;
- no pass/fail gate;
- output must include cannot-claim text.

## Boundary And API Considerations

The first implementation should not parse arbitrary test semantics. It should
start with explicit, reviewable signals:

- file-level lexical tripwires for high-risk weak patterns;
- contract.yaml validator declarations;
- fixture path conventions;
- optional repo-provided metadata for behavior-source labels;
- reviewer-readable evidence refs.

The model should not become a general test-quality oracle. It is an audit
assistant that makes weak test signals visible.

## Recommended Implementation Tranche

Smallest meaningful next tranche:

```text
DONE = add report-only test-signal quality summary for domain contract repos.
scope = governance_tools/test_signal_quality_audit.py + focused tests only
non-goals = no enforcement, no CI/hook, no consumer edits, no semantic test parser
signals = contract validator fixture pair presence, placeholder validator labeling,
          production-derived expected-value lexical warnings, mock-only lexical warnings
claim ceiling = report-only visibility; does not prove tests are industry-grade
```

Why contract repos first:

- contract validators already have explicit paths in `contract.yaml`;
- fixture expectations are easier to audit than arbitrary application tests;
- positive/negative fixture pairs map directly to `TESTING.md` mutation and
  boundary requirements;
- the result can later feed external onboarding without changing readiness
  gates.

Deferred options:

- consumer application test-suite audit after contract-repo model stabilizes;
- optional metadata file for behavior-source labels;
- integration into `external_repo_readiness.py` as a non-blocking section;
- contract-authoring skill update to require fixture-pair disclosure for each
  non-placeholder validator.

## Claim Ceiling

This design can claim:

- the consumer-repo test-signal quality problem is scoped;
- existing `TESTING.md` doctrine is mapped to report-only audit signals;
- a smallest next implementation tranche is proposed.

This design cannot claim:

- any consumer repo has industry-grade tests;
- any existing tests are good or bad without a dedicated audit;
- the framework enforces test quality;
- validators are correct;
- fixture expected results are domain truth;
- consumer repos are repaired;
- gates, hooks, CI, readiness, or release behavior changed.
