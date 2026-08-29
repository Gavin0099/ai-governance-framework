from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-readiness-freeze.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-02"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-readiness-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-02-manifest.json"
DRIVER_NAME = "capability_probe_02_driver.py"
READINESS_NAME = "execution_readiness.py"
CORRECTION_SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-freeze.v1"
CORRECTION_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-"
    "correction-freeze-20260829"
)
CORRECTION_MANIFEST_REPO_PATH = f"{CORRECTION_REPO_DIR}/invocation-journal-pinned-git-manifest.json"
EXPECTED_GIT_PATH = Path("C:/Program Files/Git/cmd/git.exe")
EXPECTED_GIT_BYTES = 46480
EXPECTED_GIT_SHA256 = "3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5"
EXPECTED_GIT_COMMON_DIR = Path("D:/ai-governance-framework/.git")
EXPECTED_CHECKOUT_ROOT = Path("C:/Users/daish/.codex/visualizations/2026/08/20/01a01f9a-76de-7b00-8170-409653fa352d/c1-nonhosted-capability-probe-02-execution")
GITFILE_MAX_BYTES = 4096
WORKTREE_COMMONDIR_BYTES = b"../..\n"
REPARSE_POINT = 0x400
INHERITED_GIT_ENVIRONMENT_KEYS = (
    "COMSPEC", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "WINDIR",
)
FIXED_GIT_ENVIRONMENT = {
    "GIT_ATTR_NOSYSTEM": "1", "GIT_CONFIG_COUNT": "0", "GIT_CONFIG_GLOBAL": "NUL",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0", "NO_COLOR": "1",
}
GitRunner = Callable[..., subprocess.CompletedProcess[bytes]]
HEX = set("0123456789abcdef")


class DriverError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _pinned_git_environment() -> dict[str, str]:
    environment = {key: value for key in INHERITED_GIT_ENVIRONMENT_KEYS if (value := os.environ.get(key))}
    environment.update(FIXED_GIT_ENVIRONMENT)
    return environment


def _pinned_git_runner(repo: Path) -> GitRunner:
    resolved = repo.resolve()
    prefix = ["git", "--no-replace-objects", "-c", f"safe.directory={resolved}", "-C", str(resolved)]

    def run(argv: list[str], *, input: bytes, capture_output: bool, check: bool, timeout: float) -> subprocess.CompletedProcess[bytes]:
        if not isinstance(argv, list) or argv[:6] != prefix:
            raise DriverError("Git argv prefix mismatch")
        command = argv[6:]
        if not (
            (len(command) == 2 and command[0] == "rev-parse" and command[1])
            or (len(command) == 3 and command[:2] == ["cat-file", "blob"] and command[2])
            or (len(command) == 3 and command[:2] == ["ls-tree", "--name-only"] and command[2])
        ):
            raise DriverError("Git argv command mismatch")
        if input != b"" or capture_output is not True or check is not False or timeout not in {15.0, 30.0}:
            raise DriverError("Git subprocess contract mismatch")
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
        raise DriverError(f"{label} must be a non-reparse regular file")
    payload = path.read_bytes()
    if not payload or len(payload) > maximum:
        raise DriverError(f"{label} byte contract mismatch")
    return payload


def _require_nonreparse_directory(path: Path, label: str) -> None:
    if not path.is_dir() or _is_reparse_or_symlink(path):
        raise DriverError(f"{label} must be a non-reparse directory")


def _gitfile_target(payload: bytes, label: str) -> Path:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DriverError(f"{label} encoding invalid") from exc
    if not text.endswith("\n") or text.count("\n") != 1 or not text.startswith("gitdir: "):
        raise DriverError(f"{label} format invalid")
    raw = text[len("gitdir: "):-1]
    if not raw or not PureWindowsPath(raw).is_absolute():
        raise DriverError(f"{label} target must be absolute")
    return Path(raw).absolute()


def _absolute_path_record(payload: bytes, label: str) -> Path:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DriverError(f"{label} encoding invalid") from exc
    if not text.endswith("\n") or text.count("\n") != 1:
        raise DriverError(f"{label} format invalid")
    raw = text[:-1]
    if not raw or not PureWindowsPath(raw).is_absolute():
        raise DriverError(f"{label} target must be absolute")
    return Path(raw).absolute()


def _verify_git_directory_identity(repo: Path, git_runner: GitRunner) -> None:
    if repo.absolute() != EXPECTED_CHECKOUT_ROOT.absolute():
        raise DriverError("checkout root does not match owner-approved identity")
    _require_nonreparse_directory(repo, "checkout root")
    if repo.resolve() != repo.absolute():
        raise DriverError("checkout root resolved identity mismatch")
    repo = repo.absolute()
    dot_git = repo / ".git"
    gitdir = _gitfile_target(_bounded_regular_file(dot_git, "checkout gitfile"), "checkout gitfile")
    common = EXPECTED_GIT_COMMON_DIR.absolute()
    _require_nonreparse_directory(common, "Git common directory")
    if common.resolve() != common:
        raise DriverError("Git common directory resolved identity mismatch")
    expected_gitdir = (common / "worktrees" / repo.name).absolute()
    if gitdir != expected_gitdir:
        raise DriverError("checkout gitfile target mismatch")
    _require_nonreparse_directory(common / "worktrees", "Git worktrees directory")
    _require_nonreparse_directory(gitdir, "worktree Git directory")
    reverse_path = _absolute_path_record(
        _bounded_regular_file(gitdir / "gitdir", "worktree reverse gitfile"),
        "worktree reverse gitfile",
    )
    if reverse_path != dot_git.absolute():
        raise DriverError("worktree reverse gitfile mismatch")
    if _bounded_regular_file(gitdir / "commondir", "worktree commondir") != WORKTREE_COMMONDIR_BYTES:
        raise DriverError("worktree commondir bytes mismatch")
    if (gitdir / "../..").resolve() != common:
        raise DriverError("Git common directory binding mismatch")
    observed = {
        "toplevel": Path(str(_git(repo, git_runner, "rev-parse", "--show-toplevel"))).resolve(),
        "gitdir": Path(str(_git(repo, git_runner, "rev-parse", "--absolute-git-dir"))).resolve(),
        "common": Path(str(_git(repo, git_runner, "rev-parse", "--git-common-dir"))).resolve(),
    }
    if observed != {"toplevel": repo, "gitdir": gitdir, "common": common}:
        raise DriverError("Git directory/worktree identity mismatch")


def _git(repo: Path, git_runner: GitRunner, *args: str, binary: bool = False) -> bytes | str:
    completed = git_runner(
        ["git", "--no-replace-objects", "-c", f"safe.directory={repo.resolve()}", "-C", str(repo.resolve()), *args],
        input=b"", capture_output=True, check=False, timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise DriverError("Git binding command failed")
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
        not posix.parts
        or posix.is_absolute()
        or windows.drive
        or windows.root
        or "." in posix.parts
        or ".." in posix.parts
        or "." in windows.parts
        or ".." in windows.parts
    ):
        raise DriverError("unsafe bound path")


def _manifest(repo: Path, git_runner: GitRunner, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, git_runner, commit, MANIFEST_REPO_PATH)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("manifest JSON invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise DriverError("manifest schema mismatch")
    return value


def _verify_frozen(
    repo: Path, git_runner: GitRunner, commit: str, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise DriverError("frozen inventory unavailable")
    actual = set(str(_git(repo, git_runner, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"capability-probe-02-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise DriverError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe(path)
        expected.add(path)
        oid, payload = _blob(repo, git_runner, commit, f"{FREEZE_REPO_DIR}/{path}")
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise DriverError(f"frozen binding mismatch: {path}")
        blobs[path] = payload
    if actual != expected:
        raise DriverError("frozen directory inventory drift")
    return blobs


def _verify_sources(
    repo: Path, git_runner: GitRunner, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise DriverError("source bindings unavailable")
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise DriverError("source binding invalid")
        label = str(item.get("label"))
        commit = str(item.get("commit"))
        path = str(item.get("path"))
        _safe(path)
        oid, payload = _blob(repo, git_runner, commit, path)
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise DriverError(f"source binding mismatch: {label}")
        blobs[label] = payload
    return blobs


def _module_from_verified_bytes(name: str, payload: bytes, origin: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = origin
    module.__package__ = ""
    sys.modules.pop(name, None)
    try:
        exec(compile(payload, origin, "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    sys.modules[name] = module
    return module


def _load_policy(blobs: Mapping[str, bytes]) -> Mapping[str, object]:
    try:
        value = json.loads(blobs["execution-convergence-policy.json"])
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("convergence policy unavailable") from exc
    if not isinstance(value, dict) or value.get("schema") != "c1-execution-convergence-policy.v1":
        raise DriverError("convergence policy invalid")
    return value


def _terminal_wrapper(engine: types.ModuleType, readiness_digest: str, readiness_receipt: Mapping[str, object], policy: Mapping[str, object], readiness_module: types.ModuleType) -> None:
    original = engine._terminal

    def wrapped(**kwargs: object) -> bytes:
        payload = original(**kwargs)
        value = json.loads(payload)
        negative = value.get("negative_control")
        positive = value.get("positive_control")
        status = value.get("status")
        category = {
            "materialization": "filesystem_projection",
            "cli_preflight": "sandbox_surface",
            "bare_control_launch": "sandbox_surface",
            "bare_control_result": "task_command_resolution",
            "absolute_control_launch": "sandbox_surface",
            "absolute_control_result": "task_command_resolution",
            "marker_read": "probe_artifact",
            "marker_validation": "probe_artifact",
            "cleanup": "cleanup",
        }.get(value.get("failure_stage"))
        evidence = {
            "sandbox_helper_launched": isinstance(negative, dict),
            "negative_control_attempted": isinstance(negative, dict),
            "absolute_python_control_attempted": isinstance(positive, dict),
            "bounded_capability_evidence_present": isinstance(negative, dict) and isinstance(positive, dict),
            "no_new_infrastructure_failure_category": True,
            "infrastructure_failure_category": None if status == "ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE" else category,
        }
        disposition = readiness_module.evaluate_convergence(policy, ATTEMPT_ID, evidence)
        value.update(
            {
                "schema": "c1-nonhosted-sandbox-capability-probe-terminal.v2",
                "readiness_review_sha256": readiness_digest,
                "readiness_receipt_sha256": readiness_receipt.get("receipt_sha256"),
                "intended_surface": evidence,
                "convergence_disposition": disposition,
            }
        )
        return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

    engine._terminal = wrapped


def execute(
    *, repo_root: Path, owner_authorized_freeze_commit: str,
    owner_authorized_readiness_review_sha256: str,
) -> Mapping[str, object]:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise DriverError("driver must be streamed by the authorized bootstrap")
    repo = repo_root.absolute()
    commit = owner_authorized_freeze_commit.lower()
    if len(commit) != 40 or any(char not in HEX for char in commit):
        raise DriverError("owner commit is not a full SHA")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.stat().st_size != EXPECTED_GIT_BYTES or _sha256_file(EXPECTED_GIT_PATH) != EXPECTED_GIT_SHA256:
        raise DriverError("Git binding mismatch")
    git_runner = _pinned_git_runner(repo)
    _verify_git_directory_identity(repo, git_runner)
    repo = repo.resolve()
    if str(_git(repo, git_runner, "rev-parse", "HEAD")) != commit:
        raise DriverError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, git_runner, commit)
    frozen = _verify_frozen(repo, git_runner, commit, manifest)
    sources = _verify_sources(repo, git_runner, manifest)
    _, correction_payload = _blob(repo, git_runner, commit, CORRECTION_MANIFEST_REPO_PATH)
    correction = json.loads(correction_payload)
    if not isinstance(correction, dict) or correction.get("schema") != CORRECTION_SCHEMA:
        raise DriverError("correction manifest schema mismatch")
    expected_driver = str(correction.get("frozen_child_driver_sha256"))
    if os.environ.get("C1_CAPABILITY_EXECUTOR_SHA256") != expected_driver:
        raise DriverError("bootstrap driver authority unavailable")
    readiness_module = _module_from_verified_bytes(
        "c1_probe02_execution_readiness",
        frozen[READINESS_NAME],
        f"<verified-git-blob:{FREEZE_REPO_DIR}/{READINESS_NAME}>",
    )
    readiness_module.verify_anchor_git_binding(
        repo, commit, manifest, git_runner=git_runner
    )
    receipt = readiness_module.validate_reviewed_readiness(
        repo=repo,
        commit=commit,
        manifest=manifest,
        owner_authorized_review_sha256=owner_authorized_readiness_review_sha256,
    )
    engine_payload = sources.get("probe01_executor")
    if engine_payload is None:
        raise DriverError("verified capability engine unavailable")
    engine = _module_from_verified_bytes(
        "c1_probe01_verified_engine", engine_payload, "<verified-git-blob:probe01-executor>"
    )
    def pinned_engine_git(bound_repo: Path, *args: str, binary: bool = False) -> bytes | str:
        if bound_repo.resolve() != repo:
            raise DriverError("capability engine repository binding mismatch")
        return _git(repo, git_runner, *args, binary=binary)

    engine._git = pinned_engine_git
    engine.SCHEMA = SCHEMA
    engine.ATTEMPT_ID = ATTEMPT_ID
    engine.FREEZE_REPO_DIR = FREEZE_REPO_DIR
    engine.MANIFEST_REPO_PATH = MANIFEST_REPO_PATH
    original_verified_frozen = engine._verified_frozen_blobs

    def verified_frozen_with_exact_probe01_surfaces(*args: object, **kwargs: object) -> Mapping[str, bytes]:
        values = dict(original_verified_frozen(*args, **kwargs))
        values[engine.MARKER_NAME] = sources["probe01_marker"]
        values[engine.CONFIG_NAME] = sources["probe01_sandbox_config"]
        values[engine.REQUIREMENTS_NAME] = sources["probe01_sandbox_requirements"]
        return values

    engine._verified_frozen_blobs = verified_frozen_with_exact_probe01_surfaces
    policy = _load_policy(frozen)
    receipt_with_digest = dict(receipt)
    receipt_path = Path(str(manifest["readiness_evidence"]["receipt_path"]))
    receipt_with_digest["receipt_sha256"] = _sha256(receipt_path.read_bytes())
    _terminal_wrapper(
        engine, owner_authorized_readiness_review_sha256,
        receipt_with_digest, policy, readiness_module,
    )
    claim_owned = False
    original_claim = engine._claim_attempt

    def tracked_claim(output: Path) -> None:
        nonlocal claim_owned
        original_claim(output)
        claim_owned = True

    engine._claim_attempt = tracked_claim
    try:
        return engine.execute(
            repo_root=repo,
            owner_authorized_freeze_commit=commit,
        )
    except Exception as exc:
        if not claim_owned:
            raise
        paths = engine._paths(repo, manifest)
        output = paths["output"]
        for root in (paths["private"], paths["cli"]):
            try:
                engine._remove_tree(root)
            except OSError:
                pass
        terminal = output / "terminal.json"
        if terminal.is_file():
            return json.loads(terminal.read_bytes())
        staging = output / ".terminal-staging"
        if staging.exists():
            staging.unlink()
        if any(output.iterdir()):
            raise DriverError("claimed attempt contains unbounded partial evidence") from exc
        payload = engine._terminal(
            status="CAPABILITY_PROBE_AMBIGUOUS",
            commit=commit,
            negative=None,
            positive=None,
            cleanup="COMPLETE" if not paths["private"].exists() and not paths["cli"].exists() else "FAILED",
            diagnostic="bounded post-claim failure",
            failure_stage="materialization",
            exception_class=type(exc).__name__ if type(exc).__name__ in {"OSError", "PermissionError", "ProbeError"} else "OTHER",
        )
        return engine._publish_terminal(output, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--owner-authorized-readiness-review-sha256", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    terminal = execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
        owner_authorized_readiness_review_sha256=args.owner_authorized_readiness_review_sha256,
    )
    print(json.dumps(terminal, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
