# Trust Signal Dashboard

Updated: 2026-03-15

This page is the stable in-repo entry point for the framework's current adoption
and release-facing trust signals.

Use it when you want one place to understand:

- whether the documented quickstart still works
- whether bundled examples are still healthy
- whether release-facing docs are aligned
- whether the governance self-audit still passes

## Fastest Local Command

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

If you want a shareable dashboard-style output:

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --format markdown
```

If you want to publish a stable generated snapshot page:

```bash
python governance_tools/trust_signal_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --write-bundle artifacts/trust-signals \
  --publish-status-dir artifacts/trust-signals/published \
  --format human
```

## CI Artifacts

CI now emits trust-signal snapshot artifacts under:

- `artifacts/trust-signals/latest.txt`
- `artifacts/trust-signals/latest.json`
- `artifacts/trust-signals/latest.md`
- `artifacts/trust-signals/history/*`
- `artifacts/trust-signals/INDEX.md`
- `artifacts/trust-signals/MANIFEST.json`
- `artifacts/trust-signals/published/*`

The bundle and published directories now also include manifest JSON so downstream tools can identify the current snapshot directly.

These artifacts are the generated status snapshot bundle.

This page is the stable landing page that explains where those generated reports
come from and how to regenerate them locally.

## Related Sources

- [Status Index](README.md)
- [Runtime Governance Status](runtime-governance-status.md)
- [Next Steps](next-steps.md)
- [Alpha Release Note](../releases/v1.0.0-alpha.md)
- [Alpha Checklist](../releases/alpha-checklist.md)
- [Known Limits](../LIMITATIONS.md)

## What “Healthy” Currently Means

For the current alpha, the expected high-level posture is:

- quickstart smoke passes
- example readiness passes
- release readiness passes
- governance auditor passes

This does **not** mean:

- full interception coverage is closed
- domain validators are universally hard-stop
- semantic verification is equivalent to a full policy engine

Those boundaries remain part of the current alpha honesty model and should stay
visible in release-facing communication.
