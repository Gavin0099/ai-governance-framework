# Reviewer Handoff

Updated: 2026-03-15

This page is the highest-level reviewer entry point for the repository's current
governance posture.

Use it when you do not want to decide up front whether the next thing to inspect
is:

- trust / adoption health
- release / package readiness
- or the relationship between the two

## Fastest Local Command

```bash
python governance_tools/reviewer_handoff_summary.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

This command aggregates:

- `trust_signal_overview.py`
- `release_surface_overview.py`

So the first pass is one summary, not two different tool families.

If you want the same reviewer packet preserved as a latest/history/index bundle:

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --write-bundle artifacts/reviewer-handoff/v1.0.0-alpha \
  --format human
```

To read that generated bundle back as a stable summary:

```bash
python governance_tools/reviewer_handoff_reader.py \
  --release-version v1.0.0-alpha \
  --file artifacts/reviewer-handoff/v1.0.0-alpha/MANIFEST.json \
  --format human
```

## When To Use This Page

Use this first when you want:

- one reviewer-facing summary instead of multiple raw manifests
- the current alpha posture across both trust and release surfaces
- a quick "is this repo handoff-ready?" answer before drilling deeper

## Suggested Reading Flow

1. Start with `reviewer_handoff_summary.py`
2. If the trust side is the question, move to [Trust Signal Dashboard](trust-signal-dashboard.md)
3. If the release/package side is the question, move to [Runtime Governance Status](runtime-governance-status.md) and the release docs under [../releases/README.md](../releases/README.md)
4. If you need exact cross-domain policy posture, move to [Domain Enforcement Matrix](domain-enforcement-matrix.md)

## CI Artifacts

CI now emits reviewer handoff artifacts under:

- `artifacts/reviewer-handoff/v1.0.0-alpha/latest.txt`
- `artifacts/reviewer-handoff/v1.0.0-alpha/latest.json`
- `artifacts/reviewer-handoff/v1.0.0-alpha/latest.md`
- `artifacts/reviewer-handoff/v1.0.0-alpha/INDEX.md`
- `artifacts/reviewer-handoff/v1.0.0-alpha/MANIFEST.json`

These artifacts are intended to be the highest-level reviewer packet when
sharing pipeline output.

## Related Sources

- [Status Index](README.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Runtime Governance Status](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Alpha Release Note](../releases/v1.0.0-alpha.md)
