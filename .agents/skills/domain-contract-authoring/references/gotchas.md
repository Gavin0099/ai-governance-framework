# Gotchas

- Do not start with a broad domain ontology. Start with the smallest slice that has real facts and a clear validator path.
- Keep `contract.yaml` minimal and machine-readable. Put detailed workflow prose in `AGENTS.md` or checklist files.
- Separate rule roots from validators. A repo can have good docs but still fail runtime usefulness if validators or rule roots are missing.
- Prefer one concrete validator over multiple aspirational placeholders.
- If the repo is meant to participate in external onboarding, add `PLAN.md` and `governance/framework.lock.json` early; otherwise readiness will stay noisy.
- Mixed enforcement should be explicit. If a rule is advisory-only, do not imply it blocks by default.
