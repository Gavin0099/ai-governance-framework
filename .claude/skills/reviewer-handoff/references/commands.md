# Commands

## One-shot reviewer summary

```bash
python governance_tools/reviewer_handoff_summary.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --format human
```

## Snapshot bundle

```bash
python governance_tools/reviewer_handoff_snapshot.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --write-bundle artifacts/reviewer-handoff/v1.0.0-alpha --publish-status-dir artifacts/reviewer-handoff/published --publication-root artifacts/reviewer-handoff --format human
```

## Read an existing bundle

```bash
python governance_tools/reviewer_handoff_reader.py --release-version v1.0.0-alpha --file artifacts/reviewer-handoff/v1.0.0-alpha/MANIFEST.json --format human
```

## Read a publication layer

```bash
python governance_tools/reviewer_handoff_publication_reader.py --release-version v1.0.0-alpha --file artifacts/reviewer-handoff/PUBLICATION_MANIFEST.json --format human
```

## Supporting views

```bash
python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/release_surface_overview.py --version v1.0.0-alpha --format human
```
