# Enumd Integration Execution Model Decision (2026-05-11)

Status: active decision  
Owner: framework maintainers  
Applies to: `integrations/enumd/*`

## Decision

Current integration mode is:

`static-governance-and-artifact-ingest`

This means Enumd is integrated through:

- governance contracts and mapping docs
- external observation artifact ingestion

and NOT through direct runtime hook parity with Python session hooks.

## Why This Decision

Enumd runtime environment (Cloudflare Workers / TS service surfaces) is not
execution-compatible with the framework's local Python hook runtime model.
Forcing parity prematurely would blur authority boundaries and introduce
portability claims not yet supported by runtime evidence.

## In-Scope (Now)

1. Schema-aligned artifact ingestion (`ingestor.py`)
2. Non-equivalence boundary enforcement (`enumd_non_equivalence.md`, mapping)
3. Reviewer-visible external observation envelopes

## Out-of-Scope (Now)

1. Direct execution of framework Python hooks inside Enumd runtime
2. Claiming hook-level behavioral equivalence across environments
3. Lifecycle-class contribution from Enumd wave reports

## Upgrade Criteria (Future Runtime-Port Track)

A future `runtime-hooks-port` mode can be proposed only when all are true:

1. Hook semantics are re-implemented in environment-native runtime
2. Cross-environment parity tests exist and pass
3. Authority boundary non-claims remain explicit
4. Portability claim is limited to tested surfaces only

Until then, all portability claims must remain bounded to artifact-level ingest
and mapping semantics.
