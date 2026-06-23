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
   - only files needed to establish current truth for the requested task
   - do not broaden into adjacent governance systems unless the task directly
     touches them
4. Prefer existing proposal-time tooling over ad hoc speculation.
5. If likely touched files are known and the task touches shared runtime
   behavior, validators, schema, public APIs, or cross-module contracts, use
   architecture-impact preview to estimate:
   - boundary risk
   - validators
   - evidence expectations
6. Write a spec that is small enough to build, review, and verify.
7. Prefer one next implementation tranche. Additional tranches may be listed
   only as deferred options, not commitments.

## Hard Rules

- Do not convert a spec into implementation unless the user explicitly asks.
- Do not claim enforcement, validation, drift closure, architecture improvement,
  or future automation from a proposed spec.
- Do not expand scope to adjacent governance systems without direct repository
  evidence that the requested task touches them.
- Prefer one smallest meaningful tranche over a roadmap.
- If repository truth is unclear, record the uncertainty instead of filling it
  with assumptions.

## Required Sections

- problem
- current repository truth
- target outcome
- scope
- non-goals
- affected surfaces
- boundary and API considerations
- claim ceiling
- failure paths or risk points
- evidence plan
- implementation tranche recommendation

## Claim Ceiling

A tech spec may claim only:

- proposed scope;
- current repository truth observed for the request;
- intended evidence;
- expected affected surfaces;
- recommended next implementation tranche.

A tech spec must not claim:

- behavior is enforced;
- drift is fixed;
- validators pass;
- architecture is improved;
- future automation exists;
- implementation has started.

Only make stronger claims when they are already backed by current repository
evidence, and cite that evidence in the current repository truth section.

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before expanding scope or claiming the spec implies a full implementation commitment.

## Output Expectations

- Start with what problem is being solved.
- Include a current repository truth section that lists concrete files,
  entrypoints, or evidence read. If no evidence exists for a claim, say so.
- Distinguish current pain from proposed scope.
- Keep non-goals explicit.
- Keep claim ceiling explicit.
- Tie evidence planning to repository tools where possible.
- Prefer the smallest implementation tranche that would still be meaningful.
