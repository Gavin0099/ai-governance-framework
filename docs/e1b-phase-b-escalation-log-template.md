# E1b Phase B Escalation Log Template

> Purpose: Track the audit chain from falsifying instance to remediation closure.
> This log is mandatory once any `decision_relevant` instance is observed.

## Trigger

- Any observation instance with `impact_scope=decision_relevant`.

## Required Fields

```json
{
  "escalation_id": "esc-YYYYMMDD-001",
  "instance_id": "obs-...",
  "escape_class": "E1|E2|E3|E4",
  "risk_tier": "HIGH|MEDIUM|LOW",
  "impact_scope": "decision_relevant",
  "decision_confidence_shift": "none|minor|significant",
  "affected_surface": "narrative-summary|structured-output-summary|...",
  "misinterpretation_path": "how this instance could shift downstream decision",
  "decision_shift_observed": "yes|no|pending_human_confirmation",
  "reproducibility": "high|medium|low|pending_human_confirmation",
  "backup_second_opinion": {
    "would_change_decision": "yes|no|not_sure",
    "pushed_conclusion": "promote|hold|block|unclear"
  },
  "reviewer_consistency": "consistent|mixed|pending_second_opinion",
  "reviewer_assessment": "triage notes from reviewer(s)",
  "is_confirmed_decision_relevant": "yes|no|pending_human_confirmation",
  "classification_type": "structural_flaw|interpretation_sensitive|false_positive_escalation|pending_classification",
  "recommended_remediation": "wording|audit_rule|schema_or_surface_redesign|combined",
  "remediation_scope": "specific components/files/surfaces affected",
  "controlled_divergence": "yes|no",
  "divergence_rationale": "required when controlled_divergence=yes",
  "emerging_pattern": "yes|no",
  "remediation_consistency_review": "required|not_required",
  "status": "open|triaged|mitigated|accepted-risk",
  "opened_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "last_updated_utc": "YYYY-MM-DDTHH:MM:SSZ"
}
```

## State Semantics

- `open`: detected but not yet triaged.
- `triaged`: misinterpretation path and remediation direction documented.
- `mitigated`: remediation implemented and verified.
- `accepted-risk`: risk accepted with explicit rationale and boundary.

## Classification Mapping

- `structural_flaw`: decision shift observed and reproducibility is high; usually
  requires schema/surface redesign.
- `interpretation_sensitive`: reviewers are mixed or reproducibility is low;
  usually addressed by wording/disclaimer/guidance plus targeted audit rule.
- `false_positive_escalation`: no stable decision shift and reviewers agree it
  does not materially affect decision.

## Classification Convergence Rule

`classification_type` is considered stable when:

- `decision_shift_observed` is consistent across reviewers.
- `misinterpretation_path` shows similar reasoning structure.
- `reproducibility` is not `low`.

Otherwise:

- classify as `interpretation_sensitive` and continue scoped observation until
  convergence.

## Non-Convergent Handling Rule

If reviewer outputs do not converge:

- default `classification_type = interpretation_sensitive`.
- mark `reproducibility = low` unless independently verified.
- require at least one additional independent observation OR one more human
  confirmation before escalation closure.

## Branch Decision Criteria (Strict)

### `structural_flaw`

All conditions must hold:

- `decision_shift_observed = yes` across at least two views.
- `reviewer_consistency = consistent`.
- `misinterpretation_path` is structurally similar across reviewers.
- `reproducibility != low`.

### `interpretation_sensitive` (default fallback)

Any condition below is sufficient:

- reviewer outputs are mixed.
- reasoning structure is not similar.
- `reproducibility = low`.
- backup second opinion conflicts with primary reviewer direction.

### `false_positive_escalation`

All conditions must hold:

- all reviewers report `decision_shift_observed = no`.
- reasoning is consistent (not due to misunderstanding).

## Escalation Closure Rule

An escalation can be closed only when:

- `classification_type` is stable under convergence rules.
- `classification_rationale` is documented.
- remediation decision is explicitly chosen (including `no change`).

## Post-Remediation Verification Rule

If an escalation previously reached `decision_relevant`:

Closure additionally requires all of:

- minimal robustness requirement:
  - one strong independent observation (`human-only`, no prior context), OR
  - two lightweight independent observations across different contexts.
- `decision_shift_observed = no` in post-remediation check.
- `decision_confidence_shift` is not `significant`.
- `misinterpretation_path` no longer leads to decision inference.
- reviewer can explicitly explain what wording/structure change removed the
  previous inference path.
- information preservation check passes (output still provides sufficient signal
  for decision-making).
- reviewer reports no residual decision lean from the output wording/structure.

Severity-aware tightening:

- if prior state included `decision_confidence_shift = significant`, closure
  requires `post_remediation_decision_confidence_shift = none` (minor is not
  sufficient for closure).

Borderline handling:

- if first observation is borderline (e.g., `decision_confidence_shift=minor`
  with hesitation or unclear rationale), require second confirmation before
  closure.

If verification fails:

- if decision shift reappears: upgrade to `potential_structural_pattern`.
- if decision shift does not reappear but misinterpretation path persists:
  remain `interpretation_sensitive` and strengthen remediation.

## Remediation Decision Rule (Interpretation-Sensitive)

If `classification_type = interpretation_sensitive`:

- do not escalate directly to structural remediation.
- do not close as false positive by convenience.
- choose exactly one remediation path:
  - `(a)` wording/label clarification
  - `(b)` consumer guidance update
  - `(c)` accepted ambiguity (with explicit rationale)

Closure is allowed only when:

- ambiguity boundary is documented.
- decision impact is assessed as non-critical.

## Recurrence Signal Rule

If similar `misinterpretation_path` appears in multiple independent contexts:

- upgrade from `interpretation_sensitive` to `potential_structural_pattern`.
- require re-evaluation of `classification_type` and remediation scope.

Independent contexts must differ in at least one of:
- repo type
- session type
- reviewer mode

## Remediation Consistency Rule

If multiple `interpretation_sensitive` cases share similar
`misinterpretation_path`:

- prefer consistent remediation type across cases.
- deviations must include explicit justification in `remediation_rationale`.

If remediation types diverge without justification:

- set `remediation_consistency_review = required`.

## Emerging Pattern Signal (Non-Binding)

If multiple similar `interpretation_sensitive` cases appear but recurrence
threshold is not yet met:

- set `emerging_pattern = yes`.
- continue monitoring for recurrence escalation.

## Controlled Divergence Rule

If a case shares similar `misinterpretation_path` but context differs
meaningfully:

- alternative remediation may be proposed.
- set `controlled_divergence = yes`.
- `divergence_rationale` is mandatory.

If multiple controlled-divergence cases converge:

- update default remediation mapping.

## Recurrence Override Consistency Rule

If `recurrence_signal` is triggered:

- re-evaluate classification independent of prior remediation consistency.
- do not treat remediation consistency as evidence against structural
  classification.
