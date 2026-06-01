#!/bin/bash
# push-github.sh
# Pushes to GitHub (origin) with Gavin0099 author identity.
#
# Local branch always stays GavinWu (gitlab-tracking default).
# This script rewrites commits to Gavin0099 in a temp branch,
# pushes that to origin/main, then cleans up — local main is untouched.
#
# Usage: bash scripts/push-github.sh [--force]
#        (--force skips the force-with-lease check; use only if lease fails)

set -euo pipefail

FORCE_FLAG="--force-with-lease"
if [ "${1:-}" = "--force" ]; then
  FORCE_FLAG="--force"
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TEMP="push_github_tmp_$$"
STASHED=0
RESTORED=0

cleanup() {
  if [ "$RESTORED" -eq 0 ]; then
    git checkout "$CURRENT_BRANCH" >/dev/null 2>&1 || true
    git branch -D "$TEMP" >/dev/null 2>&1 || true
    git config user.name "GavinWu"
    git config user.email "Gavin.Wu@genesyslogic.com.tw"
    if [ "$STASHED" -eq 1 ]; then
      git stash pop >/dev/null 2>&1 || true
    fi
    echo "[push-github] cleaned up after error — local $CURRENT_BRANCH unchanged (GavinWu)"
  fi
}
trap cleanup EXIT

# ── Guards ──────────────────────────────────────────────────────────────────

if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "error: must be on main branch (currently: $CURRENT_BRANCH)"
  exit 1
fi

# Auto-stash dirty files (tracked only)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[push-github] stashing local changes..."
  git stash push --quiet
  STASHED=1
fi

# ── Fetch & find divergence point ───────────────────────────────────────────

echo "[push-github] fetching origin/main..."
git fetch origin main --quiet 2>/dev/null || true

BASE="$(git merge-base HEAD origin/main 2>/dev/null)" || {
  BASE="$(git rev-list --max-parents=0 HEAD)"
}
N="$(git rev-list --count "$BASE..HEAD")"

if [ "$N" -eq 0 ]; then
  echo "[push-github] nothing to push — origin/main is already up to date"
  RESTORED=1
  exit 0
fi

echo "[push-github] $N commit(s) to rewrite as Gavin0099..."

# ── Create temp branch and rewrite authors ───────────────────────────────────

git checkout -b "$TEMP" >/dev/null 2>&1

# Set Gavin0099 identity (temp branch has no upstream → pre-commit hook exits early)
git config user.name "Gavin0099"
git config user.email "Gavin0099@users.noreply.github.com"

git rebase "$BASE" \
  --exec "git commit --amend --reset-author --no-edit" \
  >/dev/null 2>&1

# ── Push to GitHub ───────────────────────────────────────────────────────────

echo "[push-github] pushing $(git rev-parse --short HEAD) to origin/main as Gavin0099..."
git push origin "$TEMP:main" $FORCE_FLAG

# ── Restore ──────────────────────────────────────────────────────────────────

RESTORED=1
git checkout "$CURRENT_BRANCH" >/dev/null 2>&1
git branch -D "$TEMP" >/dev/null 2>&1
git config user.name "GavinWu"
git config user.email "Gavin.Wu@genesyslogic.com.tw"
if [ "$STASHED" -eq 1 ]; then
  echo "[push-github] restoring stashed changes..."
  git stash pop --quiet
fi

echo "[push-github] done."
echo "  GitHub: Gavin0099 (origin/main updated)"
echo "  Local:  GavinWu  (unchanged)"
