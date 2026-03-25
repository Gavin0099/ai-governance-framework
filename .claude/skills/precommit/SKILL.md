---
name: precommit
description: Run the smallest repository-boundary gate needed before commit. Use when local changes should pass runtime governance, smoke, and focused validation before being committed.
---

# Precommit

Use this skill when local work should be gated before commit instead of relying on a later push or review to discover obvious failures.

## Workflow

1. Start with one canonical gate entrypoint.
2. Prefer `scripts/run-runtime-governance.sh --mode enforce` for the default local gate.
3. If the goal is triage rather than full local gate, narrow to smoke mode first.
4. Separate failures into:
   - shell or path problem
   - Python environment problem
   - pytest dependency problem
   - governance smoke failure
   - focused test failure
5. Report blockers concretely and give one next command when handing off.

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before treating a precommit run as full-repository proof.

## Output Expectations

- Start with whether the gate passed.
- Name the exact entrypoint used.
- Distinguish environment failure from governance failure.
- If the gate fails, surface the first blocking failure clearly.
- If extra repo-specific validation is still needed, say so explicitly.