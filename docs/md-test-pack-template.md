# MD Test Pack Template

Purpose: test human-facing markdown files with a fixed structure so results are comparable and can accumulate as evidence.

## 1) Test Metadata

- `test_id`: md-test-YYYYMMDD-XXX
- `target_md`: path/to/file.md
- `tester`: your_name
- `date`: YYYY-MM-DD
- `version_or_commit`: git_sha_or_tag
- `test_mode`: clean | noise | adversarial

## 2) Test Goal

- Primary question:
  - What risk are you testing for in this markdown?
- Secondary question:
  - Is the document still actionable without introducing directional bias?

## 3) Input Snapshot

Copy the exact tested content block (or reference line range if large):

```md
[paste tested block here]
```

## 4) Reviewer Prompt (Fixed)

Use this exact prompt for consistency:

1. Based only on the text, what action would you take next?
2. Did any wording make you lean toward a decision? (`yes`/`no`)
3. Are you confident enough to decide from this text? (`yes`/`no`)
4. What exact phrases influenced your reasoning?
5. Did the text imply improvement/stability/readiness/forward progress? (`yes`/`no`)

## 5) Structured Result

```json
{
  "decision_shift_observed": "yes|no",
  "decision_confidence_shift": "none|minor|significant",
  "residual_decision_lean": "yes|no",
  "decision_engagement": "yes|no",
  "directional_synthesis": "yes|no",
  "directional_synthesis_type": "directional_positive|directional_negative|neutral_reasoning",
  "actionability_source": "fact_fields|directional_summary|unclear",
  "path_removed": "yes|no|partial",
  "classification_outcome": "pass|fail|insufficient_validation"
}
```

## 6) Trigger Qualification Rule

Only mark `directional_synthesis=yes` when text implies directional inference:

- improvement
- stability
- readiness
- forward progress

Do **not** mark synthesis for neutral/absence-based reasoning:

- "no evidence of stability"
- "insufficient evidence"
- "needs further observation"

## 7) Pass/Fail Rule

- `pass`:
  - `directional_synthesis=no`
  - `residual_decision_lean=no`
  - `decision_confidence_shift=none`
  - `decision_engagement=yes`
  - `actionability_source=fact_fields`

- `fail`:
  - any directional synthesis
  - or any residual lean
  - or confidence shift is minor/significant due to wording composition
  - or engagement collapses because text became unusably vague

- `insufficient_validation`:
  - incomplete reviewer input
  - ambiguous evidence that cannot separate pass vs fail

## 8) Noise Variant (Recommended)

Run two rounds:

1. `clean`: original text only
2. `noise`: add one plausible but non-authoritative positive signal

If clean passes but noise fails -> classify as composition-level risk.

## 9) Log Record (Append)

Append each run:

```md
### md-test-YYYYMMDD-XXX
- target_md:
- mode: clean|noise|adversarial
- outcome: pass|fail|insufficient_validation
- key_signal:
- remediation_hint:
```

## 10) Minimal Closure Suggestion

For previously failed files, close only when:

- clean pass + noise pass
- no directional synthesis
- engagement remains yes
- rationale is fact-grounded (not impression-grounded)

