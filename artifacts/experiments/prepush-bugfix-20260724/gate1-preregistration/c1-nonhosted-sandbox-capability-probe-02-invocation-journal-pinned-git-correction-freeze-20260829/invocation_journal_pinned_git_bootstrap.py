from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping, Sequence


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-freeze.v1"
START_SCHEMA = "c1-nonhosted-sandbox-capability-invocation-start.v1"
OUTCOME_SCHEMA = "c1-nonhosted-sandbox-capability-invocation-outcome.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-02"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-invocation-journal-pinned-git-"
    "correction-freeze-20260829"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/invocation-journal-pinned-git-manifest.json"
BOOTSTRAP_NAME = "invocation_journal_pinned_git_bootstrap.py"
EXPECTED_GIT_PATH = Path("C:/Program Files/Git/cmd/git.exe")
EXPECTED_GIT_BYTES = 46480
EXPECTED_GIT_SHA256 = "3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5"
EXPECTED_PYTHON_PATH = Path("D:/ai-governance-framework/.venv/Scripts/python.exe")
EXPECTED_PYTHON_BYTES = 255320
EXPECTED_PYTHON_SHA256 = "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
START_NAME = "start.json"
OUTCOME_NAME = "outcome.json"
HEX = set("0123456789abcdef")


class JournalError(RuntimeError):
    pass


class JournalAlreadyClaimed(JournalError):
    pass


class OutcomePublicationError(JournalError):
    pass


@dataclass(frozen=True)
class ChildResult:
    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes


Launcher = Callable[[Sequence[str], bytes, Path, Mapping[str, str], float], ChildResult]
Publisher = Callable[[Path, str, bytes], Mapping[str, object]]
Clock = Callable[[], str]
GitRunner = Callable[..., subprocess.CompletedProcess[bytes]]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _json_object(payload: bytes, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JournalError(f"invalid JSON: {label}") from exc
    if not isinstance(value, dict):
        raise JournalError(f"JSON object required: {label}")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _verify_file(path: Path, expected_bytes: int, expected_sha256: str, label: str) -> None:
    if (
        not path.is_file()
        or path.stat().st_size != expected_bytes
        or _sha256_file(path) != expected_sha256
    ):
        raise JournalError(f"{label} binding mismatch")


def _verify_runtime() -> None:
    _verify_file(EXPECTED_GIT_PATH, EXPECTED_GIT_BYTES, EXPECTED_GIT_SHA256, "Git")
    _verify_file(EXPECTED_PYTHON_PATH, EXPECTED_PYTHON_BYTES, EXPECTED_PYTHON_SHA256, "Python")
    if Path(sys.executable).resolve() != EXPECTED_PYTHON_PATH.resolve():
        raise JournalError("executing Python identity mismatch")


def _pinned_git_runner(repo: Path) -> GitRunner:
    resolved_repo = repo.resolve()
    expected_prefix = [
        "git",
        "--no-replace-objects",
        "-c",
        f"safe.directory={resolved_repo}",
        "-C",
        str(resolved_repo),
    ]

    def run(
        argv: list[str],
        *,
        input: bytes,
        capture_output: bool,
        check: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[bytes]:
        if not isinstance(argv, list) or argv[:6] != expected_prefix:
            raise JournalError("Git argv prefix mismatch")
        command = argv[6:]
        valid = (
            (len(command) == 2 and command[0] == "rev-parse" and bool(command[1]))
            or (len(command) == 3 and command[:2] == ["cat-file", "blob"] and bool(command[2]))
            or (len(command) == 3 and command[:2] == ["ls-tree", "--name-only"] and bool(command[2]))
        )
        if not valid:
            raise JournalError("Git argv command mismatch")
        if input != b"" or capture_output is not True or check is not False or timeout != 30.0:
            raise JournalError("Git subprocess contract mismatch")
        return subprocess.run(
            [str(EXPECTED_GIT_PATH), *argv[1:]],
            input=input,
            capture_output=capture_output,
            check=check,
            timeout=timeout,
        )

    return run


def _git(
    repo: Path, git_runner: GitRunner, *args: str, binary: bool = False
) -> bytes | str:
    completed = git_runner(
        [
            "git",
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo.resolve()}",
            "-C",
            str(repo.resolve()),
            *args,
        ],
        input=b"",
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if completed.returncode != 0 or completed.stderr:
        raise JournalError("Git binding command failed")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _blob(repo: Path, git_runner: GitRunner, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, git_runner, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, git_runner, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _safe_repo_path(raw: str, label: str) -> PurePosixPath:
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
        raise JournalError(f"unsafe repo path: {label}")
    return posix


def _contained(repo: Path, raw: str, label: str) -> Path:
    anchor = repo.resolve()
    candidate = anchor.joinpath(*_safe_repo_path(raw, label).parts).resolve()
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise JournalError(f"bound path escapes repository: {label}") from exc
    return candidate


def _manifest(repo: Path, git_runner: GitRunner, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, git_runner, commit, MANIFEST_REPO_PATH)
    value = _json_object(payload, "manifest")
    if value.get("schema") != SCHEMA:
        raise JournalError("manifest schema mismatch")
    return value


def _verify_inventory(
    repo: Path, git_runner: GitRunner, commit: str, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise JournalError("frozen inventory unavailable")
    actual = set(
        str(_git(repo, git_runner, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines()
    )
    expected = {"invocation-journal-pinned-git-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise JournalError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe_repo_path(path, "frozen_file")
        expected.add(path)
        oid, payload = _blob(repo, git_runner, commit, f"{FREEZE_REPO_DIR}/{path}")
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise JournalError(f"frozen binding mismatch: {path}")
        blobs[path] = payload
    if actual != expected:
        raise JournalError("frozen directory inventory drift")
    return blobs


def _verify_sources(
    repo: Path, git_runner: GitRunner, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise JournalError("source bindings unavailable")
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise JournalError("source binding invalid")
        label = str(item.get("label"))
        commit = str(item.get("commit"))
        path = str(item.get("path"))
        _safe_repo_path(path, "source_binding")
        oid, payload = _blob(repo, git_runner, commit, path)
        if (
            oid != item.get("git_blob_oid")
            or len(payload) != item.get("bytes")
            or _sha256(payload) != item.get("sha256")
        ):
            raise JournalError(f"source binding mismatch: {label}")
        blobs[label] = payload
    return blobs


def _paths(repo: Path, manifest: Mapping[str, object]) -> Mapping[str, Path]:
    raw = manifest.get("derived_paths")
    if not isinstance(raw, dict):
        raise JournalError("derived paths unavailable")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise JournalError("runtime binding unavailable")
    return {
        "journal": _contained(repo, str(raw["journal_root"]), "journal_root"),
        "journal_anchor": _contained(
            repo, str(raw["journal_parent_anchor"]), "journal_parent_anchor"
        ),
        "output": _contained(repo, str(raw["attempt_output_root"]), "attempt_output_root"),
        "cli": _contained(repo, str(raw["cli_staging_root"]), "cli_staging_root"),
        "private": _contained(repo, str(raw["private_root"]), "private_root"),
        "anchor": _contained(repo, str(raw["parent_anchor"]), "parent_anchor"),
        "python": Path(str(runtime["python_executable"])),
    }


def _verify_prejournal_state(
    repo: Path, git_runner: GitRunner, commit: str, manifest: Mapping[str, object], paths: Mapping[str, Path]
) -> None:
    runtime = manifest["runtime"]
    parent_binding = manifest.get("parent_binding")
    journal_parent_binding = manifest.get("journal_parent_binding")
    assert isinstance(runtime, dict)
    if not isinstance(parent_binding, dict) or not isinstance(journal_parent_binding, dict):
        raise JournalError("parent binding unavailable")
    python = paths["python"]
    if (
        not python.is_file()
        or python.stat().st_size != runtime.get("python_executable_bytes")
        or _sha256_file(python) != runtime.get("python_executable_sha256")
    ):
        raise JournalError("Python binding mismatch")
    derived = manifest["derived_paths"]
    assert isinstance(derived, dict)
    for label, anchor_key, relative_key, binding in (
        ("execution", "anchor", "parent_anchor", parent_binding),
        ("journal", "journal_anchor", "journal_parent_anchor", journal_parent_binding),
    ):
        anchor = paths[anchor_key]
        if (
            not anchor.is_file()
            or anchor.stat().st_size != binding.get("anchor_bytes")
            or _sha256_file(anchor) != binding.get("anchor_sha256")
        ):
            raise JournalError(f"{label} parent anchor binding mismatch")
        anchor_rel = str(derived[relative_key])
        oid = str(_git(repo, git_runner, "rev-parse", f"{commit}:{anchor_rel}"))
        if oid != binding.get("anchor_git_blob_oid"):
            raise JournalError(f"{label} parent anchor Git OID mismatch")
    if paths["output"].parent != paths["anchor"].parent:
        raise JournalError("attempt parent differs from its bound anchor")
    if paths["journal"].parent != paths["journal_anchor"].parent:
        raise JournalError("journal parent differs from its bound anchor")
    if sorted(item.name for item in paths["journal"].parent.iterdir()) != [
        paths["journal_anchor"].name
    ]:
        raise JournalError("journal parent contains unexpected children")
    for key in ("journal", "output", "cli", "private"):
        if paths[key].exists():
            raise JournalError(f"create-once root already exists: {key}")


def _atomic_publish(root: Path, name: str, payload: bytes) -> Mapping[str, object]:
    final = root / name
    staging = root / f".{name}.staging"
    if final.exists() or staging.exists():
        raise JournalError(f"journal file already exists: {name}")
    try:
        with staging.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if staging.read_bytes() != payload:
            raise JournalError(f"journal staging readback mismatch: {name}")
        os.replace(staging, final)
        if final.read_bytes() != payload:
            raise JournalError(f"journal final readback mismatch: {name}")
        return _json_object(payload, name)
    except BaseException:
        if staging.exists():
            try:
                staging.unlink()
            except OSError:
                pass
        raise


def _claim_journal(root: Path) -> None:
    if not root.parent.is_dir():
        raise JournalError("journal parent unavailable")
    try:
        root.mkdir()
    except FileExistsError as exc:
        raise JournalAlreadyClaimed("invocation journal already claimed") from exc


def _start_payload(
    commit: str,
    observed_at_utc: str,
    execution_packet_sha256: str,
    readiness_review_sha256: str,
    bootstrap_sha256: str,
) -> bytes:
    return _canonical(
        {
            "schema": START_SCHEMA,
            "attempt_id": ATTEMPT_ID,
            "execution_commit": commit,
            "execution_authorization_packet_sha256": execution_packet_sha256,
            "readiness_review_sha256": readiness_review_sha256,
            "journal_bootstrap_sha256": bootstrap_sha256,
            "observed_at_utc": observed_at_utc,
            "authority_consumed": True,
            "authority_consumption_event": "START_RECEIPT_VISIBLE_AND_READBACK_EXACT",
            "child_launch_attempted": False,
            "hosted_requests": 0,
            "auth_payloads": 0,
            "qualification_attempts_consumed": 0,
            "randomization_created": False,
        }
    )


def _result_evidence(result: ChildResult | None) -> Mapping[str, object] | None:
    if result is None:
        return None
    return {
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stdout_sha256": _sha256(result.stdout),
        "stderr_sha256": _sha256(result.stderr),
    }


def _child_terminal_evidence(output: Path) -> Mapping[str, object]:
    terminal = output / "terminal.json"
    if not terminal.is_file():
        return {"present": False, "bytes": 0, "sha256": None, "status": None}
    try:
        payload = terminal.read_bytes()
        value = _json_object(payload, "child_terminal")
        return {
            "present": True,
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "status": value.get("status"),
        }
    except (OSError, JournalError):
        return {"present": True, "bytes": None, "sha256": None, "status": None}


def _exception_class(exc: BaseException) -> str:
    value = type(exc).__name__
    return value if value in {
        "JournalError",
        "OSError",
        "PermissionError",
        "SubprocessError",
        "TimeoutExpired",
        "RuntimeError",
        "KeyboardInterrupt",
        "SystemExit",
    } else "OTHER"


def _default_launcher(
    argv: Sequence[str], input_payload: bytes, cwd: Path,
    environment: Mapping[str, str], timeout: float,
) -> ChildResult:
    try:
        completed = subprocess.run(
            list(argv),
            input=input_payload,
            cwd=cwd,
            env=dict(environment),
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        return ChildResult(completed.returncode, False, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return ChildResult(None, True, exc.stdout or b"", exc.stderr or b"")


def inspect_journal(root: Path) -> str:
    if not root.exists():
        return "INVOCATION_NOT_STARTED"
    start = root / START_NAME
    outcome = root / OUTCOME_NAME
    if not start.is_file():
        return "PREAUTHORITY_JOURNAL_AMBIGUOUS"
    try:
        start_value = _json_object(start.read_bytes(), START_NAME)
    except (OSError, JournalError):
        return "INVOCATION_START_INVALID"
    if (
        start_value.get("schema") != START_SCHEMA
        or start_value.get("attempt_id") != ATTEMPT_ID
        or start_value.get("authority_consumed") is not True
    ):
        return "INVOCATION_START_INVALID"
    if not outcome.is_file():
        return "INVOCATION_STARTED_OUTCOME_INCOMPLETE"
    try:
        outcome_value = _json_object(outcome.read_bytes(), OUTCOME_NAME)
    except (OSError, JournalError):
        return "INVOCATION_OUTCOME_INVALID"
    if outcome_value.get("schema") != OUTCOME_SCHEMA:
        return "INVOCATION_OUTCOME_INVALID"
    return str(outcome_value.get("status"))


def run_journaled_child(
    *,
    journal_root: Path,
    child_output_root: Path,
    commit: str,
    execution_packet_sha256: str,
    readiness_review_sha256: str,
    bootstrap_sha256: str,
    child_argv: Sequence[str],
    child_payload: bytes,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: float,
    launcher: Launcher = _default_launcher,
    publisher: Publisher = _atomic_publish,
    clock: Clock = _now,
) -> Mapping[str, object]:
    _claim_journal(journal_root)
    start_payload = _start_payload(
        commit,
        clock(),
        execution_packet_sha256,
        readiness_review_sha256,
        bootstrap_sha256,
    )
    try:
        start = publisher(journal_root, START_NAME, start_payload)
    except BaseException:
        if journal_root.exists() and not any(journal_root.iterdir()):
            try:
                journal_root.rmdir()
            except OSError:
                pass
        raise
    if (
        start.get("authority_consumed") is not True
        or (journal_root / START_NAME).read_bytes() != start_payload
    ):
        raise JournalError("start receipt authority boundary unavailable")

    result: ChildResult | None = None
    exception_class = "NONE"
    status = "INVOCATION_CHILD_LAUNCH_FAILED"
    try:
        result = launcher(child_argv, child_payload, cwd, environment, timeout)
        if result.timed_out:
            status = "INVOCATION_CHILD_TIMEOUT"
        elif result.returncode == 0:
            status = (
                "INVOCATION_CHILD_COMPLETED"
                if (child_output_root / "terminal.json").is_file()
                else "INVOCATION_CHILD_ZERO_WITHOUT_TERMINAL"
            )
        else:
            status = "INVOCATION_CHILD_NONZERO"
    except (OSError, subprocess.SubprocessError) as exc:
        exception_class = _exception_class(exc)
        status = "INVOCATION_CHILD_LAUNCH_FAILED"
    except BaseException as exc:
        exception_class = _exception_class(exc)
        status = "INVOCATION_CHILD_CRASHED"

    outcome_payload = _canonical(
        {
            "schema": OUTCOME_SCHEMA,
            "attempt_id": ATTEMPT_ID,
            "execution_commit": commit,
            "status": status,
            "authority_consumed": True,
            "start_receipt_sha256": _sha256(start_payload),
            "child_launch_attempted": True,
            "child_result": _result_evidence(result),
            "child_terminal": _child_terminal_evidence(child_output_root),
            "exception_class": exception_class,
            "raw_stdout_retained": False,
            "raw_stderr_retained": False,
            "hosted_requests": 0,
            "auth_payloads": 0,
            "qualification_attempts_consumed": 0,
            "randomization_created": False,
        }
    )
    try:
        return publisher(journal_root, OUTCOME_NAME, outcome_payload)
    except BaseException as exc:
        if not (journal_root / START_NAME).is_file():
            raise JournalError("outcome publication failed without durable start") from exc
        raise OutcomePublicationError("outcome publication failed; start receipt remains") from exc


def execute(
    *,
    repo_root: Path,
    owner_authorized_freeze_commit: str,
    owner_authorized_execution_packet_sha256: str,
    owner_authorized_readiness_review_sha256: str,
    launcher: Launcher = _default_launcher,
    publisher: Publisher = _atomic_publish,
    clock: Clock = _now,
) -> Mapping[str, object]:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise JournalError("journal bootstrap must be streamed from the owner-authorized commit blob")
    repo = repo_root.resolve()
    commit = owner_authorized_freeze_commit.lower()
    if len(commit) != 40 or any(char not in HEX for char in commit):
        raise JournalError("owner commit is not a full SHA")
    for label, digest in (
        ("execution packet", owner_authorized_execution_packet_sha256),
        ("readiness review", owner_authorized_readiness_review_sha256),
    ):
        if len(digest) != 64 or any(char not in HEX for char in digest):
            raise JournalError(f"owner-authorized {label} digest invalid")
    _verify_runtime()
    git_runner = _pinned_git_runner(repo)
    if str(_git(repo, git_runner, "rev-parse", "HEAD")) != commit:
        raise JournalError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, git_runner, commit)
    frozen = _verify_inventory(repo, git_runner, commit, manifest)
    sources = _verify_sources(repo, git_runner, manifest)
    if _sha256(frozen[BOOTSTRAP_NAME]) != manifest.get("frozen_executor_sha256"):
        raise JournalError("journal bootstrap authority mismatch")
    paths = _paths(repo, manifest)
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or (
        runtime.get("git_executable") != EXPECTED_GIT_PATH.as_posix()
        or runtime.get("git_executable_bytes") != EXPECTED_GIT_BYTES
        or runtime.get("git_executable_sha256") != EXPECTED_GIT_SHA256
        or runtime.get("python_executable") != EXPECTED_PYTHON_PATH.as_posix()
        or runtime.get("python_executable_bytes") != EXPECTED_PYTHON_BYTES
        or runtime.get("python_executable_sha256") != EXPECTED_PYTHON_SHA256
    ):
        raise JournalError("manifest runtime binding mismatch")
    _verify_prejournal_state(repo, git_runner, commit, manifest, paths)
    child = sources.get("probe02_child_bootstrap")
    if child is None:
        raise JournalError("child bootstrap unavailable")
    python = paths["python"]
    timeout = float(manifest["runtime"]["child_timeout_seconds"])
    child_argv = [
        str(python),
        "-I",
        "-",
        "--repo-root",
        str(repo),
        "--owner-authorized-freeze-commit",
        commit,
        "--owner-authorized-readiness-review-sha256",
        owner_authorized_readiness_review_sha256,
    ]
    environment = dict(os.environ)
    return run_journaled_child(
        journal_root=paths["journal"],
        child_output_root=paths["output"],
        commit=commit,
        execution_packet_sha256=owner_authorized_execution_packet_sha256,
        readiness_review_sha256=owner_authorized_readiness_review_sha256,
        bootstrap_sha256=str(manifest["frozen_executor_sha256"]),
        child_argv=child_argv,
        child_payload=child,
        cwd=repo,
        environment=environment,
        timeout=timeout,
        launcher=launcher,
        publisher=publisher,
        clock=clock,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--owner-authorized-execution-packet-sha256", required=True)
    parser.add_argument("--owner-authorized-readiness-review-sha256", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    outcome = execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
        owner_authorized_execution_packet_sha256=args.owner_authorized_execution_packet_sha256,
        owner_authorized_readiness_review_sha256=args.owner_authorized_readiness_review_sha256,
    )
    print(json.dumps(outcome, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
