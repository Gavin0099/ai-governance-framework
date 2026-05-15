# AB Causal r40 Reasoning-Separation Test Spec (2026-05-15)

Objective: test whether uplift remains when style/reviewer-facing surface cues are controlled.

## Hypothesis

- H0: observed uplift is primarily style/evaluator-manifold adaptation.
- H1: observed uplift survives style suppression, indicating deeper reasoning contribution.

## Design

- Arms:
  - `r40-arm-1-baseline-strict`
  - `r40-arm-2-style-suppressed`
- Single-variable rule:
  - only manipulate post-output style marker surface (`style_marker_presence_post`)
  - no threshold relaxation, no mixed variable changes

## Blinding Contract

- evaluator does not see:
  - governance arm label
  - style-control injection flags
- normalized output format required before scoring

## Fixed Execution

- seeds: `350101`, `350102`, `350103`
- `max_retry=3`
- checkpoint: `ab-causal-r40-reasoning-separation-checkpoint-2026-05-15.json`

## Required Per-Case Fields

- `pass|fail`
- `unsupported`
- `style_marker_presence_pre`
- `style_marker_presence_post`
- `injected_controls`
- `attempts_used`

## Decision

- apply unchanged strict gate
- interpretation rule:
  - if style-suppressed arm collapses while baseline survives in same run context, evidence favors behavioral conditioning over reasoning uplift
  - if both survive with strict pass, evidence supports reasoning-linked contribution

