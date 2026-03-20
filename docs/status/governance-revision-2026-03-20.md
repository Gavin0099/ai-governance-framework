# Governance Revision - 2026-03-20

## Summary

This revision reduces workflow friction for low-risk engineering work while preserving hard safety and architecture boundaries.

The update is motivated by two recurring failure modes:
- governance was too eager to stop adjacent engineering work such as build, test, review, commit preparation, and governance retrospectives
- governance did not explicitly require baseline validation for legacy refactors, rollbacks, and unstable historical commits

---

## What Changed

### 1. Agent Identity and Scope

Core governance now treats the assistant as a **governance-first coding agent**, not a pure reviewer.

`PLAN.md` continues to govern planned feature scope, but bounded adjacent engineering work is now default in-scope unless it crosses a hard boundary.

Examples of adjacent engineering work now treated as normal:
- build
- test
- debugging
- review
- commit preparation
- governance analysis
- documentation sync

### 2. Decision Model

The governance model now distinguishes:
- `Continue`
- `Escalate`
- `Stop`

This replaces the prior tendency to collapse ordinary uncertainty into stop conditions.

The intended interpretation is:
- use `Continue` for bounded low-risk work
- use `Escalate` when ambiguity is real but not yet a hard violation
- use `Stop` only for true red lines, undefendable correctness risk, or hard governance conflicts

### 3. Governance Contract and Memory Cadence

The Governance Contract is no longer required before every small progress update.

It is now required at:
- task start
- milestone completion
- scope change
- stop/escalation events
- other material contract-state changes

Memory updates are also reduced to meaningful checkpoints:
- milestone completion
- known-good build pass that changes task state
- commit preparation
- task close

### 4. Dirty Worktree and Review Hygiene

Governance now explicitly allows unrelated dirty files to remain in the worktree.

Escalation is required only when:
- touched files overlap with unrelated edits
- commit scope cannot be separated cleanly
- review boundaries become unclear

### 5. Low-Risk L1 Examples

The updated rules now explicitly classify common UI/UX polish work as low-risk `L1`, not automatically critical-path work.

Examples:
- UI copy consistency
- status color tokenization
- hint and warning text consistency
- message box severity normalization
- success/wait/failure prompt completion

### 6. Repo-Aware Build and Warning Policy

Testing and build governance now require repo-aware verification:
- each repo should declare at least one authoritative or known-good build configuration
- every non-trivial task should verify at least one known-good config
- warning policy is baseline-aware rather than idealized

Baseline-aware warning policy means:
- do not introduce new warnings in touched files
- do not worsen the declared warning baseline without explicit justification
- unchanged legacy warnings do not automatically block task completion

### 7. Legacy Refactor Baseline Validation

Legacy refactors now require explicit baseline validation.

The rules now require:
- rollback points and refactor baselines must be validated with the authoritative build path before being treated as stable
- canonical toolchain and canonical build command must be identified first
- unverified historical commits must not be described as trusted baselines

Minimum refactor evidence now includes:
- baseline build result
- modified-state build result
- key observable behavior preserved or intentionally documented

This change is specifically intended to prevent mid-refactor discovery that the assumed baseline was not actually buildable.

---

## Files Updated

- `governance/SYSTEM_PROMPT.md`
- `governance/AGENT.md`
- `governance/HUMAN-OVERSIGHT.md`
- `governance/ARCHITECTURE.md`
- `governance/REVIEW_CRITERIA.md`
- `governance/TESTING.md`
- `memory/01_active_task.md`

---

## Intent

The goal of this revision is not to weaken governance.

The goal is to:
- keep hard safety and architecture red lines hard
- reduce unnecessary stop-heavy friction in ordinary engineering flow
- make review and implementation rules better match legacy-repo reality
- require baseline validation before claiming refactor safety
