"""Exercise the evidence query through Bash with read-only GitHub fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "docs/proposals/evidence/query_branch_protection.sh"
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.is_file() else shutil.which("bash")
ABSENT = (404, {"message": "Branch not protected"})
EMPTY = (200, [])
DENIED = (403, {"message": "Resource not accessible by personal access token"})
RULESETS = (200, [{"name": "protect-main", "enforcement": "active"}])
RULES = (200, [{"type": "required_status_checks"}])
CLASSIC = (200, {"enforce_admins": {"enabled": True}})


@pytest.mark.skipif(not BASH, reason="requires Bash")
@pytest.mark.parametrize(
    "admin,classic,rulesets,rules,expected",
    [
        (True, ABSENT, EMPTY, EMPTY, "unprotected_verified"),
        (True, CLASSIC, EMPTY, EMPTY, "protected"),
        (True, DENIED, EMPTY, EMPTY, "unknown_not_verifiable"),
        (False, ABSENT, EMPTY, EMPTY, "unknown_not_verifiable"),
        (True, ABSENT, RULESETS, RULES, "protected"),
        (True, ABSENT, DENIED, DENIED, "unknown_not_verifiable"),
        (True, ABSENT, RULESETS, EMPTY, "unknown_not_verifiable"),
        (True, ABSENT, EMPTY, (200, None), "unknown_not_verifiable"),
        (True, (200, None), EMPTY, EMPTY, "unknown_not_verifiable"),
        (True, (200, b"{bad json"), EMPTY, EMPTY, "unknown_not_verifiable"),
        (True, (200, {"message": "upstream failure"}), EMPTY, EMPTY, "unknown_not_verifiable"),
        (True, CLASSIC, DENIED, DENIED, "protected"),
        (True, DENIED, RULESETS, RULES, "protected"),
        (True, ABSENT, (429, {"message": "rate limited"}), EMPTY, "unknown_not_verifiable"),
        (True, ABSENT, (0, b""), EMPTY, "unknown_not_verifiable"),
        (True, ABSENT, (200, b"{bad json"), EMPTY, "unknown_not_verifiable"),
        (True, ABSENT, (200, [{"enforcement": "evaluate"}]), EMPTY, "unknown_not_verifiable"),
    ],
    ids=[
        "all-protections-absent", "classic-protected", "token-denied",
        "non-admin-404", "ruleset-protected", "rulesets-denied",
        "ruleset-applicability-unknown", "rules-body-invalid",
        "classic-body-null", "classic-body-invalid-json", "classic-error-body",
        "classic-positive-precedes-api-errors", "branch-rules-precede-classic-error",
        "rulesets-rate-limited", "rulesets-no-response", "rulesets-invalid-json",
        "evaluate-ruleset-is-not-positive-evidence",
    ],
)
def test_protection_verdict(tmp_path, admin, classic, rulesets, rules, expected):
    for name, (status, payload) in zip(
        ("classic", "rulesets", "rules"), (classic, rulesets, rules)
    ):
        body = payload.decode("utf-8") if isinstance(payload, bytes) else json.dumps(payload)
        (tmp_path / name).write_text(
            f"HTTP/2.0 {status}\nContent-Type: application/json\n\n{body}\n" if status
            else body,
            encoding="utf-8", newline="\n",
        )
    (tmp_path / "gh").write_text(
        """#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$QUERY_TEST_DIR/calls"
[[ "$1" == api ]] || exit 90
if [[ "$2" == -i ]]; then
  case "$3" in
    */protection) response=classic ;;
    */rulesets) response=rulesets ;;
    */rules/branches/*) response=rules ;;
    *) exit 91 ;;
  esac
  cat "$QUERY_TEST_DIR/$response"
  [[ "$(head -1 "$QUERY_TEST_DIR/$response")" == *200 ]] || exit 1
elif [[ "$2" == user ]]; then
  printf 'reviewer\\n'
elif [[ "$4" == .default_branch ]]; then
  printf 'main\\n'
elif [[ "$4" == .permissions.admin ]]; then
  printf '%s\\n' "$QUERY_TEST_ADMIN"
else
  exit 92
fi
""",
        encoding="utf-8", newline="\n",
    )
    # Use this test interpreter on Windows too, without depending on a python3 alias.
    (tmp_path / "python3").write_text(
        "#!/usr/bin/env bash\nexec "
        + shlex.quote(sys.executable.replace("\\", "/")) + ' "$@"\n',
        encoding="utf-8", newline="\n",
    )
    for name in ("gh", "python3"):
        (tmp_path / name).chmod(0o755)
    env = os.environ.copy()
    env.update(
        PATH=str(tmp_path) + os.pathsep + env.get("PATH", ""),
        OWNER="review", QUERY_TEST_DIR=tmp_path.as_posix(),
        QUERY_TEST_ADMIN=str(admin).lower(),
    )
    result = subprocess.run(
        [BASH, str(SCRIPT), "fixture"], env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["verdict"] == expected
    assert record["repo"] == "review/fixture"
    assert record["permissions_admin"] == admin
    assert record["endpoints"]["rulesets"]["http_status"] == rulesets[0]
    assert record["endpoints"]["rules_branches"]["http_status"] == rules[0]
    assert (tmp_path / "calls").read_text(encoding="utf-8").splitlines() == [
        "api user --jq .login",
        "api repos/review/fixture --jq .default_branch",
        "api repos/review/fixture --jq .permissions.admin",
        "api -i repos/review/fixture/branches/main/protection",
        "api -i repos/review/fixture/rulesets",
        "api -i repos/review/fixture/rules/branches/main",
    ]
