#!/usr/bin/env python3
"""Static validator for the response envelope reporting contract.

This validator is intentionally structural-only.

It validates:
- required response-envelope field labels are present
- evidence_refs contains at least one non-placeholder entry with command/artifact plus result
- high-risk authority wording is downgraded or supported by evidence refs
- (opt-in, --check-response-quality) plain-language quality fields
  (`conclusion`, `recommended_action`, `next_action`) each appear exactly
  once, are non-empty after list-marker normalization, and appear before
  `evidence_refs`; label, value, and position are bound to the same field
  occurrence so a later duplicate cannot satisfy an earlier empty label

It does NOT validate semantic correctness, runtime enforcement, or artifact
truthfulness. The quality check is structural label/position checking only; it
cannot judge whether the conclusion is actually plain language.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "mode_source",
    "task_authority",
    "evidence_refs",
    "claim_ceiling",
    "not_claimed",
)

PLACEHOLDER_EVIDENCE_VALUES = {
    "none",
    "n/a",
    "see above",
    "tbd",
}

VALID_EVIDENCE_RESULTS = {
    "PASS",
    "FAIL",
    "NOT RUN",
    "NOT PRESENT",
    "NOT CLAIMED",
}

HIGH_RISK_PATTERNS = (
    "runtime enforced",
    "validated",
    "proven",
    "semantic pass",
    "behavioral pass",
    "runtime gate",
)

DOWNGRADE_MARKERS = (
    "NOT CLAIMED",
    "NOT PRESENT",
)

FIELD_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")

QUALITY_FIELDS = (
    "conclusion",
    "recommended_action",
    "next_action",
)

# `none` is a legitimate explicit value for next_action per the contract; for
# the other quality fields it is treated as placeholder content.
QUALITY_NONE_ALLOWED_FIELDS = {"next_action"}

EVIDENCE_ANCHOR_FIELD = "evidence_refs"


def _normalize_value(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def _extract_fields(text: str) -> dict[str, list[str]]:
    current_field: str | None = None
    fields: dict[str, list[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = FIELD_PATTERN.match(line)
        if match:
            current_field = match.group(1)
            remainder = match.group(2).strip()
            fields.setdefault(current_field, [])
            if remainder:
                fields[current_field].append(remainder)
            continue

        if current_field is not None:
            stripped = line.strip()
            if stripped:
                fields[current_field].append(stripped)

    return fields


def _extract_evidence_entries(field_lines: list[str]) -> list[str]:
    entries: list[str] = []
    for line in field_lines:
        normalized = line.strip()
        if not normalized:
            continue
        if normalized.startswith("- "):
            entries.append(normalized[2:].strip())
        else:
            entries.append(normalized)
    return entries


def _parse_evidence_refs(field_lines: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def ensure_current() -> dict[str, Any]:
        nonlocal current
        if current is None:
            current = {"raw": []}
            refs.append(current)
        return current

    def apply_key_value(target: dict[str, Any], text: str) -> None:
        if ":" not in text:
            return
        key, value = text.split(":", 1)
        normalized_key = key.strip()
        if normalized_key in {"command", "artifact", "result"}:
            target[normalized_key] = value.strip()

    for line in field_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            current = {"raw": [stripped[2:].strip()]}
            refs.append(current)
            apply_key_value(current, stripped[2:].strip())
            continue

        target = ensure_current()
        target["raw"].append(stripped)
        apply_key_value(target, stripped)

    return refs


def _is_placeholder_evidence_entry(entry: str) -> bool:
    normalized = _normalize_value(entry)
    if normalized in PLACEHOLDER_EVIDENCE_VALUES:
        return True
    for token in PLACEHOLDER_EVIDENCE_VALUES:
        if normalized == f"command: {token}" or normalized == f"artifact: {token}":
            return True
    return False


def _is_placeholder_evidence_ref(ref: dict[str, Any]) -> bool:
    raw_text = " ".join(str(item) for item in ref.get("raw", []))
    if _is_placeholder_evidence_entry(raw_text):
        return True
    for key in ("command", "artifact"):
        value = ref.get(key)
        if isinstance(value, str) and _normalize_value(value) in PLACEHOLDER_EVIDENCE_VALUES:
            return True
    return False


def _evidence_ref_shape_errors(ref: dict[str, Any]) -> list[str]:
    if _is_placeholder_evidence_ref(ref):
        return []

    errors: list[str] = []
    if not (ref.get("command") or ref.get("artifact")):
        errors.append("missing_command_or_artifact")
    result = ref.get("result")
    if result not in VALID_EVIDENCE_RESULTS:
        errors.append("missing_or_invalid_result")
    return errors


def _has_valid_evidence_ref(fields: dict[str, list[str]]) -> bool:
    evidence_lines = fields.get("evidence_refs", [])
    refs = _parse_evidence_refs(evidence_lines)
    if not refs:
        return False
    return any(
        not _is_placeholder_evidence_ref(ref)
        and not _evidence_ref_shape_errors(ref)
        for ref in refs
    )


def _extract_field_first_lines(text: str) -> dict[str, int]:
    first_lines: dict[str, int] = {}
    for index, raw_line in enumerate(text.splitlines()):
        match = FIELD_PATTERN.match(raw_line.rstrip())
        if match:
            first_lines.setdefault(match.group(1), index)
    return first_lines


def _extract_quality_occurrences(text: str) -> dict[str, list[dict[str, Any]]]:
    """Collect every occurrence of each quality field with its own value lines.

    Unlike ``_extract_fields`` this does NOT merge same-name occurrences: the
    value and line position stay bound to the occurrence that declared them,
    so a later duplicate cannot satisfy an earlier empty label.
    """
    occurrences: dict[str, list[dict[str, Any]]] = {
        field: [] for field in QUALITY_FIELDS
    }
    current: dict[str, Any] | None = None

    for index, raw_line in enumerate(text.splitlines()):
        line = raw_line.rstrip()
        match = FIELD_PATTERN.match(line)
        if match:
            field = match.group(1)
            if field in occurrences:
                current = {"line": index, "value_lines": []}
                remainder = match.group(2).strip()
                if remainder:
                    current["value_lines"].append(remainder)
                occurrences[field].append(current)
            else:
                current = None
            continue

        if current is not None:
            stripped = line.strip()
            if stripped:
                current["value_lines"].append(stripped)

    return occurrences


def _quality_occurrence_value(value_lines: list[str]) -> str:
    cleaned: list[str] = []
    for line in value_lines:
        if line.startswith("- "):
            line = line[2:].strip()
        elif line == "-":
            line = ""
        if line:
            cleaned.append(line)
    return _normalize_value(" ".join(cleaned))


def _quality_check(text: str) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    findings: list[str] = []
    errors: list[dict[str, str]] = []
    occurrences = _extract_quality_occurrences(text)
    evidence_line = _extract_field_first_lines(text).get(EVIDENCE_ANCHOR_FIELD)

    present: list[str] = []
    ordered_before_evidence = True

    for field in QUALITY_FIELDS:
        field_occurrences = occurrences[field]
        if not field_occurrences:
            findings.append(f"quality_missing_field:{field}")
            errors.append({"code": "quality_missing_field", "field": field})
            continue
        present.append(field)

        if evidence_line is not None and any(
            occurrence["line"] > evidence_line for occurrence in field_occurrences
        ):
            ordered_before_evidence = False
            findings.append(f"quality_field_after_evidence:{field}")
            errors.append({"code": "quality_field_after_evidence", "field": field})

        if len(field_occurrences) > 1:
            findings.append(f"quality_duplicate_field:{field}")
            errors.append({"code": "quality_duplicate_field", "field": field})
            continue

        value = _quality_occurrence_value(field_occurrences[0]["value_lines"])
        is_placeholder = value in PLACEHOLDER_EVIDENCE_VALUES and not (
            value == "none" and field in QUALITY_NONE_ALLOWED_FIELDS
        )
        if not value or is_placeholder:
            findings.append(f"quality_empty_field:{field}")
            errors.append(
                {"code": "quality_empty_field", "field": field, "value": value}
            )

    signals = {
        "quality_fields_present": present,
        "quality_ordered_before_evidence": ordered_before_evidence,
    }
    return findings, errors, signals


def validate_response_envelope_text(
    text: str, *, check_quality: bool = False
) -> dict[str, Any]:
    fields = _extract_fields(text)
    findings: list[str] = []
    errors: list[dict[str, str]] = []

    for field in REQUIRED_FIELDS:
        if field not in fields:
            findings.append(f"missing_required_field:{field}")
            errors.append({"code": "missing_required_field", "field": field})

    evidence_lines = fields.get("evidence_refs", [])
    evidence_entries = _extract_evidence_entries(evidence_lines)
    evidence_refs = _parse_evidence_refs(evidence_lines)
    placeholder_entries = [
        entry for entry in evidence_entries if _is_placeholder_evidence_entry(entry)
    ]
    placeholder_refs = [ref for ref in evidence_refs if _is_placeholder_evidence_ref(ref)]
    evidence_shape_errors = [
        {"ref": " ".join(ref.get("raw", [])), "reasons": _evidence_ref_shape_errors(ref)}
        for ref in evidence_refs
        if _evidence_ref_shape_errors(ref)
    ]

    non_placeholder_refs = [
        ref for ref in evidence_refs if not _is_placeholder_evidence_ref(ref)
    ]

    if "evidence_refs" in fields and not evidence_refs:
        findings.append("evidence_refs_empty")
        errors.append({"code": "evidence_refs_empty", "field": "evidence_refs"})
    elif "evidence_refs" in fields and not non_placeholder_refs:
        findings.append("evidence_refs_placeholder_only")
        errors.append({"code": "evidence_refs_placeholder_only", "field": "evidence_refs"})

    for entry in placeholder_entries:
        findings.append(f"placeholder_evidence_ref:{entry}")
        errors.append(
            {
                "code": "placeholder_evidence_ref",
                "field": "evidence_refs",
                "value": entry,
            }
        )

    for item in evidence_shape_errors:
        findings.append(f"invalid_evidence_ref_shape:{item['ref']}")
        errors.append(
            {
                "code": "invalid_evidence_ref_shape",
                "field": "evidence_refs",
                "value": item["ref"],
            }
        )

    lowered_text = text.lower()
    risky_hits = [pattern for pattern in HIGH_RISK_PATTERNS if pattern in lowered_text]
    has_downgrade_marker = any(marker in text for marker in DOWNGRADE_MARKERS)
    has_valid_evidence = _has_valid_evidence_ref(fields)

    if risky_hits and not (has_downgrade_marker or has_valid_evidence):
        findings.append("high_risk_authority_wording_without_support")
        errors.append(
            {
                "code": "high_risk_authority_wording_without_support",
                "field": "claim_ceiling",
                "value": ", ".join(risky_hits),
            }
        )

    quality_signals: dict[str, Any] = {}
    if check_quality:
        quality_findings, quality_errors, quality_signals = _quality_check(text)
        findings.extend(quality_findings)
        errors.extend(quality_errors)

    return {
        "ok": not errors,
        "findings": findings,
        "errors": errors,
        "signals": {
            **quality_signals,
            "fields_present": sorted(fields.keys()),
            "required_fields_present": sorted(field for field in REQUIRED_FIELDS if field in fields),
            "evidence_entry_count": len(evidence_refs),
            "placeholder_evidence_entry_count": len(placeholder_refs),
            "invalid_evidence_shape_count": len(evidence_shape_errors),
            "high_risk_hits": risky_hits,
            "has_downgrade_marker": has_downgrade_marker,
            "has_valid_evidence_ref": has_valid_evidence,
        },
    }


def validate_response_envelope_file(
    path: Path, *, check_quality: bool = False
) -> dict[str, Any]:
    return validate_response_envelope_text(
        path.read_text(encoding="utf-8"), check_quality=check_quality
    )


def _iter_input_paths(paths: list[Path]) -> tuple[list[Path], list[dict[str, str]]]:
    files: list[Path] = []
    path_errors: list[dict[str, str]] = []

    for path in paths:
        if not path.exists():
            path_errors.append({"path": str(path), "error": "path_not_found"})
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
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


def validate_response_envelope_paths(
    paths: list[Path], *, check_quality: bool = False
) -> dict[str, Any]:
    files, path_errors = _iter_input_paths(paths)
    results: list[dict[str, Any]] = []

    for path in files:
        report = validate_response_envelope_file(path, check_quality=check_quality)
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
        description="Validate a response envelope reporting contract fragment."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Response envelope file(s) or directorie(s). Directories scan *.md files.",
    )
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument(
        "--check-response-quality",
        action="store_true",
        help=(
            "Opt-in: additionally require non-empty conclusion, "
            "recommended_action, and next_action fields positioned before "
            "evidence_refs. Off by default; default behavior is unchanged."
        ),
    )
    args = parser.parse_args()

    report = validate_response_envelope_paths(
        [Path(path) for path in args.paths],
        check_quality=args.check_response_quality,
    )

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("[response_envelope_validator]")
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
