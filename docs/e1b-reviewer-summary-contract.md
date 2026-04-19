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

## Required Escalation

If interpretation is needed:

1. Create a separate interpretation artifact.
2. Record explicit phase transition and authority basis.
3. Keep observation artifact and interpretation artifact separate.

## Non-Authoritative Rule

Human-authored commentary is non-authoritative by default and must not replace
formal promote decisions.
