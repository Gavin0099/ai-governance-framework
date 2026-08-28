from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping


MANIFEST_SCHEMA = "c1-sandbox-qualification-binding-correction-freeze.v1"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-sandbox-qualification-binding-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/binding-correction-manifest.json"
EXECUTOR_NAME = "qualification_binding_executor.py"


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
        [
            "git",
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo}",
            "-C",
            str(repo),
            *args,
        ],
        check=True,
        capture_output=True,
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _json_object(payload: bytes, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"invalid JSON input: {label}") from exc
    if not isinstance(value, dict):
        raise BootstrapError(f"JSON input is not an object: {label}")
    return value


def _safe_repo_path(raw: str, *, label: str) -> PurePosixPath:
    path = PurePosixPath(raw)
    windows_path = PureWindowsPath(raw)
    if (
        path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or not path.parts
        or ".." in path.parts
        or "." in path.parts
    ):
        raise BootstrapError(f"unsafe bound path: {label}")
    return path


def _contained_repo_path(root: Path, raw: str, *, label: str) -> Path:
    anchor = root.resolve()
    candidate = anchor.joinpath(*_safe_repo_path(raw, label=label).parts).resolve()
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise BootstrapError(f"bound path escapes verified root: {label}") from exc
    return candidate


def _commit_blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _load_manifest(repo: Path, commit: str) -> Mapping[str, object]:
    _, payload = _commit_blob(repo, commit, MANIFEST_REPO_PATH)
    value = _json_object(payload, label="authorized manifest blob")
    if value.get("schema") != MANIFEST_SCHEMA:
        raise BootstrapError("authorized manifest schema mismatch")
    return value


def _verified_frozen_blobs(
    repo: Path, commit: str, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    frozen = manifest.get("frozen_files")
    if not isinstance(frozen, list):
        raise BootstrapError("frozen file list is unavailable")
    expected = {str(entry["path"]) for entry in frozen if isinstance(entry, dict)}
    tree = str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}"))
    actual = {
        line for line in tree.splitlines() if line != "binding-correction-manifest.json"
    }
    if expected != actual:
        raise BootstrapError("authorized frozen file inventory mismatch")
    result: dict[str, bytes] = {}
    for entry in frozen:
        if not isinstance(entry, dict):
            raise BootstrapError("frozen file binding is malformed")
        relative = _safe_repo_path(str(entry["path"]), label="frozen file").as_posix()
        oid, payload = _commit_blob(repo, commit, f"{FREEZE_REPO_DIR}/{relative}")
        if oid != entry.get("git_blob_oid"):
            raise BootstrapError(f"frozen file blob mismatch: {relative}")
        if len(payload) != entry.get("bytes") or _sha256(payload) != entry.get("sha256"):
            raise BootstrapError(f"frozen file content mismatch: {relative}")
        result[relative] = payload
    if EXECUTOR_NAME not in result:
        raise BootstrapError("authorized executor blob is unavailable")
    return result


def _bootstrap_root(repo: Path, manifest: Mapping[str, object]) -> Path:
    paths = manifest.get("derived_paths")
    if not isinstance(paths, dict):
        raise BootstrapError("derived path contract is unavailable")
    raw = paths.get("bootstrap_staging_root")
    if not isinstance(raw, str):
        raise BootstrapError("bootstrap staging root is unavailable")
    return _contained_repo_path(repo, raw, label="bootstrap staging root")


def _materialize(root: Path, blobs: Mapping[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for relative, payload in blobs.items():
        target = _contained_repo_path(root, relative, label="materialized frozen file")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if target.read_bytes() != payload:
            raise BootstrapError(f"materialized frozen file mismatch: {relative}")


def execute(
    *, repo_root: Path, owner_authorized_freeze_commit: str, auth_file: Path
) -> int:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise BootstrapError("bootstrap must be streamed from the authorized commit blob")
    repo = repo_root.resolve()
    top = Path(str(_git(repo, "rev-parse", "--show-toplevel"))).resolve()
    if top != repo:
        raise BootstrapError("repository root differs from bootstrap authority")
    head = str(_git(repo, "rev-parse", "HEAD"))
    if head != owner_authorized_freeze_commit:
        raise BootstrapError("owner authority does not match repository HEAD")
    manifest = _load_manifest(repo, head)
    blobs = _verified_frozen_blobs(repo, head, manifest)
    paths = manifest.get("derived_paths")
    runtime = manifest.get("runtime")
    if not isinstance(paths, dict) or not isinstance(runtime, dict):
        raise BootstrapError("runtime path binding is unavailable")
    python_raw = paths.get("python_executable")
    if not isinstance(python_raw, str):
        raise BootstrapError("Python executable binding is unavailable")
    python_executable = Path(python_raw).resolve()
    if (
        python_executable != Path(sys.executable).resolve()
        or python_executable.stat().st_size != runtime.get("python_executable_bytes")
        or _sha256_file(python_executable) != runtime.get("python_executable_sha256")
    ):
        raise BootstrapError("executing Python differs from authorized runtime")
    staging_root = _bootstrap_root(repo, manifest)
    if staging_root.exists():
        raise BootstrapError("bootstrap staging root already exists")
    try:
        _materialize(staging_root, blobs)
        executor = staging_root / EXECUTOR_NAME
        completed = subprocess.run(
            [
                str(python_executable),
                "-I",
                str(executor),
                "--owner-authorized-freeze-commit",
                head,
                "--auth-file",
                str(auth_file),
            ],
            check=False,
        )
        return completed.returncode
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--auth-file", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    return execute(
        repo_root=args.repo_root,
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
        auth_file=args.auth_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
