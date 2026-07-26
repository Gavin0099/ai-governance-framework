#!/usr/bin/env python3
"""Build and verify the scorer-handoff v3 candidate.

The builder accepts only a live-container-verified scorer-packet schema v2.
It maps operator-owned evidence into the frozen four-section scoring shape:

* FIX_DIFF         <- scorer packet final-diff.patch
* TEST_LOG         <- operator-captured post-fix test log
* VALIDATOR_OUTPUT <- operator-captured uniform post-hoc validator output
* COMPLETION_CLAIM <- scorer packet result.json

The unredacted four-section value is held in memory.  Only the redacted packet,
anonymized receipt and a manifest written last are published.  Any failure
removes every partial output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable


HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if EXPERIMENT_ROOT not in sys.path:
    sys.path.insert(0, EXPERIMENT_ROOT)

import redaction_runner as R  # noqa: E402
import scorer_packet_v2 as P  # noqa: E402


CONTRACT_ID = "gate2-scorer-handoff.v3"
PACKET_SCHEMA = "gate2-redacted-packet.v2"
HANDOFF_SCHEMA = "gate2-scorer-handoff-set.v2"
HANDOFF_FILENAME = "scorer-handoff-v3.json"
CANDIDATE_MANIFEST_SCHEMA = "gate2-scorer-handoff-v3-candidate-set.v1"
REDACTION_RUNNER_RELATIVE = (
    "artifacts/experiments/prepush-bugfix-20260724/redaction_runner.py"
)
REDACTION_RUNNER_PATH = os.path.join(EXPERIMENT_ROOT, "redaction_runner.py")
CANDIDATE_MANIFEST_RELATIVE = (
    "artifacts/experiments/prepush-bugfix-20260724/candidate/"
    "scorer-handoff-v3-candidate-manifest.json"
)
RECEIPT_RELATIVE = (
    "artifacts/evidence/test-results/"
    "receipt-gate2-scorer-handoff-v3-candidate-20260726.json"
)
CANONICAL_FILES = {
    "artifacts/experiments/prepush-bugfix-20260724/scorer-handoff-contract.json":
        "e8945c4b7eee256c96e6c7f21beef02f885b9f6c7caf6b2b65197088bcd5226a",
    "docs/governance/gate1-prereg-prepush-amendment-v2-20260724.md":
        "eb1a7747e51bd01566ee04d17123cab5262452961f53631d8769fe392f8a9c64",
    "docs/governance/gate1-prereg-prepush-amendment-v3-20260725.md":
        "376fd1f4fc9a1915e2240b6ba4d97d1163158f711e60948c7e20a175d588bdd3",
}
CANDIDATE_FILE_SET = {
    ".gitattributes",
    "docs/governance/gate1-prereg-prepush-amendment-v4-20260726.md",
    "artifacts/experiments/prepush-bugfix-20260724/candidate/scorer-handoff-contract-v3.json",
    REDACTION_RUNNER_RELATIVE,
    "artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/scorer_packet_v2.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/scorer_handoff_v3.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/test_scorer_packet_v2.py",
    "artifacts/experiments/prepush-bugfix-20260724/gate2-runtime/test_scorer_handoff_v3.py",
}
BYTE_PRESERVATION_PATHS = (
    CANDIDATE_FILE_SET
    | set(CANONICAL_FILES)
    | {CANDIDATE_MANIFEST_RELATIVE, RECEIPT_RELATIVE}
)
OUTPUT_FILES = {
    "packet": "redacted-packet.json",
    "receipt": "redacted-receipt.json",
}
SECTION_SOURCES = {
    "FIX_DIFF": "scorer_packet.artifacts.diff",
    "TEST_LOG": "attachment.test_log",
    "VALIDATOR_OUTPUT": "attachment.validator_output",
    "COMPLETION_CLAIM": "scorer_packet.artifacts.result",
}
BLINDING_INPUT_POLICY = {
    "cli_argument": "--blinding-compromised-reason",
    "absent": {
        "blinding_compromised": None,
        "blinding_compromised_reason": None,
    },
    "present": {
        "blinding_compromised": True,
        "blinding_compromised_reason": "exact non-blank argument string",
    },
    "verification": (
        "The verifier must receive the same explicit reason used by the builder; "
        "absence, omission or any byte change fails deterministic reproduction."
    ),
}


class HandoffError(Exception):
    pass


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"{label} must contain a JSON object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("contract") != CONTRACT_ID:
        raise HandoffError(f"contract id must be {CONTRACT_ID}")
    if contract.get("frozen") is not False:
        raise HandoffError(
            "v3 candidate must remain frozen=false until a separate owner re-sign"
        )
    artifact = contract.get("producer_output_artifact")
    if not isinstance(artifact, dict):
        raise HandoffError("producer_output_artifact is missing")
    if artifact.get("section_markers") != R.MARKERS:
        raise HandoffError("contract section markers differ from canonical order")
    source = contract.get("source_packet")
    if not isinstance(source, dict) or source.get("schema_version") != P.SCHEMA_VERSION:
        raise HandoffError("contract must require scorer-packet schema v2")
    if source.get("section_mapping") != SECTION_SOURCES:
        raise HandoffError("contract section mapping differs from candidate mapping")
    redaction = contract.get("redaction")
    if not isinstance(redaction, dict) or not isinstance(
        redaction.get("literal_map"), list
    ):
        raise HandoffError("contract redaction literal_map is missing")
    dependency = contract.get("canonical_builder", {}).get(
        "redaction_dependency"
    )
    if (
        not isinstance(dependency, dict)
        or dependency.get("path") != REDACTION_RUNNER_RELATIVE
        or not isinstance(dependency.get("sha256"), str)
        or len(dependency["sha256"]) != 64
    ):
        raise HandoffError("contract redaction dependency is missing or invalid")
    if contract.get("blinding_compromised_input") != BLINDING_INPUT_POLICY:
        raise HandoffError(
            "contract blinding-compromised input policy differs from runtime"
        )


def _read_regular_file(path: str, label: str) -> bytes:
    absolute = os.path.abspath(path)
    if os.path.islink(absolute) or not os.path.isfile(absolute):
        raise HandoffError(f"{label} must be a regular non-symlink file")
    try:
        with open(absolute, "rb") as handle:
            payload = handle.read()
    except OSError as exc:
        raise HandoffError(f"{label} is unreadable: {exc}") from exc
    if not payload:
        raise HandoffError(f"{label} must not be empty")
    return payload


def _canonical_section(payload: bytes, label: str) -> bytes:
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise HandoffError(f"{label} must be UTF-8") from exc
    if "\r" in text:
        raise HandoffError(f"{label} contains CR; canonical handoff requires LF")
    if any(line in R.MARKERS for line in text.split("\n")):
        raise HandoffError(f"{label} contains a reserved standalone section marker")
    return payload if payload.endswith(b"\n") else payload + b"\n"


def build_raw_output(
    *,
    diff_bytes: bytes,
    test_log_bytes: bytes,
    validator_output_bytes: bytes,
    result_bytes: bytes,
) -> bytes:
    section_payloads = {
        "FIX_DIFF": _canonical_section(diff_bytes, "final diff"),
        "TEST_LOG": _canonical_section(test_log_bytes, "test log"),
        "VALIDATOR_OUTPUT": _canonical_section(
            validator_output_bytes, "validator output"
        ),
        "COMPLETION_CLAIM": _canonical_section(result_bytes, "result.json"),
    }
    raw = b""
    for marker in R.MARKERS:
        name = marker.strip("= ").strip()
        raw += marker.encode("utf-8") + b"\n" + section_payloads[name]
    try:
        R.parse_canonical(raw)
    except R.FormatError as exc:
        raise HandoffError(f"assembled four-section input is invalid: {exc}") from exc
    return raw


def _redacted_text(sections: dict[str, str], rules: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
    redacted_claim, match_counts = R.redact(sections["COMPLETION_CLAIM"], rules)
    redacted = dict(sections)
    redacted["COMPLETION_CLAIM"] = redacted_claim
    text = ""
    for marker in R.MARKERS:
        name = marker.strip("= ").strip()
        text += marker + "\n" + redacted[name]
        if not text.endswith("\n"):
            text += "\n"
    return text, match_counts


def _blinding_fields(reason: str | None) -> tuple[bool | None, str | None]:
    if reason is None:
        return None, None
    if not isinstance(reason, str) or not reason.strip():
        raise HandoffError(
            "blinding-compromised reason must be a non-blank string when supplied"
        )
    return True, reason


def _load_pinned_source_packet(
    scorer_packet_path: str,
    *,
    expected_scorer_packet_sha256: str,
    expected_run_id: str,
    expected_baseline_commit: str,
    expected_output_commit: str,
    expected_container_id: str,
) -> tuple[bytes, dict[str, Any], dict[str, bytes]]:
    """Load and locally validate the exact scorer-packet source set.

    Live container binding remains a build-time requirement.  This verifier
    path proves that the published handoff reproduces from the exact packet
    bytes that were pinned after that live check.
    """
    packet_bytes = _read_regular_file(
        scorer_packet_path, "source scorer packet manifest"
    )
    if P.sha256(packet_bytes) != expected_scorer_packet_sha256:
        raise HandoffError("source scorer packet manifest digest mismatch")
    packet = _load_json_object(
        packet_bytes, "source scorer packet manifest"
    )
    container = packet.get("container")
    if (
        packet.get("schema_version") != P.SCHEMA_VERSION
        or packet.get("run_id") != expected_run_id
        or packet.get("baseline_commit") != expected_baseline_commit
        or packet.get("output_commit") != expected_output_commit
        or not isinstance(container, dict)
        or container.get("id") != expected_container_id
        or packet.get("receipt_container_path")
        != P.DEFAULT_RECEIPT_CONTAINER_PATH
    ):
        raise HandoffError("source scorer packet identity or schema mismatch")

    payloads, artifact_checks, artifact_errors = P._read_packet_artifacts(
        scorer_packet_path, packet
    )
    if not all(artifact_checks.values()):
        detail = ", ".join(
            name for name, passed in artifact_checks.items() if not passed
        )
        if artifact_errors:
            detail += ": " + "; ".join(artifact_errors)
        raise HandoffError("source scorer packet artifacts invalid: " + detail)
    if payloads.get("status") != b"":
        raise HandoffError("source scorer packet records a dirty worktree")
    result = _load_json_object(payloads["result"], "source result.json")
    if not result:
        raise HandoffError("source result.json must not be empty")
    receipt = _load_json_object(
        payloads["receipt"], "source producer receipt"
    )
    if receipt.get("linked_commit") != expected_output_commit:
        raise HandoffError(
            "source producer receipt does not link the output commit"
        )
    try:
        tracked_paths = P._parse_paths(payloads["tracked_paths"])
    except (KeyError, ValueError) as exc:
        raise HandoffError(
            "source scorer packet tracked inventory is invalid"
        ) from exc
    workspace = packet.get("workspace")
    semantic_checks = {
        "tracked_inventory_matches_diff": bool(tracked_paths)
        and all(
            f"diff --git a/{path} b/{path}".encode("utf-8")
            in payloads["diff"]
            for path in tracked_paths
        ),
        "manifest_inventory_matches_captured_files": (
            isinstance(workspace, dict)
            and workspace.get("clean") is True
            and workspace.get("tracked_changed_files") == tracked_paths
        ),
        "core_scorer_inputs_are_exact": (
            packet.get("scorer_input_core") == ["result", "diff"]
            and packet.get("handoff_attachments_required")
            == ["test_log", "validator_output"]
        ),
    }
    failed_semantics = [
        name for name, passed in semantic_checks.items() if not passed
    ]
    if failed_semantics:
        raise HandoffError(
            "source scorer packet semantic checks failed: "
            + ", ".join(failed_semantics)
        )
    return packet_bytes, packet, payloads


def _assemble_handoff(
    *,
    contract_bytes: bytes,
    contract: dict[str, Any],
    packet_manifest_bytes: bytes,
    packet_payloads: dict[str, bytes],
    test_log_bytes: bytes,
    validator_output_bytes: bytes,
    source_identity: dict[str, str],
    blinding_compromised_reason: str | None = None,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Deterministically build the complete published set from pinned sources."""
    redaction_runner_bytes = _read_regular_file(
        REDACTION_RUNNER_PATH, "redaction runner dependency"
    )
    dependency = contract["canonical_builder"]["redaction_dependency"]
    if dependency["sha256"] != P.sha256(redaction_runner_bytes):
        raise HandoffError("redaction runner dependency digest mismatch")

    raw_output = build_raw_output(
        diff_bytes=packet_payloads["diff"],
        test_log_bytes=test_log_bytes,
        validator_output_bytes=validator_output_bytes,
        result_bytes=packet_payloads["result"],
    )
    sections = R.parse_canonical(raw_output)
    rules = contract["redaction"]["literal_map"]
    redacted_text, match_counts = _redacted_text(sections, rules)
    raw_sha = P.sha256(raw_output)
    blinding_compromised, blinding_reason = _blinding_fields(
        blinding_compromised_reason
    )

    source_artifacts = {
        "scorer_packet": {
            "sha256": P.sha256(packet_manifest_bytes),
            "bytes": len(packet_manifest_bytes),
        },
        "result": {
            "sha256": P.sha256(packet_payloads["result"]),
            "bytes": len(packet_payloads["result"]),
        },
        "diff": {
            "sha256": P.sha256(packet_payloads["diff"]),
            "bytes": len(packet_payloads["diff"]),
        },
        "receipt": {
            "sha256": P.sha256(packet_payloads["receipt"]),
            "bytes": len(packet_payloads["receipt"]),
        },
        "test_log": {
            "sha256": P.sha256(test_log_bytes),
            "bytes": len(test_log_bytes),
        },
        "validator_output": {
            "sha256": P.sha256(validator_output_bytes),
            "bytes": len(validator_output_bytes),
        },
        "redaction_runner": {
            "sha256": P.sha256(redaction_runner_bytes),
            "bytes": len(redaction_runner_bytes),
        },
    }
    redacted_packet = {
        "schema": PACKET_SCHEMA,
        "anon_id": "OUT-" + raw_sha[:12],
        "contract_sha256": P.sha256(contract_bytes),
        "raw_output_sha256": raw_sha,
        "redacted_output_sha256": P.sha256(redacted_text.encode("utf-8")),
        "per_rule_match_count": match_counts,
        "total_redactions": sum(match_counts.values()),
        "redacted_output": redacted_text,
        "source_attestation": {
            "identity": source_identity,
            "artifacts": source_artifacts,
            "section_mapping": SECTION_SOURCES,
            "source_packet_verification": (
                "PASS: builder live-verified packet; published bytes reproduce "
                "from pinned sources"
            ),
        },
        "blinding_compromised": blinding_compromised,
        "blinding_compromised_reason": blinding_reason,
        "channel_effect": contract["common_mode_channel_effect"],
    }

    receipt = _load_json_object(
        packet_payloads["receipt"], "source producer receipt"
    )
    drop_fields = contract["redaction"].get("receipt_field_drop", ["arm"])
    anon_receipt = R.anonymize_receipt(receipt, rules, drop_fields)
    for field in drop_fields:
        if field in anon_receipt:
            raise HandoffError(
                f"receipt identity field still present: {field}"
            )
    anon_receipt["anon_id"] = redacted_packet["anon_id"]
    anon_receipt["source_output_commit"] = source_identity["output_commit"]

    packet_bytes = P._json_bytes(redacted_packet)
    receipt_bytes = P._json_bytes(anon_receipt)
    outputs = {
        OUTPUT_FILES["packet"]: packet_bytes,
        OUTPUT_FILES["receipt"]: receipt_bytes,
    }
    manifest = {
        "handoff": HANDOFF_SCHEMA,
        "candidate_authorization": "pending_owner_resign",
        "anon_id": redacted_packet["anon_id"],
        "contract_sha256": P.sha256(contract_bytes),
        "packet_path": OUTPUT_FILES["packet"],
        "receipt_path": OUTPUT_FILES["receipt"],
        "packet_sha256": P.sha256(packet_bytes),
        "receipt_sha256": P.sha256(receipt_bytes),
        "source_identity": source_identity,
        "source_artifacts": source_artifacts,
        "section_mapping": SECTION_SOURCES,
        "claim_boundary": (
            "This candidate proves byte and identity linkage from a live-verified "
            "container packet into the four-section blind input. It is not "
            "Gate-2-authorized until separately owner-signed and promoted."
        ),
    }
    return outputs, manifest


def build_handoff(
    *,
    contract_path: str,
    scorer_packet_path: str,
    expected_run_id: str,
    expected_baseline_commit: str,
    expected_output_commit: str,
    expected_container_id: str,
    observed_state: dict[str, Any],
    test_log_path: str,
    validator_output_path: str,
    blinding_compromised_reason: str | None = None,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    contract_bytes = _read_regular_file(contract_path, "candidate contract")
    contract = _load_json_object(contract_bytes, "candidate contract")
    validate_contract(contract)

    verification = P.verify_packet(
        scorer_packet_path,
        expected_run_id=expected_run_id,
        expected_baseline_commit=expected_baseline_commit,
        expected_output_commit=expected_output_commit,
        expected_container_id=expected_container_id,
        observed_state=observed_state,
    )
    if verification.get("status") != "PASS":
        failed = [
            name
            for name, passed in verification.get("checks", {}).items()
            if not passed
        ]
        raise HandoffError(
            "source scorer packet failed live verification: " + ", ".join(failed)
        )

    packet_manifest_bytes = _read_regular_file(
        scorer_packet_path, "source scorer packet manifest"
    )
    if P.sha256(packet_manifest_bytes) != verification.get("packet_sha256"):
        raise HandoffError("source scorer packet manifest changed after verification")
    packet_manifest = _load_json_object(
        packet_manifest_bytes, "source scorer packet manifest"
    )
    packet_payloads, artifact_checks, _ = P._read_packet_artifacts(
        scorer_packet_path, packet_manifest
    )
    if not all(artifact_checks.values()):
        raise HandoffError("source scorer packet artifacts changed after verification")

    test_log_bytes = _read_regular_file(test_log_path, "test log")
    validator_output_bytes = _read_regular_file(
        validator_output_path, "validator output"
    )
    source_identity = {
        "run_id": expected_run_id,
        "baseline_commit": expected_baseline_commit,
        "output_commit": expected_output_commit,
        "container_id": expected_container_id,
    }
    return _assemble_handoff(
        contract_bytes=contract_bytes,
        contract=contract,
        packet_manifest_bytes=packet_manifest_bytes,
        packet_payloads=packet_payloads,
        test_log_bytes=test_log_bytes,
        validator_output_bytes=validator_output_bytes,
        source_identity=source_identity,
        blinding_compromised_reason=blinding_compromised_reason,
    )


def publish_handoff(
    out_dir: str,
    outputs: dict[str, bytes],
    manifest: dict[str, Any],
    *,
    writer: Callable[[str, bytes], None] = P.atomic_write_bytes,
) -> str:
    destination = os.path.abspath(out_dir)
    manifest_path = os.path.join(destination, HANDOFF_FILENAME)
    targets = [os.path.join(destination, name) for name in outputs] + [manifest_path]
    existing = [path for path in targets if os.path.lexists(path)]
    if existing:
        raise FileExistsError(
            "scorer handoff v3 is create-once; existing target(s): "
            + ", ".join(existing)
        )
    os.makedirs(destination, exist_ok=True)
    published: list[str] = []
    try:
        for name, payload in outputs.items():
            path = os.path.join(destination, name)
            writer(path, payload)
            published.append(path)
        writer(manifest_path, P._json_bytes(manifest))
        published.append(manifest_path)
    except BaseException:
        for path in reversed(published):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        raise
    return manifest_path


def verify_handoff(
    manifest_path: str,
    *,
    contract_path: str,
    scorer_packet_path: str,
    test_log_path: str,
    validator_output_path: str,
    expected_run_id: str,
    expected_baseline_commit: str,
    expected_output_commit: str,
    expected_container_id: str,
    expected_scorer_packet_sha256: str,
    blinding_compromised_reason: str | None = None,
) -> dict[str, Any]:
    checks = {
        "manifest_is_valid_json_object": False,
        "handoff_schema_matches": False,
        "candidate_is_not_misrepresented_as_authorized": False,
        "contract_digest_matches": False,
        "source_identity_matches": False,
        "source_packet_digest_matches": False,
        "source_rebuild_inputs_are_valid": False,
        "output_paths_are_fixed_and_confined": False,
        "all_outputs_exist": False,
        "output_digests_match": False,
        "packet_schema_matches": False,
        "packet_contract_digest_matches": False,
        "anon_ids_match": False,
        "receipt_output_commit_matches": False,
        "redacted_output_digest_matches": False,
        "four_sections_are_complete_and_ordered": False,
        "source_artifact_set_is_exact": False,
        "source_mapping_is_exact": False,
        "source_artifacts_match_rebuild": False,
        "published_packet_matches_source_rebuild": False,
        "published_receipt_matches_source_rebuild": False,
        "published_manifest_matches_source_rebuild": False,
        "redaction_metadata_matches_source_rebuild": False,
        "blinding_and_channel_fields_match_contract": False,
    }
    errors: list[str] = []
    try:
        manifest_bytes = _read_regular_file(manifest_path, "handoff manifest")
        manifest = _load_json_object(manifest_bytes, "handoff manifest")
        checks["manifest_is_valid_json_object"] = True
    except HandoffError as exc:
        errors.append(str(exc))
        return {"status": "FAIL", "checks": checks, "errors": errors}

    checks["handoff_schema_matches"] = manifest.get("handoff") == HANDOFF_SCHEMA
    checks["candidate_is_not_misrepresented_as_authorized"] = (
        manifest.get("candidate_authorization") == "pending_owner_resign"
    )
    contract_bytes = b""
    contract: dict[str, Any] = {}
    try:
        contract_bytes = _read_regular_file(contract_path, "candidate contract")
        contract = _load_json_object(contract_bytes, "candidate contract")
        validate_contract(contract)
        checks["contract_digest_matches"] = (
            manifest.get("contract_sha256") == P.sha256(contract_bytes)
        )
    except HandoffError as exc:
        errors.append(str(exc))

    expected_identity = {
        "run_id": expected_run_id,
        "baseline_commit": expected_baseline_commit,
        "output_commit": expected_output_commit,
        "container_id": expected_container_id,
    }
    checks["source_identity_matches"] = (
        manifest.get("source_identity") == expected_identity
    )
    source_artifacts = manifest.get("source_artifacts")
    checks["source_packet_digest_matches"] = (
        isinstance(source_artifacts, dict)
        and isinstance(source_artifacts.get("scorer_packet"), dict)
        and source_artifacts["scorer_packet"].get("sha256")
        == expected_scorer_packet_sha256
    )
    rebuilt_outputs: dict[str, bytes] = {}
    rebuilt_manifest: dict[str, Any] = {}
    if contract:
        try:
            (
                source_packet_bytes,
                _source_packet,
                source_packet_payloads,
            ) = _load_pinned_source_packet(
                scorer_packet_path,
                expected_scorer_packet_sha256=expected_scorer_packet_sha256,
                expected_run_id=expected_run_id,
                expected_baseline_commit=expected_baseline_commit,
                expected_output_commit=expected_output_commit,
                expected_container_id=expected_container_id,
            )
            test_log_bytes = _read_regular_file(test_log_path, "test log")
            validator_output_bytes = _read_regular_file(
                validator_output_path, "validator output"
            )
            rebuilt_outputs, rebuilt_manifest = _assemble_handoff(
                contract_bytes=contract_bytes,
                contract=contract,
                packet_manifest_bytes=source_packet_bytes,
                packet_payloads=source_packet_payloads,
                test_log_bytes=test_log_bytes,
                validator_output_bytes=validator_output_bytes,
                source_identity=expected_identity,
                blinding_compromised_reason=blinding_compromised_reason,
            )
            checks["source_rebuild_inputs_are_valid"] = True
        except (HandoffError, KeyError, R.FormatError) as exc:
            errors.append(f"source reconstruction failed: {exc}")

    base = os.path.dirname(os.path.abspath(manifest_path))
    paths_ok = True
    payloads: dict[str, bytes] = {}
    for key, expected_name in OUTPUT_FILES.items():
        name = manifest.get(f"{key}_path")
        if name != expected_name:
            paths_ok = False
            continue
        path = os.path.abspath(os.path.join(base, name))
        if (
            os.path.dirname(path) != base
            or os.path.islink(path)
            or not os.path.isfile(path)
        ):
            paths_ok = False
            continue
        try:
            with open(path, "rb") as handle:
                payloads[key] = handle.read()
        except OSError as exc:
            errors.append(f"{key} unreadable: {exc}")
    checks["output_paths_are_fixed_and_confined"] = paths_ok
    checks["all_outputs_exist"] = len(payloads) == len(OUTPUT_FILES)
    checks["output_digests_match"] = all(
        manifest.get(f"{key}_sha256") == P.sha256(payloads.get(key, b""))
        for key in OUTPUT_FILES
    )

    try:
        packet = _load_json_object(payloads["packet"], "redacted packet")
        receipt = _load_json_object(payloads["receipt"], "redacted receipt")
        checks["packet_schema_matches"] = packet.get("schema") == PACKET_SCHEMA
        checks["packet_contract_digest_matches"] = (
            packet.get("contract_sha256") == manifest.get("contract_sha256")
        )
        checks["anon_ids_match"] = (
            packet.get("anon_id")
            == receipt.get("anon_id")
            == manifest.get("anon_id")
            == "OUT-" + packet.get("raw_output_sha256", "")[:12]
        )
        checks["receipt_output_commit_matches"] = (
            receipt.get("source_output_commit") == expected_output_commit
        )
        redacted_output = packet.get("redacted_output")
        checks["redacted_output_digest_matches"] = (
            isinstance(redacted_output, str)
            and P.sha256(redacted_output.encode("utf-8"))
            == packet.get("redacted_output_sha256")
        )
        if isinstance(redacted_output, str):
            sections = R.parse_canonical(redacted_output.encode("utf-8"))
            checks["four_sections_are_complete_and_ordered"] = (
                set(sections)
                == {
                    "FIX_DIFF",
                    "TEST_LOG",
                    "VALIDATOR_OUTPUT",
                    "COMPLETION_CLAIM",
                }
                and all(sections[name] for name in sections)
            )
        checks["published_packet_matches_source_rebuild"] = (
            payloads.get("packet")
            == rebuilt_outputs.get(OUTPUT_FILES["packet"])
        )
        checks["published_receipt_matches_source_rebuild"] = (
            payloads.get("receipt")
            == rebuilt_outputs.get(OUTPUT_FILES["receipt"])
        )
        checks["published_manifest_matches_source_rebuild"] = (
            manifest_bytes == P._json_bytes(rebuilt_manifest)
        )
        rebuilt_packet = _load_json_object(
            rebuilt_outputs.get(OUTPUT_FILES["packet"], b""),
            "rebuilt redacted packet",
        )
        checks["redaction_metadata_matches_source_rebuild"] = (
            packet.get("raw_output_sha256")
            == rebuilt_packet.get("raw_output_sha256")
            and packet.get("redacted_output_sha256")
            == rebuilt_packet.get("redacted_output_sha256")
            and packet.get("per_rule_match_count")
            == rebuilt_packet.get("per_rule_match_count")
            and packet.get("total_redactions")
            == rebuilt_packet.get("total_redactions")
        )
        checks["blinding_and_channel_fields_match_contract"] = (
            packet.get("blinding_compromised")
            == rebuilt_packet.get("blinding_compromised")
            and packet.get("blinding_compromised_reason")
            == rebuilt_packet.get("blinding_compromised_reason")
            and packet.get("channel_effect")
            == contract.get("common_mode_channel_effect")
            == rebuilt_packet.get("channel_effect")
        )
        attestation = packet.get("source_attestation")
        checks["source_artifact_set_is_exact"] = (
            isinstance(source_artifacts, dict)
            and set(source_artifacts)
            == {
                "scorer_packet",
                "result",
                "diff",
                "receipt",
                "test_log",
                "validator_output",
                "redaction_runner",
            }
            and all(
                isinstance(metadata, dict)
                and isinstance(metadata.get("bytes"), int)
                and metadata["bytes"] >= 0
                and isinstance(metadata.get("sha256"), str)
                and len(metadata["sha256"]) == 64
                for metadata in source_artifacts.values()
            )
        )
        checks["source_mapping_is_exact"] = (
            manifest.get("section_mapping") == SECTION_SOURCES
            and isinstance(attestation, dict)
            and attestation.get("section_mapping") == SECTION_SOURCES
            and attestation.get("identity") == expected_identity
            and attestation.get("artifacts") == source_artifacts
            and attestation.get("source_packet_verification")
            == (
                "PASS: builder live-verified packet; published bytes reproduce "
                "from pinned sources"
            )
        )
        checks["source_artifacts_match_rebuild"] = (
            source_artifacts == rebuilt_manifest.get("source_artifacts")
        )
    except (KeyError, HandoffError, R.FormatError) as exc:
        errors.append(f"handoff payload validation failed: {exc}")

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "errors": errors,
        "claim_boundary": (
            "PASS proves the published candidate handoff is complete and "
            "digest-consistent. It does not authorize Gate 2 or authenticate a "
            "coordinated direct writer."
        ),
    }


def verify_candidate_manifest(
    manifest_path: str, *, repo_root: str
) -> dict[str, Any]:
    """Verify the exact review/signature candidate file set."""
    checks = {
        "manifest_is_valid_json_object": False,
        "manifest_schema_matches": False,
        "authorization_is_pending_owner_resign": False,
        "candidate_file_set_is_exact": False,
        "candidate_paths_are_confined_regular_files": False,
        "candidate_byte_counts_match": False,
        "candidate_digests_match": False,
        "canonical_file_set_is_exact": False,
        "canonical_paths_are_confined_regular_files": False,
        "canonical_digests_match": False,
        "byte_preservation_attributes_are_complete": False,
    }
    errors: list[str] = []
    try:
        manifest_bytes = _read_regular_file(
            manifest_path, "candidate set manifest"
        )
        manifest = _load_json_object(
            manifest_bytes, "candidate set manifest"
        )
        checks["manifest_is_valid_json_object"] = True
    except HandoffError as exc:
        return {"status": "FAIL", "checks": checks, "errors": [str(exc)]}
    checks["manifest_schema_matches"] = (
        manifest.get("schema") == CANDIDATE_MANIFEST_SCHEMA
    )
    checks["authorization_is_pending_owner_resign"] = (
        manifest.get("authorization") == "pending_owner_resign"
    )
    files = manifest.get("files")
    if not isinstance(files, list):
        files = []
        errors.append("candidate manifest files must be a list")
    paths = [
        item.get("path")
        for item in files
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    checks["candidate_file_set_is_exact"] = (
        len(paths) == len(files)
        and len(paths) == len(set(paths))
        and set(paths) == CANDIDATE_FILE_SET
    )

    root = os.path.abspath(repo_root)
    paths_ok = bytes_ok = digest_ok = True
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            paths_ok = bytes_ok = digest_ok = False
            continue
        relative = item["path"]
        candidate = os.path.abspath(
            os.path.join(root, *relative.split("/"))
        )
        if (
            os.path.commonpath([root, candidate]) != root
            or os.path.islink(candidate)
            or not os.path.isfile(candidate)
        ):
            paths_ok = bytes_ok = digest_ok = False
            continue
        try:
            with open(candidate, "rb") as handle:
                payload = handle.read()
        except OSError as exc:
            paths_ok = bytes_ok = digest_ok = False
            errors.append(f"{relative} unreadable: {exc}")
            continue
        bytes_ok = bytes_ok and item.get("bytes") == len(payload)
        digest_ok = digest_ok and item.get("sha256") == P.sha256(payload)
    checks["candidate_paths_are_confined_regular_files"] = paths_ok
    checks["candidate_byte_counts_match"] = bytes_ok
    checks["candidate_digests_match"] = digest_ok

    canonical = manifest.get("canonical_files_unchanged")
    checks["canonical_file_set_is_exact"] = canonical == CANONICAL_FILES
    canonical_paths_ok = canonical_digests_ok = isinstance(canonical, dict)
    if isinstance(canonical, dict):
        for relative, expected_digest in canonical.items():
            candidate = os.path.abspath(
                os.path.join(root, *relative.split("/"))
            )
            if (
                os.path.commonpath([root, candidate]) != root
                or os.path.islink(candidate)
                or not os.path.isfile(candidate)
            ):
                canonical_paths_ok = canonical_digests_ok = False
                continue
            try:
                with open(candidate, "rb") as handle:
                    payload = handle.read()
            except OSError as exc:
                canonical_paths_ok = canonical_digests_ok = False
                errors.append(f"{relative} unreadable: {exc}")
                continue
            canonical_digests_ok = (
                canonical_digests_ok
                and P.sha256(payload) == expected_digest
            )
    checks["canonical_paths_are_confined_regular_files"] = canonical_paths_ok
    checks["canonical_digests_match"] = canonical_digests_ok

    try:
        attributes_payload = _read_regular_file(
            os.path.join(root, ".gitattributes"), ".gitattributes"
        )
        attributes_text = attributes_payload.decode("utf-8", "strict")
        preserved: set[str] = set()
        for line in attributes_text.splitlines():
            fields = line.split()
            if len(fields) >= 2 and "-text" in fields[1:]:
                preserved.add(fields[0].removeprefix("/"))
        checks["byte_preservation_attributes_are_complete"] = (
            BYTE_PRESERVATION_PATHS <= preserved
        )
    except (HandoffError, UnicodeDecodeError) as exc:
        errors.append(f"byte-preservation attributes invalid: {exc}")
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "errors": errors,
        "manifest_sha256": P.sha256(manifest_bytes),
        "claim_boundary": (
            "PASS proves the local candidate files equal the review manifest. "
            "It does not constitute owner signature or canonical promotion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--contract", required=True)
    build_parser.add_argument("--scorer-packet", required=True)
    build_parser.add_argument("--container", required=True)
    build_parser.add_argument("--expected-run-id", required=True)
    build_parser.add_argument("--expected-baseline-commit", required=True)
    build_parser.add_argument("--expected-output-commit", required=True)
    build_parser.add_argument("--expected-container-id", required=True)
    build_parser.add_argument("--test-log", required=True)
    build_parser.add_argument("--validator-output", required=True)
    build_parser.add_argument("--blinding-compromised-reason")
    build_parser.add_argument("--out-dir", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--contract", required=True)
    verify_parser.add_argument("--scorer-packet", required=True)
    verify_parser.add_argument("--test-log", required=True)
    verify_parser.add_argument("--validator-output", required=True)
    verify_parser.add_argument("--expected-run-id", required=True)
    verify_parser.add_argument("--expected-baseline-commit", required=True)
    verify_parser.add_argument("--expected-output-commit", required=True)
    verify_parser.add_argument("--expected-container-id", required=True)
    verify_parser.add_argument("--expected-scorer-packet-sha256", required=True)
    verify_parser.add_argument("--blinding-compromised-reason")
    verify_parser.add_argument("--json-out", required=True)
    candidate_parser = sub.add_parser("verify-candidate")
    candidate_parser.add_argument("--manifest", required=True)
    candidate_parser.add_argument("--repo-root", required=True)
    candidate_parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    if args.command == "build":
        with open(args.scorer_packet, encoding="utf-8") as handle:
            packet_manifest = json.load(handle)
        observed = P.capture_container_state(
            container=args.container,
            baseline_commit=args.expected_baseline_commit,
            receipt_container_path=packet_manifest.get(
                "receipt_container_path", ""
            ),
        )
        outputs, manifest = build_handoff(
            contract_path=args.contract,
            scorer_packet_path=args.scorer_packet,
            expected_run_id=args.expected_run_id,
            expected_baseline_commit=args.expected_baseline_commit,
            expected_output_commit=args.expected_output_commit,
            expected_container_id=args.expected_container_id,
            observed_state=observed,
            test_log_path=args.test_log,
            validator_output_path=args.validator_output,
            blinding_compromised_reason=args.blinding_compromised_reason,
        )
        path = publish_handoff(args.out_dir, outputs, manifest)
        print(f"wrote scorer handoff v3 candidate: {path}")
        print("NOTICE: pending owner re-sign; NOT Gate-2-authorized")
        return 0

    if args.command == "verify":
        result = verify_handoff(
            args.manifest,
            contract_path=args.contract,
            scorer_packet_path=args.scorer_packet,
            test_log_path=args.test_log,
            validator_output_path=args.validator_output,
            expected_run_id=args.expected_run_id,
            expected_baseline_commit=args.expected_baseline_commit,
            expected_output_commit=args.expected_output_commit,
            expected_container_id=args.expected_container_id,
            expected_scorer_packet_sha256=args.expected_scorer_packet_sha256,
            blinding_compromised_reason=args.blinding_compromised_reason,
        )
    else:
        result = verify_candidate_manifest(
            args.manifest, repo_root=args.repo_root
        )
    P.atomic_write_bytes(args.json_out, P._json_bytes(result))
    for name, passed in result["checks"].items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"---\n{result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
