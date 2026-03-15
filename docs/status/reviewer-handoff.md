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

If you want the publication-layer summary over that same bundle:

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --release-version v1.0.0-alpha \
  --file artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json \
  --format human
```

If you want the same reviewer-handoff publication written to a stable repo-local docs path:

```bash
python governance_tools/reviewer_handoff_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --publish-docs-status \
  --format human
```

That stable generated path can then be read back with:

```bash
python governance_tools/reviewer_handoff_publication_reader.py \
  --project-root . \
  --release-version v1.0.0-alpha \
  --docs-status \
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
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.md`
- `artifacts/reviewer-handoff/published/reviewer-handoff-latest.json`
- `artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `artifacts/reviewer-handoff/PUBLICATION_INDEX.md`

These artifacts are intended to be the highest-level reviewer packet when
sharing pipeline output.

## Stable Generated Docs Path

When you want a repo-local, stable consumption path instead of ad-hoc artifacts,
the generated reviewer-handoff root becomes:

- `docs/status/generated/reviewer-handoff/`

Its main entry points are:

- `docs/status/generated/reviewer-handoff/README.md`
- `docs/status/generated/reviewer-handoff/PUBLICATION_MANIFEST.json`
- `docs/status/generated/reviewer-handoff/site/README.md`

## Related Sources

- [Status Index](README.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
- [Runtime Governance Status](runtime-governance-status.md)
- [Domain Enforcement Matrix](domain-enforcement-matrix.md)
- [Alpha Release Note](../releases/v1.0.0-alpha.md)
