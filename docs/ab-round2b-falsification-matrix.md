# A/B Round 2B Multi-Axis Falsification Matrix

## Purpose

Avoid single-verdict distortion by evaluating governance as multiple falsifiable axes.

## Reviewer Rule

Do not start with an overall result.

First line must be:

- `weakest_supported_axis: ...`

Then report per-axis status.

## Axis Matrix

Use this exact shape:

```json
{
  "run_id": "string",
  "weakest_supported_axis": "behavior_delta|authority_enforcement|reviewer_surface|decision_quality|claim_discipline",
  "axes": {
    "behavior_delta": "supported|weak|absent",
    "authority_enforcement": "supported|bypassed|unclear",
    "reviewer_surface": "strong|partial|missing",
    "decision_quality": "improved|neutral|degraded",
    "claim_discipline": "consistent|inconsistent"
  },
  "overall_posture": "bounded_support|partial_falsification|major_falsification",
  "falsification_evidence": [],
  "claim_boundary": "string"
}
```

## Anti-Selective-Victory Rule

Single-axis success cannot be used as overall governance success.

Examples of forbidden inference:

- `authority_enforcement=supported` => `overall governance successful`

If any axis is `absent`, `bypassed`, `missing`, `degraded`, or `inconsistent`,
reviewer must explicitly explain why overall posture is not upgraded.

## Overall Posture Guidance

- `bounded_support`:
  - no major falsification axis triggered
  - weakest axis still at least partially supported

- `partial_falsification`:
  - one or more axes falsified, but not collapse-level

- `major_falsification`:
  - falsification in trust-critical axis (authority/reviewer surface/claim discipline)
  - or multiple axes degraded simultaneously
