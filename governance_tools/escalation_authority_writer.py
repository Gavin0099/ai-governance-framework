#!/usr/bin/env python3
"""
Authority writer and validator for E1b Phase-B escalation authority artifacts.

Design intent:
- Authority semantics are not enough; write-path and read-path must both enforce.
- Only artifacts emitted by this writer are considered authority-valid.
- Consumers fail closed when provenance is untrusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WRITER_ID = "governance_tools.escalation_authority_writer"
WRITER_VERSION = "1.0"
ARTIFACT_SCHEMA = "e1b.phase_b.escalation_authority.v1"

ALLOWED_MITIGATION_STATES = {
    "pending_human_validation",
    "pending_independent_validation",
    "author_provisional",
    "validated",
    "waived_by_policy",
}
ALLOWED_GOVERNANCE_TRACK_STATES = {
    "pending_validation",
    "pending_independent_validation",
    "closure_eligible",
    "closed",
    "governance_incomplete",
}
ALLOWED_ROUTE_STATUS = {
    "assigned",
    "in_progress",
    "overdue",
    "completed",
    "not_applicable",
}
ALLOWED_COVERAGE_ERAS = {
    "CURRENT",
    "TRANSITION",
    "PRE-SKIP-TYPE-ERA",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_authority_dir(project_root: Path) -> Path:
    return project_root / "artifacts" / "runtime" / "e1b-phase-b-escalation" / "authority"


def default_authority_artifact_path(project_root: Path, escalation_id: str) -> Path:
    return default_authority_dir(project_root) / f"{escalation_id}.json"


def _canonical_for_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "escalation_id",
        "mitigation_validation_state",
        "governance_track_state",
        "forced_owner",
        "forced_escalation_target",
        "forced_route_due_date",
        "forced_route_status",
        "protected_claim_used",
        "coverage_era",
        "coverage_caveat",
        "contamination_status",
        "release_claims_resolved",
        "release_blocked",
        "release_block_reasons",
    ]
    return {key: payload.get(key) for key in keys}


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = _canonical_for_fingerprint(payload)
    wire = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    seed = f"{WRITER_ID}|{WRITER_VERSION}|{ARTIFACT_SCHEMA}|{wire}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _hash_json(payload: dict[str, Any]) -> str:
    wire = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def _validate_required_str(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} is required and must be a non-empty string")


def _append_release_block(payload: dict[str, Any], reason: str) -> None:
    reasons = payload.setdefault("release_block_reasons", [])
    if reason not in reasons:
        reasons.append(reason)
    payload["release_blocked"] = True


def validate_prewrite_payload(payload: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    normalized = dict(payload)
    normalized.setdefault("release_blocked", False)
    normalized.setdefault("release_block_reasons", [])

    _validate_required_str(normalized, "escalation_id", errors)

    mitigation_state = normalized.get("mitigation_validation_state")
    if mitigation_state not in ALLOWED_MITIGATION_STATES:
        errors.append("mitigation_validation_state is invalid")

    governance_track = normalized.get("governance_track_state")
    if governance_track not in ALLOWED_GOVERNANCE_TRACK_STATES:
        errors.append("governance_track_state is invalid")

    route_status = normalized.get("forced_route_status", "not_applicable")
    if route_status not in ALLOWED_ROUTE_STATUS:
        errors.append("forced_route_status is invalid")

    if mitigation_state == "author_provisional":
        _validate_required_str(normalized, "forced_owner", errors)
        _validate_required_str(normalized, "forced_escalation_target", errors)
        _validate_required_str(normalized, "forced_route_due_date", errors)
        if route_status == "not_applicable":
            errors.append("forced_route_status must not be not_applicable when mitigation_validation_state=author_provisional")

    if route_status == "overdue":
        _append_release_block(normalized, "forced_route_overdue")

    if normalized.get("release_claims_resolved") and route_status == "overdue":
        errors.append("release_claims_resolved cannot be true when forced_route_status=overdue")

    if normalized.get("protected_claim_used"):
        coverage_era = normalized.get("coverage_era")
        caveat = normalized.get("coverage_caveat")
        if coverage_era not in ALLOWED_COVERAGE_ERAS:
            errors.append("coverage_era is required and must be valid when protected_claim_used=true")
        if coverage_era != "CURRENT" and caveat != "not_supported_under_current_coverage":
            errors.append("coverage_caveat must be not_supported_under_current_coverage when coverage_era is not CURRENT")
        if coverage_era != "CURRENT" and not errors:
            _append_release_block(normalized, "protected_claim_invalid_under_current_coverage")

    contamination_status = normalized.get("contamination_status")
    if contamination_status == "unresolved":
        _append_release_block(normalized, "contamination_unresolved")

    escalation_closed = bool(normalized.get("escalation_closed", False))
    if escalation_closed and governance_track in {"pending_validation", "pending_independent_validation", "governance_incomplete"}:
        errors.append("escalation_closed=true is inconsistent with current governance_track_state")

    return len(errors) == 0, errors, normalized


def build_authority_artifact(payload: dict[str, Any], *, written_at: str | None = None) -> dict[str, Any]:
    ok, errors, normalized = validate_prewrite_payload(payload)
    normalized_payload_hash = _hash_json(_canonical_for_fingerprint(normalized))
    source_inputs_hash = _hash_json(payload)
    artifact = {
        "artifact_type": "e1b_phase_b_escalation_authority",
        "artifact_schema": ARTIFACT_SCHEMA,
        "authority_provenance": {
            "writer_id": WRITER_ID,
            "writer_version": WRITER_VERSION,
            "written_at": written_at or _utc_now(),
            "provenance_linkage_version": "v1",
            "authority_valid": ok,
            "authority_errors": errors,
            "source_inputs_hash": source_inputs_hash,
            "normalized_payload_hash": normalized_payload_hash,
        },
        "payload": normalized,
    }
    artifact["authority_provenance"]["payload_fingerprint"] = _fingerprint(normalized)
    return artifact


def write_authority_artifact(project_root: Path, payload: dict[str, Any], *, out_file: Path | None = None) -> dict[str, Any]:
    artifact = build_authority_artifact(payload)
    escalation_id = payload.get("escalation_id", "unknown-escalation")
    target = out_file.resolve() if out_file else default_authority_artifact_path(project_root, escalation_id).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": bool(artifact["authority_provenance"]["authority_valid"]),
        "artifact_file": str(target),
        "escalation_id": escalation_id,
        "release_blocked": bool(artifact["payload"].get("release_blocked")),
        "release_block_reasons": artifact["payload"].get("release_block_reasons") or [],
        "authority_errors": artifact["authority_provenance"]["authority_errors"],
    }


def assess_authority_artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "ok": False,
            "exists": False,
            "authority_valid": False,
            "manifest_file": str(path),
            "error": "authority_artifact_missing",
            "release_blocked": True,
            "release_block_reasons": ["untrusted_escalation_provenance"],
        }
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "exists": True,
            "authority_valid": False,
            "manifest_file": str(path),
            "error": f"authority_artifact_unreadable:{exc}",
            "release_blocked": True,
            "release_block_reasons": ["untrusted_escalation_provenance"],
        }

    provenance = artifact.get("authority_provenance") or {}
    payload = artifact.get("payload") or {}

    ok, errors, normalized = validate_prewrite_payload(payload)
    expected_fingerprint = _fingerprint(normalized)
    actual_fingerprint = provenance.get("payload_fingerprint")
    expected_normalized_hash = _hash_json(_canonical_for_fingerprint(normalized))
    actual_normalized_hash = provenance.get("normalized_payload_hash")

    linkage_fields_ok = all(
        isinstance(provenance.get(field), str) and bool(str(provenance.get(field)).strip())
        for field in ("written_at", "payload_fingerprint", "source_inputs_hash", "normalized_payload_hash")
    )

    trusted_writer = (
        provenance.get("writer_id") == WRITER_ID
        and provenance.get("writer_version") == WRITER_VERSION
        and artifact.get("artifact_schema") == ARTIFACT_SCHEMA
        and provenance.get("provenance_linkage_version") == "v1"
    )
    fingerprint_valid = isinstance(actual_fingerprint, str) and actual_fingerprint == expected_fingerprint
    normalized_hash_valid = isinstance(actual_normalized_hash, str) and actual_normalized_hash == expected_normalized_hash

    authority_valid = bool(
        ok
        and trusted_writer
        and linkage_fields_ok
        and fingerprint_valid
        and normalized_hash_valid
        and provenance.get("authority_valid") is True
    )
    release_blocked = bool(payload.get("release_blocked")) or (not authority_valid)
    release_block_reasons = list(payload.get("release_block_reasons") or [])
    if not authority_valid:
        if "untrusted_escalation_provenance" not in release_block_reasons:
            release_block_reasons.append("untrusted_escalation_provenance")

    return {
        "ok": authority_valid,
        "exists": True,
        "authority_valid": authority_valid,
        "manifest_file": str(path),
        "error": None if authority_valid else "authority_validation_failed",
        "trusted_writer": trusted_writer,
        "linkage_fields_ok": linkage_fields_ok,
        "fingerprint_valid": fingerprint_valid,
        "normalized_hash_valid": normalized_hash_valid,
        "validation_errors": errors,
        "escalation_id": payload.get("escalation_id"),
        "release_blocked": release_blocked,
        "release_block_reasons": release_block_reasons,
    }


def assess_authority_directory(project_root: Path) -> dict[str, Any]:
    authority_dir = default_authority_dir(project_root)
    if not authority_dir.is_dir():
        return {
            "available": False,
            "ok": True,
            "source": "unavailable",
            "authority_dir": str(authority_dir),
            "artifacts_read": 0,
            "release_blocked": False,
            "release_block_reasons": [],
            "records": [],
        }

    files = sorted(authority_dir.glob("*.json"))
    records = [assess_authority_artifact(path) for path in files]
    all_ok = all(item["ok"] for item in records)
    blocked = any(item.get("release_blocked") for item in records) or (len(records) > 0 and not all_ok)
    reasons: list[str] = []
    for item in records:
        for reason in item.get("release_block_reasons") or []:
            if reason not in reasons:
                reasons.append(reason)

    return {
        "available": len(files) > 0,
        "ok": all_ok,
        "source": "authority-writer-monopoly",
        "authority_dir": str(authority_dir),
        "artifacts_read": len(files),
        "release_blocked": blocked,
        "release_block_reasons": reasons,
        "records": records,
    }


def _format_human(result: dict[str, Any]) -> str:
    lines = [
        "[escalation_authority]",
        f"ok={result.get('ok')}",
        f"available={result.get('available')}",
        f"source={result.get('source')}",
        f"artifacts_read={result.get('artifacts_read')}",
        f"release_blocked={result.get('release_blocked')}",
    ]
    reasons = result.get("release_block_reasons") or []
    if reasons:
        lines.append(f"release_block_reasons={','.join(reasons)}")
    for item in result.get("records") or []:
        lines.append(
            f"record[{item.get('escalation_id')}]="
            f"ok:{item.get('ok')},trusted_writer:{item.get('trusted_writer')},fingerprint_valid:{item.get('fingerprint_valid')}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or assess escalation authority artifacts.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--mode", choices=("assess", "write"), default="assess")
    parser.add_argument("--input")
    parser.add_argument("--out")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if args.mode == "write":
        if not args.input:
            raise SystemExit("--input JSON file is required in write mode")
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = write_authority_artifact(
            project_root,
            payload,
            out_file=Path(args.out).resolve() if args.out else None,
        )
    else:
        result = assess_authority_directory(project_root)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_human(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
