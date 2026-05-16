# Closeout Governance Admissibility Layering Contract (2026-05-16)

Status: draft-v1 (admissibility contract, not verifier enforcement contract)

## Purpose

Prevent claim inflation across closeout governance layers.

Core rule:

`artifact existence does not authorize cross-layer claim escalation`.

This contract defines which claim class is admissible at each layer.

## Layering Table

| Layer | Question | Allowed Claim | Forbidden Claim |
|---|---|---|---|
| Existence | closeout artifact exists? | closeout attempted / closeout event recorded | governance completed |
| Eligibility | memory obligation activated? | memory review required | memory update valid |
| Compliance | required action performed? | required artifact present | semantic adequacy |
| Semantics | reasoning meaningful? | reasoning reviewed | governance effective |

## Negative Admissibility Rules (Fail-Closed)

| Condition | Result |
|---|---|
| receipt missing | operational claim prohibited |
| eligibility unknown | compliance claim degraded |
| compliance absent | semantic claim inadmissible |
| semantic evidence absent | governance effectiveness claim prohibited |

## Claim-Scope Invariants

1. `receipt-backed != governance-proven`
2. `existence -> eligibility -> compliance -> semantics` is one-way; no backward promotion
3. Evidence type X may authorize only claim class Y defined by this layer
4. No cross-layer shortcut from artifact presence to semantic/effectiveness claim

## Machine-Check Boundary (v1)

Machine-checkable now:
- receipt existence
- artifact presence
- closeout lineage continuity
- eligibility confidence tier

Not machine-checkable now:
- semantic adequacy
- durable lesson value
- architecture significance judgment

## Admissibility Position

Current closeout governance should be framed as:
- framework exists
- partial installation exists
- receipt habit not yet proven
- auto closeout coverage not established

Therefore:
- operational closeout claim is not established across agents
- semantic/effectiveness claims are out of admissible scope

## Anti-Ritual Guard

Operational artifact presence must not be treated as reasoning sufficiency.

`receipt exists` may only support:
- closeout event recorded

`receipt exists` must not support:
- governance reasoning adequate
- governance process effective

## Compositional Integrity Guard

Layer-local correctness does not guarantee system-level epistemic integrity.

Hard rule:

`all layers pass != governance adequate`.

Compositional admissibility table:

| Condition | Maximum admissible claim |
|---|---|
| all layer artifacts present | procedural compliance observed |
| semantic review present without causal chain evidence | semantic activity observed |
| causal reconstruction absent | governance adequacy prohibited |
| cross-layer causal chain missing | system-level integrity unestablished |

Cross-layer shortcut prohibition:
- No claim may jump from multi-layer artifact presence to governance adequacy.
- End-to-end causal coherence must be evidenced explicitly, not socially assumed.

## Layered Ritualization Signals

These signals indicate compositional hollowing risk even when layer-local checks pass.

| Signal | Risk |
|---|---|
| repeated receipt + no causal note | procedural hollowing |
| review acknowledgment without reconstruction | semantic compression |
| status-only verification | causal disappearance |
| repeated \"looks good\" approvals | review ritualization |

Interpretation rule:
- Ritualization signals are observation-level warnings.
- They must not be converted into adequacy/effectiveness claims without independent causal-chain evidence.

## Ritualization Asymmetry (Layer-Specific Risk)

Ritualization pressure is not uniform across layers.

| Layer | Ritualization risk | Typical hollowing mode |
|---|---|---|
| Existence | very high | boilerplate receipt presence treated as trust signal |
| Compliance | high | checklist/green-status substitution for causal validation |
| Eligibility | medium | noisy obligation activation treated as meaningful governance work |
| Semantics | surface-low, latent-high | fluent narrative mimicry without causal reconstruction |

Layer-specific resistance principle:
- Controls must be tuned per layer; one generic anti-ritual control is insufficient.

## System-Level Claim Ceiling

Without cross-layer causal chain evidence, the highest admissible system-level claim is:

`procedural compliance observed`.

Therefore, the following claims remain prohibited until composition evidence exists:
- governance effective
- governance reasoning adequate
- system epistemic integrity established

## Claim Ceiling Preservation Discipline

Ceiling drift guard:

`repeated procedural compliance observed != emergent governance adequacy`.

Prohibition:
- Repetition count, time-in-green, or artifact accumulation must not promote claim ceiling by itself.

Promotion requirement:
- Any claim above `procedural compliance observed` requires explicit cross-layer causal-chain evidence with traceable reconstruction, not summary-level inference.

## Governance Survivorship Bias Guard

Core rule:

`surviving evidence != complete evidence`.

Archival cleanliness must not be interpreted as governance stability without negative-evidence visibility.

Hard rule:

`clean history != complete history`.

### Negative Evidence Admissibility

| Evidence state | Claim impact |
|---|---|
| failed closeout retained | integrity ceiling unchanged |
| failed closeout missing | integrity ceiling degraded |
| reconstruction abandoned but lineage-visible | survivorship bias bounded |
| reconstruction disappearance unexplained | historical integrity unestablished |

Interpretation:
- Missing failure evidence is itself governance-relevant evidence.
- Unexplained disappearance of degraded/incomplete states is an admissibility downgrade event.

### Lineage Visibility Scope (v1)

Retention-hardening applies to governance-relevant incompleteness only.

| Incompleteness type | Lineage-visible requirement |
|---|---|
| failed closeout | yes |
| degraded admissibility | yes |
| incomplete eligibility evaluation | yes |
| abandoned semantic draft | usually no |
| exploratory brainstorming | no |

Boundary:
- This section is not a universal reasoning-retention policy.
- Scope is limited to survivorship-bias control for governance admissibility.

## Negative Evidence Consumption Guard

Core rule:

`negative evidence retained != negative evidence consumed`.

Retention alone may support transparency claims, but cannot support adequacy/maturity claims.

### Consumption Admissibility States

| State | Maximum admissible claim |
|---|---|
| retained but unconsumed | transparency observed |
| retained + downgrade applied | bounded integrity discipline observed |
| retained + downgrade bypassed | governance adequacy prohibited |
| missing consumption lineage | claim ceiling capped |

Consumption consequence rule:
- If negative evidence does not produce an operational downgrade consequence, claim ceiling must not increase.
- No downstream adequacy/effectiveness claim is admissible when downgrade lineage is missing or bypassed.

Anti-tokenization rule:
- Visible adversity must not be laundered into trustworthiness.
- `failure/degraded/incomplete artifacts present` is not maturity evidence by itself.

Symbolic downgrade warning:
- `downgrade_applied=true` is insufficient without effect visibility.
- Recorded downgrade must show at least one concrete effect surface (for example: claim prohibition, coverage capping, reviewer-path block, or assertion-level downgrade).

## Next Step

Use this contract as claim-boundary input for:
- contamination mode-gate enforcer (`enforce_output_mode`)
- receipt-path stabilization work (Copilot/Gemini first)

Do not freeze full verifier policy until receipt lineage and eligibility inference are stable.
