from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence


MANIFEST_SCHEMA = "c1-sandbox-qualification-prerun-freeze.v1"
ATTEMPT_ID = "C1-sandboxed-runner-qualification-01"
EXPECTED_CLI_SHA256 = "f29f609375f3731d8db507a95124862a84e306982e30ba4300ddce5638bc6946"
EXPECTED_CLI_BYTES = 295_151_920
EXPECTED_PYTHON_SHA256 = "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
EXPECTED_PYTHON_BYTES = 255_320
EXPECTED_POLICY_SHA256 = "9aa1f17cc4a36a3ac502862eb42d84044799eaf1b4de7c8cb1e31a25b10c3440"
EXPECTED_RECEIPT_SHA256 = "23b297983d68898885f49131f912518f96d3d580244ed9484d0fef6395132ffd"
EXPECTED_VERSION_STDOUT_SHA256 = "867f4045c33a719c57ed0fc3751a5d9de8dbdb78494a64f43a73ca5c76ef71c5"
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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


def _validate_frozen_files(base: Path, manifest: Mapping[str, object]) -> None:
    frozen = manifest.get("frozen_files")
    if not isinstance(frozen, list):
        raise ExecutorError("frozen file list is unavailable")
    expected = {str(entry["path"]) for entry in frozen if isinstance(entry, dict)}
    actual = {
        path.relative_to(base).as_posix()
        for path in base.iterdir()
        if path.is_file() and path.name != "qualification-prerun-manifest.json"
    }
    if expected != actual:
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


def _derived_paths(repo: Path, manifest: Mapping[str, object]) -> Mapping[str, Path]:
    paths = manifest.get("derived_paths")
    if not isinstance(paths, dict):
        raise ExecutorError("derived path policy is unavailable")
    relative_keys = ("qualification_output_root", "cli_staging_root")
    result: dict[str, Path] = {}
    for key in relative_keys:
        raw = Path(str(paths[key]))
        if raw.is_absolute() or ".." in raw.parts:
            raise ExecutorError(f"derived repo path is unsafe: {key}")
        result[key] = (repo / raw).resolve()
    final_root = result["qualification_output_root"]
    staging_root = result["cli_staging_root"]
    if final_root.parent != staging_root.parent:
        raise ExecutorError("qualification and staging roots do not share a frozen parent")
    for key in ("installed_cli_source", "live_machine_policy", "python_executable"):
        value = Path(str(paths[key]))
        if not value.is_absolute() or ".." in value.parts:
            raise ExecutorError(f"derived machine path is unsafe: {key}")
        result[key] = value
    return result


def _raw_copy_exact(source: Path, target: Path) -> None:
    if source.stat().st_size != EXPECTED_CLI_BYTES or _sha256_file(source) != EXPECTED_CLI_SHA256:
        raise ExecutorError("installed exact CLI source differs from freeze")
    target.parent.mkdir(parents=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=8 * 1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())
    if target.stat().st_size != EXPECTED_CLI_BYTES or _sha256_file(target) != EXPECTED_CLI_SHA256:
        raise ExecutorError("staged exact CLI differs from freeze")


def _load_surfaces(repo: Path, manifest: Mapping[str, object]):
    source = manifest.get("sandboxed_runner_source")
    if not isinstance(source, dict):
        raise ExecutorError("sandboxed runner source is unavailable")
    base = repo / str(source["directory"])
    legacy_dir = repo / str(source["legacy_directory"])
    for module_path in (str(base), str(legacy_dir)):
        if module_path not in sys.path:
            sys.path.insert(0, module_path)
    runner = importlib.import_module("sandboxed_runner")
    adapter = importlib.import_module("preflight_adapter")
    contract = importlib.import_module("qualification_contract")
    legacy_module = importlib.import_module("gate3_route_v2_codex")

    def launch(
        command: Sequence[str],
        input_bytes: bytes,
        cwd: Path,
        environment: Mapping[str, str],
        timeout_seconds: int,
    ):
        result = legacy_module._run_contained(
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

    return (
        base,
        runner,
        adapter,
        contract,
        launch,
        legacy_module.route._current_user_only,
        legacy_module.route._verify_current_user_only,
    )


def _terminal_status(exc: BaseException) -> tuple[str, str]:
    message = str(exc).lower()
    if "machine policy" in message or "managed" in message:
        return "SANDBOXED_RUNNER_MANAGED_POLICY_UNAVAILABLE", "managed policy evidence was unavailable or invalid"
    if "offline sandbox" in message or "fallback" in message:
        return "SANDBOXED_RUNNER_FALLBACK_DETECTED", "the exact elevated offline sandbox identity was not established"
    if "network class" in message or "network denial" in message:
        return "SANDBOXED_RUNNER_TASK_NETWORK_REACHABLE", "one or more task-command network classes were not denied"
    if "hosted" in message:
        return "SANDBOXED_RUNNER_HOSTED_TRANSPORT_UNAVAILABLE", "the bounded hosted transport did not complete"
    if "cleanup" in message:
        return "SANDBOXED_RUNNER_CLEANUP_FAILED", "qualification cleanup failed"
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return "SANDBOXED_RUNNER_PARTIAL_OR_TIMEOUT", "qualification timed out"
    return "SANDBOXED_RUNNER_BINDING_MISMATCH", "qualification precondition failed"


def _publish_terminal(final_root: Path, payload: bytes) -> Mapping[str, object]:
    if final_root.exists():
        raise ExecutorError("qualification output already exists")
    final_root.mkdir(parents=True)
    target = final_root / "qualification-terminal.json"
    with target.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return json.loads(payload)


def execute_qualification(
    *,
    owner_authorized_freeze_commit: str,
    auth_file: Path,
    _launcher=None,
) -> Mapping[str, object]:
    state = {
        "authority_verified": False,
        "hosted_request_attempted": False,
        "staging_owned": False,
    }
    base = Path(__file__).resolve().parent
    repo = _repo_root(base)
    manifest = _load_json(base / "qualification-prerun-manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ExecutorError("qualification pre-run manifest schema mismatch")
    paths = _derived_paths(repo, manifest)
    final_root = paths["qualification_output_root"]
    staging_root = paths["cli_staging_root"]
    private_root = staging_root / "private-runner-root"
    cli_executable = staging_root / "codex.exe"
    freeze_commit = "0" * 40
    contract = None
    try:
        _validate_frozen_files(base, manifest)
        _validate_source_bindings(repo, manifest)
        freeze_commit = str(_git(repo, "rev-parse", "HEAD"))
        if owner_authorized_freeze_commit != freeze_commit:
            raise ExecutorError("owner authority does not match executing freeze commit")
        state["authority_verified"] = True
        if final_root.exists() or staging_root.exists():
            raise ExecutorError("qualification create-once root already exists")
        live_policy = paths["live_machine_policy"]
        if live_policy.stat().st_size != 58 or _sha256_file(live_policy) != EXPECTED_POLICY_SHA256:
            raise ExecutorError("live managed machine policy differs from freeze")
        receipt_payload = (base / "machine-policy-receipt.json").read_bytes()
        if _sha256(receipt_payload) != EXPECTED_RECEIPT_SHA256:
            raise ExecutorError("machine policy receipt differs from reviewed setup")
        python_executable = paths["python_executable"]
        if python_executable.stat().st_size != EXPECTED_PYTHON_BYTES or _sha256_file(python_executable) != EXPECTED_PYTHON_SHA256:
            raise ExecutorError("Python executable differs from freeze")
        state["staging_owned"] = True
        _raw_copy_exact(paths["installed_cli_source"], cli_executable)
        version = subprocess.run(
            [str(cli_executable), "--version"], check=False, capture_output=True, timeout=30
        )
        if (
            version.returncode
            or version.stderr
            or _sha256(version.stdout) != EXPECTED_VERSION_STDOUT_SHA256
        ):
            raise ExecutorError("exact CLI version probe failed")
        (
            runner_base,
            runner,
            adapter,
            contract,
            legacy_launcher,
            protect_path,
            verify_path,
        ) = _load_surfaces(repo, manifest)
        receipt = contract.validate_retained_document(receipt_payload)
        config_bytes = (runner_base / "sandbox-config.toml").read_bytes()
        requirements_bytes = (runner_base / "sandbox-requirements.toml").read_bytes()
        contract.validate_machine_policy_receipt(
            receipt,
            config_sha256=_sha256(config_bytes),
            requirements_sha256=_sha256(requirements_bytes),
        )
        preflight_payload = adapter.build_preflight(
            cli_version_stdout=version.stdout,
            cli_executable=cli_executable,
            python_executable=python_executable,
            runner_path=runner_base / "sandboxed_runner.py",
            config_path=runner_base / "sandbox-config.toml",
            requirements_path=runner_base / "sandbox-requirements.toml",
        )
        run = runner.SandboxedCodexRunner(
            executable=cli_executable,
            python_executable=python_executable,
            private_root=private_root,
            auth_payload=auth_file.read_bytes(),
            config_bytes=config_bytes,
            requirements_bytes=requirements_bytes,
            preflight=json.loads(preflight_payload),
            runner_sha256=_sha256((runner_base / "sandboxed_runner.py").read_bytes()),
            prompt=PROMPT,
            output_schema=OUTPUT_SCHEMA,
            workspace_files={
                "network_denial_probe.py": (runner_base / "network_denial_probe.py").read_bytes()
            },
            launcher=_launcher or legacy_launcher,
            protect_path=protect_path if _launcher is None else (lambda path, directory: None),
            verify_path=verify_path if _launcher is None else (lambda path, directory: None),
            timeout_seconds=300,
        )
        workspace, schema_path, final_path = run.prepare()
        command = runner.build_command(cli_executable, schema_path=schema_path, final_path=final_path)
        environment = {
            key: os.environ[key]
            for key in ("COMSPEC", "PATHEXT", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
            if key in os.environ
        }
        environment.update({"CODEX_HOME": str(private_root / "codex-home"), "NO_COLOR": "1"})
        state["hosted_request_attempted"] = True
        completed = run.launcher(command, PROMPT, workspace, environment, 300)
        if completed.timed_out:
            raise TimeoutError("hosted qualification timed out")
        if completed.returncode != 0:
            raise ExecutorError("hosted transport or task command did not complete")
        probe_payload = (private_root / "workspace" / "containment-result.json").read_bytes()
        probe = contract.validate_retained_document(probe_payload)
        summary = contract.validate_probe_document(probe)
        shutil.rmtree(private_root)
        cli_executable.unlink()
        staging_root.rmdir()
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
                "machine_policy_receipt_sha256": _sha256(receipt_payload),
            },
            counts={
                "network_applicable": summary.applicable_count,
                "network_denied": summary.denied_count,
                "child_network_denied": int(summary.child_denied),
            },
            cleanup="COMPLETE",
            diagnostic="exact hosted transport completed; task command network classes denied",
        )
        return _publish_terminal(final_root, terminal)
    except BaseException as exc:
        cleanup_failed = False
        if state["staging_owned"] and staging_root.exists():
            try:
                shutil.rmtree(staging_root)
            except OSError:
                cleanup_failed = True
        if not state["authority_verified"] or final_root.exists():
            raise
        if contract is None:
            try:
                _, _, _, contract, _, _, _ = _load_surfaces(repo, manifest)
            except BaseException:
                raise exc
        status, diagnostic = _terminal_status(exc)
        if cleanup_failed:
            status = "SANDBOXED_RUNNER_CLEANUP_FAILED"
            diagnostic = "qualification cleanup failed"
        terminal = contract.build_terminal(
            status=status,
            freeze_commit=freeze_commit,
            attempt_id=ATTEMPT_ID,
            hosted_request_attempted=state["hosted_request_attempted"],
            hosted_transport_completed=False,
            task_command_network_denied=False,
            sandbox_implementation="unknown",
            managed_requirement_enforced=False,
            fallback_observed=False,
            digests={},
            counts={},
            cleanup="FAILED" if cleanup_failed else "COMPLETE",
            diagnostic=diagnostic,
        )
        return _publish_terminal(final_root, terminal)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--auth-file", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    terminal = execute_qualification(
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
        auth_file=args.auth_file,
    )
    return 0 if terminal.get("status") == "SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
