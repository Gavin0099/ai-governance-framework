# C1 Gate 1 client-side identity amendment freeze

This directory freezes the owner-approved client-side invocation identity
boundary for the internal C1 Skill-funding comparison. It does not create a
randomization record or execute any A/B/C/D arm.

The selected runner remains the exact `origin/main` Git object and is not copied
or edited here. `external_preflight_adapter.py` measures the exact CLI,
interpreter, runner, and command contract and injects the existing preflight
schema into that unchanged runner.

Receipts prove only exact client-side invocation continuity. They explicitly
record that the server-executed model was not independently observed and that
provider attestation is unavailable. They must never use `model_observed_id` or
reinterpret the requested `--model` value as runtime observation.

The conclusion template carries the same limitation into every future terminal.
D1-D7 and the attempt-06 quarantine remain unchanged. D5 remains unresolved,
and execution authority remains closed.
