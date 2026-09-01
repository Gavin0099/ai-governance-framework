"""Synthetic-only lifecycle composition for Solo Evaluation Revision 2.

This module composes the committed public-ledger, controller-state, and blind
scoring boundaries.  It has no canonical-ledger bootstrap or resume entrypoint.
Every lifecycle starts from an absent, explicitly supplied repo-external ledger
and becomes unusable after any failure or process loss.

The public ledger proves public lifecycle events only.  Controller-only
checkpoints are current-state files, not a claimed private provenance chain.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypeVar
from uuid import uuid4

from governance_tools import solo_attempt_ledger_v2 as ledger
from governance_tools import solo_r2_blind_scoring_bundle as scoring_bundle
from governance_tools import solo_r2_controller_state as controller
from governance_tools import solo_r2_random_domains as random_domains


SYNTHETIC_SLOT = "R2-SHAKEDOWN"
V2_CONFORMANCE_FAILURE = "V2_CONFORMANCE_FAILURE / STOP"
PREMATURE_UNBLINDING_STOP = "PREMATURE_UNBLINDING / STOP"
CONTROLLER_ORDER_FAILURE = "CONTROLLER_ORDER_FAILURE / STOP"

_START_TOKEN = object()
_T = TypeVar("_T")


class LifecycleIntegrationError(RuntimeError):
    """Fail-closed integration error carrying only a frozen public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ScorerDelivery:
    """The complete scorer capability: one path and the exact bundle bytes."""

    bundle_path: Path
    bundle_bytes: bytes


@dataclass(frozen=True)
class SyntheticUnblindingResult:
    """Controller-only synthetic mapping recovered after two acknowledgements."""

    scoring_label_to_arm: tuple[tuple[str, str], ...]


def _fail(code: str = V2_CONFORMANCE_FAILURE) -> None:
    raise LifecycleIntegrationError(code) from None


def _is_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value) and not any(
        ord(character) < 32 for character in value
    )


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _draw_entropy32() -> bytes:
    try:
        entropy = os.urandom(random_domains.ENTROPY_BYTES)
    except Exception:
        _fail()
    if type(entropy) is not bytes or len(entropy) != random_domains.ENTROPY_BYTES:
        _fail()
    return entropy


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _contains_git_marker(path: Path) -> bool:
    for ancestor in (path, *path.parents):
        marker = ancestor / ".git"
        try:
            marker.stat()
        except FileNotFoundError:
            continue
        except OSError:
            _fail()
        else:
            return True
    return False


def _canonical_directory(value: object) -> Path:
    try:
        path = Path(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        _fail()
    if not path.is_absolute():
        _fail()
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail()
    if not resolved.is_dir():
        _fail()
    return resolved


def _canonical_absent_file(value: object) -> tuple[Path, Path]:
    try:
        path = Path(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        _fail()
    if not path.is_absolute():
        _fail()
    parent = _canonical_directory(path.parent)
    try:
        resolved = (parent / path.name).resolve(strict=False)
    except (OSError, RuntimeError):
        _fail()
    if resolved.exists():
        _fail()
    return resolved, parent


def _resolved_boundary_roots(
    boundary: controller.CustodyBoundary,
) -> tuple[Path, ...]:
    if type(boundary) is not controller.CustodyBoundary:
        _fail()
    return tuple(_canonical_directory(root) for root in boundary.roots())


def _validate_synthetic_paths(
    *,
    ledger_path: object,
    controller_root: object,
    scoring_root: object,
    custody_boundary: controller.CustodyBoundary,
) -> tuple[Path, Path, Path]:
    public_path, ledger_root = _canonical_absent_file(ledger_path)
    private_root = _canonical_directory(controller_root)
    scorer_root = _canonical_directory(scoring_root)
    boundary_roots = _resolved_boundary_roots(custody_boundary)

    governance_root = boundary_roots[0]
    canonical_public = (governance_root / ledger.PUBLIC_LEDGER_PATH).resolve(
        strict=False
    )
    if public_path == canonical_public:
        _fail()
    if scorer_root != boundary_roots[4]:
        _fail()
    if any(
        _is_within(root, forbidden) or _is_within(forbidden, root)
        for root in (ledger_root, private_root)
        for forbidden in boundary_roots
    ):
        _fail()
    if any(
        _is_within(scorer_root, forbidden) or _is_within(forbidden, scorer_root)
        for forbidden in boundary_roots[:4]
    ):
        _fail()

    roots = (ledger_root, private_root, scorer_root)
    if len(set(roots)) != len(roots) or any(
        _is_within(left, right) or _is_within(right, left)
        for index, left in enumerate(roots)
        for right in roots[index + 1 :]
    ):
        _fail()
    if any(_contains_git_marker(root) for root in roots):
        _fail()
    return public_path, private_root, scorer_root


def _write_atomic_checkpoint(path: Path, data: bytes, *, replace: bool) -> None:
    """Write one private checkpoint; replacement is allowed only when explicit."""

    if type(data) is not bytes or not data:
        raise controller.ControllerStateError(controller.SEALING_FAILURE)
    if path.exists() != replace:
        raise controller.ControllerStateError(controller.SEALING_FAILURE)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise controller.ControllerStateError(controller.SEALING_FAILURE)
    try:
        with temporary.open("xb", buffering=0) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write")
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise controller.ControllerStateError(controller.SEALING_FAILURE) from None


def _write_create_once(path: Path, data: bytes) -> None:
    if type(data) is not bytes or not data or path.exists():
        raise scoring_bundle.BlindScoringBundleError()
    try:
        with path.open("xb", buffering=0) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write")
            os.fsync(stream.fileno())
    except OSError:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise scoring_bundle.BlindScoringBundleError() from None


class SyntheticLifecycleCoordinator:
    """One non-resumable, synthetic R2-SHAKEDOWN lifecycle.

    The constructor is intentionally unavailable to callers.  ``start`` is the
    only creation path and requires an absent ledger, so a process restart
    cannot resume or silently replace an existing lifecycle.
    """

    def __init__(
        self,
        token: object,
        *,
        ledger_path: Path,
        controller_root: Path,
        scoring_root: Path,
        key_path: Path | str,
        custody_boundary: controller.CustodyBoundary,
        evaluation_id: str,
        pair_id: str,
        category: str,
        repository: str,
        frozen_identities: Mapping[str, str],
        preflight_ids: Sequence[str],
        rubric_id: str,
    ) -> None:
        if token is not _START_TOKEN:
            _fail()
        self._ledger_path = ledger_path
        self._controller_root = controller_root
        self._scoring_root = scoring_root
        self._key_path = key_path
        self._custody_boundary = custody_boundary
        self._evaluation_id = evaluation_id
        self._pair_id = pair_id
        self._category = category
        self._repository = repository
        self._frozen_identities = dict(frozen_identities)
        self._preflight_ids = list(preflight_ids)
        self._rubric_id = rubric_id
        self._identifier_registry = random_domains.OpaqueIdentifierRegistry()
        self._checkpoint_digests: dict[str, str] = {}
        self._sealed_nonces: set[str] = set()
        self._terminal_outputs: dict[str, tuple[str, str]] = {}
        self._bundle_bytes: bytes | None = None
        self._completed_labels: set[str] = set()
        self._stopped = False
        self._completed = False

    @classmethod
    def start(
        cls,
        *,
        ledger_path: Path | str,
        controller_root: Path | str,
        scoring_root: Path | str,
        key_path: Path | str,
        custody_boundary: controller.CustodyBoundary,
        evaluation_id: str,
        pair_id: str,
        category: str,
        repository: str,
        frozen_identities: Mapping[str, str],
        preflight_ids: Sequence[str],
        rubric_id: str,
    ) -> "SyntheticLifecycleCoordinator":
        """Start a fresh synthetic lifecycle; existing state is never resumed."""

        public_path, private_root, scorer_root = _validate_synthetic_paths(
            ledger_path=ledger_path,
            controller_root=controller_root,
            scoring_root=scoring_root,
            custody_boundary=custody_boundary,
        )
        if (
            not _is_nonempty_string(evaluation_id)
            or not _is_nonempty_string(pair_id)
            or not _is_nonempty_string(category)
            or not _is_nonempty_string(repository)
            or not _is_nonempty_string(rubric_id)
            or not isinstance(frozen_identities, Mapping)
            or not isinstance(preflight_ids, Sequence)
            or isinstance(preflight_ids, (str, bytes, bytearray))
            or not preflight_ids
            or not all(_is_nonempty_string(item) for item in preflight_ids)
        ):
            _fail()

        instance = cls(
            _START_TOKEN,
            ledger_path=public_path,
            controller_root=private_root,
            scoring_root=scorer_root,
            key_path=key_path,
            custody_boundary=custody_boundary,
            evaluation_id=evaluation_id,
            pair_id=pair_id,
            category=category,
            repository=repository,
            frozen_identities=frozen_identities,
            preflight_ids=preflight_ids,
            rubric_id=rubric_id,
        )
        instance._require_expected_paths_absent()
        genesis = instance._genesis_event()
        pair_probe = instance._pair_event(sequence=2)
        ledger.validate_ledger_events([genesis, pair_probe])
        ledger.append_event(instance._ledger_path, genesis)

        try:
            order_entropy = _draw_entropy32()
            realized_order = list(random_domains.arm_order_from_entropy(order_entropy))
            order_state = {
                "schema_version": controller.CONTROLLER_STATE_SCHEMA,
                "artifact_type": controller.CONTROLLER_ARTIFACT_TYPE,
                "evaluation_id": evaluation_id,
                "pair_id": pair_id,
                "slot": SYNTHETIC_SLOT,
                "state_phase": controller.ORDER_FROZEN,
                "realized_order": realized_order,
                "order_entropy": base64.b64encode(order_entropy).decode("ascii"),
                "attempt_bindings": [],
                "scoring_bindings": [],
                "presentation_order": [],
                "attempt_output_refs": [],
            }
            snapshot = controller.freeze_controller_state(order_state)
            package = instance._seal_snapshot(snapshot)
            instance._write_checkpoint(
                controller.ORDER_FROZEN, package, replace=False
            )
        except (
            LifecycleIntegrationError,
            controller.ControllerStateError,
            random_domains.RandomDomainError,
        ) as exc:
            try:
                instance._append_event(
                    "PRE_ATTEMPT_INFRA_FAILURE",
                    pair_id=None,
                    category=category,
                    repository=repository,
                    admission_result={
                        "status": "FAIL_CLOSED",
                        "preflight_ids": list(preflight_ids),
                        "task_exposure_state": "NONE",
                    },
                )
            finally:
                instance._stopped = True
            raise exc

        try:
            instance._append_event(
                "PAIR_CREATED",
                category=category,
                repository=repository,
                frozen_identities=dict(frozen_identities),
            )
        except Exception:
            instance._stopped = True
            raise
        return instance

    @property
    def ledger_path(self) -> Path:
        """Controller-side path; never included in ``ScorerDelivery``."""

        return self._ledger_path

    def _execute(self, operation: Callable[[], _T]) -> _T:
        self._ensure_live()
        try:
            return operation()
        except (
            LifecycleIntegrationError,
            ledger.LedgerError,
            controller.ControllerStateError,
            scoring_bundle.BlindScoringBundleError,
            random_domains.RandomDomainError,
        ):
            self._stopped = True
            raise
        except Exception:
            self._stopped = True
            _fail()

    def _ensure_live(self) -> None:
        if self._stopped or self._completed:
            _fail()

    def _require_expected_paths_absent(self) -> None:
        expected = [
            self._checkpoint_path(controller.ORDER_FROZEN),
            self._checkpoint_path(controller.ATTEMPT_BOUND),
            self._checkpoint_path(controller.SCORING_BOUND),
            self._bundle_path(),
        ]
        if any(path.exists() for path in expected):
            _fail()

    def _pair_token(self) -> str:
        return hashlib.sha256(self._pair_id.encode("utf-8")).hexdigest()

    def _checkpoint_path(self, phase: str) -> Path:
        phase_name = phase.lower().replace("_", "-")
        return self._controller_root / f"{self._pair_token()}.{phase_name}.sealed.json"

    def _bundle_path(self) -> Path:
        return self._scoring_root / f"{self._pair_token()}.blind-scoring-bundle.json"

    def _genesis_event(self) -> dict[str, object]:
        return {
            "schema_version": ledger.LEDGER_SCHEMA,
            "event_seq": 1,
            "event_type": "V2_GENESIS",
            "event_id": str(uuid4()),
            "timestamp_utc": _timestamp_utc(),
            "evaluation_id": self._evaluation_id,
            "predecessor_digest": ledger.V1_LEDGER_SHA256,
            "adopted_protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
            "adopted_contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
            "adopted_schema_id": ledger.ADOPTED_SCHEMA_ID,
            "legacy_pair_id": ledger.LEGACY_PAIR_ID,
            "legacy_pair_state_at_v1": "PAIR_CREATED",
            "legacy_pair_attempts_used": 0,
            "legacy_pair_disposition": "PRE_ATTEMPT_TERMINATION",
            "attempt_ceiling_total": ledger.ATTEMPT_CEILING_TOTAL,
            "attempt_ceiling_breakdown": dict(ledger.ATTEMPT_CEILING_BREAKDOWN),
        }

    def _pair_event(self, *, sequence: int) -> dict[str, object]:
        return {
            "schema_version": ledger.LEDGER_SCHEMA,
            "event_seq": sequence,
            "event_type": "PAIR_CREATED",
            "event_id": str(uuid4()),
            "timestamp_utc": _timestamp_utc(),
            "pair_id": self._pair_id,
            "slot": SYNTHETIC_SLOT,
            "category": self._category,
            "repository": self._repository,
            "frozen_identities": dict(self._frozen_identities),
        }

    def _append_event(
        self,
        event_type: str,
        *,
        pair_id: str | None | object = ...,
        **extra: object,
    ) -> ledger.LedgerSummary:
        existing = ledger.read_ledger(self._ledger_path)
        sequence = len(existing) + 1
        event = {
            "schema_version": ledger.LEDGER_SCHEMA,
            "event_seq": sequence,
            "event_type": event_type,
            "event_id": str(uuid4()),
            "timestamp_utc": _timestamp_utc(),
            "pair_id": self._pair_id if pair_id is ... else pair_id,
            "slot": SYNTHETIC_SLOT,
            **extra,
        }
        expected = ledger.append_event(self._ledger_path, event)
        persisted = ledger.validate_ledger_file(self._ledger_path)
        if persisted != expected:
            raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)
        return persisted

    def _validated_events(self) -> tuple[list[dict[str, Any]], ledger.LedgerSummary]:
        events = ledger.read_ledger(self._ledger_path)
        summary = ledger.validate_ledger_events(events)
        genesis = events[0]
        if genesis.get("evaluation_id") != self._evaluation_id:
            _fail()
        pair_events = [event for event in events if event.get("event_type") == "PAIR_CREATED"]
        if len(pair_events) != 1:
            _fail()
        pair = pair_events[0]
        if (
            pair.get("pair_id") != self._pair_id
            or pair.get("slot") != SYNTHETIC_SLOT
            or pair.get("category") != self._category
            or pair.get("repository") != self._repository
            or pair.get("frozen_identities") != self._frozen_identities
        ):
            _fail()
        if any(
            event.get("slot") != SYNTHETIC_SLOT
            or event.get("pair_id") not in {None, self._pair_id}
            for event in events[1:]
        ):
            _fail()
        return events, summary

    def _attempt_states(self, events: Sequence[Mapping[str, Any]]) -> dict[str, str]:
        states: dict[str, str] = {}
        for event in events:
            event_type = event.get("event_type")
            if event_type == "ATTEMPT_ADMITTED":
                states[event["attempt_handle"]] = "ADMITTED"
            elif event_type == "TASK_EXPOSED":
                states[event["attempt_handle"]] = "TASK_EXPOSED"
            elif event_type == "EXECUTION_TERMINAL":
                states[event["attempt_handle"]] = "TERMINAL"
            elif event_type == "ADMITTED_NOT_EXPOSED":
                states[event["attempt_handle"]] = "ADMITTED_NOT_EXPOSED"
        return states

    def _admitted_handles(self, events: Sequence[Mapping[str, Any]]) -> list[str]:
        return [
            event["attempt_handle"]
            for event in events
            if event.get("event_type") == "ATTEMPT_ADMITTED"
        ]

    def _admission_for(
        self, events: Sequence[Mapping[str, Any]], attempt_handle: str
    ) -> dict[str, Any]:
        for event in events:
            if (
                event.get("event_type") == "ATTEMPT_ADMITTED"
                and event.get("attempt_handle") == attempt_handle
            ):
                return dict(event["admission_result"])
        _fail()

    def _seal_snapshot(
        self, snapshot: controller.ValidatedControllerSnapshot
    ) -> controller.SealedControllerPackage:
        package = controller.seal_controller_state(
            snapshot,
            key_path=self._key_path,
            custody_boundary=self._custody_boundary,
        )
        envelope = controller.parse_sealed_package(package.package_bytes)
        nonce = envelope["nonce_b64"]
        if nonce in self._sealed_nonces:
            raise controller.ControllerStateError(controller.SEALING_FAILURE)
        self._sealed_nonces.add(nonce)
        return package

    def _write_checkpoint(
        self,
        phase: str,
        package: controller.SealedControllerPackage,
        *,
        replace: bool,
    ) -> None:
        path = self._checkpoint_path(phase)
        _write_atomic_checkpoint(path, package.package_bytes, replace=replace)
        self._checkpoint_digests[phase] = package.sealed_package_digest

    def _read_checkpoint(self, phase: str) -> dict[str, Any]:
        path = self._checkpoint_path(phase)
        expected_digest = self._checkpoint_digests.get(phase)
        if expected_digest is None:
            _fail()
        try:
            package_bytes = path.read_bytes()
        except OSError:
            raise controller.ControllerStateError(
                controller.AUTHENTICATION_FAILURE
            ) from None
        if hashlib.sha256(package_bytes).hexdigest() != expected_digest:
            raise controller.ControllerStateError(controller.AUTHENTICATION_FAILURE)
        state = controller.open_controller_package(
            package_bytes,
            key_path=self._key_path,
            custody_boundary=self._custody_boundary,
            expected_digest=expected_digest,
            expected_evaluation_id=self._evaluation_id,
            expected_pair_id=self._pair_id,
            expected_slot=SYNTHETIC_SLOT,
        )
        if state["state_phase"] != phase:
            _fail()
        return state

    def admit_attempt(self) -> str:
        """Bind and durably admit the next arm without exposing it."""

        def operation() -> str:
            events, _ = self._validated_events()
            states = self._attempt_states(events)
            handles = self._admitted_handles(events)
            if len(handles) > 1 or (handles and states[handles[0]] != "TERMINAL"):
                _fail()
            previous_phase = (
                controller.ORDER_FROZEN if not handles else controller.ATTEMPT_BOUND
            )
            previous = self._read_checkpoint(previous_phase)
            private_handles = [
                binding["attempt_handle"] for binding in previous["attempt_bindings"]
            ]
            if private_handles != handles:
                _fail()

            entropy = _draw_entropy32()
            handle = self._identifier_registry.admit(
                random_domains.ATTEMPT_HANDLE_DOMAIN, entropy
            )
            current = {
                **previous,
                "state_phase": controller.ATTEMPT_BOUND,
                "attempt_bindings": [
                    *previous["attempt_bindings"],
                    {
                        "attempt_handle": handle,
                        "arm": previous["realized_order"][len(handles)],
                    },
                ],
            }
            snapshot = controller.validate_state_transition(previous, current)
            package = self._seal_snapshot(snapshot)
            self._write_checkpoint(
                controller.ATTEMPT_BOUND, package, replace=bool(handles)
            )
            self._append_event(
                "ATTEMPT_ADMITTED",
                attempt_handle=handle,
                attempt_state="ADMITTED",
                admission_result={
                    "status": "ADMITTED",
                    "preflight_ids": list(self._preflight_ids),
                    "task_exposure_state": "NONE",
                },
            )
            return handle

        return self._execute(operation)

    def expose_task(self, attempt_handle: str) -> ledger.LedgerSummary:
        """Append exposure; this is the initiated-attempt consumption boundary."""

        def operation() -> ledger.LedgerSummary:
            events, _ = self._validated_events()
            states = self._attempt_states(events)
            if states.get(attempt_handle) != "ADMITTED":
                _fail()
            admission = self._admission_for(events, attempt_handle)
            admission["task_exposure_state"] = "EXPOSED"
            return self._append_event(
                "TASK_EXPOSED",
                attempt_handle=attempt_handle,
                attempt_state="TASK_EXPOSED",
                admission_result=admission,
            )

        return self._execute(operation)

    def record_admitted_not_exposed(
        self, attempt_handle: str
    ) -> ledger.LedgerSummary:
        """Reserve one admitted handle and terminally stop without consumption."""

        def operation() -> ledger.LedgerSummary:
            events, _ = self._validated_events()
            states = self._attempt_states(events)
            if states.get(attempt_handle) != "ADMITTED":
                _fail()
            summary = self._append_event(
                "ADMITTED_NOT_EXPOSED",
                attempt_handle=attempt_handle,
                attempt_state="ADMITTED_NOT_EXPOSED",
                admission_result=self._admission_for(events, attempt_handle),
            )
            self._stopped = True
            return summary

        return self._execute(operation)

    def record_terminal(
        self,
        attempt_handle: str,
        *,
        correctness_result: Mapping[str, object],
        cost_metrics: Mapping[str, object],
        output_ref: str,
        output_payload: str,
    ) -> ledger.LedgerSummary:
        """Record terminal public evidence and retain live-process scoring input."""

        def operation() -> ledger.LedgerSummary:
            if not _is_nonempty_string(output_ref) or not _is_nonempty_string(
                output_payload
            ):
                _fail()
            events, _ = self._validated_events()
            states = self._attempt_states(events)
            if states.get(attempt_handle) != "TASK_EXPOSED":
                _fail()
            if attempt_handle in self._terminal_outputs:
                _fail()
            summary = self._append_event(
                "EXECUTION_TERMINAL",
                attempt_handle=attempt_handle,
                attempt_state="TERMINAL",
                correctness_result=dict(correctness_result),
                cost_metrics=dict(cost_metrics),
            )
            self._terminal_outputs[attempt_handle] = (output_ref, output_payload)
            return summary

        return self._execute(operation)

    def prepare_scoring(self) -> ScorerDelivery:
        """Seal final controller state and create one scorer-only bundle."""

        def operation() -> ScorerDelivery:
            events, _ = self._validated_events()
            handles = self._admitted_handles(events)
            states = self._attempt_states(events)
            if (
                len(handles) != 2
                or any(states.get(handle) != "TERMINAL" for handle in handles)
                or set(self._terminal_outputs) != set(handles)
            ):
                _fail()
            previous = self._read_checkpoint(controller.ATTEMPT_BOUND)
            if [
                binding["attempt_handle"] for binding in previous["attempt_bindings"]
            ] != handles:
                _fail()

            labels = [
                self._identifier_registry.admit(
                    random_domains.SCORING_LABEL_DOMAIN, _draw_entropy32()
                )
                for _ in range(2)
            ]
            outputs_by_label = {
                labels[index]: self._terminal_outputs[handle][1]
                for index, handle in enumerate(handles)
            }
            bundle = scoring_bundle.build_blind_scoring_bundle(
                evaluation_id=self._evaluation_id,
                pair_id=self._pair_id,
                slot=SYNTHETIC_SLOT,
                rubric_id=self._rubric_id,
                outputs_by_label=outputs_by_label,
                presentation_entropy=_draw_entropy32(),
            )
            bundle_bytes = scoring_bundle.encode_blind_scoring_bundle(bundle)
            current = {
                **previous,
                "state_phase": controller.SCORING_BOUND,
                "scoring_bindings": [
                    {
                        "scoring_label": labels[index],
                        "attempt_handle": handle,
                    }
                    for index, handle in enumerate(handles)
                ],
                "presentation_order": list(bundle["presentation_order"]),
                "attempt_output_refs": [
                    {
                        "attempt_handle": handle,
                        "output_ref": self._terminal_outputs[handle][0],
                    }
                    for handle in handles
                ],
            }
            snapshot = controller.validate_state_transition(previous, current)
            package = self._seal_snapshot(snapshot)
            self._write_checkpoint(
                controller.SCORING_BOUND, package, replace=False
            )
            bundle_path = self._bundle_path()
            _write_create_once(bundle_path, bundle_bytes)
            self._bundle_bytes = bundle_bytes
            self._append_event(
                "CONTROLLER_STATE_SEALED",
                sealed_package_digest=package.sealed_package_digest,
                score_count=0,
            )
            return ScorerDelivery(
                bundle_path=bundle_path,
                bundle_bytes=bundle_bytes,
            )

        return self._execute(operation)

    def _read_current_bundle(self) -> dict[str, Any]:
        if self._bundle_bytes is None:
            _fail()
        try:
            actual = self._bundle_path().read_bytes()
        except OSError:
            raise scoring_bundle.BlindScoringBundleError() from None
        if actual != self._bundle_bytes:
            raise scoring_bundle.BlindScoringBundleError()
        return scoring_bundle.parse_blind_scoring_bundle(actual)

    def _sealed_public_digest(self, events: Sequence[Mapping[str, Any]]) -> str:
        records = [
            event
            for event in events
            if event.get("event_type")
            in {"CONTROLLER_STATE_SEALED", "SCORING_RECORDED"}
        ]
        if not records:
            _fail()
        digest = records[-1].get("sealed_package_digest")
        if digest != self._checkpoint_digests.get(controller.SCORING_BOUND):
            _fail()
        return digest

    def acknowledge_score(self, scoring_label: str) -> int:
        """Acknowledge one label only; score values are intentionally not accepted."""

        def operation() -> int:
            events, _ = self._validated_events()
            if events[-1]["event_type"] not in {
                "CONTROLLER_STATE_SEALED",
            }:
                _fail()
            bundle = self._read_current_bundle()
            if (
                scoring_label not in bundle["presentation_order"]
                or scoring_label in self._completed_labels
            ):
                _fail()
            self._completed_labels.add(scoring_label)
            count = len(self._completed_labels)
            if count == 2:
                self._append_event(
                    "SCORING_RECORDED",
                    sealed_package_digest=self._sealed_public_digest(events),
                    score_count=2,
                )
            return count

        return self._execute(operation)

    def authenticate_synthetic_unblinding(self) -> SyntheticUnblindingResult:
        """Authenticate synthetic opening after both score acknowledgements."""

        def operation() -> SyntheticUnblindingResult:
            events, _ = self._validated_events()
            if len(self._completed_labels) != 2:
                if events[-1]["event_type"] == "CONTROLLER_STATE_SEALED":
                    self._append_event(
                        "PREMATURE_UNBLINDING",
                        sealed_package_digest=self._sealed_public_digest(events),
                        score_count=len(self._completed_labels),
                    )
                self._stopped = True
                _fail(PREMATURE_UNBLINDING_STOP)
            if events[-1]["event_type"] != "SCORING_RECORDED":
                _fail()

            state = self._read_checkpoint(controller.SCORING_BOUND)
            handle_to_arm = {
                binding["attempt_handle"]: binding["arm"]
                for binding in state["attempt_bindings"]
            }
            label_to_handle = {
                binding["scoring_label"]: binding["attempt_handle"]
                for binding in state["scoring_bindings"]
            }
            result = SyntheticUnblindingResult(
                scoring_label_to_arm=tuple(
                    (label, handle_to_arm[label_to_handle[label]])
                    for label in state["presentation_order"]
                )
            )
            self._append_event(
                "UNBLINDING_RECORDED",
                sealed_package_digest=self._sealed_public_digest(events),
                score_count=2,
            )
            self._completed = True
            return result

        return self._execute(operation)


assert tuple(field.name for field in fields(ScorerDelivery)) == (
    "bundle_path",
    "bundle_bytes",
)
