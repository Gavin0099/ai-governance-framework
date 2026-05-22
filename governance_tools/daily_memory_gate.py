#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"(?i)\b(TODO|TBD|fill later)\b")
HEX_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
NA_ONLY_RE = re.compile(
    r"^\s*(branch|commits?|commit_hash|changed(_files)?(_summary)?|changed files summary|"
    r"test(_evidence)?|tests?\s*/\s*gates?|open(_risks)?|open risks|next_step)\s*:\s*(N/?A|n/?a)\s*$"
)


@dataclass
class GateResult:
    ok: bool
    code: str | None = None
    message: str | None = None


def _extract_added_lines_from_patch(patch_text: str) -> list[str]:
    lines: list[str] = []
    for raw in patch_text.splitlines():
        if raw.startswith("+++") or not raw.startswith("+"):
            continue
        lines.append(raw[1:])
    return lines


def _has_field(lines: list[str], pattern: str) -> bool:
    rx = re.compile(pattern)
    return any(rx.search(line) for line in lines)


def _extract_commit_refs(lines: list[str]) -> set[str]:
    refs: set[str] = set()
    for line in lines:
        for m in HEX_RE.findall(line):
            refs.add(m.lower())
    return refs


def validate_structural_traceability(
    *,
    added_lines: list[str],
    branch_name: str,
    outgoing_commit_hashes: list[str],
) -> GateResult:
    if not added_lines:
        return GateResult(False, "DAILY_MEMORY_MISSING_REQUIRED_SECTION", "no added lines in staged daily memory")

    for line in added_lines:
        if PLACEHOLDER_RE.search(line):
            return GateResult(False, "DAILY_MEMORY_PLACEHOLDER_PRESENT", f"placeholder token in line: {line}")
        if NA_ONLY_RE.search(line):
            return GateResult(False, "DAILY_MEMORY_PLACEHOLDER_PRESENT", f"N/A-only required section in line: {line}")

    required_ok = all(
        [
            _has_field(added_lines, r"^\s*branch\s*:"),
            _has_field(added_lines, r"^\s*commits?\s*:|^\s*commit_hash\s*:"),
            _has_field(added_lines, r"^\s*changed(_files)?(_summary)?\s*:|^\s*changed files summary\s*:"),
            _has_field(added_lines, r"^\s*test(_evidence)?\s*:|^\s*tests?\s*/\s*gates?\s*:"),
            _has_field(added_lines, r"^\s*open(_risks)?\s*:|^\s*open risks\s*:"),
            _has_field(added_lines, r"^\s*next_step\s*:"),
        ]
    )
    if not required_ok:
        return GateResult(
            False,
            "DAILY_MEMORY_MISSING_REQUIRED_SECTION",
            "required sections missing: branch, commits/commit_hash, changed files summary, tests/gates, open risks, next_step",
        )

    branch_lines = [line for line in added_lines if re.search(r"^\s*branch\s*:\s*", line)]
    if branch_lines:
        branch_val = re.sub(r"^\s*branch\s*:\s*", "", branch_lines[-1]).strip()
        if branch_val and branch_val != branch_name:
            return GateResult(
                False,
                "DAILY_MEMORY_MISSING_REQUIRED_SECTION",
                f"branch mismatch: expected={branch_name}, found={branch_val}",
            )

    outgoing_lower = [h.lower() for h in outgoing_commit_hashes if h.strip()]
    refs = _extract_commit_refs(added_lines)
    if outgoing_lower:
        if not refs:
            return GateResult(
                False,
                "DAILY_MEMORY_OUTGOING_COMMIT_NOT_DESCRIBED",
                "outgoing commits exist but daily memory references no commit hash",
            )
        for ref in refs:
            if not any(h.startswith(ref) for h in outgoing_lower):
                return GateResult(
                    False,
                    "DAILY_MEMORY_COMMIT_NOT_IN_OUTGOING_RANGE",
                    f"commit ref not found in outgoing range: {ref}",
                )

    return GateResult(True)


def _run_git(project_root: Path, *args: str) -> tuple[int, str]:
    cp = subprocess.run(
        ["git", *args],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return cp.returncode, cp.stdout


def _read_added_lines(project_root: Path, memory_path: str) -> list[str]:
    code, out = _run_git(project_root, "diff", "--cached", "--unified=0", "--", memory_path)
    if code != 0:
        return []
    return _extract_added_lines_from_patch(out)


def _read_outgoing_hashes(project_root: Path, branch: str) -> list[str]:
    code, upstream = _run_git(project_root, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    if code != 0 or not upstream.strip():
        return []
    code, hashes = _run_git(project_root, "rev-list", f"{upstream.strip()}..HEAD")
    if code != 0:
        return []
    return [x.strip() for x in hashes.splitlines() if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily Memory Gate v0.1 (structural traceability only)")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--memory-path", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    added = _read_added_lines(root, args.memory_path)
    outgoing = _read_outgoing_hashes(root, args.branch)
    result = validate_structural_traceability(
        added_lines=added,
        branch_name=args.branch,
        outgoing_commit_hashes=outgoing,
    )
    payload = {"ok": result.ok, "code": result.code, "message": result.message}
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if result.ok:
            print("[daily_memory_gate] ok")
        else:
            print(f"[daily_memory_gate] {result.code}: {result.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

