#!/usr/bin/env python3
"""Synthetic proof for the attempt-03 raw-object boundary."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

from raw_git_materialize import MaterializationError, materialize, write_json


def run(command: list[str], cwd: Path, *, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        command,
        cwd=cwd,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"COMMAND_FAILED:{command!r}:rc={result.returncode}:"
            f"stderr={result.stderr.decode('utf-8', 'replace')}"
        )
    return result.stdout


def git(git_path: Path, repo: Path, *args: str, data: bytes | None = None) -> bytes:
    return run([str(git_path), "-c", f"safe.directory={repo.as_posix()}", *args], repo, data=data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="c1-a03-raw-git-selftest-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(args.git, repo, "init", "-q")
        git(args.git, repo, "config", "user.email", "probe@example.invalid")
        git(args.git, repo, "config", "user.name", "Raw Object Probe")
        git(args.git, repo, "config", "core.autocrlf", "true")

        attributes = b"eol-trigger.txt text eol=crlf\n*.bin -text\n"
        eol_blob = b"alpha\nbeta\n"
        binary_blob = b"\x00\xff\r\n\x80binary\x00"
        nested_blob = "snowman=\u2603\n".encode("utf-8")
        (repo / ".gitattributes").write_bytes(attributes)
        (repo / "eol-trigger.txt").write_bytes(eol_blob)
        (repo / "binary.bin").write_bytes(binary_blob)
        (repo / "nested").mkdir()
        (repo / "nested" / "utf8.txt").write_bytes(nested_blob)
        git(args.git, repo, "add", "--", ".gitattributes", "eol-trigger.txt", "binary.bin", "nested/utf8.txt")
        git(args.git, repo, "commit", "-q", "-m", "synthetic raw object fixture")
        commit = git(args.git, repo, "rev-parse", "HEAD").decode("ascii").strip()

        eol_oid = git(args.git, repo, "rev-parse", "HEAD:eol-trigger.txt").decode("ascii").strip()
        committed_eol = git(args.git, repo, "cat-file", "blob", eol_oid)
        if committed_eol != eol_blob:
            raise AssertionError("SYNTHETIC_COMMITTED_EOL_FIXTURE_UNEXPECTED")

        archive_bytes = git(args.git, repo, "archive", "--format=tar", "HEAD")
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            member = archive.extractfile("eol-trigger.txt")
            if member is None:
                raise AssertionError("ARCHIVE_EOL_MEMBER_MISSING")
            archived_eol = member.read()
        if archived_eol == committed_eol or b"\r\n" not in archived_eol:
            raise AssertionError("SYNTHETIC_ARCHIVE_DID_NOT_EXERCISE_EOL_CONVERSION")

        destination = root / "materialized"
        record = materialize(
            git=args.git,
            repo=repo,
            commit=commit,
            destination=destination,
        )
        expected = {
            ".gitattributes": attributes,
            "eol-trigger.txt": eol_blob,
            "binary.bin": binary_blob,
            "nested/utf8.txt": nested_blob,
        }
        for relative, wanted in expected.items():
            actual = destination.joinpath(*relative.split("/")).read_bytes()
            if actual != wanted:
                raise AssertionError(f"RAW_BYTES_MISMATCH:{relative}")

        gitlink_destination = root / "gitlink-projection"
        git(args.git, repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},linked-framework")
        git(args.git, repo, "commit", "-q", "-m", "add synthetic gitlink")
        gitlink_commit = git(args.git, repo, "rev-parse", "HEAD").decode("ascii").strip()
        gitlink_record = materialize(
            git=args.git,
            repo=repo,
            commit=gitlink_commit,
            destination=gitlink_destination,
            allowed_gitlinks={"linked-framework": commit},
        )
        if (gitlink_destination / "linked-framework").exists():
            raise AssertionError("GITLINK_WAS_MATERIALIZED")

        unsupported_oid = git(args.git, repo, "hash-object", "-w", "--stdin", data=b"target\n").decode("ascii").strip()
        git(args.git, repo, "update-index", "--add", "--cacheinfo", f"120000,{unsupported_oid},unsupported-link")
        git(args.git, repo, "commit", "-q", "-m", "add unsupported symlink")
        unsupported_failed_closed = False
        try:
            materialize(
                git=args.git,
                repo=repo,
                commit="HEAD",
                destination=root / "unsupported-projection",
                allowed_gitlinks={"linked-framework": commit},
            )
        except MaterializationError as exc:
            unsupported_failed_closed = str(exc).startswith("UNSUPPORTED_GIT_ENTRY:unsupported-link:")
        if not unsupported_failed_closed:
            raise AssertionError("UNSUPPORTED_MODE_DID_NOT_FAIL_CLOSED")

        output = {
            "schema": "c1-stryker-sidecar-raw-materializer-self-test.v1",
            "status": "PASS",
            "git_commit": commit,
            "eol_attribute_fixture": {
                "blob_oid": eol_oid,
                "cat_file_sha256": hashlib.sha256(committed_eol).hexdigest(),
                "cat_file_bytes": len(committed_eol),
                "archive_sha256": hashlib.sha256(archived_eol).hexdigest(),
                "archive_bytes": len(archived_eol),
                "archive_differs_from_cat_file": archived_eol != committed_eol,
                "materialized_equals_cat_file": (destination / "eol-trigger.txt").read_bytes() == committed_eol,
            },
            "binary_bytes_preserved": (destination / "binary.bin").read_bytes() == binary_blob,
            "nested_utf8_bytes_preserved": (destination / "nested" / "utf8.txt").read_bytes() == nested_blob,
            "materialized_blob_count": record["materialized_blob_count"],
            "gitlink_policy": {
                "recorded_count": gitlink_record["recorded_gitlink_count"],
                "destination_absent": not (gitlink_destination / "linked-framework").exists(),
            },
            "unsupported_mode_failed_closed": unsupported_failed_closed,
        }
        write_json(args.output, output)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RAW_MATERIALIZER_SELF_TEST_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise
