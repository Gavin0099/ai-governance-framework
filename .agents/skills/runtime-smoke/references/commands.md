# Commands

## Quickstart smoke

```bash
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
```

## Shared runtime smoke

```bash
python runtime_hooks/smoke_test.py --event-type session_start --contract examples/usb-hub-contract/contract.yaml --format human
```

## Shared dispatcher replay

```bash
python runtime_hooks/dispatcher.py --file runtime_hooks/examples/shared/session_start.shared.json --contract examples/usb-hub-contract/contract.yaml --format human
```

## Shell wrapper smoke

```bash
bash scripts/run-runtime-governance.sh --mode smoke --contract examples/usb-hub-contract/contract.yaml --project-root . --plan-path PLAN.md
```

## External contract repo

```bash
python runtime_hooks/smoke_test.py --event-type session_start --contract /path/to/contract.yaml --format human
python runtime_hooks/dispatcher.py --file runtime_hooks/examples/shared/session_start.shared.json --contract /path/to/contract.yaml --format human
```
