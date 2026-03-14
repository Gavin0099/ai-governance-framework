#!/usr/bin/env bash
# onboard-external-repo.sh — install governance hooks and emit an external repo readiness report

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(realpath "$SCRIPT_DIR/..")"
INSTALL_SCRIPT="$SCRIPT_DIR/install-hooks.sh"
READINESS_TOOL="$FRAMEWORK_ROOT/governance_tools/external_repo_readiness.py"
PYTHON_LIB="$FRAMEWORK_ROOT/scripts/lib/python.sh"

TARGET_REPO=""
CONTRACT_PATH=""
DRY_RUN=false
NO_HOOK_VERIFY=false
OUTPUT_FORMAT="human"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET_REPO="$2"
            shift 2
            ;;
        --contract)
            CONTRACT_PATH="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-hook-verify)
            NO_HOOK_VERIFY=true
            shift
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        *)
            echo "Usage: bash scripts/onboard-external-repo.sh --target /path/to/repo [--contract /path/to/contract.yaml] [--dry-run] [--no-hook-verify] [--format human|json]"
            exit 1
            ;;
    esac
done

if [ -z "$TARGET_REPO" ]; then
    echo "ERROR: missing --target /path/to/repo"
    exit 1
fi

if [ ! -d "$TARGET_REPO/.git" ]; then
    echo "ERROR: target is not a git repo root: $TARGET_REPO"
    exit 1
fi

echo "== External Repo Onboarding =="
echo "target_repo      = $(realpath "$TARGET_REPO")"
echo "framework_root   = $FRAMEWORK_ROOT"
if [ -n "$CONTRACT_PATH" ]; then
    echo "contract         = $(realpath "$CONTRACT_PATH")"
fi
if [ "$DRY_RUN" = true ]; then
    echo "mode             = dry-run"
else
    echo "mode             = install-and-assess"
fi
echo ""

INSTALL_ARGS=(--target "$TARGET_REPO")
if [ "$DRY_RUN" = true ]; then
    INSTALL_ARGS+=(--dry-run)
fi
if [ "$NO_HOOK_VERIFY" = true ]; then
    INSTALL_ARGS+=(--no-verify)
fi

bash "$INSTALL_SCRIPT" "${INSTALL_ARGS[@]}"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "[dry-run] readiness assessment skipped"
    exit 0
fi

if [ ! -f "$PYTHON_LIB" ] || [ ! -f "$READINESS_TOOL" ]; then
    echo "WARNING: missing readiness tooling, skipping readiness report"
    exit 0
fi

. "$PYTHON_LIB"
if ! set_python_cmd; then
    echo "WARNING: Python not found, skipping readiness report"
    exit 0
fi

READINESS_ARGS=(--repo "$(realpath "$TARGET_REPO")" --format "$OUTPUT_FORMAT")
if [ -n "$CONTRACT_PATH" ]; then
    READINESS_ARGS+=(--contract "$(realpath "$CONTRACT_PATH")")
fi

echo ""
echo "== External Repo Readiness =="
"${PYTHON_CMD[@]}" "$READINESS_TOOL" "${READINESS_ARGS[@]}"
