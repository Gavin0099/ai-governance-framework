# Commands

## Full onboarding

```bash
bash scripts/onboard-external-repo.sh --target /path/to/repo
```

Use `--contract /path/to/contract.yaml` when discovery is ambiguous.

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
