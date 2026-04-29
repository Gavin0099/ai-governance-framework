# A/B Round 2B Multi-Axis Falsification Matrix

## Purpose

Avoid single-verdict distortion by evaluating governance as multiple falsifiable axes.

## Reviewer Rule

Do not start with an overall result.

First line must be:

- `weakest_supported_axis: ...`

Then report per-axis status.

Also report the single most direct contradiction against core governance claims.

## Axis Matrix

Use this exact shape:

```json
{
  "run_id": "string",
  "weakest_supported_axis": "behavior_delta|authority_enforcement|reviewer_surface|decision_quality|claim_discipline",
  "strongest_contradiction_evidence": {
    "claim_challenged": "string",
    "observed_contradiction": "string",
    "severity": "low|medium|high|critical",
    "reviewer_implication": "string"
  },
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

If `strongest_contradiction_evidence.severity` is `high` or `critical`,
reviewer must explicitly show which core claim is downgraded or falsified.

## Overall Posture Guidance

- `bounded_support`:
  - no major falsification axis triggered
  - weakest axis still at least partially supported

- `partial_falsification`:
  - one or more axes falsified, but not collapse-level

- `major_falsification`:
  - falsification in trust-critical axis (authority/reviewer surface/claim discipline)
  - or multiple axes degraded simultaneously
  - or a single high-severity contradiction directly invalidates a core claim
