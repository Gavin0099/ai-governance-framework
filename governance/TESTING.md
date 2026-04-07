---
audience: agent-on-demand
authority: reference
can_override: false
overridden_by: AGENT.md
default_load: on-demand
---

# TESTING.md
**Testing Strategy and Quality Gates - v4.3**

> **Version**: 4.3 | **Priority**: 6 (Quality Gatekeeper)
>
> Defines under what conditions we can reasonably trust a piece of code.
> Tests are guardrails, not KPIs.

---

## 1. Core Philosophy

- protect behavior
- prevent regression
- support safe refactoring
- prefer meaningful evidence over ceremonial checklists

Coverage is not a quality metric by itself.

---

## 2. Test Levels

### L0 - Minimal Confidence

Use only when scope is truly small and rollback is trivial.

Acceptable evidence:
- smoke test
- manual checklist
- characterization check
- visual confirmation for presentation-only work
- before/after screenshot or equivalent lightweight UI evidence when useful

`L0` must not be used to dodge required verification.

For `L0 fast-track` work:
- one lightweight verification step is enough when the task stays presentation-only
- do not require a full regression matrix unless the task upgrades out of `L0`
- if the change starts affecting behavior, schema, async flow, or shared logic,
  upgrade to `L1`

### L1 - Maintainable

Default bar for normal work.

Expected evidence includes the applicable subset of:
- unit tests
- characterization tests
- contract tests
- build verification
- failure-path evidence

Not every task needs every test type, but every task needs enough evidence to defend safety.

### L2 - Critical

Must include strong evidence across:
- behavior
- boundaries
- integration
- regression
- human-reviewable acceptance criteria

---

## 3. Mandatory Failure-Path Thinking

For `L1+`, include evidence for:
- one invalid input or invalid state when applicable
- one boundary value when applicable
- one failure path when applicable

If a category does not apply, say so explicitly.

### 3.1 Critical Function Test Quality

Coverage can be high while test quality remains weak. AI is especially good at
inflating coverage while avoiding the hardest and most decision-relevant paths.

Treat a function as **critical** when any of the following is true:
- it changes state (write, delete, command dispatch, irreversible transition)
- it interacts with external systems (USB, file I/O, network, device API)
- it is a relied-on seam for other modules (public interface, adapter layer,
  shared entrypoint)
- it is a known bug surface or previously regressed function

For critical functions:
- `L1` work must cover the applicable subset of:
  - normal path
  - failure path
  - boundary input
  - invalid input or invalid state
- `L2` work should treat all four categories as the default expectation unless a
  category is explicitly not applicable

If one of these categories is missing, the work is not "fully tested" unless
the omission is named and justified.

Recommended naming pattern:
- `test_[function]_[scenario]_[expected_outcome]`

Preferred examples:
- `test_parse_version_empty_string_returns_none`
- `test_send_command_device_disconnected_raises_error`
- `test_update_firmware_checksum_mismatch_aborts`

Avoid names that hide intent:
- `test_case_1`
- `test_parse_version_2`
- `testSendCommand`

### 3.2 Independent Expected-Value Rule

Expected results must be derived from spec, fixed examples, invariants, or
independent fixtures — not by re-implementing the production algorithm inside
the test.

If a test computes its expected value using the same logic as the code under
test, both will be wrong in the same way and the test provides no independent
verification. This is one of the most common ways AI inflates apparent test
coverage without adding real defensive value.

If an independent expected value cannot be derived, the test must be labeled
explicitly as a characterization test or weak coverage, not treated as a
behavior proof.

Re-implementing production logic in tests is forbidden.

### 3.3 Test Sensitivity and Mutation Thinking

A test that passes under a plausible logic error provides no protection. High
coverage with low sensitivity is worse than low coverage with high sensitivity,
because it creates false confidence.

For critical functions and regression-sensitive paths, tests must be able to
fail under a plausible logic mutation — for example:
- a boundary flip (`>` changed to `>=`)
- a reversed condition
- a removed guard clause
- an off-by-one in a loop bound

For bug fixes: the test added must be able to fail if the original bug is
re-introduced. If no test in the change would catch a regression of the exact
defect being fixed, the fix is not regression-protected.

If test sensitivity cannot be demonstrated, the coverage claim must be
downgraded.

### 3.4 Stateful and Sequence Behavior

Single-point function tests are insufficient for stateful or workflow-driven
code. The most common failures in such systems occur not within a single
function call, but across a sequence of operations.

For stateful or multi-step code, include sequence tests that validate:
- the correct final state after a complete operation sequence
- behavior when a step in the sequence fails midway
- consistency after retry, rollback, or recovery paths

Side-effect obligations by type:
- external write (DB, file, device) → assert the persisted state, not only
  that the write function was called
- shared or global state modification → include explicit cleanup or restoration
  verification
- async dispatch → include evidence of completion behavior and failure-path
  handling; do not treat fire-and-forget as fully tested

---

## 4. Repo-Aware Build Policy

### 4.1 Authoritative Build Config

Each repo should declare at least one **authoritative** or **known-good** build configuration.

Minimum expectation per task:
- verify at least one known-good config

### 4.2 Phase-Based Matrix

Build breadth scales by task risk:

| Task Type | Minimum Build Expectation |
|---|---|
| Low-risk UI / wording / presentation | Known-good config |
| Normal feature / bugfix / refactor | Known-good config plus any touched-path verification needed |
| Critical boundary / release / L2 | Expanded matrix appropriate to the boundary risk |

Do not require a full Debug/Release or platform matrix when the repo's real baseline does not support it.

### 4.3 Warning Policy

Use a **baseline-aware** warning policy:
- do not introduce new warnings in touched files
- do not worsen the declared warning baseline without explicit justification
- existing legacy warnings do not automatically block completion if they are unchanged

---

## 5. Legacy Refactor Baseline Validation

For refactors in legacy repos, required baseline evidence is:
- baseline commit or rollback point build result
- modified state build result
- confirmation of canonical toolchain and canonical build command

If the baseline cannot build, mark the task as operating on an unstable baseline and do not represent it as a clean regression-proof refactor.

---

## 6. Evidence Templates

### 6.1 Minimum Refactor Evidence

Acceptable evidence examples:
- before/after build results
- touched-file diff review
- key call-chain comparison
- characterization or smoke verification of preserved behavior

### 6.2 High-Risk Rule Evidence

For high-risk work, evidence should be concrete and human-reviewable. Examples:

| Rule Type | Acceptable Evidence Examples |
|---|---|
| Flash / sequencing safety | before/after diff, ordered call-path listing, build pass, explicit unchanged sequence note |
| Layer boundary | touched entrypoint list, dependency-path inspection, confirmation no direct forbidden access |
| Thread safety | UI update path list, dispatcher usage confirmation, failure-path note |
| Legacy baseline | canonical toolchain, canonical build command, baseline build, modified build |

Do not claim "verified" without naming the evidence used.

---

## 7. Hard-to-Test Areas

For I/O, native, time, environment, or legacy code:
- isolate what can be isolated
- use characterization where exact unit coverage is unrealistic
- prefer observed behavior over mocked fantasy

Mocking that hides real risk is forbidden.

### 7.1 Assertion and Mocking Discipline

Each test should contain at least one clear assertion about:
- output value
- state change
- emitted error or failure signal

Do not treat "no exception was raised" as the only passing condition unless the
behavior under test is specifically "does not raise", and the test name says so.

Preferred assertion style:
- `assert result == expected_value`
- `assert device.state == DeviceState.DISCONNECTED`
- `assert "checksum mismatch" in error_log`

Mock-only tests are insufficient when they assert only that a collaborator was
called. For example:
- weak: `mock_device.send.assert_called_once()`
- stronger: assert the resulting status, emitted output, or persisted state

Tests must also remain independent:
- each test should be runnable on its own
- setup/teardown must restore the environment
- mutable state must not leak across tests
- device, file, port, or external-resource setup must be explicit per test

### 7.2 Determinism and Flakiness Control

Tests must be deterministic. A test that produces inconsistent results across
runs is not a test — it is noise that erodes trust in the entire suite.

Unless nondeterminism is explicitly the behavior under test, avoid reliance on:
- wall-clock time or `datetime.now()`
- unseeded random values
- execution order between tests
- shared process state or global singletons across test boundaries
- `sleep()` or timing-based synchronization

When the system under test genuinely involves time, randomness, or async
scheduling, control it through injection: fake clocks, seeded random, explicit
harness control, or deterministic event replay.

Claiming stable tests while relying on uncontrolled time, random, or execution
order is forbidden.

### 7.3 Behavior Source and Test Plan Requirement

Tests without a trustworthy source of expected behavior are not tests — they
are guesses dressed as verification.

Before generating tests, identify the source of expected behavior:
- specification or design document
- public contract or interface definition
- bug report with reproducible steps
- acceptance criteria from reviewer or product owner
- existing characterization baseline with known-good output
- explicit reviewer instruction

If no trustworthy source exists, the agent must say so explicitly and
downgrade the confidence label of any tests produced. Deriving expected
behavior solely by reading the existing implementation and assuming it is
correct is not an acceptable source.

For non-trivial work, produce a short test plan before writing test code. The
plan must identify:
- behavior source (what authorizes the expected behavior)
- risk level and task classification
- candidate critical paths and failure paths
- any categories explicitly not applicable, with justification

This sequencing prevents the most common AI failure mode: generating a large
volume of structurally correct but low-value tests before the behavior contract
has been established.

---

## 8. Test Gap Records

When a meaningful test is currently infeasible, record:
- reason
- risk
- remediation condition

No remediation condition means hidden debt.

---

## 9. Definition of Done

Work is done when:
- the chosen evidence matches the task risk
- build verification matches the repo reality
- failure-path thinking has been applied where relevant
- critical functions have meaningful behavior assertions instead of ceremonial
  coverage or mock-only checks
- bug fixes include a regression test in the same change when reproduction is
  practical
- future reviewers can understand why the change is considered safe

The following are explicitly forbidden and do not satisfy any evidence
requirement, regardless of test count or coverage percentage:

- Re-implementing production logic in tests is forbidden.
- Claiming "fully tested" without independent expected-value reasoning is forbidden.
- Declaring regression-safe without a regression test for a reproducible bug is forbidden.
- Claiming stable tests while relying on uncontrolled time, random, or execution order is forbidden.
