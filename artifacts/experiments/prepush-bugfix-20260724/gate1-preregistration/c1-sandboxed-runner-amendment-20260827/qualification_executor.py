from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Mapping, Sequence

import preflight_adapter
import qualification_contract as contract
import sandboxed_runner as runner


MANIFEST_SCHEMA = "c1-sandboxed-runner-amendment-freeze.v1"
ATTEMPT_ID = "C1-sandboxed-runner-qualification-01"
PROMPT = (
    b"Run exactly: python network_denial_probe.py --output containment-result.json. "
    b"Then return only the JSON object required by output-schema.json. Do not read "
    b"any other file and do not include command output in the response.\n"
)
OUTPUT_SCHEMA = {
    "additionalProperties": False,
    "properties": {"status": {"const": "probe_completed", "type": "string"}},
    "required": ["status"],
    "type": "object",
}


class ExecutorError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ExecutorError("repository root is unavailable")


def _load_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutorError(f"invalid JSON input: {path.name}") from exc
    if not isinstance(value, dict):
        raise ExecutorError(f"JSON input is not an object: {path.name}")
    return value


def _validate_bindings(base: Path, manifest: Mapping[str, object]) -> None:
    frozen = manifest.get("frozen_files")
    if not isinstance(frozen, list):
        raise ExecutorError("frozen file list is unavailable")
    expected_names = {entry["path"] for entry in frozen if isinstance(entry, dict)}
    actual_names = {
        path.relative_to(base).as_posix()
        for path in base.iterdir()
        if path.is_file() and path.name != "amendment-manifest.json"
    }
    if expected_names != actual_names:
        raise ExecutorError("frozen file inventory mismatch")
    for entry in frozen:
        if not isinstance(entry, dict):
            raise ExecutorError("frozen file binding is malformed")
        payload = (base / str(entry["path"])).read_bytes()
        if len(payload) != entry.get("bytes") or _sha256(payload) != entry.get("sha256"):
            raise ExecutorError(f"frozen file binding mismatch: {entry.get('path')}")


def _validate_source_bindings(repo: Path, manifest: Mapping[str, object]) -> None:
    bindings = manifest.get("source_bindings")
    if not isinstance(bindings, list):
        raise ExecutorError("source binding list is unavailable")
    for entry in bindings:
        if not isinstance(entry, dict):
            raise ExecutorError("source binding is malformed")
        commit = str(entry["commit"])
        path = str(entry["path"])
        oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
        if oid != entry.get("git_blob_oid"):
            raise ExecutorError(f"source blob mismatch: {path}")
        payload = _git(repo, "cat-file", "blob", oid, binary=True)
        assert isinstance(payload, bytes)
        if len(payload) != entry.get("bytes") or _sha256(payload) != entry.get("sha256"):
            raise ExecutorError(f"source content mismatch: {path}")


def _validate_authority(repo: Path, owner_commit: str) -> str:
    head = str(_git(repo, "rev-parse", "HEAD"))
    if owner_commit != head:
        raise ExecutorError("owner authority does not match executing freeze commit")
    return head


def _load_legacy_surfaces(repo: Path, manifest: Mapping[str, object]):
    legacy = manifest["legacy_process_containment"]
    if not isinstance(legacy, dict):
        raise ExecutorError("legacy containment binding is unavailable")
    module_path = repo / str(legacy["runner_path"])
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    module = importlib.import_module("gate3_route_v2_codex")

    def launch(
        command: Sequence[str],
        input_bytes: bytes,
        cwd: Path,
        environment: Mapping[str, str],
        timeout_seconds: int,
    ) -> runner.LaunchResult:
        result = module._run_contained(
            list(command),
            input_bytes=input_bytes,
            cwd=cwd,
            env=dict(environment),
            timeout_seconds=timeout_seconds,
        )
        return runner.LaunchResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=result.timed_out,
        )

    return launch, module.route._current_user_only, module.route._verify_current_user_only


def execute_qualification(
    *,
    owner_authorized_freeze_commit: str,
    owner_authorized_machine_policy_receipt_sha256: str,
    cli_executable: Path,
    python_executable: Path,
    auth_file: Path,
    machine_policy_receipt_path: Path,
    output_root: Path,
    launcher=None,
    _state: dict[str, bool] | None = None,
) -> Mapping[str, object]:
    state = _state if _state is not None else {}
    state["hosted_request_attempted"] = False
    base = Path(__file__).resolve().parent
    repo = _repo_root(base)
    manifest = _load_json(base / "amendment-manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ExecutorError("amendment manifest schema mismatch")
    publication = manifest.get("publication")
    if not isinstance(publication, dict):
        raise ExecutorError("publication policy is unavailable")
    expected_root = (repo / str(publication["qualification_output_root"])).resolve()
    if output_root.resolve() != expected_root:
        raise ExecutorError("qualification output root differs from freeze")
    _validate_bindings(base, manifest)
    _validate_source_bindings(repo, manifest)
    freeze_commit = _validate_authority(repo, owner_authorized_freeze_commit)
    if output_root.exists():
        raise ExecutorError("qualification output already exists")
    policy_payload = machine_policy_receipt_path.read_bytes()
    if _sha256(policy_payload) != owner_authorized_machine_policy_receipt_sha256:
        raise ExecutorError("machine policy receipt lacks exact owner authority")
    policy = contract.validate_retained_document(policy_payload)
    config_bytes = (base / "sandbox-config.toml").read_bytes()
    requirements_bytes = (base / "sandbox-requirements.toml").read_bytes()
    contract.validate_machine_policy_receipt(
        policy,
        config_sha256=_sha256(config_bytes),
        requirements_sha256=_sha256(requirements_bytes),
    )
    if _sha256(cli_executable.read_bytes()) != runner.EXPECTED_CLI_SHA256:
        raise ExecutorError("CLI executable differs from freeze")
    if _sha256(python_executable.read_bytes()) != runner.EXPECTED_PYTHON_SHA256:
        raise ExecutorError("Python executable differs from freeze")
    version = subprocess.run(
        [str(cli_executable), "--version"], check=False, capture_output=True, timeout=30
    )
    if version.returncode or version.stderr:
        raise ExecutorError("exact CLI version probe failed")
    preflight_payload = preflight_adapter.build_preflight(
        cli_version_stdout=version.stdout,
        cli_executable=cli_executable,
        python_executable=python_executable,
        runner_path=base / "sandboxed_runner.py",
        config_path=base / "sandbox-config.toml",
        requirements_path=base / "sandbox-requirements.toml",
    )
    private_root = output_root.parent / f".{output_root.name}.{uuid.uuid4().hex}.staging"
    if launcher is None:
        launcher, protect_path, verify_path = _load_legacy_surfaces(repo, manifest)
    else:
        protect_path = lambda path, directory: None
        verify_path = lambda path, directory: None
    run = runner.SandboxedCodexRunner(
        executable=cli_executable,
        python_executable=python_executable,
        private_root=private_root,
        auth_payload=auth_file.read_bytes(),
        config_bytes=config_bytes,
        requirements_bytes=requirements_bytes,
        preflight=json.loads(preflight_payload),
        runner_sha256=_sha256((base / "sandboxed_runner.py").read_bytes()),
        prompt=PROMPT,
        output_schema=OUTPUT_SCHEMA,
        workspace_files={
            "network_denial_probe.py": (base / "network_denial_probe.py").read_bytes()
        },
        launcher=launcher,
        protect_path=protect_path,
        verify_path=verify_path,
        timeout_seconds=300,
    )
    try:
        state["hosted_request_attempted"] = True
        completed = run.run()
        if completed.timed_out or completed.returncode != 0:
            raise ExecutorError("hosted transport or task command did not complete")
        probe_path = private_root / "workspace" / "containment-result.json"
        probe_payload = probe_path.read_bytes()
        probe = contract.validate_retained_document(probe_payload)
        summary = contract.validate_probe_document(probe)
        shutil.rmtree(private_root)
        terminal = contract.build_terminal(
            status="SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED",
            freeze_commit=freeze_commit,
            attempt_id=ATTEMPT_ID,
            hosted_request_attempted=True,
            hosted_transport_completed=True,
            task_command_network_denied=True,
            sandbox_implementation="elevated",
            managed_requirement_enforced=True,
            fallback_observed=False,
            digests={
                "preflight_sha256": _sha256(preflight_payload),
                "probe_sha256": _sha256(probe_payload),
                "stdout_sha256": _sha256(completed.stdout),
                "stderr_sha256": _sha256(completed.stderr),
                "machine_policy_receipt_sha256": _sha256(policy_payload),
            },
            counts={
                "network_applicable": summary.applicable_count,
                "network_denied": summary.denied_count,
                "child_network_denied": int(summary.child_denied),
            },
            cleanup="COMPLETE",
            diagnostic="exact hosted transport completed; task command network classes denied",
        )
        output_root.mkdir(parents=True)
        terminal_path = output_root / "qualification-terminal.json"
        terminal_path.write_bytes(terminal)
        return contract.validate_retained_document(terminal)
    except BaseException:
        if private_root.exists():
            shutil.rmtree(private_root, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--owner-authorized-machine-policy-receipt-sha256", required=True)
    parser.add_argument("--cli-executable", type=Path, required=True)
    parser.add_argument("--python-executable", type=Path, required=True)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--machine-policy-receipt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def _failure_status(exc: BaseException) -> tuple[str, str]:
    message = str(exc).lower()
    if "machine policy" in message or "managed" in message:
        return (
            "SANDBOXED_RUNNER_MANAGED_POLICY_UNAVAILABLE",
            "reviewed machine-policy evidence was unavailable or invalid",
        )
    if "offline sandbox" in message or "fallback" in message:
        return (
            "SANDBOXED_RUNNER_FALLBACK_DETECTED",
            "the exact elevated offline sandbox identity was not established",
        )
    if "network class" in message or "network denial" in message:
        return (
            "SANDBOXED_RUNNER_TASK_NETWORK_REACHABLE",
            "one or more task-command network classes were not denied",
        )
    if "hosted" in message:
        return (
            "SANDBOXED_RUNNER_HOSTED_TRANSPORT_UNAVAILABLE",
            "the bounded hosted transport did not complete",
        )
    if "cleanup" in message:
        return "SANDBOXED_RUNNER_CLEANUP_FAILED", "qualification cleanup failed"
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return "SANDBOXED_RUNNER_PARTIAL_OR_TIMEOUT", "qualification timed out"
    return "SANDBOXED_RUNNER_BINDING_MISMATCH", "qualification precondition failed"


def _publish_authorized_failure(
    *,
    args: argparse.Namespace,
    state: Mapping[str, bool],
    exc: BaseException,
) -> bool:
    base = Path(__file__).resolve().parent
    repo = _repo_root(base)
    manifest = _load_json(base / "amendment-manifest.json")
    publication = manifest.get("publication")
    if not isinstance(publication, dict):
        return False
    expected_root = (repo / str(publication["qualification_output_root"])).resolve()
    try:
        head = str(_git(repo, "rev-parse", "HEAD"))
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False
    if (
        args.output_root.resolve() != expected_root
        or args.owner_authorized_freeze_commit != head
        or expected_root.exists()
    ):
        return False
    staging_prefix = f".{expected_root.name}."
    leftovers = [
        path
        for path in expected_root.parent.glob(f"{staging_prefix}*.staging")
        if path.exists()
    ]
    status, diagnostic = _failure_status(exc)
    cleanup = "FAILED" if leftovers else "COMPLETE"
    if leftovers:
        status = "SANDBOXED_RUNNER_CLEANUP_FAILED"
        diagnostic = "qualification staging cleanup was incomplete"
    terminal = contract.build_terminal(
        status=status,
        freeze_commit=head,
        attempt_id=ATTEMPT_ID,
        hosted_request_attempted=bool(state.get("hosted_request_attempted")),
        hosted_transport_completed=False,
        task_command_network_denied=False,
        sandbox_implementation="unknown",
        managed_requirement_enforced=False,
        fallback_observed=False,
        digests={},
        counts={},
        cleanup=cleanup,
        diagnostic=diagnostic,
    )
    expected_root.mkdir(parents=True)
    (expected_root / "qualification-terminal.json").write_bytes(terminal)
    return True


def main() -> int:
    args = _parser().parse_args()
    state: dict[str, bool] = {}
    try:
        execute_qualification(
            owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
            owner_authorized_machine_policy_receipt_sha256=(
                args.owner_authorized_machine_policy_receipt_sha256
            ),
            cli_executable=args.cli_executable,
            python_executable=args.python_executable,
            auth_file=args.auth_file,
            machine_policy_receipt_path=args.machine_policy_receipt,
            output_root=args.output_root,
            _state=state,
        )
    except BaseException as exc:
        _publish_authorized_failure(args=args, state=state, exc=exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
