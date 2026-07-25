#!/usr/bin/env bash
# Create the disposable gate2-admission-canary workspace container and seed it.
#
# Deliberately NOT the frozen sanitized baseline tree: a dry run that fails
# mid-way must not contaminate or consume a real Gate 2 arm. Nothing from the
# host is mounted -- the repo is streamed in over stdin -- so the container has
# no path back to the framework repo even if the channel were broken.
set -euo pipefail
export MSYS_NO_PATHCONV=1

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="${GATE2_CANARY_CONTAINER:-gate2-admission-canary}"
# Immutable image ID from RUN-RECIPE.md -- never the mutable :pinned tag.
IMG="${GATE2_IMAGE:-sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168}"

docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d --name "$NAME" \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /work:rw,nosuid,uid=65532,gid=65532,size=512m \
  --cap-drop ALL --security-opt no-new-privileges \
  "$IMG" sleep infinity >/dev/null

x() { docker exec -u 65532:65532 -e HOME=/work "$@"; }

x "$NAME" mkdir -p /work/repo /work/out
tar -cf - -C "$HERE/canary-repo" . | docker exec -i -u 65532:65532 -e HOME=/work -w /work/repo "$NAME" tar -xf -

x -w /work/repo "$NAME" git init -q -b main
x -w /work/repo "$NAME" git config user.email canary@localhost
x -w /work/repo "$NAME" git config user.name "Canary Seed"
x -w /work/repo "$NAME" git add -A
x -w /work/repo "$NAME" git commit -q -m "canary baseline (planted defect in src/calc.py)"

echo "container: $NAME"
x -w /work/repo "$NAME" git log --oneline -1
x -w /work/repo "$NAME" git ls-files
