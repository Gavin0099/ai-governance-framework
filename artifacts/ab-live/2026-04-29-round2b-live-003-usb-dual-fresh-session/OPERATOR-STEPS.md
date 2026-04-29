# Operator Steps (Dual Fresh Session Required)

## Group A (Fresh Session A)

1. Start new session A with no prior context.
2. Use repo snapshot `examples/usb-hub-contract` copied to `workspace/group-a`.
3. Apply baseline sanitization.
4. Execute locked prompts Task 1-4.
5. For each task, save:
   - `raw_prompt.txt`
   - `raw_agent_response.md`
   - `actions.log`
   - `files_changed.txt`
   - `tests.log`
   - `validator-output.json`
   - `task-result.json`

## Group B (Fresh Session B)

1. Start separate new session B with no context from A.
2. Use same snapshot hash copied to `workspace/group-b`.
3. Keep governance enabled.
4. Execute the exact same locked prompts Task 1-4.
5. Save the same evidence files per task.

## Parity Finalization

1. Fill `execution-parity.template.json` -> `execution-parity.json`.
2. Fill `CAPTURE-MANIFEST.template.json` -> `capture-manifest.json`.
3. Ensure:
   - `memory_carryover_absent=true`
   - `parity_ok=true`
   - `capture_complete=true`

## Reviewer Handoff

Submit this run root back to reviewer session:

- `artifacts/ab-live/2026-04-29-round2b-live-003-usb-dual-fresh-session/`
