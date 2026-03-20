# TESTING.md
**Testing Strategy and Quality Gates - v4.1**

> **Version**: 4.1 | **Priority**: 6 (Quality Gatekeeper)
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

`L0` must not be used to dodge required verification.

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
- future reviewers can understand why the change is considered safe
