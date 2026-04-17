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
5. For previously `decision_relevant` escalations, closure requires
   post-remediation evidence that decision pathway is removed.
6. Robustness floor for previously `decision_relevant` escalations:
   one strong independent observation, or two lightweight independent
   observations across different contexts.
7. `ai_adversarial_simulation` evidence is lightweight only and cannot by
   itself satisfy strong closure evidence.
8. For escalations with prior `decision_confidence_shift=significant`, closure
   uses strict profile: post-remediation confidence shift must be `none` and
   human-only review must report no residual decision lean with
   decision_engagement=`yes`.
9. Recommended noise robustness check: validate strict profile once under
   mixed-signal context to ensure pathway removal remains stable outside
   clean-context evaluation.
10. For composition-level cases, strict closure also requires
    `actionability_source=fact_fields` in clean/noise human-only checks.

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

## Controlled Divergence Rule

If a case shares similar `misinterpretation_path` but context differs
meaningfully:

- alternative remediation may be proposed.
- explicit divergence rationale is required.
- mark `controlled_divergence = yes`.

Periodic review:

- if multiple `controlled_divergence` cases converge, update default
  remediation mapping.

## Recurrence Override Consistency Rule

If `recurrence_signal` is triggered:

- re-evaluate classification independent of prior remediation consistency.
- do not use remediation consistency itself as evidence against structural
  classification.

## Composition Guardrail Rule

When outputs combine transition status, confidence-like cues, and positive
metrics:

- list facts without readiness/progress synthesis.
- do not emit cross-field directional conclusion sentences.
- include explicit anti-inference framing that these signals are not readiness
  or promote evidence.

If noise-context observation reintroduces residual lean/minor confidence shift,
treat remediation as composition-level and keep escalation open.

## Expected Outcome

Phase B remains conservative under uncertainty, progresses with explicit
remediation choices, and avoids cross-event policy drift.
