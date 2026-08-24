#!/usr/bin/env python3
"""Materialize an explicitly bounded projection directly from Git blobs.

This module intentionally uses Git object semantics.  It never calls checkout,
archive, show, or a working-tree conversion API.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any, Iterable


class MaterializationError(RuntimeError):
    """Closed failure from the raw-object boundary."""


def _run_git(git: Path, repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    completed = subprocess.run(
        [str(git), "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise MaterializationError(
            f"GIT_COMMAND_FAILED:rc={completed.returncode}:args={args!r}:stderr={stderr}"
        )
    return completed.stdout


def _read_blobs_batch(git: Path, repo: Path, oids: list[str]) -> dict[str, bytes]:
    if not oids:
        return {}
    completed = subprocess.run(
        [
            str(git),
            "-c",
            f"safe.directory={repo.as_posix()}",
            "-C",
            str(repo),
            "cat-file",
            "--batch",
        ],
        input=("\n".join(oids) + "\n").encode("ascii"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise MaterializationError(f"GIT_CAT_FILE_BATCH_FAILED:{stderr}")
    stream = io.BytesIO(completed.stdout)
    blobs: dict[str, bytes] = {}
    for requested_oid in oids:
        header = stream.readline().rstrip(b"\n")
        try:
            actual_oid_raw, kind, size_raw = header.split(b" ")
            actual_oid = actual_oid_raw.decode("ascii")
            size = int(size_raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise MaterializationError(f"MALFORMED_CAT_FILE_BATCH_HEADER:{header!r}") from exc
        if actual_oid != requested_oid or kind != b"blob":
            raise MaterializationError(
                f"CAT_FILE_BATCH_BINDING:requested={requested_oid}:actual={actual_oid}:type={kind!r}"
            )
        data = stream.read(size)
        separator = stream.read(1)
        if len(data) != size or separator != b"\n":
            raise MaterializationError(f"TRUNCATED_CAT_FILE_BATCH_OBJECT:{requested_oid}")
        blobs[requested_oid] = data
    if stream.read(1) != b"":
        raise MaterializationError("CAT_FILE_BATCH_TRAILING_OUTPUT")
    return blobs


def _decode_path(raw: bytes) -> str:
    try:
        value = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise MaterializationError("NON_UTF8_GIT_PATH") from exc
    posix = PurePosixPath(value)
    if (
        not value
        or posix.is_absolute()
        or any(part in {"", ".", ".."} for part in posix.parts)
        or "\\" in value
        or any(":" in part for part in posix.parts)
    ):
        raise MaterializationError(f"UNSAFE_GIT_PATH:{value!r}")
    return value


def list_entries(
    *, git: Path, repo: Path, commit: str, paths: Iterable[str] | None = None
) -> list[dict[str, str]]:
    args = ["ls-tree", "-rz", "--full-tree", commit]
    selected = list(paths or [])
    if selected:
        args.extend(["--", *selected])
    output = _run_git(git, repo, *args)
    entries: list[dict[str, str]] = []
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as exc:
            raise MaterializationError("MALFORMED_LS_TREE_RECORD") from exc
        entries.append(
            {"mode": mode, "type": kind, "oid": oid, "path": _decode_path(raw_path)}
        )
    entries.sort(key=lambda item: item["path"])
    if selected:
        actual = {item["path"] for item in entries}
        expected = set(selected)
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise MaterializationError(
                f"SELECTED_PATH_SET_MISMATCH:missing={missing!r}:unexpected={unexpected!r}"
            )
    return entries


def _safe_target(destination: Path, git_path: str) -> Path:
    target = destination.joinpath(*PurePosixPath(git_path).parts)
    root = destination.resolve()
    resolved_parent = target.parent.resolve()
    try:
        resolved_parent.relative_to(root)
    except ValueError as exc:
        raise MaterializationError(f"DESTINATION_ESCAPE:{git_path!r}") from exc
    return target


def _require_empty_directory(destination: Path) -> None:
    if destination.exists():
        if not destination.is_dir():
            raise MaterializationError(f"DESTINATION_NOT_DIRECTORY:{destination}")
        if any(destination.iterdir()):
            raise MaterializationError(f"DESTINATION_NOT_EMPTY:{destination}")
    else:
        destination.mkdir(parents=True)


def materialize(
    *,
    git: Path,
    repo: Path,
    commit: str,
    destination: Path,
    paths: Iterable[str] | None = None,
    allowed_gitlinks: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Write only 100644 blobs and record explicitly allowed 160000 gitlinks."""

    destination = destination.resolve()
    _require_empty_directory(destination)
    allowed = dict(allowed_gitlinks or {})
    entries = list_entries(git=git, repo=repo, commit=commit, paths=paths)
    blob_oids = [
        entry["oid"]
        for entry in entries
        if entry["mode"] == "100644" and entry["type"] == "blob"
    ]
    blobs = _read_blobs_batch(git, repo, blob_oids)
    inventory: list[dict[str, Any]] = []
    observed_gitlinks: dict[str, str] = {}

    for entry in entries:
        path = entry["path"]
        mode = entry["mode"]
        kind = entry["type"]
        oid = entry["oid"]
        target = _safe_target(destination, path)

        if mode == "100644" and kind == "blob":
            data = blobs[oid]
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise MaterializationError(f"TARGET_ALREADY_EXISTS:{path}")
            target.write_bytes(data)
            persisted = target.read_bytes()
            if persisted != data:
                raise MaterializationError(f"POST_WRITE_BYTE_MISMATCH:{path}")
            inventory.append(
                {
                    **entry,
                    "disposition": "MATERIALIZED_RAW_BLOB",
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                }
            )
            continue

        if mode == "160000" and kind == "commit":
            expected_oid = allowed.get(path)
            if expected_oid != oid:
                raise MaterializationError(
                    f"UNAUTHORIZED_GITLINK:{path}:expected={expected_oid}:actual={oid}"
                )
            if target.exists():
                raise MaterializationError(f"GITLINK_DESTINATION_PRESENT:{path}")
            observed_gitlinks[path] = oid
            inventory.append(
                {
                    **entry,
                    "disposition": "RECORDED_NOT_MATERIALIZED",
                    "sha256": None,
                    "bytes": None,
                }
            )
            continue

        raise MaterializationError(
            f"UNSUPPORTED_GIT_ENTRY:{path}:mode={mode}:type={kind}:oid={oid}"
        )

    if observed_gitlinks != allowed:
        raise MaterializationError(
            f"GITLINK_SET_MISMATCH:expected={allowed!r}:actual={observed_gitlinks!r}"
        )

    materialized = [item for item in inventory if item["disposition"] == "MATERIALIZED_RAW_BLOB"]
    return {
        "schema": "raw-git-object-materialization.v1",
        "repository": str(repo.resolve()),
        "commit": commit,
        "destination": str(destination),
        "object_semantics": "git ls-tree + git cat-file blob",
        "working_tree_conversion_used": False,
        "entry_count": len(inventory),
        "materialized_blob_count": len(materialized),
        "recorded_gitlink_count": len(observed_gitlinks),
        "inventory": inventory,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _load_json(path: Path | None, fallback: Any) -> Any:
    if path is None:
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--paths-json", type=Path)
    parser.add_argument("--allowed-gitlinks-json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        record = materialize(
            git=args.git,
            repo=args.repo,
            commit=args.commit,
            destination=args.destination,
            paths=_load_json(args.paths_json, None),
            allowed_gitlinks=_load_json(args.allowed_gitlinks_json, {}),
        )
        write_json(args.output, {**record, "status": "PASS"})
        return 0
    except Exception as exc:  # terminal caller needs one closed error surface
        failure = {
            "schema": "raw-git-object-materialization.v1",
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(args.output, failure)
        print(f"RAW_OBJECT_MATERIALIZATION_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
