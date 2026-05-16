# Cross-Agent Closeout Coverage Smoke (2026-05-16)

Status framing: framework exists, installation is partial, and receipt habit is not yet proven.

## Scope

This smoke focuses on operational closeout evidence, not configuration presence.
Primary question: can each agent path produce compliant closeout receipt evidence.

## Evidence Commands

- `./.venv/Scripts/python.exe -m governance_tools.manage_agent_closeout --project-root . --format human verify --agent all`
- `./.venv/Scripts/python.exe -m governance_tools.manage_agent_closeout --project-root . --format human smoke --agent <agent>` for `copilot`, `gemini`, `claude`, `chatgpt-web`, `codex`
- Receipt directory check: `artifacts/runtime/closeout-receipts`

## Pass/Fail Criteria

- `PASS`: hook/command executable and receipt produced
- `PARTIAL`: manual path can produce receipt, but no automatic hook surface
- `FAIL`: cannot install/verify, or smoke does not produce receipt
- `N/A`: platform has no hook surface by design

## Matrix

| Agent | Install Status | Auto Closeout Possible | Verify Result | Receipt Produced (smoke) | Conclusion |
|---|---|---|---|---|---|
| copilot | installed | yes | installed (`session-end.json` found) | no (`receipt_recorded=False`, `compliance_status=NON_COMPLIANT`) | FAIL |
| gemini | installed | yes | installed (`.gemini/settings.json` found) | no (`receipt_recorded=False`, `compliance_status=NON_COMPLIANT`) | FAIL |
| claude | not_installed | yes/partial (Tier A capability, not installed here) | not_installed | no (`receipt_recorded=False`, `compliance_status=NON_COMPLIANT`) | FAIL (gap) |
| chatgpt-web | manual_only | no (known platform limitation) | manual_only | no in smoke (`receipt_recorded=False`) | N/A for auto; manual path exists but not proven in this smoke |
| codex | manual_only/stub | TBD (Tier B, sessionEnd unconfirmed) | manual_only | no in smoke (`receipt_recorded=False`) | FAIL (gap) |

## Key Findings

- `installed != operational`: Copilot/Gemini are installed but failed smoke receipt evidence.
- `verify pass != habitual execution`: verify confirms configuration presence, not runtime closeout behavior.
- `receipt exists != all agents covered`: this run produced no receipt directory and no per-agent receipt evidence.

## Conservative Conclusion

Cross-agent closeout should currently be described as:

`framework exists, partial installation, receipt habit not yet proven`.

It must not be described as "all-agent automation complete".

Operational precision:

`cross-agent closeout is not operationally proven`.

## Invariant

`No receipt -> no operational closeout claim`.

## Next Step

Run targeted root-cause on why smoke exits with `NON_COMPLIANT` before receipt emission,
starting with Copilot and Gemini (already installed, lowest-friction path to first PASS evidence).
