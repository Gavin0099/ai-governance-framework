from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import uuid

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_attempt_execution as subject
from governance_tools.solo_r2_attempt_materialization import (
    ArmMaterializationEvidence,
    FROZEN_BASE_COMMIT,
    HostLocalIsolation,
    PairMaterializationEvidence,
    TREATMENT_PACKET_SHA256,
    inventory_sha256,
)
from governance_tools.solo_r2_codex_runner import (
    CanaryQualification,
    NativeExecutionResult,
    PAIR_INVALID,
    PreparedArm,
    RuntimeIdentity,
    SandboxGenerationFingerprint,
    ToolCatalog,
    ToolDescriptor,
    REQUIRED_EXECUTION_POLICY,
    IDENTITY_DISPOSITION,
)


CANONICAL = Path("artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson")
HOST_LOCAL = HostLocalIsolation(True, 0)
CATALOG = ToolCatalog.project((ToolDescriptor("read"), ToolDescriptor("shell")))
IDENTITY = RuntimeIdentity(
    "gpt-5.6-sol", "high", "UNAVAILABLE", "client", "host", IDENTITY_DISPOSITION
)
OFFLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1003"
ONLINE_SID = "S-1-5-21-4017902291-1272973841-664929404-1004"
GENERATION = SandboxGenerationFingerprint.create(
    offline_sid=OFFLINE_SID,
    online_sid=ONLINE_SID,
    offline_password_last_set_utc="2026-09-02T10:25:08.5697508Z",
    online_password_last_set_utc="2026-09-02T10:25:08.6099464Z",
    sandbox_users_json_byte_length=2,
    sandbox_users_json_sha256=hashlib.sha256(b"{}").hexdigest(),
)


def _ledger_copy(tmp_path: Path) -> Path:
    target = (tmp_path / "ledger.ndjson").resolve()
    target.write_bytes(CANONICAL.read_bytes())
    return target


def _binding(path: Path) -> subject.PairBinding:
    events = ledger.read_ledger(path)
    pair = events[1]
    return subject.PairBinding(
        evaluation_id=events[0]["evaluation_id"],
        pair_id=pair["pair_id"],
        slot=pair["slot"],
        category=pair["category"],
        repository=pair["repository"],
        frozen_identities=pair["frozen_identities"],
    )


def _materialization(generation: str = GENERATION.value) -> PairMaterializationEvidence:
    rows = (("source.txt", 7, hashlib.sha256(b"source\n").hexdigest()),)
    common = dict(
        base_commit=FROZEN_BASE_COMMIT,
        inventory=rows,
        inventory_sha256=inventory_sha256(rows),
        sandbox_principal=OFFLINE_SID,
        sandbox_account_generation=generation,
        fresh_leaf_destroyed=True,
    )
    return PairMaterializationEvidence(
        control=ArmMaterializationEvidence(
            ordinal=1, treatment_instruction_sha256=None, **common
        ),
        treatment=ArmMaterializationEvidence(
            ordinal=2,
            treatment_instruction_sha256=TREATMENT_PACKET_SHA256,
            **common,
        ),
        host_local=HOST_LOCAL,
    )


def _canary(generation: str = GENERATION.value) -> CanaryQualification:
    return CanaryQualification(
        "canary-context",
        "canary-workspace",
        IDENTITY,
        REQUIRED_EXECUTION_POLICY,
        CATALOG,
        OFFLINE_SID,
        generation,
        HOST_LOCAL,
    )


def _arm(ordinal: int, generation: str = GENERATION.value) -> PreparedArm:
    return PreparedArm(
        arm_ordinal=ordinal,
        context_id=f"context-{ordinal}",
        workspace_id=f"workspace-{ordinal}",
        runtime_identity=IDENTITY,
        execution_policy=REQUIRED_EXECUTION_POLICY,
        configured_tool_inventory=CATALOG.public_inventory(),
        catalog_sha256=CATALOG.catalog_sha256,
        sandbox_principal=OFFLINE_SID,
        sandbox_account_generation=generation,
        host_local=HOST_LOCAL,
    )


def test_pre_id_surface_validates_without_mutating_ledger(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    before = path.read_bytes()
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "locks" / "pair.lock").resolve(),
        binding=_binding(path),
        expected_ledger_sha256=hashlib.sha256(before).hexdigest(),
    )
    with lock:
        result = subject.PreAttemptExecutionCoordinator(lock).validate(
            materialization=_materialization(),
            canary=_canary(),
            control=_arm(1),
            treatment=_arm(2),
        )
    assert result.disposition == subject.VALIDATED
    assert result.pair_count == 1
    assert result.initiated_attempt_count == 0
    assert result.attempt_ceiling_total == 14
    assert result.task_exposure_state == "NONE"
    assert result.attempt_handle is None
    assert path.read_bytes() == before
    assert not lock.lock_path.exists()


def test_pair_lock_rejects_ledger_drift(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(path),
    ).acquire()
    path.write_bytes(path.read_bytes() + b"\n")
    try:
        with pytest.raises(subject.AttemptExecutionError) as caught:
            lock.assert_unchanged()
        assert caught.value.code == PAIR_INVALID
    finally:
        lock.release()


def test_pair_lock_rejects_target_pair_after_attempt_admission(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    binding = _binding(path)
    event = {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": 3,
        "event_type": "ATTEMPT_ADMITTED",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": "2026-09-03T00:00:00Z",
        "pair_id": binding.pair_id,
        "slot": binding.slot,
        "attempt_handle": "a" * 64,
        "attempt_state": "ADMITTED",
        "admission_result": {
            "status": "ADMITTED",
            "preflight_ids": ["preflight"],
            "task_exposure_state": "NONE",
        },
    }
    path.write_bytes(path.read_bytes() + ledger.encode_event(event))
    with pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PairLedgerLock(
            ledger_path=path,
            lock_path=(tmp_path / "pair.lock").resolve(),
            binding=binding,
        ).acquire()
    assert caught.value.code == PAIR_INVALID


def test_configured_tool_projection_is_consumed_as_pair_invalid(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(path),
    )
    drifted = ToolCatalog.project((ToolDescriptor("read"),))
    treatment = replace(
        _arm(2),
        configured_tool_inventory=drifted.public_inventory(),
        catalog_sha256=drifted.catalog_sha256,
    )
    with lock, pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PreAttemptExecutionCoordinator(lock).validate(
            materialization=_materialization(),
            canary=_canary(),
            control=_arm(1),
            treatment=treatment,
        )
    assert caught.value.code == PAIR_INVALID


def _result(tmp_path: Path, name: str, tool: str) -> NativeExecutionResult:
    trace = b"".join(
        json.dumps(event, separators=(",", ":"), sort_keys=True).encode("ascii")
        + b"\n"
        for event in (
            {"type": "thread.started", "thread_id": "thread"},
            {"type": "turn.started"},
            {"type": "item.started", "item": {"id": "one", "type": tool}},
            {"type": "turn.completed"},
        )
    )
    path = tmp_path / f"{name}.jsonl"
    schema_path = tmp_path / f"{name}-schema.json"
    final_path = tmp_path / f"{name}-final.json"
    path.write_bytes(trace)
    schema = b'{"type":"object"}\n'
    final = b"{}\n"
    schema_path.write_bytes(schema)
    final_path.write_bytes(final)
    digest = hashlib.sha256(trace).hexdigest()
    return NativeExecutionResult(
        trace_path=path,
        schema_path=schema_path,
        final_message_path=final_path,
        schema_sha256=hashlib.sha256(schema).hexdigest(),
        schema_byte_length=len(schema),
        trace_sha256=digest,
        trace_byte_length=len(trace),
        tool_call_count=1,
        observed_tool_inventory=(tool,),
        terminal_event="turn.completed",
        disposition="SUCCESS",
        returncode=0,
        timed_out=False,
        tree_terminated=True,
        stderr_sha256=hashlib.sha256(b"").hexdigest(),
        stderr_byte_length=0,
        final_message_sha256=hashlib.sha256(final).hexdigest(),
        final_message_byte_length=len(final),
    )


def test_arm_observed_tool_inventories_may_diverge_post_hoc(tmp_path: Path) -> None:
    control = _result(tmp_path, "control", "read")
    treatment = _result(tmp_path, "treatment", "shell")
    subject.PreAttemptExecutionCoordinator.validate_terminal_execution(
        prepared_arm=_arm(1), result=control
    )
    subject.PreAttemptExecutionCoordinator.validate_terminal_execution(
        prepared_arm=_arm(2), result=treatment
    )
    assert control.observed_tool_inventory != treatment.observed_tool_inventory


def test_observed_tool_outside_configured_projection_is_pair_invalid(
    tmp_path: Path,
) -> None:
    with pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PreAttemptExecutionCoordinator.validate_terminal_execution(
            prepared_arm=_arm(1), result=_result(tmp_path, "arm", "outside_surface")
        )
    assert caught.value.code == PAIR_INVALID


def test_sandbox_account_generation_must_match_between_arms(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(path),
    )
    with lock, pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PreAttemptExecutionCoordinator(lock).validate(
            materialization=_materialization(),
            canary=_canary(),
            control=_arm(1),
            treatment=_arm(2, "sha256:" + "1" * 64),
        )
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_sid_only_generation_is_pre_attempt_infrastructure_failure(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(path),
    )
    with lock, pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PreAttemptExecutionCoordinator(lock).validate(
            materialization=_materialization(OFFLINE_SID),
            canary=_canary(OFFLINE_SID),
            control=_arm(1, OFFLINE_SID),
            treatment=_arm(2, OFFLINE_SID),
        )
    assert caught.value.code == subject.PRE_ATTEMPT_INFRA_FAILURE


def test_formal_host_local_observation_must_match_canary(tmp_path: Path) -> None:
    path = _ledger_copy(tmp_path)
    lock = subject.PairLedgerLock(
        ledger_path=path,
        lock_path=(tmp_path / "pair.lock").resolve(),
        binding=_binding(path),
    )
    treatment = replace(_arm(2), host_local=HostLocalIsolation(False, 0))
    with lock, pytest.raises(subject.AttemptExecutionError) as caught:
        subject.PreAttemptExecutionCoordinator(lock).validate(
            materialization=_materialization(),
            canary=_canary(),
            control=_arm(1),
            treatment=treatment,
        )
    assert caught.value.code == PAIR_INVALID
