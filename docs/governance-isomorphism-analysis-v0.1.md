# Governance Isomorphism Analysis v0.1 (Invariant Stress-Test)

- as_of: 2026-05-13
- scope: boundary discovery only
- objective: identify where governance invariants degrade when moving from deterministic AI runtime to human organizational runtime
- claim level: partial structural isomorphism observed

## Positioning

This document does not evaluate "can we govern organizations".
It evaluates "which governance invariants only hold in deterministic runtime".

Boundedness is treated as a feature, not a limitation.

## Method

For each invariant:
1. Compare AI runtime semantics vs organization runtime analog.
2. Assess semantic parity (`full` / `partial` / `weak` / `collapse`).
3. Record first breakpoint and degradation mechanism.
4. Downgrade claims at the first observed break.

## Invariant Stress-Test Matrix

| Invariant | AI Runtime Behavior | Organization Runtime Analog | Semantic Parity | First Breakpoint | Degradation Mechanism | Claim Boundary |
|---|---|---|---|---|---|---|
| authority explicitness | Authority graph is explicit, enumerable, and enforceable by policy/runtime checks. | Authority is often intentionally ambiguous, negotiated, and context-dependent. | partial | Ambiguous authority with unresolved owner of final decision. | Political flexibility and responsibility diffusion reduce formal explicitness. | Do not claim organizational authority determinism. |
| escalation determinism | `if X -> escalate to Y` is codified and replayable. | Escalation path is frequently bypassed by hierarchy exceptions and social capital. | weak | Formal escalation exists but informal shortcut overrides it. | Social dynamics override deterministic flow logic. | Do not claim deterministic escalation outside runtime. |
| evidence legitimacy | Evidence legitimacy is source-defined and machine-checkable. | Evidence legitimacy is contested, negotiated, and role-weighted. | unstable | Same evidence interpreted differently across departments/roles. | Seniority/politics can override evidence hierarchy. | Do not claim universal evidence-legitimacy hierarchy. |
| replayability | Same inputs can be replayed with bounded output variation. | Decisions depend on tacit context (mood, trust, relationship, timing). | low | Stakeholders cannot reconstruct prior decision path consistently. | Tacit social factors are non-canonical and non-replayable. | Do not claim organizational replayability parity. |
| review-surface non-authority | Visibility surface is separated from execution authority by contract. | Visibility itself can alter authority (CC, executive presence, thread dynamics). | collapse-prone | A visibility event changes decision power without explicit policy change. | Observation channel becomes an implicit authority channel. | Do not claim review/execution separation in org runtime by default. |

## Aggregate Reading

- Structural similarity exists at concept level.
- Invariant degradation begins when social dynamics become execution-relevant.
- Organization runtime contains non-deterministic governance properties outside current runtime assumptions.

## What This Supports

- `partial structural isomorphism observed`
- deterministic governance primitives are transferable only within bounded domains
- invariant degradation map is a valid primary output

## What This Does Not Support

- framework can govern organization runtime end-to-end
- machine-authoritative organizational policy claims
- replay-equivalent organization governance claims

## Next Step (Boundary-First)

1. Keep framework bounded; do not expand runtime scope from this result alone.
2. Track invariant breakpoints as first-class artifacts in future cross-domain studies.
3. Treat social-dynamics-induced degradation as boundary evidence, not implementation debt.
