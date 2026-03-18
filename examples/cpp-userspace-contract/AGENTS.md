# C++ User-Space Safety Governance Rules

## Purpose

This contract defines mandatory AI constraints for C++ user-mode applications
(Win32, MFC, COM, Qt, or cross-platform desktop tools).  The three rules
target the most common resource-safety defects found in legacy and modern
user-space C++ codebases.

This is NOT the Kernel-Driver-Contract.  Kernel-specific rules (IRQL, pool
allocation, WDK types) are out of scope here.

## Core Constraints

- The agent must not add or modify mutex usage without using RAII wrappers
  (`std::scoped_lock`, `std::lock_guard`, `std::unique_lock`).  Bare
  `.lock()` / `.unlock()` calls are forbidden.

- The agent must not generate `= new T` or `= new T[n]` allocation patterns.
  Use `std::make_unique<T>()` or `std::make_shared<T>()` instead.

- The agent must not generate `reinterpret_cast<>` at callback or WinAPI
  boundaries without a preceding null-check and explanation of why
  `static_cast` is insufficient.

## No-Assumption Policy

The agent must not assume any of the following without a concrete source:

- Whether an existing mutex acquisition is exception-safe
- Whether raw memory is cleaned up on all exit paths
- Whether a `reinterpret_cast` target has been validated before dereferencing

If a required fact is missing, stop and ask for clarification.

## Validator Failure Policy

- A `CPP_*` rule in advisory mode must be acknowledged in the PR description
  if the agent's changes produce a violation.
- The agent must not claim a violation is benign without a triage record in
  `triage/triage.json`.

## PLAN.md Freshness Policy

- Before starting any task, verify that `PLAN.md` is not stale.
- A stale PLAN.md (> threshold days) is a blocking signal — do not proceed
  with architectural changes until PLAN.md is updated.

## Scope Boundary

- This contract is a pre-merge static pattern checker for C++ user-mode code.
- It does not replace compiler warnings (`/W4`, `/Wall`), static analysis
  tools (clang-tidy, CppCoreCheck), sanitizers (ASAN, TSAN), or code review.
- Passing all checks does not guarantee correct resource management end-to-end.

## Governance Contract Header Format

Every non-trivial AI agent response must begin with:

```
[Governance Contract]
LANG     = C++
PLAN     = <current phase / focus from PLAN.md>
TOUCHES  = <mutex|heap|callback|other>
PRESSURE = <SAFE|WARNING|CRITICAL> (<n>/200)
```

**PRESSURE** is derived from the line count of `memory/MEMORY.md`:
- SAFE: ≤ 150 lines
- WARNING: 151–180 lines (prioritise compaction)
- CRITICAL: > 180 lines (stop new feature work, compact first)

Run `hooks/codex_pre_task.py` at session start to get the current values
for `plan_freshness` and `memory_pressure` automatically.

## Related Documents

- `rules/cpp_safety.md`
- `.github/copilot-instructions.md` (GitHub Copilot adapter)
- `hooks/codex_pre_task.py` (Codex --before-task hook)
