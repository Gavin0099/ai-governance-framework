---
name: create-pr
description: Deprecated redirect. Use reviewer-handoff for reviewer-ready PR handoff packets; keep create-pr only as a historical workflow alias for pr_handoff terminology.
---

# Create PR

This skill is retained only as a historical redirect for the `pr_handoff` workflow term. Use `reviewer-handoff` for active reviewer-ready packet generation.

Do not maintain a separate PR-summary guidance layer here. The canonical reviewer packet behavior lives in `reviewer-handoff`.

## Workflow

1. Route to `reviewer-handoff`.
2. Preserve `pr_handoff` as the artifact/workflow term when that terminology is needed.
3. Do not invent a parallel PR body, packet, checklist, or playbook.

## Commands

Read `references/commands.md` for redirect targets only.

## Gotchas

Read `references/gotchas.md` before using this historical alias as if it were still an active standalone skill.

## Output Expectations

- Name `reviewer-handoff` as the active target.
- State that `create-pr` is deprecated as standalone guidance.
- Keep scope, evidence, risk, and non-claims in the reviewer packet.
