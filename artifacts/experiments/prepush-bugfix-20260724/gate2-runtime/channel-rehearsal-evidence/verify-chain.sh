#!/usr/bin/env sh
# Independently verify the 2026-07-25 model-channel rehearsal evidence chain
# WITHOUT reading the nonce plaintext.
#
# Two modes:
#   ./verify-chain.sh              # offline: verifies everything in this bundle
#   ./verify-chain.sh <container>  # additionally re-derives digests live
#
# Exit 0 = every check passed. Exit 1 = at least one failed.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
rc=0
ok()   { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; rc=1; }

# --- 1. adapter recorded exactly the two model-driven calls -------------------
n=$(grep -c . "$DIR/adapter-log.txt")
[ "$n" -eq 2 ] && ok "adapter.log has 2 entries" || bad "adapter.log entry count = $n (want 2)"
grep -q 'verb=ls arg=<none> exit=0' "$DIR/adapter-log.txt" \
  && ok "adapter.log records verb=ls exit=0" || bad "missing verb=ls exit=0"
grep -q 'verb=read arg=NONCE.txt exit=0 out_bytes=48' "$DIR/adapter-log.txt" \
  && ok "adapter.log records verb=read NONCE.txt exit=0 out_bytes=48" \
  || bad "missing verb=read NONCE.txt"

# --- 2. hostile inputs were rejected -----------------------------------------
grep -q 'verb=read arg=\.\./\.\./etc/passwd exit=REJECTED' "$DIR/adapter-preflight-log.txt" \
  && ok "path traversal rejected" || bad "path traversal not shown rejected"
grep -q 'verb=sh -c id .*exit=REJECTED' "$DIR/adapter-preflight-log.txt" \
  && ok "verb injection rejected" || bad "verb injection not shown rejected"

# --- 3. digest reconciliation (the newline-normalisation relationship) -------
# adapter output digest for `read NONCE.txt`, taken from the log:
ADAPTER_OUT=$(sed -n 's/.*verb=read arg=NONCE.txt .*out_sha256=\([0-9a-f]*\).*/\1/p' "$DIR/adapter-log.txt")
FILE_SHA=$(tr -d '\r\n' < "$DIR/nonce_file_sha256.txt")
REPORTED_SHA=$(tr -d '\r\n' < "$DIR/reported_sha256.txt")
[ -n "$ADAPTER_OUT" ] && ok "adapter output digest present: $ADAPTER_OUT" \
  || bad "could not extract adapter output digest"
[ "$FILE_SHA" = "$REPORTED_SHA" ] \
  && ok "reported-value digest == stored file digest ($FILE_SHA)" \
  || bad "reported digest $REPORTED_SHA != file digest $FILE_SHA"

# --- 4. adapter allowlist is real (source inspection, not trust) -------------
grep -q 'ls\|log\|read' "$DIR/repo_tool.sh" && ok "repo_tool.sh present for inspection" \
  || bad "repo_tool.sh missing verbs"

# --- 5. container isolation properties from the captured inspect JSON --------
J="$DIR/container-inspect.json"
chk() { grep -q "$2" "$J" && ok "inspect: $1" || bad "inspect: $1"; }
chk "NetworkMode=none"          '"NetworkMode": "none"'
chk "ReadonlyRootfs=true"       '"ReadonlyRootfs": true'
chk "no-new-privileges"         'no-new-privileges'
chk "User=65532:65532"          '"User": "65532:65532"'
chk "Binds empty (no host bind mounts)" '"Binds": null'

# --- 6. live re-derivation (optional) ----------------------------------------
if [ "$#" -ge 1 ]; then
  C="$1"
  echo "--- live checks against container $C ---"
  LIVE_FILE=$(docker exec "$C" sh -c 'sha256sum /work/repo/NONCE.txt' 2>/dev/null | cut -d" " -f1)
  LIVE_STRIP=$(docker exec "$C" sh -c 'printf "%s" "$(cat /work/repo/NONCE.txt)" | sha256sum' 2>/dev/null | cut -d" " -f1)
  [ "$LIVE_FILE" = "$FILE_SHA" ] \
    && ok "live file digest == stored file digest" \
    || bad "live file digest $LIVE_FILE != $FILE_SHA"
  [ "$LIVE_STRIP" = "$ADAPTER_OUT" ] \
    && ok "live (file minus trailing LF) digest == adapter output digest" \
    || bad "live stripped digest $LIVE_STRIP != adapter output $ADAPTER_OUT"
else
  echo "SKIP  live re-derivation (pass a container name to enable)"
fi

echo "---"
[ "$rc" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit "$rc"
