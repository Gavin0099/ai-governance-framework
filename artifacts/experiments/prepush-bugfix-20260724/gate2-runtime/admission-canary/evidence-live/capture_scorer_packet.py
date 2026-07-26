#!/usr/bin/env python3
"""Capture an operator-owned, byte-attested packet for the blind scorer.

The packet is the commit marker for a small evidence transaction. Component
files are written atomically first; ``scorer-packet.json`` is written last.
Without that final manifest, a partial capture is not a valid scorer packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Callable

from evidence_io import atomic_write_bytes


SCHEMA_VERSION = "1.0"
ARTIFACT_FILES = {
    "result": "result.json",
    "diff": "final-diff.patch",
    "status": "final-status.txt",
    "tracked_paths": "final-tracked-paths.txt",
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_status(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8", "strict")
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        if not line:
            continue
        if len(line) < 4 or line[2] != " ":
            raise ValueError(f"unsupported porcelain-v1 status line: {line!r}")
        code, path = line[:2], line[3:]
        if not path or " -> " in path:
            raise ValueError(
                "renames and empty paths are outside the canary packet contract"
            )
        item = (code, path)
        if item in seen:
            raise ValueError(f"duplicate status entry: {line!r}")
        seen.add(item)
        entries.append({"code": code, "path": path})
    return entries


def parse_paths(payload: bytes) -> list[str]:
    paths = [line for line in payload.decode("utf-8", "strict").splitlines() if line]
    if len(paths) != len(set(paths)):
        raise ValueError("tracked path list contains duplicates")
    return sorted(paths)


def _artifact(path: str, payload: bytes, role: str) -> dict:
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
    baseline_head: str,
    result_bytes: bytes,
    diff_bytes: bytes,
    status_bytes: bytes,
    tracked_paths_bytes: bytes,
    captured_at: str,
) -> tuple[dict[str, bytes], dict]:
    """Validate captured bytes and build the manifest without writing files."""
    if not run_id:
        raise ValueError("run_id is required")
    if not container_name or not container_id:
        raise ValueError("container identity is required")
    if not baseline_head:
        raise ValueError("baseline HEAD is required")
    try:
        result_json = json.loads(result_bytes.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("result.json must be valid UTF-8 JSON") from exc
    if not isinstance(result_json, dict):
        raise ValueError("result.json must contain a JSON object")
    if not diff_bytes:
        raise ValueError("final diff is empty")

    status_entries = parse_status(status_bytes)
    tracked_paths = parse_paths(tracked_paths_bytes)
    if not tracked_paths:
        raise ValueError("no tracked changed file was captured")
    tracked_from_status = sorted(
        entry["path"] for entry in status_entries if entry["code"] != "??"
    )
    if tracked_paths != tracked_from_status:
        raise ValueError(
            "tracked path list does not match tracked porcelain status entries"
        )
    for path in tracked_paths:
        header = f"diff --git a/{path} b/{path}".encode("utf-8")
        if header not in diff_bytes:
            raise ValueError(f"final diff omits tracked changed file: {path}")

    untracked_paths = sorted(
        entry["path"] for entry in status_entries if entry["code"] == "??"
    )
    files = {
        ARTIFACT_FILES["result"]: result_bytes,
        ARTIFACT_FILES["diff"]: diff_bytes,
        ARTIFACT_FILES["status"]: status_bytes,
        ARTIFACT_FILES["tracked_paths"]: tracked_paths_bytes,
    }
    packet = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "captured_at": captured_at,
        "container": {"name": container_name, "id": container_id},
        "baseline_head": baseline_head,
        "artifacts": {
            "result": _artifact(
                ARTIFACT_FILES["result"], result_bytes, "producer_self_report"
            ),
            "diff": _artifact(
                ARTIFACT_FILES["diff"], diff_bytes, "operator_captured_ground_truth"
            ),
            "status": _artifact(
                ARTIFACT_FILES["status"], status_bytes, "workspace_inventory_source"
            ),
            "tracked_paths": _artifact(
                ARTIFACT_FILES["tracked_paths"],
                tracked_paths_bytes,
                "tracked_change_inventory",
            ),
        },
        "workspace": {
            "status_entries": status_entries,
            "tracked_changed_files": tracked_paths,
            "untracked_files": untracked_paths,
        },
        "scorer_inputs": ["result", "diff"],
        "claim_boundary": (
            "The packet proves byte equality and makes the producer report plus "
            "the operator-captured final diff available to the scorer. It does "
            "not prove the report is truthful, the change is good, or the "
            "manifest was written by an independent trusted party."
        ),
    }
    return files, packet


def write_packet(
    out_dir: str,
    files: dict[str, bytes],
    packet: dict,
    *,
    writer: Callable[[str, bytes], None] = atomic_write_bytes,
) -> str:
    """Write components atomically and the packet manifest last."""
    destination = os.path.abspath(out_dir)
    packet_path = os.path.join(destination, "scorer-packet.json")
    targets = [os.path.join(destination, name) for name in files] + [packet_path]
    existing = [path for path in targets if os.path.exists(path)]
    if existing:
        raise FileExistsError(
            "scorer packet capture is create-once; existing target(s): "
            + ", ".join(existing)
        )
    os.makedirs(destination, exist_ok=True)
    for name, payload in files.items():
        writer(os.path.join(destination, name), payload)
    packet_bytes = (
        json.dumps(packet, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    writer(packet_path, packet_bytes)
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


def capture(container: str, run_id: str, out_dir: str) -> str:
    container_id = run_bytes(
        ["docker", "inspect", "-f", "{{.Id}}", container]
    ).decode("ascii", "strict").strip()
    state = run_bytes(
        ["docker", "inspect", "-f", "{{.State.Status}}", container]
    ).decode("ascii", "strict").strip()
    if state != "running":
        raise RuntimeError(f"container is not running: {state!r}")
    head = docker_exec(
        container, ["git", "rev-parse", "HEAD"], workdir="/work/repo"
    ).decode("ascii", "strict").strip()
    result_bytes = docker_exec(
        container, ["cat", "/work/out/result.json"], workdir="/work"
    )
    diff_bytes = docker_exec(
        container,
        ["git", "diff", "--binary", "--no-ext-diff", "--no-renames", "HEAD", "--"],
        workdir="/work/repo",
    )
    status_bytes = docker_exec(
        container,
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        workdir="/work/repo",
    )
    tracked_paths_bytes = docker_exec(
        container,
        ["git", "diff", "--name-only", "--no-renames", "HEAD", "--"],
        workdir="/work/repo",
    )
    files, packet = build_packet(
        run_id=run_id,
        container_name=container,
        container_id=container_id,
        baseline_head=head,
        result_bytes=result_bytes,
        diff_bytes=diff_bytes,
        status_bytes=status_bytes,
        tracked_paths_bytes=tracked_paths_bytes,
        captured_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    return write_packet(out_dir, files, packet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--container",
        default=os.environ.get("GATE2_CANARY_CONTAINER"),
        required=os.environ.get("GATE2_CANARY_CONTAINER") is None,
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    packet_path = capture(args.container, args.run_id, args.out_dir)
    with open(packet_path, encoding="utf-8") as handle:
        packet = json.load(handle)
    print(f"wrote scorer packet: {packet_path}")
    print(f"  baseline: {packet['baseline_head']}")
    print(f"  tracked : {packet['workspace']['tracked_changed_files']}")
    print(f"  scorer  : {packet['scorer_inputs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
