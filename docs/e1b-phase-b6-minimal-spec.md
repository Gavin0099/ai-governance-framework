# E1b Phase B.6 Minimal Spec

## Purpose

Define the minimum governance rules that keep Phase B stable across many
escalation events, not only single-event correctness.

## Scope

- classification convergence
- remediation governance
- recurrence awareness
- cross-event remediation consistency

## Core Rules

1. Non-convergent outputs default to `interpretation_sensitive`.
2. `interpretation_sensitive` must choose a remediation path before closure:
   - wording/label clarification
   - consumer guidance update
   - accepted ambiguity with explicit rationale
3. Repeated similar `misinterpretation_path` across independent contexts triggers
   `potential_structural_pattern` re-evaluation.
4. Escalation closure requires stable classification, classification rationale,
   and explicit remediation decision.

## Remediation Consistency Rule

If multiple `interpretation_sensitive` cases share similar
`misinterpretation_path`:

- prefer consistent remediation type across cases.
- deviations must include explicit justification in `remediation_rationale`.

If remediation types diverge without justification:

- flag for policy inconsistency review.

## Emerging Pattern Signal (Non-Binding)

If multiple similar `interpretation_sensitive` cases appear but recurrence
threshold is not yet met:

- mark `emerging_pattern = yes`.
- keep monitoring for recurrence escalation.

This signal does not force structural classification by itself.

## Expected Outcome

Phase B remains conservative under uncertainty, progresses with explicit
remediation choices, and avoids cross-event policy drift.
