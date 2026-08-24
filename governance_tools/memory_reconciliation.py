"""Deterministic report-only detectors for memory reconciliation candidates.

M1a is intentionally limited to exact raw-byte equality between two records
that the caller has already admitted. It does not read, write, or reconcile
memory surfaces.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


REPORT_VERSION = "mrcsp-exact-byte-detector.v0.1"
DETECTOR_NAME = "exact_byte_duplicate"
FINDING_CODE = "duplicate_memory_entry"


@dataclass(frozen=True)
class MemoryRecordBytes:
    """One independently identified, caller-admitted memory record payload."""

    record_id: str
    surface: str
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        if not isinstance(self.surface, str) or not self.surface.strip():
            raise ValueError("surface must be a non-empty string")
        if not isinstance(self.content, bytes) or not self.content:
            raise ValueError("content must be non-empty bytes")


def detect_exact_byte_duplicate(
    records: Sequence[MemoryRecordBytes],
) -> dict[str, Any]:
    """Return a report-only exact-byte duplicate report for two records."""

    if not isinstance(records, Sequence) or isinstance(
        records, (str, bytes, bytearray)
    ):
        raise ValueError("records must be a sequence of MemoryRecordBytes")
    if len(records) != 2:
        raise ValueError("exact-byte detection requires exactly two records")
    if not all(isinstance(item, MemoryRecordBytes) for item in records):
        raise ValueError("records must contain only MemoryRecordBytes")

    ordered = sorted(records, key=lambda item: (item.record_id, item.surface))
    if ordered[0].record_id == ordered[1].record_id:
        raise ValueError("record_id values must identify distinct records")

    digests = [hashlib.sha256(item.content).hexdigest() for item in ordered]
    findings: list[dict[str, Any]] = []
    if digests[0] == digests[1]:
        findings.append(
            {
                "code": FINDING_CODE,
                "digest": digests[0],
                "digest_algorithm": "sha256",
                "mode": "report_only",
                "occurrences": 2,
                "record_ids": [item.record_id for item in ordered],
                "severity": "warning",
                "surfaces": sorted(item.surface for item in ordered),
            }
        )

    return {
        "detector": DETECTOR_NAME,
        "findings": findings,
        "mode": "report_only",
        "report_version": REPORT_VERSION,
    }


def render_report_json(report: dict[str, Any]) -> bytes:
    """Serialize a detector report to the M1a byte-stable JSON form."""

    return (
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
