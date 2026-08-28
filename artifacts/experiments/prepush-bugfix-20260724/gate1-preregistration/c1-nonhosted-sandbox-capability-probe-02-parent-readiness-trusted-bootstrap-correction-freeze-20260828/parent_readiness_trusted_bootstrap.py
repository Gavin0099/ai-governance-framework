from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import ModuleType
from typing import Mapping


SCHEMA = "c1-probe02-parent-readiness-trusted-bootstrap-freeze.v1"
FRAMEWORK_BASE = "2615e1da701ac35d4b2f47861ff1546f2c2cae33"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-parent-readiness-trusted-"
    "bootstrap-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/parent-readiness-trusted-bootstrap-manifest.json"
EXPECTED_GIT_PATH = Path("C:/Program Files/Git/cmd/git.exe")
EXPECTED_GIT_BYTES = 46480
EXPECTED_GIT_SHA256 = "3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5"
EXPECTED_PYTHON_PATH = Path("D:/ai-governance-framework/.venv/Scripts/python.exe")
EXPECTED_PYTHON_BYTES = 255320
EXPECTED_PYTHON_SHA256 = "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
REQUIRED_SOURCE_LABELS = {
    "readiness_manifest",
    "journal_manifest",
    "parent_readiness_probe",
    "execution_readiness",
}


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


def _verify_file(path: Path, expected_bytes: int, expected_sha256: str, label: str) -> None:
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or _sha256_file(path) != expected_sha256
    ):
        raise BootstrapError(f"{label} binding mismatch")


def _verify_runtime() -> None:
    _verify_file(EXPECTED_GIT_PATH, EXPECTED_GIT_BYTES, EXPECTED_GIT_SHA256, "Git")
    _verify_file(EXPECTED_PYTHON_PATH, EXPECTED_PYTHON_BYTES, EXPECTED_PYTHON_SHA256, "Python")
    if Path(sys.executable).resolve() != EXPECTED_PYTHON_PATH.resolve():
        raise BootstrapError("executing Python identity mismatch")


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        [
            str(EXPECTED_GIT_PATH),
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo}",
            "-C",
            str(repo),
            *args,
        ],
        input=b"",
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise BootstrapError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _safe_repo_path(raw: str) -> None:
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        not posix.parts
        or posix.is_absolute()
        or windows.drive
        or windows.root
        or "." in posix.parts
        or ".." in posix.parts
        or "." in windows.parts
        or ".." in windows.parts
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
    if value.get("framework_base") != FRAMEWORK_BASE:
        raise BootstrapError("framework base mismatch")
    return value


def _verify_inventory(repo: Path, commit: str, manifest: Mapping[str, object]) -> None:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise BootstrapError("frozen inventory unavailable")
    actual = set(str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"parent-readiness-trusted-bootstrap-manifest.json"}
    executor_sha256: str | None = None
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe_repo_path(path)
        expected.add(path)
        oid, payload = _blob(repo, commit, f"{FREEZE_REPO_DIR}/{path}")
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise BootstrapError(f"frozen binding mismatch: {path}")
        if path == "parent_readiness_trusted_bootstrap.py":
            executor_sha256 = _sha256(payload)
    if actual != expected:
        raise BootstrapError("frozen directory inventory drift")
    if executor_sha256 != manifest.get("frozen_executor_sha256"):
        raise BootstrapError("bootstrap authority mismatch")


def _verify_sources(repo: Path, manifest: Mapping[str, object]) -> Mapping[str, bytes]:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise BootstrapError("source bindings unavailable")
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("source binding invalid")
        label = str(item.get("label"))
        path = str(item.get("path"))
        commit = str(item.get("commit"))
        _safe_repo_path(path)
        oid, payload = _blob(repo, commit, path)
        if (
            commit != FRAMEWORK_BASE
            or oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise BootstrapError(f"source binding mismatch: {label}")
        if label in blobs:
            raise BootstrapError("duplicate source binding")
        blobs[label] = payload
    if set(blobs) != REQUIRED_SOURCE_LABELS:
        raise BootstrapError("source binding label set mismatch")
    return blobs


def _staging_root(repo: Path) -> Path:
    staging = repo.parent / f".{repo.name}.c1-probe02-parent-readiness-bootstrap-staging"
    execution_parent = (
        repo
        / "artifacts/experiments/prepush-bugfix-20260724/gate1-execution"
    ).resolve()
    candidate = staging.resolve()
    try:
        candidate.relative_to(execution_parent)
    except ValueError:
        return candidate
    raise BootstrapError("bootstrap staging entered readiness exact-child boundary")


def _write_exact(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != payload:
        raise BootstrapError("materialized source readback mismatch")


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BootstrapError("verified module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(name, None)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _materialize_and_import(
    repo: Path, sources: Mapping[str, bytes]
) -> tuple[ModuleType, ModuleType, Path]:
    staging = _staging_root(repo)
    if staging.exists():
        raise BootstrapError("bootstrap staging root already exists")
    staging.mkdir()
    try:
        readiness_path = staging / "execution_readiness.py"
        probe_path = staging / "parent_readiness_probe.py"
        _write_exact(readiness_path, sources["execution_readiness"])
        _write_exact(probe_path, sources["parent_readiness_probe"])
        readiness = _load_module("execution_readiness", readiness_path)
        probe = _load_module("c1_verified_parent_readiness_probe", probe_path)
        return probe, readiness, staging
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _remove_staging(staging: Path) -> None:
    shutil.rmtree(staging)
    if staging.exists():
        raise BootstrapError("bootstrap staging cleanup failed")


def execute(*, repo_root: Path, owner_authorized_freeze_commit: str) -> Mapping[str, object]:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise BootstrapError("bootstrap must be streamed from the owner-authorized commit blob")
    if (
        len(owner_authorized_freeze_commit) != 40
        or any(ch not in "0123456789abcdef" for ch in owner_authorized_freeze_commit)
    ):
        raise BootstrapError("owner-authorized commit invalid")
    repo = repo_root.resolve()
    _verify_runtime()
    if str(_git(repo, "rev-parse", "HEAD")) != owner_authorized_freeze_commit:
        raise BootstrapError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, owner_authorized_freeze_commit)
    _verify_inventory(repo, owner_authorized_freeze_commit, manifest)
    sources = _verify_sources(repo, manifest)
    probe: ModuleType | None = None
    readiness: ModuleType | None = None
    staging: Path | None = None
    prior_readiness = sys.modules.get("execution_readiness")
    prior_probe = sys.modules.get("c1_verified_parent_readiness_probe")
    try:
        probe, readiness, staging = _materialize_and_import(repo, sources)
        probe._git = _git
        readiness._git = _git
        _remove_staging(staging)
        staging = None
        receipt = probe.execute(
            repo_root=repo,
            execution_commit=owner_authorized_freeze_commit,
        )
        if not isinstance(receipt, dict) or receipt.get("status") != "PARENT_READINESS_PASSED":
            raise BootstrapError("readiness receipt invalid")
        return receipt
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        for name, prior in (
            ("execution_readiness", prior_readiness),
            ("c1_verified_parent_readiness_probe", prior_probe),
        ):
            sys.modules.pop(name, None)
            if prior is not None:
                sys.modules[name] = prior


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    receipt = execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit.lower(),
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
