"""Bounded exact round trip for one caller-authorized active-task record."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from governance_tools import memory_record
from memory_pipeline import memory_layout


LOGICAL_NAME_ACTIVE_TASK = "active_task"
QUERY_CLASS_CURRENT_PROGRESS = "current_progress"
RESOLUTION_STATE_RESOLVED = "resolved"
NON_RESOLVED_STATES = frozenset(
    {
        "reviewer_required",
        "disputed",
        "insufficient_authority",
        "unassessable",
    }
)

_PROJECTION_MARKER_NAMESPACE = b"memory_record_projection:"
_ACTIVE_TASK_LINE = re.compile(
    rb"^- (.+) <!-- memory_record_projection:active-task-summary:([0-9a-f]{64}) -->$"
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SUMMARY_RESERVED_TOKENS = (
    b"memory_record_projection:",
    b"<!--",
    b"-->",
)
_SUMMARY_LINE_BOUNDARIES = (
    b"\n",
    b"\r",
    b"\x0b",
    b"\x0c",
    b"\x1c",
    b"\x1d",
    b"\x1e",
    "\x85".encode("utf-8"),
    "\u2028".encode("utf-8"),
    "\u2029".encode("utf-8"),
)


def round_trip_active_task(
    *,
    project_root: Path,
    memory_root: Path,
    logical_name: str,
    record: dict[str, str],
    summary: str,
    authority_observation: Mapping[str, Any],
    m1b3_observation: Mapping[str, Any] | None = None,
) -> tuple[str, bytes]:
    """Write, retrieve, verify, and render one active-task projection.

    The return value is intentionally minimal: the preserved semantic
    disposition and either one canonical LF context line or ``b""``.
    Transport and public result-schema concerns are outside R0.
    """

    _validate_inputs(
        project_root=project_root,
        memory_root=memory_root,
        logical_name=logical_name,
        record=record,
        summary=summary,
        authority_observation=authority_observation,
        m1b3_observation=m1b3_observation,
    )

    try:
        record_snapshot = dict(record)
        observation_snapshot = dict(authority_observation)
        m1b3_snapshot = None if m1b3_observation is None else dict(m1b3_observation)
    except Exception as exc:
        raise ValueError("R0 input snapshot failed") from exc

    try:
        identity_builder = memory_record.build_record_identity
        expected_identity = identity_builder(record_snapshot)
        if record_snapshot.get("record_identity") != expected_identity:
            raise ValueError("caller record identity does not match canonical identity")

        renderer = memory_record.render_active_task_projection
        expected_line = renderer(record_snapshot, summary=summary)
        expected_bytes = expected_line.encode("utf-8", errors="strict")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("canonical identity or projection rendering failed") from exc

    if not expected_bytes.endswith(b"\n") or expected_bytes.endswith(b"\r\n"):
        raise ValueError("canonical projection must contain one terminal LF")
    expected_payload = expected_bytes[:-1]
    expected_digest = hashlib.sha256(expected_bytes).hexdigest()

    resolution_state = _validate_authority_observation(
        observation_snapshot,
        expected_identity=expected_identity,
        expected_digest=expected_digest,
    )

    try:
        writer = memory_record.append_projection_with_outcome
        writer_result = writer(
            project_root=project_root,
            record=record_snapshot,
            surface=memory_record.SURFACE_ACTIVE_TASK_SUMMARY,
            active_task_summary=summary,
        )
        writer_path = writer_result.path
        writer_status = writer_result.status
        writer_identity = writer_result.record_identity
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("canonical active-task write failed") from exc

    if not isinstance(writer_path, Path):
        raise ValueError("canonical writer returned an invalid path")
    if not isinstance(writer_status, str) or writer_status not in {
        memory_record.MEMORY_WRITE_STATUS_WRITTEN,
        memory_record.MEMORY_WRITE_STATUS_ALREADY_PRESENT,
    }:
        raise ValueError("canonical writer returned an unsupported status")
    if writer_identity != expected_identity:
        raise ValueError("canonical writer identity mismatch")

    try:
        resolver = memory_layout.resolve_memory_file
        resolved_path = resolver(memory_root, logical_name)
    except Exception as exc:
        raise ValueError("logical active-task resolution failed") from exc
    if not isinstance(resolved_path, Path):
        raise ValueError("logical resolver returned an invalid path")
    if writer_path != resolved_path:
        raise ValueError("canonical writer path does not match logical resolver path")

    _validate_m1b3_observation(
        m1b3_snapshot,
        logical_name=logical_name,
        resolved_path=resolved_path,
    )

    try:
        resolved_exists = resolved_path.exists()
    except Exception as exc:
        raise ValueError("resolved active-task existence check failed") from exc
    if not resolved_exists:
        raise ValueError("resolved active-task surface is missing")

    try:
        persisted_bytes = resolved_path.read_bytes()
    except Exception as exc:
        raise ValueError("resolved active-task read failed") from exc
    try:
        persisted_text = persisted_bytes.decode("utf-8", errors="strict")
    except Exception as exc:
        raise ValueError("resolved active-task surface is not strict UTF-8") from exc

    candidates = _parse_projection_candidates(
        persisted_text,
        persisted_bytes=persisted_bytes,
    )
    target_payloads = [
        payload
        for identity, payload in candidates
        if identity == expected_identity
    ]
    if len(target_payloads) != 1:
        raise ValueError("expected exactly one persisted active-task identity")
    if target_payloads[0] != expected_payload:
        raise ValueError("persisted active-task payload does not match canonical projection")

    if resolution_state in NON_RESOLVED_STATES:
        return resolution_state, b""
    return RESOLUTION_STATE_RESOLVED, expected_bytes


def _validate_inputs(
    *,
    project_root: object,
    memory_root: object,
    logical_name: object,
    record: object,
    summary: object,
    authority_observation: object,
    m1b3_observation: object,
) -> None:
    if not isinstance(project_root, Path):
        raise ValueError("project_root must be a pathlib.Path")
    if not isinstance(memory_root, Path):
        raise ValueError("memory_root must be a pathlib.Path")
    if not isinstance(logical_name, str):
        raise ValueError("logical_name must be a string")
    if logical_name != LOGICAL_NAME_ACTIVE_TASK:
        raise ValueError("logical_name must be the configured active_task surface")
    if logical_name not in memory_layout.MEMORY_FILE_ALIASES:
        raise ValueError("logical_name must be defined in MEMORY_FILE_ALIASES")
    _validate_canonical_roots(project_root=project_root, memory_root=memory_root)
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in record.items()):
        raise ValueError("record keys and values must be strings")
    if not isinstance(summary, str):
        raise ValueError("summary must be a string")
    if not isinstance(authority_observation, Mapping):
        raise ValueError("authority_observation must be exactly one mapping")
    if m1b3_observation is not None and not isinstance(m1b3_observation, Mapping):
        raise ValueError("m1b3_observation must be one mapping when provided")


def _validate_canonical_roots(*, project_root: Path, memory_root: Path) -> None:
    if not project_root.is_absolute():
        raise ValueError("project_root must be absolute")
    if not memory_root.is_absolute():
        raise ValueError("memory_root must be absolute")
    try:
        project_root_is_directory = project_root.exists() and project_root.is_dir()
        memory_root_is_directory = memory_root.exists() and memory_root.is_dir()
    except Exception as exc:
        raise ValueError("R0 root validation failed") from exc
    if not project_root_is_directory:
        raise ValueError("project_root must exist and be a directory")
    if not memory_root_is_directory:
        raise ValueError("memory_root must exist and be a directory")
    try:
        canonical_project_root = project_root.resolve(strict=True)
        canonical_memory_root = memory_root.resolve(strict=True)
    except Exception as exc:
        raise ValueError("R0 canonical root resolution failed") from exc
    if project_root != canonical_project_root:
        raise ValueError("project_root must be canonical")
    if memory_root != canonical_memory_root:
        raise ValueError("memory_root must be canonical")
    if canonical_memory_root != canonical_project_root / "memory":
        raise ValueError("memory_root must be the canonical project memory root")
    try:
        git_marker = canonical_project_root / ".git"
        project_root_has_git_marker = git_marker.is_dir() or git_marker.is_file()
    except Exception as exc:
        raise ValueError("R0 repository root marker validation failed") from exc
    if not project_root_has_git_marker:
        raise ValueError("project_root must be a Git worktree root")


def _validate_authority_observation(
    observation: dict[str, Any],
    *,
    expected_identity: str,
    expected_digest: str,
) -> str:
    if observation.get("query_class") != QUERY_CLASS_CURRENT_PROGRESS:
        raise ValueError("authority observation query_class mismatch")
    if observation.get("logical_name") != LOGICAL_NAME_ACTIVE_TASK:
        raise ValueError("authority observation logical_name mismatch")
    if observation.get("requested_record_identity") != expected_identity:
        raise ValueError("authority observation requested identity mismatch")

    state = observation.get("resolution_state")
    if not isinstance(state, str):
        raise ValueError("authority observation has an invalid resolution state")
    if state in NON_RESOLVED_STATES:
        return state
    if state != RESOLUTION_STATE_RESOLVED:
        raise ValueError("authority observation has an invalid resolution state")
    if observation.get("resolved_record_identity") != expected_identity:
        raise ValueError("resolved authority identity mismatch")
    digest = observation.get("authorized_projection_sha256")
    if not isinstance(digest, str) or _LOWER_SHA256.fullmatch(digest) is None:
        raise ValueError("resolved authority projection digest is malformed")
    if digest != expected_digest:
        raise ValueError("resolved authority projection digest mismatch")
    return RESOLUTION_STATE_RESOLVED


def _validate_m1b3_observation(
    observation: dict[str, Any] | None,
    *,
    logical_name: str,
    resolved_path: Path,
) -> None:
    if observation is None:
        return
    findings = observation.get("findings")
    if not isinstance(findings, list):
        raise ValueError("M1b-3 observation findings must be a list")
    if not findings:
        return
    if len(findings) != 1 or not isinstance(findings[0], Mapping):
        raise ValueError("M1b-3 observation must contain at most one finding")
    finding = findings[0]
    if finding.get("code") != "missing_logical_memory_surface":
        raise ValueError("M1b-3 observation contains an unsupported finding")
    if finding.get("logical_name") != logical_name:
        raise ValueError("M1b-3 finding logical_name mismatch")
    if finding.get("resolved_path") != str(resolved_path):
        raise ValueError("M1b-3 finding resolved_path mismatch")


def _parse_projection_candidates(
    persisted_text: str,
    *,
    persisted_bytes: bytes,
) -> tuple[tuple[str, bytes], ...]:
    # The strict decode above establishes the text snapshot. Re-encoding it
    # must recover the exact buffer before byte-framing decisions are made.
    if persisted_text.encode("utf-8", errors="strict") != persisted_bytes:
        raise ValueError("resolved active-task UTF-8 snapshot changed")

    candidates: list[tuple[str, bytes]] = []
    for framed_line in persisted_bytes.splitlines(keepends=True):
        if _PROJECTION_MARKER_NAMESPACE not in framed_line:
            continue
        if framed_line.endswith(b"\r\n"):
            payload = framed_line[:-2]
        elif framed_line.endswith(b"\n"):
            payload = framed_line[:-1]
        else:
            raise ValueError("projection-looking line has an unsupported terminator")
        if b"\r" in payload:
            raise ValueError("projection-looking line contains a bare CR")

        match = _ACTIVE_TASK_LINE.fullmatch(payload)
        if match is None:
            raise ValueError("projection-looking line has malformed active-task grammar")
        summary, identity_bytes = match.groups()
        if not summary or summary.strip() != summary:
            raise ValueError("persisted active-task summary whitespace is invalid")
        if any(boundary in summary for boundary in _SUMMARY_LINE_BOUNDARIES):
            raise ValueError("persisted active-task summary contains a line boundary")
        if any(token in summary for token in _SUMMARY_RESERVED_TOKENS):
            raise ValueError("persisted active-task summary contains reserved syntax")
        candidates.append((identity_bytes.decode("ascii"), payload))
    return tuple(candidates)
