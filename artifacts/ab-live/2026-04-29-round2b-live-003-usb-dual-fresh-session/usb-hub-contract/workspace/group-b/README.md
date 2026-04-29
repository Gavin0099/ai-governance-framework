# USB-Hub Contract Example

This example is a minimal dual-repo style domain plugin sample.

It is intentionally small and exists to validate three things:

1. `contract.yaml` discovery works
2. `session_start.py --contract ...` injects domain context
3. `pre_task_check.py --contract ...` can see external rule packs

It also works as the smallest onboarding case for an external project:

1. clone this framework
2. point runtime tools at a contract
3. verify that contract-aware startup and pre-task guidance work without hardcoded paths

## Files

- `contract.yaml`
- `AGENTS.md`
- `USB_HUB_FW_CHECKLIST.md`
- `USB_HUB_ARCHITECTURE.md`
- `rules/hub-firmware/safety.md`
- `validators/interrupt_safety_validator.py`

## Verify

PowerShell:

```powershell
$env:AI_GOVERNANCE_PYTHON='C:\Users\daish\AppData\Local\Python\pythoncore-3.14-64\python.exe'

& $env:AI_GOVERNANCE_PYTHON governance_tools\domain_contract_loader.py `
  --contract examples\usb-hub-contract\contract.yaml `
  --format human

& $env:AI_GOVERNANCE_PYTHON runtime_hooks\core\session_start.py `
  --project-root . `
  --plan PLAN.md `
  --rules common,hub-firmware `
  --risk medium `
  --oversight review-required `
  --memory-mode candidate `
  --task-text "Validate USB hub firmware response flow" `
  --contract examples\usb-hub-contract\contract.yaml `
  --format human

& $env:AI_GOVERNANCE_PYTHON runtime_hooks\core\pre_task_check.py `
  --project-root . `
  --rules common,hub-firmware `
  --risk medium `
  --oversight review-required `
  --memory-mode candidate `
  --task-text "Validate USB hub firmware response flow" `
  --contract examples\usb-hub-contract\contract.yaml `
  --format json

& $env:AI_GOVERNANCE_PYTHON governance_tools\external_repo_smoke.py `
  --repo examples\usb-hub-contract `
  --contract examples\usb-hub-contract\contract.yaml `
  --format human
```

## Expected Signals

Minimal success indicators:

- `domain_contract_loader.py` shows `name=usb-hub-firmware-contract`
- `session_start.py` shows domain contract context and proposal guidance
- `pre_task_check.py` accepts `common,hub-firmware`
- `external_repo_smoke.py` prints a shared `summary=` line with:
  - `ok=True`
  - `rules=common,hub-firmware`
  - `pre_task_ok=True`
  - `session_start_ok=True`

This is the intended onboarding threshold:

- no hardcoded firmware path checks
- contract-aware runtime entry works
- external rule root is discoverable
