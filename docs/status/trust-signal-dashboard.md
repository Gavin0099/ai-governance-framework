# Trust Signal Dashboard

Updated: 2026-03-22

This page is the stable in-repo entry point for the framework's current adoption
and release-facing trust signals.

Use it when you want one place to understand:

- whether the documented quickstart still works
- whether bundled examples are still healthy
- whether release-facing docs are aligned
- whether the governance self-audit still passes
- and, when provided, whether external domain repos still expose the expected enforcement posture

## Fastest Local Command

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
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
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
  --write-bundle artifacts/trust-signals \
  --publish-status-dir artifacts/trust-signals/published \
  --format human
```

If you want the same publication to land under a stable repo-local docs path:

```bash
python governance_tools/trust_signal_snapshot.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --external-contract-repo D:/USB-Hub-Firmware-Architecture-Contract \
  --external-contract-repo D:/Kernel-Driver-Contract \
  --external-contract-repo D:/IC-Verification-Contract \
  --publish-docs-status \
  --format human
```

If you want to read the latest publication metadata as a compact summary:

```bash
python governance_tools/trust_signal_publication_reader.py \
  --file artifacts/trust-signals/PUBLICATION_MANIFEST.json \
  --format human
```

If you are using the stable repo-local generated path instead:

```bash
python governance_tools/trust_signal_publication_reader.py \
  --project-root . \
  --docs-status \
  --format human
```

That generated root now also writes its own `generated/README.md`, so the repo-local path has a human-readable landing page even before you open the manifest directly.

## CI Artifacts

CI now emits trust-signal snapshot artifacts under:

- `artifacts/trust-signals/latest.txt`
- `artifacts/trust-signals/latest.json`
- `artifacts/trust-signals/latest.md`
- `artifacts/trust-signals/history/*`
- `artifacts/trust-signals/INDEX.md`
- `artifacts/trust-signals/MANIFEST.json`
- `artifacts/trust-signals/PUBLICATION_MANIFEST.json`
- `artifacts/trust-signals/PUBLICATION_INDEX.md`
- `artifacts/trust-signals/published/manifest.json`
- `artifacts/trust-signals/published/*`
- `artifacts/trust-signals/published/history/*`
- `artifacts/trust-signals/published/INDEX.md`

The bundle and published directories now also include manifest JSON so downstream tools and the publication reader can identify the current snapshot directly.
When external contract repos are provided, the publication metadata now also carries a compact cross-domain enforcement summary, including profile counts and per-repo hard-stop posture.
The generated status surface now also includes a dedicated `domain-enforcement-matrix.md` page on the published side, so cross-domain enforcement posture is shareable as a first-class status page rather than only embedded inside manifests.

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
