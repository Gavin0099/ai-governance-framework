# Repo-Min Baseline

This baseline is the minimum adoption package used by `governance_tools/adopt_governance.py`.

Included by default:

- `AGENTS.base.md`
- `AGENTS.md`
- `PLAN.md`
- `contract.yaml`
- `.github/workflows/governance-drift.yml`

Adoption behavior:

- `AGENTS.base.md` is always refreshed from the framework baseline
- `AGENTS.md`, `contract.yaml`, `PLAN.md`, and `.github/workflows/governance-drift.yml` are only copied when missing
- existing `contract.yaml` is preserved, but adopt may still add `AGENTS.base.md` to `ai_behavior_override` when that baseline reference is missing
- existing `governance-drift.yml` is preserved and never overwritten
