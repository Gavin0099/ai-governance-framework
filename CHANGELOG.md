# Changelog

## Unreleased

### AI Governance update reporting status accuracy - 2026-07-03

- Added explicit `manual_update` and `destructive_manual_update` reporting
  statuses to the AI Governance update protocol, F-7 protocol, repo-min
  baseline AGENTS guidance, and framework AGENTS guidance so manual or
  destructive update paths cannot be described with completed/latest-style
  update claims.
- Updated F-7 and external governance submodule update status handling so
  completed-style results are downgraded when `governance_maturity_summary`
  reports that `framework.lock.json` and the checked-out framework HEAD are not
  consistent.
- Release-note boundary: this entry records unreleased user-visible
  update-reporting and status-accuracy changes only. It does not bump the
  framework version, publish a release, start v1.3.0 release prep, repair
  consuming repos, guarantee agent compliance, or wire hook/CI/pre-push/gate/
  enforcement behavior.

### External submodule updater console-safe output - 2026-07-02

- Updated `governance_tools/external_governance_submodule_updater.py` so CLI
  human and JSON output is encoded with replacement for the active console
  encoding. This prevents Chinese `human_readable_adoption_summary` output from
  crashing legacy or non-UTF stdout surfaces such as ascii, cp950, or cp1252.
- Added focused coverage in `tests/test_external_governance_submodule_updater.py`
  for ascii-only stdout, verifying the updater emits a replacement-safe report
  instead of raising `UnicodeEncodeError`.
- Release-note boundary: this entry records unreleased user-visible output
  robustness only. It does not bump the framework version, publish a release,
  change adoption summary semantics, add i18n/locale selection, alter update or
  F-7 decisions, repair consuming repos, or wire hook/CI/pre-push/gate/
  enforcement behavior.

### Framework pin freshness diagnostics - 2026-07-01

- Refined `governance_tools/adoption_doctor.py` so framework pin freshness is
  no longer limited to `.gitmodules` submodule paths. When a repo-owned
  framework checkout or hook-config external framework root is itself a git
  worktree root, the doctor now reports the same no-fetch local-tracking pin
  status used for submodule consumers.
- Propagated the expanded signal through `governance_maturity_summary` so
  consuming repos can see stale local-tracking framework checkout evidence in
  `framework_pin_freshness` during adoption/update diagnostics.
- Release-note boundary: this entry records unreleased report-only diagnostic
  coverage only. It does not bump the framework version, publish a release,
  fetch or update any framework checkout, prove true remote latest, implement
  self-update behavior, repair consuming repos, or wire hook/CI/pre-push/gate/
  enforcement behavior.

### Governance maturity summary adoption/update output - 2026-07-01

- Wired the derived, report-only `governance_maturity_summary` into
  `governance_tools/adopt_governance.py` and
  `governance_tools/f7_full_update.py` so consuming repos can see adoption
  topology, static self-contained prerequisites, hook framework-root wiring,
  local-tracking pin freshness, repo-specific rule calibration, domain
  contract/validator surfaces, and explicit non-claims during AI Governance
  adoption or F-7 update flows.
- Added focused coverage in `tests/test_adopt_governance.py` and
  `tests/test_f7_full_update.py` for copy-based, repo-owned, submodule, and
  external-contract report surfaces, including `not_available` fail-safe
  behavior when the summary builder raises.
- Release-note boundary: this entry records unreleased report-only adoption
  visibility only. It does not bump the framework version, publish a release,
  prove complete adoption in any consuming repo, install or repair hooks,
  update submodule pins, validate runtime self-contained governance, or wire
  CI/pre-push/gates/enforcement behavior.

### AUTHORITY_MANIFEST cache-invalidation refinement - 2026-06-30

- Refined `governance_tools/authority_manifest.py` and
  `governance_tools/authority_manifest_preflight.py` so routine `PLAN.md`
  planning/content churn remains observable but no longer forces
  `reload_required` for cache-preflight decisions. `PLAN.md` is now surfaced as
  `content_planning` / non-invalidating, while cache-stable authority files
  such as `AGENTS.md`, `AGENTS.base.md`, and `contract.yaml` still invalidate
  candidate reuse when changed.
- Added focused coverage in `tests/test_authority_manifest.py` and
  `tests/test_authority_manifest_preflight.py` for PLAN-only churn staying
  `reuse_candidate` and stable-authority changes still producing
  `reload_required`.
- Release-note boundary: this entry records unreleased candidate tooling
  refinement only. It does not bump the framework version, publish a release,
  implement prompt-cache behavior, observe provider cache hit/miss, prove real
  harness adoption, wire runtime hooks/CI/pre-push/gates or enforcement,
  rewrite `.governance/baseline.yaml`, change memory behavior, or authorize
  cross-repo writes.

### AUTHORITY_MANIFEST preflight consumer simulation - 2026-06-29

- Added `governance_tools/authority_manifest_preflight.py` as a read-only
  preflight consumer simulation for `AUTHORITY_MANIFEST v1`. The tool reads a
  candidate manifest and emits reviewer-facing decisions
  `reuse_candidate`, `reload_required`, `cache_unsafe`, and `not_checked`
  without performing prompt-cache reuse, discard, provider integration, or
  runtime enforcement.
- Added focused coverage in `tests/test_authority_manifest_preflight.py` for
  unreadable manifest handling, wrong-schema rejection, missing required-field
  fallback, authority-change reload signaling, unchanged-manifest reuse
  candidate signaling, and CLI no-write JSON output.
- Release-note boundary: this entry records unreleased candidate tooling only.
  It does not bump the framework version, publish a release, implement prompt
  cache behavior, observe provider cache hit/miss, wire runtime hooks/CI/
  pre-push/gates or enforcement, rewrite `.governance/baseline.yaml`, change
  memory behavior, or authorize cross-repo writes.

### AUTHORITY_MANIFEST candidate generator - 2026-06-29

- Added `governance_tools/authority_manifest.py` as a read-only
  `AUTHORITY_MANIFEST v1` candidate generator. It derives authority file
  membership from `.governance/baseline.yaml` `sha256.*` keys, summarizes
  `governance_drift_checker` status, compares base/head git blobs for
  authority-change invalidation signals, and labels hash sources so reviewers
  can distinguish baseline, working-tree, and git-blob hashes.
- Added focused coverage in `tests/test_authority_manifest.py` for baseline
  hash/provenance derivation, unchanged and changed base/head invalidation
  cases, dynamic `generated_at` exclusion from the stable manifest hash, JSON
  serialization, and CLI JSON output.
- Release-note boundary: this entry records unreleased candidate tooling only.
  It does not bump the framework version, publish a release, implement prompt
  cache behavior, monitor cache hit/miss, wire runtime hooks/CI/pre-push/gates
  or enforcement, rewrite `.governance/baseline.yaml`, change memory behavior,
  or authorize cross-repo writes.

### Adoption diagnostics and UX disposition - 2026-06-26

- Added `governance_tools/adoption_doctor.py` as a report-only local
  diagnostic for adoption class, static self-contained prerequisites,
  local-tracking submodule pin state, root-level runtime hook leftovers, and
  hook framework-root wiring. Findings remain informational or warning-level
  and do not change exit status for ordinary findings.
- Updated adoption UX wording in `governance_tools/adopt_governance.py` so
  copy-based adoption is described as audit-surface readiness, not runtime
  self-contained governance. Repo-owned framework paths are reported without
  claiming hooks, pin freshness, runtime smoke, full installer execution, or
  full test-suite success.
- Added a hook-root mismatch diagnostic after Bookstore-Scraper dogfooding:
  `hook_config_framework_root=external` is now surfaced when a repo-owned
  framework path or initialized framework submodule exists but installed hooks
  point to an external framework checkout.
- Release-note boundary: this entry records unreleased tooling changes only.
  It does not bump the framework version, publish a release, add a full or
  submodule installer, perform fetch/update/repair actions, wire the doctor
  into hooks/CI/pre-push/gates/enforcement, or claim runtime self-contained
  governance for consuming repos.

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
