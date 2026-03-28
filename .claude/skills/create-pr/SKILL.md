---
name: create-pr
description: Convert a completed change into a reviewer-ready PR handoff. Use when code, risk, and evidence should be packaged into a clear pull-request summary rather than left as raw diff context.
---

# Create PR

Use this skill when implementation is done and the next job is reviewer comprehension.

## Workflow

1. Start from the actual change intent.
2. State what changed and what intentionally did not change.
3. Summarize risk, assumptions, and evidence honestly.
4. Prefer existing reviewer-facing repository surfaces over inventing a new summary layer.
5. Keep the result reviewer-oriented:
   - why this exists
   - what to look at first
   - what evidence exists
   - what remains uncertain

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before turning the PR body into marketing copy or unsupported safety claims.

## Output Expectations

- Start with the change purpose.
- Include scope and non-scope.
- Include risk and evidence.
- If validation is partial, say it is partial.
- Provide one reviewer entrypoint when possible.