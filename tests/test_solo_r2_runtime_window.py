from __future__ import annotations

import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import subprocess
import tarfile

import pytest
from jsonschema import Draft202012Validator

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_attempt_materialization as materialization_subject
from governance_tools import solo_r2_controller_state as controller_state
from governance_tools import solo_r2_random_domains as random_domains
from governance_tools import solo_r2_runtime_window as subject
from governance_tools.solo_r2_attempt_execution import PairBinding, PairLedgerLock
from governance_tools.solo_r2_attempt_materialization import (
    FROZEN_BASE_COMMIT,
    FrozenGitMaterializer,
    HostLocalEndpointDisposition,
    HostLocalIsolation,
    LeafAclObservation,
    LeafWorkspaceManager,
    PinnedExecutable,
    RepositoryBinding,
    TreatmentInstruction,
)
from governance_tools.solo_r2_codex_runner import (
    CODEX_PAYLOAD_BYTE_LENGTH,
    CODEX_PAYLOAD_SHA256,
    IDENTITY_DISPOSITION,
    NativeExecutionResult,
    NativeCodexExecBackend,
    ProcessResult,
    RuntimeIdentity,
    SandboxGenerationFingerprint,
    ToolCatalog,
    ToolDescriptor,
    _canonical_json,
    derive_trace_metrics,
)


CANONICAL = Path("artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson")
PACKET = Path("artifacts/experiments/prepush-bugfix-20260724/skill-packet-bugfix.md")
OFFLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1003"
ONLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1004"
HOST_LOCAL = HostLocalIsolation(HostLocalEndpointDisposition.REACHABLE, 0)
CATALOG = ToolCatalog.project((ToolDescriptor("command_execution"),))
OFF_HOST_ENDPOINT = subject.OffHostControlEndpoint("192.0.2.1", 443)
PROBE_IDENTITY = subject.BoundaryProbeIdentity(
    subject._PROBE_SCRIPT_RELPATH,
    len(subject._BOUNDARY_PROBE_SCRIPT),
    hashlib.sha256(subject._BOUNDARY_PROBE_SCRIPT).hexdigest(),
    str(subject.WINDOWS_POWERSHELL_PATH),
    subject.WINDOWS_POWERSHELL_BYTE_LENGTH,
    subject.WINDOWS_POWERSHELL_SHA256,
)


# Literal JSON-decoded display fixture: JSON escaping is not CLI escaping.
_DIRECT_PROBE_COMMAND = r"& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoLogo -NoProfile -NonInteractive -File 'D:\probe\qualification-boundary-probe.ps1' -ConfigPath 'D:\probe\qualification-boundary-config.json'"
_WRAPPED_PROBE_COMMAND = r'''"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "& 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe' -NoLogo -NoProfile -NonInteractive -File 'D:\\probe\\qualification-boundary-probe.ps1' -ConfigPath 'D:\\probe\\qualification-boundary-config.json'"'''
_NO_PROFILE_WRAPPED_PROBE_COMMAND = r'''"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "& 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe' -NoLogo -NoProfile -NonInteractive -File 'D:\\probe\\qualification-boundary-probe.ps1' -ConfigPath 'D:\\probe\\qualification-boundary-config.json'"'''


@pytest.mark.parametrize("recorded,accepted", [
    (_DIRECT_PROBE_COMMAND, True),
    (_WRAPPED_PROBE_COMMAND, True),
    (_NO_PROFILE_WRAPPED_PROBE_COMMAND, True),
    (_WRAPPED_PROBE_COMMAND.replace(' -Command ', ' -NoLogo -Command ', 1), False),
    (_NO_PROFILE_WRAPPED_PROBE_COMMAND.replace(' -Command ', ' -NoLogo -Command ', 1), False),
    (_NO_PROFILE_WRAPPED_PROBE_COMMAND.replace(' -NoProfile -Command ', ' -Command -NoProfile ', 1), False),
    (_NO_PROFILE_WRAPPED_PROBE_COMMAND.replace('boundary-probe.ps1', 'boundary-probe.ps2'), False),
    (_NO_PROFILE_WRAPPED_PROBE_COMMAND.replace('powershell.exe', 'other.exe', 1), False),
    ('"powershell.exe" -Command "' + _NO_PROFILE_WRAPPED_PROBE_COMMAND + '"', False),
    (_WRAPPED_PROBE_COMMAND.replace("boundary-probe.ps1", "other.ps1"), False),
    (_WRAPPED_PROBE_COMMAND + " -NoProfile", False),
    (_WRAPPED_PROBE_COMMAND.replace("powershell.exe", "other.exe", 1), False),
    ('"powershell.exe" -Command "' + _WRAPPED_PROBE_COMMAND + '"', False),
    (_WRAPPED_PROBE_COMMAND.replace("\\\\", "\\", 1), False),
    ("prefix " + _WRAPPED_PROBE_COMMAND, False),
    (_DIRECT_PROBE_COMMAND + "; Write-Output forged", False),
])
def test_probe_command_accepts_only_closed_representations(tmp_path, recorded, accepted):
    (tmp_path / "qualification-challenge.txt").write_text("a" * 32)
    backend = NativeBackendDouble(None, command_override=recorded)
    result = backend.execute(
        prepared_arm=None, workspace_root=tmp_path, output_root=tmp_path,
        output_schema=subject.MachineBackedBoundaryProbe._schema(),
        prompt=("probe\nonce\n" + _DIRECT_PROBE_COMMAND).encode(),
    )
    kwargs = dict(configured_catalog=CATALOG, expected_command=_DIRECT_PROBE_COMMAND,
                  powershell_path=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    if accepted:
        assert subject.MachineBackedBoundaryProbe._read_command_result(result, **kwargs)["challenge"] == "a" * 32
    else:
        with pytest.raises(subject.RuntimeWindowError) as caught:
            subject.MachineBackedBoundaryProbe._read_command_result(result, **kwargs)
        assert caught.value.code == subject.PAIR_INVALID


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell 5.1")
@pytest.mark.parametrize("case,expected,root_type", [
    ("acl", "DENIED", "UnauthorizedAccessException"),
    ("missing", "ERROR", "FileNotFoundException"),
    ("missing-parent", "ERROR", "DirectoryNotFoundException"),
    ("sharing", "ERROR", "IOException"),
    ("direct-denied", "DENIED", "UnauthorizedAccessException"),
    ("security", "DENIED", "SecurityException"),
    ("unknown", "ERROR", "InvalidOperationException"),
    ("unknown-wrapper", "ERROR", "UnauthorizedAccessException"),
])
def test_real_powershell_probe_credential_classifier(tmp_path, case, expected, root_type):
    # Extract the deployed bytes, not a Python translation of the classifier.
    source = subject._BOUNDARY_PROBE_SCRIPT.decode("ascii")
    fragment = source[source.index("try {\n    [void][IO.File]::ReadAllBytes"):source.index("$offHostConnect =")]
    read_expression = "[void][IO.File]::ReadAllBytes([string]$config.credential_sentinel_path)"
    synthetic = {
        "direct-denied": "throw [UnauthorizedAccessException]::new('synthetic')",
        "security": "throw [Security.SecurityException]::new('synthetic')",
        "unknown": "throw [InvalidOperationException]::new('synthetic')",
        "unknown-wrapper": "throw [InvalidOperationException]::new('synthetic', [UnauthorizedAccessException]::new('inner'))",
    }
    if case in synthetic:
        fragment = fragment.replace(read_expression, synthetic[case])
    # Capture the actual exception without replacing production classification.
    fragment = fragment.replace("} catch {", "} catch {\n    $caught = $_.Exception", 1)
    fixture = str(tmp_path / "fixture.txt").replace("'", "''")
    script = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) { throw 'PowerShell 5.1 required' }
$path = '__FIXTURE__'
$case = '__CASE__'
$originalAcl = $null
$handle = $null
[IO.File]::WriteAllText($path, 'public test fixture')
try {
    if ($case -eq 'acl') {
        $originalAcl = [IO.File]::GetAccessControl($path)
        $acl = [IO.File]::GetAccessControl($path)
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, [Security.AccessControl.FileSystemRights]::ReadData, [Security.AccessControl.AccessControlType]::Deny)
        $acl.AddAccessRule($rule)
        [IO.File]::SetAccessControl($path, $acl)
    }
    if ($case -eq 'sharing') { $handle = [IO.File]::Open($path, 'Open', 'ReadWrite', 'None') }
    if ($case -eq 'missing') { $path += '.absent' }
    if ($case -eq 'missing-parent') { $path += '.absent\child.txt' }
    $config = @{credential_sentinel_path=$path}
    __FRAGMENT__
    [ordered]@{classification=$credentialRead; outer=$caught.GetType().Name; root=$caught.GetBaseException().GetType().Name; hresult=$caught.GetBaseException().HResult} | ConvertTo-Json -Compress
} finally {
    if ($null -ne $handle) { $handle.Dispose() }
    if ($null -ne $originalAcl) {
        $sections = [Security.AccessControl.AccessControlSections]::Access
        $restoredAcl = [Security.AccessControl.FileSecurity]::new()
        $restoredAcl.SetSecurityDescriptorSddlForm($originalAcl.GetSecurityDescriptorSddlForm($sections), $sections)
        [IO.File]::SetAccessControl($path, $restoredAcl)
        $actualAcl = [IO.File]::GetAccessControl($path)
        $actualSddl = $actualAcl.GetSecurityDescriptorSddlForm($sections)
        $expectedSddl = $originalAcl.GetSecurityDescriptorSddlForm($sections)
        # Windows may set the auto-inherited bookkeeping bit when restoring.
        # Every ACE and the inheritance protection state must still match.
        if ($actualSddl.Substring($actualSddl.IndexOf('(')) -cne $expectedSddl.Substring($expectedSddl.IndexOf('(')) -or $actualAcl.AreAccessRulesProtected -ne $originalAcl.AreAccessRulesProtected) { throw 'Fixture ACL restoration failed' }
    }
}
'''.replace("__FIXTURE__", fixture).replace("__CASE__", case).replace("__FRAGMENT__", fragment)
    completed = subprocess.run(
        [str(subject.WINDOWS_POWERSHELL_PATH), "-NoLogo", "-NoProfile", "-NonInteractive",
         "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode("ascii")],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    assert observed["classification"] == expected
    assert observed["root"] == root_type
    if case in {"acl", "missing", "missing-parent", "sharing"}:
        assert observed["outer"] == "MethodInvocationException"
    if case == "acl":
        assert observed["hresult"] == -2147024891
    if case == "sharing":
        assert observed["hresult"] == -2147024864


def _generation(timestamp: str, marker: bytes) -> SandboxGenerationFingerprint:
    return SandboxGenerationFingerprint.create(
        offline_sid=OFFLINE_SID,
        online_sid=ONLINE_SID,
        offline_password_last_set_utc=timestamp,
        online_password_last_set_utc=timestamp,
        sandbox_users_json_byte_length=len(marker),
        sandbox_users_json_sha256=hashlib.sha256(marker).hexdigest(),
    )


GENERATION_A = _generation("2026-09-04T04:52:33.0000000Z", b"old")
GENERATION_B = _generation("2026-09-04T05:00:00.0000000Z", b"new")


def _ledger_copy(tmp_path: Path) -> Path:
    path = (tmp_path / "ledger.ndjson").resolve()
    path.write_bytes(CANONICAL.read_bytes())
    return path


def _binding(path: Path) -> PairBinding:
    events = ledger.read_ledger(path)
    pair = events[1]
    return PairBinding(
        evaluation_id=events[0]["evaluation_id"],
        pair_id=pair["pair_id"],
        slot=pair["slot"],
        category=pair["category"],
        repository=pair["repository"],
        frozen_identities=pair["frozen_identities"],
    )


def _order_state(binding: PairBinding) -> dict[str, object]:
    entropy = next(
        value.to_bytes(32, "big")
        for value in range(1, 100)
        if random_domains.arm_order_from_entropy(value.to_bytes(32, "big"))[0]
        == "TREATMENT"
    )
    return {
        "schema_version": controller_state.CONTROLLER_STATE_SCHEMA,
        "artifact_type": controller_state.CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": binding.evaluation_id,
        "pair_id": binding.pair_id,
        "slot": binding.slot,
        "state_phase": controller_state.ORDER_FROZEN,
        "realized_order": list(random_domains.arm_order_from_entropy(entropy)),
        "order_entropy": base64.b64encode(entropy).decode("ascii"),
        "attempt_bindings": [],
        "scoring_bindings": [],
        "presentation_order": [],
        "attempt_output_refs": [],
    }


class NativeBackendDouble:
    owner_payload_pin = None

    def resolve_payload(self):
        return subject.resolve_codex_payload()

    def __init__(
        self,
        executable: PinnedExecutable,
        *,
        qualification_changes: dict[str, object] | None = None,
        qualification_output: str | None = None,
        execution_evidence: bool = True,
        command_override: str | None = None,
    ) -> None:
        self.executable = executable
        self.configured_catalog = CATALOG
        self.calls = 0
        self.preparations: list[object] = []
        self.non_git_options: list[object] = []
        self.qualification_changes = qualification_changes or {}
        self.qualification_output = qualification_output
        self.execution_evidence = execution_evidence
        self.command_override = command_override

    def execute(self, **kwargs) -> NativeExecutionResult:
        self.non_git_options.append(kwargs.get("allow_non_git_workdir", False))
        self.calls += 1
        self.preparations.append(kwargs["prepared_arm"])
        workspace = kwargs["workspace_root"]
        output = kwargs["output_root"]
        challenge = (workspace / "qualification-challenge.txt").read_text("ascii")
        whoami = str(Path(sys.executable).resolve())
        properties = kwargs["output_schema"]["properties"]
        machine_probe = "credential_read" in properties
        if machine_probe:
            command = kwargs["prompt"].decode("utf-8").splitlines()[2]
            final_value = {
                "challenge": challenge,
                "challenge_read": "READ",
                "credential_read": "DENIED",
                "host_local_connect": "CONNECTED",
                "off_host_connect": "CONNECTION_FAILED",
                "principal_observation": "OBSERVED",
                "principal_sid": OFFLINE_SID,
                "status": subject.QUALIFICATION_STATUS,
            }
            final_value.update(self.qualification_changes)
            aggregated_output = json.dumps(
                final_value, separators=(",", ":"), sort_keys=True
            )
            if self.qualification_output is not None:
                aggregated_output = self.qualification_output
        else:
            command = f"read qualification-challenge.txt; '{whoami}' /user"
            final_value = {
                "status": subject.QUALIFICATION_STATUS,
                "challenge": challenge,
                "principal_sid": OFFLINE_SID,
            }
            aggregated_output = f"CodexSandboxOffline {OFFLINE_SID}\n{challenge}"
        trace = b"".join(
            json.dumps(event, separators=(",", ":"), sort_keys=True).encode("ascii")
            + b"\n"
            for event in (
                {"type": "thread.started", "thread_id": "thread"},
                {"type": "turn.started"},
                {
                    "type": "item.started",
                    "item": {"id": "one", "type": "command_execution"},
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": "one",
                        "type": "command_execution",
                        "command": command,
                        "aggregated_output": aggregated_output,
                        "status": "completed",
                        "exit_code": 0,
                    },
                },
                {"type": "turn.completed"},
            )
        )
        if not self.execution_evidence:
            trace = b"".join(
                _canonical_json(event) + b"\n"
                for event in (
                    {"type": "thread.started", "thread_id": "thread"},
                    {"type": "turn.started"},
                    {"type": "item.completed", "item": {
                        "id": "answer", "type": "agent_message",
                        "text": _canonical_json(final_value).decode("ascii"),
                    }},
                    {"type": "turn.completed"},
                )
            )
        elif self.command_override is not None:
            events = [json.loads(line) for line in trace.splitlines()]
            for event in events:
                if event["type"] == "item.completed":
                    event["item"]["command"] = self.command_override
            trace = b"".join(_canonical_json(event) + b"\n" for event in events)
        schema = _canonical_json(kwargs["output_schema"]) + b"\n"
        final = _canonical_json(final_value) + b"\n"
        trace_path = output / "codex-trace.jsonl"
        schema_path = output / "output-schema.json"
        final_path = output / "final-message.json"
        trace_path.write_bytes(trace)
        schema_path.write_bytes(schema)
        final_path.write_bytes(final)
        metrics = derive_trace_metrics(trace)
        return NativeExecutionResult(
            trace_path,
            schema_path,
            final_path,
            hashlib.sha256(schema).hexdigest(),
            len(schema),
            metrics.trace_sha256,
            metrics.byte_length,
            metrics.tool_call_count,
            metrics.observed_tool_inventory,
            metrics.terminal_event,
            "SUCCESS",
            0,
            False,
            True,
            hashlib.sha256(b"").hexdigest(),
            0,
            hashlib.sha256(final).hexdigest(),
            len(final),
        )


class FreezeProbeDouble:
    def __init__(
        self,
        pair_lock: PairLedgerLock,
        freeze: subject.RuntimeFreeze,
        qualification_helper: PinnedExecutable,
    ) -> None:
        self.pair_lock = pair_lock
        self.freeze = freeze
        self.qualification_helper = qualification_helper
        self.checks = 0
        self.quiescence_checks = 0

    def assert_runtime_quiescent(self) -> None:
        self.quiescence_checks += 1

    def capture_candidate(self) -> subject.RuntimeFreezeCandidate:
        self.pair_lock.assert_unchanged()
        return subject.RuntimeFreezeCandidate(
            **{
                key: value
                for key, value in self.freeze.__dict__.items()
                if key != "boundary_evidence_sha256"
            }
        )

    def finalize(
        self,
        candidate: subject.RuntimeFreezeCandidate,
        boundary_evidence: subject.PreExposureBoundaryEvidence,
    ) -> subject.RuntimeFreeze:
        assert candidate == self.capture_candidate()
        self.freeze = subject.RuntimeFreeze(
            **candidate.__dict__,
            boundary_evidence_sha256=boundary_evidence.evidence_sha256,
        )
        return self.freeze

    def assert_unchanged(self, expected: subject.RuntimeFreeze) -> None:
        self.pair_lock.assert_unchanged()
        assert expected == self.freeze
        self.checks += 1


def _freeze(
    executable: PinnedExecutable,
    binding: PairBinding,
    generation: SandboxGenerationFingerprint,
) -> subject.RuntimeFreeze:
    runner = subject.RepositoryFileIdentity(
        "governance_tools/solo_r2_codex_runner.py", 1, "1" * 64
    )
    materialization = subject.RepositoryFileIdentity(
        "governance_tools/solo_r2_attempt_materialization.py", 1, "2" * 64
    )
    return subject.RuntimeFreeze(
        executable.path,
        executable.byte_length,
        executable.sha256,
        executable.path,
        executable.byte_length,
        executable.sha256,
        subject.RepositoryRuntimeIdentity("a" * 40, runner, materialization),
        generation,
        "3" * 64,
        binding.evaluation_id,
        binding.pair_id,
        binding.slot,
        (str(executable.path), "exec"),
        "4" * 64,
        True,
        "5" * 64,
    )


def _host_local_tcp(**changes: object) -> subject.HostLocalTcpObservation:
    values: dict[str, object] = {
        "expected_nonce": "1" * 32,
        "child_connect": "CONNECTED",
        "listener_outcome": "PAYLOAD_RECEIVED",
        "listener_payload": "1" * 32,
        "launcher_pre_reachable": True,
        "launcher_post_reachable": True,
        "same_child_required_probes_passed": True,
    }
    values.update(changes)
    return subject.HostLocalTcpObservation(**values)  # type: ignore[arg-type]


class PassingBoundarySource:
    def __call__(self, **kwargs) -> subject.PreExposureBoundaryObservation:
        assert kwargs["result"] is not None
        kwargs["generation"].validate()
        return subject.PreExposureBoundaryObservation(
            "DENIED",
            True,
            "BLOCKED",
            True,
            _host_local_tcp(),
            0,
            (),
            OFF_HOST_ENDPOINT,
            PROBE_IDENTITY,
        )


class FakeLocalBoundaryListener:
    host = "127.0.0.1"
    port = 49152

    def __init__(
        self,
        *,
        workspace: Path,
        outcome: str = "PAYLOAD_RECEIVED",
        payload: str | None = None,
        pre_control: bool = True,
        post_control: bool = True,
        close_count: int = 0,
        close_error: bool = False,
    ) -> None:
        self.workspace = workspace
        self.outcome = outcome
        self.payload = payload
        self.controls = [pre_control, post_control]
        self.close_count = close_count
        self.close_error = close_error
        self.closed = False

    def launcher_round_trip(self, payload: str, *, timeout_seconds: float) -> bool:
        assert len(payload) == 32
        assert timeout_seconds > 0
        return self.controls.pop(0)

    def observe_child(self) -> tuple[str, str | None]:
        value = self.payload
        if value == "EXPECTED":
            value = (self.workspace / "qualification-challenge.txt").read_text("ascii")
        return self.outcome, value

    def close_and_count(self) -> int:
        if self.close_error:
            raise OSError("teardown failed")
        self.closed = True
        return self.close_count


class FakeBoundaryTransport:
    def __init__(
        self,
        listener: FakeLocalBoundaryListener,
        *,
        egress_controls: tuple[bool, bool] = (True, True),
    ) -> None:
        self.listener = listener
        self.egress_controls = list(egress_controls)

    def open_local_listener(self) -> FakeLocalBoundaryListener:
        return self.listener

    def can_connect(
        self, endpoint: subject.OffHostControlEndpoint, *, timeout_seconds: float
    ) -> bool:
        assert endpoint == OFF_HOST_ENDPOINT
        assert timeout_seconds > 0
        return self.egress_controls.pop(0)


def _run_machine_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    listener_outcome: str = "PAYLOAD_RECEIVED",
    listener_payload: str | None = "EXPECTED",
    listener_pre_control: bool = True,
    listener_post_control: bool = True,
    listener_close_count: int = 0,
    listener_close_error: bool = False,
    egress_controls: tuple[bool, bool] = (True, True),
    qualification_changes: dict[str, object] | None = None,
    qualification_output: str | None = None,
    execution_evidence: bool = True,
    command_override: str | None = None,
) -> tuple[
    subject.PreExposureBoundaryObservation,
    NativeExecutionResult,
    FakeLocalBoundaryListener,
]:
    workspace = (tmp_path / "qualification-workspace").resolve()
    output = (tmp_path / "qualification-output").resolve()
    workspace.mkdir()
    output.mkdir()
    challenge = "a" * 32
    challenge_path = workspace / "qualification-challenge.txt"
    challenge_path.write_text(challenge, encoding="ascii")
    sentinel = (tmp_path / subject._CREDENTIAL_SENTINEL_NAME).resolve()
    sentinel.write_text("c" * 32, encoding="ascii")
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_PATH", executable.path)
    monkeypatch.setattr(
        subject, "WINDOWS_POWERSHELL_BYTE_LENGTH", executable.byte_length
    )
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_SHA256", executable.sha256)
    listener = FakeLocalBoundaryListener(
        workspace=workspace,
        outcome=listener_outcome,
        payload=listener_payload,
        pre_control=listener_pre_control,
        post_control=listener_post_control,
        close_count=listener_close_count,
        close_error=listener_close_error,
    )
    transport = FakeBoundaryTransport(listener, egress_controls=egress_controls)
    probe = subject.MachineBackedBoundaryProbe(
        off_host_control_endpoint=OFF_HOST_ENDPOINT,
        credential_sentinel_path=sentinel,
        transport=transport,
    )
    native = NativeBackendDouble(
        executable,
        qualification_changes=qualification_changes,
        qualification_output=qualification_output,
        execution_evidence=execution_evidence,
        command_override=command_override,
    )

    def execute(
        *, prompt: bytes, output_schema: dict[str, object]
    ) -> NativeExecutionResult:
        return native.execute(
            prepared_arm=SimpleNamespace(),
            workspace_root=workspace,
            output_root=output,
            prompt=prompt,
            output_schema=output_schema,
        )

    result, observation = probe.run(
        workspace=workspace,
        challenge=challenge,
        challenge_path=challenge_path,
        whoami=executable,
        generation=GENERATION_B,
        configured_catalog=CATALOG,
        execute=execute,  # type: ignore[arg-type]
    )
    assert set(workspace.iterdir()) == {challenge_path}
    return observation, result, listener


@pytest.mark.parametrize("probe_class", (
    subject.NativePreExposureObservationBackend, subject.MachineBackedBoundaryProbe,
))
def test_probe_schema_requires_challenge_shape_but_does_not_prove_execution(
    probe_class: type,
) -> None:
    schema = probe_class._schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    value = {
        key: (definition["const"] if "const" in definition else
              "ERROR" if "enum" in definition else "")
        for key, definition in schema["properties"].items()
    }
    for challenge in ("", "a" * 31, "a" * 33, "g" * 32, "A" * 32, "a" * 32 + "\n"):
        value["challenge"] = challenge
        assert not validator.is_valid(value)
    # Invented but well-shaped data can pass schema. The evidence gate must
    # still reject it; ERROR probe fields remain representable.
    value["challenge"] = "0123456789abcdef0123456789abcdef"
    assert validator.is_valid(value)


@pytest.mark.parametrize(
    "execution_evidence,challenge,command_override,accepted",
    (
        (False, "b" * 32, None, False),
        (True, "b" * 32, None, False),
        (False, "a" * 32, None, False),
        (True, "a" * 32, None, True),
        (True, "a" * 32, "Write-Output unrelated", False),
    ),
    ids=("no-exec-fabricated", "exec-wrong-challenge", "no-exec-exact-challenge",
         "exec-exact-challenge", "unrelated-command-exact-challenge"),
)
def test_qualification_requires_exact_execution_and_hidden_challenge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    execution_evidence: bool, challenge: str, command_override: str | None,
    accepted: bool,
) -> None:
    evidence_path = (tmp_path / "boundary.json").resolve()

    def qualify():
        observation, result, _ = _run_machine_probe(
            tmp_path, monkeypatch, execution_evidence=execution_evidence,
            qualification_changes={"challenge": challenge},
            command_override=command_override,
        )
        return subject.PreExposureBoundaryEvidenceProducer(
            evidence_path=evidence_path,
        ).produce(result=result, generation=GENERATION_B, observation=observation)

    if accepted:
        evidence = qualify()
        assert evidence_path.is_file()
        assert subject.PreExposureBoundaryEvidence.load(
            evidence_path, expected_sha256=evidence.evidence_sha256,
        ) == evidence
    else:
        with pytest.raises(subject.RuntimeWindowError):
            qualify()
        assert not evidence_path.exists()


def test_machine_probe_reachable_uses_one_exact_governed_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation, result, listener = _run_machine_probe(tmp_path, monkeypatch)
    assert observation.host_local_tcp.classify() is (
        HostLocalEndpointDisposition.REACHABLE
    )
    assert observation.credential_read == "DENIED"
    assert observation.child_egress_connect == "BLOCKED"
    assert observation.off_host_control_endpoint == OFF_HOST_ENDPOINT
    observation.qualification_probe.validate()
    assert result.tool_call_count == 1
    assert listener.closed is True
    event = next(
        json.loads(line)
        for line in result.trace_path.read_bytes().splitlines()
        if json.loads(line).get("type") == "item.completed"
    )
    command = event["item"]["command"]
    assert command.startswith("& '")
    assert " -NoLogo -NoProfile -NonInteractive -File " in command
    assert subject._PROBE_SCRIPT_RELPATH in command
    assert subject._PROBE_CONFIG_RELPATH in command
    assert b"qualification-boundary-probe.ps1" not in b"".join(
        path.read_bytes() for path in (tmp_path / "qualification-workspace").iterdir()
    )


def test_machine_probe_blocked_is_valid_structured_negative_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observation, result, _ = _run_machine_probe(
        tmp_path,
        monkeypatch,
        listener_outcome="NO_CONNECTION",
        listener_payload=None,
        qualification_changes={"host_local_connect": "CONNECTION_FAILED"},
    )
    evidence_path = (tmp_path / "boundary.json").resolve()
    evidence = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=evidence_path
    ).produce(
        result=result,
        generation=GENERATION_B,
        observation=observation,
    )
    assert evidence.host_local.host_local_endpoint_reachable is (
        HostLocalEndpointDisposition.BLOCKED
    )
    assert evidence.off_host_control_endpoint == OFF_HOST_ENDPOINT
    assert subject.PreExposureBoundaryEvidence.load(
        evidence_path, expected_sha256=evidence.evidence_sha256
    ) == evidence


@pytest.mark.parametrize(
    "probe_args",
    (
        {"listener_outcome": "TIMEOUT", "listener_payload": None},
        {"listener_payload": "b" * 32},
        {"listener_post_control": False},
        {"egress_controls": (True, False)},
        {"qualification_changes": {"challenge_read": "ERROR"}},
        {"qualification_changes": {"challenge": "b" * 32}},
        {"qualification_changes": {"credential_read": "VISIBLE"}},
        {"qualification_changes": {"off_host_connect": "TIMEOUT"}},
    ),
)
def test_machine_probe_unknown_facts_never_create_boundary_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe_args: dict[str, object],
) -> None:
    observation, result, _ = _run_machine_probe(
        tmp_path, monkeypatch, **probe_args  # type: ignore[arg-type]
    )
    producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=(tmp_path / "boundary.json").resolve()
    )
    with pytest.raises(subject.RuntimeWindowError):
        producer.produce(
            result=result,
            generation=GENERATION_B,
            observation=observation,
        )
    assert not (tmp_path / "boundary.json").exists()


def test_machine_probe_missing_or_malformed_output_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(subject.RuntimeWindowError):
        _run_machine_probe(
            tmp_path,
            monkeypatch,
            qualification_output='{"status":"R2_NON_EXPOSURE_OK"}',
        )


def test_machine_probe_teardown_failure_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(subject.RuntimeWindowError):
        _run_machine_probe(tmp_path, monkeypatch, listener_close_error=True)


def test_machine_probe_nonzero_listener_count_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(subject.RuntimeWindowError):
        _run_machine_probe(tmp_path, monkeypatch, listener_close_count=1)


def test_machine_probe_pre_control_failure_stops_before_child_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(subject.RuntimeWindowError) as caught:
        _run_machine_probe(tmp_path, monkeypatch, listener_pre_control=False)
    assert caught.value.code == subject.HOST_LOCAL_OBSERVATION_UNAVAILABLE


def test_machine_probe_off_host_pre_control_failure_stops_before_child_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(subject.RuntimeWindowError) as caught:
        _run_machine_probe(tmp_path, monkeypatch, egress_controls=(False, True))
    assert caught.value.code == subject.HOST_LOCAL_OBSERVATION_UNAVAILABLE


def test_probe_script_uses_pinned_inputs_without_ambient_path() -> None:
    script = subject._BOUNDARY_PROBE_SCRIPT.decode("ascii")
    assert "$config.whoami_path" in script
    assert "qualification-challenge.txt" not in script
    assert "$env:PATH" not in script
    assert "Get-Command" not in script
    assert hashlib.sha256(subject._BOUNDARY_PROBE_SCRIPT).hexdigest() == (
        PROBE_IDENTITY.script_sha256
    )


def test_current_codex_0153_payload_is_exactly_pinned() -> None:
    assert CODEX_PAYLOAD_BYTE_LENGTH == 295_295_792
    assert CODEX_PAYLOAD_SHA256 == (
        "be83164c07287d028cc4725105f3cceaaf244d53a862e19743f55e9150a66fc1"
    )


def test_native_command_policy_projection_binds_keyring_and_path_slots() -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    backend = NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
        expected_launcher_sid="S-1-5-21-1-2-3-1001",
    )
    projection = backend.command_policy_projection()
    assert projection.count("{output_schema_path}") == 1
    assert projection.count("{final_message_path}") == 1
    assert projection.count('cli_auth_credentials_store="keyring"') == 1
    assert 'cli_auth_credentials_store="auto"' not in projection
    assert 'cli_auth_credentials_store="file"' not in projection
    assert "--ignore-user-config" in projection
    assert "--strict-config" in projection
    assert "--dangerously-bypass-approvals-and-sandbox" not in projection
    assert "danger-full-access" not in projection


def test_non_git_opt_in_changes_only_git_check_in_command_and_projection() -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    backend = NativeCodexExecBackend(
        executable=executable, configured_catalog=CATALOG,
        expected_launcher_sid="S-1-5-21-1-2-3-1001",
    )
    schema, final = Path("schema.json"), Path("final.json")
    expected = (
        str(executable.path), "-c", "model_reasoning_effort=high",
        "-c", 'approval_policy="never"', "-c", 'windows.sandbox="elevated"',
        "-c", "sandbox_workspace_write.network_access=false",
        "-c", 'cli_auth_credentials_store="keyring"', "exec",
        "--ignore-user-config", "--strict-config", "--sandbox", "workspace-write",
        "--json", "--ephemeral", "--output-last-message", str(final),
        "--output-schema", str(schema), "--model", "gpt-5.6-sol", "-",
    )
    assert backend._command(schema, final) == expected
    assert backend._command(schema, final, allow_non_git_workdir=False) == expected
    for allow in (False, True):
        command = backend._command(schema, final, allow_non_git_workdir=allow)
        projection = backend.command_policy_projection(allow_non_git_workdir=allow)
        assert command.count("--skip-git-repo-check") == int(allow)
        assert projection.count("--skip-git-repo-check") == int(allow)
        assert tuple(t for t in command if t != "--skip-git-repo-check") == expected
        assert tuple(
            str(schema) if t == "{output_schema_path}" else
            str(final) if t == "{final_message_path}" else t
            for t in projection
        ) == command


@pytest.mark.parametrize("value", (None, 0, 1, "true"))
def test_non_git_opt_in_rejects_non_boolean(value: object) -> None:
    from governance_tools.solo_r2_codex_runner import RunnerGateError
    backend = NativeCodexExecBackend(
        executable=PinnedExecutable.capture(Path(sys.executable).resolve()),
        configured_catalog=CATALOG, expected_launcher_sid="S-1-5-21-1-2-3-1001",
    )
    with pytest.raises(RunnerGateError):
        backend.command_policy_projection(allow_non_git_workdir=value)


def test_git_repository_probe_binds_head_blobs_and_worktree_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "repo").resolve()
    git_dir = root / ".git"
    common_dir = git_dir / "common"
    temp = (tmp_path / "temp").resolve()
    for path in (root, git_dir, common_dir, temp):
        path.mkdir(exist_ok=True)
    runner_path = root / "governance_tools" / "solo_r2_codex_runner.py"
    materialization_path = (
        root / "governance_tools" / "solo_r2_attempt_materialization.py"
    )
    runner_path.parent.mkdir()
    runner_payload = b"runner\n"
    materialization_payload = b"materialization\n"
    runner_path.write_bytes(runner_payload)
    materialization_path.write_bytes(materialization_payload)
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    binding = RepositoryBinding(root, git_dir.resolve(), common_dir.resolve())
    monkeypatch.setattr(subject, "verify_repository_binding", lambda *args, **kwargs: None)

    def run_git(executable, repository, args, *, temp_root):
        if args == ("rev-parse", "--verify", "HEAD"):
            return ("a" * 40 + "\n").encode("ascii")
        if args[-1].endswith("solo_r2_codex_runner.py"):
            return runner_payload
        if args[-1].endswith("solo_r2_attempt_materialization.py"):
            return materialization_payload
        raise AssertionError(args)

    monkeypatch.setattr(subject, "_run_git", run_git)
    probe = subject.GitRepositoryFreezeProbe(
        git=executable,
        repository=binding,
        temp_root=temp,
    )
    observed = probe.capture()
    assert observed.head_commit == "a" * 40
    assert observed.runner.sha256 == hashlib.sha256(runner_payload).hexdigest()
    assert observed.materialization.byte_length == len(materialization_payload)
    runner_path.write_bytes(b"drift\n")
    with pytest.raises(subject.RuntimeWindowError) as caught:
        probe.capture()
    assert caught.value.code == subject.PAIR_INVALID


def test_freeze_capture_rejects_generation_drift_during_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    monkeypatch.setattr(subject, "resolve_codex_payload", lambda: executable)
    ledger_path = _ledger_copy(tmp_path)
    pair_lock = PairLedgerLock(
        ledger_path=ledger_path,
        lock_path=(tmp_path / "freeze.lock").resolve(),
        binding=_binding(ledger_path),
    )
    repository = subject.RepositoryRuntimeIdentity(
        "a" * 40,
        subject.RepositoryFileIdentity("runner.py", 1, "1" * 64),
        subject.RepositoryFileIdentity("materialization.py", 1, "2" * 64),
    )
    projected_options = []

    def command_policy_projection(**kwargs):
        projected_options.append(kwargs)
        return (str(executable.path), "exec", "--skip-git-repo-check")

    native = SimpleNamespace(
        executable=executable,
        owner_payload_pin=None,
        resolve_payload=lambda: subject.resolve_codex_payload(),
        command_policy_projection=command_policy_projection,
    )
    generations = iter((GENERATION_A, GENERATION_B))
    probe = subject.RuntimeFreezeProbe(
        backend=native,  # type: ignore[arg-type]
        repository_probe=SimpleNamespace(capture=lambda: repository),  # type: ignore[arg-type]
        qualification_helper=executable,
        generation_probe=lambda: next(generations),
        pair_lock=pair_lock,
        boundary_evidence=subject.PreExposureBoundaryEvidence(
            "5" * 64,
            False,
            True,
            HOST_LOCAL,
            OFF_HOST_ENDPOINT,
            PROBE_IDENTITY,
        ),
        assert_runtime_quiescent=lambda: None,
    )
    with pair_lock, pytest.raises(subject.RuntimeWindowError) as caught:
        probe.capture()
    assert caught.value.code == subject.SAME_MACHINE_WINDOW_REJECTED
    assert projected_options == [{"allow_non_git_workdir": True}]


@pytest.mark.parametrize("failure", ["wrong_pair", "record_changed"])
def test_owner_payload_pin_failure_precedes_window_lock_and_provisioning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    from governance_tools import solo_r2_codex_runner as runner

    local = tmp_path / "Local"
    executable_path = local / "OpenAI" / "Codex" / "bin" / "0123456789abcdef" / "codex.exe"
    executable_path.parent.mkdir(parents=True)
    executable_path.write_bytes(b"adopted-native-fixture")
    monkeypatch.setattr(runner, "_windows_local_app_data_path", lambda: local.resolve())
    value = {
        "schema": "solo-r2-owner-payload-pin/v1", "authority_class": "OWNER_ATTESTED",
        "evaluation_id": "bba7af6e-6b0f-43b6-9af3-be755c7ade2d",
        "pair_id": "07fc2e7f-2eae-49f0-9021-0793f0778902", "slot": "R2-SHAKEDOWN",
        "payload_byte_length": executable_path.stat().st_size,
        "payload_sha256": hashlib.sha256(executable_path.read_bytes()).hexdigest(),
    }
    path = tmp_path / "owner-pin.json"
    path.write_bytes(runner._canonical_json(value) + b"\n")
    pin = runner.OwnerPayloadPin(
        PinnedExecutable.capture(path.resolve()), value["evaluation_id"],
        value["pair_id"], value["slot"],
    )
    native = runner.NativeCodexExecBackend(
        executable=runner.resolve_codex_payload(owner_pin=pin), configured_catalog=CATALOG,
        expected_launcher_sid="S-1-5-21-4017902291-1272973841-664929404-1001",
        owner_payload_pin=pin,
    )
    binding = SimpleNamespace(evaluation_id=pin.evaluation_id, pair_id=pin.pair_id, slot=pin.slot)
    if failure == "wrong_pair":
        binding.pair_id = "346df3b9-4637-4187-a59e-52863bb8b172"
    else:
        path.write_bytes(b"{}\n")
    # No context-manager methods: reaching lock acquisition fails this test.
    lock = SimpleNamespace(binding=binding)
    backend = SimpleNamespace(
        native_backend=native, whoami=native.executable,
        provision_sandbox=lambda: pytest.fail("provisioning reached"),
    )
    window = subject.PreAttemptFrozenRuntimeWindow(
        backend=backend, adapter=SimpleNamespace(backend=backend),
        freeze_probe=SimpleNamespace(pair_lock=lock, qualification_helper=backend.whoami),
        materializer=None, pair_lock=lock, sealed_order=None,
    )
    with pytest.raises((subject.RuntimeWindowError, runner.RunnerGateError)):
        window.run()
    assert not (tmp_path / "pair.lock").exists()


def test_boundary_evidence_loads_only_exact_fail_closed_projection(tmp_path: Path) -> None:
    value = {
        "schema": subject.BOUNDARY_SCHEMA,
        "credential_sentinel_visible": False,
        "network_tcp_egress_denied": True,
        "host_local_endpoint_reachable": "REACHABLE",
        "observed_host_listener_count": 0,
        "runtime_endpoint_inputs": [],
        "off_host_control_endpoint": {
            "host": OFF_HOST_ENDPOINT.host,
            "port": OFF_HOST_ENDPOINT.port,
        },
        "qualification_probe": {
            "script_relative_path": PROBE_IDENTITY.script_relative_path,
            "script_byte_length": PROBE_IDENTITY.script_byte_length,
            "script_sha256": PROBE_IDENTITY.script_sha256,
            "powershell_path": PROBE_IDENTITY.powershell_path,
            "powershell_byte_length": PROBE_IDENTITY.powershell_byte_length,
            "powershell_sha256": PROBE_IDENTITY.powershell_sha256,
        },
    }
    path = tmp_path / "boundary.json"
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("ascii")
    path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    evidence = subject.PreExposureBoundaryEvidence.load(path, expected_sha256=digest)
    assert evidence.host_local == HOST_LOCAL
    value["network_tcp_egress_denied"] = False
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(subject.RuntimeWindowError):
        subject.PreExposureBoundaryEvidence.load(path, expected_sha256=digest)
    value["network_tcp_egress_denied"] = True
    value["host_local_endpoint_reachable"] = True
    legacy_payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode(
        "ascii"
    )
    path.write_bytes(legacy_payload)
    with pytest.raises(subject.RuntimeWindowError) as caught:
        subject.PreExposureBoundaryEvidence.load(
            path, expected_sha256=hashlib.sha256(legacy_payload).hexdigest()
        )
    assert caught.value.code == subject.PAIR_INVALID
    value["host_local_endpoint_reachable"] = "REACHABLE"
    value["schema"] = "solo-r2-pre-exposure-boundary/v2"
    old_schema_payload = json.dumps(
        value, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    path.write_bytes(old_schema_payload)
    with pytest.raises(subject.RuntimeWindowError):
        subject.PreExposureBoundaryEvidence.load(
            path,
            expected_sha256=hashlib.sha256(old_schema_payload).hexdigest(),
        )


def test_boundary_evidence_create_once_and_producer_round_trip(tmp_path: Path) -> None:
    path = (tmp_path / "boundary.json").resolve()
    producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=path,
        observation_source=PassingBoundarySource(),
    )
    result = SimpleNamespace()
    evidence = producer.produce(  # type: ignore[arg-type]
        result=result,
        generation=GENERATION_B,
    )
    evidence.validate()
    assert evidence.credential_sentinel_visible is False
    assert evidence.network_tcp_egress_denied is True
    assert evidence.host_local == HOST_LOCAL
    assert evidence.off_host_control_endpoint == OFF_HOST_ENDPOINT
    assert evidence.qualification_probe == PROBE_IDENTITY
    assert subject.PreExposureBoundaryEvidence.load(
        path,
        expected_sha256=evidence.evidence_sha256,
    ) == evidence
    with pytest.raises(subject.RuntimeWindowError):
        producer.produce(result=result, generation=GENERATION_B)  # type: ignore[arg-type]
    with pytest.raises(subject.RuntimeWindowError):
        subject.PreExposureBoundaryEvidence.create_once(
            path,
            credential_sentinel_visible=False,
            network_tcp_egress_denied=True,
            host_local=HOST_LOCAL,
            off_host_control_endpoint=OFF_HOST_ENDPOINT,
            qualification_probe=PROBE_IDENTITY,
        )


@pytest.mark.parametrize(
    "changes, expected_code",
    (
        ({"credential_read": "UNAVAILABLE"}, subject.PAIR_INVALID),
        ({"launcher_egress_pre_reachable": False}, subject.PAIR_INVALID),
        ({"child_egress_connect": "CONNECTED"}, subject.PAIR_INVALID),
        ({"launcher_egress_post_reachable": False}, subject.PAIR_INVALID),
        ({"host_local_tcp": None}, subject.HOST_LOCAL_OBSERVATION_UNAVAILABLE),
        ({"observed_host_listener_count": None}, subject.PAIR_INVALID),
        ({"observed_host_listener_count": 1}, subject.PAIR_INVALID),
        ({"runtime_endpoint_inputs": ("tcp://host:1",)}, subject.PAIR_INVALID),
    ),
)
def test_boundary_producer_fails_closed_on_unusable_observation(
    tmp_path: Path,
    changes: dict[str, object],
    expected_code: str,
) -> None:
    values: dict[str, object] = {
        "credential_read": "DENIED",
        "launcher_egress_pre_reachable": True,
        "child_egress_connect": "BLOCKED",
        "launcher_egress_post_reachable": True,
        "host_local_tcp": _host_local_tcp(),
        "observed_host_listener_count": 0,
        "runtime_endpoint_inputs": (),
        "off_host_control_endpoint": OFF_HOST_ENDPOINT,
        "qualification_probe": PROBE_IDENTITY,
    }
    values.update(changes)

    def source(**kwargs) -> subject.PreExposureBoundaryObservation:
        del kwargs
        return subject.PreExposureBoundaryObservation(**values)  # type: ignore[arg-type]

    path = (tmp_path / "boundary.json").resolve()
    producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=path,
        observation_source=source,
    )
    with pytest.raises(subject.RuntimeWindowError) as caught:
        producer.produce(result=SimpleNamespace(), generation=GENERATION_B)  # type: ignore[arg-type]
    assert caught.value.code == expected_code
    assert not path.exists()


def test_current_host_local_source_is_an_explicit_stop(tmp_path: Path) -> None:
    path = (tmp_path / "boundary.json").resolve()
    producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=path,
        observation_source=subject.HostLocalObservationUnavailable(),
    )
    with pytest.raises(subject.RuntimeWindowError) as caught:
        producer.produce(result=SimpleNamespace(), generation=GENERATION_B)  # type: ignore[arg-type]
    assert caught.value.code == subject.HOST_LOCAL_OBSERVATION_UNAVAILABLE
    assert not path.exists()


@pytest.mark.parametrize(
    "changes, expected",
    (
        ({}, HostLocalEndpointDisposition.REACHABLE),
        (
            {
                "child_connect": "CONNECTION_FAILED",
                "listener_outcome": "NO_CONNECTION",
                "listener_payload": None,
            },
            HostLocalEndpointDisposition.BLOCKED,
        ),
        ({"listener_outcome": "TIMEOUT"}, HostLocalEndpointDisposition.UNRESOLVED),
        ({"child_connect": "failed somehow"}, HostLocalEndpointDisposition.UNRESOLVED),
        ({"launcher_pre_reachable": False}, HostLocalEndpointDisposition.UNRESOLVED),
        ({"launcher_post_reachable": False}, HostLocalEndpointDisposition.UNRESOLVED),
        (
            {"listener_payload": "2" * 32},
            HostLocalEndpointDisposition.UNRESOLVED,
        ),
        ({"listener_payload": None}, HostLocalEndpointDisposition.UNRESOLVED),
        (
            {"same_child_required_probes_passed": False},
            HostLocalEndpointDisposition.UNRESOLVED,
        ),
        ({"listener_outcome": "UNKNOWN"}, HostLocalEndpointDisposition.UNRESOLVED),
    ),
)
def test_host_local_tcp_facts_classify_without_treating_unknown_as_safe(
    changes: dict[str, object],
    expected: HostLocalEndpointDisposition,
) -> None:
    assert _host_local_tcp(**changes).classify() is expected


def test_blocked_host_local_observation_creates_resolved_boundary_evidence(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "boundary.json").resolve()

    def source(**kwargs) -> subject.PreExposureBoundaryObservation:
        del kwargs
        return subject.PreExposureBoundaryObservation(
            "DENIED",
            True,
            "BLOCKED",
            True,
            _host_local_tcp(
                child_connect="CONNECTION_FAILED",
                listener_outcome="NO_CONNECTION",
                listener_payload=None,
            ),
            0,
            (),
            OFF_HOST_ENDPOINT,
            PROBE_IDENTITY,
        )

    evidence = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=path,
        observation_source=source,
    ).produce(result=SimpleNamespace(), generation=GENERATION_B)  # type: ignore[arg-type]
    assert evidence.host_local.host_local_endpoint_reachable is (
        HostLocalEndpointDisposition.BLOCKED
    )
    assert evidence.host_local.observed_host_listener_count == 0
    assert evidence.host_local.runtime_endpoint_inputs == ()
    assert subject.PreExposureBoundaryEvidence.load(
        path, expected_sha256=evidence.evidence_sha256
    ) == evidence


def test_unresolved_host_local_observation_cannot_create_boundary_evidence(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "boundary.json").resolve()

    def source(**kwargs) -> subject.PreExposureBoundaryObservation:
        del kwargs
        return subject.PreExposureBoundaryObservation(
            "DENIED",
            True,
            "BLOCKED",
            True,
            _host_local_tcp(listener_outcome="TIMEOUT"),
            0,
            (),
            OFF_HOST_ENDPOINT,
            PROBE_IDENTITY,
        )

    producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=path,
        observation_source=source,
    )
    with pytest.raises(subject.RuntimeWindowError) as caught:
        producer.produce(result=SimpleNamespace(), generation=GENERATION_B)  # type: ignore[arg-type]
    assert caught.value.code == subject.HOST_LOCAL_OBSERVATION_UNAVAILABLE
    assert not path.exists()


def test_provision_freeze_qualification_and_sealed_pre_attempt_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    monkeypatch.setattr(subject, "resolve_codex_payload", lambda: executable)
    for name in (
        "codex-home",
        "provision-workspace",
        "provision-output",
        "qualification-workspace",
        "qualification-output",
    ):
        (tmp_path / name).mkdir()
    observations = 0

    def generation_probe() -> SandboxGenerationFingerprint:
        nonlocal observations
        observations += 1
        return GENERATION_A if observations == 1 else GENERATION_B

    boundary_path = (tmp_path / "boundary.json").resolve()
    boundary_producer = subject.PreExposureBoundaryEvidenceProducer(
        evidence_path=boundary_path,
    )
    credential_sentinel = (tmp_path / subject._CREDENTIAL_SENTINEL_NAME).resolve()
    credential_sentinel.write_text("c" * 32, encoding="ascii")
    listener = FakeLocalBoundaryListener(
        workspace=(tmp_path / "qualification-workspace").resolve(),
        payload="EXPECTED",
    )
    transport = FakeBoundaryTransport(listener)
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_PATH", executable.path)
    monkeypatch.setattr(
        subject, "WINDOWS_POWERSHELL_BYTE_LENGTH", executable.byte_length
    )
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_SHA256", executable.sha256)
    boundary_probe = subject.MachineBackedBoundaryProbe(
        off_host_control_endpoint=OFF_HOST_ENDPOINT,
        credential_sentinel_path=credential_sentinel,
        transport=transport,
    )
    identity = RuntimeIdentity(
        "gpt-5.6-sol",
        "high",
        "UNAVAILABLE_NOT_INDEPENDENTLY_ATTESTED",
        f"sha256:{executable.sha256}",
        "host-bound-by-exclusive-window",
        IDENTITY_DISPOSITION,
    )
    native = NativeBackendDouble(executable)
    backend = subject.NativePreExposureObservationBackend(
        native_backend=native,  # type: ignore[arg-type]
        codex_home=(tmp_path / "codex-home").resolve(),
        provisioning_workspace=(tmp_path / "provision-workspace").resolve(),
        provisioning_output=(tmp_path / "provision-output").resolve(),
        qualification_workspace=(tmp_path / "qualification-workspace").resolve(),
        qualification_output=(tmp_path / "qualification-output").resolve(),
        whoami=executable,
        runtime_identity=identity,
        boundary_producer=boundary_producer,
        boundary_probe=boundary_probe,
        generation_probe=generation_probe,
    )
    adapter = subject.CodexRunnerAdapter(
        executable=executable,
        backend=backend,
        expected_catalog=CATALOG,
        codex_home=(tmp_path / "codex-home").resolve(),
        temp_root=tmp_path.resolve(),
        sandbox_generation_probe=lambda: GENERATION_B,
    )
    ledger_path = _ledger_copy(tmp_path)
    before = ledger_path.read_bytes()
    pair_lock = PairLedgerLock(
        ledger_path=ledger_path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(ledger_path),
        expected_ledger_sha256=hashlib.sha256(before).hexdigest(),
    )
    state = _order_state(pair_lock.binding)
    package_path = (tmp_path / "sealed-controller.json").resolve()
    package_path.write_bytes(b"sealed\n")
    monkeypatch.setattr(
        controller_state, "open_controller_package", lambda *args, **kwargs: state
    )
    sealed_order = subject.SealedArmOrder.from_sealed_package(
        package_path,
        key_path=(tmp_path / "external-key.json").resolve(),
        custody_boundary=object(),  # type: ignore[arg-type]
        expected_digest="6" * 64,
        pair_lock=pair_lock,
    )
    assert sealed_order.ordinals() == (2, 1)
    repository_root = (tmp_path / "materialization-repository").resolve()
    repository_root.mkdir()
    leaves = LeafWorkspaceManager(
        (tmp_path / "materialization-leaves").resolve(),
        acl_probe=lambda path: LeafAclObservation(
            path,
            OFFLINE_SID,
            GENERATION_B.value,
            True,
            True,
        ),
    )
    materializer = FrozenGitMaterializer(
        git=executable,
        repository=RepositoryBinding(repository_root, repository_root, repository_root),
        leaves=leaves,
        packet=TreatmentInstruction.load(PACKET),
    )

    archive_bytes = BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:") as archive:
        payload = b"source\n"
        info = tarfile.TarInfo("source.txt")
        info.size = len(payload)
        archive.addfile(info, BytesIO(payload))

    def fake_materialization_git(executable, binding, args, *, temp_root):
        del executable, binding, temp_root
        if args[:2] == ("rev-parse", "--verify"):
            return (FROZEN_BASE_COMMIT + "\n").encode("ascii")
        if args[:2] == ("archive", "--format=tar"):
            return archive_bytes.getvalue()
        raise AssertionError(args)

    monkeypatch.setattr(materialization_subject, "verify_repository_binding", lambda *args, **kwargs: None)
    monkeypatch.setattr(materialization_subject, "_run_git", fake_materialization_git)
    freeze_probe = FreezeProbeDouble(
        pair_lock,
        _freeze(executable, pair_lock.binding, GENERATION_B),
        executable,
    )
    window = subject.PreAttemptFrozenRuntimeWindow(
        backend=backend,
        adapter=adapter,
        freeze_probe=freeze_probe,  # type: ignore[arg-type]
        materializer=materializer,
        pair_lock=pair_lock,
        sealed_order=sealed_order,
    )

    result = window.run()

    assert result.disposition == subject.READY_BEFORE_ATTEMPT
    assert result.next_arm == "TREATMENT"
    assert result.next_arm_ordinal == 2
    assert result.attempt_handle is None
    assert result.task_exposure_state == "NONE"
    assert result.target_pair_attempt_events == 0
    assert result.provisioning.generation_changed is True
    assert result.validation.initiated_attempt_count == 0
    assert backend.prepared_ordinals == (2, 1)
    assert native.calls == 2
    assert native.non_git_options == [True, True]
    assert all(
        isinstance(value, subject.ProvisioningExecutionPreparation)
        for value in native.preparations
    )
    assert all(not hasattr(value, "host_local") for value in native.preparations)
    assert backend.boundary_evidence is not None
    assert backend.boundary_evidence.off_host_control_endpoint == OFF_HOST_ENDPOINT
    assert backend.boundary_evidence.qualification_probe.powershell_path == str(
        executable.path
    )
    assert boundary_path.is_file()
    assert listener.closed is True
    assert result.materialization.host_local == backend.require_boundary_evidence().host_local
    assert materializer.leaves.active is None
    assert freeze_probe.checks == 5
    assert freeze_probe.quiescence_checks == 1
    assert ledger_path.read_bytes() == before
    assert not pair_lock.lock_path.exists()


def test_sealed_order_cannot_be_constructed_without_validated_state() -> None:
    with pytest.raises(TypeError):
        subject.SealedArmOrder(("CONTROL", "TREATMENT"))  # type: ignore[call-arg]


@pytest.mark.skipif(os.name != "nt", reason="Windows process inventory contract")
def test_windows_quiescence_rejects_visible_codex_family_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = PinnedExecutable.capture(Path(sys.executable).resolve())
    monkeypatch.setattr(
        subject.PinnedExecutable,
        "capture",
        classmethod(lambda cls, path: executable),
    )
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_BYTE_LENGTH", executable.byte_length)
    monkeypatch.setattr(subject, "WINDOWS_POWERSHELL_SHA256", executable.sha256)
    probe = subject.WindowsCodexRuntimeQuiescence(temp_root=tmp_path.resolve())
    monkeypatch.setattr(
        subject,
        "_run_contained_once",
        lambda *args, **kwargs: ProcessResult(0, b"[]\r\n", b"", False, True),
    )
    probe()
    monkeypatch.setattr(
        subject,
        "_run_contained_once",
        lambda *args, **kwargs: ProcessResult(
            0,
            b'[{"name":"ChatGPT.exe","process_id":123}]\r\n',
            b"",
            False,
            True,
        ),
    )
    with pytest.raises(subject.RuntimeWindowError) as caught:
        probe()
    assert caught.value.code == subject.SAME_MACHINE_WINDOW_REJECTED
