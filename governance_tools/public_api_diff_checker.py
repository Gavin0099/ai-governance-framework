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
    r"\b(?:public|protected\s+internal|public\s+partial)\b.*?(?:(?:=>[^;\n]+;)|(?:\{)|;)",
    re.MULTILINE | re.DOTALL,
)
CPP_API_RE = re.compile(
    r"^\s*(?:class|struct)\s+\w+|^\s*(?:virtual\s+)?(?:[\w:<>*&]+\s+)+\w+\s*\([^;{]*\)\s*(?:const)?\s*;",
    re.MULTILINE,
)
SWIFT_API_RE = re.compile(
    r"^\s*(?:public|open)\s+(?:class|struct|enum|protocol|func|var|let|actor)\b.*$",
    re.MULTILINE,
)
CSHARP_TYPE_RE = re.compile(
    r"\b(public|protected\s+internal|public\s+partial)\s+(?:partial\s+)?"
    r"(class|struct|interface|record)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)
CSHARP_METHOD_RE = re.compile(
    r"\b(public|protected\s+internal)\s+"
    r"(?:(?:static|virtual|abstract|override|sealed|partial|async|extern|new)\s+)*"
    r"(?P<return>[A-Za-z_][A-Za-z0-9_<>,\.\?\[\]\s]*)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((?P<params>[^)]*)\)"
)


def _extract_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [match.group(0).strip() for match in pattern.finditer(text)]


def _normalize_csharp_params(params: str) -> list[str]:
    normalized = []
    for item in params.split(","):
        raw = item.strip()
        if not raw:
            continue
        raw = raw.split("=")[0].strip()
        parts = raw.split()
        if len(parts) >= 2:
            if parts[0] in {"ref", "out", "in", "params"} and len(parts) >= 3:
                param_type = " ".join(parts[:-1])
            else:
                param_type = " ".join(parts[:-1])
        else:
            param_type = parts[0]
        normalized.append(param_type)
    return normalized


def _extract_csharp_semantic_entries(text: str) -> list[dict]:
    entries: list[dict] = []
    type_matches = list(CSHARP_TYPE_RE.finditer(text))

    def _find_container(position: int) -> str:
        container = None
        for type_match in type_matches:
            if type_match.start() < position:
                container = type_match.group("name")
            else:
                break
        return container or "<global>"

    for match in type_matches:
        name = match.group("name")
        entries.append(
            {
                "kind": "type",
                "identity": f"type:{name}",
                "display": match.group(0).strip(),
                "signature": match.group(0).strip(),
                "container": name,
            }
        )

    for match in CSHARP_METHOD_RE.finditer(text):
        method_name = match.group("name")
        return_type = " ".join(match.group("return").split())
        params = _normalize_csharp_params(match.group("params"))
        container = _find_container(match.start())
        normalized_signature = f"{return_type} {method_name}({', '.join(params)})"
        entries.append(
            {
                "kind": "method",
                "identity": f"method:{container}.{method_name}",
                "display": match.group(0).strip(),
                "signature": normalized_signature,
                "container": container,
            }
        )

    offset = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("public ", "protected internal ")):
            offset += len(line) + 1
            continue
        if "{ get;" not in stripped and "{ set;" not in stripped and "{ init;" not in stripped:
            offset += len(line) + 1
            continue
        if any(token in stripped for token in (" class ", " struct ", " interface ", " record ")):
            offset += len(line) + 1
            continue
        header, _, body = stripped.partition("{")
        header_parts = header.split()
        if len(header_parts) < 3:
            offset += len(line) + 1
            continue
        property_name = header_parts[-1]
        property_type = header_parts[-2]
        container = _find_container(offset)
        accessors = body
        accessor_signature = []
        if "get;" in accessors or "get =>" in accessors:
            accessor_signature.append("get")
        if "set;" in accessors or "set =>" in accessors or "init;" in accessors:
            accessor_signature.append("set")
        normalized_signature = f"{property_type} {property_name} [{' '.join(accessor_signature)}]".strip()
        entries.append(
            {
                "kind": "property",
                "identity": f"property:{container}.{property_name}",
                "display": match.group(0).strip(),
                "signature": normalized_signature,
                "container": container,
            }
        )
        offset += len(line) + 1

    for type_match in type_matches:
        type_name = type_match.group("name")
        ctor_re = re.compile(
            rf"\b(public|protected\s+internal)\s+{re.escape(type_name)}\s*\((?P<params>[^)]*)\)"
        )
        for match in ctor_re.finditer(text):
            params = _normalize_csharp_params(match.group("params"))
            normalized_signature = f"{type_name}({', '.join(params)})"
            entries.append(
                {
                    "kind": "constructor",
                    "identity": f"constructor:{type_name}",
                    "display": match.group(0).strip(),
                    "signature": normalized_signature,
                    "container": type_name,
                }
            )

    return entries


def extract_public_api_manifest(file_paths: list[Path]) -> dict:
    entries: list[dict] = []

    for path in sorted(file_paths):
        suffix = path.suffix.lower()
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(path).replace("\\", "/")

        if suffix == ".cs":
            signatures = _extract_matches(text, C_SHARP_API_RE)
            semantic_entries = _extract_csharp_semantic_entries(text)
        elif suffix in {".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"}:
            signatures = _extract_matches(text, CPP_API_RE)
            semantic_entries = []
        elif suffix == ".swift":
            signatures = _extract_matches(text, SWIFT_API_RE)
            semantic_entries = []
        else:
            continue

        if signatures:
            entry = {"path": rel_path, "signatures": signatures}
            if semantic_entries:
                entry["semantic_entries"] = semantic_entries
            entries.append(entry)

    return {"entries": entries}


def _assess_semantic_compatibility(before: dict, after: dict) -> dict:
    # Build identity -> signatures maps from any semantic entries present.
    before_map: dict[str, set[str]] = {}
    after_map: dict[str, set[str]] = {}

    for manifest, target in ((before, before_map), (after, after_map)):
        for entry in manifest.get("entries", []):
            for semantic in entry.get("semantic_entries", []):
                target.setdefault(semantic["identity"], set()).add(semantic["signature"])

    if not before_map and not after_map:
        return {
            "compatibility_risk": "unknown",
            "breaking_changes": [],
            "non_breaking_changes": [],
        }

    breaking_changes: list[str] = []
    non_breaking_changes: list[str] = []

    identities = sorted(set(before_map) | set(after_map))
    for identity in identities:
        before_signatures = before_map.get(identity, set())
        after_signatures = after_map.get(identity, set())

        if identity not in before_map:
            non_breaking_changes.append(f"New public API introduced: {identity}")
            continue
        if identity not in after_map:
            breaking_changes.append(f"Public API removed: {identity}")
            continue
        if before_signatures == after_signatures:
            continue

        removed = before_signatures - after_signatures
        added = after_signatures - before_signatures
        if removed:
            breaking_changes.append(
                f"Public API signature changed for {identity}: removed {sorted(removed)}"
            )
        elif added:
            non_breaking_changes.append(
                f"Public API overload or expansion for {identity}: added {sorted(added)}"
            )

    risk = "high" if breaking_changes else "low"
    return {
        "compatibility_risk": risk,
        "breaking_changes": breaking_changes,
        "non_breaking_changes": non_breaking_changes,
    }


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

    compatibility = _assess_semantic_compatibility(before, after)
    for item in compatibility["breaking_changes"]:
        errors.append(item)
    for item in compatibility["non_breaking_changes"]:
        warnings.append(item)

    return {
        "ok": len(errors) == 0,
        "removed": removed,
        "added": added,
        "compatibility_risk": compatibility["compatibility_risk"],
        "breaking_changes": compatibility["breaking_changes"],
        "non_breaking_changes": compatibility["non_breaking_changes"],
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
        "compatibility_risk": diff["compatibility_risk"],
        "breaking_changes": diff["breaking_changes"],
        "non_breaking_changes": diff["non_breaking_changes"],
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
        print(f"compatibility_risk={result['compatibility_risk']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
