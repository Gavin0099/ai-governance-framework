# E1b Phase B Observation Log Template

> Use this template to record falsification-oriented evidence instances for
> Phase B. One entry = one observed escape instance.
>
> Canonical interpretation source:
> [docs/e1b-consumer-audit-checklist.md](e1b-consumer-audit-checklist.md)

## Usage Rules

- Record only observed instances (do not backfill inferred history).
- Prioritize HIGH-risk escapes first.
- Keep one entry per instance; do not aggregate before logging.
- If `impact_scope=decision_relevant`, escalate immediately.
- `decision_confidence_shift` is required even when `impact_scope=none`.
- `self_challenge_note` is required for every instance.

## Entry Format (Markdown)

```markdown
### Observation <id>

- observed_at_utc: <YYYY-MM-DDTHH:MM:SSZ>
- observer: <name/role>
- source_type: session_note | memory_update | phase_c_draft_candidate
- source_ref: <path or artifact reference>
- consumer_surface: <script/doc/output name>
- escape_class: E1 | E2 | E3 | E4
- escape_risk_tier: HIGH | MEDIUM | LOW
- escape_phrase_or_pattern: "<exact phrase or structured pattern>"

- q1_escape_present: yes | no
- q2_human_misinterpretation_likely: yes | no
- q3_affects_decision_outcome: yes | no

- impact_scope: none | interpretive_only | decision_relevant
- decision_confidence_shift: none | minor | significant

- context:
  - repo_name: <repo>
  - repo_type: tool | app | infra | experiment
  - session_type: bugfix | feature | analysis
  - reviewer_mode: AI-assisted | human-only

- interpretation_note: >
    <why this instance was labeled with current impact_scope and confidence_shift>

- self_challenge_note: >
    <if this were misinterpreted, what would go wrong?>

- decision_trace:
  - decision_target: <promote/block/readiness/phase-c-framing>
  - observed_effect: <none or specific shift>

- escalation:
  - required: yes | no
  - reason: <if required=yes>
  - human_review_ref: <ticket/note/link or n/a>
```

## Minimal Starter Batch (First Run)

For initial operational start, collect at least:

- 1 HIGH-risk narrative instance that creates plausible "promote/readiness"
  pull for a reviewer.
- 1 HIGH-risk structured-combination instance where single fields are legal but
  combined semantics can distort downstream interpretation.

Expected first-batch signal quality:
- At least one instance should be `impact_scope != none`.
- At least one instance should be `decision_confidence_shift != none`.
- If both first instances are fully `none`, treat sample quality as suspect and
  re-sample with more adversarial cases.

Do not summarize distribution yet. Keep case-by-case records.
