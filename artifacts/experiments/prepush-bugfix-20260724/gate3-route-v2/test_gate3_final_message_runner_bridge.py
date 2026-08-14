from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import gate3_final_message_actual_capture as capture
import gate3_final_message_runner_bridge as bridge
import gate3_final_message_runner_integration as integration


STDOUT_CANARY = b"PRIVATE_STDOUT_CANARY"
STDERR_CANARY = b"PRIVATE_STDERR_CANARY"
RAW_COMPLETE = (
    b'{"type":"thread.started"}\n'
    b'{"type":"turn.started"}\n'
    b'{"item":{"text":"PRIVATE_STDOUT_CANARY","type":"agent_message"},'
    b'"type":"item.completed"}\n'
    b'{"type":"turn.completed"}\n'
)
RUNTIME_BYTES = {
    "runner_source": b"synthetic runner source\n",
    "integration_source": b"synthetic integration source\n",
    "adapter_source": Path(capture.__file__).read_bytes(),
    "adapter_contract": capture.ADAPTER_CONTRACT_BYTES,
    "raw_contract": capture.RAW_ENVELOPE_CONTRACT_BYTES,
    "projector_contract": capture.PROJECTOR_CONTRACT_BYTES,
    "public_schemas": capture.canonical_bytes(capture.public_schema_sha256()),
}
SYNTHETIC_BASELINE = {"notes.md": b"baseline\n", "src/app.py": b"print(1)\n"}


@dataclass(frozen=True)
class FakeContained:
    """Shape-compatible stand-in for the runner's private contained result.

    The generated ``repr`` is replaced by a closed token.  The real
    ``_ContainedResult`` and ``InjectedContainedResult`` are ordinary dataclasses
    whose ``repr`` renders raw stdout, and a failing assertion here would
    otherwise print it into the test log — the exact leak the design flags as
    needing a structural fix before production wiring.
    """

    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    tree_terminated: bool

    def __repr__(self) -> str:
        return "<FakeContained redacted>"


def contained(
    *,
    raw: bytes = RAW_COMPLETE,
    returncode: int = 0,
    timed_out: bool = False,
    tree_terminated: bool = True,
) -> FakeContained:
    return FakeContained(
        returncode=returncode,
        stdout=raw,
        stderr=STDERR_CANARY,
        timed_out=timed_out,
        tree_terminated=tree_terminated,
    )


def bindings() -> capture.CaptureBindings:
    return capture.synthetic_bindings()


def authority() -> integration.RuntimeAuthority:
    current = bindings()
    return integration.RuntimeAuthority(
        action_sha256=current.action_sha256,
        arm=current.arm,
        git_commit="e7410b3469d4e3112904b4f822180e51d5c1a3ea",
        runner_blob="d308331cc59cfce50604488a2ab9121727338fd7886c61a7f2e6fa6b5b2af7e8",
        integration_blob="d0d1609bc111bb8cef28f8442f80beddeb6ad87744be9e74723d3e11126a19fd",
        integration_contract_sha256=capture.sha256(
            integration.RUNNER_INTEGRATION_CONTRACT_BYTES
        ),
        capture_bindings_sha256=capture.sha256(
            capture.canonical_bytes(current.authorization())
        ),
        runtime_sha256={
            name: capture.sha256(payload) for name, payload in RUNTIME_BYTES.items()
        },
    )


def readers() -> dict[str, object]:
    return {
        name: (lambda payload=payload: payload)
        for name, payload in RUNTIME_BYTES.items()
    }


class FakePreparation:
    """Records preparation without writing credential bytes anywhere."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def coordinator(
    *,
    capture_store: capture.CreateOnceStore | None = None,
    evidence_store: capture.CreateOnceStore | None = None,
    invoke=None,
    observe_final=None,
    observe_workspace=None,
) -> integration.RunnerIntegrationCoordinator:
    return integration.RunnerIntegrationCoordinator(
        capture_store=capture_store or capture.CreateOnceStore(),
        evidence_store=evidence_store or capture.CreateOnceStore(),
        bindings=bindings(),
        authority=authority(),
        runtime_readers=readers(),
        invoke=invoke or bridge.make_invoke(
            prepare=FakePreparation(), run_contained=contained
        ),
        observe_final=observe_final or (lambda: bridge.FINAL_CAPTURED),
        observe_workspace=observe_workspace or (lambda: bridge.WORKSPACE_CHANGED),
        cleanup=lambda: "PASS",
    )


# --- mapping ---------------------------------------------------------------


def test_exited_mapping_forwards_returncode_and_validates() -> None:
    injected = bridge.map_contained_result(contained(returncode=3))
    assert injected.process_disposition == "EXITED"
    assert injected.returncode == 3
    result = injected.process_result()
    capture.validate_process_result(result)
    assert result["exit_code"] == 3
    assert result["stdout_read_failed"] is False


def test_timeout_mapping_drops_returncode_that_would_fail_validation() -> None:
    injected = bridge.map_contained_result(contained(returncode=137, timed_out=True))
    assert injected.process_disposition == "TIMED_OUT"
    assert injected.returncode is None
    capture.validate_process_result(injected.process_result())

    with pytest.raises(capture.CaptureError):
        capture.build_process_result(
            exit_code=137, process_disposition="TIMED_OUT"
        )


def test_incomplete_tree_termination_is_closed_and_never_terminated_row() -> None:
    with pytest.raises(bridge.BridgeError) as caught:
        bridge.map_contained_result(contained(tree_terminated=False))
    assert caught.value.code == "CONTAINED_TERMINATION_INCOMPLETE"


@pytest.mark.parametrize(
    "broken",
    [
        object(),
        FakeContained(0, "not bytes", b"", False, True),
        FakeContained(None, RAW_COMPLETE, b"", False, True),
    ],
)
def test_malformed_contained_results_fail_closed(broken: object) -> None:
    with pytest.raises(bridge.BridgeError) as caught:
        bridge.map_contained_result(broken)
    assert caught.value.code == "CONTAINED_RESULT_INVALID"


# --- privacy ---------------------------------------------------------------


def test_stderr_is_dropped_and_never_reaches_the_seam() -> None:
    injected = bridge.map_contained_result(contained())
    assert injected.stderr == b""
    assert STDERR_CANARY not in capture.canonical_bytes(injected.process_result())


def test_stdout_object_identity_is_forwarded_and_not_copied() -> None:
    raw = bytes(RAW_COMPLETE)
    injected = bridge.map_contained_result(contained(raw=raw))
    assert injected.stdout is raw


def test_stdout_reaches_the_publisher_once_and_is_retained_nowhere(
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = bytes(RAW_COMPLETE)
    seen: list[bytes] = []
    original = capture.CapturePublisher.capture

    def recording(self, stdout, process_result, current_bindings):
        seen.append(stdout)
        return original(self, stdout, process_result, current_bindings)

    capture.CapturePublisher.capture = recording
    try:
        current = coordinator(
            invoke=bridge.make_invoke(
                prepare=FakePreparation(),
                run_contained=lambda: contained(raw=raw),
            )
        )
        result = current.run()
    finally:
        capture.CapturePublisher.capture = original

    assert len(seen) == 1 and seen[0] is raw
    for store in (current.capture_store, current.evidence_store):
        for payload in store.files.values():
            assert STDOUT_CANARY not in payload
            assert STDERR_CANARY not in payload
    assert result.claim == capture.PUBLIC_CLAIM
    captured = capsys.readouterr()
    assert STDOUT_CANARY.decode() not in captured.out + captured.err
    assert STDERR_CANARY.decode() not in captured.out + captured.err


def test_closed_errors_never_render_private_bytes() -> None:
    with pytest.raises(bridge.BridgeError) as caught:
        bridge.map_contained_result(contained(tree_terminated=False))
    rendered = str(caught.value) + repr(caught.value)
    assert STDOUT_CANARY.decode() not in rendered
    assert STDERR_CANARY.decode() not in rendered


# --- invocation and fail-closed -------------------------------------------


def test_generic_failure_is_unknown_and_publishes_no_capture_result() -> None:
    def exploding() -> object:
        raise OSError(STDOUT_CANARY.decode())

    current = coordinator(
        invoke=bridge.make_invoke(
            prepare=FakePreparation(), run_contained=exploding
        )
    )
    with pytest.raises(integration.IntegrationError) as caught:
        current.run()
    assert caught.value.code == "INVOCATION_DISPOSITION_UNKNOWN"
    assert capture.CAPTURE_RESULT_PATH not in current.capture_store.files
    assert (
        integration.reconstruct_profile(
            current.capture_store, current.evidence_store
        )
        == "RUNNER_CAPTURE_RESULT_UNKNOWN"
    )


def test_bridge_never_claims_start_failed_from_an_opaque_failure() -> None:
    def exploding() -> object:
        raise RuntimeError("process creation may or may not have happened")

    invoke = bridge.make_invoke(
        prepare=FakePreparation(), run_contained=exploding
    )
    with pytest.raises(RuntimeError) as caught:
        invoke()
    assert not isinstance(caught.value, integration.ContainedStartFailed)


def test_invocation_and_preparation_happen_exactly_once() -> None:
    prepare = FakePreparation()
    calls = {"run": 0}

    def counting() -> FakeContained:
        calls["run"] += 1
        return contained()

    current = coordinator(
        invoke=bridge.make_invoke(prepare=prepare, run_contained=counting)
    )
    current.run()
    assert prepare.calls == 1 and calls["run"] == 1


def test_preparation_runs_before_the_contained_call() -> None:
    order: list[str] = []

    def prepare() -> None:
        order.append("prepare")

    def run() -> FakeContained:
        order.append("run")
        return contained()

    bridge.make_invoke(prepare=prepare, run_contained=run)()
    assert order == ["prepare", "run"]


# --- observations ----------------------------------------------------------


def test_final_observation_tokens_are_closed() -> None:
    def raising() -> bytes:
        raise OSError("unreadable")

    assert bridge.make_observe_final(lambda: b"{}")() == bridge.FINAL_CAPTURED
    assert bridge.make_observe_final(lambda: None)() == bridge.FINAL_ABSENT
    assert bridge.make_observe_final(raising)() == bridge.FINAL_READ_FAILED
    assert bridge.make_observe_final(lambda: "text")() == bridge.FINAL_READ_FAILED


def test_workspace_observation_tokens_are_closed() -> None:
    def raising() -> dict[str, bytes]:
        raise OSError("unreadable")

    unchanged = bridge.make_observe_workspace(
        lambda: dict(SYNTHETIC_BASELINE), SYNTHETIC_BASELINE
    )
    changed = bridge.make_observe_workspace(
        lambda: {**SYNTHETIC_BASELINE, "notes.md": b"edited\n"}, SYNTHETIC_BASELINE
    )
    failed = bridge.make_observe_workspace(raising, SYNTHETIC_BASELINE)
    assert unchanged() == bridge.WORKSPACE_UNCHANGED
    assert changed() == bridge.WORKSPACE_CHANGED
    assert failed() == bridge.WORKSPACE_CAPTURE_FAILED


def test_workspace_baseline_shape_is_validated() -> None:
    with pytest.raises(bridge.BridgeError) as caught:
        bridge.make_observe_workspace(lambda: {}, {"notes.md": "not bytes"})
    assert caught.value.code == "WORKSPACE_BASELINE_INVALID"


def test_observations_cannot_reach_stdout() -> None:
    """The observation axes take no argument and close over no stdout."""

    raw = bytes(RAW_COMPLETE)
    injected = bridge.map_contained_result(contained(raw=raw))
    observe_final = bridge.make_observe_final(lambda: b"{}")
    observe_workspace = bridge.make_observe_workspace(
        lambda: dict(SYNTHETIC_BASELINE), SYNTHETIC_BASELINE
    )

    for observe in (observe_final, observe_workspace):
        assert observe.__code__.co_argcount == 0
        for cell in observe.__closure__ or ():
            assert cell.cell_contents is not raw
            assert cell.cell_contents is not injected

    assert observe_final() == bridge.FINAL_CAPTURED
    assert observe_workspace() == bridge.WORKSPACE_UNCHANGED


def test_complete_capture_with_unchanged_workspace_is_negative() -> None:
    current = coordinator(
        observe_workspace=bridge.make_observe_workspace(
            lambda: dict(SYNTHETIC_BASELINE), SYNTHETIC_BASELINE
        )
    )
    result = current.run()
    assert result.capture_status == "COMPLETE"
    assert result.profile == "RUNNER_CAPTURE_NEGATIVE"


# --- boundaries the tranche must not cross --------------------------------


def test_runner_call_path_is_untouched_and_bridge_is_not_a_trusted_runner() -> None:
    route = pytest.importorskip("gate3_route_v2")
    codex = pytest.importorskip("gate3_route_v2_codex")

    assert codex._TRUSTED_CODEX_INVOKE is codex.CodexExecRunner.__call__

    invoke = bridge.make_invoke(
        prepare=FakePreparation(), run_contained=contained
    )
    with pytest.raises(route.RouteV2Error):
        route._trusted_live_runner(
            execution_identity={},
            preflight=b"",
            invoke=invoke,
        )


def test_bridge_exposes_no_authority_surface() -> None:
    assert not [name for name in dir(bridge) if "authority" in name.lower()]
    assert "bridge_source" not in integration.RUNTIME_SUBJECTS


def test_mapping_tranche_uses_in_memory_fake_preparation() -> None:
    """The preparation reached by this tranche is the in-memory fake, called once.

    This asserts only that ``FakePreparation`` ran and that its implementation
    updates a counter and nothing else.  It is **not** credential-write
    detection: it cannot observe an arbitrary preparation writing credentials on
    some other path.  That guarantee belongs to the production credential-residue
    tranche, not here.
    """

    prepare = FakePreparation()
    current = coordinator(
        invoke=bridge.make_invoke(prepare=prepare, run_contained=contained)
    )
    current.run()
    assert prepare.calls == 1
    assert vars(prepare) == {"calls": 1}


def test_public_claim_ceiling_is_unchanged() -> None:
    current = coordinator()
    result = current.run()
    assert result.claim == capture.PUBLIC_CLAIM == integration.PUBLIC_CLAIM
    assert (
        capture.verify_public(current.capture_store, bindings()).claim
        == capture.PUBLIC_CLAIM
    )
