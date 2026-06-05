# Gotchas

- If hooks are not installed yet, readiness can misread the target repo as the framework repo unless an explicit `--framework-root` is provided.
- A repo can fail readiness for only hooks while contract/rule content is otherwise healthy. Do not collapse these into one vague error.
- `PLAN.md` freshness is strict about the header format. Use the repo's real freshness convention instead of inventing a new header.
- Relative repo paths can resolve incorrectly in sandboxed environments. Prefer absolute repo paths for cross-repo onboarding commands.
- The most useful remediation is usually one next command:
  - install hooks
  - fix `PLAN.md`
  - add or fix `contract.yaml`
  - record `governance/framework.lock.json`
