"""Deterministic report-only detectors for memory reconciliation candidates.

Each detector consumes values that the caller has already admitted. This
module does not discover, read, write, or reconcile memory surfaces.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any

from memory_pipeline import memory_layout


REPORT_VERSION = "mrcsp-exact-byte-detector.v0.1"
DETECTOR_NAME = "exact_byte_duplicate"
FINDING_CODE = "duplicate_memory_entry"
ENCODING_REPORT_VERSION = "mrcsp-encoding-integrity.v0.1"
ENCODING_DETECTOR_NAME = "memory_encoding_integrity"
ENCODING_FINDING_CODE = "memory_encoding_integrity_anomaly"
IDENTITY_REPORT_VERSION = "mrcsp-knowledge-identity-collision.v0.1"
IDENTITY_DETECTOR_NAME = "knowledge_identity_collision"
IDENTITY_FINDING_CODE = "knowledge_identity_collision"
MISSING_SURFACE_REPORT_VERSION = "mrcsp-missing-logical-memory-surface.v0.1"
MISSING_SURFACE_DETECTOR_NAME = "missing_logical_memory_surface"
MISSING_SURFACE_FINDING_CODE = "missing_logical_memory_surface"


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


@dataclass(frozen=True)
class KnowledgeIdentityObservation:
    """One caller-admitted knowledge identity attached to a distinct record."""

    record_id: str
    surface: str
    knowledge_id: str

    def __post_init__(self) -> None:
        if type(self.record_id) is not str or not self.record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        if type(self.surface) is not str or not self.surface.strip():
            raise ValueError("surface must be a non-empty string")
        if type(self.knowledge_id) is not str or not self.knowledge_id.strip():
            raise ValueError("knowledge_id must be a non-empty string")
        if self.knowledge_id != self.knowledge_id.strip():
            raise ValueError("knowledge_id must not contain surrounding whitespace")


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


def detect_memory_encoding_integrity(record: MemoryRecordBytes) -> dict[str, Any]:
    """Return a report-only strict UTF-8 integrity report for one record."""

    if not isinstance(record, MemoryRecordBytes):
        raise ValueError("record must be a MemoryRecordBytes value")
    record_id = record.record_id
    surface = record.surface
    content = record.content
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(surface, str) or not surface.strip():
        raise ValueError("surface must be a non-empty string")
    if not isinstance(content, bytes) or not content:
        raise ValueError("content must be non-empty bytes")

    reason: str | None = None
    try:
        decoded = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        reason = "invalid_utf8"
    else:
        if "\ufffd" in decoded:
            reason = "replacement_character_present"

    findings: list[dict[str, Any]] = []
    if reason is not None:
        findings.append(
            {
                "code": ENCODING_FINDING_CODE,
                "digest": hashlib.sha256(content).hexdigest(),
                "digest_algorithm": "sha256",
                "mode": "report_only",
                "reason": reason,
                "record_id": record_id,
                "severity": "warning",
                "surface": surface,
            }
        )

    return {
        "detector": ENCODING_DETECTOR_NAME,
        "findings": findings,
        "mode": "report_only",
        "report_version": ENCODING_REPORT_VERSION,
    }


def detect_knowledge_identity_collision(
    observations: Sequence[KnowledgeIdentityObservation],
) -> dict[str, Any]:
    """Return a report-only exact knowledge-identity collision report."""

    if not isinstance(observations, Sequence) or isinstance(
        observations, (str, bytes, bytearray)
    ):
        raise ValueError(
            "observations must be a sequence of KnowledgeIdentityObservation"
        )
    try:
        materialized = tuple(islice(iter(observations), 3))
    except Exception as exc:
        raise ValueError("observations must be safely materializable") from exc
    if len(materialized) != 2:
        raise ValueError(
            "identity collision detection requires exactly two observations"
        )
    if not all(
        isinstance(item, KnowledgeIdentityObservation) for item in materialized
    ):
        raise ValueError(
            "observations must contain only KnowledgeIdentityObservation values"
        )

    snapshots: list[tuple[str, str, str]] = []
    for observation in materialized:
        try:
            record_id = observation.record_id
            surface = observation.surface
            knowledge_id = observation.knowledge_id
            record_id_stripped = (
                record_id.strip() if type(record_id) is str else None
            )
            surface_stripped = surface.strip() if type(surface) is str else None
            knowledge_id_stripped = (
                knowledge_id.strip() if type(knowledge_id) is str else None
            )
        except Exception as exc:
            raise ValueError("observation fields must be safely readable") from exc
        if type(record_id) is not str or not record_id_stripped:
            raise ValueError("record_id must be a non-empty string")
        if type(surface) is not str or not surface_stripped:
            raise ValueError("surface must be a non-empty string")
        if type(knowledge_id) is not str or not knowledge_id_stripped:
            raise ValueError("knowledge_id must be a non-empty string")
        if knowledge_id != knowledge_id_stripped:
            raise ValueError("knowledge_id must not contain surrounding whitespace")
        snapshots.append((record_id, surface, knowledge_id))

    ordered = sorted(snapshots, key=lambda item: (item[0], item[1], item[2]))
    if ordered[0][0] == ordered[1][0]:
        raise ValueError("record_id values must identify distinct records")

    findings: list[dict[str, Any]] = []
    if ordered[0][2] == ordered[1][2]:
        knowledge_id = ordered[0][2]
        findings.append(
            {
                "code": IDENTITY_FINDING_CODE,
                "knowledge_id": knowledge_id,
                "mode": "report_only",
                "namespace": "knowledge",
                "occurrences": 2,
                "qualified_identity": f"knowledge:{knowledge_id}",
                "record_ids": [item[0] for item in ordered],
                "severity": "warning",
                "surfaces": [item[1] for item in ordered],
            }
        )

    return {
        "detector": IDENTITY_DETECTOR_NAME,
        "findings": findings,
        "mode": "report_only",
        "report_version": IDENTITY_REPORT_VERSION,
    }


def detect_missing_logical_memory_surface(
    memory_root: Path, logical_name: str
) -> dict[str, Any]:
    """Report whether one caller-admitted logical memory surface is missing."""

    if not isinstance(memory_root, Path):
        raise ValueError("memory_root must be a pathlib.Path")
    if type(logical_name) is not str or not logical_name:
        raise ValueError("logical_name must be a configured non-empty string")

    try:
        root_is_directory = memory_root.is_dir()
    except Exception as exc:
        raise ValueError("memory_root must be safely readable") from exc
    if not root_is_directory:
        raise ValueError("memory_root must exist and be a directory")

    if logical_name not in memory_layout.MEMORY_FILE_ALIASES:
        raise ValueError("logical_name must be defined in MEMORY_FILE_ALIASES")

    resolver = memory_layout.resolve_memory_file
    try:
        resolved_path = resolver(memory_root, logical_name)
        resolved_exists = resolved_path.exists()
    except Exception as exc:
        raise ValueError("logical memory surface resolution failed") from exc

    findings: list[dict[str, Any]] = []
    if not resolved_exists:
        findings.append(
            {
                "code": MISSING_SURFACE_FINDING_CODE,
                "logical_name": logical_name,
                "mode": "report_only",
                "resolved_path": str(resolved_path),
                "severity": "warning",
            }
        )

    return {
        "detector": MISSING_SURFACE_DETECTOR_NAME,
        "findings": findings,
        "mode": "report_only",
        "report_version": MISSING_SURFACE_REPORT_VERSION,
    }


def render_report_json(report: dict[str, Any]) -> bytes:
    """Serialize a detector report to the shared byte-stable JSON form."""

    return (
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
