# E1b Reviewer Summary Contract

## Purpose

Define a strict boundary for human-authored reviewer summaries when the source
material is Phase 3 observation-only artifacts.

This contract prevents socio-semantic smuggling: commentary that looks like
"just a summary" but is later reused as decision authority.

## Scope

- Applies to reviewer notes, PR comments, decision notes, and status summaries
  that reference `phase3_observation` output.
- Applies before Phase 2 metric authority is formally promoted.

## Allowed Summary Scope

- Raw observation restatement
- Coverage gap note
- Schema migration context
- Evidence scope caveat

## Forbidden Summary Claims

- Readiness declared
- Promotion recommended
- Stability conclusion declared
- Interpretation authority substitution
- Directional interpretation without phase transition
- Confidence laundering (hedged wording that still implies forbidden conclusions)

### Forbidden Claims Taxonomy

| Pattern ID | Category | Meaning |
|---|---|---|
| `R1` | `readiness_claim` | Declares readiness from observation-only artifacts |
| `R2` | `promotion_claim` | Recommends or implies promotion from observation-only signals |
| `R3` | `stability_claim` | Declares stability conclusion from observation-only data |
| `R4` | `quality_verdict` | Gives evaluative quality verdict (good/healthy/reassuring) |
| `R5` | `directional_interpretation` | Implies interpretation direction without phase transition |
| `R6` | `confidence_laundering` | Uses hedging to smuggle forbidden conclusion |

## Required Escalation

If interpretation is needed:

1. Create a separate interpretation artifact.
2. Record explicit phase transition and authority basis.
3. Keep observation artifact and interpretation artifact separate.

## Non-Authoritative Rule

Human-authored commentary is non-authoritative by default and must not replace
formal promote decisions.

## Executable Lint Boundary

Use the reviewer-summary linter to enforce this contract:

```powershell
python -m governance_tools.e1b_consumer_audit --input <summary-file.md> --json
```

Exit code semantics:

- `0` = clean
- `2` = non-clean (one or more forbidden claims detected)
