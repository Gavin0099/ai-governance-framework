# Alpha Release Checklist

Updated: 2026-03-28

Current tracked release: `v1.1.0`

This checklist is intentionally lightweight. It exists to make the repository's
release-facing trust signals explicit and reviewable instead of leaving them
spread across CI, README notes, and ad-hoc terminal checks.

## Core Confidence Checks

- [x] `requirements.txt` exists and matches the documented local setup path
- [x] `start_session.md` provides a five-minute guided entry path
- [x] `python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human`
- [x] `python governance_tools/example_readiness.py --format human`
- [x] `python governance_tools/release_readiness.py --version v1.1.0 --format human`
- [x] `python governance_tools/governance_auditor.py --project-root . --release-version v1.1.0 --format human`
- [x] `python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human`
- [x] `python governance_tools/trust_signal_snapshot.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --publish-docs-status --format human`
- [x] `python governance_tools/trust_signal_publication_reader.py --project-root . --docs-status --format human`
- [x] `python governance_tools/release_package_snapshot.py --version v1.1.0 --publish-docs-release --format human`
- [x] `python governance_tools/release_package_reader.py --version v1.1.0 --project-root . --docs-release --format human`
- [x] `python governance_tools/release_package_publication_reader.py --project-root . --docs-release-root --format human`
- [x] `python governance_tools/release_surface_overview.py --version v1.1.0 --format human`
- [x] `bash scripts/verify_phase_gates.sh`

## Release-Facing Artifacts

- [x] `README.md` reflects the current release positioning
- [x] `CHANGELOG.md` links to `docs/releases/v1.1.0.md`
- [x] `docs/releases/v1.1.0.md` exists
- [x] `docs/releases/v1.1.0-github-release.md` exists
- [x] `docs/releases/v1.1.0-publish-checklist.md` exists
- [x] `docs/releases/v1.0.0-alpha.md` exists (previous release)
- [x] `docs/releases/v1.0.0-alpha-github-release.md` exists (previous release)
- [x] `docs/releases/v1.0.0-alpha-publish-checklist.md` exists (previous release)
- [x] `docs/status/runtime-governance-status.md` reflects current maturity
- [x] `docs/status/README.md` points to the generated status landing path
- [x] `docs/status/trust-signal-dashboard.md` explains the repo-local generated status path
- [x] `docs/releases/generated/README.md` exists for generated release-package publishing
- [x] `docs/LIMITATIONS.md` describes current boundaries honestly

## Known Boundaries To Keep Explicit

- [x] interception coverage is still partial, not fully closed
- [x] most domain validation remains advisory-first
- [x] semantic verification is still shallower than a full policy engine
- [x] rule classification is not yet differentiated by repo type
- [x] the external domain seam is real, but not yet a versioned plugin marketplace
