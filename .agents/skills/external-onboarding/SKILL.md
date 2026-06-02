---
name: external-onboarding
description: Onboard an external repository into this AI Governance Framework. Use when Codex needs to install or verify governance hooks, assess external repo readiness, run onboarding smoke, generate onboarding reports, or triage why an external repo is not yet governance-ready.
---

# External Onboarding

Use the existing framework entrypoints instead of reconstructing the workflow by hand.

## Workflow

1. Identify the target repo root and, if needed, the explicit `contract.yaml` path.
2. Prefer `scripts/onboard-external-repo.sh` for full onboarding.
3. Prefer `governance_tools/external_repo_readiness.py` for read-only triage.
4. If the repo still fails readiness, separate failures into:
   - hook installation / framework-root wiring
   - PLAN freshness
   - contract resolution
   - contract file completeness
   - framework version lock state
5. Produce the smallest next command that moves the repo forward.

## Commands

Read `references/commands.md` for the normal command paths.

## Gotchas

Read `references/gotchas.md` before changing the onboarding path or interpreting readiness failures.

## Output Expectations

- Start with the blocking readiness state.
- Distinguish missing hooks from missing contract/PLAN state.
- When the repo is not yet hooked into the framework, prefer passing an explicit framework root.
- Suggest one concrete next command, not a long menu.
