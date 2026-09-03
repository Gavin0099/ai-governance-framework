from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import os
import sys

import pytest

from governance_tools import solo_r2_codex_runner as subject
from governance_tools.solo_r2_attempt_materialization import (
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
HOST_LOCAL = HostLocalIsolation(True, 0)
IDENTITY = subject.RuntimeIdentity(
    subject.MODEL_SELECTOR,
    subject.REASONING_EFFORT,
    "UNAVAILABLE",
    "codex-cli-0.146.0",
    "host-a",
    subject.IDENTITY_DISPOSITION,
)


class Backend:
    def __init__(self) -> None:
        self.canary = subject.CanaryObservation(
            context_id="canary-context",
            workspace_id="canary-workspace",
            runtime_identity=IDENTITY,
            execution_policy=subject.REQUIRED_EXECUTION_POLICY,
            configured_tool_inventory=CATALOG.public_inventory(),
            catalog_sha256=CATALOG.catalog_sha256,
            credential_sentinel_visible=False,
            network_tcp_egress_denied=True,
            host_local=HOST_LOCAL,
            sandbox_principal="CodexSandboxOffline",
            sandbox_account_generation="generation-1",
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
            sandbox_principal="CodexSandboxOffline",
            sandbox_account_generation="generation-1",
            credential_sentinel_visible=False,
            host_local=HOST_LOCAL,
        )


def _adapter(tmp_path: Path, backend: Backend | None = None) -> subject.CodexRunnerAdapter:
    return subject.CodexRunnerAdapter(
        executable=PinnedExecutable.capture(Path(sys.executable).resolve()),
        backend=backend or Backend(),
        expected_catalog=CATALOG,
        codex_home=(tmp_path / "codex-home").resolve(),
        temp_root=tmp_path.resolve(),
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
        "CodexSandboxOffline",
        "generation-1",
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
    assert policy.tool_call_cap_enforcement == "MEASURED_POST_HOC"
    assert policy.hard_pre_dispatch_cap == "NOT_CLAIMED"


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
        assert command[1:4] == ("-c", "model_reasoning_effort=high", "exec")
        assert "--json" in command and "--ignore-user-config" in command
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
        lambda: subject.SandboxProcessIdentity(
            "CodexSandboxOffline", "generation-1", "MEDIUM", False
        ),
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
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


def test_security_identity_mismatch_denies_before_process_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        lambda: subject.SandboxProcessIdentity(
            "Administrator", "generation-1", "HIGH", True
        ),
    )
    backend = subject.NativeCodexExecBackend(
        executable=executable,
        configured_catalog=CATALOG,
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
