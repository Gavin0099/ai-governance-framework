#!/usr/bin/env python3
"""Static validator for the response envelope reporting contract.

This validator is intentionally structural-only.

It validates:
- required response-envelope field labels are present
- evidence_refs contains at least one non-placeholder entry with command/artifact plus result
- high-risk authority wording is downgraded or supported by evidence refs

It does NOT validate semantic correctness, runtime enforcement, or artifact
truthfulness.
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


def validate_response_envelope_text(text: str) -> dict[str, Any]:
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

    return {
        "ok": not errors,
        "findings": findings,
        "errors": errors,
        "signals": {
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


def validate_response_envelope_file(path: Path) -> dict[str, Any]:
    return validate_response_envelope_text(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a response envelope reporting contract fragment."
    )
    parser.add_argument("path", help="Path to the response envelope text file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    report = validate_response_envelope_file(Path(args.path))

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("[response_envelope_validator]")
        print(f"  ok:                     {report['ok']}")
        print(
            f"  required fields:        {len(report['signals']['required_fields_present'])}/{len(REQUIRED_FIELDS)}"
        )
        print(f"  evidence entries:       {report['signals']['evidence_entry_count']}")
        print(
            f"  placeholder evidence:   {report['signals']['placeholder_evidence_entry_count']}"
        )
        print(
            f"  invalid evidence shape: {report['signals']['invalid_evidence_shape_count']}"
        )
        print(
            f"  high-risk wording hits: {len(report['signals']['high_risk_hits'])}"
        )
        if report["errors"]:
            print("  errors:")
            for item in report["errors"]:
                detail = item.get("value") or item.get("field") or ""
                print(f"    - {item['code']}: {detail}".rstrip(": "))

    if not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
