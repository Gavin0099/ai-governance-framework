#!/usr/bin/env bash
# Managed tool adapter for the tool-channel mechanism rehearsal.
#
# This is the ONLY sanctioned path from a model session to the workspace
# repository. It accepts a fixed verb set, validates every argument, and
# executes the request inside a container started with --network none,
# --read-only, cap-drop ALL, no-new-privileges, non-root uid 65532.
# It never passes a shell string into the container.
#
# Usage:
#   repo_tool.sh ls              list tracked files
#   repo_tool.sh log             show recent commits
#   repo_tool.sh read <file>     print one tracked file
set -u
export MSYS_NO_PATHCONV=1

CONTAINER="gate2-channel-rehearsal"
LOG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/adapter.log"

log_line() {
  printf '%s verb=%s arg=%s exit=%s out_bytes=%s out_sha256=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$3" "$4" "$5" >>"$LOG"
}

reject() {
  log_line "${1:-<none>}" "${2:-<none>}" "REJECTED" 0 -
  echo "adapter: rejected request (allowed verbs: ls, log, read <file>)" >&2
  exit 2
}

verb="${1:-}"
arg="${2:-}"
[ -n "$verb" ] && [ "$#" -le 2 ] || reject "$verb" "$arg"

case "$verb" in
  ls)   [ -z "$arg" ] || reject "$verb" "$arg"
        set -- git -C /work/repo ls-files ;;
  log)  [ -z "$arg" ] || reject "$verb" "$arg"
        set -- git -C /work/repo log --oneline -5 ;;
  read) [[ "$arg" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || reject "$verb" "$arg"
        [ "$arg" != ".." ] || reject "$verb" "$arg"
        set -- cat "/work/repo/$arg" ;;
  *)    reject "$verb" "$arg" ;;
esac

out="$(docker exec -u 65532:65532 -e HOME=/work -w /work/repo "$CONTAINER" "$@" 2>&1)"
rc=$?
sha="$(printf '%s' "$out" | sha256sum | cut -d' ' -f1)"
log_line "$verb" "${arg:-<none>}" "$rc" "${#out}" "$sha"
printf '%s\n' "$out"
exit "$rc"
