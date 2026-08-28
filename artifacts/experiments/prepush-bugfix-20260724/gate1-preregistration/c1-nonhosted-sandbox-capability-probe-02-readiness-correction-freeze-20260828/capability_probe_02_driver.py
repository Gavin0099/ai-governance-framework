from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping


SCHEMA = "c1-nonhosted-sandbox-capability-probe-02-readiness-freeze.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-02"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-02-readiness-correction-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-02-manifest.json"
DRIVER_NAME = "capability_probe_02_driver.py"
READINESS_NAME = "execution_readiness.py"
HEX = set("0123456789abcdef")


class DriverError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
        raise DriverError("Git binding command failed")
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


def _manifest(repo: Path, commit: str) -> Mapping[str, object]:
    _, payload = _blob(repo, commit, MANIFEST_REPO_PATH)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("manifest JSON invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise DriverError("manifest schema mismatch")
    return value


def _verify_frozen(
    repo: Path, commit: str, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise DriverError("frozen inventory unavailable")
    actual = set(str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}")).splitlines())
    expected = {"capability-probe-02-manifest.json"}
    blobs: dict[str, bytes] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise DriverError("frozen inventory entry invalid")
        path = str(item.get("path"))
        _safe(path)
        expected.add(path)
        oid, payload = _blob(repo, commit, f"{FREEZE_REPO_DIR}/{path}")
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
    repo: Path, manifest: Mapping[str, object]
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
        oid, payload = _blob(repo, commit, path)
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
    repo = repo_root.resolve()
    commit = owner_authorized_freeze_commit.lower()
    if len(commit) != 40 or any(char not in HEX for char in commit):
        raise DriverError("owner commit is not a full SHA")
    if str(_git(repo, "rev-parse", "HEAD")) != commit:
        raise DriverError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, commit)
    frozen = _verify_frozen(repo, commit, manifest)
    sources = _verify_sources(repo, manifest)
    expected_driver = str(manifest.get("frozen_executor_sha256"))
    if os.environ.get("C1_CAPABILITY_EXECUTOR_SHA256") != expected_driver:
        raise DriverError("bootstrap driver authority unavailable")
    readiness_module = _module_from_verified_bytes(
        "c1_probe02_execution_readiness",
        frozen[READINESS_NAME],
        f"<verified-git-blob:{FREEZE_REPO_DIR}/{READINESS_NAME}>",
    )
    readiness_module.verify_anchor_git_binding(repo, commit, manifest)
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
