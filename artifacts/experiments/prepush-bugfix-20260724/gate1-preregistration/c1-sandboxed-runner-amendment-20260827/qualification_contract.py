from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


PROBE_SCHEMA = "c1-task-network-denial-probe.v1"
RECEIPT_SCHEMA = "c1-sandboxed-runner-qualification-receipt.v1"
TERMINAL_SCHEMA = "c1-sandboxed-runner-qualification-terminal.v1"
EXPECTED_ATTEMPTS = frozenset(
    {
        "dns",
        "public_ipv4_tcp",
        "public_ipv6_tcp",
        "https",
        "loopback_tcp",
        "private_tcp",
        "link_local_tcp",
    }
)
ALLOWED_TERMINALS = frozenset(
    {
        "SANDBOXED_RUNNER_LEAKAGE_REVIEW_REQUIRED",
        "SANDBOXED_RUNNER_BINDING_MISMATCH",
        "SANDBOXED_RUNNER_MANAGED_POLICY_UNAVAILABLE",
        "SANDBOXED_RUNNER_ELEVATED_SETUP_UNAVAILABLE",
        "SANDBOXED_RUNNER_FALLBACK_DETECTED",
        "SANDBOXED_RUNNER_TASK_NETWORK_REACHABLE",
        "SANDBOXED_RUNNER_HOSTED_TRANSPORT_UNAVAILABLE",
        "SANDBOXED_RUNNER_PARTIAL_OR_TIMEOUT",
        "SANDBOXED_RUNNER_CLEANUP_FAILED",
        "SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED",
    }
)
FORBIDDEN_FIELDS = frozenset(
    {
        "authorization",
        "cookie",
        "credentials",
        "environment",
        "event_stream",
        "firewall_rules",
        "local_path",
        "model_response",
        "prompt",
        "raw_output",
        "resolved_addresses",
        "username",
    }
)


class QualificationError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _walk(value: object) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_FIELDS.intersection(value)
        if forbidden:
            raise QualificationError(
                f"retained document contains forbidden fields: {sorted(forbidden)}"
            )
        for child in value.values():
            _walk(child)
    elif isinstance(value, list):
        for child in value:
            _walk(child)


@dataclass(frozen=True)
class ProbeSummary:
    denied_count: int
    applicable_count: int
    child_denied: bool
    elevated_account_observed: bool


def validate_probe_document(document: Mapping[str, object]) -> ProbeSummary:
    if document.get("schema") != PROBE_SCHEMA or document.get("mode") != "parent":
        raise QualificationError("network probe schema mismatch")
    if document.get("sandbox_account_class") != "offline_sandbox":
        raise QualificationError("elevated offline sandbox account was not observed")
    attempts = document.get("attempts")
    child = document.get("child")
    if not isinstance(attempts, dict) or set(attempts) != EXPECTED_ATTEMPTS:
        raise QualificationError("network probe class set mismatch")
    if not isinstance(child, dict) or child.get("schema") != PROBE_SCHEMA:
        raise QualificationError("child-process probe is missing")
    if child.get("mode") != "child" or child.get("public_ipv4_tcp") != "denied":
        raise QualificationError("child-process network denial was not observed")
    applicable = 0
    denied = 0
    for name, state in attempts.items():
        if state == "not_applicable" and name == "public_ipv6_tcp":
            continue
        applicable += 1
        if state == "denied":
            denied += 1
        else:
            raise QualificationError(f"network class was not denied: {name}")
    if not applicable or denied != applicable:
        raise QualificationError("network denial aggregate mismatch")
    return ProbeSummary(denied, applicable, True, True)


def validate_machine_policy_receipt(
    document: Mapping[str, object],
    *,
    config_sha256: str,
    requirements_sha256: str,
) -> None:
    expected = {
        "schema": "c1-windows-sandbox-machine-policy-receipt.v1",
        "sandbox_implementation": "elevated",
        "managed_requirement_enforced": True,
        "fallback_observed": False,
        "config_sha256": config_sha256,
        "requirements_sha256": requirements_sha256,
        "machine_state_change_owner_authorized": True,
        "rollback_path_reviewed": True,
    }
    if dict(document) != expected:
        raise QualificationError("machine policy receipt does not satisfy the freeze")


def build_terminal(
    *,
    status: str,
    freeze_commit: str,
    attempt_id: str,
    hosted_request_attempted: bool,
    hosted_transport_completed: bool,
    task_command_network_denied: bool,
    sandbox_implementation: str,
    managed_requirement_enforced: bool,
    fallback_observed: bool,
    digests: Mapping[str, str],
    counts: Mapping[str, int],
    cleanup: str,
    diagnostic: str,
) -> bytes:
    if status not in ALLOWED_TERMINALS:
        raise QualificationError("terminal status is not allowlisted")
    if len(diagnostic) > 240:
        raise QualificationError("terminal diagnostic exceeds bound")
    if status == "SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED":
        if not (
            hosted_transport_completed
            and task_command_network_denied
            and sandbox_implementation == "elevated"
            and managed_requirement_enforced
            and not fallback_observed
            and cleanup == "COMPLETE"
        ):
            raise QualificationError("PASS terminal lacks the required conjunction")
    value = {
        "schema": TERMINAL_SCHEMA,
        "status": status,
        "freeze_commit": freeze_commit,
        "qualification_attempt_id": attempt_id,
        "randomization_created": False,
        "hosted_request_attempted": hosted_request_attempted,
        "hosted_transport_completed": hosted_transport_completed,
        "task_command_network_denied": task_command_network_denied,
        "sandbox_implementation": sandbox_implementation,
        "managed_requirement_enforced": managed_requirement_enforced,
        "fallback_observed": fallback_observed,
        "digests": dict(digests),
        "counts": dict(counts),
        "cleanup": cleanup,
        "diagnostic": diagnostic,
    }
    _walk(value)
    return canonical_json(value)


def validate_retained_document(payload: bytes) -> Mapping[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError("retained document is not JSON") from exc
    if not isinstance(value, dict) or canonical_json(value) != payload:
        raise QualificationError("retained document is not canonical JSON")
    _walk(value)
    return value

