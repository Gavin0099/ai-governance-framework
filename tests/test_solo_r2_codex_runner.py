from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest

from governance_tools import solo_r2_codex_runner as subject
from governance_tools.solo_r2_attempt_materialization import (
    HostLocalEndpointDisposition,
    HostLocalIsolation,
    PinnedExecutable,
)


CATALOG = subject.ToolCatalog.project(
    (
        subject.ToolDescriptor("command_execution"),
        subject.ToolDescriptor("file_change"),
        subject.ToolDescriptor("mcp_tool_call", approval_required=True),
    )
)
HOST_LOCAL = HostLocalIsolation(HostLocalEndpointDisposition.REACHABLE, 0)
OFFLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1003"
ONLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1004"
LAUNCHER_SID = "S-1-5-21-4017902291-1272973841-664929404-1001"
GENERATION = subject.SandboxGenerationFingerprint.create(
    offline_sid=OFFLINE_SID,
    online_sid=ONLINE_SID,
    offline_password_last_set_utc="2026-09-02T10:25:08.5697508Z",
    online_password_last_set_utc="2026-09-02T10:25:08.6099464Z",
    sandbox_users_json_byte_length=2,
    sandbox_users_json_sha256=hashlib.sha256(b"{}").hexdigest(),
)
IDENTITY = subject.RuntimeIdentity(
    subject.MODEL_SELECTOR,
    subject.REASONING_EFFORT,
    "UNAVAILABLE",
    "codex-cli-0.146.0",
    "host-a",
    subject.IDENTITY_DISPOSITION,
)


class Backend:
    def __init__(self, host_local: HostLocalIsolation = HOST_LOCAL) -> None:
        self.canary = subject.CanaryObservation(
            context_id="canary-context",
            workspace_id="canary-workspace",
            runtime_identity=IDENTITY,
            execution_policy=subject.REQUIRED_EXECUTION_POLICY,
            configured_tool_inventory=CATALOG.public_inventory(),
            catalog_sha256=CATALOG.catalog_sha256,
            credential_sentinel_visible=False,
            network_tcp_egress_denied=True,
            host_local=host_local,
            sandbox_principal=OFFLINE_SID,
            sandbox_account_generation=GENERATION.value,
        )

    def run_canary(self, **kwargs):
        assert "PATH" not in kwargs["launcher_environment"]
        assert "CODEX_HOME" not in kwargs["model_tool_environment"]
        return self.canary

    def prepare_arm(self, *, arm_ordinal: int, **kwargs):
        return subject.ArmPreparationObservation(
            arm_ordinal=arm_ordinal,
            context_id=f"context-{arm_ordinal}",
            workspace_id=f"workspace-{arm_ordinal}",
            runtime_identity=IDENTITY,
            execution_policy=subject.REQUIRED_EXECUTION_POLICY,
            configured_tool_inventory=CATALOG.public_inventory(),
            catalog_sha256=CATALOG.catalog_sha256,
            task_exposure_state="NONE",
            sandbox_principal=OFFLINE_SID,
            sandbox_account_generation=GENERATION.value,
            credential_sentinel_visible=False,
            host_local=self.canary.host_local,
        )


def _adapter(tmp_path: Path, backend: Backend | None = None) -> subject.CodexRunnerAdapter:
    return subject.CodexRunnerAdapter(
        executable=PinnedExecutable.capture(Path(sys.executable).resolve()),
        backend=backend or Backend(),
        expected_catalog=CATALOG,
        codex_home=(tmp_path / "codex-home").resolve(),
        temp_root=tmp_path.resolve(),
        sandbox_generation_probe=lambda: GENERATION,
    )


def _trace(tool_types: tuple[str, ...], terminal: str = "turn.completed") -> bytes:
    events: list[dict[str, object]] = [
        {"type": "thread.started", "thread_id": "thread"},
        {"type": "turn.started"},
    ]
    events.extend(
        {
            "type": "item.started",
            "item": {"id": f"item-{index}", "type": tool_type},
        }
        for index, tool_type in enumerate(tool_types)
    )
    events.append({"type": terminal})
    return b"".join(
        json.dumps(event, separators=(",", ":"), sort_keys=True).encode("ascii") + b"\n"
        for event in events
    )


def _prepared() -> subject.PreparedArm:
    return subject.PreparedArm(
        1,
        "context-1",
        "workspace-1",
        IDENTITY,
        subject.REQUIRED_EXECUTION_POLICY,
        CATALOG.public_inventory(),
        CATALOG.catalog_sha256,
        OFFLINE_SID,
        GENERATION.value,
        HOST_LOCAL,
    )


def test_catalog_projection_is_order_independent_and_closed() -> None:
    assert subject.ToolCatalog.project(tuple(reversed(CATALOG.tools))) == CATALOG
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.ToolCatalog.observed(
            ({"name": "file_change", "approval_required": False, "extra": True},),
            CATALOG.catalog_sha256,
        )
    assert caught.value.code == subject.PAIR_INVALID


def test_tool_gate_is_explicitly_reference_only() -> None:
    gate = subject.ToolCallGate(CATALOG)
    effects = 0

    def effect() -> int:
        nonlocal effects
        effects += 1
        return effects

    for _ in range(60):
        gate.invoke("file_change", effect)
    with pytest.raises(subject.RunnerGateError) as caught:
        gate.invoke("file_change", effect)
    assert caught.value.code == subject.TOOL_CALL_LIMIT_REACHED
    assert gate.enforcement_disposition == "SPECIFIED_NOT_INSTALLED"
    assert effects == 60


def test_policy_claims_only_post_hoc_cap() -> None:
    policy = subject.REQUIRED_EXECUTION_POLICY
    assert policy.approval_mode == "CODEX_NATIVE_NEVER"
    assert policy.network_mode == "CODEX_NATIVE_SANDBOX_OFFLINE"
    assert policy.tool_call_cap_enforcement == "MEASURED_POST_HOC"
    assert policy.hard_pre_dispatch_cap == "NOT_CLAIMED"


def test_generation_fingerprint_changes_with_password_or_marker() -> None:
    password_changed = subject.SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc="2026-09-02T10:26:08.5697508Z",
        online_password_last_set_utc=GENERATION.online_password_last_set_utc,
        sandbox_users_json_byte_length=GENERATION.sandbox_users_json_byte_length,
        sandbox_users_json_sha256=GENERATION.sandbox_users_json_sha256,
    )
    marker_changed = subject.SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc=GENERATION.offline_password_last_set_utc,
        online_password_last_set_utc=GENERATION.online_password_last_set_utc,
        sandbox_users_json_byte_length=3,
        sandbox_users_json_sha256=hashlib.sha256(b"{ }").hexdigest(),
    )
    assert password_changed.value != GENERATION.value
    assert marker_changed.value != GENERATION.value


def test_sid_cannot_be_used_as_generation() -> None:
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.validate_sandbox_binding_value(OFFLINE_SID, OFFLINE_SID)
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_sandbox_principal_stays_bound_to_machine_offline_sid() -> None:
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.validate_sandbox_binding(LAUNCHER_SID, GENERATION.value, GENERATION)
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_payload_resolver_requires_one_content_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = tmp_path / "Local"
    root = local / "OpenAI" / "Codex" / "bin"
    payload = b"exact-codex"
    candidate = root / "0123456789abcdef" / "codex.exe"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(payload)
    monkeypatch.setattr(subject, "_windows_local_app_data_path", lambda: local.resolve())
    monkeypatch.setattr(subject, "CODEX_PAYLOAD_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(subject, "CODEX_PAYLOAD_SHA256", hashlib.sha256(payload).hexdigest())

    resolved = subject.resolve_codex_payload()
    assert resolved.path == candidate.resolve()
    resolved.verify()

    duplicate = root / "fedcba9876543210" / "codex.exe"
    duplicate.parent.mkdir()
    duplicate.write_bytes(payload)
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.resolve_codex_payload()
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def _owner_payload_fixture(tmp_path, monkeypatch):
    local = tmp_path / "Local"
    candidate = local / "OpenAI" / "Codex" / "bin" / "0123456789abcdef" / "codex.exe"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"owner-adopted-payload")
    monkeypatch.setattr(subject, "_windows_local_app_data_path", lambda: local.resolve())
    record = tmp_path / "owner-pin.json"
    value = {
        "schema": "solo-r2-owner-payload-pin/v1",
        "authority_class": "OWNER_ATTESTED",
        "evaluation_id": "bba7af6e-6b0f-43b6-9af3-be755c7ade2d",
        "pair_id": "07fc2e7f-2eae-49f0-9021-0793f0778902",
        "slot": "R2-SHAKEDOWN",
        "payload_byte_length": candidate.stat().st_size,
        "payload_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }
    record.write_bytes(subject._canonical_json(value) + b"\n")
    pin = subject.OwnerPayloadPin(
        PinnedExecutable.capture(record.resolve()), value["evaluation_id"],
        value["pair_id"], value["slot"],
    )
    return candidate, record, value, pin


def test_owner_pin_selects_exact_payload_without_changing_legacy_policy(tmp_path, monkeypatch):
    candidate, record, value, pin = _owner_payload_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "hostile"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "decoy"))
    resolved = subject.resolve_codex_payload(owner_pin=pin)
    assert resolved.path == candidate.resolve()
    with pytest.raises(subject.RunnerGateError):
        subject.resolve_codex_payload()
    duplicate = candidate.parent.parent / "fedcba9876543210" / "codex.exe"
    duplicate.parent.mkdir()
    duplicate.write_bytes(candidate.read_bytes())
    with pytest.raises(subject.RunnerGateError):
        subject.resolve_codex_payload(owner_pin=pin)


@pytest.mark.parametrize("field,replacement", [
    ("evaluation_id", "2fc5fd9b-9283-4d45-8c6a-ed6e2eb525e5"),
    ("pair_id", "346df3b9-4637-4187-a59e-52863bb8b172"),
    ("slot", "OTHER"), ("authority_class", "AUTO_DISCOVERED"),
    ("payload_byte_length", True), ("payload_sha256", "ABC"),
])
def test_owner_pin_rejects_invalid_record_before_discovery(tmp_path, monkeypatch, field, replacement):
    _, record, value, pin = _owner_payload_fixture(tmp_path, monkeypatch)
    value[field] = replacement
    record.write_bytes(subject._canonical_json(value) + b"\n")
    pin = replace(pin, record=PinnedExecutable.capture(record.resolve()))
    monkeypatch.setattr(subject, "_windows_local_app_data_path", lambda: pytest.fail("discovery reached"))
    with pytest.raises(subject.RunnerGateError):
        subject.resolve_codex_payload(owner_pin=pin)


@pytest.mark.parametrize("change", ["record", "payload", "missing", "noncanonical", "duplicate_key"])
def test_owner_pin_drift_stops_before_native_dispatch(tmp_path, monkeypatch, change):
    candidate, record, value, pin = _owner_payload_fixture(tmp_path, monkeypatch)
    backend = subject.NativeCodexExecBackend(
        executable=subject.resolve_codex_payload(owner_pin=pin),
        configured_catalog=CATALOG, expected_launcher_sid=LAUNCHER_SID,
        owner_payload_pin=pin,
    )
    if change == "record":
        record.write_bytes(b"{}\n")
    elif change == "payload":
        candidate.write_bytes(b"unapproved-update")
    elif change == "missing":
        record.unlink()
    else:
        payload = json.dumps(value, indent=2).encode() if change == "noncanonical" else b'{"schema":1,"schema":2}\n'
        record.write_bytes(payload)
        backend.owner_payload_pin = replace(pin, record=PinnedExecutable.capture(record.resolve()))
    monkeypatch.setattr(subject, "_windows_process_identity", lambda: pytest.fail("identity probe reached"))
    output = tmp_path / "output"
    with pytest.raises(subject.RunnerGateError):
        backend.execute(
            prepared_arm=_prepared(), workspace_root=tmp_path, codex_home=tmp_path,
            output_root=output, prompt=b"never dispatched", output_schema={},
        )
    assert not output.exists()


def test_payload_resolver_rejects_zero_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = tmp_path / "Local"
    candidate = local / "OpenAI" / "Codex" / "bin" / "0123456789abcdef" / "codex.exe"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"wrong")
    monkeypatch.setattr(subject, "_windows_local_app_data_path", lambda: local.resolve())
    monkeypatch.setattr(subject, "CODEX_PAYLOAD_BYTE_LENGTH", 5)
    monkeypatch.setattr(subject, "CODEX_PAYLOAD_SHA256", "0" * 64)
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.resolve_codex_payload()
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_payload_resolver_rejects_reparse_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = tmp_path / "Local"
    root = local / "OpenAI" / "Codex" / "bin"
    target = tmp_path / "payload-target"
    target.mkdir(parents=True)
    root.mkdir(parents=True)
    link = root / "0123456789abcdef"
    if os.name == "nt":
        completed = subprocess.run(
            (
                r"C:\Windows\System32\cmd.exe",
                "/d",
                "/c",
                "mklink",
                "/J",
                str(link),
                str(target),
            ),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        assert completed.returncode == 0, completed.stderr
    else:
        link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(subject, "_windows_local_app_data_path", lambda: local.resolve())
    try:
        with pytest.raises(subject.RunnerGateError) as caught:
            subject.resolve_codex_payload()
    finally:
        if os.name == "nt":
            os.rmdir(link)
        else:
            link.unlink()
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_generation_capture_hashes_unique_marker_and_account_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = (tmp_path / "codex-home").resolve()
    temp = (tmp_path / "temp").resolve()
    home.mkdir()
    temp.mkdir()
    marker = home / "state" / "sandbox_users.json"
    marker.parent.mkdir()
    marker.write_bytes(b'{"generation":2}\n')
    executable = Path(sys.executable).resolve()
    payload = executable.read_bytes()
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_PATH", executable)
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_PATH", executable)
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_SHA256", hashlib.sha256(payload).hexdigest())

    projection = {
        "offline_sid": OFFLINE_SID,
        "online_sid": ONLINE_SID,
        "offline_password_last_set_utc": "2026-09-02T10:25:08.5697508Z",
        "online_password_last_set_utc": "2026-09-02T10:25:08.6099464Z",
    }

    def query(command, *, input_bytes, cwd, env, timeout_seconds):
        assert command[0] == str(executable)
        assert command[1:5] == ("-NoLogo", "-NoProfile", "-NonInteractive", "-Command")
        assert input_bytes == b"" and cwd == home and timeout_seconds == 30
        assert "PATH" not in env
        return subject.ProcessResult(
            0, json.dumps(projection).encode("ascii"), b"", False, True
        )

    monkeypatch.setattr(subject, "_run_contained_once", query)
    observed = subject.capture_sandbox_generation(codex_home=home, temp_root=temp)
    assert observed.offline_sid == OFFLINE_SID
    assert observed.sandbox_users_json_byte_length == len(marker.read_bytes())
    assert observed.sandbox_users_json_sha256 == hashlib.sha256(marker.read_bytes()).hexdigest()
    subject.validate_sandbox_binding(OFFLINE_SID, observed.value, observed)


def test_generation_marker_must_be_unique(tmp_path: Path) -> None:
    home = (tmp_path / "codex-home").resolve()
    home.mkdir()
    with pytest.raises(subject.RunnerGateError) as absent:
        subject._sandbox_users_json_identity(home)
    assert absent.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE
    for name in ("one", "two"):
        path = home / name / "sandbox_users.json"
        path.parent.mkdir()
        path.write_text("{}", encoding="ascii")
    with pytest.raises(subject.RunnerGateError) as ambiguous:
        subject._sandbox_users_json_identity(home)
    assert ambiguous.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_generation_capture_maps_malformed_projection_to_pre_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = (tmp_path / "codex-home").resolve()
    temp = (tmp_path / "temp").resolve()
    home.mkdir()
    temp.mkdir()
    executable = Path(sys.executable).resolve()
    payload = executable.read_bytes()
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_PATH", executable)
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_PATH", executable)
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(subject, "LOCAL_ACCOUNTS_MODULE_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(
        subject,
        "_run_contained_once",
        lambda *args, **kwargs: subject.ProcessResult(
            0, b'{"offline_sid":"one","offline_sid":"two"}', b"", False, True
        ),
    )

    with pytest.raises(subject.RunnerGateError) as caught:
        subject.capture_sandbox_generation(codex_home=home, temp_root=temp)
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_adapter_rejects_generation_change_during_pre_id_observation(
    tmp_path: Path,
) -> None:
    changed = subject.SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc="2026-09-02T10:26:08.5697508Z",
        online_password_last_set_utc=GENERATION.online_password_last_set_utc,
        sandbox_users_json_byte_length=GENERATION.sandbox_users_json_byte_length,
        sandbox_users_json_sha256=GENERATION.sandbox_users_json_sha256,
    )
    observations = iter((GENERATION, changed))
    adapter = subject.CodexRunnerAdapter(
        executable=PinnedExecutable.capture(Path(sys.executable).resolve()),
        backend=Backend(),
        expected_catalog=CATALOG,
        codex_home=(tmp_path / "codex-home").resolve(),
        temp_root=tmp_path.resolve(),
        sandbox_generation_probe=lambda: next(observations),
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        adapter.qualify_canary()
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_adapter_remeasures_generation_before_formal_arm(tmp_path: Path) -> None:
    changed = subject.SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc="2026-09-02T10:26:08.5697508Z",
        online_password_last_set_utc=GENERATION.online_password_last_set_utc,
        sandbox_users_json_byte_length=GENERATION.sandbox_users_json_byte_length,
        sandbox_users_json_sha256=GENERATION.sandbox_users_json_sha256,
    )
    observations = iter((GENERATION, GENERATION, changed))
    backend = Backend()
    prepare_calls = 0
    original = backend.prepare_arm

    def counted_prepare(**kwargs):
        nonlocal prepare_calls
        prepare_calls += 1
        return original(**kwargs)

    backend.prepare_arm = counted_prepare
    adapter = subject.CodexRunnerAdapter(
        executable=PinnedExecutable.capture(Path(sys.executable).resolve()),
        backend=backend,
        expected_catalog=CATALOG,
        codex_home=(tmp_path / "codex-home").resolve(),
        temp_root=tmp_path.resolve(),
        sandbox_generation_probe=lambda: next(observations),
    )
    adapter.qualify_canary()
    with pytest.raises(subject.RunnerGateError) as caught:
        adapter.prepare_formal_arm(1)
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE
    assert prepare_calls == 0


def test_canary_and_formal_arms_are_fresh_and_unexposed(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    canary = adapter.qualify_canary()
    first = adapter.prepare_formal_arm(1)
    second = adapter.prepare_formal_arm(2)
    assert len({canary.context_id, first.context_id, second.context_id}) == 3
    assert len({canary.workspace_id, first.workspace_id, second.workspace_id}) == 3
    assert first.task_exposure_state == second.task_exposure_state == "NONE"
    with pytest.raises(subject.RunnerGateError):
        adapter.prepare_formal_arm(1)


def test_adapter_propagates_resolved_blocked_host_local_disposition(
    tmp_path: Path,
) -> None:
    host_local = HostLocalIsolation(HostLocalEndpointDisposition.BLOCKED, 0)
    adapter = _adapter(tmp_path, Backend(host_local))
    assert adapter.qualify_canary().host_local == host_local
    assert adapter.prepare_formal_arm(1).host_local == host_local


def test_configured_tool_projection_drift_is_pair_invalid(tmp_path: Path) -> None:
    backend = Backend()
    drifted = subject.ToolCatalog.project((subject.ToolDescriptor("file_change"),))
    backend.canary = replace(
        backend.canary,
        configured_tool_inventory=drifted.public_inventory(),
        catalog_sha256=drifted.catalog_sha256,
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        _adapter(tmp_path, backend).qualify_canary()
    assert caught.value.code == subject.PAIR_INVALID


def test_formal_timeout_policy_drift_is_pair_invalid(tmp_path: Path) -> None:
    backend = Backend()
    original = backend.prepare_arm

    def drifted_prepare_arm(**kwargs):
        observed = original(**kwargs)
        return replace(
            observed,
            execution_policy=replace(
                subject.REQUIRED_EXECUTION_POLICY, max_elapsed_seconds=1_801
            ),
        )

    backend.prepare_arm = drifted_prepare_arm
    adapter = _adapter(tmp_path, backend)
    adapter.qualify_canary()
    with pytest.raises(subject.RunnerGateError) as caught:
        adapter.prepare_formal_arm(1)
    assert caught.value.code == subject.PAIR_INVALID


@pytest.mark.parametrize(
    ("field", "value"),
    (("credential_sentinel_visible", True), ("network_tcp_egress_denied", False)),
)
def test_canary_fails_closed_on_boundary_regression(
    tmp_path: Path, field: str, value: bool
) -> None:
    backend = Backend()
    backend.canary = replace(backend.canary, **{field: value})
    with pytest.raises(subject.RunnerGateError):
        _adapter(tmp_path, backend).qualify_canary()


def test_native_backend_launches_exact_codex_argv_and_derives_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    called = 0

    def execute(command, *, input_bytes, cwd, env, timeout_seconds):
        nonlocal called
        called += 1
        assert command[0] == str(executable.path)
        assert command[1:12] == (
            "-c",
            "model_reasoning_effort=high",
            "-c",
            'approval_policy="never"',
            "-c",
            'windows.sandbox="elevated"',
            "-c",
            "sandbox_workspace_write.network_access=false",
            "-c",
            'cli_auth_credentials_store="keyring"',
            "exec",
        )
        assert command.count('cli_auth_credentials_store="keyring"') == 1
        assert 'cli_auth_credentials_store="auto"' not in command
        assert 'cli_auth_credentials_store="file"' not in command
        assert "--json" in command and "--ignore-user-config" in command
        assert "--strict-config" in command
        assert command[command.index("--sandbox") + 1] == "workspace-write"
        assert "--dangerously-bypass-approvals-and-sandbox" not in command
        assert "danger-full-access" not in command
        assert command[-3:] == ("--model", "gpt-5.6-sol", "-")
        assert timeout_seconds == 1_800 and input_bytes == b"task\n"
        assert cwd == (tmp_path / "workspace").resolve()
        assert "PATH" not in env and env["CODEX_HOME"].endswith("codex-home")
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_bytes(b'{"status":"ok"}\n')
        return subject.ProcessResult(
            0, _trace(("command_execution",)), b"", False, True
        )

    for name in ("workspace", "codex-home", "output"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(subject, "_run_contained_once", execute)
    monkeypatch.setattr(
        subject,
        "_windows_process_identity",
        lambda: subject.LauncherProcessIdentity(
            "DESKTOP\\daish", LAUNCHER_SID, "MEDIUM", False
        ),
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
        expected_launcher_sid=LAUNCHER_SID,
        sandbox_generation_capture=lambda **kwargs: GENERATION,
    )
    result = backend.execute(
        prepared_arm=_prepared(),
        workspace_root=(tmp_path / "workspace").resolve(),
        codex_home=(tmp_path / "codex-home").resolve(),
        output_root=(tmp_path / "output").resolve(),
        prompt=b"task\n",
        output_schema={"type": "object"},
    )
    assert called == 1
    assert result.disposition == subject.SUCCESS
    assert result.tool_call_count == 1
    assert result.observed_tool_inventory == ("command_execution",)
    subject.validate_execution_result(result, CATALOG)


def test_61_calls_are_agent_failure_derived_post_hoc(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    schema_path = tmp_path / "schema.json"
    final_path = tmp_path / "final.json"
    trace = _trace(("command_execution",) * 61)
    trace_path.write_bytes(trace)
    schema = b'{"type":"object"}\n'
    final = b"{}\n"
    schema_path.write_bytes(schema)
    final_path.write_bytes(final)
    metrics = subject.derive_trace_metrics(trace)
    result = subject.NativeExecutionResult(
        trace_path=trace_path, schema_path=schema_path, final_message_path=final_path,
        schema_sha256=subject._sha256(schema), schema_byte_length=len(schema),
        trace_sha256=metrics.trace_sha256, trace_byte_length=metrics.byte_length,
        tool_call_count=metrics.tool_call_count,
        observed_tool_inventory=metrics.observed_tool_inventory,
        terminal_event=metrics.terminal_event, disposition=subject.AGENT_FAILURE,
        returncode=0, timed_out=False, tree_terminated=True,
        stderr_sha256=subject._sha256(b""), stderr_byte_length=0,
        final_message_sha256=subject._sha256(final),
        final_message_byte_length=len(final),
    )
    subject.validate_execution_result(result, CATALOG)
    assert result.tool_call_count == 61


def test_observed_tools_only_need_to_be_subset_of_projection(tmp_path: Path) -> None:
    control = subject.derive_trace_metrics(_trace(("command_execution",)))
    treatment = subject.derive_trace_metrics(_trace(("file_change",)))
    assert CATALOG.admits(control.observed_tool_inventory)
    assert CATALOG.admits(treatment.observed_tool_inventory)
    assert control.observed_tool_inventory != treatment.observed_tool_inventory
    assert not CATALOG.admits(("unconfigured_tool",))


@pytest.mark.parametrize(
    "identity",
    (
        subject.LauncherProcessIdentity(
            "DESKTOP\\other", "S-1-5-21-1-2-3-1002", "MEDIUM", False
        ),
        subject.LauncherProcessIdentity(
            "DESKTOP\\daish", LAUNCHER_SID, "HIGH", False
        ),
        subject.LauncherProcessIdentity(
            "DESKTOP\\daish", LAUNCHER_SID, "MEDIUM", True
        ),
    ),
)
def test_launcher_identity_mismatch_denies_before_process_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: subject.LauncherProcessIdentity,
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    called = False

    def execute(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("must not dispatch")

    for name in ("workspace", "codex-home", "output"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(subject, "_run_contained_once", execute)
    monkeypatch.setattr(
        subject,
        "_windows_process_identity",
        lambda: identity,
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
        expected_launcher_sid=LAUNCHER_SID,
        sandbox_generation_capture=lambda **kwargs: GENERATION,
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        backend.execute(
            prepared_arm=_prepared(),
            workspace_root=(tmp_path / "workspace").resolve(),
            codex_home=(tmp_path / "codex-home").resolve(),
            output_root=(tmp_path / "output").resolve(),
            prompt=b"task\n",
            output_schema={"type": "object"},
        )
    assert caught.value.code == subject.PAIR_INVALID
    assert called is False


def test_generation_mismatch_denies_before_schema_or_codex_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    dispatched = False
    changed = subject.SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc="2026-09-02T10:26:08.5697508Z",
        online_password_last_set_utc=GENERATION.online_password_last_set_utc,
        sandbox_users_json_byte_length=GENERATION.sandbox_users_json_byte_length,
        sandbox_users_json_sha256=GENERATION.sandbox_users_json_sha256,
    )

    def execute(*args, **kwargs):
        nonlocal dispatched
        dispatched = True
        raise AssertionError("must not dispatch")

    for name in ("workspace", "codex-home", "output"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(subject, "_run_contained_once", execute)
    monkeypatch.setattr(
        subject,
        "_windows_process_identity",
        lambda: subject.LauncherProcessIdentity(
            "DESKTOP\\daish", LAUNCHER_SID, "MEDIUM", False
        ),
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
        expected_launcher_sid=LAUNCHER_SID,
        sandbox_generation_capture=lambda **kwargs: changed,
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        backend.execute(
            prepared_arm=_prepared(),
            workspace_root=(tmp_path / "workspace").resolve(),
            codex_home=(tmp_path / "codex-home").resolve(),
            output_root=(tmp_path / "output").resolve(),
            prompt=b"task\n",
            output_schema={"type": "object"},
        )
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE
    assert dispatched is False
    assert tuple((tmp_path / "output").iterdir()) == ()


def test_generation_probe_output_mutation_denies_before_codex_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    dispatched = False
    for name in ("workspace", "codex-home", "output"):
        (tmp_path / name).mkdir()

    def execute(*args, **kwargs):
        nonlocal dispatched
        dispatched = True
        raise AssertionError("must not dispatch")

    def mutating_capture(**kwargs):
        (kwargs["temp_root"] / "unexpected").write_bytes(b"mutation")
        return GENERATION

    monkeypatch.setattr(subject, "_run_contained_once", execute)
    monkeypatch.setattr(
        subject,
        "_windows_process_identity",
        lambda: subject.LauncherProcessIdentity(
            "DESKTOP\\daish", LAUNCHER_SID, "MEDIUM", False
        ),
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
        expected_launcher_sid=LAUNCHER_SID,
        sandbox_generation_capture=mutating_capture,
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        backend.execute(
            prepared_arm=_prepared(),
            workspace_root=(tmp_path / "workspace").resolve(),
            codex_home=(tmp_path / "codex-home").resolve(),
            output_root=(tmp_path / "output").resolve(),
            prompt=b"task\n",
            output_schema={"type": "object"},
        )
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE
    assert dispatched is False


def test_trace_and_claim_tampering_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    schema_path = tmp_path / "schema.json"
    final_path = tmp_path / "final.json"
    trace = _trace(("command_execution",))
    path.write_bytes(trace)
    schema = b'{"type":"object"}\n'
    final = b"{}\n"
    schema_path.write_bytes(schema)
    final_path.write_bytes(final)
    metrics = subject.derive_trace_metrics(trace)
    result = subject.NativeExecutionResult(
        trace_path=path, schema_path=schema_path, final_message_path=final_path,
        schema_sha256=subject._sha256(schema), schema_byte_length=len(schema),
        trace_sha256=metrics.trace_sha256, trace_byte_length=metrics.byte_length,
        tool_call_count=2, observed_tool_inventory=metrics.observed_tool_inventory,
        terminal_event=metrics.terminal_event, disposition=subject.SUCCESS,
        returncode=0, timed_out=False, tree_terminated=True,
        stderr_sha256=subject._sha256(b""), stderr_byte_length=0,
        final_message_sha256=subject._sha256(final),
        final_message_byte_length=len(final),
    )
    with pytest.raises(subject.RunnerGateError) as caught:
        subject.validate_execution_result(result, CATALOG)
    assert caught.value.code == subject.PAIR_INVALID


@pytest.mark.skipif(os.name != "nt", reason="Windows containment contract")
def test_default_executor_binds_job_before_child_executes(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    home = (tmp_path / "codex-home").resolve()
    output = (tmp_path / "output").resolve()
    workspace.mkdir()
    home.mkdir()
    output.mkdir()
    result = subject._run_contained_once(
        (str(Path(sys.executable).resolve()), "-I", "-S", "-c", "print('ok')"),
        input_bytes=b"",
        cwd=workspace,
        env=subject.launcher_environment(home, output),
        timeout_seconds=5,
    )
    assert result.returncode == 0
    assert result.stdout == b"ok\r\n"
    assert result.tree_terminated is True
    assert not tuple(output.glob(".solo-r2-job-*"))
