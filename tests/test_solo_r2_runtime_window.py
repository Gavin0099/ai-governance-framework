from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_controller_state as controller_state
from governance_tools import solo_r2_random_domains as random_domains
from governance_tools import solo_r2_runtime_window as subject
from governance_tools.solo_r2_attempt_execution import PairBinding, PairLedgerLock
from governance_tools.solo_r2_attempt_materialization import (
    ArmMaterializationEvidence,
    FROZEN_BASE_COMMIT,
    HostLocalEndpointDisposition,
    HostLocalIsolation,
    PairMaterializationEvidence,
    PinnedExecutable,
    RepositoryBinding,
    TREATMENT_PACKET_SHA256,
    inventory_sha256,
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
OFFLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1003"
ONLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1004"
HOST_LOCAL = HostLocalIsolation(HostLocalEndpointDisposition.REACHABLE, 0)
CATALOG = ToolCatalog.project((ToolDescriptor("command_execution"),))


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


def _materialization(generation: SandboxGenerationFingerprint) -> PairMaterializationEvidence:
    rows = (("source.txt", 7, hashlib.sha256(b"source\n").hexdigest()),)
    common = dict(
        base_commit=FROZEN_BASE_COMMIT,
        inventory=rows,
        inventory_sha256=inventory_sha256(rows),
        sandbox_principal=OFFLINE_SID,
        sandbox_account_generation=generation.value,
        fresh_leaf_destroyed=True,
    )
    return PairMaterializationEvidence(
        ArmMaterializationEvidence(1, treatment_instruction_sha256=None, **common),
        ArmMaterializationEvidence(
            2, treatment_instruction_sha256=TREATMENT_PACKET_SHA256, **common
        ),
        HOST_LOCAL,
    )


class NativeBackendDouble:
    def __init__(self, executable: PinnedExecutable) -> None:
        self.executable = executable
        self.configured_catalog = CATALOG
        self.calls = 0
        self.preparations: list[object] = []

    def execute(self, **kwargs) -> NativeExecutionResult:
        self.calls += 1
        self.preparations.append(kwargs["prepared_arm"])
        workspace = kwargs["workspace_root"]
        output = kwargs["output_root"]
        challenge = (workspace / "qualification-challenge.txt").read_text("ascii")
        whoami = str(Path(sys.executable).resolve())
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
                        "command": f"read qualification-challenge.txt; '{whoami}' /user",
                        "aggregated_output": (
                            f"CodexSandboxOffline {OFFLINE_SID}\n{challenge}"
                        ),
                        "status": "completed",
                        "exit_code": 0,
                    },
                },
                {"type": "turn.completed"},
            )
        )
        schema = _canonical_json(kwargs["output_schema"]) + b"\n"
        final = _canonical_json(
            {
                "status": subject.QUALIFICATION_STATUS,
                "challenge": challenge,
                "principal_sid": OFFLINE_SID,
            }
        ) + b"\n"
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


class MaterializerDouble:
    def __init__(self, evidence: PairMaterializationEvidence) -> None:
        self.evidence = evidence
        self.leaves = SimpleNamespace(active=None)
        self.calls: list[str] = []

    def qualify_pair(self, pair_id: str) -> PairMaterializationEvidence:
        assert self.leaves.active is None
        self.calls.append(pair_id)
        return self.evidence


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
    native = SimpleNamespace(
        executable=executable,
        command_policy_projection=lambda: (str(executable.path), "exec"),
    )
    generations = iter((GENERATION_A, GENERATION_B))
    probe = subject.RuntimeFreezeProbe(
        backend=native,  # type: ignore[arg-type]
        repository_probe=SimpleNamespace(capture=lambda: repository),  # type: ignore[arg-type]
        qualification_helper=executable,
        generation_probe=lambda: next(generations),
        pair_lock=pair_lock,
        boundary_evidence=subject.PreExposureBoundaryEvidence(
            "5" * 64, False, True, HOST_LOCAL
        ),
        assert_runtime_quiescent=lambda: None,
    )
    with pair_lock, pytest.raises(subject.RuntimeWindowError) as caught:
        probe.capture()
    assert caught.value.code == subject.SAME_MACHINE_WINDOW_REJECTED


def test_boundary_evidence_loads_only_exact_fail_closed_projection(tmp_path: Path) -> None:
    value = {
        "schema": subject.BOUNDARY_SCHEMA,
        "credential_sentinel_visible": False,
        "network_tcp_egress_denied": True,
        "host_local_endpoint_reachable": "REACHABLE",
        "observed_host_listener_count": 0,
        "runtime_endpoint_inputs": [],
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
        observation_source=PassingBoundarySource(),
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
    materializer = MaterializerDouble(_materialization(GENERATION_B))
    freeze_probe = FreezeProbeDouble(
        pair_lock,
        _freeze(executable, pair_lock.binding, GENERATION_B),
        executable,
    )
    window = subject.PreAttemptFrozenRuntimeWindow(
        backend=backend,
        adapter=adapter,
        freeze_probe=freeze_probe,  # type: ignore[arg-type]
        materializer=materializer,  # type: ignore[arg-type]
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
    assert all(
        isinstance(value, subject.ProvisioningExecutionPreparation)
        for value in native.preparations
    )
    assert all(not hasattr(value, "host_local") for value in native.preparations)
    assert backend.boundary_evidence is not None
    assert boundary_path.is_file()
    assert materializer.calls == [pair_lock.binding.pair_id]
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
