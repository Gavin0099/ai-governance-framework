#!/usr/bin/env python3
"""
High-signal public API manifest extraction and diff checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


C_SHARP_API_RE = re.compile(
    r"^\s*(?:public|protected\s+internal|public\s+partial)\s+.*$",
    re.MULTILINE,
)
CPP_API_RE = re.compile(
    r"^\s*(?:class|struct)\s+\w+|^\s*(?:virtual\s+)?(?:[\w:<>*&]+\s+)+\w+\s*\([^;{]*\)\s*(?:const)?\s*;",
    re.MULTILINE,
)
SWIFT_API_RE = re.compile(
    r"^\s*(?:public|open)\s+(?:class|struct|enum|protocol|func|var|let|actor)\b.*$",
    re.MULTILINE,
)


def _extract_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [match.group(0).strip() for match in pattern.finditer(text)]


def extract_public_api_manifest(file_paths: list[Path]) -> dict:
    entries: list[dict] = []

    for path in sorted(file_paths):
        suffix = path.suffix.lower()
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(path).replace("\\", "/")

        if suffix == ".cs":
            signatures = _extract_matches(text, C_SHARP_API_RE)
        elif suffix in {".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"}:
            signatures = _extract_matches(text, CPP_API_RE)
        elif suffix == ".swift":
            signatures = _extract_matches(text, SWIFT_API_RE)
        else:
            continue

        if signatures:
            entries.append({"path": rel_path, "signatures": signatures})

    return {"entries": entries}


def diff_public_api_manifests(before: dict, after: dict) -> dict:
    before_signatures = {
        signature
        for entry in before.get("entries", [])
        for signature in entry.get("signatures", [])
    }
    after_signatures = {
        signature
        for entry in after.get("entries", [])
        for signature in entry.get("signatures", [])
    }

    removed = sorted(before_signatures - after_signatures)
    added = sorted(after_signatures - before_signatures)

    warnings: list[str] = []
    errors: list[str] = []

    if removed:
        errors.append("Public API surface removed or changed.")
    if added:
        warnings.append("Public API surface added or changed.")

    return {
        "ok": len(errors) == 0,
        "removed": removed,
        "added": added,
        "warnings": warnings,
        "errors": errors,
    }


def check_public_api_diff(before_files: list[Path], after_files: list[Path]) -> dict:
    before_manifest = extract_public_api_manifest(before_files)
    after_manifest = extract_public_api_manifest(after_files)
    diff = diff_public_api_manifests(before_manifest, after_manifest)
    return {
        "ok": diff["ok"],
        "before_manifest": before_manifest,
        "after_manifest": after_manifest,
        "removed": diff["removed"],
        "added": diff["added"],
        "warnings": diff["warnings"],
        "errors": diff["errors"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and diff public API manifests.")
    parser.add_argument("--before", action="append", default=[], help="Path to a pre-change source file")
    parser.add_argument("--after", action="append", default=[], help="Path to a post-change source file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    result = check_public_api_diff(
        [Path(path) for path in args.before],
        [Path(path) for path in args.after],
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"removed={len(result['removed'])}")
        print(f"added={len(result['added'])}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
