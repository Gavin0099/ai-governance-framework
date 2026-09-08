#!/usr/bin/env python3
"""Fail-closed C1 admission integration that never creates randomization."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

FRAMEWORK_ROOT = Path(__file__).resolve().parents[5]
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))

from governance_tools import rekor_provider


PASSED = "ARM_EXECUTION_ADMISSION_PASSED_NOT_RANDOMIZED"
STOPPED = "STOP_BEFORE_RANDOMIZATION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path.name}")
    return value


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"module cannot be loaded: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_blob_bytes(repo_root: Path, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"committed Git blob is unavailable: {relative}")
    return completed.stdout


def _repo_file(repo_root: Path, relative: Any) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise ValueError("repository-relative path is invalid")
    return repo_root.joinpath(*relative.split("/"))


def _binding_failures(repo_root: Path, bindings: Any) -> list[str]:
    if not isinstance(bindings, list):
        return ["BINDINGS_MISSING"]
    failures: list[str] = []
    for entry in bindings:
        relative = entry.get("path") if isinstance(entry, dict) else None
        expected = entry.get("sha256") if isinstance(entry, dict) else None
        source = entry.get("source") if isinstance(entry, dict) else None
        try:
            path = _repo_file(repo_root, relative)
        except ValueError:
            failures.append("BINDING_PATH_INVALID")
            continue
        if (
            not isinstance(expected, str)
            or HEX64.fullmatch(expected) is None
            or source not in {"git_blob", "raw_file"}
            or not path.is_file()
            or (
                hashlib.sha256(
                    _git_blob_bytes(repo_root, relative)
                    if source == "git_blob"
                    else path.read_bytes()
                ).hexdigest()
                != expected
            )
        ):
            failures.append(f"BINDING_MISMATCH:{relative}")
    return failures


def _validate_client_identity(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
    runtime_facts: dict[str, Any],
) -> None:
    config = manifest["client_identity"]
    amendment = _load_json(_repo_file(repo_root, config["amendment_manifest_path"]))
    if (
        amendment.get("schema")
        != "c1-gate1-client-identity-amendment-freeze.v1"
        or amendment.get("status")
        != "CLIENT_SIDE_IDENTITY_AMENDMENT_FROZEN_NOT_ARM_AUTHORIZED"
        or amendment.get("owner_authority", {}).get("decision")
        != "CLIENT_SIDE_IDENTITY_EVIDENCE_ACCEPTED"
        or amendment.get("preserved_decisions", {}).get("d5_countability")
        != "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION"
    ):
        raise ValueError("client identity amendment is not the accepted freeze")

    identity_module = _load_module(
        "c1_client_identity_receipt",
        _repo_file(repo_root, config["receipt_validator_path"]),
    )
    claim = _load_json(_repo_file(repo_root, config["claim_template_path"]))
    identity_module.validate_claim_template(claim)
    if set(runtime_facts) != {
        "schema",
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
    } or runtime_facts.get("schema") != "c1-client-side-runtime-facts.v1":
        raise ValueError("client runtime facts shape is invalid")
    identity_module.invariant_projection(runtime_facts)
    if (
        runtime_facts.get("identity_evidence_level")
        != "CLIENT_SIDE_INVOCATION_ONLY"
        or runtime_facts.get("server_executed_model_observed") is not False
        or runtime_facts.get("provider_attestation_available") is not False
    ):
        raise ValueError("client runtime facts imply provider observation")


def _validate_provider_capability(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
) -> None:
    config = manifest["external_pin_provider"]
    rekor_provider.load_frozen_profile(repo_root)
    profile_raw = _git_blob_bytes(repo_root, config["provider_profile_path"])
    profile = rekor_provider.RekorProviderProfile.from_bytes(profile_raw)
    if (
        profile.source_sha256 != config.get("provider_profile_sha256")
        or rekor_provider.RECEIPT_SCHEMA != config.get("proof_receipt_schema")
        or config.get("event") != "external_chain_head_pinned"
        or config.get("per_comparison_proof_required") is not True
        or config.get("qualification_is_not_comparison_evidence") is not True
    ):
        raise ValueError("external pin provider contract is invalid")

    terminal = _load_json(
        _repo_file(repo_root, config["qualification_terminal_path"])
    )
    expected = {
        "schema": "ai-governance.rekor-write-probe-terminal/2",
        "status": "WRITE_PROBE_PASSED",
        "freeze_commit": "f5014fb88446324703efcc2f8eece64c3ea942f5",
        "provider_profile_sha256": profile.source_sha256,
        "locator_parse_status": "STRICT_SHAPE_PARSED",
        "locator_verification_status": "VERIFIED_PROOF_BOUND",
        "post_attempt_count": 1,
        "public_append_attempted": True,
        "public_append_may_have_occurred": True,
    }
    if any(terminal.get(key) != value for key, value in expected.items()):
        raise ValueError("Rekor qualification terminal is not proof-bound")
    for key in (
        "external_record_id",
        "request_sha256",
        "subject_sha256",
        "canonicalized_body_sha256",
        "checkpoint_signed_text_sha256",
    ):
        if HEX64.fullmatch(str(terminal.get(key, ""))) is None:
            raise ValueError(f"Rekor qualification terminal {key} is invalid")
    if (
        not isinstance(terminal.get("log_index"), int)
        or terminal["log_index"] < 0
        or not isinstance(terminal.get("tree_size"), int)
        or terminal["tree_size"] <= terminal["log_index"]
        or not isinstance(terminal.get("inclusion_hash_count"), int)
        or terminal["inclusion_hash_count"] < 0
    ):
        raise ValueError("Rekor qualification locator is invalid")


def evaluate_admission(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
    runtime_facts: dict[str, Any],
    randomization_path: Path,
) -> dict[str, Any]:
    reasons: list[str] = []
    if manifest.get("schema") != "c1-arm-execution-admission.v2":
        reasons.append("ADMISSION_MANIFEST_INVALID")
    if manifest.get("status") != "candidate_not_randomized":
        reasons.append("ADMISSION_STATUS_INVALID")
    if manifest.get("d5_countability") != "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION":
        reasons.append("D5_DECISION_DRIFT")
    if randomization_path.exists():
        reasons.append("RANDOMIZATION_ALREADY_EXISTS")

    reasons.extend(_binding_failures(repo_root, manifest.get("bindings")))

    try:
        _validate_client_identity(
            repo_root=repo_root,
            manifest=manifest,
            runtime_facts=runtime_facts,
        )
    except (KeyError, OSError, ValueError) as exc:
        reasons.append(f"CLIENT_IDENTITY_INVALID:{type(exc).__name__}")

    try:
        _validate_provider_capability(repo_root=repo_root, manifest=manifest)
    except (
        KeyError,
        OSError,
        ValueError,
        rekor_provider.RekorVerificationError,
    ) as exc:
        reasons.append(f"EXTERNAL_PIN_PROVIDER_INVALID:{type(exc).__name__}")

    adapter = manifest.get("arm_d_adapter")
    try:
        if not isinstance(adapter, dict):
            raise ValueError("Arm D adapter binding is absent")
        module = _load_module(
            "c1_arm_d_feedback_adapter",
            _repo_file(repo_root, adapter["path"]),
        )
        module.validate_policy(
            _load_json(_repo_file(repo_root, adapter["policy_path"]))
        )
    except (KeyError, OSError, ValueError) as exc:
        reasons.append(f"ARM_D_ADAPTER_INVALID:{type(exc).__name__}")

    reasons = sorted(set(reasons))
    return {
        "checks": {
            "arm_d_adapter_bound": not any(
                reason.startswith("ARM_D_ADAPTER") for reason in reasons
            ),
            "bindings_match": not any(
                reason.startswith(("BINDING", "ADMISSION_MANIFEST"))
                for reason in reasons
            ),
            "client_identity_accepted": not any(
                reason.startswith("CLIENT_IDENTITY") for reason in reasons
            ),
            "d5_remains_unresolved": "D5_DECISION_DRIFT" not in reasons,
            "external_pin_provider_qualified": not any(
                reason.startswith("EXTERNAL_PIN_PROVIDER") for reason in reasons
            ),
            "randomization_absent": "RANDOMIZATION_ALREADY_EXISTS" not in reasons,
        },
        "randomization_created": False,
        "reasons": reasons,
        "schema": "c1-arm-execution-admission-terminal.v2",
        "status": STOPPED if reasons else PASSED,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runtime-facts", required=True)
    parser.add_argument("--randomization-path", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate_admission(
            repo_root=Path(args.repo_root).resolve(),
            manifest=_load_json(Path(args.manifest)),
            runtime_facts=_load_json(Path(args.runtime_facts)),
            randomization_path=Path(args.randomization_path),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "checks": {},
            "randomization_created": False,
            "reasons": [f"ADMISSION_PRECONDITION_FAILED:{type(exc).__name__}"],
            "schema": "c1-arm-execution-admission-terminal.v2",
            "status": STOPPED,
        }
    Path(args.out).write_bytes(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == PASSED else 3


if __name__ == "__main__":
    raise SystemExit(main())
