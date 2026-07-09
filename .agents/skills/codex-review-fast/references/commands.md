# Commands

`codex-review-fast` is deprecated as a standalone skill. Use the target skill command references instead.

## Reviewer packet support

```bash
python governance_tools/reviewer_handoff_summary.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --format human
```

## Trust and release drill-down

```bash
python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/release_surface_overview.py --version v1.0.0-alpha --format human
```

## Runtime smoke support

```bash
bash scripts/run-runtime-governance.sh --mode smoke
```
