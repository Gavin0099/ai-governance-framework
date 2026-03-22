#!/usr/bin/env python3
"""
adopt_governance.py — Cross-platform Python equivalent of init-governance.sh.

Designed for Windows users who cannot run bash scripts.

Usage:
    python governance_tools/adopt_governance.py --target /path/to/repo
    python governance_tools/adopt_governance.py --target . --refresh
    python governance_tools/adopt_governance.py --target . --dry-run
    python governance_tools/adopt_governance.py --target . --framework-root /path/to/framework

Modes:
    (default)  adopt-existing: fills governance gaps without overwriting anything
    --refresh  refresh-baseline: recomputes hashes + inventory; no template files copied

What adopt-existing does:
    1. Copies AGENTS.base.md from framework baseline (always; protected file)
    2. Creates AGENTS.md, contract.yaml from template (only if missing)
    3. Creates PLAN.md from template (only if not found in common locations)
    4. Generates .governance/baseline.yaml with hashes + inventory
    5. Runs drift checker inline and prints findings

What adopt-existing does NOT do:
    - Set plan_required_sections (no mandate imposed on existing repos)
    - Overwrite files that already exist
    - Install git hooks (optional; use scripts/install-hooks.sh on Linux/Mac)

What --refresh does:
    1. Reads plan_path and plan_required_sections from existing baseline.yaml
    2. Recomputes sha256 hashes for all tracked files
    3. Re-detects plan_section_inventory from current PLAN.md
    4. Rewrites .governance/baseline.yaml (preserves mandate, updates hashes + inventory)
    5. Runs drift checker inline

What --refresh does NOT do:
    - Copy or overwrite any template files
    - Change plan_required_sections
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.framework_versioning import (
    discover_framework_root,
    repo_root_from_tooling,
)


# ── Plan path discovery ────────────────────────────────────────────────────────

_PLAN_SEARCH_PATHS = ["PLAN.md", "governance/PLAN.md", "memory/PLAN.md", "docs/PLAN.md"]


def _discover_plan_path(repo_root: Path) -> Path | None:
    """Return the first PLAN.md found in standard locations, or None."""
    for rel in _PLAN_SEARCH_PATHS:
        p = repo_root / rel
        if p.exists():
            return p
    return None


# ── File hashing ──────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── PLAN.md heading inventory ─────────────────────────────────────────────────

def _detect_plan_sections(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.startswith("## ")]


# ── Source commit ─────────────────────────────────────────────────────────────

def _git_head_sha(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        sha = result.stdout.strip()
        return sha if len(sha) == 40 else "unknown"
    except Exception:
        return "unknown"


# ── Baseline YAML writer ──────────────────────────────────────────────────────

def _write_baseline_yaml(
    repo_root: Path,
    framework_root: Path,
    plan_rel: str,
    inventory: list[str],
    dry_run: bool,
    plan_required_sections: list[str] | None = None,
) -> None:
    """Generate .governance/baseline.yaml."""
    from governance_tools.framework_versioning import current_framework_release

    gov_dir = repo_root / ".governance"
    baseline_path = gov_dir / "baseline.yaml"

    agents_base = repo_root / "AGENTS.base.md"
    plan_path = repo_root / plan_rel
    contract_path = repo_root / "contract.yaml"
    agents_path = repo_root / "AGENTS.md"

    def _hash_or_zero(p: Path) -> str:
        return _sha256(p) if p.exists() else ("0" * 64)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = _git_head_sha(repo_root)
    baseline_version = "1.0.0"

    plan_path_block = ""
    if plan_rel != "PLAN.md":
        plan_path_block = f"plan_path: {plan_rel}\n"

    inventory_block = ""
    if inventory:
        lines = "".join(f'  - "{s}"\n' for s in inventory)
        inventory_block = f"plan_section_inventory:\n{lines}"

    content = (
        "# .governance/baseline.yaml\n"
        "# Written by governance_tools/adopt_governance.py — do not edit manually.\n"
        "# Verified by: python governance_tools/governance_drift_checker.py --repo .\n"
        "#\n"
        "# Semantic layers in this file:\n"
        "#   PROVENANCE  — who generated this baseline and from which commit\n"
        "#   INTEGRITY   — sha256 hashes + overridability of tracked files\n"
        "#   CONTRACT    — governance mandates that MUST be satisfied (enforced by drift checker)\n"
        "#   OBSERVED    — snapshot of repo structure at adoption time (informational, not enforced)\n"
        "\n"
        "# ── PROVENANCE ────────────────────────────────────────────────────────────────\n"
        f'schema_version: "1"\n'
        f"baseline_version: {baseline_version}\n"
        f"source_commit: {commit}\n"
        f"framework_root: {framework_root}\n"
        f"initialized_at: {now}\n"
        f"initialized_by: governance_tools/adopt_governance.py\n"
        f"{plan_path_block}"
        "\n"
        "# ── INTEGRITY ─────────────────────────────────────────────────────────────────\n"
        "# sha256.<file>: hash recorded at init/refresh time; \"protected\" files are hash-verified\n"
        "# overridable.<file>: protected = must not change | overridable = repo may extend freely\n"
        f"sha256.AGENTS.base.md: {_hash_or_zero(agents_base)}\n"
        f"sha256.PLAN.md: {_hash_or_zero(plan_path)}\n"
        f"sha256.contract.yaml: {_hash_or_zero(contract_path)}\n"
        f"sha256.AGENTS.md: {_hash_or_zero(agents_path)}\n"
        "overridable.AGENTS.base.md: protected\n"
        "overridable.PLAN.md: overridable\n"
        "overridable.contract.yaml: overridable\n"
        "overridable.AGENTS.md: overridable\n"
        "\n"
        "# ── CONTRACT (framework-enforced mandates) ────────────────────────────────────\n"
        "# Fields listed here are actively checked by drift checker; violations block ci/gate.\n"
        "# CONTRACT layer policy: only values that affect validation judgments belong here.\n"
        "#   Do NOT use this layer for metadata, notes, or domain-specific configuration.\n"
        "# plan_required_sections: ## headings that MUST be present in PLAN.md (governance mandate).\n"
        "#   Empty = no mandate enforced (adopt-existing default). Set explicitly to harden.\n"
        "# plan_freshness_threshold_days: CONTRACT OVERRIDE — changes the staleness threshold\n"
        "#   for plan_freshness check. Default: 14d (framework default) or PLAN.md Freshness header.\n"
        "contract_required_fields:\n"
        "  - name\n"
        "  - framework_interface_version\n"
        "  - framework_compatible\n"
        "  - domain\n"
        + (
            "plan_required_sections:\n"
            + "".join(f'  - "{s}"\n' for s in plan_required_sections)
            if plan_required_sections
            else ""
        )
        + "\n"
        "# ── OBSERVED (repo snapshot — informational only, never enforced) ──────────────\n"
        "# plan_section_inventory: ## headings detected in PLAN.md at adoption/refresh time.\n"
        "#   Drift checker surfaces these for visibility but never fails on missing inventory items.\n"
        f"{inventory_block}"
    )

    if dry_run:
        print(f"  [dry-run] Would write: {baseline_path}")
        return

    gov_dir.mkdir(exist_ok=True)
    baseline_path.write_text(content, encoding="utf-8")
    print(f"  Wrote {baseline_path}")


# ── Main adopt logic ──────────────────────────────────────────────────────────

def adopt_existing(
    repo_root: Path,
    framework_root: Path,
    dry_run: bool = False,
) -> int:
    """
    Run the adopt-existing flow. Returns exit code (0 = success, 1 = errors found).
    """
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()
    baseline_source = framework_root / "baselines" / "repo-min"

    print(f"Adopting governance baseline into existing repo: {repo_root}")
    print(f"Baseline source: {baseline_source}")
    print()

    if not (repo_root / ".git").exists():
        print(f"ERROR: {repo_root} is not a git repository (.git not found)")
        return 1

    if not baseline_source.is_dir():
        print(f"ERROR: baseline source not found: {baseline_source}")
        print("  Set --framework-root or GOVERNANCE_FRAMEWORK_ROOT env var to the framework installation.")
        return 1

    # ── Discover PLAN.md ──────────────────────────────────────────────────────
    plan_path = _discover_plan_path(repo_root)
    if plan_path:
        plan_rel = str(plan_path.relative_to(repo_root)).replace("\\", "/")
        if plan_rel != "PLAN.md":
            print(f"  PLAN.md — found at {plan_rel} (non-standard location; plan_path recorded in baseline)")
        else:
            if not dry_run:
                print(f"  PLAN.md — kept as-is (already exists)")
    else:
        plan_rel = "PLAN.md"
        target_plan = repo_root / "PLAN.md"
        if dry_run:
            print(f"  [dry-run] PLAN.md — would copy from template (missing)")
        else:
            import shutil
            shutil.copy2(baseline_source / "PLAN.md", target_plan)
            print(f"  PLAN.md — copied from template (was missing)")
            print(f"  ⚠ Edit PLAN.md: fill in 最後更新, Owner, Freshness fields and section content")

    # ── AGENTS.base.md — always copy (protected) ─────────────────────────────
    target_agents_base = repo_root / "AGENTS.base.md"
    if dry_run:
        print(f"  [dry-run] AGENTS.base.md — would copy (protected baseline, always refreshed)")
    else:
        import shutil
        shutil.copy2(baseline_source / "AGENTS.base.md", target_agents_base)
        print(f"  Copied AGENTS.base.md (protected baseline)")

    # ── Overridable files — copy from template only if missing ────────────────
    for fname in ("AGENTS.md", "contract.yaml"):
        target = repo_root / fname
        if target.exists():
            print(f"  {fname} — kept as-is (already exists)")
        else:
            if dry_run:
                print(f"  [dry-run] {fname} — would copy from template (missing)")
            else:
                import shutil
                shutil.copy2(baseline_source / fname, target)
                print(f"  {fname} — copied from template (was missing)")
                if fname == "contract.yaml":
                    print(f"  ⚠ Edit contract.yaml: replace <repo-name> and <domain> placeholders")

    # ── Detect plan inventory ─────────────────────────────────────────────────
    effective_plan = repo_root / plan_rel
    inventory: list[str] = []
    if effective_plan.exists():
        inventory = _detect_plan_sections(effective_plan.read_text(encoding="utf-8"))
        if inventory:
            print()
            print(f"  plan_section_inventory: {len(inventory)} heading(s) observed in {plan_rel}")
            for s in inventory:
                print(f"    {s}")
            print("  (recorded as inventory; no sections are enforced until you set plan_required_sections)")

    # ── Write baseline.yaml ───────────────────────────────────────────────────
    print()
    _write_baseline_yaml(
        repo_root=repo_root,
        framework_root=framework_root,
        plan_rel=plan_rel,
        inventory=inventory,
        dry_run=dry_run,
    )

    if dry_run:
        print()
        print("Dry-run complete. No files were written.")
        return 0

    # ── Post-adoption drift summary ───────────────────────────────────────────
    print()
    print("─" * 60)
    print("Post-adoption drift check:")
    print("─" * 60)
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(framework_root / "governance_tools" / "governance_drift_checker.py"),
                "--repo", str(repo_root),
                "--framework-root", str(framework_root),
                "--format", "human",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        # Print checks section and any findings
        in_checks = False
        for line in output.splitlines():
            if line.strip().startswith("[checks]"):
                in_checks = True
            if in_checks or line.strip().startswith("FAIL") or line.strip().startswith("WARNING"):
                print(line)
    except Exception as exc:
        print(f"  (drift check failed: {exc})")

    print()
    print("Adoption complete. Next steps:")
    print("  1. Fix any FAIL/warning items shown above")
    print(f"  2. When files change: python governance_tools/adopt_governance.py --target {repo_root} --refresh")
    print(f"  3. Commit: git add AGENTS.base.md AGENTS.md PLAN.md contract.yaml .governance/baseline.yaml")
    print(f"  4. Verify: python governance_tools/governance_drift_checker.py --repo {repo_root}")
    return 0


# ── Baseline reader (for --refresh) ──────────────────────────────────────────

def _read_baseline_state(repo_root: Path) -> dict:
    """Read plan_path and plan_required_sections from existing baseline.yaml.

    Returns a dict with keys:
        plan_rel        str   — relative path to PLAN.md (default: "PLAN.md")
        required        list  — plan_required_sections values (may be empty)
    """
    from governance_tools.domain_contract_loader import _parse_contract_yaml

    baseline_path = repo_root / ".governance" / "baseline.yaml"
    if not baseline_path.exists():
        return {"plan_rel": "PLAN.md", "required": []}

    data = _parse_contract_yaml(baseline_path.read_text(encoding="utf-8"))
    plan_rel = str(data.get("plan_path") or "PLAN.md")

    raw_required = data.get("plan_required_sections")
    if isinstance(raw_required, list):
        required = [str(s) for s in raw_required]
    else:
        required = []

    return {"plan_rel": plan_rel, "required": required}


# ── Refresh baseline ──────────────────────────────────────────────────────────

def refresh_baseline(
    repo_root: Path,
    framework_root: Path,
    dry_run: bool = False,
) -> int:
    """Re-hash tracked files and refresh plan_section_inventory.

    Equivalent to: bash scripts/init-governance.sh --target <repo> --refresh-baseline

    Preserves plan_required_sections from the existing baseline (governance mandate).
    Does NOT copy or overwrite any template files.
    """
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()

    print(f"Refreshing baseline hashes and section inventory: {repo_root}")
    print()

    baseline_path = repo_root / ".governance" / "baseline.yaml"
    if not baseline_path.exists():
        print("ERROR: no .governance/baseline.yaml found")
        print("  Run adopt first: python governance_tools/adopt_governance.py --target .")
        return 1

    # ── Read existing state ───────────────────────────────────────────────────
    state = _read_baseline_state(repo_root)
    plan_rel = state["plan_rel"]
    required = state["required"]

    if required:
        print(f"  Preserved {len(required)} plan_required_sections from existing baseline")

    # ── Re-detect plan inventory ──────────────────────────────────────────────
    plan_path = repo_root / plan_rel
    inventory: list[str] = []
    if plan_path.exists():
        inventory = _detect_plan_sections(plan_path.read_text(encoding="utf-8"))
        if inventory:
            print(f"  plan_section_inventory: {len(inventory)} heading(s) in {plan_rel}")

    if dry_run:
        print()
        print(f"  [dry-run] Would recompute hashes for: AGENTS.base.md AGENTS.md {plan_rel} contract.yaml")
        if required:
            print(f"  [dry-run] plan_required_sections — {len(required)} section(s) preserved")
        print(f"  [dry-run] Would rewrite: {baseline_path}")
        print()
        print("Dry-run complete. No files were written.")
        return 0

    # ── Write refreshed baseline ──────────────────────────────────────────────
    # Build the required_block to re-inject into _write_baseline_yaml content.
    # We do this by writing baseline via the standard writer then appending
    # the plan_required_sections block if it was present before.
    _write_baseline_yaml(
        repo_root=repo_root,
        framework_root=framework_root,
        plan_rel=plan_rel,
        inventory=inventory,
        dry_run=False,
        plan_required_sections=required,
    )

    print()
    print("Refresh complete. Verify with:")
    print(f"  python governance_tools/governance_drift_checker.py --repo {repo_root}")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _resolve_framework_root(target: Path, cli_value: str | None) -> Path:
    """Resolve framework root using the standard priority chain."""
    if cli_value:
        return Path(cli_value).resolve()
    import os
    env_root = os.environ.get("GOVERNANCE_FRAMEWORK_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    discovered = discover_framework_root(target)
    return discovered if discovered else repo_root_from_tooling()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adopt or refresh AI Governance Framework baseline (cross-platform)."
    )
    parser.add_argument("--target", required=True, help="Path to the target repository")
    parser.add_argument("--framework-root", help="Path to framework installation (auto-detected if omitted)")
    parser.add_argument("--refresh", action="store_true",
                        help="Refresh mode: recompute hashes + inventory without copying template files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    framework_root = _resolve_framework_root(target, args.framework_root)

    if args.refresh:
        return refresh_baseline(target, framework_root, dry_run=args.dry_run)
    return adopt_existing(target, framework_root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
