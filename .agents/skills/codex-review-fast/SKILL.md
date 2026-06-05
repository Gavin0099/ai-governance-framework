---
name: codex-review-fast
description: Run a fast, parallel-review mindset before code leaves local development. Use when a non-trivial diff should be reviewed from more than one angle to reduce blind spots and self-confirming optimism.
---

# Codex Review Fast

Use this skill when one review pass is not enough confidence for the change.

## Workflow

1. Treat review as a findings exercise, not a summary exercise.
2. Run two independent review passes with different emphasis when possible:
   - correctness and regressions
   - architecture, risk, and missing evidence
3. Consolidate overlap instead of duplicating the same finding.
4. Preserve disagreements instead of averaging them away.
5. Escalate to `seek-verdict` only when the dispute is real and consequential.

## Review Priorities

- bugs
- behavioral regressions
- architecture drift
- missing or weak evidence
- test gaps
- over-broad scope

## Commands

Read `references/commands.md` for supporting reviewer surfaces.

## Gotchas

Read `references/gotchas.md` before turning a review pass into vague reassurance.

## Output Expectations

- Findings first, ordered by severity.
- Keep summaries brief.
- Distinguish confirmed issues from disputed ones.
- Call out missing tests or missing evidence as first-class findings.