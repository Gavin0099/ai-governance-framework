---
audience: agent-on-demand
authority: reference
can_override: false
overridden_by: AGENT.md
default_load: on-demand
---

# TESTING.md
**Testing Strategy and Quality Gates - v4.2**

> **Version**: 4.2 | **Priority**: 6 (Quality Gatekeeper)
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
