---
name: domain-contract-authoring
description: Create or refine external domain contract repositories for this AI Governance Framework. Use when Codex needs to scaffold or update contract.yaml, AGENTS.md, CHECKLIST.md, rules, validators, fixtures, or minimal onboarding structure for a new or existing domain contract repo.
---

# Domain Contract Authoring

Use this skill when shaping a domain contract repo, not when only consuming one.

## Workflow

1. Start with the narrowest useful domain slice.
2. Create the minimum contract structure:
   - `contract.yaml`
   - `AGENTS.md`
   - one checklist or domain doc
   - one rule root
   - one validator path or placeholder
3. Keep machine-readable facts and human workflow guidance separate.
4. Validate the contract with the framework tools before adding more breadth.

## Templates

- `assets/contract.yaml.template`
- `assets/AGENTS.md.template`
- `assets/CHECKLIST.md.template`

## References

Read `references/commands.md` for the authoring and validation loop.
Read `references/gotchas.md` before broadening the contract scope.
Read `references/response-template.md` when you need the model to explain changes under domain constraints instead of only narrating implementation steps.

## Output Expectations

- Prefer a narrow, runnable vertical slice over a broad abstract contract.
- Explain which files are source-of-truth versus reviewer guidance.
- Call out any placeholder validator or facts file explicitly.
- When evaluating a contract-guided coding response, require four things in the written answer:
  - rule basis
  - untouched safety boundaries
  - concrete verification evidence
  - scope justification
