#!/usr/bin/env python3
"""Fail-closed verification for an operator-captured scorer packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any

from capture_scorer_packet import ARTIFACT_FILES, SCHEMA_VERSION, parse_paths, parse_status
from evidence_io import atomic_write_json


REQUIRED_ARTIFACTS = set(ARTIFACT_FILES)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify(
    packet_path: str,
    *,
    expected_run_id: str,
    expected_head: str,
    expected_container_id: str,
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "packet_is_valid_json_object": False,
        "schema_version_matches": False,
        "run_id_matches": False,
        "baseline_head_matches": False,
        "container_id_matches": False,
        "required_artifact_set_is_exact": False,
        "artifact_paths_are_fixed_and_confined": False,
        "all_artifacts_exist": False,
        "artifact_byte_counts_match": False,
        "artifact_digests_match": False,
        "result_json_is_parseable_object": False,
        "tracked_inventory_matches_status": False,
        "manifest_inventory_matches_captured_files": False,
        "diff_covers_every_tracked_changed_file": False,
        "scorer_inputs_include_result_and_diff": False,
    }
    errors: list[str] = []
    packet: dict[str, Any] = {}
    packet_dir = os.path.dirname(os.path.abspath(packet_path))
    payloads: dict[str, bytes] = {}
    try:
        with open(packet_path, encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("packet root is not an object")
        packet = loaded
        checks["packet_is_valid_json_object"] = True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"packet load failed: {exc}")
        return {
            "status": "FAIL",
            "checks": checks,
            "errors": errors,
            "claim_boundary": "No scorer packet claim is valid when the manifest cannot be loaded.",
        }

    checks["schema_version_matches"] = packet.get("schema_version") == SCHEMA_VERSION
    checks["run_id_matches"] = packet.get("run_id") == expected_run_id
    checks["baseline_head_matches"] = packet.get("baseline_head") == expected_head
    container = packet.get("container")
    checks["container_id_matches"] = (
        isinstance(container, dict)
        and container.get("id") == expected_container_id
    )
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
        errors.append("artifacts is not an object")
    checks["required_artifact_set_is_exact"] = set(artifacts) == REQUIRED_ARTIFACTS

    paths_ok = True
    exists_ok = True
    bytes_ok = True
    digest_ok = True
    for key, expected_name in ARTIFACT_FILES.items():
        metadata = artifacts.get(key)
        if not isinstance(metadata, dict) or metadata.get("path") != expected_name:
            paths_ok = False
            exists_ok = False
            bytes_ok = False
            digest_ok = False
            continue
        candidate = os.path.abspath(os.path.join(packet_dir, expected_name))
        if os.path.dirname(candidate) != packet_dir or os.path.islink(candidate):
            paths_ok = False
            continue
        try:
            with open(candidate, "rb") as handle:
                payload = handle.read()
            payloads[key] = payload
        except OSError as exc:
            exists_ok = False
            bytes_ok = False
            digest_ok = False
            errors.append(f"{key} missing or unreadable: {exc}")
            continue
        bytes_ok = bytes_ok and metadata.get("bytes") == len(payload)
        digest_ok = digest_ok and metadata.get("sha256") == digest(payload)
    checks["artifact_paths_are_fixed_and_confined"] = paths_ok
    checks["all_artifacts_exist"] = exists_ok and len(payloads) == len(ARTIFACT_FILES)
    checks["artifact_byte_counts_match"] = bytes_ok
    checks["artifact_digests_match"] = digest_ok

    try:
        result = json.loads(payloads["result"].decode("utf-8", "strict"))
        checks["result_json_is_parseable_object"] = isinstance(result, dict)
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        pass

    status_entries: list[dict[str, str]] = []
    tracked_paths: list[str] = []
    try:
        status_entries = parse_status(payloads["status"])
        tracked_paths = parse_paths(payloads["tracked_paths"])
        tracked_from_status = sorted(
            entry["path"] for entry in status_entries if entry["code"] != "??"
        )
        checks["tracked_inventory_matches_status"] = tracked_paths == tracked_from_status
    except (KeyError, UnicodeDecodeError, ValueError) as exc:
        errors.append(f"inventory parse failed: {exc}")

    workspace = packet.get("workspace")
    if isinstance(workspace, dict):
        untracked = sorted(
            entry["path"] for entry in status_entries if entry["code"] == "??"
        )
        checks["manifest_inventory_matches_captured_files"] = (
            workspace.get("status_entries") == status_entries
            and workspace.get("tracked_changed_files") == tracked_paths
            and workspace.get("untracked_files") == untracked
        )

    diff_payload = payloads.get("diff", b"")
    checks["diff_covers_every_tracked_changed_file"] = bool(tracked_paths) and all(
        f"diff --git a/{path} b/{path}".encode("utf-8") in diff_payload
        for path in tracked_paths
    )
    checks["scorer_inputs_include_result_and_diff"] = (
        packet.get("scorer_inputs") == ["result", "diff"]
    )

    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "errors": errors,
        "run_id": packet.get("run_id"),
        "baseline_head": packet.get("baseline_head"),
        "tracked_changed_files": tracked_paths,
        "claim_boundary": (
            "PASS proves that the fixed packet artifacts are present, byte-attested, "
            "and inventory-consistent. It does not authenticate the manifest writer "
            "or prove the change or producer report is correct."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-container-id", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()
    result = verify(
        args.packet,
        expected_run_id=args.expected_run_id,
        expected_head=args.expected_head,
        expected_container_id=args.expected_container_id,
    )
    atomic_write_json(args.json_out, result)
    for name, passed in result["checks"].items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    for error in result["errors"]:
        print(f"[ERROR] {error}")
    print(f"---\n{result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
