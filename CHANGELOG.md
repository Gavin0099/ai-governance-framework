# Changelog

## post-alpha hardening (continued) - 2026-03-22 (part 3)

**Adoption friction fixes (from validation report)**
- `hooks_ready` removed from `readiness_ready` gate — hooks are a deployment convenience,
  not a governance requirement; Windows users with clean governance no longer blocked
- Hooks warnings relabelled as `hooks (optional): ...` so the non-blocking nature is
  visible in output without digging into docs
- PLAN.md `最後更新` missing-field error now includes a full 3-line example snippet
  explaining that the framework uses Traditional Chinese field names (design decision)
- New test: `test_assess_external_repo_ready_without_hooks` — explicit contract that
  hooks=False must not block readiness_ready

## post-alpha hardening (continued) - 2026-03-22 (part 2)

**Framework root auto-discovery (❻)**
- `is_framework_root(path)` — detects governance framework installation via `governance_tools/`, `governance/`, or `docs/governance-runtime*` markers
- `discover_framework_root(start_path)` — walks upward from start_path to find nearest framework root; returns None if not found (no silent guess)
- `check_governance_drift()` resolution order: CLI `framework_root=` → `GOVERNANCE_FRAMEWORK_ROOT` env → upward scan → `__file__` fallback
- `init-governance.sh` adds `--framework-root` CLI flag; resolution order: `--framework-root` → `GOVERNANCE_FRAMEWORK_ROOT` → `FRAMEWORK_ROOT` (legacy) → upward scan → script dir fallback
- `_discover_framework_root()` bash equivalent using same detection heuristics
- Edge cases (nested repos, monorepos, symlinks): not handled — callers that need deterministic behaviour use explicit path; 9 new tests covering all detection cases and priority ordering

**Freshness default hardened (❺ guardrail)**
- `FRAMEWORK_DEFAULT_FRESHNESS_DAYS = 14` — framework default raised from 7 to 14
- Threshold detection: `PLAN.md Freshness:` header is checked for *explicit* policy (via `.policy` field); absent header falls through to framework default 14d, not plan_freshness.py's internal 7d
- Override guardrail: if `plan_freshness_threshold_days > 14`, drift output emits warning naming the override value and framework default — deviations are visible, not silent
- 2 new tests: framework default 14d active when no header, override-above-default warning

**Test coverage**
- 870 tests passing (up from 859)

## post-alpha hardening (continued) - 2026-03-22

**Drift check hardening (checks 13–16 + threshold visibility)**
- Check #13 `contract_no_placeholders` — fails when contract.yaml still contains `<...>` template tokens
- Check #14 `agents_sections_filled` — fails when governance:key sections in AGENTS.md have no real content; multi-line HTML comment tracking prevents false positives on template blocks
- Check #15 `plan_inventory_current` — warns when plan_section_inventory in baseline no longer matches actual PLAN.md headings; emits `--refresh-baseline` hint
- Check #16 `contract_not_framework_copy` — fails when contract.yaml name matches framework's own contract (catches verbatim copy); skips self when repo_root == framework_root

**PLAN.md path discovery**
- `discover_plan_path()` in `init-governance.sh` scans `PLAN.md`, `governance/`, `memory/`, `docs/` to support non-root PLAN.md repos
- Non-standard path recorded in baseline PROVENANCE layer as `plan_path:`
- `--refresh-baseline` reads `plan_path` from existing baseline to re-hash the correct file

**Framework root portability**
- `GOVERNANCE_FRAMEWORK_ROOT` env var in `repo_root_from_tooling()` — lets repos that vendor a copy of `governance_tools/` point back to the real framework installation; resolution order: env var → `__file__` parent.parent
- 6 tests cover all priority-order cases including empty-string fallback

**Freshness threshold CONTRACT override**
- `plan_freshness_threshold_days` in baseline.yaml CONTRACT layer overrides the staleness threshold for the `plan_freshness` check
- Override source is always labelled in drift output: `contract override: Nd` / `PLAN.md policy: Nd` / `framework default: 7d` — deviations are auditable, not silent
- CONTRACT layer policy documented: only values that affect validation judgments belong there
- 4 tests cover: relaxed threshold passes, tightened threshold fails, warning labels source, no-override uses PLAN.md policy

**Post-adoption drift summary**
- `--adopt-existing` now runs the drift checker inline and prints a filtered `[checks]` + findings summary, so adoption gaps are visible immediately

**Baseline semantic layers**
- `baseline.yaml` now carries four-layer semantic comments: PROVENANCE / INTEGRITY / CONTRACT / OBSERVED

**Test coverage**
- 859 tests passing (up from 835)
- New: `tests/test_framework_versioning.py` (6 tests)
- New drift check tests: +18 tests across checks 13–16 and freshness threshold override

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
