---
name: tech-spec
description: Turn a non-trivial repository task into a reviewable technical specification. Use when scope, non-goals, boundaries, evidence, or implementation tranches need to be made explicit before coding.
---

# Tech Spec

Use this skill when the task should not jump directly from idea to implementation.

## Workflow

1. State the actual problem, not only the requested change.
2. Separate in-scope work from explicit non-goals.
3. Read current repository truth first:
   - `PLAN.md`
   - relevant governance docs
   - relevant runtime or tool entrypoints
4. Prefer existing proposal-time tooling over ad hoc speculation.
5. If likely touched files are known, use architecture-impact preview to estimate:
   - boundary risk
   - validators
   - evidence expectations
6. Write a spec that is small enough to build, review, and verify.

## Required Sections

- problem
- target outcome
- scope
- non-goals
- affected surfaces
- boundary and API considerations
- failure paths or risk points
- evidence plan
- implementation tranche recommendation

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before expanding scope or claiming the spec implies a full implementation commitment.

## Output Expectations

- Start with what problem is being solved.
- Distinguish current pain from proposed scope.
- Keep non-goals explicit.
- Tie evidence planning to repository tools where possible.
- Prefer the smallest implementation tranche that would still be meaningful.