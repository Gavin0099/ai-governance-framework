"""Pure C1 D5 countability amendment and fail-closed admission overlay.

This module performs no network, producer, scorer, mapping-release, or
randomization I/O. The only repository reads in the admission overlay verify
already-committed bindings.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from types import ModuleType
from typing import Any, Mapping, Sequence


RESOLVED_TOKEN = "CURRENT_C1_FINAL_HEAD_RECEIPT_NOT_REQUIRED"
POLICY_SCHEMA = "c1-gate1-d5-countability-policy.v1"
MANIFEST_SCHEMA = "c1-gate1-d5-countability-amendment-freeze.v1"
TERMINAL_SCHEMA = "c1-gate1-d5-amendment-admission-terminal.v1"
PASSED = "ARM_EXECUTION_ADMISSION_PASSED_NOT_RANDOMIZED"
STOPPED = "STOP_BEFORE_RANDOMIZATION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EVENT_ORDER = (
    "randomization_committed",
    "first_outcome_sealed",
    "second_outcome_sealed",
    "blind_set_closed",
    "primary_scorer_submitted",
    "second_scorer_submitted",
    "external_chain_head_pinned",
    "mapping_released",
)


class D5CountabilityError(ValueError):
    """Raised when the frozen D5 amendment is violated."""


@dataclass(frozen=True)
class CountabilityAssessment:
    countable: bool
    reasons: tuple[str, ...]
    final_head_receipt_required: bool = False


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise D5CountabilityError(f"JSON root is not an object: {path.name}")
    return value


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise D5CountabilityError(f"module cannot be loaded: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo_file(repo_root: Path, relative: Any) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise D5CountabilityError("repository-relative path is invalid")
    return repo_root.joinpath(*relative.split("/"))


def _git_blob_bytes(repo_root: Path, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise D5CountabilityError(f"committed Git blob is unavailable: {relative}")
    return completed.stdout


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
        except D5CountabilityError:
            failures.append("BINDING_PATH_INVALID")
            continue
        if source not in {"git_blob", "raw_file"}:
            failures.append(f"BINDING_SOURCE_INVALID:{relative}")
            continue
        if not isinstance(expected, str) or HEX64.fullmatch(expected) is None:
            failures.append(f"BINDING_DIGEST_INVALID:{relative}")
            continue
        try:
            raw = (
                _git_blob_bytes(repo_root, relative)
                if source == "git_blob"
                else path.read_bytes()
            )
        except (OSError, D5CountabilityError):
            failures.append(f"BINDING_UNAVAILABLE:{relative}")
            continue
        if hashlib.sha256(raw).hexdigest() != expected:
            failures.append(f"BINDING_MISMATCH:{relative}")
    return failures


def validate_policy(policy: Mapping[str, Any]) -> None:
    if set(policy) != {
        "claim_ceiling",
        "decision_scope",
        "event_7",
        "event_8",
        "event_order",
        "final_head_receipt",
        "preserved_decisions",
        "resolved_token",
        "schema",
        "status",
    }:
        raise D5CountabilityError("D5 policy shape is invalid")
    if (
        policy.get("schema") != POLICY_SCHEMA
        or policy.get("status") != RESOLVED_TOKEN
        or policy.get("resolved_token") != RESOLVED_TOKEN
        or policy.get("decision_scope") != "internal_skill_funding_only"
        or tuple(policy.get("event_order", ())) != EVENT_ORDER
    ):
        raise D5CountabilityError("D5 policy identity or event order differs")

    event_7 = policy.get("event_7")
    if not isinstance(event_7, Mapping) or event_7 != {
        "failure": "INVALID_AND_UNCOUNTABLE",
        "must_follow_both_scorer_submissions": True,
        "must_precede_mapping_release": True,
        "name": "external_chain_head_pinned",
        "proof_bearing": True,
        "qualified_provider": "rekor_v2",
        "required": True,
    }:
        raise D5CountabilityError("event 7 external pin was weakened")

    event_8 = policy.get("event_8")
    if not isinstance(event_8, Mapping) or event_8 != {
        "external_final_head_anchor_required": False,
        "local_chain_required": True,
        "mapping_commitment_required": True,
        "missing_or_altered": "INVALID_AND_UNCOUNTABLE",
        "name": "mapping_released",
    }:
        raise D5CountabilityError("event 8 local requirements differ")

    final_head = policy.get("final_head_receipt")
    if not isinstance(final_head, Mapping) or final_head != {
        "absence_alone": "NOT_A_FAILURE",
        "event_9_defined": False,
        "presence_cannot_rescue_another_failure": True,
        "required_for_current_c1": False,
    }:
        raise D5CountabilityError("final-head receipt semantics differ")

    preserved = policy.get("preserved_decisions")
    if not isinstance(preserved, Mapping) or set(preserved.values()) != {True}:
        raise D5CountabilityError("a preserved decision was changed")


def assess_countability(
    *,
    event_names: Sequence[str],
    event_7_proof_verified: bool,
    event_8_mapping_commitment_verified: bool,
    local_chain_verified: bool,
    final_head_receipt_present: bool,
) -> CountabilityAssessment:
    if any(
        not isinstance(value, bool)
        for value in (
            event_7_proof_verified,
            event_8_mapping_commitment_verified,
            local_chain_verified,
            final_head_receipt_present,
        )
    ):
        raise D5CountabilityError("countability evidence flags must be booleans")

    reasons: list[str] = []
    if tuple(event_names) != EVENT_ORDER:
        reasons.append("EVENT_SEQUENCE_INVALID")
    if not event_7_proof_verified:
        reasons.append("EVENT_7_EXTERNAL_PIN_INVALID")
    if not event_8_mapping_commitment_verified:
        reasons.append("EVENT_8_MAPPING_COMMITMENT_INVALID")
    if not local_chain_verified:
        reasons.append("LOCAL_FINAL_CHAIN_INVALID")
    return CountabilityAssessment(not reasons, tuple(sorted(reasons)))


def _validate_manifest_decision(manifest: Mapping[str, Any]) -> None:
    if (
        manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("status")
        != "D5_COUNTABILITY_AMENDMENT_FROZEN_NOT_RANDOMIZED"
        or manifest.get("countability_decision", {}).get("resolved_token")
        != RESOLVED_TOKEN
        or manifest.get("countability_decision", {}).get("decision_scope")
        != "internal_skill_funding_only"
    ):
        raise D5CountabilityError("D5 amendment manifest is not the accepted freeze")
    packet = manifest.get("owner_authority", {}).get("decision_packet", {})
    if packet != {
        "bytes": 14040,
        "file": "c1-d5-final-head-countability-owner-decision-packet-2026-08-26.md",
        "lines": 326,
        "location": "repo_external_review_surface",
        "review_verdict": "APPROVED",
        "sha256": "d4fe3ba43ec9b2d1b74c3a14feb36dfad05ea945353e45b87dd979c89796cb6b",
    }:
        raise D5CountabilityError("owner decision packet binding differs")
    authority = manifest.get("execution_authority", {})
    if (
        authority.get("randomization_authorized") is not False
        or authority.get("arm_execution_authorized") is not False
    ):
        raise D5CountabilityError("execution authority must remain closed")


def evaluate_amended_admission(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    randomization_path: Path,
) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        _validate_manifest_decision(manifest)
    except (KeyError, TypeError, D5CountabilityError):
        reasons.append("D5_AMENDMENT_INVALID")

    reasons.extend(_binding_failures(repo_root, manifest.get("bindings")))

    try:
        policy = _load_json(
            _repo_file(repo_root, manifest["countability_decision"]["policy_path"])
        )
        validate_policy(policy)
    except (KeyError, OSError, D5CountabilityError):
        reasons.append("D5_POLICY_INVALID")

    try:
        base_manifest = _load_json(
            _repo_file(repo_root, manifest["base_admission"]["manifest_path"])
        )
        base_terminal = _load_json(
            _repo_file(repo_root, manifest["base_admission"]["terminal_path"])
        )
        if (
            base_manifest.get("d5_countability")
            != "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION"
            or base_terminal.get("status") != PASSED
            or base_terminal.get("randomization_created") is not False
            or base_terminal.get("reasons") != []
        ):
            raise D5CountabilityError("base admission is not the preserved pass")
    except (KeyError, OSError, D5CountabilityError):
        reasons.append("BASE_ADMISSION_INVALID")

    if randomization_path.exists():
        reasons.append("RANDOMIZATION_ALREADY_EXISTS")

    reasons = sorted(set(reasons))
    checks = {
        "base_admission_passed": "BASE_ADMISSION_INVALID" not in reasons,
        "bindings_match": not any(reason.startswith("BINDING") for reason in reasons),
        "event_7_external_pin_preserved": "D5_POLICY_INVALID" not in reasons,
        "event_8_local_chain_required": "D5_POLICY_INVALID" not in reasons,
        "final_head_receipt_not_required": not any(
            reason.startswith("D5_") for reason in reasons
        ),
        "randomization_absent": "RANDOMIZATION_ALREADY_EXISTS" not in reasons,
        "resolved_token_exact": "D5_AMENDMENT_INVALID" not in reasons,
    }
    return {
        "checks": checks,
        "randomization_created": False,
        "reasons": reasons,
        "schema": TERMINAL_SCHEMA,
        "status": STOPPED if reasons else PASSED,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--randomization-path", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate_amended_admission(
            repo_root=Path(args.repo_root).resolve(),
            manifest=_load_json(Path(args.manifest)),
            randomization_path=Path(args.randomization_path),
        )
    except (OSError, json.JSONDecodeError, D5CountabilityError) as exc:
        result = {
            "checks": {},
            "randomization_created": False,
            "reasons": [f"ADMISSION_PRECONDITION_FAILED:{type(exc).__name__}"],
            "schema": TERMINAL_SCHEMA,
            "status": STOPPED,
        }
    Path(args.out).write_bytes(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == PASSED else 3


if __name__ == "__main__":
    raise SystemExit(main())
