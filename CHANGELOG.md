# Changelog

## v1.2.0 - 2026-04-28

### Phase D Governance Baseline Freeze

**Constitutional authority contract** — `governance/PHASE_D_CLOSE_AUTHORITY.md`:

- Canonical authority source for Phase D close semantics; registered in `governance/AUTHORITY.md`
- Precedence declaration: overrides README, PLAN.md, implementation presence, version tags, generated summaries, AI-produced assertions
- Explicit Non-Claims (NC-1–5): prohibits AI self-certification, implementation-as-completion, validator-as-authority, documentation-as-authority, proxy signing
- Required Authority Artifacts (A1–A7): authority event → canonical artifact → writer attribution (A3a/A3b split) → explicit acceptance → independence declaration → confirmed conditions → integrity constraints
- Reviewer Independence Rules (RI-1–5): self-review void (no cure), proxy review void, org hierarchy ≠ independence, code review ≠ closeout scope, retroactive signing presumptively void
- Validator Role Boundary (VRB-1–3): validators observe/reject/recommend; cannot authorize; "reviewer cannot silently override validator" + explicit exception path
- Failure Semantics (FS-1–4): Blocked vs Void distinction; F1–F17 failure mode table with remediation paths; fail-closed default; proportionate remediation

**Runtime structural enforcement** — `governance_tools/phase_d_closeout_writer.py`:

- `REQUIRED_CONDITIONS`: 5-item frozenset for F10/F11 minimum coverage enforcement
- `EXCEPTION_OVERRIDE_SUPPORTED = False`: VRB-3 exception path explicitly unsupported in this runtime
- `assess_phase_d_closeout()` new output: `failures[]` (structured with `failure_code`/`failure_class`/`remediation`), `missing_required_conditions`, `exception_override_supported`, `exception_override_note`, `runtime_unverifiable_conditions`

**Capability boundary**: runtime-aligned structural enforcement v0.1.
Legitimacy failures (F12–F15) remain reviewer-attested / audit-invalidatable.
Artifact immutability (F4) and exception artifact path (F16/F17) not yet implemented.
This is not full runtime enforcement of the constitutional contract.

18 new tests; state_reconciliation fixtures updated to require all 5 confirmed conditions.

---

## v1.1.0 - 2026-03-22

See [docs/releases/README.md](docs/releases/README.md), [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md), [docs/releases/v1.1.0-github-release.md](docs/releases/v1.1.0-github-release.md), and [docs/releases/v1.1.0-publish-checklist.md](docs/releases/v1.1.0-publish-checklist.md).



### Adoption tooling

- **`governance_tools/adopt_governance.py`** — cross-platform Python equivalent of `bash scripts/init-governance.sh --adopt-existing` for Windows users; same semantics: copies AGENTS.base.md (protected), creates missing AGENTS.md/contract.yaml/PLAN.md from templates, generates `.governance/baseline.yaml` with hashes + inventory
  - `--refresh` mode: re-hashes existing baseline, updates section inventory, preserves `plan_required_sections` — does not copy template files
  - `--dry-run` flag: previews planned actions without writing anything
  - Framework root resolution: `--framework-root` > `GOVERNANCE_FRAMEWORK_ROOT` env > upward scan > `__file__` fallback
  - 26 tests covering adopt + refresh scenarios

### Drift check hardening (checks 13–16)

- Check #13 `contract_no_placeholders` — fails when contract.yaml still contains `<...>` template tokens
- Check #14 `agents_sections_filled` — fails when governance:key sections in AGENTS.md have no real content
- Check #15 `plan_inventory_current` — warns when plan_section_inventory in baseline no longer matches actual PLAN.md headings; emits `--refresh` hint
- Check #16 `contract_not_framework_copy` — fails when contract.yaml name matches framework's own contract (verbatim-copy guard)
- `protected_file_sentinel_present` now fails with severity=critical when AGENTS.base.md is absent (previously silently skipped) — closes gap with `readiness.contract_files_complete`; both tools now agree

### Freshness threshold (❺)

- `FRAMEWORK_DEFAULT_FRESHNESS_DAYS = 14` — framework default raised from 7 to 14
- Threshold source always labelled in drift output: `contract override: Nd` / `PLAN.md policy: Nd` / `framework default: 14d`
- Guardrail warning when `plan_freshness_threshold_days > 14` (override exceeds framework default)
- `plan_freshness_threshold_days` in `baseline.yaml` CONTRACT layer overrides staleness threshold

### Framework root auto-discovery (❻)

- `is_framework_root(path)` — detects framework via `governance_tools/`, `governance/`, `docs/governance-runtime*` markers
- `discover_framework_root(start_path)` — walks upward; returns None if not found (no silent guess)
- `check_governance_drift()` resolution order: CLI → `GOVERNANCE_FRAMEWORK_ROOT` env → upward scan → `__file__` fallback
- `init-governance.sh` gains `--framework-root` flag and `_discover_framework_root()` bash equivalent
- `GOVERNANCE_FRAMEWORK_ROOT` env var in `repo_root_from_tooling()` for vendored-copy repos

### Adoption friction fixes

- `hooks_ready` removed from `readiness_ready` gate — hooks are a deployment convenience, not a governance requirement; Windows users with clean governance are no longer blocked
- Hooks warnings relabelled as `hooks (optional): ...` so non-blocking status is visible in output
- PLAN.md `最後更新` missing-field error now includes a 3-line example snippet explaining Traditional Chinese field names are a framework design decision
- `[governance_drift]` section in `external_repo_readiness` human output moved above `[contract]`, labelled "authoritative governance compliance check"
- PLAN.md discovery in `external_repo_readiness`: scans `PLAN.md`, `governance/`, `memory/`, `docs/` (same as adopt tool)

### Baseline

- `baseline.yaml` carries four-layer semantic comments: PROVENANCE / INTEGRITY / CONTRACT / OBSERVED
- `plan_path:` recorded for non-standard PLAN.md locations; read back by `--refresh` and drift checker

### Test coverage

- 889 tests passing (up from 835)
- New test files: `tests/test_framework_versioning.py`, `tests/test_adopt_governance.py`

## post-alpha hardening - 2026-03-21

Cross-repo governance baseline distribution system (6 commits since v1.0.0-alpha):

**Cross-repo adoption infrastructure**
- `baselines/repo-min/` — minimum viable baseline: `AGENTS.base.md` (protected), `AGENTS.md`, `PLAN.md`, `contract.yaml`
- `scripts/init-governance.sh` — four lifecycle stages: `init`, `--adopt-existing`, `--upgrade`, `--refresh-baseline`
- `governance_tools/governance_drift_checker.py` — 12-check drift detection across 4 categories; exit codes 0/1/2

**Lifecycle semantics clarified**
- `plan_required_sections` (governance mandate) separated from `plan_section_inventory` (observed snapshot)
- `--adopt-existing` imposes no mandate on existing repos; records inventory only
- `--refresh-baseline` rehashes without copying template files; preserves mandate
- `governance:key=<name>` anchors added to AGENTS.md template for machine-readable section discovery

**Framework integration**
- `external_repo_readiness.py` now calls `check_governance_drift()` and surfaces `governance_baseline_present` / `governance_drift_clean` checks
- Framework repo self-applies its own baseline (`.governance/baseline.yaml`, `contract.yaml`)

**Test coverage**
- 835 tests passing (up from 800 at v1.0.0-alpha)
- `test_governance_drift_checker.py`: 35 tests covering all 12 checks, custom sections, adopt-existing, lifecycle modes
- `test_external_repo_readiness.py`: 4 new governance drift integration tests

## v1.0.0-alpha - 2026-03-15

See [docs/releases/README.md](docs/releases/README.md), [docs/releases/v1.0.0-alpha.md](docs/releases/v1.0.0-alpha.md), [docs/releases/v1.0.0-alpha-github-release.md](docs/releases/v1.0.0-alpha-github-release.md), and [docs/releases/v1.0.0-alpha-publish-checklist.md](docs/releases/v1.0.0-alpha-publish-checklist.md).

Highlights:

- runtime governance spine is operational
- external domain contract seam is validated
- USB-Hub and Kernel-Driver low-level domain slices now exist
- onboarding path now has `requirements.txt`, `start_session.md`, `quickstart_smoke.py`, and `example_readiness.py`
- release-facing trust signals now also include `docs/releases/alpha-checklist.md`
- repo status docs now also include `docs/status/trust-signal-dashboard.md`
- `docs/status/README.md` now provides a stable index over repo status pages
- trust-signal publishing now also supports a stable repo-local generated path under `docs/status/generated/`
- CI now emits trust-signal snapshot bundles with latest/history/index outputs
- CI now installs documented dependencies and verifies runnable examples more strictly
