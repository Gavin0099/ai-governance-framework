# Retrieval Authority Round A — Checkpoint Log

Purpose: capture exploratory observation checkpoints without KPI drift.

## Usage Rule
- Qualitative findings first.
- Quantitative distribution second.
- Review triggers are interpretation prompts, not policy thresholds.

---

## Checkpoint Entry Template

```yaml
round: "A"
window: "sessions 01-05"
sample_size: 5
sample_quality: "controlled|mixed|weak"

qualitative_findings:
  - ""
  - ""

observer_effect_signals:
  - ""

distribution:
  used_candidate_rate: 0.00
  used_superseded_rate: 0.00
  authority_conflict_rate: 0.00
  needs_human_review_rate: 0.00
  explicit_candidate_context_rate: 0.00

advisory_volume:
  total_advisories: 0
  advisory_per_session: 0.00

review_triggers:
  - ""

integration_readiness_note: "defer|needs_dedup_first|candidate_for_limited_integration"
```

---

## Entry 01 (sessions 01-05)

```yaml
round: "A"
window: "sessions 01-05"
sample_size: 0
sample_quality: "weak"

qualitative_findings:
  - "pending"

observer_effect_signals:
  - "pending"

distribution:
  used_candidate_rate: 0.00
  used_superseded_rate: 0.00
  authority_conflict_rate: 0.00
  needs_human_review_rate: 0.00
  explicit_candidate_context_rate: 0.00

advisory_volume:
  total_advisories: 0
  advisory_per_session: 0.00

review_triggers:
  - "pending"

integration_readiness_note: "defer"
```

## Entry 02 (sessions 06-10)

```yaml
round: "A"
window: "sessions 06-10"
sample_size: 0
sample_quality: "weak"

qualitative_findings:
  - "pending"

observer_effect_signals:
  - "pending"

distribution:
  used_candidate_rate: 0.00
  used_superseded_rate: 0.00
  authority_conflict_rate: 0.00
  needs_human_review_rate: 0.00
  explicit_candidate_context_rate: 0.00

advisory_volume:
  total_advisories: 0
  advisory_per_session: 0.00

review_triggers:
  - "pending"

integration_readiness_note: "defer"
```

## Entry 03 (optional, sessions 11-15)

```yaml
round: "A"
window: "sessions 11-15"
sample_size: 0
sample_quality: "weak"

qualitative_findings:
  - "pending"

observer_effect_signals:
  - "pending"

distribution:
  used_candidate_rate: 0.00
  used_superseded_rate: 0.00
  authority_conflict_rate: 0.00
  needs_human_review_rate: 0.00
  explicit_candidate_context_rate: 0.00

advisory_volume:
  total_advisories: 0
  advisory_per_session: 0.00

review_triggers:
  - "pending"

integration_readiness_note: "defer"
```

## Entry 04 (optional, sessions 16-20)

```yaml
round: "A"
window: "sessions 16-20"
sample_size: 0
sample_quality: "weak"

qualitative_findings:
  - "pending"

observer_effect_signals:
  - "pending"

distribution:
  used_candidate_rate: 0.00
  used_superseded_rate: 0.00
  authority_conflict_rate: 0.00
  needs_human_review_rate: 0.00
  explicit_candidate_context_rate: 0.00

advisory_volume:
  total_advisories: 0
  advisory_per_session: 0.00

review_triggers:
  - "pending"

integration_readiness_note: "defer"
```
