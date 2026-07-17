# Gotchas

- If hooks are not installed yet, readiness can misread the target repo as the framework repo unless an explicit `--framework-root` is provided.
- A repo can fail readiness for only hooks while contract/rule content is otherwise healthy. Do not collapse these into one vague error.
- `PLAN.md` freshness is strict about the header format. Use the repo's real freshness convention instead of inventing a new header.
- Relative repo paths can resolve incorrectly in sandboxed environments. Prefer absolute repo paths for cross-repo onboarding commands.
- `git submodule add <local-path>` writes and stages the local path before any canonicalization. Editing `.gitmodules` afterward is insufficient unless it is explicitly re-staged; otherwise the index can still commit the local URL. Use `offline_submodule_onboarding.py` so the worktree, staged file, parent config, and nested remotes are asserted together.
- Do not leave a local package path as the nested `origin`. Keep `origin` canonical so an accidental standard F-7 apply fails closed while offline, and keep the local path on the separate `offline-bundle` remote.
- The most useful remediation is usually one next command:
  - install hooks
  - fix `PLAN.md`
  - add or fix `contract.yaml`
  - record `governance/framework.lock.json`
