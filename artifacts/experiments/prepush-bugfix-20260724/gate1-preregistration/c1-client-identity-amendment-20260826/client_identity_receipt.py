"""Pure calculators for client-side invocation identity receipts.

The module performs no filesystem, Git, network, producer, scorer, or arm I/O.
It deliberately does not represent requested model identity as observed model
identity.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA = "c1-gate1-client-runtime-identity-receipt.v1"
CLAIM_TEMPLATE_SCHEMA = "c1-gate1-client-identity-claim-template.v1"
PHASES = {"PRE_DISPATCH", "POST_SEAL"}
EXPECTED_MODEL = "gpt-5.6-sol"
EXPECTED_MODEL_SOURCE = "frozen_cli_argv"
EVIDENCE_LEVEL = "CLIENT_SIDE_INVOCATION_ONLY"
EXPECTED_CLI_VERSION = "codex-cli 0.148.0-alpha.9"
EXPECTED_CLI_VERSION_STDOUT_BYTES = 26
EXPECTED_CLI_VERSION_STDOUT_SHA256 = (
    "867f4045c33a719c57ed0fc3751a5d9de8dbdb78494a64f43a73ca5c76ef71c5"
)
EXPECTED_CLI_BYTES = 295_151_920
EXPECTED_CLI_SHA256 = (
    "f29f609375f3731d8db507a95124862a84e306982e30ba4300ddce5638bc6946"
)
EXPECTED_RUNNER_OID = "d74dc12984ec8b4d997b6ed4cb39e02a49891bf0"
EXPECTED_RUNNER_BYTES = 44_296
EXPECTED_RUNNER_SHA256 = (
    "55403b05196c44e73c71b041c18888ad66629843c23ab9d5c3f6430690e737be"
)
EXPECTED_PREFLIGHT_ADAPTER_SHA256 = (
    "070c3445d85027115d42b07cd01afb5ef194a034367ebd047df62bb3d9c5c89f"
)
EXPECTED_PYTHON_BYTES = 255_320
EXPECTED_PYTHON_SHA256 = (
    "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
)
EXPECTED_COMMAND_CONTRACT_SHA256 = (
    "4aa350abd4eb3575fd0319d349091ed1180199423fd72719c7b5e22f6e2690e1"
)
WINDOW = timedelta(hours=12)
RECEIPT_MAX_AGE = timedelta(minutes=5)
PAIR_MAX_GAP = timedelta(minutes=15)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OID_RE = re.compile(r"^[0-9a-f]{40}$")
PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")

FORBIDDEN_PROVIDER_OBSERVATION_FIELDS = frozenset(
    {
        "model_observed_id",
        "model_observation_source",
        "model_observation_record_bytes",
        "model_observation_record_sha256",
        "provider_response_model",
        "server_model_id",
    }
)

REQUIRED_LIMITATION = "server-executed model was not independently observed"
REQUIRED_APPLICABILITY = (
    "result applies only to the frozen exact client/harness and 12-hour window"
)
REQUIRED_NON_GENERALIZATION = (
    "result must not be generalized to another deployment or model family"
)


class ClientIdentityError(ValueError):
    """Client identity evidence is missing, misleading, stale, or drifted."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def model_request_argument_sha256() -> str:
    return sha256_hex(canonical_json_bytes(["--model", EXPECTED_MODEL]))


def _require_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ClientIdentityError(f"{name} is invalid")
    return value


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ClientIdentityError("captured_at_utc is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ClientIdentityError("captured_at_utc is invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise ClientIdentityError("captured_at_utc is not UTC")
    return parsed


def invariant_projection(fields: Mapping[str, object]) -> dict[str, object]:
    projection = {
        "model_requested_id": fields.get("model_requested_id"),
        "model_request_source": fields.get("model_request_source"),
        "model_request_argument_sha256": fields.get("model_request_argument_sha256"),
        "identity_evidence_level": fields.get("identity_evidence_level"),
        "server_executed_model_observed": fields.get("server_executed_model_observed"),
        "provider_attestation_available": fields.get("provider_attestation_available"),
        "cli_version": fields.get("cli_version"),
        "cli_executable_sha256": fields.get("cli_executable_sha256"),
        "runner_sha256": fields.get("runner_sha256"),
        "preflight_adapter_sha256": fields.get("preflight_adapter_sha256"),
        "python_executable_sha256": fields.get("python_executable_sha256"),
        "command_contract_sha256": fields.get("command_contract_sha256"),
    }
    expected_literals = {
        "model_requested_id": EXPECTED_MODEL,
        "model_request_source": EXPECTED_MODEL_SOURCE,
        "model_request_argument_sha256": model_request_argument_sha256(),
        "identity_evidence_level": EVIDENCE_LEVEL,
        "server_executed_model_observed": False,
        "provider_attestation_available": False,
        "cli_version": EXPECTED_CLI_VERSION,
        "cli_executable_sha256": EXPECTED_CLI_SHA256,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "preflight_adapter_sha256": EXPECTED_PREFLIGHT_ADAPTER_SHA256,
        "python_executable_sha256": EXPECTED_PYTHON_SHA256,
        "command_contract_sha256": EXPECTED_COMMAND_CONTRACT_SHA256,
    }
    for key, expected in expected_literals.items():
        if projection[key] != expected:
            raise ClientIdentityError(f"{key} differs from the client identity freeze")
    return projection


def client_runtime_projection_sha256(fields: Mapping[str, object]) -> str:
    return sha256_hex(canonical_json_bytes(invariant_projection(fields)))


def build_receipt(fields: Mapping[str, object]) -> dict[str, object]:
    value = dict(fields)
    value["schema"] = SCHEMA
    value["client_runtime_projection_sha256"] = client_runtime_projection_sha256(value)
    return validate_receipt(value)


def validate_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    if FORBIDDEN_PROVIDER_OBSERVATION_FIELDS.intersection(receipt):
        raise ClientIdentityError("provider-observation fields are forbidden")
    required = {
        "schema",
        "phase",
        "comparison_id",
        "anonymous_outcome_id",
        "captured_at_utc",
        "batch_admission_sha256",
        "model_requested_id",
        "model_request_source",
        "model_request_argument_sha256",
        "identity_evidence_level",
        "server_executed_model_observed",
        "provider_attestation_available",
        "cli_version",
        "cli_version_stdout_bytes",
        "cli_version_stdout_sha256",
        "cli_executable_bytes",
        "cli_executable_sha256",
        "runner_git_blob_oid",
        "runner_bytes",
        "runner_sha256",
        "preflight_adapter_sha256",
        "python_executable_sha256",
        "command_contract_sha256",
        "client_runtime_projection_sha256",
        "previous_event_sha256",
    }
    if set(receipt) != required or receipt.get("schema") != SCHEMA:
        raise ClientIdentityError("client identity receipt shape is invalid")
    if receipt.get("phase") not in PHASES:
        raise ClientIdentityError("receipt phase is invalid")
    for key in ("comparison_id", "anonymous_outcome_id"):
        value = receipt.get(key)
        if not isinstance(value, str) or PUBLIC_ID_RE.fullmatch(value) is None:
            raise ClientIdentityError(f"{key} is invalid")
    _parse_utc(receipt.get("captured_at_utc"))
    if receipt.get("cli_executable_bytes") != EXPECTED_CLI_BYTES:
        raise ClientIdentityError("CLI byte count differs from freeze")
    if receipt.get("runner_git_blob_oid") != EXPECTED_RUNNER_OID:
        raise ClientIdentityError("runner Git blob differs from freeze")
    if receipt.get("runner_bytes") != EXPECTED_RUNNER_BYTES:
        raise ClientIdentityError("runner byte count differs from freeze")
    if receipt.get("cli_version_stdout_bytes") != EXPECTED_CLI_VERSION_STDOUT_BYTES:
        raise ClientIdentityError("CLI version byte count differs from freeze")
    if receipt.get("cli_version_stdout_sha256") != EXPECTED_CLI_VERSION_STDOUT_SHA256:
        raise ClientIdentityError("CLI version output differs from freeze")
    for key in (
        "batch_admission_sha256",
        "cli_version_stdout_sha256",
        "cli_executable_sha256",
        "runner_sha256",
        "preflight_adapter_sha256",
        "python_executable_sha256",
        "command_contract_sha256",
        "client_runtime_projection_sha256",
        "previous_event_sha256",
    ):
        _require_sha256(receipt.get(key), key)
    expected = client_runtime_projection_sha256(receipt)
    if receipt["client_runtime_projection_sha256"] != expected:
        raise ClientIdentityError("client runtime projection differs")
    return dict(receipt)


def validate_receipt_pair(
    pre_dispatch: Mapping[str, object],
    post_seal: Mapping[str, object],
    *,
    batch_projection_sha256: str,
    admission_at_utc: datetime,
    dispatch_at_utc: datetime,
    outcome_sealed_at_utc: datetime,
) -> None:
    pre = validate_receipt(pre_dispatch)
    post = validate_receipt(post_seal)
    if pre["phase"] != "PRE_DISPATCH" or post["phase"] != "POST_SEAL":
        raise ClientIdentityError("receipt pair phases are invalid")
    if pre["comparison_id"] != post["comparison_id"] or pre["anonymous_outcome_id"] != post["anonymous_outcome_id"]:
        raise ClientIdentityError("receipt pair identifiers differ")
    _require_sha256(batch_projection_sha256, "batch_projection_sha256")
    if pre["client_runtime_projection_sha256"] != batch_projection_sha256 or post["client_runtime_projection_sha256"] != batch_projection_sha256:
        raise ClientIdentityError("receipt pair differs from batch admission")

    pre_time = _parse_utc(pre["captured_at_utc"])
    post_time = _parse_utc(post["captured_at_utc"])
    if any(value.tzinfo != timezone.utc for value in (admission_at_utc, dispatch_at_utc, outcome_sealed_at_utc)):
        raise ClientIdentityError("validation timestamps must be UTC")
    expiry = admission_at_utc + WINDOW
    if not admission_at_utc <= pre_time <= dispatch_at_utc <= expiry:
        raise ClientIdentityError("pre-dispatch receipt is outside the batch window")
    if dispatch_at_utc - pre_time > RECEIPT_MAX_AGE:
        raise ClientIdentityError("pre-dispatch receipt is stale")
    if not outcome_sealed_at_utc <= post_time <= expiry:
        raise ClientIdentityError("post-seal receipt is outside the batch window")
    if post_time - outcome_sealed_at_utc > RECEIPT_MAX_AGE:
        raise ClientIdentityError("post-seal receipt is late")
    if outcome_sealed_at_utc < dispatch_at_utc or post_time < pre_time:
        raise ClientIdentityError("receipt event chronology is invalid")


def validate_paired_execution_gap(
    *, first_outcome_sealed_at_utc: datetime, second_dispatch_at_utc: datetime
) -> None:
    if first_outcome_sealed_at_utc.tzinfo != timezone.utc or second_dispatch_at_utc.tzinfo != timezone.utc:
        raise ClientIdentityError("paired execution timestamps must be UTC")
    gap = second_dispatch_at_utc - first_outcome_sealed_at_utc
    if gap < timedelta(0) or gap > PAIR_MAX_GAP:
        raise ClientIdentityError("paired execution gap exceeds the freeze")


def validate_claim_template(template: Mapping[str, object]) -> dict[str, object]:
    required = {
        "schema",
        "decision_purpose",
        "identity_evidence_level",
        "server_executed_model_observed",
        "provider_attestation_available",
        "required_statements",
        "prohibited_generalizations",
    }
    if set(template) != required or template.get("schema") != CLAIM_TEMPLATE_SCHEMA:
        raise ClientIdentityError("claim template shape is invalid")
    if template.get("decision_purpose") != "internal_skill_funding_only":
        raise ClientIdentityError("claim purpose exceeds the decision")
    if template.get("identity_evidence_level") != EVIDENCE_LEVEL:
        raise ClientIdentityError("claim identity level differs")
    if template.get("server_executed_model_observed") is not False or template.get("provider_attestation_available") is not False:
        raise ClientIdentityError("claim template implies provider observation")
    required_statements = set(template.get("required_statements", ()))
    if required_statements != {
        REQUIRED_LIMITATION,
        REQUIRED_APPLICABILITY,
        REQUIRED_NON_GENERALIZATION,
    }:
        raise ClientIdentityError("claim template limitations differ")
    prohibited = set(template.get("prohibited_generalizations", ()))
    expected_prohibited = {
        "server_executed_model_was_proven",
        "immutable_hosted_deployment_was_proven",
        "applies_to_other_deployments",
        "applies_to_model_family",
        "supports_external_model_effectiveness_claim",
    }
    if prohibited != expected_prohibited:
        raise ClientIdentityError("claim generalization prohibitions differ")
    return dict(template)
