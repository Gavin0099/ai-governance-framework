#!/usr/bin/env python3
"""Pure memory identity calculators and relation invariants.

This module deliberately has no filesystem, Git, receipt, or writer side
effects.  Runtime integration is a separate, higher-risk tranche.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


EVENT_IDENTITY_SCHEMA = "memory-event/1"
RECORD_IDENTITY_SCHEMA = "memory-record/2"
SESSION_CLOSEOUT_EVENT_KIND = "session-closeout"
SESSION_DERIVED_MEMORY_TYPE = "session-derived"
CANONICAL_MEMORY_WRITER = "governance_tools.memory_record"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TargetExistence(str, Enum):
    """Whether an exact record target exists in an audited source."""

    RECORD_TARGET_PRESENT = "RECORD_TARGET_PRESENT"
    EVENT_ONLY = "EVENT_ONLY"


class RelationStatus(str, Enum):
    """Current durability/materialization state of an identity relation."""

    MATERIALIZED = "MATERIALIZED"
    PENDING_SOURCE_PRESERVATION = "PENDING_SOURCE_PRESERVATION"
    RECORD_VERSION_UNMATERIALIZED = "RECORD_VERSION_UNMATERIALIZED"
    RECORD_DANGLING = "RECORD_DANGLING"


class RecordAttemptKind(str, Enum):
    """Semantic result of comparing a candidate with an existing record."""

    RETRY = "RETRY"
    CORRECTION = "CORRECTION"


_TARGET_BY_STATUS = {
    RelationStatus.MATERIALIZED: TargetExistence.RECORD_TARGET_PRESENT,
    RelationStatus.PENDING_SOURCE_PRESERVATION:
        TargetExistence.RECORD_TARGET_PRESENT,
    RelationStatus.RECORD_VERSION_UNMATERIALIZED: TargetExistence.EVENT_ONLY,
    RelationStatus.RECORD_DANGLING: TargetExistence.EVENT_ONLY,
}


def _canonical_sha256(payload: dict[str, str]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_single_line(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{field_name} must be exactly one line")
    return value


def _require_sha256(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return value


def build_event_identity(
    *,
    session_id: str,
    event_kind: str = SESSION_CLOSEOUT_EVENT_KIND,
    memory_type: str = SESSION_DERIVED_MEMORY_TYPE,
    writer: str = CANONICAL_MEMORY_WRITER,
) -> str:
    """Return the domain-separated identity of a session-closeout event."""

    payload = {
        "identity_schema": EVENT_IDENTITY_SCHEMA,
        "event_kind": _require_single_line(event_kind, field_name="event_kind"),
        "memory_type": _require_single_line(memory_type, field_name="memory_type"),
        "writer": _require_single_line(writer, field_name="writer"),
        "session_id": _require_single_line(session_id, field_name="session_id"),
    }
    return _canonical_sha256(payload)


def build_record_identity(
    *,
    event_identity: str,
    record_format_version: str,
    memory_type: str,
    writer: str,
    what_changed: str,
    commit_hash: str,
    test_evidence: str,
    next_step: str,
    plan_reconciliation: str,
) -> str:
    """Return the identity of one exact semantic record version."""

    payload = {
        "identity_schema": RECORD_IDENTITY_SCHEMA,
        "event_identity": _require_sha256(
            event_identity,
            field_name="event_identity",
        ),
        "record_format_version": _require_single_line(
            record_format_version,
            field_name="record_format_version",
        ),
        "memory_type": _require_single_line(memory_type, field_name="memory_type"),
        "writer": _require_single_line(writer, field_name="writer"),
        "what_changed": _require_single_line(
            what_changed,
            field_name="what_changed",
        ),
        "commit_hash": _require_single_line(commit_hash, field_name="commit_hash"),
        "test_evidence": _require_single_line(
            test_evidence,
            field_name="test_evidence",
        ),
        "next_step": _require_single_line(next_step, field_name="next_step"),
        "plan_reconciliation": _require_single_line(
            plan_reconciliation,
            field_name="plan_reconciliation",
        ),
    }
    return _canonical_sha256(payload)


def classify_record_attempt(
    *,
    previous_record_identity: str,
    candidate_record_identity: str,
    supersedes_record_identity: str | None = None,
) -> RecordAttemptKind:
    """Classify a same-event write as a retry or explicit correction.

    Changed content is fail-closed unless it explicitly supersedes the current
    record.  This function does not decide whether both records belong to the
    same event; the caller must establish that boundary first.
    """

    previous = _require_sha256(
        previous_record_identity,
        field_name="previous_record_identity",
    )
    candidate = _require_sha256(
        candidate_record_identity,
        field_name="candidate_record_identity",
    )
    if previous == candidate:
        if supersedes_record_identity is not None:
            raise ValueError("an idempotent retry must not declare supersession")
        return RecordAttemptKind.RETRY

    if supersedes_record_identity is None:
        raise ValueError(
            "changed same-event content requires supersedes_record_identity"
        )
    supersedes = _require_sha256(
        supersedes_record_identity,
        field_name="supersedes_record_identity",
    )
    if supersedes != previous:
        raise ValueError("supersedes_record_identity must name the current record")
    return RecordAttemptKind.CORRECTION


@dataclass(frozen=True)
class IdentityRelation:
    """One append-only legacy-to-event/record compatibility relation."""

    legacy_record_identity_v1: str
    event_identity: str
    record_identity_v2: str | None
    session_id: str
    target_existence: TargetExistence
    current_status: RelationStatus

    def validate(self) -> None:
        _require_sha256(
            self.legacy_record_identity_v1,
            field_name="legacy_record_identity_v1",
        )
        _require_sha256(self.event_identity, field_name="event_identity")
        _require_single_line(self.session_id, field_name="session_id")

        expected_target = _TARGET_BY_STATUS[self.current_status]
        if self.target_existence is not expected_target:
            raise ValueError(
                f"{self.current_status.value} requires "
                f"{expected_target.value}, not {self.target_existence.value}"
            )

        if self.target_existence is TargetExistence.RECORD_TARGET_PRESENT:
            if self.record_identity_v2 is None:
                raise ValueError(
                    "RECORD_TARGET_PRESENT requires record_identity_v2"
                )
            _require_sha256(
                self.record_identity_v2,
                field_name="record_identity_v2",
            )
        elif self.record_identity_v2 is not None:
            raise ValueError("EVENT_ONLY requires a null record_identity_v2")


@dataclass(frozen=True)
class RelationDimensionSummary:
    """Validated counts for the two orthogonal relation dimensions."""

    total: int
    target_counts: dict[TargetExistence, int]
    status_counts: dict[RelationStatus, int]

    @property
    def record_target_present(self) -> int:
        return self.target_counts.get(TargetExistence.RECORD_TARGET_PRESENT, 0)

    @property
    def event_only(self) -> int:
        return self.target_counts.get(TargetExistence.EVENT_ONLY, 0)

    @property
    def materialized(self) -> int:
        return self.status_counts.get(RelationStatus.MATERIALIZED, 0)

    @property
    def pending_source_preservation(self) -> int:
        return self.status_counts.get(
            RelationStatus.PENDING_SOURCE_PRESERVATION,
            0,
        )

    @property
    def record_version_unmaterialized(self) -> int:
        return self.status_counts.get(
            RelationStatus.RECORD_VERSION_UNMATERIALIZED,
            0,
        )

    @property
    def record_dangling(self) -> int:
        return self.status_counts.get(RelationStatus.RECORD_DANGLING, 0)

    def validate_cross_dimension_invariants(self) -> None:
        target_total = sum(self.target_counts.values())
        status_total = sum(self.status_counts.values())
        if target_total != self.total or status_total != self.total:
            raise ValueError("target and status dimensions must cover every relation")
        if (
            self.materialized + self.pending_source_preservation
            != self.record_target_present
        ):
            raise ValueError(
                "MATERIALIZED + PENDING_SOURCE_PRESERVATION must equal "
                "RECORD_TARGET_PRESENT"
            )
        if (
            self.record_version_unmaterialized + self.record_dangling
            != self.event_only
        ):
            raise ValueError(
                "RECORD_VERSION_UNMATERIALIZED + RECORD_DANGLING must equal "
                "EVENT_ONLY"
            )


def summarize_relations(
    relations: Iterable[IdentityRelation],
) -> RelationDimensionSummary:
    """Validate relations and return their two-dimensional count summary."""

    materialized = list(relations)
    seen_keys: set[tuple[str, str, str | None]] = set()
    for relation in materialized:
        relation.validate()
        key = (
            relation.legacy_record_identity_v1,
            relation.event_identity,
            relation.record_identity_v2,
        )
        if key in seen_keys:
            raise ValueError("duplicate legacy/event/record relation")
        seen_keys.add(key)

    summary = RelationDimensionSummary(
        total=len(materialized),
        target_counts=dict(Counter(r.target_existence for r in materialized)),
        status_counts=dict(Counter(r.current_status for r in materialized)),
    )
    summary.validate_cross_dimension_invariants()
    return summary
