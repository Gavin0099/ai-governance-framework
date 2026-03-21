#!/usr/bin/env bash
# init-governance.sh — Scaffold baseline governance files into a target repo.
#
# Usage:
#   bash scripts/init-governance.sh --target /path/to/repo
#   bash scripts/init-governance.sh --target /path/to/repo --upgrade
#   bash scripts/init-governance.sh --target /path/to/repo --dry-run
#
# What it does (initial):
#   1. Copies baselines/repo-min/* into target repo root
#   2. Writes .governance/baseline.yaml with:
#      - baseline_version (from AGENTS.base.md sentinel)
#      - source_commit (git rev-parse HEAD of framework repo)
#      - per-file sha256 hashes
#      - overridability map (protected vs overridable)
#      - initialized_at timestamp
#
# What it does (--upgrade):
#   - Protected files: overwrite silently + update hash
#   - Overridable files: show diff, overwrite only with --auto-merge
#   - Update baseline_version, source_commit, initialized_at
#
# Environment:
#   FRAMEWORK_ROOT  Override auto-detected framework root (default: script dir/..)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="${FRAMEWORK_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASELINE_SOURCE="$FRAMEWORK_ROOT/baselines/repo-min"

# ── Argument Parsing ──────────────────────────────────────────────────────────

TARGET=""
UPGRADE=false
DRY_RUN=false
AUTO_MERGE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)    TARGET="$2"; shift 2 ;;
        --upgrade)   UPGRADE=true; shift ;;
        --dry-run)   DRY_RUN=true; shift ;;
        --auto-merge) AUTO_MERGE=true; shift ;;
        *)           echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "ERROR: --target is required"
    echo "Usage: bash scripts/init-governance.sh --target /path/to/repo [--upgrade] [--dry-run]"
    exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"

if [[ ! -d "$TARGET/.git" ]]; then
    echo "ERROR: $TARGET is not a git repository"
    exit 1
fi

if [[ ! -d "$BASELINE_SOURCE" ]]; then
    echo "ERROR: baseline source not found: $BASELINE_SOURCE"
    exit 1
fi

# ── Helper Functions ──────────────────────────────────────────────────────────

sha256_of() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$file"
    fi
}

read_baseline_version() {
    grep -m1 'baseline_version:' "$BASELINE_SOURCE/AGENTS.base.md" \
        | sed 's/.*baseline_version:[[:space:]]*//' \
        | sed 's/[[:space:]]*-->.*//' \
        | tr -d '[:space:]'
}

source_commit() {
    git -C "$FRAMEWORK_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown"
}

write_baseline_yaml() {
    local target="$1"
    local baseline_version
    baseline_version="$(read_baseline_version)"
    local commit
    commit="$(source_commit)"
    local now
    now="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))')"

    local hash_agents hash_plan hash_contract
    hash_agents="$(sha256_of "$target/AGENTS.base.md")"
    hash_plan="$(sha256_of "$target/PLAN.md")"
    hash_contract="$(sha256_of "$target/contract.yaml")"

    mkdir -p "$target/.governance"
    cat > "$target/.governance/baseline.yaml" <<EOF
# .governance/baseline.yaml
# Written by scripts/init-governance.sh — do not edit manually.
# Verified by: python governance_tools/governance_drift_checker.py --repo .

schema_version: "1"
baseline_version: $baseline_version
source_commit: $commit
framework_root: $FRAMEWORK_ROOT
initialized_at: $now
initialized_by: scripts/init-governance.sh

# SHA256 hashes recorded at init time (prefix: sha256.<filename>)
sha256.AGENTS.base.md: $hash_agents
sha256.PLAN.md: $hash_plan
sha256.contract.yaml: $hash_contract

# Overridability: "protected" = must not change, "overridable" = repo may extend
overridable.AGENTS.base.md: protected
overridable.PLAN.md: overridable
overridable.contract.yaml: overridable

# Required fields in contract.yaml
contract_required_fields:
  - name
  - framework_interface_version
  - framework_compatible
  - domain

# Required sections in PLAN.md (heading text anchors)
plan_required_sections:
  - "## Current Phase"
  - "## Active Sprint"
  - "## Backlog"
EOF
    echo "  Wrote $target/.governance/baseline.yaml"
}

# ── Initial Scaffold ──────────────────────────────────────────────────────────

do_init() {
    echo "Initialising governance baseline in: $TARGET"
    echo "Baseline source: $BASELINE_SOURCE"
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] Would copy:"
        for f in AGENTS.base.md PLAN.md contract.yaml; do
            echo "  $BASELINE_SOURCE/$f -> $TARGET/$f"
        done
        echo "[dry-run] Would write: $TARGET/.governance/baseline.yaml"
        return
    fi

    for f in AGENTS.base.md PLAN.md contract.yaml; do
        cp "$BASELINE_SOURCE/$f" "$TARGET/$f"
        echo "  Copied $f"
    done

    write_baseline_yaml "$TARGET"

    echo ""
    echo "Next steps:"
    echo "  1. Edit $TARGET/PLAN.md — fill in Owner, phases, sprint tasks"
    echo "  2. Edit $TARGET/contract.yaml — replace <repo-name> and <domain>"
    echo "  3. Optionally add AGENTS.md for repo-specific rules (do NOT edit AGENTS.base.md)"
    echo "  4. Commit: git add AGENTS.base.md PLAN.md contract.yaml .governance/baseline.yaml"
    echo "  5. Verify: python governance_tools/governance_drift_checker.py --repo $TARGET"
}

# ── Upgrade ───────────────────────────────────────────────────────────────────

do_upgrade() {
    echo "Upgrading governance baseline in: $TARGET"
    local old_version
    old_version="$(grep 'baseline_version:' "$TARGET/.governance/baseline.yaml" 2>/dev/null | head -1 | awk '{print $2}' || echo '<unknown>')"
    local new_version
    new_version="$(read_baseline_version)"
    echo "  $old_version -> $new_version"
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] Would overwrite (protected): AGENTS.base.md"
        echo "[dry-run] Would diff (overridable): PLAN.md contract.yaml"
        return
    fi

    # Protected files: overwrite silently
    cp "$BASELINE_SOURCE/AGENTS.base.md" "$TARGET/AGENTS.base.md"
    echo "  Overwrote AGENTS.base.md (protected)"

    # Overridable files: show diff, overwrite only if --auto-merge
    for f in PLAN.md contract.yaml; do
        if diff -u "$TARGET/$f" "$BASELINE_SOURCE/$f" > /dev/null 2>&1; then
            echo "  $f unchanged"
        else
            echo ""
            echo "  --- diff for $f (baseline change) ---"
            diff -u "$TARGET/$f" "$BASELINE_SOURCE/$f" || true
            echo "  --- end diff ---"
            if [[ "$AUTO_MERGE" == true ]]; then
                cp "$BASELINE_SOURCE/$f" "$TARGET/$f"
                echo "  Overwrote $f (--auto-merge)"
            else
                echo "  Skipped $f (review diff above, then manually merge or re-run with --auto-merge)"
            fi
        fi
    done

    # Update baseline.yaml with new hashes and version
    write_baseline_yaml "$TARGET"

    echo ""
    echo "Upgrade complete. Verify with:"
    echo "  python governance_tools/governance_drift_checker.py --repo $TARGET"
}

# ── Entry Point ───────────────────────────────────────────────────────────────

if [[ "$UPGRADE" == true ]]; then
    if [[ ! -f "$TARGET/.governance/baseline.yaml" ]]; then
        echo "ERROR: no existing .governance/baseline.yaml found — run without --upgrade first"
        exit 1
    fi
    do_upgrade
else
    if [[ -f "$TARGET/.governance/baseline.yaml" ]] && [[ "$DRY_RUN" == false ]]; then
        echo "WARNING: $TARGET/.governance/baseline.yaml already exists."
        echo "  Re-initialising will overwrite baseline files. Use --upgrade to preserve overridable files."
        read -r -p "  Continue? [y/N] " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    fi
    do_init
fi
