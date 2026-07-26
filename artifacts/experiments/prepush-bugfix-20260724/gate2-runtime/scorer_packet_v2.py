#!/usr/bin/env python3
"""Capture and verify a commit-bound Gate 2 scorer packet.

Schema v2 is intentionally separate from the admission-canary schema v1.
The canary captured an uncommitted working-tree diff.  Gate 2 producers must
instead leave a clean output commit, so v2 binds:

    baseline_commit -> output_commit -> producer receipt -> final diff

The packet manifest is written last.  A packet is valid only when the manifest
and every fixed component exist and match, and live verification additionally
re-reads the running container and compares the captured bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable


SCHEMA_VERSION = "2.0"
PACKET_FILENAME = "scorer-packet-v2.json"
DEFAULT_RECEIPT_CONTAINER_PATH = "/work/out/producer-receipt.json"
ARTIFACT_FILES = {
    "result": "result.json",
    "diff": "final-diff.patch",
    "status": "final-status.txt",
    "tracked_paths": "final-tracked-paths.txt",
    "receipt": "producer-receipt.json",
}
REQUIRED_ARTIFACTS = set(ARTIFACT_FILES)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_lower_hex(value: str, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(ch in "0123456789abcdef" for ch in value)
    )


def atomic_write_bytes(path: str, payload: bytes) -> None:
    destination = os.path.abspath(path)
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=directory,
        prefix=f".{os.path.basename(destination)}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _parse_paths(payload: bytes) -> list[str]:
    try:
        paths = [
            line
            for line in payload.decode("utf-8", "strict").splitlines()
            if line
        ]
    except UnicodeDecodeError as exc:
        raise ValueError("tracked path list must be UTF-8") from exc
    if paths != sorted(paths):
        raise ValueError("tracked path list must be sorted")
    if len(paths) != len(set(paths)):
        raise ValueError("tracked path list contains duplicates")
    for path in paths:
        if path.startswith("/") or "\\" in path or path in (".", ".."):
            raise ValueError(f"unsupported tracked path: {path!r}")
        if any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError(f"unsupported tracked path: {path!r}")
    return paths


def _artifact(path: str, payload: bytes, role: str) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": sha256(payload),
        "role": role,
    }


def build_packet(
    *,
    run_id: str,
    container_name: str,
    container_id: str,
    baseline_commit: str,
    output_commit: str,
    receipt_container_path: str,
    result_bytes: bytes,
    diff_bytes: bytes,
    status_bytes: bytes,
    tracked_paths_bytes: bytes,
    receipt_bytes: bytes,
    captured_at: str,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Validate source bytes and build a v2 manifest without writing files."""
    for label, value in (
        ("run_id", run_id),
        ("container_name", container_name),
        ("container_id", container_id),
        ("baseline_commit", baseline_commit),
        ("output_commit", output_commit),
        ("receipt_container_path", receipt_container_path),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} is required")
    if not _is_lower_hex(baseline_commit, 40):
        raise ValueError("baseline_commit must be a full lowercase SHA-1")
    if not _is_lower_hex(output_commit, 40):
        raise ValueError("output_commit must be a full lowercase SHA-1")
    if not _is_lower_hex(container_id, 64):
        raise ValueError("container_id must be a full lowercase Docker id")
    if receipt_container_path != DEFAULT_RECEIPT_CONTAINER_PATH:
        raise ValueError(
            f"receipt_container_path must be {DEFAULT_RECEIPT_CONTAINER_PATH}"
        )
    if baseline_commit == output_commit:
        raise ValueError("baseline_commit and output_commit must differ")
    if status_bytes:
        raise ValueError("producer worktree is dirty; clean output commit required")
    if not diff_bytes:
        raise ValueError("baseline-to-output final diff is empty")

    _load_json_object(result_bytes, "result.json")
    receipt = _load_json_object(receipt_bytes, "producer receipt")
    if receipt.get("linked_commit") != output_commit:
        raise ValueError("producer receipt linked_commit does not match output_commit")

    tracked_paths = _parse_paths(tracked_paths_bytes)
    if not tracked_paths:
        raise ValueError("no tracked changed file was captured")
    for path in tracked_paths:
        header = f"diff --git a/{path} b/{path}".encode("utf-8")
        if header not in diff_bytes:
            raise ValueError(f"final diff omits tracked changed file: {path}")

    files = {
        ARTIFACT_FILES["result"]: result_bytes,
        ARTIFACT_FILES["diff"]: diff_bytes,
        ARTIFACT_FILES["status"]: status_bytes,
        ARTIFACT_FILES["tracked_paths"]: tracked_paths_bytes,
        ARTIFACT_FILES["receipt"]: receipt_bytes,
    }
    packet = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "captured_at": captured_at,
        "container": {"name": container_name, "id": container_id},
        "baseline_commit": baseline_commit,
        "output_commit": output_commit,
        "receipt_container_path": receipt_container_path,
        "artifacts": {
            "result": _artifact(
                ARTIFACT_FILES["result"], result_bytes, "producer_self_report"
            ),
            "diff": _artifact(
                ARTIFACT_FILES["diff"],
                diff_bytes,
                "operator_captured_baseline_to_output_diff",
            ),
            "status": _artifact(
                ARTIFACT_FILES["status"], status_bytes, "clean_worktree_proof"
            ),
            "tracked_paths": _artifact(
                ARTIFACT_FILES["tracked_paths"],
                tracked_paths_bytes,
                "tracked_change_inventory",
            ),
            "receipt": _artifact(
                ARTIFACT_FILES["receipt"],
                receipt_bytes,
                "producer_commit_linkage",
            ),
        },
        "workspace": {
            "clean": True,
            "tracked_changed_files": tracked_paths,
        },
        "scorer_input_core": ["result", "diff"],
        "handoff_attachments_required": ["test_log", "validator_output"],
        "claim_boundary": (
            "The packet binds captured bytes to a named run, running container, "
            "baseline commit, clean output commit and producer receipt. Live "
            "verification re-reads the container. It does not authenticate the "
            "operator or prove the change, report or receipt is truthful."
        ),
    }
    return files, packet


def publish_packet(
    out_dir: str,
    files: dict[str, bytes],
    packet: dict[str, Any],
    *,
    writer: Callable[[str, bytes], None] = atomic_write_bytes,
) -> str:
    """Create a packet transaction; clean every partial output on failure."""
    destination = os.path.abspath(out_dir)
    packet_path = os.path.join(destination, PACKET_FILENAME)
    targets = [os.path.join(destination, name) for name in files] + [packet_path]
    existing = [path for path in targets if os.path.lexists(path)]
    if existing:
        raise FileExistsError(
            "scorer packet v2 is create-once; existing target(s): "
            + ", ".join(existing)
        )
    os.makedirs(destination, exist_ok=True)
    published: list[str] = []
    try:
        for name, payload in files.items():
            path = os.path.join(destination, name)
            writer(path, payload)
            published.append(path)
        writer(packet_path, _json_bytes(packet))
        published.append(packet_path)
    except BaseException:
        for path in reversed(published):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        raise
    return packet_path


def run_bytes(argv: list[str]) -> bytes:
    completed = subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "MSYS_NO_PATHCONV": "1"},
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(
            f"command failed ({completed.returncode}): {argv!r}: {detail}"
        )
    return completed.stdout


def docker_exec(container: str, argv: list[str], *, workdir: str) -> bytes:
    return run_bytes(
        [
            "docker",
            "exec",
            "-u",
            "65532:65532",
            "-e",
            "HOME=/work",
            "-w",
            workdir,
            container,
            *argv,
        ]
    )


def capture_container_state(
    *,
    container: str,
    baseline_commit: str,
    receipt_container_path: str,
) -> dict[str, Any]:
    container_id = run_bytes(
        ["docker", "inspect", "-f", "{{.Id}}", container]
    ).decode("ascii", "strict").strip()
    state = run_bytes(
        ["docker", "inspect", "-f", "{{.State.Status}}", container]
    ).decode("ascii", "strict").strip()
    if state != "running":
        raise RuntimeError(f"container is not running: {state!r}")
    output_commit = docker_exec(
        container, ["git", "rev-parse", "HEAD"], workdir="/work/repo"
    ).decode("ascii", "strict").strip()
    docker_exec(
        container,
        ["git", "cat-file", "-e", f"{baseline_commit}^{{commit}}"],
        workdir="/work/repo",
    )
    docker_exec(
        container,
        ["git", "merge-base", "--is-ancestor", baseline_commit, output_commit],
        workdir="/work/repo",
    )
    return {
        "container_name": container,
        "container_id": container_id,
        "baseline_commit": baseline_commit,
        "output_commit": output_commit,
        "receipt_container_path": receipt_container_path,
        "result_bytes": docker_exec(
            container, ["cat", "/work/out/result.json"], workdir="/work"
        ),
        "diff_bytes": docker_exec(
            container,
            [
                "git",
                "diff",
                "--binary",
                "--no-ext-diff",
                "--no-renames",
                baseline_commit,
                output_commit,
                "--",
            ],
            workdir="/work/repo",
        ),
        "status_bytes": docker_exec(
            container,
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            workdir="/work/repo",
        ),
        "tracked_paths_bytes": docker_exec(
            container,
            [
                "git",
                "diff",
                "--name-only",
                "--no-renames",
                baseline_commit,
                output_commit,
                "--",
            ],
            workdir="/work/repo",
        ),
        "receipt_bytes": docker_exec(
            container, ["cat", receipt_container_path], workdir="/work"
        ),
    }


def _read_packet_artifacts(
    packet_path: str, packet: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, bool], list[str]]:
    checks = {
        "required_artifact_set_is_exact": False,
        "artifact_paths_are_fixed_and_confined": False,
        "all_artifacts_exist": False,
        "artifact_byte_counts_match": False,
        "artifact_digests_match": False,
    }
    errors: list[str] = []
    payloads: dict[str, bytes] = {}
    packet_dir = os.path.dirname(os.path.abspath(packet_path))
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts is not an object")
        return payloads, checks, errors
    checks["required_artifact_set_is_exact"] = set(artifacts) == REQUIRED_ARTIFACTS
    paths_ok = exists_ok = bytes_ok = digest_ok = True
    for key, expected_name in ARTIFACT_FILES.items():
        metadata = artifacts.get(key)
        if not isinstance(metadata, dict) or metadata.get("path") != expected_name:
            paths_ok = exists_ok = bytes_ok = digest_ok = False
            continue
        candidate = os.path.abspath(os.path.join(packet_dir, expected_name))
        if (
            os.path.dirname(candidate) != packet_dir
            or os.path.islink(candidate)
            or not os.path.isfile(candidate)
        ):
            paths_ok = False
            exists_ok = False
            bytes_ok = False
            digest_ok = False
            continue
        try:
            with open(candidate, "rb") as handle:
                payload = handle.read()
        except OSError as exc:
            exists_ok = bytes_ok = digest_ok = False
            errors.append(f"{key} missing or unreadable: {exc}")
            continue
        payloads[key] = payload
        bytes_ok = bytes_ok and metadata.get("bytes") == len(payload)
        digest_ok = digest_ok and metadata.get("sha256") == sha256(payload)
    checks["artifact_paths_are_fixed_and_confined"] = paths_ok
    checks["all_artifacts_exist"] = exists_ok and len(payloads) == len(ARTIFACT_FILES)
    checks["artifact_byte_counts_match"] = bytes_ok
    checks["artifact_digests_match"] = digest_ok
    return payloads, checks, errors


def verify_packet(
    packet_path: str,
    *,
    expected_run_id: str,
    expected_baseline_commit: str,
    expected_output_commit: str,
    expected_container_id: str,
    observed_state: dict[str, Any] | None,
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "packet_is_valid_json_object": False,
        "schema_version_matches": False,
        "run_id_matches": False,
        "baseline_commit_matches": False,
        "output_commit_matches": False,
        "container_id_matches": False,
        "receipt_container_path_is_fixed": False,
        "required_artifact_set_is_exact": False,
        "artifact_paths_are_fixed_and_confined": False,
        "all_artifacts_exist": False,
        "artifact_byte_counts_match": False,
        "artifact_digests_match": False,
        "worktree_status_is_clean": False,
        "result_json_is_parseable_object": False,
        "receipt_links_output_commit": False,
        "tracked_inventory_matches_diff": False,
        "manifest_inventory_matches_captured_files": False,
        "core_scorer_inputs_are_exact": False,
        "live_container_binding_present": observed_state is not None,
        "live_container_identity_matches": False,
        "live_commit_identity_matches": False,
        "live_artifact_bytes_match": False,
    }
    errors: list[str] = []
    try:
        with open(packet_path, "rb") as handle:
            packet_bytes = handle.read()
        packet = _load_json_object(packet_bytes, "packet")
        checks["packet_is_valid_json_object"] = True
    except (OSError, ValueError) as exc:
        errors.append(f"packet load failed: {exc}")
        return {
            "status": "FAIL",
            "checks": checks,
            "errors": errors,
            "claim_boundary": "No claim is valid when the packet manifest cannot be loaded.",
        }

    checks["schema_version_matches"] = packet.get("schema_version") == SCHEMA_VERSION
    checks["run_id_matches"] = packet.get("run_id") == expected_run_id
    checks["baseline_commit_matches"] = (
        packet.get("baseline_commit") == expected_baseline_commit
    )
    checks["output_commit_matches"] = (
        packet.get("output_commit") == expected_output_commit
    )
    container = packet.get("container")
    checks["container_id_matches"] = (
        isinstance(container, dict)
        and container.get("id") == expected_container_id
    )
    checks["receipt_container_path_is_fixed"] = (
        packet.get("receipt_container_path") == DEFAULT_RECEIPT_CONTAINER_PATH
    )

    payloads, artifact_checks, artifact_errors = _read_packet_artifacts(
        packet_path, packet
    )
    checks.update(artifact_checks)
    errors.extend(artifact_errors)
    checks["worktree_status_is_clean"] = payloads.get("status") == b""
    try:
        checks["result_json_is_parseable_object"] = isinstance(
            _load_json_object(payloads["result"], "result.json"), dict
        )
    except (KeyError, ValueError):
        pass
    try:
        receipt = _load_json_object(payloads["receipt"], "producer receipt")
        checks["receipt_links_output_commit"] = (
            receipt.get("linked_commit") == expected_output_commit
            and receipt.get("linked_commit") == packet.get("output_commit")
        )
    except (KeyError, ValueError):
        pass
    tracked_paths: list[str] = []
    try:
        tracked_paths = _parse_paths(payloads["tracked_paths"])
        diff_payload = payloads["diff"]
        checks["tracked_inventory_matches_diff"] = bool(tracked_paths) and all(
            f"diff --git a/{path} b/{path}".encode("utf-8") in diff_payload
            for path in tracked_paths
        )
    except (KeyError, ValueError):
        pass
    workspace = packet.get("workspace")
    checks["manifest_inventory_matches_captured_files"] = (
        isinstance(workspace, dict)
        and workspace.get("clean") is True
        and workspace.get("tracked_changed_files") == tracked_paths
    )
    checks["core_scorer_inputs_are_exact"] = (
        packet.get("scorer_input_core") == ["result", "diff"]
        and packet.get("handoff_attachments_required")
        == ["test_log", "validator_output"]
    )

    if observed_state is not None:
        checks["live_container_identity_matches"] = (
            observed_state.get("container_id") == expected_container_id
            and observed_state.get("container_name")
            == (container.get("name") if isinstance(container, dict) else None)
        )
        checks["live_commit_identity_matches"] = (
            observed_state.get("baseline_commit") == expected_baseline_commit
            and observed_state.get("output_commit") == expected_output_commit
            and observed_state.get("receipt_container_path")
            == packet.get("receipt_container_path")
        )
        observed_map = {
            "result": observed_state.get("result_bytes"),
            "diff": observed_state.get("diff_bytes"),
            "status": observed_state.get("status_bytes"),
            "tracked_paths": observed_state.get("tracked_paths_bytes"),
            "receipt": observed_state.get("receipt_bytes"),
        }
        checks["live_artifact_bytes_match"] = all(
            isinstance(observed_map[key], bytes)
            and payloads.get(key) == observed_map[key]
            for key in ARTIFACT_FILES
        )

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "errors": errors,
        "packet_sha256": sha256(packet_bytes),
        "run_id": packet.get("run_id"),
        "baseline_commit": packet.get("baseline_commit"),
        "output_commit": packet.get("output_commit"),
        "container_id": container.get("id") if isinstance(container, dict) else None,
        "tracked_changed_files": tracked_paths,
        "claim_boundary": (
            "PASS proves internal packet integrity plus equality with bytes re-read "
            "from the named running container. It does not authenticate the "
            "operator or establish semantic correctness."
        ),
    }


def capture(
    *,
    container: str,
    run_id: str,
    baseline_commit: str,
    receipt_container_path: str,
    out_dir: str,
) -> str:
    observed = capture_container_state(
        container=container,
        baseline_commit=baseline_commit,
        receipt_container_path=receipt_container_path,
    )
    files, packet = build_packet(
        run_id=run_id,
        captured_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **observed,
    )
    return publish_packet(out_dir, files, packet)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--container", required=True)
    capture_parser.add_argument("--run-id", required=True)
    capture_parser.add_argument("--baseline-commit", required=True)
    capture_parser.add_argument(
        "--receipt-container-path",
        default=DEFAULT_RECEIPT_CONTAINER_PATH,
    )
    capture_parser.add_argument("--out-dir", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--packet", required=True)
    verify_parser.add_argument("--container", required=True)
    verify_parser.add_argument("--expected-run-id", required=True)
    verify_parser.add_argument("--expected-baseline-commit", required=True)
    verify_parser.add_argument("--expected-output-commit", required=True)
    verify_parser.add_argument("--expected-container-id", required=True)
    verify_parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    if args.command == "capture":
        packet_path = capture(
            container=args.container,
            run_id=args.run_id,
            baseline_commit=args.baseline_commit,
            receipt_container_path=args.receipt_container_path,
            out_dir=args.out_dir,
        )
        print(f"wrote scorer packet v2: {packet_path}")
        return 0

    with open(args.packet, encoding="utf-8") as handle:
        packet = json.load(handle)
    observed = capture_container_state(
        container=args.container,
        baseline_commit=args.expected_baseline_commit,
        receipt_container_path=packet.get("receipt_container_path", ""),
    )
    result = verify_packet(
        args.packet,
        expected_run_id=args.expected_run_id,
        expected_baseline_commit=args.expected_baseline_commit,
        expected_output_commit=args.expected_output_commit,
        expected_container_id=args.expected_container_id,
        observed_state=observed,
    )
    atomic_write_bytes(args.json_out, _json_bytes(result))
    for name, passed in result["checks"].items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"---\n{result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
