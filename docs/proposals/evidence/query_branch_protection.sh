#!/usr/bin/env bash
# Re-run the branch protection / ruleset evidence query for PR #214 (read-only GET requests).
# Usage: OWNER=Gavin0099 ./query_branch_protection.sh repo1 repo2 ... > out.jsonl
# Requires: gh (authenticated), python3. Emits one JSON object per repo (JSON Lines).
# Output contains no tokens or headers: only status codes and selected response fields.
# NOTE: a 403/404 from an identity WITHOUT admin on the repo means "unknown / not verifiable",
#       not "unprotected". Only a 404 "Branch not protected" seen with permissions.admin=true is
#       evidence of no classic branch protection.
set -euo pipefail
OWNER="${OWNER:-Gavin0099}"
QUERIED_AT="$(TZ=Asia/Taipei date '+%Y-%m-%dT%H:%M:%S+08:00')"
VIEWER="$(gh api user --jq .login)"

call() {  # prints "<http_status>\t<body>" without headers
  local out status body
  out="$(gh api -i "$1" 2>/dev/null || true)"
  status="$(printf '%s\n' "$out" | head -1 | awk '{print $2}')"
  body="$(printf '%s\n' "$out" | awk 'BEGIN{b=0} /^\r?$/{b=1;next} b{print}')"
  printf '%s\t%s' "${status:-000}" "$body"
}

for repo in "$@"; do
  branch="$(gh api "repos/$OWNER/$repo" --jq .default_branch)"
  admin="$(gh api "repos/$OWNER/$repo" --jq .permissions.admin)"
  enc="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$branch")"
  prot="$(call "repos/$OWNER/$repo/branches/$enc/protection")"
  rs="$(call "repos/$OWNER/$repo/rulesets")"
  rb="$(call "repos/$OWNER/$repo/rules/branches/$enc")"
  QUERIED_AT="$QUERIED_AT" VIEWER="$VIEWER" OWNER="$OWNER" REPO="$repo" BRANCH="$branch" ADMIN="$admin" \
  PROT="$prot" RS="$rs" RB="$rb" python3 - <<'PY'
import json, os
def split(v):
    st, _, body = v.partition("\t")
    try: data = json.loads(body) if body.strip() else None
    except ValueError: data = None
    return int(st or 0), data
ps, pd = split(os.environ["PROT"]); rs, rd = split(os.environ["RS"]); bs, bd = split(os.environ["RB"])
prot = {"http_status": ps}
if isinstance(pd, dict) and "message" in pd:
    prot["message"] = pd["message"]
elif isinstance(pd, dict):
    rsc = pd.get("required_status_checks") or {}
    prot.update({"required_status_checks": {"contexts": rsc.get("contexts", []), "strict": rsc.get("strict")},
                 "enforce_admins": (pd.get("enforce_admins") or {}).get("enabled"),
                 "required_pull_request_reviews": pd.get("required_pull_request_reviews") is not None})
admin = os.environ["ADMIN"] == "true"
if ps == 200: verdict = "protected"
elif ps == 404 and admin and prot.get("message") == "Branch not protected": verdict = "unprotected_verified"
else: verdict = "unknown_not_verifiable"
print(json.dumps({
  "queried_at": os.environ["QUERIED_AT"], "viewer": os.environ["VIEWER"],
  "repo": f'{os.environ["OWNER"]}/{os.environ["REPO"]}', "branch": os.environ["BRANCH"],
  "permissions_admin": admin,
  "endpoints": {
    "branch_protection": {"path": f'GET /repos/{os.environ["OWNER"]}/{os.environ["REPO"]}/branches/{{branch}}/protection', **prot},
    "rulesets": {"path": f'GET /repos/{os.environ["OWNER"]}/{os.environ["REPO"]}/rulesets', "http_status": rs,
                 "count": len(rd) if isinstance(rd, list) else None,
                 "names": [r.get("name") for r in rd] if isinstance(rd, list) else None},
    "rules_branches": {"path": f'GET /repos/{os.environ["OWNER"]}/{os.environ["REPO"]}/rules/branches/{{branch}}', "http_status": bs,
                       "rule_types": [r.get("type") for r in bd] if isinstance(bd, list) else None}},
  "verdict": verdict}, ensure_ascii=False))
PY
done
