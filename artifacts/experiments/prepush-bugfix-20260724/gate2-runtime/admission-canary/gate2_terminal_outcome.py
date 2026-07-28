#!/usr/bin/env python3
"""Strict terminal-timeout packet for the Gate 2 pre-push experiment only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA = "gate2-terminal-timeout-packet.v1"
PACKET_KIND = "terminal_timeout_v1"
TIMEOUT_SECONDS = 1800
MANIFEST = "terminal-outcome-v1.json"
BASE_ARTIFACTS = (
    "final-diff.patch",
    "final-status.txt",
    "timeout-cleanup.json",
)
ARM_IDENTITY_PATTERN = re.compile(
    r"(?:^|[-_/\\\s])arm[-_/\\\s]?[abcd](?:$|[-_/\\\s])",
    re.IGNORECASE,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_record(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "name": path.name,
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
    }


def _external_record(name: str, path: Path) -> dict[str, object]:
    if not path.exists():
        return {"name": name, "present": False, "bytes": 0, "sha256": None}
    raw = path.read_bytes()
    return {
        "name": name,
        "present": True,
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
    }


def _assert_identity_free(label: str, value: str) -> None:
    if ARM_IDENTITY_PATTERN.search(value):
        raise ValueError(f"{label} leaks an arm identity")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _validate_cleanup(value: dict[str, Any]) -> None:
    required = {
        "timeout_seconds",
        "process_pid",
        "termination_method",
        "termination_returncode",
        "process_tree_terminated",
        "stdout_pipe_closed",
        "completed_at_epoch",
    }
    if set(value) != required:
        raise ValueError("timeout cleanup receipt has an unexpected field set")
    if value["timeout_seconds"] != TIMEOUT_SECONDS:
        raise ValueError("timeout cleanup receipt changed the frozen limit")
    if not isinstance(value["process_pid"], int) or value["process_pid"] <= 0:
        raise ValueError("timeout cleanup receipt has no valid process pid")
    if value["termination_method"] not in {
        "windows_taskkill_tree",
        "posix_process_group",
    }:
        raise ValueError("timeout cleanup receipt has an unknown method")
    if not isinstance(value["termination_returncode"], int):
        raise ValueError("timeout cleanup return code is malformed")
    if value["process_tree_terminated"] is not True:
        raise ValueError("timeout process tree was not verified terminated")
    if value["stdout_pipe_closed"] is not True:
        raise ValueError("timeout stdout pipe was not verified closed")
    if not isinstance(value["completed_at_epoch"], (int, float)):
        raise ValueError("timeout cleanup completion time is malformed")


def build_packet(
    *,
    out_dir: Path,
    run_id: str,
    container_id: str,
    baseline_commit: str,
    current_head: str,
    current_tree: str,
    final_diff: bytes,
    final_status: bytes,
    producer_result: bytes | None,
    cleanup_receipt: dict[str, Any],
    transcript_path: Path,
    adapter_log_path: Path,
    stream_path: Path,
) -> Path:
    """Create a packet transaction; the manifest is written last."""
    for label, value in (
        ("run_id", run_id),
        ("container_id", container_id),
        ("baseline_commit", baseline_commit),
        ("current_head", current_head),
        ("current_tree", current_tree),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")
        _assert_identity_free(label, value)
    _validate_cleanup(cleanup_receipt)
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "final-diff.patch").write_bytes(final_diff)
    (out_dir / "final-status.txt").write_bytes(final_status)
    (out_dir / "timeout-cleanup.json").write_text(
        json.dumps(cleanup_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    producer_claim_status = "absent"
    operator_claim = (
        "The producer did not submit a completion claim before the frozen "
        "wall-clock cap."
    )
    artifact_names = list(BASE_ARTIFACTS)
    if producer_result is not None:
        try:
            result_value = json.loads(producer_result.decode("utf-8", "strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("producer result is not valid UTF-8 JSON") from exc
        if not isinstance(result_value, dict):
            raise ValueError("producer result must be a JSON object")
        (out_dir / "result.json").write_bytes(producer_result)
        artifact_names.append("result.json")
        producer_claim_status = "present"
        operator_claim = (
            "The producer submitted the attached completion claim before the "
            "frozen wall-clock cap, but the model process did not terminate "
            "before the cap."
        )
    external = []
    for name, path in (
        ("transcript.jsonl", transcript_path),
        ("adapter-log.jsonl", adapter_log_path),
        ("claude-stream.jsonl", stream_path),
    ):
        external.append(_external_record(name, path))
    core: dict[str, object] = {
        "schema": SCHEMA,
        "packet_kind": PACKET_KIND,
        "source_attestation": {
            "identity": {
                "run_id": run_id,
                "container_id": container_id,
                "baseline_commit": baseline_commit,
            }
        },
        "terminal_outcome": {
            "outcome": "timeout",
            "timeout_seconds": TIMEOUT_SECONDS,
            "producer_completion_claim": producer_claim_status,
            "operator_terminal_claim": operator_claim,
            "current_head": current_head,
            "current_tree": current_tree,
        },
        "artifacts": [
            _file_record(out_dir / name) for name in artifact_names
        ],
        "external_evidence": external,
    }
    core_sha256 = _sha256_bytes(_canonical(core))
    packet = {
        **core,
        "anon_id": f"OUT-{core_sha256[:12]}",
        "core_sha256": core_sha256,
    }
    manifest = out_dir / MANIFEST
    manifest.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def verify_packet(
    *,
    packet_path: Path,
    expected_run_id: str,
    expected_container_id: str,
    expected_baseline_commit: str,
    transcript_path: Path,
    adapter_log_path: Path,
    stream_path: Path,
) -> dict[str, object]:
    packet_dir = packet_path.parent
    checks: dict[str, bool] = {}
    packet = _read_json_object(packet_path)
    terminal = packet.get("terminal_outcome", {})
    claim_status = (
        terminal.get("producer_completion_claim")
        if isinstance(terminal, dict) else None
    )
    artifact_names = list(BASE_ARTIFACTS)
    if claim_status == "present":
        artifact_names.append("result.json")
    expected_files = frozenset((*artifact_names, MANIFEST))
    checks["exact_file_set"] = (
        {path.name for path in packet_dir.iterdir() if path.is_file()}
        == expected_files
    )
    checks["schema"] = packet.get("schema") == SCHEMA
    checks["packet_kind"] = packet.get("packet_kind") == PACKET_KIND
    identity = packet.get("source_attestation", {}).get("identity", {})
    checks["identity_object"] = isinstance(identity, dict)
    checks["identity_matches"] = (
        isinstance(identity, dict)
        and identity
        == {
            "run_id": expected_run_id,
            "container_id": expected_container_id,
            "baseline_commit": expected_baseline_commit,
        }
    )
    try:
        for label, value in identity.items():
            if not isinstance(value, str):
                raise ValueError(f"{label} is not a string")
            _assert_identity_free(label, value)
        checks["identity_free"] = True
    except (AttributeError, ValueError):
        checks["identity_free"] = False
    checks["timeout_outcome"] = (
        isinstance(terminal, dict)
        and terminal.get("outcome") == "timeout"
        and terminal.get("timeout_seconds") == TIMEOUT_SECONDS
        and terminal.get("producer_completion_claim") in {"absent", "present"}
        and isinstance(terminal.get("operator_terminal_claim"), str)
        and bool(terminal.get("operator_terminal_claim"))
        and isinstance(terminal.get("current_head"), str)
        and isinstance(terminal.get("current_tree"), str)
    )
    if claim_status == "present":
        try:
            result_value = json.loads(
                (packet_dir / "result.json").read_text(encoding="utf-8")
            )
            checks["producer_claim_artifact"] = isinstance(result_value, dict)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            checks["producer_claim_artifact"] = False
    else:
        checks["producer_claim_artifact"] = claim_status == "absent"
    artifact_records = packet.get("artifacts")
    checks["artifact_record_set"] = (
        isinstance(artifact_records, list)
        and [item.get("name") for item in artifact_records
             if isinstance(item, dict)]
        == artifact_names
    )
    if checks["artifact_record_set"]:
        checks["artifact_hashes"] = all(
            item == _file_record(packet_dir / str(item["name"]))
            for item in artifact_records
        )
    else:
        checks["artifact_hashes"] = False
    try:
        _validate_cleanup(_read_json_object(packet_dir / "timeout-cleanup.json"))
        checks["cleanup_receipt"] = True
    except ValueError:
        checks["cleanup_receipt"] = False
    external_records = packet.get("external_evidence")
    expected_external = []
    for name, path in (
        ("transcript.jsonl", transcript_path),
        ("adapter-log.jsonl", adapter_log_path),
        ("claude-stream.jsonl", stream_path),
    ):
        expected_external.append(_external_record(name, path))
    checks["external_evidence_hashes"] = external_records == expected_external
    core = {
        key: value
        for key, value in packet.items()
        if key not in {"anon_id", "core_sha256"}
    }
    core_sha256 = _sha256_bytes(_canonical(core))
    checks["anonymous_id"] = (
        packet.get("core_sha256") == core_sha256
        and packet.get("anon_id") == f"OUT-{core_sha256[:12]}"
    )
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "packet_kind": PACKET_KIND,
        "anon_id": packet.get("anon_id"),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--packet", type=Path, required=True)
    verify.add_argument("--expected-run-id", required=True)
    verify.add_argument("--expected-container-id", required=True)
    verify.add_argument("--expected-baseline-commit", required=True)
    verify.add_argument("--transcript", type=Path, required=True)
    verify.add_argument("--adapter-log", type=Path, required=True)
    verify.add_argument("--stream", type=Path, required=True)
    verify.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    result = verify_packet(
        packet_path=args.packet,
        expected_run_id=args.expected_run_id,
        expected_container_id=args.expected_container_id,
        expected_baseline_commit=args.expected_baseline_commit,
        transcript_path=args.transcript,
        adapter_log_path=args.adapter_log,
        stream_path=args.stream,
    )
    args.json_out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
