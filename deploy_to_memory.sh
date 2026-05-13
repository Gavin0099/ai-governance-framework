#!/bin/bash
# Deploy ai-governance-framework into a target project workspace.
# Usage:
#   ./deploy_to_memory.sh [target-path]
# If target-path is omitted, deploy to current directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$(pwd)}"

echo "== Deploying AI governance framework =="
echo "Source: $SCRIPT_DIR"
echo "Target: $TARGET"
echo

if [ ! -d "$TARGET" ]; then
  echo "ERROR: target path does not exist: $TARGET"
  exit 1
fi

if [ ! -d "$SCRIPT_DIR/governance" ]; then
  echo "ERROR: governance/ not found in source: $SCRIPT_DIR"
  exit 1
fi

if [ -d "$TARGET/governance" ]; then
  BACKUP="$TARGET/governance_backup_$(date +%Y%m%d_%H%M%S)"
  echo "Backing up existing governance/ to: $BACKUP"
  cp -r "$TARGET/governance" "$BACKUP"
fi

echo "Copying governance/ ..."
cp -r "$SCRIPT_DIR/governance" "$TARGET/"

echo "Copying governance_tools/ ..."
cp -r "$SCRIPT_DIR/governance_tools" "$TARGET/"
chmod +x "$TARGET/governance_tools/"*.py || true

# Workspace-level behavior contract:
# Copy AGENTS.md so adopters get memory/update protocol by default.
if [ -f "$SCRIPT_DIR/AGENTS.md" ]; then
  if [ -f "$TARGET/AGENTS.md" ]; then
    AGENTS_BACKUP="$TARGET/AGENTS_backup_$(date +%Y%m%d_%H%M%S).md"
    echo "Backing up existing AGENTS.md to: $AGENTS_BACKUP"
    cp "$TARGET/AGENTS.md" "$AGENTS_BACKUP"
  fi
  echo "Copying AGENTS.md ..."
  cp "$SCRIPT_DIR/AGENTS.md" "$TARGET/AGENTS.md"
fi

echo "Copying docs/ integration guide ..."
mkdir -p "$TARGET/docs"
if [ -f "$SCRIPT_DIR/docs/INTEGRATION_GUIDE.md" ]; then
  cp "$SCRIPT_DIR/docs/INTEGRATION_GUIDE.md" "$TARGET/docs/"
fi

if [ ! -f "$TARGET/PLAN.md" ]; then
  echo "Creating PLAN.md template ..."
  cat > "$TARGET/PLAN.md" << 'EOF'
# PLAN.md

> Project: [name]
> Owner: [name/team]
> Level: L1 / L2 / L3
> Timeline: [start] ~ [end]

## Scope

- [bounded context 1]
- [bounded context 2]

## Phases

- [ ] Phase A: [goal]
- [ ] Phase B: [goal]

## Current

- Active phase: Phase A
- Next milestone: [milestone]
EOF
else
  echo "PLAN.md already exists; skipped."
fi

echo
echo "Deployment complete."
echo "Next:"
echo "  1) Update $TARGET/PLAN.md"
echo "  2) Run memory check:"
echo "     python $TARGET/governance_tools/memory_janitor.py --check"

