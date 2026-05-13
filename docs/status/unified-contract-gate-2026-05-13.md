# Unified Contract Gate (2026-05-13)

## Purpose

Force all agent lanes (Copilot / Claude / Codex) through the same
`[Governance Contract]` validation path, instead of relying on model habit.

## Added Script

- `scripts/run_with_contract_gate.ps1`

Behavior:

1. Run the provided command (optional skip mode for already-generated output).
2. Validate `ResponseFile` with `governance_tools/contract_validator.py`.
3. Fail closed if contract block is missing or non-compliant.

## Why This Fix

Previous enforcement existed in adapter paths only.  
If a lane bypassed adapter `post_task`, contract output became non-mandatory.

This script gives a shared gate for all lanes.

## Minimal Usage

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_contract_gate.ps1 `
  -RunCommand "<your-agent-run-command>" `
  -ResponseFile "<path-to-agent-response.txt>"
```

Skip re-running command and validate an existing response file:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_with_contract_gate.ps1 `
  -RunCommand "Write-Output noop" `
  -ResponseFile "<path-to-agent-response.txt>" `
  -SkipRunCommand
```

## Boundary

- This enforces contract presence/compliance.
- It does not auto-generate model responses.
- Any lane not routed through this script (or adapter `post_task`) is still ungated.

