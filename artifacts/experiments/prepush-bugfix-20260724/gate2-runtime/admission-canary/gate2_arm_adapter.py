#!/usr/bin/env python3
"""Experiment-local producer adapter for the frozen Gate 2 pre-push task.

This deliberately reuses the admitted canary transport and logging machinery,
but adds only two fixed, argument-free mechanics required by the frozen task:

* ``reproduce`` creates a pushed commit with git plumbing while HEAD remains on
  the baseline, feeds that exact ref update to the pre-push hook, and succeeds
  only when the advisory reports the marker file.
* ``commit`` stages only the frozen task's source/test roots, creates one output
  commit, and writes an immutable commit receipt under /work/out.

No arbitrary command or general git surface is exposed to the producer.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import canary_adapter as base


REPRO_INDEX = "/work/gate2-reproduction.index"
REPRO_REF = "refs/heads/gate2-reproduction-pushed"
REMOTE_MAIN = "refs/remotes/origin/main"
MARKER_PATH = "gate2-pushed-ref-marker.txt"
COMMIT_RECEIPT = "/work/out/producer-receipt.json"
COMMIT_ROOTS = ["governance_tools", "scripts/hooks", "tests"]
PYTEST_PAYLOAD = "/work/vendor/offline-pytest.zip"
INPUT_ROOT = "/work/input"


def _run(argv: list[str], stdin: bytes | None = None) -> tuple[int, str]:
    return base.docker(argv, stdin=stdin)


def _require_ok(
    label: str,
    result: tuple[int, str],
) -> tuple[str | None, tuple[int, str] | None]:
    rc, output = result
    if rc != 0:
        return None, (rc, f"{label} failed:\n{output}")
    value = output.strip()
    if not value:
        return None, (3, f"{label} returned no value")
    return value.splitlines()[-1].strip(), None


def reproduce(_args: list[str]) -> tuple[int, str]:
    """Exercise the frozen pushed-ref symptom with no worktree checkout."""
    _run(["rm", "-f", REPRO_INDEX])

    head, error = _require_ok("read baseline HEAD", _run(["git", "rev-parse", "HEAD"]))
    if error:
        return error
    assert head is not None

    rc, output = _run(["git", "update-ref", REMOTE_MAIN, head])
    if rc != 0:
        return rc, f"seed remote main failed:\n{output}"
    rc, output = _run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", REMOTE_MAIN]
    )
    if rc != 0:
        return rc, f"seed remote default branch failed:\n{output}"

    blob, error = _require_ok(
        "write reproduction marker blob",
        _run(["git", "hash-object", "-w", "--stdin"],
             stdin=b"gate2 pushed-ref reproduction\n"),
    )
    if error:
        return error
    assert blob is not None

    env_git = ["env", f"GIT_INDEX_FILE={REPRO_INDEX}", "git"]
    for label, argv in (
        ("read baseline tree", env_git + ["read-tree", head]),
        (
            "stage reproduction marker",
            env_git
            + ["update-index", "--add", "--cacheinfo", "100644", blob, MARKER_PATH],
        ),
    ):
        rc, output = _run(argv)
        if rc != 0:
            return rc, f"{label} failed:\n{output}"

    tree, error = _require_ok(
        "write reproduction tree", _run(env_git + ["write-tree"])
    )
    if error:
        return error
    assert tree is not None

    pushed, error = _require_ok(
        "create reproduction commit",
        _run(["git", "commit-tree", tree, "-p", head, "-m",
              "Gate 2 pushed-ref reproduction"]),
    )
    if error:
        return error
    assert pushed is not None

    rc, output = _run(["git", "update-ref", REPRO_REF, pushed])
    if rc != 0:
        return rc, f"update reproduction ref failed:\n{output}"

    push_line = (
        f"{REPRO_REF} {pushed} refs/heads/main {head}\n".encode("utf-8")
    )
    rc, hook_output = _run(
        ["bash", f"{base.REPO}/scripts/hooks/pre-push",
         "origin", "/work/gate2-reproduction-remote"],
        stdin=push_line,
    )
    observed = (
        rc == 0
        and "changed_files=1" in hook_output
        and MARKER_PATH in hook_output
    )
    verdict = {
        "changed_files_one": "changed_files=1" in hook_output,
        "head_unchanged": True,
        "marker_reported": MARKER_PATH in hook_output,
        "pushed_commit": pushed,
        "remote_base": head,
        "verdict": "PASS" if observed else "FAIL",
    }
    return (0 if observed else 1), (
        hook_output.rstrip("\r\n")
        + "\n[gate2_reproduction]\n"
        + json.dumps(verdict, sort_keys=True)
    )


def _load_json_object(payload: str, label: str) -> dict[str, Any] | None:
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def commit_output(_args: list[str]) -> tuple[int, str]:
    """Create exactly one output commit and persist its attested receipt."""
    exists_rc, exists_output = _run(["test", "-e", COMMIT_RECEIPT])
    if exists_rc == 0:
        return 3, "adapter: output commit already exists"
    if exists_rc != 1:
        return exists_rc, f"commit receipt preflight failed:\n{exists_output}"

    rc, output = _run(["git", "add", "-A", "--", *COMMIT_ROOTS])
    if rc != 0:
        return rc, f"stage output failed:\n{output}"

    staged_rc, _ = _run(["git", "diff", "--cached", "--quiet"])
    if staged_rc == 0:
        return 3, "adapter: no in-scope staged change to commit"
    if staged_rc != 1:
        return staged_rc, "adapter: could not inspect staged output"

    rc, output = _run(["git", "commit", "-m", "Gate 2 producer output"])
    if rc != 0:
        return rc, f"output commit failed:\n{output}"

    head, error = _require_ok("read output commit", _run(["git", "rev-parse", "HEAD"]))
    if error:
        return error
    tree, error = _require_ok(
        "read output tree", _run(["git", "rev-parse", "HEAD^{tree}"])
    )
    if error:
        return error
    assert head is not None and tree is not None

    rc, changed_output = _run(
        ["git", "diff", "--name-only", "HEAD~1...HEAD"]
    )
    if rc != 0:
        return rc, f"read committed paths failed:\n{changed_output}"
    changed_files = [
        line.strip() for line in changed_output.splitlines() if line.strip()
    ]

    rc, status_output = _run(["git", "status", "--porcelain"])
    if rc != 0:
        return rc, f"read post-commit status failed:\n{status_output}"
    if status_output.strip():
        return 3, f"adapter: worktree is not clean after commit:\n{status_output}"

    receipt = {
        "changed_files": changed_files,
        "linked_commit": head,
        "status_clean": True,
        "tree": tree,
    }
    blob = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    rc, output = _run(["cp", "/dev/stdin", COMMIT_RECEIPT], stdin=blob)
    if rc != 0:
        return rc, f"write commit receipt failed:\n{output}"
    return 0, json.dumps(receipt, sort_keys=True)


def run_tests(_args: list[str]) -> tuple[int, str]:
    return _run(
        [
            "env",
            "PYTHONDONTWRITEBYTECODE=1",
            f"PYTHONPATH={PYTEST_PAYLOAD}:{base.REPO}",
            "python",
            "-m",
            "pytest",
            "-q",
            "tests",
        ]
    )


def read_file(args: list[str]) -> tuple[int, str]:
    relative = args[0]
    target = (
        f"{INPUT_ROOT}/{relative.removeprefix('input/')}"
        if relative.startswith("input/")
        else f"{base.REPO}/{relative}"
    )
    return _run(["cat", target])


def run_validators(_args: list[str]) -> tuple[int, str]:
    commands = (
        (
            "shellcheck",
            ["shellcheck", "--shell=bash", "--severity=style",
             "scripts/hooks/pre-push"],
        ),
        (
            "ruff",
            [
                "ruff", "check", "--no-cache", "--line-length", "100",
                "--target-version", "py312", "--select", "E,F,W,I,B",
                "governance_tools/version_bump_guard.py",
            ],
        ),
        (
            "mypy",
            [
                "mypy", "--no-incremental", "--python-version", "3.12",
                "--warn-unused-ignores", "--warn-return-any",
                "--no-implicit-optional",
                "governance_tools/version_bump_guard.py",
            ],
        ),
    )
    rendered: list[str] = []
    for label, argv in commands:
        rc, output = _run(argv)
        rendered.extend((f"[{label} exit={rc}]", output.rstrip("\r\n")))
    return 0, "\n".join(rendered)


base.EXEC = {
    **base.EXEC,
    "read": (1, read_file),
    "test": (0, run_tests),
    "reproduce": (0, reproduce),
    "commit": (0, commit_output),
}
if os.environ.get("GATE2_TREATMENT_VALIDATORS") == "1":
    base.EXEC["validate"] = (0, run_validators)


if __name__ == "__main__":
    sys.exit(base.main(sys.argv[1:]))
