# Control-Plane MVP Spec

As-of: 2026-05-14  
Phase: R2

## Controls

1. Degrade mode
- trigger: risk score above threshold or repeated non-critical failures
- effect: restrict capabilities, require reviewer checkpoints

2. Rollback controller
- supports config rollback + checkpoint restore
- integrates side-effect classes for compensation workflow

3. Cost throttle
- max token budget per task
- max retry count
- over-budget => degrade or fail-closed (policy-driven)

4. Arbitration
- deterministic tie-break for conflicting agent outputs
- tie-break source is fixed per run window

5. Execution freeze
- unknown unsafe state => stop autonomous side effects
- allow only observe/diagnose/export

## Freeze Trigger Contract

Freeze must activate on any:
- authority conflict (role/action mismatch)
- state checksum mismatch on critical path
- uncontrolled retry loop
- repeated unsafe-action attempts
- unresolved determinism divergence

## Test Matrix (minimum)

| control | pass case | fail-closed case |
|---|---|---|
| degrade | threshold breach enters degrade | bypass attempt blocked |
| rollback | checkpoint restore succeeds | restore mismatch triggers freeze |
| throttle | over-budget action blocked | retry storm prevented |
| arbitration | deterministic winner selected | unresolved tie triggers freeze |
| freeze | unsafe state enters freeze | side effect attempt blocked in freeze |
