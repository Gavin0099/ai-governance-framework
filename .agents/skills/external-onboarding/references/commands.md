# Commands

## Full onboarding

```bash
bash scripts/onboard-external-repo.sh --target /path/to/repo
```

Use `--contract /path/to/contract.yaml` when discovery is ambiguous.

## Offline submodule import

Use this when the consuming repo cannot reach the canonical GitLab server and
the framework and domain-contract repositories were delivered as clean local
Git repositories. Run the command without `--apply` first.

```bash
python governance_tools/offline_submodule_onboarding.py \
  --repo /path/to/consumer \
  --framework-source /path/to/ai-governance-framework \
  --framework-head <framework-commit> \
  --framework-canonical-url <canonical-framework-gitlab-url> \
  --domain-source /path/to/domain-contract \
  --domain-head <domain-contract-commit> \
  --domain-canonical-url <canonical-domain-contract-gitlab-url>
```

Repeat the same command with `--apply` to add and stage the submodules. The
apply path rewrites the local URLs created by `git submodule add`, then
explicitly re-stages `.gitmodules` and the new gitlinks. It fails unless all of
these assertions pass:

1. Worktree `.gitmodules` contains only the requested canonical URLs.
2. Staged `.gitmodules` contains the same canonical URLs, so a commit cannot
   retain the original local package paths.
3. Parent-repo `submodule.<path>.url` values are canonical.
4. Each nested `origin` is canonical and its separate `offline-bundle` remote
   points to the local package repository.

The target repo must have no pre-existing staged files or uncommitted
`.gitmodules` changes. A successful apply leaves only `.gitmodules` and the
requested submodule gitlinks staged; committing them remains a separate
reviewer decision.

## Read-only readiness

```bash
python governance_tools/external_repo_readiness.py --repo /path/to/repo --framework-root /path/to/ai-governance-framework --format human
```

## Read-only smoke

```bash
python governance_tools/external_repo_smoke.py --repo /path/to/repo --contract /path/to/contract.yaml --format human
```

## Version drift

```bash
python governance_tools/external_repo_version_audit.py --repo /path/to/repo1 --repo /path/to/repo2 --format human
```

## Hook validation only

```bash
python governance_tools/hook_install_validator.py --repo /path/to/repo --framework-root /path/to/ai-governance-framework --format human
```
