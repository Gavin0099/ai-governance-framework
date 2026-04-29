# Hub Firmware Safety

## HUB-001 - cfu-response-must-follow-request

- CFU response handling must preserve request ordering
- Required evidence: `cfu_state_trace`

## HUB-004 - dptr-guard

- Pointer-sensitive buffer access must include interrupt safety review notes
- Required evidence: `interrupt_safety_review`
