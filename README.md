# AI Governance Framework

Machine-interpretable governance runtime for AI-assisted development.
This repository focuses on execution evidence, review surfaces, and governance boundaries.

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## Token Cross-Repo Controlled Slice Closeout (2026-05-06)

### Closeout Status
Status: closed for current controlled slice

This package establishes:
- cross-repo distribution slice evidence
- interpretation guard
- citation requirement
- documented misuse scenarios

This package does not establish:
- full regression coverage
- token correctness
- production readiness
- automated misuse enforcement
- runtime decision safety

Reopen only when:
- a new repository is added
- token contract changes
- citation or misuse wording changes
- sentinel run detects drift

Primary references:
- [docs/payload-audit/token-cross-repo-summary-2026-05-05.md](docs/payload-audit/token-cross-repo-summary-2026-05-05.md)
- [docs/payload-audit/token-cross-repo-index-2026-05-06.md](docs/payload-audit/token-cross-repo-index-2026-05-06.md)
- [docs/payload-audit/token-observability-misuse-scenarios-v0.1.md](docs/payload-audit/token-observability-misuse-scenarios-v0.1.md)

## What This Repo Is

- Canonical governance runtime and policy source for this workspace.
- Session/task evidence pipeline for reviewer-facing verification.
- Tooling for adoption, drift checking, and governance status surfacing.

Core surfaces:
- `execution`
- `evidence`
- `decision`
- `memory / state`
- `reviewer surface`

## What This Repo Is Not

- A full execution harness for arbitrary projects.
- A machine-authoritative decision engine.
- A generic multi-agent orchestration platform.
- Proof of production readiness by default.

## Runtime Hooks

- [runtime_hooks/core/session_start.py](runtime_hooks/core/session_start.py)
- [runtime_hooks/core/pre_task_check.py](runtime_hooks/core/pre_task_check.py)
- [runtime_hooks/core/post_task_check.py](runtime_hooks/core/post_task_check.py)
- [runtime_hooks/core/session_end.py](runtime_hooks/core/session_end.py)

Shared entrypoint:
- `scripts/run-runtime-governance.sh`

## Governance Tools

- [governance_tools/](governance_tools/)
- [governance_tools/adopt_governance.py](governance_tools/adopt_governance.py)
- [governance_tools/governance_drift_checker.py](governance_tools/governance_drift_checker.py)
- [governance_tools/external_repo_readiness.py](governance_tools/external_repo_readiness.py)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)

## Canonical Governance Source

- [governance/](governance/)
- [governance/AGENT.md](governance/AGENT.md)
- [governance/SYSTEM_PROMPT.md](governance/SYSTEM_PROMPT.md)
- [governance/TESTING.md](governance/TESTING.md)
- [governance/ARCHITECTURE.md](governance/ARCHITECTURE.md)
- [governance/RULE_REGISTRY.md](governance/RULE_REGISTRY.md)

## Reviewer / Status Surface

- [docs/status/README.md](docs/status/README.md)
- [docs/status/runtime-governance-status.md](docs/status/runtime-governance-status.md)
- [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
- [docs/status/reviewer-handoff.md](docs/status/reviewer-handoff.md)

## Phase D Governance Authority

- Constitutional authority contract:
  - [governance/PHASE_D_CLOSE_AUTHORITY.md](governance/PHASE_D_CLOSE_AUTHORITY.md)
- Runtime implementation:
  - [governance_tools/phase_d_closeout_writer.py](governance_tools/phase_d_closeout_writer.py)

Note:
- Runtime structural enforcement exists for core closeout fields.
- Legitimacy failures remain reviewer-attested and audit-invalidatable.

## Releases

- [CHANGELOG.md](CHANGELOG.md)
- [docs/releases/README.md](docs/releases/README.md)
- [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)
- [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)

## Quickstart

```bash
pip install -r requirements.txt
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

## Adopt In Another Repo

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

Related docs:
- [examples/starter-pack/](examples/starter-pack/)
- [governance_tools/upgrade_starter_pack.py](governance_tools/upgrade_starter_pack.py)
- [docs/consuming-repo-adoption-checklist.md](docs/consuming-repo-adoption-checklist.md)
- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
