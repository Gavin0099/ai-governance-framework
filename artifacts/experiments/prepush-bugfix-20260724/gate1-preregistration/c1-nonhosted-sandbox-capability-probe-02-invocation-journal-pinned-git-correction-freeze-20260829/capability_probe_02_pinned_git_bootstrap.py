from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-readiness-freeze.v1"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-readiness-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-02-manifest.json"
DRIVER_NAME = "capability_probe_02_driver.py"
CORRECTION_SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-freeze.v1"
CORRECTION_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-"
    "correction-freeze-20260829"
)
CORRECTION_MANIFEST_REPO_PATH = (
    f"{CORRECTION_REPO_DIR}/invocation-journal-pinned-git-manifest.json"
)
CORRECTED_DRIVER_NAME = "capability_probe_02_pinned_git_driver.py"
EXPECTED_GIT_PATH = Path("C:/Program Files/Git/mingw64/bin/git.exe")
EXPECTED_GIT_BYTES = 4321168
EXPECTED_GIT_SHA256 = "fc0f1cae1304fcdcf4d0749f421c5ed21471efc856301f92f56d4b844be84363"
EXPECTED_PYTHON_PATH = Path("D:/ai-governance-framework/.venv/Scripts/python.exe")
EXPECTED_PYTHON_BYTES = 255320
EXPECTED_PYTHON_SHA256 = "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
EXPECTED_GIT_COMMON_DIR = Path("D:/ai-governance-framework/.git")
EXPECTED_CHECKOUT_ROOT = Path("C:/Users/daish/.codex/visualizations/2026/08/20/01a01f9a-76de-7b00-8170-409653fa352d/c1-nonhosted-capability-probe-02-execution")
GITFILE_MAX_BYTES = 4096
WORKTREE_COMMONDIR_BYTES = b"../..\n"
REPARSE_POINT = 0x400
INHERITED_ENVIRONMENT_KEYS = (
    "COMSPEC", "PATHEXT", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "WINDIR",
)
FIXED_GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_COUNT": "0",
    "GIT_CONFIG_GLOBAL": "NUL",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "NO_COLOR": "1",
}
GitRunner = Callable[..., subprocess.CompletedProcess[bytes]]


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
    if not path.is_file() or path.stat().st_size != expected_bytes or _sha256_file(path) != expected_sha256:
        raise BootstrapError(f"{label} binding mismatch")


def _verify_runtime() -> None:
    _verify_file(EXPECTED_GIT_PATH, EXPECTED_GIT_BYTES, EXPECTED_GIT_SHA256, "Git")
    _verify_file(EXPECTED_PYTHON_PATH, EXPECTED_PYTHON_BYTES, EXPECTED_PYTHON_SHA256, "Python")
    if Path(sys.executable).resolve() != EXPECTED_PYTHON_PATH.resolve():
        raise BootstrapError("executing Python identity mismatch")


def _pinned_git_environment() -> dict[str, str]:
    environment = {key: value for key in INHERITED_ENVIRONMENT_KEYS if (value := os.environ.get(key))}
    environment.update(FIXED_GIT_ENVIRONMENT)
    return environment


def _pinned_child_environment(driver_sha256: str) -> dict[str, str]:
    environment = {key: value for key in INHERITED_ENVIRONMENT_KEYS if (value := os.environ.get(key))}
    environment.update({"NO_COLOR": "1", "C1_CAPABILITY_EXECUTOR_SHA256": driver_sha256})
    return environment


def _pinned_git_runner(repo: Path) -> GitRunner:
    resolved = repo.resolve()
    prefix = ["git", "--no-replace-objects", "-c", f"safe.directory={resolved}", "-C", str(resolved)]

    def run(argv: list[str], *, input: bytes, capture_output: bool, check: bool, timeout: float) -> subprocess.CompletedProcess[bytes]:
        if not isinstance(argv, list) or argv[:6] != prefix:
            raise BootstrapError("Git argv prefix mismatch")
        command = argv[6:]
        if not (
            (len(command) == 2 and command[0] == "rev-parse" and command[1])
            or (len(command) == 3 and command[:2] == ["cat-file", "blob"] and command[2])
            or (len(command) == 3 and command[:2] == ["ls-tree", "--name-only"] and command[2])
        ):
            raise BootstrapError("Git argv command mismatch")
        if input != b"" or capture_output is not True or check is not False or timeout != 30.0:
            raise BootstrapError("Git subprocess contract mismatch")
        return subprocess.run(
            [str(EXPECTED_GIT_PATH), *argv[1:]], input=input,
            env=_pinned_git_environment(), capture_output=capture_output,
            check=check, timeout=timeout,
        )

    return run


def _is_reparse_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    return bool(getattr(path.lstat(), "st_file_attributes", 0) & REPARSE_POINT)


def _bounded_regular_file(path: Path, label: str, maximum: int = GITFILE_MAX_BYTES) -> bytes:
    if not path.is_file() or _is_reparse_or_symlink(path):
        raise BootstrapError(f"{label} must be a non-reparse regular file")
    payload = path.read_bytes()
    if not payload or len(payload) > maximum:
        raise BootstrapError(f"{label} byte contract mismatch")
    return payload


def _require_nonreparse_directory(path: Path, label: str) -> None:
    if not path.is_dir() or _is_reparse_or_symlink(path):
        raise BootstrapError(f"{label} must be a non-reparse directory")


def _gitfile_target(payload: bytes, label: str) -> Path:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BootstrapError(f"{label} encoding invalid") from exc
    if not text.endswith("\n") or text.count("\n") != 1 or not text.startswith("gitdir: "):
        raise BootstrapError(f"{label} format invalid")
    raw = text[len("gitdir: "):-1]
    if not raw or not PureWindowsPath(raw).is_absolute():
        raise BootstrapError(f"{label} target must be absolute")
    return Path(raw).absolute()


def _absolute_path_record(payload: bytes, label: str) -> Path:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BootstrapError(f"{label} encoding invalid") from exc
    if not text.endswith("\n") or text.count("\n") != 1:
        raise BootstrapError(f"{label} format invalid")
    raw = text[:-1]
    if not raw or not PureWindowsPath(raw).is_absolute():
        raise BootstrapError(f"{label} target must be absolute")
    return Path(raw).absolute()


def _verify_git_directory_identity(repo: Path, git_runner: GitRunner) -> None:
    if repo.absolute() != EXPECTED_CHECKOUT_ROOT.absolute():
        raise BootstrapError("checkout root does not match owner-approved identity")
    _require_nonreparse_directory(repo, "checkout root")
    if repo.resolve() != repo.absolute():
        raise BootstrapError("checkout root resolved identity mismatch")
    repo = repo.absolute()
    dot_git = repo / ".git"
    gitdir = _gitfile_target(_bounded_regular_file(dot_git, "checkout gitfile"), "checkout gitfile")
    common = EXPECTED_GIT_COMMON_DIR.absolute()
    _require_nonreparse_directory(common, "Git common directory")
    if common.resolve() != common:
        raise BootstrapError("Git common directory resolved identity mismatch")
    expected_gitdir = (common / "worktrees" / repo.name).absolute()
    if gitdir != expected_gitdir:
        raise BootstrapError("checkout gitfile target mismatch")
    _require_nonreparse_directory(common / "worktrees", "Git worktrees directory")
    _require_nonreparse_directory(gitdir, "worktree Git directory")
    reverse_path = _absolute_path_record(
        _bounded_regular_file(gitdir / "gitdir", "worktree reverse gitfile"),
        "worktree reverse gitfile",
    )
    if reverse_path != dot_git.absolute():
        raise BootstrapError("worktree reverse gitfile mismatch")
    if _bounded_regular_file(gitdir / "commondir", "worktree commondir") != WORKTREE_COMMONDIR_BYTES:
        raise BootstrapError("worktree commondir bytes mismatch")
    if (gitdir / "../..").resolve() != common:
        raise BootstrapError("Git common directory binding mismatch")
    observed = {
        "toplevel": Path(str(_git(repo, git_runner, "rev-parse", "--show-toplevel"))).resolve(),
        "gitdir": Path(str(_git(repo, git_runner, "rev-parse", "--absolute-git-dir"))).resolve(),
        "common": Path(str(_git(repo, git_runner, "rev-parse", "--git-common-dir"))).resolve(),
    }
    if observed != {"toplevel": repo, "gitdir": gitdir, "common": common}:
        raise BootstrapError("Git directory/worktree identity mismatch")


def _git(repo: Path, git_runner: GitRunner, *args: str, binary: bool = False) -> bytes | str:
    completed = git_runner(
        ["git", "--no-replace-objects", "-c", f"safe.directory={repo.resolve()}", "-C", str(repo.resolve()), *args],
        input=b"", capture_output=True, check=False, timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise BootstrapError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _blob(repo: Path, git_runner: GitRunner, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, git_runner, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, git_runner, "cat-file", "blob", oid, binary=True)
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


def _manifest(repo: Path, git_runner: GitRunner, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, git_runner, commit, MANIFEST_REPO_PATH)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("manifest JSON invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise BootstrapError("manifest schema mismatch")
    return value


def _verify_inventory(repo: Path, git_runner: GitRunner, commit: str, manifest: Mapping[str, object]) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise BootstrapError("frozen inventory unavailable")
    actual = set(str(_git(repo, git_runner, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"capability-probe-02-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe(path)
        expected.add(path)
        oid, payload = _blob(repo, git_runner, commit, f"{FREEZE_REPO_DIR}/{path}")
        if oid != item.get("git_blob_oid") or len(payload) != item.get("bytes") or _sha256(payload) != item.get("sha256"):
            raise BootstrapError(f"frozen binding mismatch: {path}")
        blobs[path] = payload
    if actual != expected:
        raise BootstrapError("frozen directory inventory drift")
    return blobs


def _verify_sources(repo: Path, git_runner: GitRunner, manifest: Mapping[str, object]) -> None:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise BootstrapError("source bindings unavailable")
    for item in entries:
        if not isinstance(item, dict):
            raise BootstrapError("source binding invalid")
        path = str(item.get("path"))
        _safe(path)
        oid, payload = _blob(repo, git_runner, str(item.get("commit")), path)
        if oid != item.get("git_blob_oid") or len(payload) != item.get("bytes") or _sha256(payload) != item.get("sha256"):
            raise BootstrapError(f"source binding mismatch: {item.get('label')}")


def execute(*, repo_root: Path, owner_authorized_freeze_commit: str, owner_authorized_readiness_review_sha256: str) -> int:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise BootstrapError("bootstrap must be streamed from the owner-authorized commit blob")
    repo = repo_root.absolute()
    _verify_runtime()
    git_runner = _pinned_git_runner(repo)
    _verify_git_directory_identity(repo, git_runner)
    repo = repo.resolve()
    if str(_git(repo, git_runner, "rev-parse", "HEAD")) != owner_authorized_freeze_commit:
        raise BootstrapError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, git_runner, owner_authorized_freeze_commit)
    _verify_inventory(repo, git_runner, owner_authorized_freeze_commit, manifest)
    _verify_sources(repo, git_runner, manifest)
    _, correction_payload = _blob(
        repo, git_runner, owner_authorized_freeze_commit, CORRECTION_MANIFEST_REPO_PATH
    )
    correction = json.loads(correction_payload)
    if not isinstance(correction, dict) or correction.get("schema") != CORRECTION_SCHEMA:
        raise BootstrapError("correction manifest schema mismatch")
    _, driver = _blob(
        repo, git_runner, owner_authorized_freeze_commit,
        f"{CORRECTION_REPO_DIR}/{CORRECTED_DRIVER_NAME}",
    )
    if _sha256(driver) != correction.get("frozen_child_driver_sha256"):
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
    if python.resolve() != EXPECTED_PYTHON_PATH.resolve():
        raise BootstrapError("manifest Python identity mismatch")
    environment = _pinned_child_environment(_sha256(driver))
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
