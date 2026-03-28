# Claude Skills Index

This directory contains Claude-facing local skills for the AI Governance Framework repository.

## Available Skills

- `tech-spec`
  - Use when a non-trivial task needs a reviewable technical specification before coding.
  - Covers scope, non-goals, boundary notes, evidence planning, and tranche shaping.

- `precommit`
  - Use when local changes should pass the repository's canonical commit-time gate before commit.
  - Covers shared runtime enforcement, smoke vs enforce mode selection, and blocker triage.

- `codex-review-fast`
  - Use when a non-trivial diff should get a fast findings-first review from more than one angle.
  - Covers parallel review mindset, disagreement surfacing, and evidence-gap reporting.

- `create-pr`
  - Use when implementation is done and the next step is a reviewer-ready pull-request summary.
  - Covers PR framing, scope boundaries, risk/evidence language, and reviewer entrypoints.

- `external-onboarding`
  - Use when onboarding or triaging an external repo against this framework.
  - Covers hook installation, readiness assessment, onboarding smoke, and report generation.

- `reviewer-handoff`
  - Use when building or reading reviewer-facing trust, release, and handoff surfaces.
  - Covers reviewer summaries, snapshot bundles, and publication readers.

- `domain-contract-authoring`
  - Use when creating or refining an external domain contract repo.
  - Covers `contract.yaml`, checklist/docs, rule roots, validators, and minimal repo structure.

- `runtime-smoke`
  - Use when validating runtime governance entrypoints without doing a full release/reviewer flow.
  - Covers `quickstart_smoke.py`, shared runtime smoke, dispatcher replay, and shell wrapper smoke paths.

## Design Notes

- These skills are intentionally narrow and workflow-oriented.
- The tranche-1 workflow skills are meant to compose into `Plan -> Build -> Gate -> Ship`, not replace the existing runtime governance loop.
- `SKILL.md` holds the trigger logic and core workflow.
- `references/` holds commands and gotchas to keep the top-level skill concise.
- `assets/` only exists when a skill benefits from reusable templates.

## Current Bias

- Prefer existing framework tools over ad hoc shell reconstruction.
- Prefer summary-first outputs and one clear next step.
- Keep external onboarding, reviewer handoff, contract authoring, and runtime smoke as separate concerns.
- Keep new workflow skills repo-specific and bounded; do not drift into a generic orchestration platform.
