from __future__ import annotations

import copy
from pathlib import Path

import pytest

import gate3_final_message_actual_capture as capture
import gate3_final_message_runner_integration as integration


RAW_COMPLETE = (
    b'{"type":"thread.started"}\n'
    b'{"type":"turn.started"}\n'
    b'{"item":{"text":"PRIVATE_STDOUT_CANARY","type":"agent_message"},"type":"item.completed"}\n'
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
EXPECTED_INTEGRATION_CONTRACT_BYTES = (
    b'{"checkpoints":["before_authorization","before_invocation",'
    b'"before_private_parse","before_seal"],'
    b'"cleanup_protocol":"CREATE_ONCE_AUTHORIZATION_THEN_RESULT_NO_RETRY",'
    b'"launch_ordinal":1,'
    b'"observation_protocol":"CREATE_ONCE_CHAIN_AUTHORIZATION_BEFORE_LAUNCH",'
    b'"profiles":["RUNNER_CAPTURE_FINALIZED","RUNNER_CAPTURE_NEGATIVE",'
    b'"RUNNER_CAPTURE_RESULT_UNKNOWN","RUNNER_SEAL_UNAVAILABLE"],'
    b'"replacement":false,"retry":false,"runtime_subjects":['
    b'"adapter_contract","adapter_source","integration_source",'
    b'"projector_contract","public_schemas","raw_contract","runner_source"],'
    b'"schema":"gate3-route-v2.runner-integration-contract.v1",'
    b'"stdout_handoff_count":1}\n'
)
EXPECTED_PUBLIC_CHAIN_BYTES = {
    "final-output-observation.json": (
        b'{"schema":"gate3-route-v2.final-output-observation.v1",'
        b'"state":"CAPTURED"}\n'
    ),
    "workspace-observation.json": (
        b'{"schema":"gate3-route-v2.workspace-observation.v1",'
        b'"state":"CHANGED"}\n'
    ),
    "runner-cleanup-result.json": (
        b'{"result":"PASS","schema":"gate3-route-v2.runner-cleanup-result.v1",'
        b'"seal_sha256":"a401a6ed35bb713985367ec55fa9c1166eb03a957480c24ecfa01173d3ffe0d4"}\n'
    ),
    "runner-cleanup-authorization.json": (
        b'{"attempt_ordinal":1,"profile":"RUNNER_CAPTURE_FINALIZED","retry":false,'
        b'"schema":"gate3-route-v2.runner-cleanup-authorization.v1",'
        b'"seal_sha256":"a401a6ed35bb713985367ec55fa9c1166eb03a957480c24ecfa01173d3ffe0d4"}\n'
    ),
    "runner-receipt.json": (
        b'{"cleanup_sha256":"93a83580706b3023662a0fdcd0ab5c25e777615736d2d8827aedee5796297be3",'
        b'"disposition":"DIAGNOSTIC_RECEIPT","profile":"RUNNER_CAPTURE_FINALIZED",'
        b'"schema":"gate3-route-v2.runner-receipt.v1",'
        b'"seal_sha256":"a401a6ed35bb713985367ec55fa9c1166eb03a957480c24ecfa01173d3ffe0d4"}\n'
    ),
    "runner-finalization.json": (
        b'{"disposition":"FINALIZED_DIAGNOSTIC","profile":"RUNNER_CAPTURE_FINALIZED",'
        b'"receipt_sha256":"fb834f85882e754388bb33018d9ae9a6fe4105cb06a5fbbaccfb145371f5a0d3",'
        b'"schema":"gate3-route-v2.runner-finalization.v1"}\n'
    ),
    "runner-observation-seal.json": (
        b'{"authority_sha256":"1235b265f88d1015e458eb864beef810355ea4e559d78f091d04c25fe64ece18",'
        b'"capture_artifact_sha256":{"capture-authorization.json":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9b676dc7e1d20b9bc0a23b5edf",'
        b'"capture-result.json":"d0f3610664cc28d1f528514e4377afe976b02407659f7c0fce67903ea21757d9",'
        b'"lifecycle-projection.json":"2f5675e7b589a5af94fe253d8a3a9301d807391e73c4449641d7de2cd46d5396",'
        b'"process-result.json":"e762121801d1561ce157df9de85c06060854e988176314e9875c663703f8a050"},'
        b'"capture_status":"COMPLETE","final_observation_sha256":"f052c4cdd94713533a6a7c3ff5d74968190224ca176f5867864acf026216d1b4",'
        b'"integration_contract_sha256":"efac9147b39cc5290fc60c7e3516bebc774c4c22c8b026658755e127614ccc91",'
        b'"observation_stage_sha256":"4b4bb2de9115282219fbef7c721413a35382c35a1cafec8fe0e521a0b551be07",'
        b'"profile":"RUNNER_CAPTURE_FINALIZED","schema":"gate3-route-v2.runner-observation-seal.v1",'
        b'"workspace_observation_sha256":"b1dd83d698aece172fbc8b6507161926c4535d6964dd81ae9b2d4722853f4ccf"}\n'
    ),
    "runner-observation-stage.json": (
        b'{"capture_authorization_sha256":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9b676dc7e1d20b9bc0a23b5edf",'
        b'"schema":"gate3-route-v2.observation-stage.v1",'
        b'"stage":"OBSERVATION_CHAIN_AUTHORIZED"}\n'
    ),
    "runner-integration-authority.json": (
        b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebdc3d89ee74a0170feb2",'
        b'"arm":"A","capture_bindings_sha256":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9b676dc7e1d20b9bc0a23b5edf",'
        b'"capture_ordinal":1,"git_commit":"e7410b3469d4e3112904b4f822180e51d5c1a3ea",'
        b'"integration_blob":"d0d1609bc111bb8cef28f8442f80beddeb6ad87744be9e74723d3e11126a19fd",'
        b'"integration_contract_sha256":"efac9147b39cc5290fc60c7e3516bebc774c4c22c8b026658755e127614ccc91",'
        b'"launch_ordinal":1,"replacement":false,"retry":false,'
        b'"runner_blob":"d308331cc59cfce50604488a2ab9121727338fd7886c61a7f2e6fa6b5b2af7e8",'
        b'"runtime_sha256":{"adapter_contract":"be06661ba87ecdb3255524aedf6df775f27b96b9a57c8a1c005150a0755c1206",'
        b'"adapter_source":"67d098138d2442f1c68aae462d350a7a461e191d831b8bea8799d3498ee1d99d",'
        b'"integration_source":"4785aa2413b1bcc4cd1cc5112c9520e53691fb14c07ab9cc0636f39f0af2510b",'
        b'"projector_contract":"e60f346e182e8c146e3aaadda2aa3c659abf22a03ae641b1c45769a81b0e3965",'
        b'"public_schemas":"eb47a6ce92326ab68a05f177c169cf99b93b971a0e39a77a96a797f497f1b26d",'
        b'"raw_contract":"6d04e7371b740435ad5aa2e10986e003d7157e7c0aef68de5f476f76afbc57eb",'
        b'"runner_source":"e9be4d2adae79c99a314d1b79f15339b41b2dacdeed1424e23724ed136c481ff"},'
        b'"schema":"gate3-route-v2.runner-integration-authority.v1"}\n'
    ),
}


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


def contained(*, raw: bytes = RAW_COMPLETE) -> integration.InjectedContainedResult:
    return integration.InjectedContainedResult(
        returncode=0,
        stdout=raw,
        stderr=b"PRIVATE_STDERR_CANARY",
    )


def coordinator(
    *,
    capture_store: capture.CreateOnceStore | None = None,
    evidence_store: capture.CreateOnceStore | None = None,
    invoke=None,
    runtime_readers=None,
    final_state: str = "CAPTURED",
    workspace_state: str = "CHANGED",
    cleanup=None,
    crash_at: str | None = None,
) -> integration.RunnerIntegrationCoordinator:
    return integration.RunnerIntegrationCoordinator(
        capture_store=capture_store or capture.CreateOnceStore(),
        evidence_store=evidence_store or capture.CreateOnceStore(),
        bindings=bindings(),
        authority=authority(),
        runtime_readers=runtime_readers or readers(),
        invoke=invoke or contained,
        observe_final=lambda: final_state,
        observe_workspace=lambda: workspace_state,
        cleanup=cleanup or (lambda: "PASS"),
        crash_at=crash_at,
    )


def run_complete(**kwargs):
    current = coordinator(**kwargs)
    result = current.run()
    return current, result


def replace(store: capture.CreateOnceStore, path: str, value: object) -> None:
    store.files[path] = capture.canonical_bytes(value)


def parsed(store: capture.CreateOnceStore, path: str) -> dict[str, object]:
    value = __import__("json").loads(store.read(path))
    assert isinstance(value, dict)
    return value


def test_complete_path_consumes_one_launch_and_verifies_closed_package() -> None:
    calls = 0

    def invoke() -> integration.InjectedContainedResult:
        nonlocal calls
        calls += 1
        return contained()

    current, result = run_complete(invoke=invoke)

    assert calls == 1
    assert result == integration.IntegrationResult(
        "RUNNER_CAPTURE_FINALIZED", "COMPLETE", capture.PUBLIC_CLAIM, "PASS"
    )
    assert integration.verify_package(
        current.capture_store, current.evidence_store, current.bindings, current.authority
    ) == integration.Verification(
        True, "VERIFIED", "RUNNER_CAPTURE_FINALIZED", capture.PUBLIC_CLAIM
    )


def test_public_contract_matches_independent_literal_bytes() -> None:
    current, _ = run_complete()

    assert integration.RUNNER_INTEGRATION_CONTRACT_BYTES == EXPECTED_INTEGRATION_CONTRACT_BYTES
    assert (
        current.evidence_store.read(integration.INTEGRATION_CONTRACT_PATH)
        == EXPECTED_INTEGRATION_CONTRACT_BYTES
    )


def test_complete_public_chain_matches_independent_literal_bytes() -> None:
    current, _ = run_complete()
    actual = dict(current.evidence_store.files)
    actual.pop(integration.INTEGRATION_CONTRACT_PATH)

    assert actual == EXPECTED_PUBLIC_CHAIN_BYTES


@pytest.mark.parametrize(
    ("raw", "final_state", "workspace_state"),
    (
        (b'{"type":"future.event"}\n', "CAPTURED", "CHANGED"),
        (RAW_COMPLETE, "ABSENT", "CHANGED"),
        (RAW_COMPLETE, "CAPTURED", "UNCHANGED"),
    ),
)
def test_negative_discriminator_is_derived_not_caller_selected(
    raw: bytes, final_state: str, workspace_state: str
) -> None:
    current, result = run_complete(
        invoke=lambda: contained(raw=raw),
        final_state=final_state,
        workspace_state=workspace_state,
    )

    assert result.profile == "RUNNER_CAPTURE_NEGATIVE"
    assert parsed(current.evidence_store, integration.RECEIPT_PATH)["disposition"] == "NEGATIVE_RECEIPT"
    assert integration.verify_package(
        current.capture_store, current.evidence_store, current.bindings, current.authority
    ).verified


def test_private_stdout_identity_is_handed_to_capture_once_and_never_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = bytearray(RAW_COMPLETE)
    raw_bytes = bytes(raw)
    seen: list[bytes] = []
    original = capture.CapturePublisher.capture

    def observe(self, private_raw, process_result, current_bindings):
        seen.append(private_raw)
        return original(self, private_raw, process_result, current_bindings)

    monkeypatch.setattr(capture.CapturePublisher, "capture", observe)
    current, result = run_complete(invoke=lambda: contained(raw=raw_bytes))
    public_bytes = b"".join(current.capture_store.files.values()) + b"".join(
        current.evidence_store.files.values()
    )

    assert seen == [raw_bytes]
    assert seen[0] is raw_bytes
    assert b"PRIVATE_STDOUT_CANARY" not in public_bytes
    assert b"PRIVATE_STDERR_CANARY" not in public_bytes
    assert not hasattr(result, "stdout")


def test_cleanup_is_not_called_until_seal_is_durable_and_reopened() -> None:
    capture_store = capture.CreateOnceStore()
    evidence_store = capture.CreateOnceStore()
    observations: list[str] = []

    def cleanup() -> str:
        payload = evidence_store.read(integration.SEAL_PATH)
        assert capture.sha256(payload)
        observations.append("cleanup")
        return "PASS"

    current = coordinator(
        capture_store=capture_store,
        evidence_store=evidence_store,
        cleanup=cleanup,
    )
    current.run()

    assert observations == ["cleanup"]
    assert integration.CLEANUP_PATH in evidence_store.files


def test_semantically_mutated_seal_blocks_cleanup_before_callback() -> None:
    class MutatingSealStore(capture.CreateOnceStore):
        seal_reads = 0

        def read(self, path: str) -> bytes:
            if path == integration.SEAL_PATH:
                self.seal_reads += 1
                if self.seal_reads == 2:
                    value = __import__("json").loads(self.files[path])
                    value["profile"] = "RUNNER_CAPTURE_NEGATIVE"
                    self.files[path] = capture.canonical_bytes(value)
            return super().read(path)

    evidence_store = MutatingSealStore()
    cleanup_calls = 0

    def cleanup() -> str:
        nonlocal cleanup_calls
        cleanup_calls += 1
        return "PASS"

    current = coordinator(evidence_store=evidence_store, cleanup=cleanup)
    with pytest.raises(integration.IntegrationError, match="SEAL_LINK_INVALID"):
        current.run()

    assert cleanup_calls == 0
    assert integration.CLEANUP_PATH not in evidence_store.files


@pytest.mark.parametrize(
    ("crash_at", "expected_calls"),
    (
        ("r0_before_runtime_check", 0),
        ("after_authorization_before_invoke", 0),
        ("before_invoke_entry", 0),
        ("after_invoke_before_capture", 1),
        ("after_capture_before_observations", 1),
        ("after_observations_before_seal", 1),
        ("after_seal_before_cleanup", 1),
    ),
)
def test_crash_invocation_boundary_is_zero_then_one_never_more(
    crash_at: str, expected_calls: int
) -> None:
    calls = 0

    def invoke() -> integration.InjectedContainedResult:
        nonlocal calls
        calls += 1
        return contained()

    current = coordinator(invoke=invoke, crash_at=crash_at)
    with pytest.raises(integration.SyntheticIntegrationCrash):
        current.run()

    assert calls == expected_calls
    assert calls <= 1
    if capture.AUTHORIZATION_PATH in current.capture_store.files:
        restarted = coordinator(
            capture_store=current.capture_store,
            evidence_store=current.evidence_store,
            invoke=invoke,
        )
        with pytest.raises(integration.IntegrationError, match="INTEGRATION_ALREADY_STARTED"):
            restarted.run()
        assert calls == expected_calls


def test_authorization_without_result_is_permanent_unknown_and_not_reinvoked() -> None:
    capture_store = capture.CreateOnceStore()
    evidence_store = capture.CreateOnceStore()
    current = coordinator(
        capture_store=capture_store,
        evidence_store=evidence_store,
        crash_at="after_authorization_before_invoke",
    )
    with pytest.raises(integration.SyntheticIntegrationCrash):
        current.run()

    assert integration.reconstruct_profile(capture_store, evidence_store) == "RUNNER_CAPTURE_RESULT_UNKNOWN"
    assert integration.verify_package(
        capture_store, evidence_store, current.bindings, current.authority
    ) == integration.Verification(
        True, "VERIFIED", "RUNNER_CAPTURE_RESULT_UNKNOWN", None
    )

    capture_store.files[capture.AUTHORIZATION_PATH] = b"{}\n"
    assert not integration.verify_package(
        capture_store, evidence_store, current.bindings, current.authority
    ).verified


def test_outer_authority_rejects_capture_binding_substitution() -> None:
    current = coordinator()
    object.__setattr__(
        current,
        "bindings",
        capture.CaptureBindings(
            executable_sha256=capture.sha256(b"substituted executable"),
            command_contract_sha256=capture.sha256(b"substituted command"),
            adapter_source_sha256=current.bindings.adapter_source_sha256,
            action_sha256=current.bindings.action_sha256,
            arm=current.bindings.arm,
        ),
    )

    with pytest.raises(integration.IntegrationError, match="INTEGRATION_AUTHORITY_MISMATCH"):
        current.run()


@pytest.mark.parametrize(
    "crash_path",
    (capture.PROCESS_RESULT_PATH, capture.PROJECTION_PATH),
)
def test_adapter_partial_durable_prefix_reconstructs_unknown(
    crash_path: str,
) -> None:
    capture_store = capture.CreateOnceStore()
    capture_store.arm_crash(crash_path, "after")
    current = coordinator(capture_store=capture_store)

    with pytest.raises(capture.SyntheticCrash):
        current.run()

    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_CAPTURE_RESULT_UNKNOWN"
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert checked == integration.Verification(
        True, "VERIFIED", "RUNNER_CAPTURE_RESULT_UNKNOWN", None
    )


def test_capture_result_after_durability_crash_reconstructs_seal_unavailable() -> None:
    capture_store = capture.CreateOnceStore()
    capture_store.arm_crash(capture.CAPTURE_RESULT_PATH, "after")
    current = coordinator(capture_store=capture_store)
    with pytest.raises(capture.SyntheticCrash):
        current.run()

    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_SEAL_UNAVAILABLE"
    assert integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    ) == integration.Verification(
        True, "VERIFIED", "RUNNER_SEAL_UNAVAILABLE", None
    )


@pytest.mark.parametrize(
    "crash_at",
    (
        "after_seal_before_cleanup",
        "after_cleanup_before_receipt",
        "after_receipt_before_finalization",
    ),
)
def test_post_seal_continuation_never_reinvokes_or_repeats_cleanup(
    crash_at: str,
) -> None:
    invoke_calls = 0
    cleanup_calls = 0

    def invoke() -> integration.InjectedContainedResult:
        nonlocal invoke_calls
        invoke_calls += 1
        return contained()

    def cleanup() -> str:
        nonlocal cleanup_calls
        cleanup_calls += 1
        return "PASS"

    current = coordinator(invoke=invoke, cleanup=cleanup, crash_at=crash_at)
    with pytest.raises(integration.SyntheticIntegrationCrash):
        current.run()
    assert invoke_calls == 1
    expected_cleanup_calls = 0 if crash_at == "after_seal_before_cleanup" else 1
    assert cleanup_calls == expected_cleanup_calls

    resumed = coordinator(
        capture_store=current.capture_store,
        evidence_store=current.evidence_store,
        invoke=lambda: pytest.fail("invoke must not run during sealed continuation"),
        cleanup=cleanup,
    )
    result = resumed.resume_after_seal()

    assert result.profile == "RUNNER_CAPTURE_FINALIZED"
    assert invoke_calls == 1
    assert cleanup_calls == 1
    assert integration.verify_package(
        resumed.capture_store,
        resumed.evidence_store,
        resumed.bindings,
        resumed.authority,
    ).verified
    assert resumed.resume_after_seal() == result
    assert cleanup_calls == 1


def test_cleanup_side_effect_crash_before_result_is_permanent_unknown_no_retry() -> None:
    class ProcessDeath(BaseException):
        pass

    cleanup_calls = 0

    def cleanup() -> str:
        nonlocal cleanup_calls
        cleanup_calls += 1
        raise ProcessDeath()

    current = coordinator(cleanup=cleanup)
    with pytest.raises(ProcessDeath):
        current.run()

    assert cleanup_calls == 1
    assert integration.CLEANUP_AUTHORIZATION_PATH in current.evidence_store.files
    assert integration.CLEANUP_PATH not in current.evidence_store.files
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert checked == integration.Verification(
        True, "CLEANUP_RESULT_UNKNOWN", "RUNNER_CAPTURE_FINALIZED", None
    )

    resumed = coordinator(
        capture_store=current.capture_store,
        evidence_store=current.evidence_store,
        cleanup=cleanup,
    )
    with pytest.raises(integration.IntegrationError, match="CLEANUP_RESULT_UNKNOWN"):
        resumed.resume_after_seal()
    assert cleanup_calls == 1
    assert integration.verify_package(
        resumed.capture_store,
        resumed.evidence_store,
        resumed.bindings,
        resumed.authority,
    ).verified


@pytest.mark.parametrize(
    ("target_read", "expected_calls"),
    ((1, 0), (2, 0), (3, 1), (4, 1)),
)
def test_private_runtime_snapshot_mutation_fails_at_each_checkpoint(
    target_read: int, expected_calls: int
) -> None:
    source_reads = 0
    calls = 0

    def runner_source() -> bytes:
        nonlocal source_reads
        source_reads += 1
        if source_reads == target_read:
            return b"mutated private filesystem source\n"
        return RUNTIME_BYTES["runner_source"]

    current_readers = readers()
    current_readers["runner_source"] = runner_source

    def invoke() -> integration.InjectedContainedResult:
        nonlocal calls
        calls += 1
        return contained()

    current = coordinator(runtime_readers=current_readers, invoke=invoke)
    with pytest.raises(integration.IntegrationError, match="RUNTIME_SOURCE_MISMATCH"):
        current.run()

    assert calls == expected_calls
    assert calls <= 1
    retained = b"".join(current.evidence_store.files.values())
    assert b"mutated private filesystem source" not in retained
    assert b"synthetic runner source" not in retained


def test_runtime_reader_failure_is_sanitized() -> None:
    current_readers = readers()

    def fail() -> bytes:
        raise RuntimeError("PRIVATE_RUNTIME_EXCEPTION_CANARY")

    current_readers["runner_source"] = fail
    with pytest.raises(integration.IntegrationError) as caught:
        coordinator(runtime_readers=current_readers).run()

    assert caught.value.code == "RUNTIME_SOURCE_UNAVAILABLE"
    assert "CANARY" not in str(caught.value)


def test_launch_exception_yields_closed_negative_without_exception_text() -> None:
    def invoke():
        raise integration.ContainedStartFailed("PRIVATE_LAUNCH_EXCEPTION_CANARY")

    current = coordinator(invoke=invoke)
    with pytest.raises(integration.IntegrationError, match="NEGATIVE_CLEANUP_NOT_ADMITTED"):
        current.run()
    public_bytes = b"".join(current.capture_store.files.values()) + b"".join(
        current.evidence_store.files.values()
    )

    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_CAPTURE_NEGATIVE"
    assert b"PRIVATE_LAUNCH_EXCEPTION_CANARY" not in public_bytes


def test_untyped_invocation_exception_remains_unknown_not_start_failed() -> None:
    def invoke():
        raise RuntimeError("PRIVATE_UNKNOWN_INVOCATION_CANARY")

    current = coordinator(invoke=invoke)
    with pytest.raises(integration.IntegrationError) as caught:
        current.run()

    assert caught.value.code == "INVOCATION_DISPOSITION_UNKNOWN"
    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_CAPTURE_RESULT_UNKNOWN"
    assert capture.PROCESS_RESULT_PATH not in current.capture_store.files
    assert b"CANARY" not in b"".join(current.evidence_store.files.values())
    assert integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    ) == integration.Verification(
        True, "VERIFIED", "RUNNER_CAPTURE_RESULT_UNKNOWN", None
    )


def test_observation_exceptions_publish_closed_negative_observations() -> None:
    current = coordinator()
    current.observe_final = lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_FINAL_CANARY"))
    current.observe_workspace = lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_WORKSPACE_CANARY"))
    result = current.run()

    assert result.profile == "RUNNER_CAPTURE_NEGATIVE"
    assert parsed(current.evidence_store, integration.FINAL_OBSERVATION_PATH)["state"] == "READ_FAILED"
    assert parsed(current.evidence_store, integration.WORKSPACE_OBSERVATION_PATH)["state"] == "CAPTURE_FAILED"
    assert b"CANARY" not in b"".join(current.evidence_store.files.values())


@pytest.mark.parametrize(
    ("final_value", "workspace_value", "expected_final", "expected_workspace"),
    (([], "CHANGED", "READ_FAILED", "CHANGED"), ("CAPTURED", {}, "CAPTURED", "CAPTURE_FAILED")),
)
def test_non_string_observations_are_durably_normalized(
    final_value, workspace_value, expected_final: str, expected_workspace: str
) -> None:
    current = coordinator()
    current.observe_final = lambda: final_value
    current.observe_workspace = lambda: workspace_value
    result = current.run()

    assert result.profile == "RUNNER_CAPTURE_NEGATIVE"
    assert parsed(current.evidence_store, integration.FINAL_OBSERVATION_PATH)["state"] == expected_final
    assert parsed(current.evidence_store, integration.WORKSPACE_OBSERVATION_PATH)["state"] == expected_workspace


@pytest.mark.parametrize(
    "subject",
    ("adapter_source", "adapter_contract", "raw_contract", "projector_contract", "public_schemas"),
)
def test_runtime_identity_must_cross_bind_capture_authorization(subject: str) -> None:
    current = coordinator()
    mutated = dict(current.authority.runtime_sha256)
    mutated[subject] = capture.sha256(b"unrelated but internally authorized runtime bytes")
    object.__setattr__(current.authority, "runtime_sha256", mutated)
    current.runtime_readers = {
        **current.runtime_readers,
        subject: lambda: b"unrelated but internally authorized runtime bytes",
    }

    with pytest.raises(integration.IntegrationError, match="RUNTIME_CAPTURE_BINDING_MISMATCH"):
        current.run()


def test_negative_cleanup_requires_explicit_terminal_admission() -> None:
    cleanup_calls = 0

    def cleanup() -> str:
        nonlocal cleanup_calls
        cleanup_calls += 1
        return "PASS"

    current = coordinator(
        invoke=lambda: (_ for _ in ()).throw(integration.ContainedStartFailed()),
        cleanup=cleanup,
    )
    with pytest.raises(integration.IntegrationError, match="NEGATIVE_CLEANUP_NOT_ADMITTED"):
        current.run()

    assert cleanup_calls == 0
    assert integration.SEAL_PATH in current.evidence_store.files
    assert integration.CLEANUP_PATH not in current.evidence_store.files
    assert integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    ) == integration.Verification(
        True, "VERIFIED", "RUNNER_CAPTURE_NEGATIVE", None
    )


def test_cross_profile_mutation_fails_after_all_ordinary_links_are_recomputed() -> None:
    current, _ = run_complete()
    evidence = current.evidence_store

    final_observation = parsed(evidence, integration.FINAL_OBSERVATION_PATH)
    final_observation["state"] = "ABSENT"
    replace(evidence, integration.FINAL_OBSERVATION_PATH, final_observation)

    seal = parsed(evidence, integration.SEAL_PATH)
    seal["final_observation_sha256"] = capture.sha256(
        evidence.read(integration.FINAL_OBSERVATION_PATH)
    )
    replace(evidence, integration.SEAL_PATH, seal)
    cleanup = parsed(evidence, integration.CLEANUP_PATH)
    cleanup["seal_sha256"] = capture.sha256(evidence.read(integration.SEAL_PATH))
    replace(evidence, integration.CLEANUP_PATH, cleanup)
    receipt = parsed(evidence, integration.RECEIPT_PATH)
    receipt["seal_sha256"] = capture.sha256(evidence.read(integration.SEAL_PATH))
    receipt["cleanup_sha256"] = capture.sha256(evidence.read(integration.CLEANUP_PATH))
    replace(evidence, integration.RECEIPT_PATH, receipt)
    finalization = parsed(evidence, integration.FINALIZATION_PATH)
    finalization["receipt_sha256"] = capture.sha256(evidence.read(integration.RECEIPT_PATH))
    replace(evidence, integration.FINALIZATION_PATH, finalization)

    checked = integration.verify_package(
        current.capture_store, evidence, current.bindings, current.authority
    )
    assert not checked.verified
    assert checked.code == "SEAL_LINK_INVALID"


@pytest.mark.parametrize("extra_path", ("extra.json", "private-stdout.json"))
def test_extra_public_artifact_fails_closed(extra_path: str) -> None:
    current, _ = run_complete()
    current.evidence_store.files[extra_path] = b"{}\n"

    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert not checked.verified
    assert checked.code == "PROFILE_INVENTORY_INVALID"


def test_truncated_observation_chain_cannot_masquerade_as_seal_unavailable() -> None:
    current, _ = run_complete()
    retained = {
        integration.INTEGRATION_AUTHORITY_PATH,
        integration.INTEGRATION_CONTRACT_PATH,
    }
    current.evidence_store.files = {
        path: payload
        for path, payload in current.evidence_store.files.items()
        if path in retained
    }

    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_SEAL_UNAVAILABLE"
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert not checked.verified
    assert checked.code == "PROFILE_INVENTORY_INVALID"


def test_coherently_relinked_observation_stage_mutation_fails_closed() -> None:
    current, _ = run_complete()
    evidence = current.evidence_store
    stage = parsed(evidence, integration.OBSERVATION_STAGE_PATH)
    stage["capture_authorization_sha256"] = "0" * 64
    replace(evidence, integration.OBSERVATION_STAGE_PATH, stage)

    seal = parsed(evidence, integration.SEAL_PATH)
    seal["observation_stage_sha256"] = capture.sha256(
        evidence.read(integration.OBSERVATION_STAGE_PATH)
    )
    replace(evidence, integration.SEAL_PATH, seal)
    for path in (integration.CLEANUP_AUTHORIZATION_PATH, integration.CLEANUP_PATH):
        artifact = parsed(evidence, path)
        artifact["seal_sha256"] = capture.sha256(evidence.read(integration.SEAL_PATH))
        replace(evidence, path, artifact)
    receipt = parsed(evidence, integration.RECEIPT_PATH)
    receipt["seal_sha256"] = capture.sha256(evidence.read(integration.SEAL_PATH))
    receipt["cleanup_sha256"] = capture.sha256(evidence.read(integration.CLEANUP_PATH))
    replace(evidence, integration.RECEIPT_PATH, receipt)
    finalization = parsed(evidence, integration.FINALIZATION_PATH)
    finalization["receipt_sha256"] = capture.sha256(evidence.read(integration.RECEIPT_PATH))
    replace(evidence, integration.FINALIZATION_PATH, finalization)

    checked = integration.verify_package(
        current.capture_store, evidence, current.bindings, current.authority
    )
    assert not checked.verified
    assert checked.code == "OBSERVATION_STAGE_INVALID"


def test_seal_unavailable_never_admits_cleanup() -> None:
    current = coordinator(crash_at="after_observations_before_seal")
    with pytest.raises(integration.SyntheticIntegrationCrash):
        current.run()

    assert integration.reconstruct_profile(
        current.capture_store, current.evidence_store
    ) == "RUNNER_SEAL_UNAVAILABLE"
    assert integration.CLEANUP_PATH not in current.evidence_store.files
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert checked == integration.Verification(
        True, "VERIFIED", "RUNNER_SEAL_UNAVAILABLE", None
    )

    current.evidence_store.files["unexpected.json"] = b"{}\n"
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )
    assert not checked.verified
    assert checked.code == "PROFILE_INVENTORY_INVALID"


def test_authority_or_observation_mismatch_fails_before_or_at_boundary() -> None:
    wrong = copy.deepcopy(authority())
    object.__setattr__(wrong, "arm", "B")
    current = coordinator()
    current.authority = wrong
    with pytest.raises(integration.IntegrationError, match="INTEGRATION_AUTHORITY_MISMATCH"):
        current.run()

    normalized = coordinator(final_state="FUTURE_STATE")
    result = normalized.run()
    assert result.profile == "RUNNER_CAPTURE_NEGATIVE"
    assert parsed(normalized.evidence_store, integration.FINAL_OBSERVATION_PATH)["state"] == "READ_FAILED"


def test_public_claim_never_exceeds_capture_attestation_chain() -> None:
    current, result = run_complete()
    checked = integration.verify_package(
        current.capture_store,
        current.evidence_store,
        current.bindings,
        current.authority,
    )

    assert result.claim == capture.PUBLIC_CLAIM
    assert checked.claim == capture.PUBLIC_CLAIM
    assert "FINAL_ANSWER" not in checked.claim
    assert "MODEL_COMPLETION" not in checked.claim
