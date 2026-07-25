#!/usr/bin/env bash
# Thin wrapper: the sanctioned token-0 the guard resolves and compares against.
# It holds no logic -- all admissibility lives in policy_canary.json and all
# execution in canary_adapter.py -- so there is nothing here to drift.
set -u
export MSYS_NO_PATHCONV=1
# `pwd -W` on git-bash: a Windows-native python cannot open the MSYS `/d/...`
# form, and MSYS_NO_PATHCONV (needed for docker) stops the shell fixing it up.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"
exec "${GATE2_PYTHON:-python}" "$here/canary_adapter.py" "$@"
