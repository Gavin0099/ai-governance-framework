# Reviewer Semantic Hotspot Surface Spec (v0.1)

As-of: 2026-05-15  
Mode: observation-only  
Goal: improve reviewer attention allocation for semantic-risk regions.

## Why

Authority/runtime checks can pass while semantic reasoning still drifts.  
This surface exposes likely semantic risk hotspots without claiming semantic truth verification.

## Inputs

- Semantic failure observations (from taxonomy `SF-01..SF-07`)
- Invariant registry matches (`governance/INVARIANT_REGISTRY.yaml`)
- Evidence-output linkage traces (when available)
- Existing runtime authority artifacts (for context only)

## Output

Generate a reviewer section (or artifact) with:

1. `hotspot_id`
2. `risk_rank` (`high|medium|low`)
3. `failure_class` (`SF-*`)
4. `invariant_id`
5. `evidence_refs`
6. `decision_refs`
7. `ambiguity_zone` (short plain text)
8. `recommended_review_action`

Example:

```json
{
  "hotspot_id": "hs-20260515-001",
  "risk_rank": "high",
  "failure_class": "SF-05",
  "invariant_id": "evidence_output_alignment",
  "evidence_refs": ["artifact://datasheet/page-12#reg-x"],
  "decision_refs": ["artifact://patch/hunk-3"],
  "ambiguity_zone": "evidence cites reg-x mask 0x03, patch applies 0x07",
  "recommended_review_action": "verify semantic mapping before merge"
}
```

## Ranking Heuristic (v0.1)

- `high`: S3 class or multiple invariant hits in one decision path
- `medium`: S2 class with clear evidence mismatch/authority reinterpretation signal
- `low`: isolated ambiguity without invariant breach signal

## Reviewer Workflow Integration

Add a "Semantic Hotspots" section in reviewer handoff outputs:

- show top 3 `high` first
- collapse `low` by default
- require reviewer disposition for each `high` hotspot:
  - `confirmed_risk`
  - `false_positive`
  - `needs_more_evidence`

## Guardrails

- This surface is advisory, not authority-granting.
- No auto-block solely from semantic hotspot score.
- Any enforcement escalation must be explicit and separately governed.

## Non-Goals

- No global semantic score
- No universal reasoning validator
- No use of model self-explanations as authoritative proof
