#!/usr/bin/env python3
"""Derive deterministic Stryker line ranges from two sibling source trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SCHEMA = "c1-stryker-diff-ranges.v1"
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
SAFE_ROLE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
PRODUCTION_ROOTS = ("src", "lib", "app", "packages")
MUTATABLE_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs", ".cts")
EXCLUDED_SEGMENTS = {"__tests__", "test", "tests", "fixtures", "generated"}
EXCLUDED_NAME_MARKERS = (".test.", ".spec.", ".fixture.", ".generated.")


class RangeDerivationError(RuntimeError):
    """A fail-closed diff or path condition prevented range derivation."""


@dataclass(frozen=True)
class ChangedRange:
    path: str
    start: int
    end: int


def _is_mutatable_production_path(relative_path: str) -> bool:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    if path.parts[0] not in PRODUCTION_ROOTS:
        return False
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & EXCLUDED_SEGMENTS:
        return False
    lowered_name = path.name.lower()
    if any(marker in lowered_name for marker in EXCLUDED_NAME_MARKERS):
        return False
    return lowered_name.endswith(MUTATABLE_SUFFIXES)


def _merge_ranges(ranges: list[ChangedRange]) -> list[ChangedRange]:
    merged: list[ChangedRange] = []
    for item in sorted(ranges, key=lambda value: (value.path, value.start, value.end)):
        if merged and merged[-1].path == item.path and item.start <= merged[-1].end + 1:
            previous = merged[-1]
            merged[-1] = ChangedRange(previous.path, previous.start, max(previous.end, item.end))
        else:
            merged.append(item)
    return merged


def _run_diff(baseline_root: Path, candidate_root: Path) -> bytes:
    if baseline_root.parent != candidate_root.parent:
        raise RangeDerivationError("ROOTS_NOT_SIBLINGS")
    if baseline_root == candidate_root:
        raise RangeDerivationError("ROOTS_IDENTICAL")
    if not SAFE_ROLE_RE.fullmatch(baseline_root.name) or not SAFE_ROLE_RE.fullmatch(candidate_root.name):
        raise RangeDerivationError("UNSAFE_ROLE_NAME")

    command = [
        "git",
        "diff",
        "--no-index",
        "--unified=0",
        "--no-renames",
        "--",
        baseline_root.name,
        candidate_root.name,
    ]
    completed = subprocess.run(
        command,
        cwd=baseline_root.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        raise RangeDerivationError("NO_DIFF")
    if completed.returncode != 1:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RangeDerivationError(f"GIT_DIFF_FAILED:{completed.returncode}:{detail}")
    return completed.stdout


def derive_ranges(baseline_root: Path, candidate_root: Path) -> dict[str, object]:
    baseline_root = baseline_root.resolve(strict=True)
    candidate_root = candidate_root.resolve(strict=True)
    diff_bytes = _run_diff(baseline_root, candidate_root)
    diff_text = diff_bytes.decode("utf-8", errors="strict")
    candidate_prefix = f"b/{candidate_root.name}/"

    current_path: str | None = None
    changed_paths: set[str] = set()
    excluded_paths: set[str] = set()
    ranges: list[ChangedRange] = []

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            marker = line[4:]
            if marker == "/dev/null":
                current_path = None
                continue
            if not marker.startswith(candidate_prefix):
                raise RangeDerivationError(f"UNEXPECTED_CANDIDATE_PATH:{marker}")
            current_path = marker[len(candidate_prefix) :]
            changed_paths.add(current_path)
            if not _is_mutatable_production_path(current_path):
                excluded_paths.add(current_path)
            continue

        match = HUNK_RE.match(line)
        if not match or current_path is None:
            continue
        new_start = int(match.group(1))
        new_count = int(match.group(2) or "1")
        if new_count == 0:
            continue
        if not _is_mutatable_production_path(current_path):
            continue
        candidate_file = candidate_root / PurePosixPath(current_path)
        if not candidate_file.is_file():
            raise RangeDerivationError(f"CANDIDATE_FILE_MISSING:{current_path}")
        line_count = len(candidate_file.read_bytes().splitlines())
        new_end = new_start + new_count - 1
        if new_start < 1 or new_end > line_count:
            raise RangeDerivationError(
                f"RANGE_OUTSIDE_CANDIDATE:{current_path}:{new_start}-{new_end}:{line_count}"
            )
        ranges.append(ChangedRange(current_path, new_start, new_end))

    merged = _merge_ranges(ranges)
    if not merged:
        raise RangeDerivationError("NO_MUTATABLE_CHANGED_PRODUCTION_LINES")

    return {
        "schema": SCHEMA,
        "baseline_role": baseline_root.name,
        "candidate_role": candidate_root.name,
        "diff_sha256": hashlib.sha256(diff_bytes).hexdigest(),
        "mutate_ranges": [f"{item.path}:{item.start}-{item.end}" for item in merged],
        "included_files": sorted({item.path for item in merged}),
        "excluded_changed_paths": sorted(excluded_paths),
        "all_changed_paths": sorted(changed_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = derive_ranges(args.baseline_root, args.candidate_root)
        serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    except (OSError, UnicodeError, RangeDerivationError) as exc:
        print(f"range_derivation_error={exc}", file=sys.stderr)
        return 3

    print(f"range_output={args.output}")
    print(f"mutate_range_count={len(result['mutate_ranges'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
