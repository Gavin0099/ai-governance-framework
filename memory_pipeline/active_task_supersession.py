"""Bounded two-version supersession for the logical active-task surface."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from governance_tools import memory_record
from memory_pipeline import memory_layout


LOGICAL_NAME_ACTIVE_TASK = "active_task"
QUERY_CLASS_CURRENT_PROGRESS = "current_progress"
RESOLUTION_STATE_RESOLVED = "resolved"
CURRENT_STATE_BASE = "base_current"
CURRENT_STATE_SUPERSEDED = "superseded_current"
NON_RESOLVED_STATES = frozenset(
    {
        "reviewer_required",
        "disputed",
        "insufficient_authority",
        "unassessable",
    }
)

_PROJECTION_NAMESPACE = b"memory_record_projection:"
_SUPERSESSION_NAMESPACE = b"memory_runtime_supersession:"
_ACTIVE_TASK_PROJECTION = re.compile(
    rb"^- (.+) <!-- memory_record_projection:active-task-summary:([0-9a-f]{64}) -->$"
)
_ACTIVE_TASK_RELATION = re.compile(
    rb"^<!-- memory_runtime_supersession:active-task-summary:"
    rb"([0-9a-f]{64}):([0-9a-f]{64}):([0-9a-f]{64}):([0-9a-f]{64}) -->$"
)
_UNSUPPORTED_LINE_BOUNDARIES = (
    b"\x0b",
    b"\x0c",
    b"\x1c",
    b"\x1d",
    b"\x1e",
    "\x85".encode("utf-8"),
    "\u2028".encode("utf-8"),
    "\u2029".encode("utf-8"),
)
_SUMMARY_RESERVED_TOKENS = (
    b"memory_record_projection:",
    b"<!--",
    b"-->",
)
_AUTHORITY_SOURCES = frozenset({"current_human_instruction", "approved_change"})


@dataclass(frozen=True)
class _Version:
    record: dict[str, str]
    summary: str
    identity: str
    canonical_bytes: bytes
    payload: bytes
    digest: str


@dataclass(frozen=True)
class _Relation:
    predecessor_identity: str
    predecessor_digest: str
    successor_identity: str
    successor_digest: str
    payload: bytes


@dataclass(frozen=True)
class _SurfaceSnapshot:
    raw_bytes: bytes
    projections: tuple[tuple[str, bytes], ...]
    relations: tuple[_Relation, ...]


def supersede_active_task(
    *,
    project_root: Path,
    memory_root: Path,
    logical_name: str,
    predecessor_record: dict[str, str],
    predecessor_summary: str,
    successor_record: dict[str, str],
    successor_summary: str,
    authority_observation: Mapping[str, Any],
) -> tuple[str, bytes]:
    """Persist one authorized v1-to-v2 relation and return only v2 context."""

    inputs = _snapshot_inputs(
        predecessor_record=predecessor_record,
        predecessor_summary=predecessor_summary,
        successor_record=successor_record,
        successor_summary=successor_summary,
        authority_observation=authority_observation,
    )
    path = _validate_roots_and_resolve(
        project_root=project_root,
        memory_root=memory_root,
        logical_name=logical_name,
    )
    predecessor = _build_version(*inputs[:2])
    successor = _build_version(*inputs[2:4])
    if predecessor.identity == successor.identity:
        raise ValueError("active-task supersession identities must be distinct")

    prewrite = _read_surface(path)
    state = _classify_snapshot(
        prewrite,
        predecessor=predecessor,
        successor=successor,
    )
    authority_state = _validate_authority_observation(
        inputs[4],
        predecessor=predecessor,
        successor=successor,
    )
    if authority_state in NON_RESOLVED_STATES:
        return authority_state, b""

    if state == CURRENT_STATE_SUPERSEDED:
        return CURRENT_STATE_SUPERSEDED, successor.canonical_bytes

    if state == CURRENT_STATE_BASE:
        _append_successor_projection(
            project_root=project_root,
            path=path,
            successor=successor,
        )

    _append_relation(
        project_root=project_root,
        path=path,
        predecessor=predecessor,
        successor=successor,
    )

    final_snapshot = _read_surface(path)
    final_state = _classify_snapshot(
        final_snapshot,
        predecessor=predecessor,
        successor=successor,
    )
    if final_state != CURRENT_STATE_SUPERSEDED:
        raise ValueError("active-task supersession final snapshot is incomplete")
    return CURRENT_STATE_SUPERSEDED, successor.canonical_bytes


def select_current_active_task(
    *,
    project_root: Path,
    memory_root: Path,
    logical_name: str,
    predecessor_record: dict[str, str],
    predecessor_summary: str,
    successor_record: dict[str, str] | None = None,
    successor_summary: str | None = None,
    authority_observation: Mapping[str, Any] | None = None,
) -> tuple[str, bytes]:
    """Read one bounded v1-only or complete v1-to-v2 lineage."""

    _validate_basic_inputs(
        predecessor_record=predecessor_record,
        predecessor_summary=predecessor_summary,
    )
    path = _validate_roots_and_resolve(
        project_root=project_root,
        memory_root=memory_root,
        logical_name=logical_name,
    )
    predecessor = _build_version(dict(predecessor_record), predecessor_summary)
    snapshot = _read_surface(path)

    successor_values = (successor_record, successor_summary, authority_observation)
    if all(value is None for value in successor_values):
        _validate_base_snapshot(snapshot, predecessor=predecessor)
        return CURRENT_STATE_BASE, predecessor.canonical_bytes
    if any(value is None for value in successor_values):
        raise ValueError("successor record, summary, and authorization must be supplied together")
    if not isinstance(successor_record, dict) or not isinstance(successor_summary, str):
        raise ValueError("successor record and summary types are invalid")
    if not isinstance(authority_observation, Mapping):
        raise ValueError("authority_observation must be exactly one mapping")

    try:
        successor_snapshot = dict(successor_record)
        authority_snapshot = dict(authority_observation)
    except Exception as exc:
        raise ValueError("R1 input snapshot failed") from exc
    successor = _build_version(successor_snapshot, successor_summary)
    if predecessor.identity == successor.identity:
        raise ValueError("active-task supersession identities must be distinct")
    state = _classify_snapshot(
        snapshot,
        predecessor=predecessor,
        successor=successor,
    )
    authority_state = _validate_authority_observation(
        authority_snapshot,
        predecessor=predecessor,
        successor=successor,
    )
    if authority_state in NON_RESOLVED_STATES:
        return authority_state, b""
    if state != CURRENT_STATE_SUPERSEDED:
        raise ValueError("active-task supersession has no unique current record")
    return CURRENT_STATE_SUPERSEDED, successor.canonical_bytes


def _snapshot_inputs(
    *,
    predecessor_record: object,
    predecessor_summary: object,
    successor_record: object,
    successor_summary: object,
    authority_observation: object,
) -> tuple[dict[str, str], str, dict[str, str], str, dict[str, Any]]:
    _validate_basic_inputs(
        predecessor_record=predecessor_record,
        predecessor_summary=predecessor_summary,
    )
    if not isinstance(successor_record, dict):
        raise ValueError("successor_record must be a dict")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in successor_record.items()
    ):
        raise ValueError("successor record keys and values must be strings")
    if not isinstance(successor_summary, str):
        raise ValueError("successor_summary must be a string")
    if not isinstance(authority_observation, Mapping):
        raise ValueError("authority_observation must be exactly one mapping")
    try:
        return (
            dict(predecessor_record),
            predecessor_summary,
            dict(successor_record),
            successor_summary,
            dict(authority_observation),
        )
    except Exception as exc:
        raise ValueError("R1 input snapshot failed") from exc


def _validate_basic_inputs(
    *,
    predecessor_record: object,
    predecessor_summary: object,
) -> None:
    if not isinstance(predecessor_record, dict):
        raise ValueError("predecessor_record must be a dict")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in predecessor_record.items()
    ):
        raise ValueError("predecessor record keys and values must be strings")
    if not isinstance(predecessor_summary, str):
        raise ValueError("predecessor_summary must be a string")


def _validate_roots_and_resolve(
    *,
    project_root: object,
    memory_root: object,
    logical_name: object,
) -> Path:
    if not isinstance(project_root, Path) or not isinstance(memory_root, Path):
        raise ValueError("project_root and memory_root must be pathlib.Path values")
    if logical_name != LOGICAL_NAME_ACTIVE_TASK:
        raise ValueError("logical_name must be the configured active_task surface")
    if not project_root.is_absolute() or not memory_root.is_absolute():
        raise ValueError("R1 roots must be absolute")
    try:
        project_is_directory = project_root.exists() and project_root.is_dir()
        memory_is_directory = memory_root.exists() and memory_root.is_dir()
        canonical_project = project_root.resolve(strict=True)
        canonical_memory = memory_root.resolve(strict=True)
    except Exception as exc:
        raise ValueError("R1 root validation failed") from exc
    if not project_is_directory or not memory_is_directory:
        raise ValueError("R1 roots must exist and be directories")
    if project_root != canonical_project or memory_root != canonical_memory:
        raise ValueError("R1 roots must be canonical")
    if canonical_memory != canonical_project / "memory":
        raise ValueError("memory_root must be the canonical project memory root")
    try:
        git_marker = canonical_project / ".git"
        has_git_marker = git_marker.is_dir() or git_marker.is_file()
    except Exception as exc:
        raise ValueError("R1 repository root marker validation failed") from exc
    if not has_git_marker:
        raise ValueError("project_root must be a Git worktree root")
    if logical_name not in memory_layout.MEMORY_FILE_ALIASES:
        raise ValueError("logical_name must be defined in MEMORY_FILE_ALIASES")
    try:
        resolver = memory_layout.resolve_memory_file
        resolved_path = resolver(memory_root, logical_name)
    except Exception as exc:
        raise ValueError("logical active-task resolution failed") from exc
    if not isinstance(resolved_path, Path):
        raise ValueError("logical resolver returned an invalid path")
    writer_path = canonical_project / "memory" / "01_active_task.md"
    if resolved_path != writer_path:
        raise ValueError("relation writer path does not match logical resolver path")
    return resolved_path


def _build_version(record: dict[str, str], summary: str) -> _Version:
    try:
        identity = memory_record.build_record_identity(record)
        if record.get("record_identity") != identity:
            raise ValueError("caller record identity does not match canonical identity")
        rendered = memory_record.render_active_task_projection(record, summary=summary)
        canonical_bytes = rendered.encode("utf-8", errors="strict")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("canonical active-task version rendering failed") from exc
    if not canonical_bytes.endswith(b"\n") or canonical_bytes.endswith(b"\r\n"):
        raise ValueError("canonical active-task projection must end with one LF")
    return _Version(
        record=record,
        summary=summary,
        identity=identity,
        canonical_bytes=canonical_bytes,
        payload=canonical_bytes[:-1],
        digest=hashlib.sha256(canonical_bytes).hexdigest(),
    )


def _read_surface(path: Path) -> _SurfaceSnapshot:
    try:
        exists = path.exists()
        is_file = path.is_file()
    except Exception as exc:
        raise ValueError("active-task surface existence check failed") from exc
    if not exists or not is_file:
        raise ValueError("active-task projection surface must exist as a file")
    try:
        raw_bytes = path.read_bytes()
    except Exception as exc:
        raise ValueError("active-task projection surface read failed") from exc
    projections, relations = _parse_surface(raw_bytes)
    return _SurfaceSnapshot(
        raw_bytes=raw_bytes,
        projections=projections,
        relations=relations,
    )


def _parse_surface(
    raw_bytes: bytes,
) -> tuple[tuple[tuple[str, bytes], ...], tuple[_Relation, ...]]:
    try:
        text_snapshot = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("active-task surface is not strict UTF-8") from exc
    if text_snapshot.encode("utf-8", errors="strict") != raw_bytes:
        raise ValueError("active-task UTF-8 snapshot changed")
    if any(boundary in raw_bytes for boundary in _UNSUPPORTED_LINE_BOUNDARIES):
        raise ValueError("active-task surface contains an unsupported line boundary")
    if b"\r" in raw_bytes.replace(b"\r\n", b""):
        raise ValueError("active-task surface contains a bare CR")

    projections: list[tuple[str, bytes]] = []
    relations: list[_Relation] = []
    for framed_line in raw_bytes.splitlines(keepends=True):
        is_projection = _PROJECTION_NAMESPACE in framed_line
        is_relation = _SUPERSESSION_NAMESPACE in framed_line
        if not is_projection and not is_relation:
            continue
        if framed_line.endswith(b"\r\n"):
            payload = framed_line[:-2]
        elif framed_line.endswith(b"\n"):
            payload = framed_line[:-1]
        else:
            raise ValueError("active-task structured line has an unsupported terminator")

        if is_projection:
            match = _ACTIVE_TASK_PROJECTION.fullmatch(payload)
            if match is None:
                raise ValueError("active-task projection line is malformed")
            summary, identity_bytes = match.groups()
            if not summary or summary.strip() != summary:
                raise ValueError("active-task projection summary whitespace is invalid")
            if any(token in summary for token in _SUMMARY_RESERVED_TOKENS):
                raise ValueError("active-task projection summary contains reserved syntax")
            projections.append((identity_bytes.decode("ascii"), payload))
            continue

        match = _ACTIVE_TASK_RELATION.fullmatch(payload)
        if match is None:
            raise ValueError("active-task supersession relation is malformed")
        predecessor_identity, predecessor_digest, successor_identity, successor_digest = (
            part.decode("ascii") for part in match.groups()
        )
        if predecessor_identity == successor_identity:
            raise ValueError("active-task supersession relation is self-referential")
        relations.append(
            _Relation(
                predecessor_identity=predecessor_identity,
                predecessor_digest=predecessor_digest,
                successor_identity=successor_identity,
                successor_digest=successor_digest,
                payload=payload,
            )
        )
    return tuple(projections), tuple(relations)


def _validate_base_snapshot(
    snapshot: _SurfaceSnapshot,
    *,
    predecessor: _Version,
) -> None:
    _require_exact_projection(snapshot, version=predecessor, allow_missing=False)
    if any(
        relation.predecessor_identity == predecessor.identity
        or relation.successor_identity == predecessor.identity
        for relation in snapshot.relations
    ):
        raise ValueError("base active-task record already participates in a relation")


def _classify_snapshot(
    snapshot: _SurfaceSnapshot,
    *,
    predecessor: _Version,
    successor: _Version,
) -> str:
    _require_exact_projection(snapshot, version=predecessor, allow_missing=False)
    successor_present = _require_exact_projection(
        snapshot,
        version=successor,
        allow_missing=True,
    )
    endpoint_identities = {predecessor.identity, successor.identity}
    involving = tuple(
        relation
        for relation in snapshot.relations
        if relation.predecessor_identity in endpoint_identities
        or relation.successor_identity in endpoint_identities
    )
    if not successor_present:
        if involving:
            raise ValueError("active-task relation names a missing successor")
        return CURRENT_STATE_BASE
    if not involving:
        return "recoverable_partial"
    expected = (
        predecessor.identity,
        predecessor.digest,
        successor.identity,
        successor.digest,
    )
    actual = tuple(
        (
            relation.predecessor_identity,
            relation.predecessor_digest,
            relation.successor_identity,
            relation.successor_digest,
        )
        for relation in involving
    )
    if actual != (expected,):
        raise ValueError("active-task supersession relation is duplicate or conflicting")
    return CURRENT_STATE_SUPERSEDED


def _require_exact_projection(
    snapshot: _SurfaceSnapshot,
    *,
    version: _Version,
    allow_missing: bool,
) -> bool:
    payloads = [
        payload
        for identity, payload in snapshot.projections
        if identity == version.identity
    ]
    if not payloads and allow_missing:
        return False
    if len(payloads) != 1:
        raise ValueError("active-task endpoint must exist exactly once")
    if payloads[0] != version.payload:
        raise ValueError("active-task endpoint payload does not match canonical projection")
    return True


def _validate_authority_observation(
    observation: dict[str, Any],
    *,
    predecessor: _Version,
    successor: _Version,
) -> str:
    expected_common = {
        "decision": "supersede",
        "logical_name": LOGICAL_NAME_ACTIVE_TASK,
        "query_class": QUERY_CLASS_CURRENT_PROGRESS,
        "predecessor_record_identity": predecessor.identity,
        "predecessor_projection_sha256": predecessor.digest,
        "successor_record_identity": successor.identity,
        "successor_projection_sha256": successor.digest,
    }
    for field_name, expected in expected_common.items():
        value = observation.get(field_name)
        if not isinstance(value, str) or value != expected:
            raise ValueError(f"supersession authorization {field_name} mismatch")

    state = observation.get("resolution_state")
    if not isinstance(state, str):
        raise ValueError("supersession authorization resolution_state is invalid")
    if state in NON_RESOLVED_STATES:
        return state
    if state != RESOLUTION_STATE_RESOLVED:
        raise ValueError("supersession authorization resolution_state is invalid")

    required_resolved = {
        "projection_status": "current",
        "review_status": "reviewed",
        "reviewer_authority_state": "authority_qualified",
        "anchor_state": "covers_latest_qualified_evidence",
        "state_transition_coverage": "covers_latest_substantive_transition",
        "later_change_state": "none_unreconciled",
        "coverage_boundary_state": "determinable_without_semantic_guessing",
    }
    for field_name, expected in required_resolved.items():
        value = observation.get(field_name)
        if not isinstance(value, str) or value != expected:
            raise ValueError(f"resolved supersession authorization {field_name} mismatch")
    authority_source = observation.get("authority_source")
    if not isinstance(authority_source, str) or authority_source not in _AUTHORITY_SOURCES:
        raise ValueError("resolved supersession authorization source is invalid")
    source_anchor = observation.get("source_anchor")
    if (
        not isinstance(source_anchor, str)
        or not source_anchor
        or source_anchor.strip() != source_anchor
        or any(boundary in source_anchor for boundary in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
    ):
        raise ValueError("resolved supersession authorization source anchor is invalid")
    return RESOLUTION_STATE_RESOLVED


def _append_successor_projection(
    *,
    project_root: Path,
    path: Path,
    successor: _Version,
) -> None:
    try:
        writer = memory_record.append_projection_with_outcome
        outcome = writer(
            project_root=project_root,
            record=successor.record,
            surface=memory_record.SURFACE_ACTIVE_TASK_SUMMARY,
            active_task_summary=successor.summary,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("canonical successor projection write failed") from exc
    _validate_write_outcome(outcome, path=path, identity=successor.identity)


def _append_relation(
    *,
    project_root: Path,
    path: Path,
    predecessor: _Version,
    successor: _Version,
) -> None:
    try:
        writer = memory_record.append_active_task_supersession_relation_with_outcome
        outcome = writer(
            project_root=project_root,
            predecessor_record_identity=predecessor.identity,
            predecessor_projection_sha256=predecessor.digest,
            successor_record_identity=successor.identity,
            successor_projection_sha256=successor.digest,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("active-task supersession relation write failed") from exc
    _validate_write_outcome(outcome, path=path, identity=successor.identity)


def _validate_write_outcome(
    outcome: object,
    *,
    path: Path,
    identity: str,
) -> None:
    try:
        outcome_path = outcome.path  # type: ignore[attr-defined]
        outcome_status = outcome.status  # type: ignore[attr-defined]
        outcome_identity = outcome.record_identity  # type: ignore[attr-defined]
    except Exception as exc:
        raise ValueError("active-task writer returned an invalid outcome") from exc
    if not isinstance(outcome_path, Path) or outcome_path != path:
        raise ValueError("active-task writer returned an unexpected path")
    if not isinstance(outcome_status, str) or outcome_status not in {
        memory_record.MEMORY_WRITE_STATUS_WRITTEN,
        memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
    }:
        raise ValueError("active-task writer returned an unsupported status")
    if not isinstance(outcome_identity, str) or outcome_identity != identity:
        raise ValueError("active-task writer returned an unexpected identity")
