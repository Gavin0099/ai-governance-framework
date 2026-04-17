# E1b Phase B Escalation Decisions (Versioned)

> This file is the versioned decision trail for escalation outcomes.
> Runtime artifacts can rotate or be ignored by git; this file preserves the
> decision evolution for audit.

## Decision Record Template

```markdown
### <date> - <escalation_id>

- instance_id:
- classification_type: structural_flaw | interpretation_sensitive | false_positive_escalation
- decision_shift_observed: yes | no
- reproducibility: high | medium | low
- is_confirmed_decision_relevant: yes | no
- reviewer_consistency: consistent | mixed
- misinterpretation_path:
- classification_rationale:
- remediation_decision:
- remediation_scope:
- remediation_rationale:
- controlled_divergence: yes | no
- divergence_rationale:
- recurrence_signal: none | observed_once | repeated_independent_contexts
- potential_structural_pattern: yes | no
- emerging_pattern: yes | no
- remediation_consistency_review: required | not_required
- post_remediation_evidence_ref:
- post_remediation_decision_shift_observed: yes | no | pending
- post_remediation_decision_confidence_shift: none | minor | significant | pending
- post_remediation_decision_path_removed: yes | no | pending
- post_remediation_path_removal_rationale:
- post_remediation_information_preserved: yes | no | pending
- post_remediation_residual_decision_lean: yes | no | pending
- post_remediation_decision_engagement: yes | no | pending
- post_remediation_noise_check_used: yes | no | pending
- post_remediation_noise_residual_decision_lean: yes | no | pending
- post_remediation_noise_decision_confidence_shift: none | minor | significant | pending
- closure_threshold_profile: default | strict_no_minor_after_prior_significant
- escalation_closed: yes | no
- closure_rationale:
- owner:
- status: open | triaged | mitigated | accepted-risk
- linked_runtime_log:
```

## Records

### 2026-04-17 - esc-20260417-001

- instance_id: `obs-20260417-002-structured-high`
- classification_type: `interpretation_sensitive`
- decision_shift_observed: `yes`
- reproducibility: `low`
- is_confirmed_decision_relevant: `yes`
- reviewer_consistency: `mixed`
- misinterpretation_path: structured field recombination may create implicit readiness proxy and shift hold->promote interpretation.
- classification_rationale: primary reviewer observed decision-shift risk while backup second opinion remained hold/no-change; non-convergent handling therefore defaults to interpretation_sensitive with low reproducibility.
- remediation_decision: wording clarification.
- remediation_scope: consumer summaries that co-present status/lifecycle/confidence in readiness-like phrasing.
- remediation_rationale: this case does not meet structural_flaw threshold due mixed reviewer signal and low reproducibility, but still requires explicit wording guardrail to prevent implicit readiness inference.
- controlled_divergence: `no`
- divergence_rationale: n/a
- recurrence_signal: `observed_once`
- potential_structural_pattern: `no`
- emerging_pattern: `no`
- remediation_consistency_review: `not_required`
- post_remediation_evidence_ref: `docs/e1b-post-remediation-adversarial-2026-04-17.json` (lightweight; not strong closure evidence)
- post_remediation_decision_shift_observed: `no`
- post_remediation_decision_confidence_shift: `minor`
- post_remediation_decision_path_removed: `yes`
- post_remediation_path_removal_rationale: explicit disclaimer now states confidence is not readiness/promote evidence, removing prior inference path.
- post_remediation_information_preserved: `yes`
- post_remediation_residual_decision_lean: `pending` (human-only strong check not yet run)
- post_remediation_decision_engagement: `pending`
- post_remediation_noise_check_used: `pending`
- post_remediation_noise_residual_decision_lean: `pending`
- post_remediation_noise_decision_confidence_shift: `pending`
- closure_threshold_profile: `strict_no_minor_after_prior_significant`
- escalation_closed: `no`
- closure_rationale: prior state included significant confidence shift; this escalation now uses strict closure profile requiring human-only strong evidence with confidence_shift=none, no residual decision lean, and decision_engagement=yes.
- owner: `framework`
- status: `triaged`
- linked_runtime_log: `artifacts/runtime/e1b-phase-b-escalation/phase-b-escalation-log.jsonl`
