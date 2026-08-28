from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Mapping

import execution_readiness as readiness


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-readiness-freeze.v1"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-readiness-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-02-manifest.json"


class ProbeError(RuntimeError):
    pass


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        [
            "git", "--no-replace-objects", "-c", f"safe.directory={repo}",
            "-C", str(repo), *args,
        ],
        input=b"",
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise ProbeError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _manifest(repo: Path, commit: str) -> Mapping[str, object]:
    payload = _git(repo, "show", f"{commit}:{MANIFEST_REPO_PATH}", binary=True)
    assert isinstance(payload, bytes)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError("manifest JSON invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ProbeError("manifest schema mismatch")
    return value


def execute(*, repo_root: Path, execution_commit: str) -> Mapping[str, object]:
    repo = repo_root.resolve()
    if len(execution_commit) != 40 or str(_git(repo, "rev-parse", "HEAD")) != execution_commit:
        raise ProbeError("execution commit does not match checkout HEAD")
    manifest = _manifest(repo, execution_commit)
    readiness.verify_anchor_git_binding(repo, execution_commit, manifest)
    return readiness.run_readiness_probe(
        repo=repo,
        commit=execution_commit,
        manifest=manifest,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--execution-commit", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    receipt = execute(
        repo_root=Path(args.repo_root), execution_commit=args.execution_commit.lower()
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
