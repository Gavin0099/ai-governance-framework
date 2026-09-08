from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = next(path for path in BASE.parents if (path / ".git").exists())
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

runner = importlib.import_module("sandboxed_runner")
preflight = importlib.import_module("preflight_adapter")
contract = importlib.import_module("qualification_contract")
executor = importlib.import_module("qualification_executor")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _probe() -> dict[str, object]:
    return {
        "schema": contract.PROBE_SCHEMA,
        "mode": "parent",
        "sandbox_account_class": "offline_sandbox",
        "attempts": {
            "dns": "denied",
            "public_ipv4_tcp": "denied",
            "public_ipv6_tcp": "not_applicable",
            "https": "denied",
            "loopback_tcp": "denied",
            "private_tcp": "denied",
            "link_local_tcp": "denied",
        },
        "child": {
            "schema": contract.PROBE_SCHEMA,
            "mode": "child",
            "public_ipv4_tcp": "denied",
        },
    }


def test_command_is_exactly_sandboxed() -> None:
    command = runner.build_command(
        Path("codex.exe"),
        schema_path=Path("schema.json"),
        final_path=Path("final.json"),
    )
    assert command[1] == "exec"
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert 'windows.sandbox="elevated"' in command
    assert "sandbox_workspace_write.network_access=false" in command
    assert not runner.FORBIDDEN_ARGUMENTS.intersection(command)
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


@pytest.mark.parametrize(
    "argument",
    [
        "--dangerously-bypass-approvals-and-sandbox",
        "--yolo",
        "danger-full-access",
        "sandbox_workspace_write.network_access=true",
        "windows.sandbox=unelevated",
    ],
)
def test_full_access_arguments_are_forbidden(argument: str) -> None:
    assert argument in runner.FORBIDDEN_ARGUMENTS
    assert argument not in runner.COMMAND_TEMPLATE


def test_policy_requires_elevated_offline_without_fallback() -> None:
    runner.validate_policy_bytes(
        (BASE / "sandbox-config.toml").read_bytes(),
        (BASE / "sandbox-requirements.toml").read_bytes(),
    )


@pytest.mark.parametrize(
    ("config", "requirements"),
    [
        (
            b'approval_policy="never"\nsandbox_mode="workspace-write"\n'
            b'[sandbox_workspace_write]\nnetwork_access=true\n[windows]\n'
            b'sandbox="elevated"\n',
            (BASE / "sandbox-requirements.toml").read_bytes(),
        ),
        (
            (BASE / "sandbox-config.toml").read_bytes(),
            b'[windows]\nallowed_sandbox_implementations=["unelevated"]\n',
        ),
    ],
)
def test_policy_drift_fails_closed(config: bytes, requirements: bytes) -> None:
    with pytest.raises(runner.SandboxedRunnerError):
        runner.validate_policy_bytes(config, requirements)


def test_command_contract_is_interpreter_bound() -> None:
    digest = runner.command_contract_sha256(
        python_executable_sha256=runner.EXPECTED_PYTHON_SHA256
    )
    assert len(digest) == 64
    with pytest.raises(runner.SandboxedRunnerError):
        runner.command_contract_sha256(python_executable_sha256="0" * 64)


def test_preflight_round_trip_with_exact_test_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = tmp_path / "codex.exe"
    python = tmp_path / "python.exe"
    cli.write_bytes(b"cli")
    python.write_bytes(b"python")
    monkeypatch.setattr(runner, "EXPECTED_CLI_SHA256", _sha(b"cli"))
    monkeypatch.setattr(runner, "EXPECTED_PYTHON_SHA256", _sha(b"python"))
    payload = preflight.build_preflight(
        cli_version_stdout=(runner.EXPECTED_CLI_VERSION + "\n").encode(),
        cli_executable=cli,
        python_executable=python,
        runner_path=BASE / "sandboxed_runner.py",
        config_path=BASE / "sandbox-config.toml",
        requirements_path=BASE / "sandbox-requirements.toml",
    )
    value = preflight.parse_and_validate(
        payload,
        runner_sha256=_sha((BASE / "sandboxed_runner.py").read_bytes()),
        config_sha256=_sha((BASE / "sandbox-config.toml").read_bytes()),
        requirements_sha256=_sha((BASE / "sandbox-requirements.toml").read_bytes()),
    )
    assert value["identity_evidence_level"] == "CLIENT_SIDE_INVOCATION_ONLY"
    assert value["server_executed_model_observed"] is False


def test_preflight_rejects_provider_observation_fields() -> None:
    value = {
        "schema": runner.PREFLIGHT_SCHEMA,
        "model_observed_id": runner.EXPECTED_MODEL,
    }
    with pytest.raises(runner.SandboxedRunnerError):
        runner.validate_preflight(
            value,
            runner_sha256="0" * 64,
            config_sha256="0" * 64,
            requirements_sha256="0" * 64,
        )


def test_network_probe_requires_every_applicable_class() -> None:
    summary = contract.validate_probe_document(_probe())
    assert summary.denied_count == summary.applicable_count == 6
    changed = _probe()
    changed["attempts"]["public_ipv4_tcp"] = "reachable"  # type: ignore[index]
    with pytest.raises(contract.QualificationError, match="public_ipv4_tcp"):
        contract.validate_probe_document(changed)


def test_child_process_denial_is_required() -> None:
    changed = _probe()
    changed["child"]["public_ipv4_tcp"] = "reachable"  # type: ignore[index]
    with pytest.raises(contract.QualificationError, match="child-process"):
        contract.validate_probe_document(changed)


def test_offline_sandbox_account_is_required() -> None:
    changed = _probe()
    changed["sandbox_account_class"] = "other"
    with pytest.raises(contract.QualificationError, match="offline sandbox"):
        contract.validate_probe_document(changed)


def test_machine_policy_receipt_requires_owner_reviewed_state() -> None:
    config_sha = _sha((BASE / "sandbox-config.toml").read_bytes())
    requirements_sha = _sha((BASE / "sandbox-requirements.toml").read_bytes())
    value = {
        "schema": "c1-windows-sandbox-machine-policy-receipt.v1",
        "sandbox_implementation": "elevated",
        "managed_requirement_enforced": True,
        "fallback_observed": False,
        "config_sha256": config_sha,
        "requirements_sha256": requirements_sha,
        "machine_state_change_owner_authorized": True,
        "rollback_path_reviewed": True,
    }
    contract.validate_machine_policy_receipt(
        value, config_sha256=config_sha, requirements_sha256=requirements_sha
    )
    value["rollback_path_reviewed"] = False
    with pytest.raises(contract.QualificationError):
        contract.validate_machine_policy_receipt(
            value, config_sha256=config_sha, requirements_sha256=requirements_sha
        )


def test_pass_terminal_requires_full_conjunction() -> None:
    kwargs = dict(
        status="SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED",
        freeze_commit="1" * 40,
        attempt_id=executor.ATTEMPT_ID,
        hosted_request_attempted=True,
        hosted_transport_completed=True,
        task_command_network_denied=True,
        sandbox_implementation="elevated",
        managed_requirement_enforced=True,
        fallback_observed=False,
        digests={"probe_sha256": "0" * 64},
        counts={"network_denied": 6},
        cleanup="COMPLETE",
        diagnostic="qualified",
    )
    payload = contract.build_terminal(**kwargs)
    assert contract.validate_retained_document(payload)["randomization_created"] is False
    kwargs["hosted_transport_completed"] = False
    with pytest.raises(contract.QualificationError, match="conjunction"):
        contract.build_terminal(**kwargs)


def test_forbidden_retention_is_recursive() -> None:
    payload = contract.canonical_json(
        {"schema": "fixture", "nested": {"raw_output": "forbidden"}}
    )
    with pytest.raises(contract.QualificationError, match="forbidden"):
        contract.validate_retained_document(payload)


def test_executor_checks_output_root_before_hosted_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = json.loads((BASE / "amendment-manifest.json").read_text())
    expected = REPO / manifest["publication"]["qualification_output_root"]
    called = False

    def tripwire(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("hosted launch occurred")

    monkeypatch.setattr(executor, "_validate_bindings", lambda *args: None)
    monkeypatch.setattr(executor, "_validate_source_bindings", lambda *args: None)
    with pytest.raises(executor.ExecutorError, match="output root"):
        executor.execute_qualification(
            owner_authorized_freeze_commit="0" * 40,
            owner_authorized_machine_policy_receipt_sha256="0" * 64,
            cli_executable=tmp_path / "codex.exe",
            python_executable=tmp_path / "python.exe",
            auth_file=tmp_path / "auth.json",
            machine_policy_receipt_path=tmp_path / "policy.json",
            output_root=expected.parent / "wrong-attempt",
            launcher=tripwire,
        )
    assert called is False


def test_executor_requires_exact_machine_receipt_before_hosted_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = json.loads((BASE / "amendment-manifest.json").read_text())
    output = REPO / manifest["publication"]["qualification_output_root"]
    policy = tmp_path / "policy.json"
    policy.write_bytes(b"{}\n")
    called = False

    def tripwire(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("hosted launch occurred")

    monkeypatch.setattr(executor, "_validate_bindings", lambda *args: None)
    monkeypatch.setattr(executor, "_validate_source_bindings", lambda *args: None)
    monkeypatch.setattr(executor, "_validate_authority", lambda *args: "1" * 40)
    with pytest.raises(executor.ExecutorError, match="exact owner authority"):
        executor.execute_qualification(
            owner_authorized_freeze_commit="1" * 40,
            owner_authorized_machine_policy_receipt_sha256="0" * 64,
            cli_executable=tmp_path / "codex.exe",
            python_executable=tmp_path / "python.exe",
            auth_file=tmp_path / "auth.json",
            machine_policy_receipt_path=policy,
            output_root=output,
            launcher=tripwire,
        )
    assert called is False


def test_preparation_applies_and_verifies_acl_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = tmp_path / "codex.exe"
    python = tmp_path / "python.exe"
    cli.write_bytes(b"codex")
    python.write_bytes(b"python")
    monkeypatch.setattr(runner.SandboxedCodexRunner, "validate", lambda self: None)
    protected: list[tuple[Path, bool]] = []
    verified: list[tuple[Path, bool]] = []

    def protect(path: Path, is_directory: bool) -> None:
        protected.append((path, is_directory))

    def verify(path: Path, is_directory: bool) -> None:
        verified.append((path, is_directory))

    instance = runner.SandboxedCodexRunner(
        executable=cli,
        python_executable=python,
        private_root=tmp_path / "private",
        auth_payload=b"{}\n",
        config_bytes=b"sandbox_mode = \"workspace-write\"\n",
        requirements_bytes=b"allowed_sandbox_modes = [\"elevated\"]\n",
        preflight={},
        runner_sha256="0" * 64,
        prompt="probe",
        output_schema={"type": "object"},
        workspace_files={"network_denial_probe.py": b"pass\n"},
        launcher=lambda *args, **kwargs: None,
        protect_path=protect,
        verify_path=verify,
        timeout_seconds=1,
    )
    instance.prepare()
    assert protected
    assert verified
    codex_home = instance.private_root / "codex-home"
    auth_file = codex_home / "auth.json"
    assert (codex_home, True) in protected
    assert (auth_file, False) in protected
    assert (codex_home, True) in verified
    assert (auth_file, False) in verified


def test_failure_terminal_is_bounded_and_authority_gated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = tmp_path / "evidence" / "attempt"
    manifest = {"publication": {"qualification_output_root": "evidence/attempt"}}
    monkeypatch.setattr(executor, "_repo_root", lambda base: tmp_path)
    monkeypatch.setattr(executor, "_load_json", lambda path: manifest)
    monkeypatch.setattr(executor, "_git", lambda *args: "1" * 40)
    args = argparse.Namespace(
        output_root=expected,
        owner_authorized_freeze_commit="0" * 40,
    )
    assert not executor._publish_authorized_failure(
        args=args, state={}, exc=executor.ExecutorError("binding mismatch")
    )
    assert not expected.exists()

    args.owner_authorized_freeze_commit = "1" * 40
    assert executor._publish_authorized_failure(
        args=args, state={}, exc=executor.ExecutorError("binding mismatch")
    )
    files = list(expected.iterdir())
    assert [path.name for path in files] == ["qualification-terminal.json"]
    terminal = contract.validate_retained_document(files[0].read_bytes())
    assert terminal["status"] == "SANDBOXED_RUNNER_BINDING_MISMATCH"
    assert terminal["hosted_request_attempted"] is False


def test_network_probe_uses_windows_identity_surface() -> None:
    source = (BASE / "network_denial_probe.py").read_text(encoding="utf-8")
    assert "GetUserNameW" in source
    assert 'os.name == "nt"' in source


def test_manifest_preserves_prior_decisions() -> None:
    manifest = json.loads((BASE / "amendment-manifest.json").read_text())
    preserved = manifest["preserved_decisions"]
    assert preserved["identity_evidence_level"] == "CLIENT_SIDE_INVOCATION_ONLY"
    assert preserved["server_executed_model_observed"] is False
    assert preserved["promotion_comparison"] == "B_vs_A_only"
    assert preserved["d1_d7_thresholds_unchanged"] is True
    assert preserved["attempt_06_quarantine_unchanged"] is True
    assert preserved["d5_countability_decision_unchanged"] is True
    assert manifest["execution_authority"]["authorized"] is False
    assert manifest["authoring_boundary"]["hosted_request_executed"] is False
    assert manifest["authoring_boundary"]["randomization_created"] is False


def test_frozen_files_bind_every_file_except_manifest() -> None:
    manifest = json.loads((BASE / "amendment-manifest.json").read_text())
    bindings = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {
        path.name for path in BASE.iterdir() if path.is_file() and path.name != "amendment-manifest.json"
    }
    assert set(bindings) == actual
    for name, entry in bindings.items():
        payload = (BASE / name).read_bytes()
        assert len(payload) == entry["bytes"]
        assert _sha(payload) == entry["sha256"]


def test_source_bindings_are_git_exact() -> None:
    manifest = json.loads((BASE / "amendment-manifest.json").read_text())
    for entry in manifest["source_bindings"]:
        oid = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={REPO}",
                "-C",
                str(REPO),
                "rev-parse",
                f'{entry["commit"]}:{entry["path"]}',
            ],
            text=True,
        ).strip()
        assert oid == entry["git_blob_oid"]
        payload = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={REPO}",
                "-C",
                str(REPO),
                "cat-file",
                "blob",
                oid,
            ]
        )
        assert len(payload) == entry["bytes"]
        assert _sha(payload) == entry["sha256"]


def test_output_policy_matches_contract() -> None:
    policy = json.loads((BASE / "output-policy.json").read_text())
    assert policy["aggregate_only"] is True
    assert set(policy["forbidden_fields"]) == contract.FORBIDDEN_FIELDS
    assert policy["retain_raw_event_stream"] is False
    assert policy["cleanup_required_before_pass"] is True


def test_no_full_access_literal_in_execution_modules() -> None:
    for name in ("sandboxed_runner.py", "qualification_executor.py"):
        text = (BASE / name).read_text(encoding="utf-8")
        if name == "sandboxed_runner.py":
            # The literal may appear only in the denylist, never in COMMAND_TEMPLATE/build_command.
            assert text.count("--dangerously-bypass-approvals-and-sandbox") == 1
        else:
            assert "--dangerously-bypass-approvals-and-sandbox" not in text
