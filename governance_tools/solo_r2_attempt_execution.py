"""General pre-ID execution coordinator for Solo Evaluation R2.

This is the last gate before ``SyntheticLifecycleCoordinator.admit_attempt``.
It intentionally has no method that generates a handle or exposes a task.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools.solo_r2_attempt_materialization import (
    PairMaterializationEvidence,
)
from governance_tools.solo_r2_codex_runner import (
    CanaryQualification,
    NativeExecutionResult,
    PAIR_INVALID,
    PreparedArm,
    RunnerGateError,
    ToolCatalog,
    validate_execution_result,
)


PRE_ATTEMPT_INFRA_FAILURE = "PRE_ATTEMPT_INFRA_FAILURE / STOP"
VALIDATED = "R2_PRE_ID_EXECUTION_SURFACE_VALIDATED"


class AttemptExecutionError(RuntimeError):
    def __init__(self, code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
    raise AttemptExecutionError(code)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_ledger_snapshot(path: Path) -> tuple[bytes, list[dict[str, Any]], ledger.LedgerSummary]:
    try:
        payload = path.read_bytes()
    except OSError:
        _fail()
    if not payload or not payload.endswith(b"\n") or b"\r" in payload:
        _fail()
    try:
        events = ledger.read_ledger(path)
        summary = ledger.validate_ledger_events(events)
    except ledger.LedgerError:
        _fail()
    return payload, events, summary


@dataclass(frozen=True)
class PairBinding:
    evaluation_id: str
    pair_id: str
    slot: str
    category: str
    repository: str
    frozen_identities: Mapping[str, object]

    def validate_event(self, genesis: Mapping[str, Any], event: Mapping[str, Any]) -> None:
        if (
            genesis.get("evaluation_id") != self.evaluation_id
            or event.get("event_type") != "PAIR_CREATED"
            or event.get("pair_id") != self.pair_id
            or event.get("slot") != self.slot
            or event.get("category") != self.category
            or event.get("repository") != self.repository
            or event.get("frozen_identities") != dict(self.frozen_identities)
        ):
            _fail(PAIR_INVALID)


class PairLedgerLock:
    """Exclusive lease bound to current complete ledger bytes and one Pair.

    Unlike the historical creation helper, this gate is not pinned to a
    genesis-only ledger digest.  It can guard the shakedown or any later slot.
    The ledger remains the durable one-shot record; a crashed lease file is a
    fail-closed condition requiring owner recovery.
    """

    def __init__(
        self,
        *,
        ledger_path: Path | str,
        lock_path: Path | str,
        binding: PairBinding,
        expected_ledger_sha256: str | None = None,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.lock_path = Path(lock_path)
        self.binding = binding
        self.expected_ledger_sha256 = expected_ledger_sha256
        self._digest: str | None = None
        self._summary: ledger.LedgerSummary | None = None
        self._held = False

    def _validate_target(
        self, events: list[dict[str, Any]], summary: ledger.LedgerSummary
    ) -> None:
        matching = [
            event
            for event in events
            if event.get("event_type") == "PAIR_CREATED"
            and event.get("pair_id") == self.binding.pair_id
        ]
        if len(matching) != 1:
            _fail(PAIR_INVALID)
        self.binding.validate_event(events[0], matching[0])
        target_events = [
            event
            for event in events
            if event.get("pair_id") == self.binding.pair_id
            and event.get("event_type") != "PAIR_CREATED"
        ]
        if target_events:
            _fail(PAIR_INVALID)
        if summary.admitted_attempt_count or summary.initiated_attempt_count:
            # Before the first R2 Pair this is globally zero.  Later slots may
            # follow completed pairs, so only target events are authoritative.
            earlier_pair_ids = {
                event.get("pair_id")
                for event in events
                if event.get("event_type") == "PAIR_CREATED"
                and event.get("event_seq", 0) < matching[0].get("event_seq", 0)
            }
            attempt_pair_ids = {
                event.get("pair_id")
                for event in events
                if event.get("event_type") in {
                    "ATTEMPT_ADMITTED", "ADMITTED_NOT_EXPOSED",
                    "TASK_EXPOSED", "EXECUTION_TERMINAL",
                }
            }
            if not attempt_pair_ids <= earlier_pair_ids:
                _fail(PAIR_INVALID)

    def acquire(self) -> "PairLedgerLock":
        if self._held or not self.ledger_path.is_absolute() or not self.lock_path.is_absolute():
            _fail()
        payload, events, summary = _read_ledger_snapshot(self.ledger_path)
        digest = _sha256(payload)
        if self.expected_ledger_sha256 is not None and digest != self.expected_ledger_sha256:
            _fail(PAIR_INVALID)
        self._validate_target(events, summary)
        lock_payload = json.dumps(
            {
                "ledger_sha256": digest,
                "pair_id": self.binding.pair_id,
                "slot": self.binding.slot,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii") + b"\n"
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                self.lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(lock_payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            _fail()
        self._digest = digest
        self._summary = summary
        self._held = True
        return self

    def assert_unchanged(self) -> ledger.LedgerSummary:
        if not self._held or self._digest is None or self._summary is None:
            _fail()
        try:
            current_payload = self.ledger_path.read_bytes()
        except OSError:
            _fail()
        if _sha256(current_payload) != self._digest:
            _fail(PAIR_INVALID)
        payload, events, summary = _read_ledger_snapshot(self.ledger_path)
        if payload != current_payload:
            _fail(PAIR_INVALID)
        self._validate_target(events, summary)
        return summary

    def release(self) -> None:
        if not self._held:
            _fail()
        try:
            self.lock_path.unlink()
        except OSError:
            _fail()
        self._held = False

    def __enter__(self) -> "PairLedgerLock":
        return self.acquire()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


@dataclass(frozen=True)
class PreAttemptValidation:
    disposition: str
    pair_id: str
    slot: str
    pair_count: int
    initiated_attempt_count: int
    attempt_ceiling_total: int
    catalog_sha256: str
    task_exposure_state: str = "NONE"
    attempt_handle: None = None


class PreAttemptExecutionCoordinator:
    """Consume all pre-ID evidence exactly once and return no authority token."""

    def __init__(self, pair_lock: PairLedgerLock) -> None:
        self.pair_lock = pair_lock
        self._used = False

    @staticmethod
    def _catalog(arm: PreparedArm) -> ToolCatalog:
        try:
            return ToolCatalog.observed(
                arm.configured_tool_inventory, arm.catalog_sha256
            )
        except RunnerGateError:
            _fail(PAIR_INVALID)

    @staticmethod
    def validate_terminal_execution(
        *, prepared_arm: PreparedArm, result: NativeExecutionResult
    ) -> None:
        """Require a retained, recomputable trace for either arm independently."""

        try:
            prepared_arm.runtime_identity.validate()
            prepared_arm.execution_policy.validate()
            catalog = PreAttemptExecutionCoordinator._catalog(prepared_arm)
            validate_execution_result(result, catalog)
        except (AttributeError, RunnerGateError):
            _fail(PAIR_INVALID)

    def validate(
        self,
        *,
        materialization: PairMaterializationEvidence,
        canary: CanaryQualification,
        control: PreparedArm,
        treatment: PreparedArm,
    ) -> PreAttemptValidation:
        if self._used:
            _fail()
        summary = self.pair_lock.assert_unchanged()
        try:
            materialization.validate()
            canary.host_local.validate()
            control_catalog = self._catalog(control)
            treatment_catalog = self._catalog(treatment)
        except Exception as exc:
            if getattr(exc, "code", None) == PAIR_INVALID:
                _fail(PAIR_INVALID)
            _fail()

        if (
            control.arm_ordinal != 1
            or treatment.arm_ordinal != 2
            or control.task_exposure_state != "NONE"
            or treatment.task_exposure_state != "NONE"
            or control_catalog != canary.catalog
            or treatment_catalog != canary.catalog
            or control.runtime_identity.equality_projection()
            != treatment.runtime_identity.equality_projection()
            or control.runtime_identity.equality_projection()
            != canary.runtime_identity.equality_projection()
            or control.runtime_identity.model_selector
            != treatment.runtime_identity.model_selector
            or control.runtime_identity.reasoning_effort
            != treatment.runtime_identity.reasoning_effort
            or control.execution_policy != treatment.execution_policy
            or control.execution_policy != canary.execution_policy
            or control.sandbox_principal != treatment.sandbox_principal
            or control.sandbox_account_generation
            != treatment.sandbox_account_generation
            or control.sandbox_principal != canary.sandbox_principal
            or control.sandbox_account_generation
            != canary.sandbox_account_generation
            or control.sandbox_principal
            != materialization.control.sandbox_principal
            or control.sandbox_account_generation
            != materialization.control.sandbox_account_generation
            or treatment.sandbox_principal
            != materialization.treatment.sandbox_principal
            or treatment.sandbox_account_generation
            != materialization.treatment.sandbox_account_generation
            or len({control.context_id, treatment.context_id, canary.context_id}) != 3
            or len({control.workspace_id, treatment.workspace_id, canary.workspace_id}) != 3
            or control_catalog.catalog_sha256 != treatment_catalog.catalog_sha256
            or materialization.host_local != canary.host_local
            or control.host_local != canary.host_local
            or treatment.host_local != canary.host_local
        ):
            _fail(PAIR_INVALID)

        control_host = materialization.host_local
        control_host.validate()
        final_summary = self.pair_lock.assert_unchanged()
        if final_summary != summary:
            _fail(PAIR_INVALID)
        self._used = True
        return PreAttemptValidation(
            disposition=VALIDATED,
            pair_id=self.pair_lock.binding.pair_id,
            slot=self.pair_lock.binding.slot,
            pair_count=final_summary.pair_count,
            initiated_attempt_count=final_summary.initiated_attempt_count,
            attempt_ceiling_total=final_summary.attempt_ceiling_total,
            catalog_sha256=control_catalog.catalog_sha256,
        )
