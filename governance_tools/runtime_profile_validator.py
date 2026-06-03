#!/usr/bin/env python3
"""Static validator for agent runtime governance profiles.

This validator is intentionally structural-only.

It validates:
- required top-level runtime profile fields are present
- surface entries include minimum review fields
- evidence_refs include command/artifact plus result
- high-risk runtime claims are downgraded or listed under not_claimed

It does NOT validate runtime enforcement, authority correctness, evidence
truthfulness, semantic correctness, or sandbox containment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL_FIELDS = (
    "profile_id",
    "profile_version",
    "profile_authority",
    "claim_ceiling",
    "not_claimed",
    "surfaces",
    "evidence_refs",
)

REQUIRED_SURFACE_FIELDS = (
    "id",
    "type",
    "boundary_class",
    "max_side_effect",
    "controls",
    "control_claim_ceiling",
)

VALID_EVIDENCE_RESULTS = {
    "PASS",
    "FAIL",
    "NOT RUN",
    "NOT PRESENT",
    "NOT CLAIMED",
}

PLACEHOLDER_VALUES = {
    "",
    "none",
    "n/a",
    "see above",
    "tbd",
}

HIGH_RISK_TERMS = (
    "runtime enforced",
    "runtime enforcement",
    "sandboxed",
    "contained",
    "authority confirmed",
    "evidence validated",
    "behaviorally safe",
    "semantically verified",
)

DOWNGRADE_TERMS = (
    "not claimed",
    "no runtime enforcement",
    "not containment",
    "not trusted",
    "structural",
    "reviewer-facing",
    "heuristic",
    "requires os-level",
    "requires os boundary",
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize(value: Any) -> str:
    return " ".join(str(value).strip().split()).lower()


def _is_placeholder(value: Any) -> bool:
    return _normalize(value) in PLACEHOLDER_VALUES


def _text_contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _load_yaml_text(text: str) -> tuple[Any, list[dict[str, str]]]:
    try:
        return yaml.safe_load(text), []
    except yaml.YAMLError as exc:
        return None, [{"code": "invalid_yaml", "field": "document", "value": str(exc)}]


def _validate_evidence_refs(refs: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(refs, list) or not refs:
        return [{"code": "missing_or_empty_list", "field": "evidence_refs"}]

    for index, ref in enumerate(refs):
        field = f"evidence_refs[{index}]"
        if not isinstance(ref, dict):
            errors.append({"code": "invalid_evidence_ref_shape", "field": field})
            continue

        command = ref.get("command")
        artifact = ref.get("artifact")
        result = ref.get("result")
        if _is_placeholder(command) and _is_placeholder(artifact):
            errors.append({"code": "missing_command_or_artifact", "field": field})
        if result not in VALID_EVIDENCE_RESULTS:
            errors.append({"code": "missing_or_invalid_result", "field": field})

    return errors


def _validate_surfaces(surfaces: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(surfaces, list) or not surfaces:
        return [{"code": "missing_or_empty_list", "field": "surfaces"}]

    for index, surface in enumerate(surfaces):
        field = f"surfaces[{index}]"
        if not isinstance(surface, dict):
            errors.append({"code": "invalid_surface_shape", "field": field})
            continue

        for required in REQUIRED_SURFACE_FIELDS:
            value = surface.get(required)
            if value is None or _is_placeholder(value):
                errors.append(
                    {
                        "code": "missing_required_surface_field",
                        "field": f"{field}.{required}",
                    }
                )

        controls = surface.get("controls")
        if not isinstance(controls, list) or not controls:
            errors.append({"code": "missing_or_empty_controls", "field": f"{field}.controls"})

    return errors


def _validate_claim_boundaries(profile: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    claim_ceiling = _as_list(profile.get("claim_ceiling"))
    not_claimed = _as_list(profile.get("not_claimed"))
    not_claimed_text = " ".join(str(item) for item in not_claimed).lower()

    if not claim_ceiling:
        errors.append({"code": "missing_or_empty_list", "field": "claim_ceiling"})
    if not not_claimed:
        errors.append({"code": "missing_or_empty_list", "field": "not_claimed"})

    if claim_ceiling and all(_is_placeholder(item) for item in claim_ceiling):
        errors.append({"code": "placeholder_only_claim_ceiling", "field": "claim_ceiling"})
    if not_claimed and all(_is_placeholder(item) for item in not_claimed):
        errors.append({"code": "placeholder_only_not_claimed", "field": "not_claimed"})

    document_text = json.dumps(profile, ensure_ascii=False).lower()
    high_risk_hits = [term for term in HIGH_RISK_TERMS if term in document_text]
    has_downgrade = _text_contains_any(not_claimed_text, DOWNGRADE_TERMS)

    for surface in _as_list(profile.get("surfaces")):
        if isinstance(surface, dict):
            has_downgrade = has_downgrade or _text_contains_any(
                str(surface.get("control_claim_ceiling", "")),
                DOWNGRADE_TERMS,
            )

    if high_risk_hits and not has_downgrade:
        errors.append(
            {
                "code": "high_risk_runtime_claim_without_downgrade",
                "field": "claim_ceiling",
                "value": ", ".join(high_risk_hits),
            }
        )

    return errors


def validate_runtime_profile_data(data: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(data, dict):
        errors.append({"code": "invalid_profile_shape", "field": "document"})
        return _report(data, errors)

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        value = data.get(field)
        if value is None or _is_placeholder(value):
            errors.append({"code": "missing_required_field", "field": field})

    errors.extend(_validate_claim_boundaries(data))
    errors.extend(_validate_surfaces(data.get("surfaces")))
    errors.extend(_validate_evidence_refs(data.get("evidence_refs")))

    return _report(data, errors)


def _report(data: Any, errors: list[dict[str, str]]) -> dict[str, Any]:
    profile = data if isinstance(data, dict) else {}
    surfaces = _as_list(profile.get("surfaces"))
    evidence_refs = _as_list(profile.get("evidence_refs"))
    return {
        "ok": not errors,
        "errors": errors,
        "signals": {
            "profile_id": profile.get("profile_id"),
            "surface_count": len(surfaces),
            "evidence_ref_count": len(evidence_refs),
            "required_fields_present": sorted(
                field for field in REQUIRED_TOP_LEVEL_FIELDS if field in profile
            ),
        },
    }


def validate_runtime_profile_text(text: str) -> dict[str, Any]:
    data, yaml_errors = _load_yaml_text(text)
    if yaml_errors:
        return _report({}, yaml_errors)
    return validate_runtime_profile_data(data)


def validate_runtime_profile_file(path: Path) -> dict[str, Any]:
    return validate_runtime_profile_text(path.read_text(encoding="utf-8"))


def _iter_input_paths(paths: list[Path]) -> tuple[list[Path], list[dict[str, str]]]:
    files: list[Path] = []
    path_errors: list[dict[str, str]] = []

    for path in paths:
        if not path.exists():
            path_errors.append({"path": str(path), "error": "path_not_found"})
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.yaml")))
            files.extend(sorted(path.rglob("*.yml")))
            continue
        files.append(path)

    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)

    return deduped, path_errors


def validate_runtime_profile_paths(paths: list[Path]) -> dict[str, Any]:
    files, path_errors = _iter_input_paths(paths)
    results: list[dict[str, Any]] = []

    for path in files:
        report = validate_runtime_profile_file(path)
        results.append({"path": str(path), **report})

    valid_count = sum(1 for item in results if item["ok"])
    invalid_count = len(results) - valid_count
    return {
        "ok": not path_errors and invalid_count == 0,
        "total_files": len(results),
        "valid_files": valid_count,
        "invalid_files": invalid_count,
        "path_errors": path_errors,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate agent runtime governance profile YAML files."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Runtime profile YAML file(s) or directories. Directories scan *.yaml and *.yml.",
    )
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    report = validate_runtime_profile_paths([Path(path) for path in args.paths])

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("[runtime_profile_validator]")
        print(f"  ok:            {report['ok']}")
        print(f"  total files:   {report['total_files']}")
        print(f"  valid files:   {report['valid_files']}")
        print(f"  invalid files: {report['invalid_files']}")
        if report["path_errors"]:
            print("  path errors:")
            for item in report["path_errors"]:
                print(f"    - {item['path']}: {item['error']}")
        for item in report["results"]:
            status = "ok" if item["ok"] else "invalid"
            print(f"  - {item['path']}: {status}")
            for error in item["errors"]:
                detail = error.get("value") or error.get("field") or ""
                print(f"      {error['code']}: {detail}".rstrip(": "))

    if not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
