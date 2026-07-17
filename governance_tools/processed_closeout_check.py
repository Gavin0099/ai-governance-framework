"""Report whether the current closeout artifact has a complete handoff receipt.

This module is deliberately read-only.  It does not invoke closeout, write
memory, create receipts, or change gate behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


CANONICAL_ENTRYPOINT = "governance_tools.session_closeout_entry"
SUPPORTED_RECEIPT_SCHEMAS = frozenset({"1.1", "1.2", "1.3", "1.4"})
DEFAULT_CLOSEOUT_PATH = Path("artifacts/session-closeout.txt")
DEFAULT_RECEIPT_DIR = Path("artifacts/runtime/closeout-receipts")

_PLAIN_REASONS = {
    "closeout_artifact_not_present": "the closeout artifact is not present.",
    "closeout_artifact_not_regular_file": "the closeout artifact is not a regular file.",
    "matching_receipt_not_present": "no valid matching canonical receipt was found.",
    "matching_receipt_failed": "the latest matching receipt reports failure.",
    "closeout_newer_than_receipt": "the closeout file is newer than the latest matching receipt.",
    "closeout_checksum_mismatch": "the current closeout checksum does not match the receipt.",
    "memory_eligibility_not_evaluated": "memory eligibility was not evaluated.",
    "required_memory_write_not_performed": "the required memory write was not performed.",
    "memory_write_claim_not_verified": "the reported memory write was not independently verified.",
    "closeout_handoff_complete": "the current closeout file has complete handoff evidence.",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime | None) -> str:
    return value.astimezone(timezone.utc).isoformat() if value is not None else ""


def _resolved_path(raw_path: str | Path, project_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _is_bool(payload: dict[str, Any], field: str) -> bool:
    return type(payload.get(field)) is bool


def _has_valid_outcome_shape(payload: dict[str, Any]) -> bool:
    return (
        type(payload.get("exit_code")) is int
        and _is_bool(payload, "memory_eligibility_evaluated")
        and _is_bool(payload, "memory_write_required")
        and _is_bool(payload, "memory_write_performed")
        and _is_bool(payload, "memory_write_claim_verified")
    )


def _empty_report(project_root: Path, closeout_path: Path) -> dict[str, Any]:
    return {
        "report_only": True,
        "closeout_handoff_complete": False,
        "reason_code": "matching_receipt_not_present",
        "project_root": str(project_root),
        "closeout_artifact_path": str(closeout_path),
        "closeout_exists": False,
        "closeout_mtime_utc": "",
        "closeout_sha256": "",
        "matching_receipt_path": "",
        "matching_receipt_timestamp_utc": "",
        "matching_receipt_schema_version": "",
        "receipt_exit_code": None,
        "checksum_matches": False,
        "memory_eligibility_evaluated": False,
        "memory_write_required": False,
        "memory_write_performed": False,
        "memory_write_claim_verified": False,
        "ignored_malformed_receipt_count": 0,
        "ignored_unsupported_receipt_count": 0,
    }


def build_processed_closeout_report(
    project_root: str | Path,
    closeout_artifact: str | Path = DEFAULT_CLOSEOUT_PATH,
) -> dict[str, Any]:
    """Build a deterministic, read-only processed-closeout report."""

    root = Path(project_root).expanduser().resolve()
    closeout_path = _resolved_path(closeout_artifact, root)
    report = _empty_report(root, closeout_path)

    if not closeout_path.exists():
        report["reason_code"] = "closeout_artifact_not_present"
        return report
    report["closeout_exists"] = True

    if not closeout_path.is_file():
        report["reason_code"] = "closeout_artifact_not_regular_file"
        return report

    closeout_stat = closeout_path.stat()
    closeout_mtime = datetime.fromtimestamp(closeout_stat.st_mtime, timezone.utc)
    closeout_checksum = _sha256(closeout_path)
    report["closeout_mtime_utc"] = _iso_utc(closeout_mtime)
    report["closeout_sha256"] = closeout_checksum

    receipt_dir = root / DEFAULT_RECEIPT_DIR
    candidates: list[tuple[datetime, str, Path, dict[str, Any]]] = []
    malformed_count = 0
    unsupported_count = 0

    if receipt_dir.exists() and not receipt_dir.is_dir():
        raise NotADirectoryError(f"receipt path is not a directory: {receipt_dir}")

    if receipt_dir.is_dir():
        for receipt_path in sorted(receipt_dir.glob("closeout_receipt_*.json")):
            try:
                payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                malformed_count += 1
                continue

            if not isinstance(payload, dict):
                malformed_count += 1
                continue

            schema_version = payload.get("schema_version")
            if schema_version not in SUPPORTED_RECEIPT_SCHEMAS:
                unsupported_count += 1
                continue

            timestamp = _parse_aware_timestamp(payload.get("timestamp"))
            raw_closeout_path = payload.get("closeout_artifact_path")
            if (
                timestamp is None
                or not isinstance(raw_closeout_path, str)
                or not raw_closeout_path.strip()
                or not _has_valid_outcome_shape(payload)
            ):
                malformed_count += 1
                continue

            if payload.get("entrypoint") != CANONICAL_ENTRYPOINT:
                continue

            try:
                receipt_closeout_path = _resolved_path(raw_closeout_path, root)
            except (OSError, ValueError):
                malformed_count += 1
                continue
            if _path_key(receipt_closeout_path) != _path_key(closeout_path):
                continue

            receipt_key = _path_key(receipt_path.resolve())
            candidates.append((timestamp, receipt_key, receipt_path.resolve(), payload))

    report["ignored_malformed_receipt_count"] = malformed_count
    report["ignored_unsupported_receipt_count"] = unsupported_count

    if not candidates:
        report["reason_code"] = "matching_receipt_not_present"
        return report

    receipt_timestamp, _, receipt_path, receipt = max(
        candidates, key=lambda candidate: (candidate[0], candidate[1])
    )
    schema_version = str(receipt["schema_version"])
    exit_code = receipt["exit_code"]
    eligibility_evaluated = receipt["memory_eligibility_evaluated"] is True
    write_required = receipt["memory_write_required"] is True
    write_performed = receipt["memory_write_performed"] is True
    write_verified = receipt.get("memory_write_claim_verified") is True
    receipt_checksum = receipt.get("checksum_of_cleaned_path")
    checksum_matches = isinstance(receipt_checksum, str) and receipt_checksum == closeout_checksum

    report.update(
        {
            "matching_receipt_path": str(receipt_path),
            "matching_receipt_timestamp_utc": _iso_utc(receipt_timestamp),
            "matching_receipt_schema_version": schema_version,
            "receipt_exit_code": exit_code,
            "checksum_matches": checksum_matches,
            "memory_eligibility_evaluated": eligibility_evaluated,
            "memory_write_required": write_required,
            "memory_write_performed": write_performed,
            "memory_write_claim_verified": write_verified,
        }
    )

    if exit_code != 0:
        reason_code = "matching_receipt_failed"
    elif receipt_timestamp < closeout_mtime:
        reason_code = "closeout_newer_than_receipt"
    elif not checksum_matches:
        reason_code = "closeout_checksum_mismatch"
    elif not eligibility_evaluated:
        reason_code = "memory_eligibility_not_evaluated"
    elif write_required and not write_performed:
        reason_code = "required_memory_write_not_performed"
    elif write_required and not write_verified:
        reason_code = "memory_write_claim_not_verified"
    else:
        reason_code = "closeout_handoff_complete"
        report["closeout_handoff_complete"] = True

    report["reason_code"] = reason_code
    return report


def format_human_report(report: dict[str, Any]) -> str:
    if report["closeout_handoff_complete"]:
        first_line = "Closeout handoff is complete for the current closeout file."
    else:
        reason = _PLAIN_REASONS.get(
            str(report.get("reason_code", "")), "complete positive evidence is unavailable."
        )
        first_line = f"Closeout handoff is not complete: {reason}"
    return first_line + "\n" + json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report whether the current closeout file has complete canonical handoff evidence."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--closeout-artifact", default=str(DEFAULT_CLOSEOUT_PATH))
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_processed_closeout_report(args.project_root, args.closeout_artifact)
    except (OSError, ValueError) as exc:
        print(f"processed-closeout check failed: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_human_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
