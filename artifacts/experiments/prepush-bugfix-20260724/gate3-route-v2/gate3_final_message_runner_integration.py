"""Offline-only Gate 3 runner/capture integration seam.

The coordinator accepts an injected contained-process callable.  It never reads
credentials, launches Codex, or retains stdout/stderr.  Public evidence proves
only a closed, internally linked attestation chain.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Mapping

import gate3_final_message_actual_capture as capture


PUBLIC_CLAIM = capture.PUBLIC_CLAIM
INTEGRATION_AUTHORITY_PATH = "runner-integration-authority.json"
INTEGRATION_CONTRACT_PATH = "runner-integration-contract.json"
OBSERVATION_STAGE_PATH = "runner-observation-stage.json"
FINAL_OBSERVATION_PATH = "final-output-observation.json"
WORKSPACE_OBSERVATION_PATH = "workspace-observation.json"
SEAL_PATH = "runner-observation-seal.json"
CLEANUP_PATH = "runner-cleanup-result.json"
CLEANUP_AUTHORIZATION_PATH = "runner-cleanup-authorization.json"
RECEIPT_PATH = "runner-receipt.json"
FINALIZATION_PATH = "runner-finalization.json"

INTEGRATION_AUTHORITY_SCHEMA = "gate3-route-v2.runner-integration-authority.v1"
FINAL_OBSERVATION_SCHEMA = "gate3-route-v2.final-output-observation.v1"
OBSERVATION_STAGE_SCHEMA = "gate3-route-v2.observation-stage.v1"
WORKSPACE_OBSERVATION_SCHEMA = "gate3-route-v2.workspace-observation.v1"
SEAL_SCHEMA = "gate3-route-v2.runner-observation-seal.v1"
CLEANUP_SCHEMA = "gate3-route-v2.runner-cleanup-result.v1"
CLEANUP_AUTHORIZATION_SCHEMA = "gate3-route-v2.runner-cleanup-authorization.v1"
RECEIPT_SCHEMA = "gate3-route-v2.runner-receipt.v1"
FINALIZATION_SCHEMA = "gate3-route-v2.runner-finalization.v1"

FINAL_STATES = {"CAPTURED", "ABSENT", "READ_FAILED"}
WORKSPACE_STATES = {"CHANGED", "UNCHANGED", "CAPTURE_FAILED"}
PROFILES = {
    "RUNNER_CAPTURE_FINALIZED",
    "RUNNER_CAPTURE_NEGATIVE",
    "RUNNER_CAPTURE_RESULT_UNKNOWN",
    "RUNNER_SEAL_UNAVAILABLE",
}
CHECKPOINTS = (
    "before_authorization",
    "before_invocation",
    "before_private_parse",
    "before_seal",
)
RUNTIME_SUBJECTS = {
    "runner_source",
    "integration_source",
    "adapter_source",
    "adapter_contract",
    "raw_contract",
    "projector_contract",
    "public_schemas",
}
RUNNER_INTEGRATION_CONTRACT_BYTES = capture.canonical_bytes(
    {
        "checkpoints": list(CHECKPOINTS),
        "cleanup_protocol": "CREATE_ONCE_AUTHORIZATION_THEN_RESULT_NO_RETRY",
        "observation_protocol": "CREATE_ONCE_CHAIN_AUTHORIZATION_BEFORE_LAUNCH",
        "launch_ordinal": 1,
        "profiles": sorted(PROFILES),
        "replacement": False,
        "retry": False,
        "runtime_subjects": sorted(RUNTIME_SUBJECTS),
        "schema": "gate3-route-v2.runner-integration-contract.v1",
        "stdout_handoff_count": 1,
    }
)


class IntegrationError(ValueError):
    """Closed integration error that never renders private input."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SyntheticIntegrationCrash(RuntimeError):
    """Deterministic crash used only by injected offline tests."""


class ContainedStartFailed(RuntimeError):
    """Typed injected boundary proving that process creation did not succeed."""


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _parse_canonical(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("ascii"))
        if not isinstance(value, dict) or capture.canonical_bytes(value) != payload:
            raise IntegrationError("PUBLIC_ARTIFACT_INVALID")
        return value
    except IntegrationError:
        raise
    except Exception:
        raise IntegrationError("PUBLIC_ARTIFACT_INVALID") from None


def _exact_fields(value: Mapping[str, object], fields: set[str]) -> None:
    if set(value) != fields:
        raise IntegrationError("PUBLIC_ARTIFACT_INVALID")


@dataclass(frozen=True)
class RuntimeAuthority:
    action_sha256: str
    arm: str
    git_commit: str
    runner_blob: str
    integration_blob: str
    integration_contract_sha256: str
    capture_bindings_sha256: str
    runtime_sha256: Mapping[str, str]

    def validate(self) -> None:
        if (
            not _is_sha256(self.action_sha256)
            or not _is_sha256(self.integration_contract_sha256)
            or not _is_sha256(self.capture_bindings_sha256)
        ):
            raise IntegrationError("INTEGRATION_AUTHORITY_INVALID")
        if self.arm not in {"A", "B"}:
            raise IntegrationError("INTEGRATION_AUTHORITY_INVALID")
        if not all(
            isinstance(item, str)
            and len(item) in {40, 64}
            and all(character in "0123456789abcdef" for character in item)
            for item in (self.git_commit, self.runner_blob, self.integration_blob)
        ):
            raise IntegrationError("INTEGRATION_AUTHORITY_INVALID")
        if set(self.runtime_sha256) != RUNTIME_SUBJECTS or not all(
            isinstance(name, str) and name and _is_sha256(digest)
            for name, digest in self.runtime_sha256.items()
        ):
            raise IntegrationError("INTEGRATION_AUTHORITY_INVALID")

    def public_value(self) -> dict[str, object]:
        self.validate()
        return {
            "action_sha256": self.action_sha256,
            "arm": self.arm,
            "capture_ordinal": 1,
            "capture_bindings_sha256": self.capture_bindings_sha256,
            "git_commit": self.git_commit,
            "integration_blob": self.integration_blob,
            "integration_contract_sha256": self.integration_contract_sha256,
            "launch_ordinal": 1,
            "replacement": False,
            "retry": False,
            "runner_blob": self.runner_blob,
            "runtime_sha256": dict(sorted(self.runtime_sha256.items())),
            "schema": INTEGRATION_AUTHORITY_SCHEMA,
        }


@dataclass(frozen=True)
class InjectedContainedResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    process_disposition: str = "EXITED"
    stdout_eof: bool = True
    stdout_reader_complete: bool = True
    stdout_read_failed: bool = False

    def process_result(self) -> dict[str, object]:
        return capture.build_process_result(
            exit_code=self.returncode,
            process_disposition=self.process_disposition,
            stdout_eof=self.stdout_eof,
            stdout_reader_complete=self.stdout_reader_complete,
            stdout_read_failed=self.stdout_read_failed,
        )


@dataclass(frozen=True)
class IntegrationResult:
    profile: str
    capture_status: str
    claim: str
    cleanup_result: str


@dataclass(frozen=True)
class Verification:
    verified: bool
    code: str
    profile: str | None = None
    claim: str | None = None


def derive_profile(
    capture_status: str, final_state: str, workspace_state: str
) -> str:
    if capture_status == "COMPLETE" and final_state == "CAPTURED" and workspace_state == "CHANGED":
        return "RUNNER_CAPTURE_FINALIZED"
    return "RUNNER_CAPTURE_NEGATIVE"


def cleanup_admitted(
    profile: str, capture_status: str, final_state: str, workspace_state: str
) -> bool:
    """Closed ordinary-cleanup matrix derived only from retained terminal facts."""

    if profile != derive_profile(capture_status, final_state, workspace_state):
        return False
    if profile == "RUNNER_CAPTURE_FINALIZED":
        return (
            capture_status == "COMPLETE"
            and final_state == "CAPTURED"
            and workspace_state == "CHANGED"
        )
    return capture_status in {"COMPLETE", "INCOMPLETE", "INVALID"}


def _runtime_binding_sha256(bindings: capture.CaptureBindings) -> dict[str, str]:
    return {
        "adapter_source": bindings.adapter_source_sha256,
        "adapter_contract": bindings.adapter_contract_sha256,
        "raw_contract": bindings.raw_envelope_contract_sha256,
        "projector_contract": bindings.lifecycle_projector_sha256,
        "public_schemas": capture.sha256(
            capture.canonical_bytes(dict(bindings.public_schema_sha256))
        ),
    }


def _validate_runtime_binding(
    authority: RuntimeAuthority, bindings: capture.CaptureBindings
) -> None:
    expected = _runtime_binding_sha256(bindings)
    if any(authority.runtime_sha256.get(name) != digest for name, digest in expected.items()):
        raise IntegrationError("RUNTIME_CAPTURE_BINDING_MISMATCH")


def _validate_authority_artifact(
    evidence_store: capture.CreateOnceStore, authority: RuntimeAuthority
) -> None:
    retained = _parse_canonical(evidence_store.read(INTEGRATION_AUTHORITY_PATH))
    if retained != authority.public_value():
        raise IntegrationError("INTEGRATION_AUTHORITY_MISMATCH")


def _validate_contract_artifact(
    evidence_store: capture.CreateOnceStore, authority: RuntimeAuthority
) -> None:
    payload = evidence_store.read(INTEGRATION_CONTRACT_PATH)
    if (
        payload != RUNNER_INTEGRATION_CONTRACT_BYTES
        or capture.sha256(payload) != authority.integration_contract_sha256
    ):
        raise IntegrationError("INTEGRATION_CONTRACT_MISMATCH")


def _validate_observation(
    evidence_store: capture.CreateOnceStore,
    path: str,
    schema: str,
    states: set[str],
) -> dict[str, object]:
    value = _parse_canonical(evidence_store.read(path))
    _exact_fields(value, {"schema", "state"})
    if value["schema"] != schema or value["state"] not in states:
        raise IntegrationError("OBSERVATION_INVALID")
    return value


def _validate_capture_unknown_prefix(
    store: capture.CreateOnceStore, bindings: capture.CaptureBindings
) -> None:
    paths = set(store.files)
    allowed = (
        {capture.AUTHORIZATION_PATH},
        {capture.AUTHORIZATION_PATH, capture.PROCESS_RESULT_PATH},
        {
            capture.AUTHORIZATION_PATH,
            capture.PROCESS_RESULT_PATH,
            capture.PROJECTION_PATH,
        },
    )
    if paths not in allowed:
        raise IntegrationError("PROFILE_INVENTORY_INVALID")
    authorization_sha = capture.verify_authorization_for_launch(store, bindings)
    if capture.PROCESS_RESULT_PATH in paths:
        process_payload = store.read(capture.PROCESS_RESULT_PATH)
        process_result = _parse_canonical(process_payload)
        capture.validate_process_result(process_result)
    if capture.PROJECTION_PATH in paths:
        projection_payload = store.read(capture.PROJECTION_PATH)
        projection = _parse_canonical(projection_payload)
        capture.validate_projection(projection, bindings)
        if not authorization_sha:
            raise IntegrationError("PUBLIC_LINK_MISMATCH")


def _validate_observation_stage(
    capture_store: capture.CreateOnceStore,
    evidence_store: capture.CreateOnceStore,
) -> None:
    observation_stage = _parse_canonical(evidence_store.read(OBSERVATION_STAGE_PATH))
    _exact_fields(
        observation_stage, {"capture_authorization_sha256", "schema", "stage"}
    )
    if observation_stage != {
        "capture_authorization_sha256": capture.sha256(
            capture_store.read(capture.AUTHORIZATION_PATH)
        ),
        "schema": OBSERVATION_STAGE_SCHEMA,
        "stage": "OBSERVATION_CHAIN_AUTHORIZED",
    }:
        raise IntegrationError("OBSERVATION_STAGE_INVALID")


def _validate_precleanup(
    capture_store: capture.CreateOnceStore,
    evidence_store: capture.CreateOnceStore,
    bindings: capture.CaptureBindings,
    authority: RuntimeAuthority,
) -> str:
    if set(evidence_store.files) != {
        INTEGRATION_AUTHORITY_PATH,
        INTEGRATION_CONTRACT_PATH,
        OBSERVATION_STAGE_PATH,
        FINAL_OBSERVATION_PATH,
        WORKSPACE_OBSERVATION_PATH,
        SEAL_PATH,
    }:
        raise IntegrationError("PRE_CLEANUP_INVENTORY_INVALID")
    _validate_authority_artifact(evidence_store, authority)
    _validate_contract_artifact(evidence_store, authority)
    _validate_observation_stage(capture_store, evidence_store)
    public_capture = capture.verify_public(capture_store, bindings)
    if not public_capture.verified or public_capture.claim != PUBLIC_CLAIM:
        raise IntegrationError("CAPTURE_PUBLIC_VERIFICATION_FAILED")
    final_observation = _validate_observation(
        evidence_store, FINAL_OBSERVATION_PATH, FINAL_OBSERVATION_SCHEMA, FINAL_STATES
    )
    workspace_observation = _validate_observation(
        evidence_store,
        WORKSPACE_OBSERVATION_PATH,
        WORKSPACE_OBSERVATION_SCHEMA,
        WORKSPACE_STATES,
    )
    result = _parse_canonical(capture_store.read(capture.CAPTURE_RESULT_PATH))
    expected_profile = derive_profile(
        str(result["status"]),
        str(final_observation["state"]),
        str(workspace_observation["state"]),
    )
    seal = _parse_canonical(evidence_store.read(SEAL_PATH))
    _exact_fields(
        seal,
        {
            "authority_sha256",
            "capture_artifact_sha256",
            "capture_status",
            "final_observation_sha256",
            "integration_contract_sha256",
            "observation_stage_sha256",
            "profile",
            "schema",
            "workspace_observation_sha256",
        },
    )
    if (
        seal["schema"] != SEAL_SCHEMA
        or seal["profile"] != expected_profile
        or seal["capture_status"] != result["status"]
        or seal["authority_sha256"]
        != capture.sha256(evidence_store.read(INTEGRATION_AUTHORITY_PATH))
        or seal["final_observation_sha256"]
        != capture.sha256(evidence_store.read(FINAL_OBSERVATION_PATH))
        or seal["integration_contract_sha256"]
        != capture.sha256(evidence_store.read(INTEGRATION_CONTRACT_PATH))
        or seal["observation_stage_sha256"]
        != capture.sha256(evidence_store.read(OBSERVATION_STAGE_PATH))
        or seal["workspace_observation_sha256"]
        != capture.sha256(evidence_store.read(WORKSPACE_OBSERVATION_PATH))
        or seal["capture_artifact_sha256"]
        != {
            path: capture.sha256(payload)
            for path, payload in sorted(capture_store.files.items())
        }
    ):
        raise IntegrationError("SEAL_LINK_INVALID")
    return expected_profile


@dataclass
class RunnerIntegrationCoordinator:
    capture_store: capture.CreateOnceStore
    evidence_store: capture.CreateOnceStore
    bindings: capture.CaptureBindings
    authority: RuntimeAuthority
    runtime_readers: Mapping[str, Callable[[], bytes]]
    invoke: Callable[[], InjectedContainedResult]
    observe_final: Callable[[], str]
    observe_workspace: Callable[[], str]
    cleanup: Callable[[], str]
    crash_at: str | None = None

    def _crash(self, point: str) -> None:
        if self.crash_at == point:
            raise SyntheticIntegrationCrash(point)

    def _check_runtime(self, checkpoint: str) -> None:
        if checkpoint not in CHECKPOINTS:
            raise IntegrationError("TOCTOU_CHECKPOINT_INVALID")
        if set(self.runtime_readers) != set(self.authority.runtime_sha256):
            raise IntegrationError("RUNTIME_SOURCE_INVENTORY_MISMATCH")
        try:
            for name, expected in self.authority.runtime_sha256.items():
                payload = self.runtime_readers[name]()
                if type(payload) is not bytes or capture.sha256(payload) != expected:
                    raise IntegrationError("RUNTIME_SOURCE_MISMATCH")
        except IntegrationError:
            raise
        except Exception:
            raise IntegrationError("RUNTIME_SOURCE_UNAVAILABLE") from None

    def _publish_authority(self) -> str:
        if self.authority.integration_contract_sha256 != capture.sha256(
            RUNNER_INTEGRATION_CONTRACT_BYTES
        ):
            raise IntegrationError("INTEGRATION_CONTRACT_MISMATCH")
        contract_digest = self.evidence_store.publish(
            INTEGRATION_CONTRACT_PATH, RUNNER_INTEGRATION_CONTRACT_BYTES
        )
        if (
            self.evidence_store.read(INTEGRATION_CONTRACT_PATH)
            != RUNNER_INTEGRATION_CONTRACT_BYTES
            or contract_digest != self.authority.integration_contract_sha256
        ):
            raise IntegrationError("INTEGRATION_CONTRACT_MISMATCH")
        payload = capture.canonical_bytes(self.authority.public_value())
        digest = self.evidence_store.publish(INTEGRATION_AUTHORITY_PATH, payload)
        if self.evidence_store.read(INTEGRATION_AUTHORITY_PATH) != payload:
            raise IntegrationError("DURABLE_REOPEN_MISMATCH")
        return digest

    def _publish_observation(self, path: str, schema: str, state: str) -> str:
        payload = capture.canonical_bytes({"schema": schema, "state": state})
        digest = self.evidence_store.publish(path, payload)
        if self.evidence_store.read(path) != payload:
            raise IntegrationError("DURABLE_REOPEN_MISMATCH")
        return digest

    def _continue_after_seal(self) -> IntegrationResult:
        base_paths = {
            INTEGRATION_AUTHORITY_PATH,
            INTEGRATION_CONTRACT_PATH,
            OBSERVATION_STAGE_PATH,
            FINAL_OBSERVATION_PATH,
            WORKSPACE_OBSERVATION_PATH,
            SEAL_PATH,
        }
        allowed_paths = (
            base_paths,
            base_paths | {CLEANUP_AUTHORIZATION_PATH},
            base_paths | {CLEANUP_AUTHORIZATION_PATH, CLEANUP_PATH},
            base_paths | {CLEANUP_AUTHORIZATION_PATH, CLEANUP_PATH, RECEIPT_PATH},
            base_paths
            | {
                CLEANUP_AUTHORIZATION_PATH,
                CLEANUP_PATH,
                RECEIPT_PATH,
                FINALIZATION_PATH,
            },
        )
        if set(self.evidence_store.files) not in allowed_paths:
            raise IntegrationError("POST_SEAL_INVENTORY_INVALID")
        precleanup = capture.CreateOnceStore(
            {path: self.evidence_store.files[path] for path in base_paths}
        )
        profile = _validate_precleanup(
            self.capture_store, precleanup, self.bindings, self.authority
        )
        seal_payload = self.evidence_store.read(SEAL_PATH)
        seal_sha = capture.sha256(seal_payload)
        seal = _parse_canonical(seal_payload)
        if seal.get("profile") != profile:
            raise IntegrationError("SEAL_LINK_INVALID")
        final_state = str(
            _parse_canonical(self.evidence_store.read(FINAL_OBSERVATION_PATH))["state"]
        )
        workspace_state = str(
            _parse_canonical(self.evidence_store.read(WORKSPACE_OBSERVATION_PATH))["state"]
        )
        capture_status = str(seal["capture_status"])
        admitted = cleanup_admitted(
            profile, capture_status, final_state, workspace_state
        )
        if CLEANUP_PATH in self.evidence_store.files and not admitted:
            raise IntegrationError("CLEANUP_NOT_ADMITTED")

        if CLEANUP_PATH not in self.evidence_store.files:
            if profile == "RUNNER_CAPTURE_NEGATIVE" and not admitted:
                raise IntegrationError("NEGATIVE_CLEANUP_NOT_ADMITTED")
            if profile == "RUNNER_CAPTURE_FINALIZED" and not admitted:
                raise IntegrationError("CLEANUP_NOT_ADMITTED")
            cleanup_authorization = capture.canonical_bytes(
                {
                    "attempt_ordinal": 1,
                    "profile": profile,
                    "retry": False,
                    "schema": CLEANUP_AUTHORIZATION_SCHEMA,
                    "seal_sha256": seal_sha,
                }
            )
            if CLEANUP_AUTHORIZATION_PATH in self.evidence_store.files:
                if self.evidence_store.read(CLEANUP_AUTHORIZATION_PATH) != cleanup_authorization:
                    raise IntegrationError("CLEANUP_AUTHORIZATION_INVALID")
                raise IntegrationError("CLEANUP_RESULT_UNKNOWN")
            self.evidence_store.publish(
                CLEANUP_AUTHORIZATION_PATH, cleanup_authorization
            )
            if self.evidence_store.read(CLEANUP_AUTHORIZATION_PATH) != cleanup_authorization:
                raise IntegrationError("DURABLE_REOPEN_MISMATCH")
            self._crash("after_cleanup_authorization_before_side_effect")
            try:
                cleanup_result = self.cleanup()
            except Exception:
                cleanup_result = "FAIL"
            if cleanup_result not in {"PASS", "FAIL"}:
                raise IntegrationError("CLEANUP_RESULT_INVALID")
            cleanup_payload = capture.canonical_bytes(
                {"result": cleanup_result, "schema": CLEANUP_SCHEMA, "seal_sha256": seal_sha}
            )
            self.evidence_store.publish(CLEANUP_PATH, cleanup_payload)
            self._crash("after_cleanup_before_receipt")

        cleanup_authorization = _parse_canonical(
            self.evidence_store.read(CLEANUP_AUTHORIZATION_PATH)
        )
        _exact_fields(
            cleanup_authorization,
            {"attempt_ordinal", "profile", "retry", "schema", "seal_sha256"},
        )
        if cleanup_authorization != {
            "attempt_ordinal": 1,
            "profile": profile,
            "retry": False,
            "schema": CLEANUP_AUTHORIZATION_SCHEMA,
            "seal_sha256": seal_sha,
        }:
            raise IntegrationError("CLEANUP_AUTHORIZATION_INVALID")

        cleanup_payload = self.evidence_store.read(CLEANUP_PATH)
        cleanup = _parse_canonical(cleanup_payload)
        _exact_fields(cleanup, {"result", "schema", "seal_sha256"})
        if (
            cleanup["schema"] != CLEANUP_SCHEMA
            or cleanup["result"] not in {"PASS", "FAIL"}
            or cleanup["seal_sha256"] != seal_sha
        ):
            raise IntegrationError("CLEANUP_LINK_INVALID")
        cleanup_sha = capture.sha256(cleanup_payload)
        receipt_disposition = (
            "DIAGNOSTIC_RECEIPT"
            if profile == "RUNNER_CAPTURE_FINALIZED" and cleanup["result"] == "PASS"
            else "NEGATIVE_RECEIPT"
        )
        if RECEIPT_PATH not in self.evidence_store.files:
            receipt_payload = capture.canonical_bytes(
                {
                    "cleanup_sha256": cleanup_sha,
                    "disposition": receipt_disposition,
                    "profile": profile,
                    "schema": RECEIPT_SCHEMA,
                    "seal_sha256": seal_sha,
                }
            )
            self.evidence_store.publish(RECEIPT_PATH, receipt_payload)
            self._crash("after_receipt_before_finalization")
        receipt_payload = self.evidence_store.read(RECEIPT_PATH)
        receipt = _parse_canonical(receipt_payload)
        _exact_fields(
            receipt,
            {"cleanup_sha256", "disposition", "profile", "schema", "seal_sha256"},
        )
        if (
            receipt["schema"] != RECEIPT_SCHEMA
            or receipt["cleanup_sha256"] != cleanup_sha
            or receipt["disposition"] != receipt_disposition
            or receipt["profile"] != profile
            or receipt["seal_sha256"] != seal_sha
        ):
            raise IntegrationError("RECEIPT_LINK_INVALID")
        if FINALIZATION_PATH not in self.evidence_store.files:
            finalization_payload = capture.canonical_bytes(
                {
                    "disposition": (
                        "FINALIZED_DIAGNOSTIC"
                        if receipt_disposition == "DIAGNOSTIC_RECEIPT"
                        else "FINALIZED_NEGATIVE"
                    ),
                    "profile": profile,
                    "receipt_sha256": capture.sha256(receipt_payload),
                    "schema": FINALIZATION_SCHEMA,
                }
            )
            self.evidence_store.publish(FINALIZATION_PATH, finalization_payload)
        verified = verify_package(
            self.capture_store, self.evidence_store, self.bindings, self.authority
        )
        if not verified.verified:
            raise IntegrationError(verified.code)
        return IntegrationResult(
            profile, capture_status, PUBLIC_CLAIM, str(cleanup["result"])
        )

    def resume_after_seal(self) -> IntegrationResult:
        """Continue cleanup/receipt/finalization only; never invoke or recapture."""

        if SEAL_PATH not in self.evidence_store.files:
            raise IntegrationError("SEALED_CONTINUATION_UNAVAILABLE")
        return self._continue_after_seal()

    def run(self) -> IntegrationResult:
        self.authority.validate()
        self.bindings.validate()
        if (
            self.bindings.action_sha256 != self.authority.action_sha256
            or self.bindings.arm != self.authority.arm
            or capture.sha256(capture.canonical_bytes(self.bindings.authorization()))
            != self.authority.capture_bindings_sha256
        ):
            raise IntegrationError("INTEGRATION_AUTHORITY_MISMATCH")
        _validate_runtime_binding(self.authority, self.bindings)
        if self.capture_store.files or self.evidence_store.files:
            raise IntegrationError("INTEGRATION_ALREADY_STARTED")

        self._crash("r0_before_runtime_check")
        self._check_runtime("before_authorization")
        self._publish_authority()
        publisher = capture.CapturePublisher(self.capture_store)
        expected_capture_authorization = capture.canonical_bytes(
            self.bindings.authorization()
        )
        observation_stage_payload = capture.canonical_bytes(
            {
                "capture_authorization_sha256": capture.sha256(
                    expected_capture_authorization
                ),
                "schema": OBSERVATION_STAGE_SCHEMA,
                "stage": "OBSERVATION_CHAIN_AUTHORIZED",
            }
        )
        self.evidence_store.publish(OBSERVATION_STAGE_PATH, observation_stage_payload)
        if self.evidence_store.read(OBSERVATION_STAGE_PATH) != observation_stage_payload:
            raise IntegrationError("DURABLE_REOPEN_MISMATCH")
        publisher.authorize(self.bindings)
        self._crash("after_authorization_before_invoke")

        self._check_runtime("before_invocation")
        self._crash("before_invoke_entry")
        try:
            completed = self.invoke()
        except SyntheticIntegrationCrash:
            raise
        except ContainedStartFailed:
            completed = InjectedContainedResult(
                returncode=None,
                stdout=b"",
                stderr=b"",
                process_disposition="START_FAILED",
                stdout_eof=False,
                stdout_reader_complete=False,
                stdout_read_failed=True,
            )
        except Exception:
            raise IntegrationError("INVOCATION_DISPOSITION_UNKNOWN") from None
        self._crash("after_invoke_before_capture")
        if not isinstance(completed, InjectedContainedResult):
            raise IntegrationError("CONTAINED_RESULT_INVALID")
        self._check_runtime("before_private_parse")
        capture_result = publisher.capture(
            completed.stdout, completed.process_result(), self.bindings
        )
        public_capture = capture.verify_public(self.capture_store, self.bindings)
        if not public_capture.verified or public_capture.claim != PUBLIC_CLAIM:
            raise IntegrationError("CAPTURE_PUBLIC_VERIFICATION_FAILED")
        self._crash("after_capture_before_observations")

        try:
            final_state = self.observe_final()
        except Exception:
            final_state = "READ_FAILED"
        try:
            workspace_state = self.observe_workspace()
        except Exception:
            workspace_state = "CAPTURE_FAILED"
        if type(final_state) is not str or final_state not in FINAL_STATES:
            final_state = "READ_FAILED"
        if type(workspace_state) is not str or workspace_state not in WORKSPACE_STATES:
            workspace_state = "CAPTURE_FAILED"
        final_sha = self._publish_observation(
            FINAL_OBSERVATION_PATH, FINAL_OBSERVATION_SCHEMA, final_state
        )
        workspace_sha = self._publish_observation(
            WORKSPACE_OBSERVATION_PATH, WORKSPACE_OBSERVATION_SCHEMA, workspace_state
        )
        self._crash("after_observations_before_seal")
        self._check_runtime("before_seal")

        profile = derive_profile(
            str(capture_result["status"]), final_state, workspace_state
        )
        authority_sha = capture.sha256(
            self.evidence_store.read(INTEGRATION_AUTHORITY_PATH)
        )
        capture_digests = {
            path: capture.sha256(payload)
            for path, payload in sorted(self.capture_store.files.items())
        }
        seal = {
            "authority_sha256": authority_sha,
            "capture_artifact_sha256": capture_digests,
            "capture_status": capture_result["status"],
            "final_observation_sha256": final_sha,
            "integration_contract_sha256": capture.sha256(
                self.evidence_store.read(INTEGRATION_CONTRACT_PATH)
            ),
            "observation_stage_sha256": capture.sha256(
                self.evidence_store.read(OBSERVATION_STAGE_PATH)
            ),
            "profile": profile,
            "schema": SEAL_SCHEMA,
            "workspace_observation_sha256": workspace_sha,
        }
        seal_payload = capture.canonical_bytes(seal)
        seal_sha = self.evidence_store.publish(SEAL_PATH, seal_payload)
        if self.evidence_store.read(SEAL_PATH) != seal_payload:
            raise IntegrationError("DURABLE_REOPEN_MISMATCH")
        self._crash("after_seal_before_cleanup")

        return self._continue_after_seal()


def reconstruct_profile(
    capture_store: capture.CreateOnceStore, evidence_store: capture.CreateOnceStore
) -> str:
    if capture.AUTHORIZATION_PATH not in capture_store.files:
        return "NOT_STARTED"
    if capture.CAPTURE_RESULT_PATH not in capture_store.files:
        return "RUNNER_CAPTURE_RESULT_UNKNOWN"
    if SEAL_PATH not in evidence_store.files:
        return "RUNNER_SEAL_UNAVAILABLE"
    try:
        seal = _parse_canonical(evidence_store.read(SEAL_PATH))
        profile = seal.get("profile")
        if profile not in {
            "RUNNER_CAPTURE_FINALIZED",
            "RUNNER_CAPTURE_NEGATIVE",
        }:
            return "INVALID"
        return str(profile)
    except IntegrationError:
        return "INVALID"


def verify_package(
    capture_store: capture.CreateOnceStore,
    evidence_store: capture.CreateOnceStore,
    bindings: capture.CaptureBindings,
    authority: RuntimeAuthority,
) -> Verification:
    try:
        authority.validate()
        if (
            bindings.action_sha256 != authority.action_sha256
            or bindings.arm != authority.arm
            or capture.sha256(capture.canonical_bytes(bindings.authorization()))
            != authority.capture_bindings_sha256
        ):
            raise IntegrationError("INTEGRATION_AUTHORITY_MISMATCH")
        _validate_runtime_binding(authority, bindings)
        profile = reconstruct_profile(capture_store, evidence_store)
        if profile == "RUNNER_CAPTURE_RESULT_UNKNOWN":
            _validate_capture_unknown_prefix(capture_store, bindings)
            if set(evidence_store.files) != {
                INTEGRATION_AUTHORITY_PATH,
                INTEGRATION_CONTRACT_PATH,
                OBSERVATION_STAGE_PATH,
            }:
                raise IntegrationError("PROFILE_INVENTORY_INVALID")
            _validate_authority_artifact(evidence_store, authority)
            _validate_contract_artifact(evidence_store, authority)
            observation_stage = _parse_canonical(
                evidence_store.read(OBSERVATION_STAGE_PATH)
            )
            if observation_stage != {
                "capture_authorization_sha256": capture.sha256(
                    capture_store.read(capture.AUTHORIZATION_PATH)
                ),
                "schema": OBSERVATION_STAGE_SCHEMA,
                "stage": "OBSERVATION_CHAIN_AUTHORIZED",
            }:
                raise IntegrationError("OBSERVATION_STAGE_INVALID")
            return Verification(True, "VERIFIED", profile, None)
        if profile == "RUNNER_SEAL_UNAVAILABLE":
            capture_verification = capture.verify_public(capture_store, bindings)
            if not capture_verification.verified:
                raise IntegrationError("CAPTURE_PUBLIC_VERIFICATION_FAILED")
            allowed_prefixes = (
                {
                    INTEGRATION_AUTHORITY_PATH,
                    INTEGRATION_CONTRACT_PATH,
                    OBSERVATION_STAGE_PATH,
                },
                {
                    INTEGRATION_AUTHORITY_PATH,
                    INTEGRATION_CONTRACT_PATH,
                    OBSERVATION_STAGE_PATH,
                    FINAL_OBSERVATION_PATH,
                },
                {
                    INTEGRATION_AUTHORITY_PATH,
                    INTEGRATION_CONTRACT_PATH,
                    OBSERVATION_STAGE_PATH,
                    FINAL_OBSERVATION_PATH,
                    WORKSPACE_OBSERVATION_PATH,
                },
            )
            current_paths = set(evidence_store.files)
            if current_paths not in allowed_prefixes:
                raise IntegrationError("PROFILE_INVENTORY_INVALID")
            _validate_authority_artifact(evidence_store, authority)
            _validate_contract_artifact(evidence_store, authority)
            observation_stage = _parse_canonical(
                evidence_store.read(OBSERVATION_STAGE_PATH)
            )
            if observation_stage != {
                "capture_authorization_sha256": capture.sha256(
                    capture_store.read(capture.AUTHORIZATION_PATH)
                ),
                "schema": OBSERVATION_STAGE_SCHEMA,
                "stage": "OBSERVATION_CHAIN_AUTHORIZED",
            }:
                raise IntegrationError("OBSERVATION_STAGE_INVALID")
            if FINAL_OBSERVATION_PATH in current_paths:
                _validate_observation(
                    evidence_store,
                    FINAL_OBSERVATION_PATH,
                    FINAL_OBSERVATION_SCHEMA,
                    FINAL_STATES,
                )
            if WORKSPACE_OBSERVATION_PATH in current_paths:
                _validate_observation(
                    evidence_store,
                    WORKSPACE_OBSERVATION_PATH,
                    WORKSPACE_OBSERVATION_SCHEMA,
                    WORKSPACE_STATES,
                )
            return Verification(True, "VERIFIED", profile, None)
        if profile not in {"RUNNER_CAPTURE_FINALIZED", "RUNNER_CAPTURE_NEGATIVE"}:
            raise IntegrationError("PROFILE_INVALID")

        sealed_prefix = {
            INTEGRATION_AUTHORITY_PATH,
            INTEGRATION_CONTRACT_PATH,
            OBSERVATION_STAGE_PATH,
            FINAL_OBSERVATION_PATH,
            WORKSPACE_OBSERVATION_PATH,
            SEAL_PATH,
        }
        if profile == "RUNNER_CAPTURE_NEGATIVE" and set(evidence_store.files) == sealed_prefix:
            if _validate_precleanup(
                capture_store, evidence_store, bindings, authority
            ) != profile:
                raise IntegrationError("PROFILE_INVALID")
            return Verification(True, "VERIFIED", profile, None)

        cleanup_unknown_paths = sealed_prefix | {CLEANUP_AUTHORIZATION_PATH}
        if set(evidence_store.files) == cleanup_unknown_paths:
            if _validate_precleanup(
                capture_store,
                capture.CreateOnceStore(
                    {path: evidence_store.files[path] for path in sealed_prefix}
                ),
                bindings,
                authority,
            ) != profile:
                raise IntegrationError("PROFILE_INVALID")
            cleanup_authorization = _parse_canonical(
                evidence_store.read(CLEANUP_AUTHORIZATION_PATH)
            )
            if cleanup_authorization != {
                "attempt_ordinal": 1,
                "profile": profile,
                "retry": False,
                "schema": CLEANUP_AUTHORIZATION_SCHEMA,
                "seal_sha256": capture.sha256(evidence_store.read(SEAL_PATH)),
            }:
                raise IntegrationError("CLEANUP_AUTHORIZATION_INVALID")
            return Verification(True, "CLEANUP_RESULT_UNKNOWN", profile, None)

        capture_verification = capture.verify_public(capture_store, bindings)
        if not capture_verification.verified:
            raise IntegrationError("CAPTURE_PUBLIC_VERIFICATION_FAILED")
        expected_evidence = {
            INTEGRATION_AUTHORITY_PATH,
            INTEGRATION_CONTRACT_PATH,
            OBSERVATION_STAGE_PATH,
            FINAL_OBSERVATION_PATH,
            WORKSPACE_OBSERVATION_PATH,
            SEAL_PATH,
            CLEANUP_AUTHORIZATION_PATH,
            CLEANUP_PATH,
            RECEIPT_PATH,
            FINALIZATION_PATH,
        }
        if set(evidence_store.files) != expected_evidence:
            raise IntegrationError("PROFILE_INVENTORY_INVALID")

        _validate_authority_artifact(evidence_store, authority)
        _validate_contract_artifact(evidence_store, authority)
        _validate_observation_stage(capture_store, evidence_store)
        final_observation = _validate_observation(
            evidence_store, FINAL_OBSERVATION_PATH, FINAL_OBSERVATION_SCHEMA, FINAL_STATES
        )
        workspace_observation = _validate_observation(
            evidence_store,
            WORKSPACE_OBSERVATION_PATH,
            WORKSPACE_OBSERVATION_SCHEMA,
            WORKSPACE_STATES,
        )

        result = _parse_canonical(capture_store.read(capture.CAPTURE_RESULT_PATH))
        expected_profile = derive_profile(
            str(result["status"]),
            str(final_observation["state"]),
            str(workspace_observation["state"]),
        )
        if not cleanup_admitted(
            expected_profile,
            str(result["status"]),
            str(final_observation["state"]),
            str(workspace_observation["state"]),
        ):
            raise IntegrationError("CLEANUP_NOT_ADMITTED")
        seal_payload = evidence_store.read(SEAL_PATH)
        seal = _parse_canonical(seal_payload)
        _exact_fields(
            seal,
            {
                "authority_sha256",
                "capture_artifact_sha256",
                "capture_status",
                "final_observation_sha256",
                "integration_contract_sha256",
                "observation_stage_sha256",
                "profile",
                "schema",
                "workspace_observation_sha256",
            },
        )
        if (
            seal["schema"] != SEAL_SCHEMA
            or seal["profile"] != expected_profile
            or profile != expected_profile
            or seal["capture_status"] != result["status"]
            or seal["authority_sha256"]
            != capture.sha256(evidence_store.read(INTEGRATION_AUTHORITY_PATH))
            or seal["final_observation_sha256"]
            != capture.sha256(evidence_store.read(FINAL_OBSERVATION_PATH))
            or seal["integration_contract_sha256"]
            != capture.sha256(evidence_store.read(INTEGRATION_CONTRACT_PATH))
            or seal["observation_stage_sha256"]
            != capture.sha256(evidence_store.read(OBSERVATION_STAGE_PATH))
            or seal["workspace_observation_sha256"]
            != capture.sha256(evidence_store.read(WORKSPACE_OBSERVATION_PATH))
            or seal["capture_artifact_sha256"]
            != {
                path: capture.sha256(payload)
                for path, payload in sorted(capture_store.files.items())
            }
        ):
            raise IntegrationError("SEAL_LINK_INVALID")

        cleanup_payload = evidence_store.read(CLEANUP_PATH)
        cleanup_authorization = _parse_canonical(
            evidence_store.read(CLEANUP_AUTHORIZATION_PATH)
        )
        if cleanup_authorization != {
            "attempt_ordinal": 1,
            "profile": expected_profile,
            "retry": False,
            "schema": CLEANUP_AUTHORIZATION_SCHEMA,
            "seal_sha256": capture.sha256(seal_payload),
        }:
            raise IntegrationError("CLEANUP_AUTHORIZATION_INVALID")
        cleanup = _parse_canonical(cleanup_payload)
        _exact_fields(cleanup, {"result", "schema", "seal_sha256"})
        if (
            cleanup["schema"] != CLEANUP_SCHEMA
            or cleanup["result"] not in {"PASS", "FAIL"}
            or cleanup["seal_sha256"] != capture.sha256(seal_payload)
        ):
            raise IntegrationError("CLEANUP_LINK_INVALID")
        receipt_payload = evidence_store.read(RECEIPT_PATH)
        receipt = _parse_canonical(receipt_payload)
        _exact_fields(
            receipt,
            {"cleanup_sha256", "disposition", "profile", "schema", "seal_sha256"},
        )
        expected_receipt = (
            "DIAGNOSTIC_RECEIPT"
            if expected_profile == "RUNNER_CAPTURE_FINALIZED" and cleanup["result"] == "PASS"
            else "NEGATIVE_RECEIPT"
        )
        if (
            receipt["schema"] != RECEIPT_SCHEMA
            or receipt["profile"] != expected_profile
            or receipt["disposition"] != expected_receipt
            or receipt["seal_sha256"] != capture.sha256(seal_payload)
            or receipt["cleanup_sha256"] != capture.sha256(cleanup_payload)
        ):
            raise IntegrationError("RECEIPT_LINK_INVALID")
        finalization = _parse_canonical(evidence_store.read(FINALIZATION_PATH))
        _exact_fields(
            finalization, {"disposition", "profile", "receipt_sha256", "schema"}
        )
        if (
            finalization["schema"] != FINALIZATION_SCHEMA
            or finalization["profile"] != expected_profile
            or finalization["receipt_sha256"] != capture.sha256(receipt_payload)
            or finalization["disposition"]
            != (
                "FINALIZED_DIAGNOSTIC"
                if expected_receipt == "DIAGNOSTIC_RECEIPT"
                else "FINALIZED_NEGATIVE"
            )
        ):
            raise IntegrationError("FINALIZATION_LINK_INVALID")
        return Verification(True, "VERIFIED", expected_profile, PUBLIC_CLAIM)
    except (IntegrationError, capture.CaptureError) as exc:
        return Verification(False, getattr(exc, "code", "PUBLIC_ARTIFACT_INVALID"))
    except Exception:
        return Verification(False, "PUBLIC_ARTIFACT_INVALID")


__all__ = [
    "CHECKPOINTS",
    "CLEANUP_AUTHORIZATION_PATH",
    "ContainedStartFailed",
    "FINALIZATION_PATH",
    "FINAL_OBSERVATION_PATH",
    "INTEGRATION_AUTHORITY_PATH",
    "INTEGRATION_CONTRACT_PATH",
    "OBSERVATION_STAGE_PATH",
    "IntegrationError",
    "IntegrationResult",
    "InjectedContainedResult",
    "PUBLIC_CLAIM",
    "RECEIPT_PATH",
    "RunnerIntegrationCoordinator",
    "RUNNER_INTEGRATION_CONTRACT_BYTES",
    "RuntimeAuthority",
    "SEAL_PATH",
    "SyntheticIntegrationCrash",
    "Verification",
    "WORKSPACE_OBSERVATION_PATH",
    "derive_profile",
    "cleanup_admitted",
    "reconstruct_profile",
    "verify_package",
]
