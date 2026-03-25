# AI Governance Framework

> A runnable AI governance runtime for multi-repo engineering workflows, now in the cost-and-efficiency hardening stage before full productization.

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## What This Is

In long-lived projects, the most common AI failure modes are not one-off intelligence misses, but:

- gradually forgetting context
- drifting away from the current sprint or phase
- breaking architectural boundaries
- finishing work without leaving reviewable knowledge behind

This repository provides governance documents, validation tools, and runtime hooks that move an AI coding workflow from:

`AI -> code -> human review`

to:

`AI -> runtime governance -> task execution -> session lifecycle -> memory governance`

The most precise current positioning is:

- a runnable `AI Coding Runtime Governance Framework`, already exercised on real repos
- a framework with a real runtime governance spine, not just static policy documents
- an established external domain validator seam with firmware, kernel-driver, and IC-verification slices already running
- a cross-platform adopt toolchain (`adopt_governance.py`) validated against multiple repo types and self-hosting paths
- a drift checker with 16 named checks and a minimum-legal schema reference that lets users onboard without reading source code
- still actively strengthening:
  - semantic verification depth
  - practical git-hook / CI-gate interception coverage
  - repo-type-specific rule classification to reduce governance overhead on minimal repos

## Status

Current release-facing status:

- version: `v1.1.0` (2026-03-22)
- previous release: [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md)
- changelog: [CHANGELOG.md](CHANGELOG.md)
- known limits: [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- status index: [docs/status/README.md](docs/status/README.md)
- trust signal dashboard: [docs/status/trust-signal-dashboard.md](docs/status/trust-signal-dashboard.md)
- domain enforcement matrix: [docs/status/domain-enforcement-matrix.md](docs/status/domain-enforcement-matrix.md)
- schema reference: [docs/minimum-legal-schema.md](docs/minimum-legal-schema.md)

This framework is suitable for evaluation, internal adoption trials, and domain-contract experimentation.
It should still be treated as an early-stage framework rather than a fully closed enforcement platform:
semantic verification depth, adoption smoothness, and rule classification remain open fronts.

### What Changed in v1.1.0 and Since

- **Cross-platform adopt toolchain** - `adopt_governance.py` replaces bash-only `init-governance.sh` for Windows and now seeds a minimal drift CI workflow when missing
- **Schema visibility** - adopt substitutes repo slug and today's date into templates, repairs the required `AGENTS.base.md` seam, and surfaces repo-specific `AGENTS.md` follow-up prompts
- **16-check drift checker** - placeholder detection, template-copy guard, inventory staleness, and `AGENTS.md` fill checks are part of the named baseline
- **Freshness threshold** - framework default raised to 14d; CONTRACT-layer override remains auditable in drift output, with a warning when override > 14d
- **Framework root auto-discovery** - `GOVERNANCE_FRAMEWORK_ROOT` env var + upward scan are consistent across Python tools and bash scripts
- **Minimum legal schema reference** - [docs/minimum-legal-schema.md](docs/minimum-legal-schema.md) is surfaced at multiple onboarding touch points
- **Current test count** - `1,333 tests` at the end of the Step 7 token-optimization roadmap
- **Recent hardening** - onboarding now has its own audit lane, Windows terminal output is safer, and `kernel-driver-adapter-summary.md` is live for summary-first contract loading

### Validation Status

| What Has Been Validated | Status |
|-------------------------|--------|
| Core governance tools pass automated test suite (`1,333 tests`) | Done |
| Runtime hooks work across Claude / Codex / Gemini adapters | Done |
| External domain contract seam (firmware, kernel-driver, IC-verification) | Done |
| CI pipeline runs governance checks on every push | Done |
| Quickstart smoke reproducible in < 5 minutes | Done |
| Real-repo adoption validated across multiple repo types | Done |
| Empty repo + adopt reaches a drift-clean or repo-specific-follow-up baseline without source edits | Done |
| **Independent reviewer onboards without author guidance** | **Next Gate** |
| Rule classification: core vs optional checks per repo type | Not yet |

### Tested Scope

Adoption has been validated on:

| Repo type | Example | Result |
|-----------|---------|--------|
| Service (minimal backend) | ziwei-service (Express HTTP wrapper) | adoption friction identified, then fixed |
| Tooling (Python validator collection) | governance_tools subset | adoption friction identified, then fixed |
| Product (Next.js + Supabase + Claude) | Mirra | `ready=True`, drift 16/16 PASS |
| Governance-heavy (this repo) | ai-governance-framework | self-hosting |
| Low-level contract repo | Kernel-Driver-Contract | contract loading, validator preflight, and summary-first onboarding path validated |

Not yet validated on:

- large monorepos or multi-package workspaces
- data pipelines or ML repos
- repos with no PLAN / contract concept and no intention to add one
- large validated adopter sets outside the current Python / TypeScript / C# / C/C++ governance surfaces

If your repo falls outside the validated scope, treat adoption as an experiment rather than a guaranteed path.
The schema reference ([docs/minimum-legal-schema.md](docs/minimum-legal-schema.md)) and the `--dry-run` flag are your safest starting points.

## Comparison & Differentiation

The simplest way to describe the difference is:

- this repository is designed around a multi-repo runtime-governance stack with:
  - external domain contracts
  - runtime policy input and runtime policy reclassification
  - reviewer, trust, and release publication surfaces
- and it operates primarily at the task/session boundary
  - rather than trying to govern every agent action or every generation token inside the model runtime

See [docs/competitive-landscape.md](docs/competitive-landscape.md) for the fuller comparison memo.

## Core Capabilities

### 1. Governance Constitution

The `governance/` directory defines AI roles, boundaries, and stop conditions inside the repository:

- `SYSTEM_PROMPT.md`
- `HUMAN-OVERSIGHT.md`
- `AGENT.md`
- `ARCHITECTURE.md`
- `REVIEW_CRITERIA.md`
- `TESTING.md`
- `NATIVE-INTEROP.md`
- `PLAN.md`

The repo also carries local workflow skills under [`.claude/skills/`](./.claude/skills/) with an index at [`.claude/README.md`](./.claude/README.md).

### 2. Static Governance Tooling

`governance_tools/` includes contract validation, drift checking, readiness/onboarding, payload auditing, reviewer handoff, release/trust surfaces, and domain-specific evidence tooling.

Key entry points:

- `adopt_governance.py`
- `governance_drift_checker.py`
- `external_repo_readiness.py`
- `external_repo_onboarding_report.py`
- `trust_signal_overview.py`
- `reviewer_handoff_summary.py`

### 3. Runtime Governance

`runtime_hooks/` supports:

- `session_start`
- `pre_task_check`
- `post_task_check`
- `session_end`
- Claude / Codex / Gemini adapters
- verdict and trace artifact emission under `artifacts/runtime/`

This runtime governance loop is real and operational, but interception coverage is still not fully closed. Some IDE, local-edit, or direct-commit paths can still bypass it.

### 4. Memory Pipeline

`memory_pipeline/` supports:

- session snapshots
- memory curation
- promotion policy
- memory promotion
- preservation of domain contract metadata into curated artifacts

### 5. Rule Packs and Decision Model

Built-in rule packs include:

- scope packs: `common`, `refactor`
- language packs: `python`, `cpp`, `csharp`, `swift`
- framework packs: `avalonia`
- platform packs: `kernel-driver`

The next runtime step is captured in:

- [docs/governance-runtime-v2.6.md](docs/governance-runtime-v2.6.md)
- [governance/governance_decision_model.v2.6.json](governance/governance_decision_model.v2.6.json)

That decision model defines ownership, policy precedence, evidence trust, violation handling, and a determinism contract as machine-checkable spec inputs.

### 6. External Domain Seam

The framework currently supports an external domain extension seam with:

- `contract.yaml` discovery
- external rule roots
- validator preflight
- validator execution
- contract-level policy inputs for selected validator rule IDs via `hard_stop_rules`
- versioned validator payload envelopes with backward-compatible legacy fields

This is the current transitional seam, not the final decision architecture. Final verdict computation, violation handling, and fallback behavior are being pulled into the runtime decision model.

Validated external slices currently include:

- `USB-Hub-Firmware-Architecture-Contract`
- `Kernel-Driver-Contract`
- `IC-Verification-Contract`

To reduce adoption friction, runtime hooks support contract auto-discovery and summary-first domain loading. The `kernel-driver` path now resolves [kernel-driver-adapter-summary.md](docs/domain-summaries/kernel-driver-adapter-summary.md) as a live low-token adapter rather than a placeholder.

## Quick Start

For a five-minute guided run, start with [start_session.md](start_session.md).

Verify installation with one command:

```bash
python governance_tools/quickstart_smoke.py --project-root . --plan PLAN.md --contract examples/usb-hub-contract/contract.yaml --format human
```

Expected output:

```text
[quickstart_smoke]
ok=True
summary=ok=True | pre_task_ok=True | session_start_ok=True | contract=firmware/medium
```

## Adopting into an Existing Repo

Use `adopt_governance.py` to onboard an existing project. It copies required framework files, creates missing templates, and generates `.governance/baseline.yaml` without overwriting anything you already have.

When an existing `contract.yaml` is kept, adopt still performs one framework-required repair: if `AGENTS.base.md` is not referenced in `documents` or `ai_behavior_override`, it adds `AGENTS.base.md` to `ai_behavior_override` so first-run drift does not fail on that single missing baseline reference.

Adopt also:

- seeds a minimal `.github/workflows/governance-drift.yml` when the target repo does not already have one
- points out which `AGENTS.md` repo-specific sections are still at template `N/A` defaults
- supports refresh delta summaries after baseline rewrites
- works cross-platform on macOS, Linux, and Windows

Onboarding-shaped payload audits now emit a dedicated `onboarding-*.jsonl` lane, and Windows terminal output falls back safely when the active code page cannot encode some Unicode characters.

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

Common options:

| Flag | Effect |
|------|--------|
| `--target PATH` | Path to the repo to adopt (default: current directory) |
| `--framework-root PATH` | Override framework root (default: auto-discovered) |
| `--refresh` | Re-hash existing baseline without copying template files |
| `--dry-run` | Preview planned actions without writing anything |

Refresh after governance files change:

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo --refresh
```

> **Windows note:** `scripts/init-governance.sh` requires bash. Use `adopt_governance.py` instead - it is the canonical cross-platform equivalent.

If a drift check is still failing after adoption, consult [docs/minimum-legal-schema.md](docs/minimum-legal-schema.md).

## Common Entry Points

### Static Governance Tools

```bash
python governance_tools/contract_validator.py --file ai_response.txt
python governance_tools/plan_freshness.py --plan PLAN.md
python governance_tools/governance_drift_checker.py --repo . --framework-root .
python governance_tools/external_repo_readiness.py --repo /path/to/repo
python governance_tools/reviewer_handoff_summary.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human
python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.1.0 --contract examples/usb-hub-contract/contract.yaml --format human
```

### Runtime Hooks

```bash
python runtime_hooks/core/pre_task_check.py --rules common,python,cpp --risk high --oversight review-required
python runtime_hooks/core/session_start.py --project-root . --plan PLAN.md --rules common,refactor --task-text "Refactor Avalonia boundary"
python runtime_hooks/core/post_task_check.py --file ai_response.txt --risk medium --oversight review-required --checks-file checks.json
python runtime_hooks/core/session_end.py --project-root . --session-id 2026-03-12-01 --runtime-contract-file contract.json --checks-file checks.json --response-file ai_response.txt
```

### Smoke Test

```bash
python runtime_hooks/smoke_test.py --harness claude_code --event-type pre_task
python runtime_hooks/smoke_test.py --harness codex --event-type session_start
python runtime_hooks/smoke_test.py --event-type session_start
```

### Shared Runtime Enforcement

The canonical CI / git-hook entrypoint is `scripts/run-runtime-governance.sh`.
It wraps pre-task, post-task, and session hooks into a single shell call:

```bash
bash scripts/run-runtime-governance.sh --mode enforce
bash scripts/run-runtime-governance.sh --mode ci
```

## Payload Audit and Token Work

The Step 1-Step 7 roadmap and rebaseline outputs live under [docs/payload-audit/](docs/payload-audit/README.md).

Current headline numbers:

- strict comparable reduction (`L0 + L1`): `44073 -> 28114` (`-15959`, `-36.2%`)
- observed total reduction: `104696 -> 49202` (`-55494`, `-53.0%`)
- KDC summary-first onboarding recheck: `60623 -> 37142` (`-23481`, `-38.7%`)

The next high-leverage optimization target is not the kernel-driver summary itself anymore; it is the `pre_task_check` and rendered-output cost on the KDC onboarding path.

## Further Reading

- [docs/competitive-landscape.md](docs/competitive-landscape.md)
- [docs/runtime-governance-update.md](docs/runtime-governance-update.md)
- [runtime_hooks/README.md](runtime_hooks/README.md)
- [memory_pipeline/README.md](memory_pipeline/README.md)
- [governance_tools/README.md](governance_tools/README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
