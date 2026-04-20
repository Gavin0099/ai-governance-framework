# Enum Adoption Safety Checklist

Purpose: separate engineering-level enum hardening from governance-level authority promotion.

## Core Principle

Engineering enum adoption improves syntax quality and drift resistance.
It does not, by itself, promote semantic authority.

## Safe Now (Engineering Layer)

These are allowed before governance validation closure:

| Item | Allowed Now | Semantic Risk If Misused |
|---|---|---|
| String-to-enum type migration in internal models | Yes | Enum presence may be misread as semantic validation complete |
| Strict parser/validator for enum fields | Yes | Over-strict parser can hide ingestion coverage gaps if errors are not surfaced |
| Explicit `UNKNOWN` / `INVALID` / `UNRECOGNIZED` states | Yes | Teams may later coerce UNKNOWN into a valid decision path |
| Serializer/deserializer consistency tests | Yes | Format consistency may be mistaken for decision correctness |
| Backward-compat mapping table (legacy -> enum) | Yes, but must be explicit and auditable | Silent remap can rewrite evidence meaning |
| Human-facing boundary note (`enum != authority promotion`) | Yes (required) | Omission re-opens authority drift path |

## Mandatory Guardrails (Safe-Now Preconditions)

1. No silent normalization.
2. No fallback-to-valid for unknown/invalid enum values.
3. Legacy-to-enum mapping must be explicit, logged, and reviewable.
4. Unknown/invalid enum values must be reviewer-visible.
5. `UNKNOWN`/`INVALID` values must not directly drive gate/classification/closure decisions.

## Blocked Until Validation (Governance Layer)

These remain blocked until validation conditions are met:

| Item | Blocked Until Validation | Semantic Risk If Misused |
|---|---|---|
| Enum value directly gates verdict decisions | Yes | Syntax closure masquerades as policy authority |
| Enum value directly determines classification outcome | Yes | Evidence interpretation gets silently re-weighted |
| Enum value directly closes escalation | Yes | Closure may occur without human cognition validation |
| Missing enum value auto-defaults to authoritative decision | Yes | Data absence is transformed into false certainty |
| Removal of human validation requirement because enum exists | Yes | Governance guardrail bypass via type-system confidence |

## Validation Conditions Before Any Authority Promotion

All conditions below must hold before enum values can affect authority decisions:

1. Round 3 human-only validation outcome is `pass` (not `fail` / `insufficient_validation`).
2. Existing decision-relevant escalation is closed under strict profile.
3. Phase 2 readiness gate conditions are fully satisfied.
4. Regression tests complete with clean pass (not partial validation).
5. Consumer semantics are aligned across gate/classification/closure/audit readers.

## Consumer Alignment Rule

Consumers must not infer higher authority from enum presence alone.
Enum syntax guarantees are not semantic validation guarantees.
