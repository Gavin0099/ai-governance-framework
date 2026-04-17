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
- post_remediation_actionability_source: fact_fields | directional_summary | insufficient_signal | mixed | pending
- post_remediation_free_text_synthesis: yes | no | pending
- post_remediation_free_text_synthesis_trigger:
- post_remediation_noise_check_used: yes | no | pending
- post_remediation_noise_residual_decision_lean: yes | no | pending
- post_remediation_noise_decision_confidence_shift: none | minor | significant | pending
- post_remediation_noise_actionability_source: fact_fields | directional_summary | insufficient_signal | mixed | pending
- post_remediation_noise_free_text_synthesis: yes | no | pending
- post_remediation_noise_free_text_synthesis_trigger:
- composition_guardrail_required: yes | no
- composition_guardrail_status: pending | implemented | verified | failed
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
- remediation_decision: composition-level output guardrail update (presentation composition constraints).
- remediation_scope: consumer outputs that co-present transition status, confidence cues, and positive metrics.
- remediation_rationale: human-only strong observation shows clean context loses decision engagement while mixed-signal context reintroduces directional lean/minor confidence shift; issue is composition-level and cannot be closed by wording tweaks alone.
- controlled_divergence: `no`
- divergence_rationale: n/a
- recurrence_signal: `observed_once`
- potential_structural_pattern: `no`
- emerging_pattern: `no`
- remediation_consistency_review: `not_required`
- post_remediation_evidence_ref: `docs/e1b-post-remediation-adversarial-2026-04-17.json` (lightweight) + `docs/e1b-post-remediation-human-strong-2026-04-17.json` (strong)
- post_remediation_decision_shift_observed: `no` (clean)
- post_remediation_decision_confidence_shift: `none` (clean)
- post_remediation_decision_path_removed: `yes` (clean only)
- post_remediation_path_removal_rationale: clean wording suppresses original direct inference, but noise context reactivates directional interpretation through additional positive signals.
- post_remediation_information_preserved: `no` (clean engagement dropped)
- post_remediation_residual_decision_lean: `no` (clean)
- post_remediation_decision_engagement: `no` (clean)
- post_remediation_actionability_source: `insufficient_signal` (clean)
- post_remediation_free_text_synthesis: `no` (clean)
- post_remediation_free_text_synthesis_trigger: n/a
- post_remediation_noise_check_used: `yes`
- post_remediation_noise_residual_decision_lean: `yes`
- post_remediation_noise_decision_confidence_shift: `minor`
- post_remediation_noise_actionability_source: `directional_summary`
- post_remediation_noise_free_text_synthesis: `yes`
- post_remediation_noise_free_text_synthesis_trigger: "appears improving / looks more stable" style synthesis in reviewer rationale
- composition_guardrail_required: `yes`
- composition_guardrail_status: `in_progress` (redesign spec: docs/esc-20260417-001-composition-redesign.md)
- closure_threshold_profile: `strict_no_minor_after_prior_significant`
- escalation_closed: `no`
- closure_rationale: strict closure failed. Clean context fails actionability (`insufficient_signal`) and decision_engagement, while noise context reintroduces lean/minor shift through directional synthesis. Composition-level guardrail remediation is required before re-test.
- owner: `framework`
- status: `triaged`
- linked_runtime_log: `artifacts/runtime/e1b-phase-b-escalation/phase-b-escalation-log.jsonl`
