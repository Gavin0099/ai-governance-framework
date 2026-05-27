# GOVERNANCE_ARTIFACT_FORMAT_RULE

Status: normative contribution rule (formalizing existing practice)
Scope: gate-consumed governance operational state only.

## Rule A — Structured Operational State

Any governance state directly consumed by:
- automated gate evaluation,
- matrix classification, or
- verifier tooling

MUST be stored in structured JSON/YAML artifacts.

Gate-relevant operational state MUST NOT exist only in prose markdown.

## Rule B — Reason Code Usage

Gate-consumed reason fields MUST use codes documented in:
- `docs/governance/reason-code-registry.md`

If a new gate-consumed code is introduced, the same change stream must:
1. add the code to the registry, and
2. record its structured usage location.

No taxonomy/scoring layer is introduced by this rule.

## Rule C — Commentary Separation

Human-readable commentary MAY exist for:
- rationale,
- architecture explanation,
- future direction.

But commentary MUST NOT alter deterministic gate semantics.

Deterministic semantics are defined by structured artifacts/config plus verifier tooling.

## Clarifications

- This rule does not activate retrieval governance.
- This rule does not add schema layers by itself.
- This rule formalizes existing deterministic artifact discipline.

