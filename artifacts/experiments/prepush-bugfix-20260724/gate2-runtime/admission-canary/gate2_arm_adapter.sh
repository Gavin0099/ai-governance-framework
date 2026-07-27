#!/usr/bin/env bash
# Formal Gate 2 adapter wrapper. It exposes no capability beyond the Python
# adapter and enforces the frozen per-arm call ceiling before dispatch.
set -u
export MSYS_NO_PATHCONV=1
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })"
seq_file="${GATE2_ADAPTER_LOG:?GATE2_ADAPTER_LOG is required}.seq"
limit="${GATE2_MAX_CALLS:-60}"
count=0
if [ -f "$seq_file" ]; then
    count="$(cat "$seq_file" 2>/dev/null || echo 0)"
fi
if [ "$count" -ge "$limit" ]; then
    echo "adapter: frozen call budget exhausted (${count}/${limit})" >&2
    exit 3
fi
exec "${GATE2_PYTHON:-python}" "$here/gate2_arm_adapter.py" "$@"
