# Commands

## Default local gate

```bash
bash scripts/run-runtime-governance.sh --mode enforce
```

## Smoke-only triage

```bash
bash scripts/run-runtime-governance.sh --mode smoke
```

## Local gate with explicit contract and plan overrides

```bash
bash scripts/run-runtime-governance.sh --mode enforce --contract examples/usb-hub-contract/contract.yaml --project-root . --plan-path PLAN.md
```

## Local gate with extra pytest arguments

```bash
bash scripts/run-runtime-governance.sh --mode enforce --pytest-arg -q
```