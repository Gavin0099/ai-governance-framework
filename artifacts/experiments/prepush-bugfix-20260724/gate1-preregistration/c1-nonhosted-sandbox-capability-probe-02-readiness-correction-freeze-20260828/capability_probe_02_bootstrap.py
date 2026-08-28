from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-readiness-freeze.v1"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-readiness-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-02-manifest.json"
DRIVER_NAME = "capability_probe_02_driver.py"


class BootstrapError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        input=b"", capture_output=True, check=False, timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise BootstrapError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _safe(raw: str) -> None:
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        not posix.parts or posix.is_absolute() or windows.drive or windows.root
        or "." in posix.parts or ".." in posix.parts
        or "." in windows.parts or ".." in windows.parts
    ):
        raise BootstrapError("unsafe bound path")


def _manifest(repo: Path, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, commit, MANIFEST_REPO_PATH)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("manifest JSON invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise BootstrapError("manifest schema mismatch")
    return value


def _verify_inventory(repo: Path, commit: str, manifest: Mapping[str, object]) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise BootstrapError("frozen inventory unavailable")
    actual = set(str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"capability-probe-02-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe(path)
        expected.add(path)
        oid, payload = _blob(repo, commit, f"{FREEZE_REPO_DIR}/{path}")
        if oid != item.get("git_blob_oid") or len(payload) != item.get("bytes") or _sha256(payload) != item.get("sha256"):
            raise BootstrapError(f"frozen binding mismatch: {path}")
        blobs[path] = payload
    if actual != expected:
        raise BootstrapError("frozen directory inventory drift")
    return blobs


def _verify_sources(repo: Path, manifest: Mapping[str, object]) -> None:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise BootstrapError("source bindings unavailable")
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("source binding invalid")
        path = str(item.get("path"))
        _safe(path)
        oid, payload = _blob(repo, str(item.get("commit")), path)
        if oid != item.get("git_blob_oid") or len(payload) != item.get("bytes") or _sha256(payload) != item.get("sha256"):
            raise BootstrapError(f"source binding mismatch: {item.get('label')}")


def execute(*, repo_root: Path, owner_authorized_freeze_commit: str, owner_authorized_readiness_review_sha256: str) -> int:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise BootstrapError("bootstrap must be streamed from the owner-authorized commit blob")
    repo = repo_root.resolve()
    if str(_git(repo, "rev-parse", "HEAD")) != owner_authorized_freeze_commit:
        raise BootstrapError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, owner_authorized_freeze_commit)
    blobs = _verify_inventory(repo, owner_authorized_freeze_commit, manifest)
    _verify_sources(repo, manifest)
    driver = blobs.get(DRIVER_NAME)
    if driver is None or _sha256(driver) != manifest.get("frozen_executor_sha256"):
        raise BootstrapError("driver authority mismatch")
    runtime = manifest.get("runtime")
    paths = manifest.get("derived_paths")
    if not isinstance(runtime, dict) or not isinstance(paths, dict):
        raise BootstrapError("runtime binding unavailable")
    python = Path(str(paths.get("python_executable")))
    if (
        not python.is_file()
        or python.stat().st_size != runtime.get("python_executable_bytes")
        or _sha256_file(python) != runtime.get("python_executable_sha256")
    ):
        raise BootstrapError("Python binding mismatch")
    environment = dict(os.environ)
    environment["C1_CAPABILITY_EXECUTOR_SHA256"] = _sha256(driver)
    completed = subprocess.run(
        [
            str(python), "-I", "-", "--repo-root", str(repo),
            "--owner-authorized-freeze-commit", owner_authorized_freeze_commit,
            "--owner-authorized-readiness-review-sha256", owner_authorized_readiness_review_sha256,
        ],
        input=driver, env=environment, check=False,
    )
    return completed.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--owner-authorized-readiness-review-sha256", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    return execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
        owner_authorized_readiness_review_sha256=args.owner_authorized_readiness_review_sha256,
    )


if __name__ == "__main__":
    raise SystemExit(main())
