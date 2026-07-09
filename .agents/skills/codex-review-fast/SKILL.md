---
name: codex-review-fast
description: Deprecated redirect. Do not use as a standalone review enhancer; use reviewer-handoff for reviewer packets and precommit for commit-boundary validation.
---

# Codex Review Fast

This skill is retained only as a historical redirect after its useful review heuristics were merged into `reviewer-handoff` and `precommit`.

Do not treat this skill as standalone decision-improvement evidence. A single seeded Codex harness produced negative `decision_effect`, and the merge disposition is recorded in the governance surface ledger.

Use:

- `reviewer-handoff` when the task is reviewer-facing status, risk, evidence, or handoff packaging.
- `precommit` when the task is local commit-boundary validation or scoped precommit risk reporting.

## Workflow

1. Stop and route to `reviewer-handoff` or `precommit` based on the task boundary.
2. Preserve the claim boundary: this skill is a deprecated redirect, not proof of review quality.
3. If a user explicitly asks about the historical A/B result, cite the ledger and `result-blind.json` rather than rerunning by default.

## Review Priorities

These priorities now live in the target skills:

- reviewer-facing risks and evidence gaps: `reviewer-handoff`
- gate result, scoped validation, and precommit risks: `precommit`

## Commands

Read `references/commands.md` for redirect targets only.

## Gotchas

Read `references/gotchas.md` before using this historical redirect as if it were still an active standalone skill.

## Output Expectations

- Name the redirect target.
- State that `codex-review-fast` is deprecated as a standalone skill.
- Do not claim broad skill ineffectiveness or broad review improvement from the single seeded harness.
