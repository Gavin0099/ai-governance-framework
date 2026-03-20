# Commands

## Validate contract loading

```bash
python governance_tools/domain_contract_loader.py --contract /path/to/contract.yaml --format human
```

## Check external repo readiness

```bash
python governance_tools/external_repo_readiness.py --repo /path/to/repo --contract /path/to/contract.yaml --framework-root /path/to/ai-governance-framework --format human
```

## Run onboarding smoke against the contract repo

```bash
python governance_tools/external_repo_smoke.py --repo /path/to/repo --contract /path/to/contract.yaml --format human
```

## Replay shared runtime examples against the contract

```bash
python runtime_hooks/smoke_test.py --event-type session_start --contract /path/to/contract.yaml --format human
python runtime_hooks/dispatcher.py --file runtime_hooks/examples/shared/session_start.shared.json --contract /path/to/contract.yaml --format human
```
