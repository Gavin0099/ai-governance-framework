#!/usr/bin/env python3
"""
Canonical closeout producer.

Trust boundary:
  - AI output (candidate) is untrusted input.
  - This module validates, normalizes, and produces the canonical closeout artifact.
  - Only this module may write to artifacts/runtime/closeouts/.

Caller (run_session_end) is responsible for all IO before calling build_canonical_closeout():
  - load candidate via pick_latest_candidate()
  - supply closed_at from datetime.now()
  - supply existing_artifacts snapshot
  - supply runtime_signals from session

build_canonical_closeout() is a pure function: no filesystem IO, no timestamp generation.
Same inputs → same canonical output. Enables replay, audit re-run, dry-run testing.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Controlled vocabulary for closeout_status
_VALID_STATUSES = frozenset({
    "valid",
    "missing",
    "schema_invalid",
    "content_insufficient",
    "inconsistent",
})

# Tool names that imply verifiable execution traces.
# FROZEN TAXONOMY — do not extend without updating docs/closeout-schema.md.
# Matching is case-insensitive (lowercased before comparison).
# Normalization is NOT performed: "python -m pytest" does NOT match "pytest".
# Callers that want fuzzy matching must normalize tool names before supplying
# runtime_signals["tools_executed"].
_VERIFIABLE_TOOLS = frozenset({"pytest", "build", "lint", "test", "make"})

# Required fields in candidate payload
_CANDIDATE_REQUIRED_FIELDS: dict[str, type] = {
    "task_intent": str,
    "work_summary": str,
    "tools_used": list,
    "artifacts_referenced": list,
    "open_risks": list,
}

# Session ID lifecycle — written by /wrap-up, consumed by session_end
_CURRENT_SESSION_ID_FILE = ".current-session-id"
_RUNTIME_CURRENT_SESSION_ID_FILE = Path("artifacts/runtime/.current-session-id")
_CURRENT_SESSION_ID_STALENESS_SECONDS = 12 * 3600  # 12 hours
_SESSION_ENVELOPE_SCHEMA_VERSION = "1.0"


def _parse_aware_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _resolve_head_commit(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _session_envelope_path(session_id: str, project_root: Path) -> Path:
    return (
        project_root
        / "artifacts"
        / "runtime"
        / "sessions"
        / session_id
        / "session-envelope.json"
    )


def write_session_envelope(
    session_id: str,
    project_root: Path,
    *,
    provider: str = "unknown",
    started_at: str | None = None,
    repo_head_before: str | None = None,
) -> dict[str, Any]:
    """Create the session-start identity envelope used by closeout binding."""
    normalized_session_id = session_id.strip()
    if not normalized_session_id:
        raise ValueError("session_id is required")
    normalized_started_at = started_at or datetime.now(timezone.utc).isoformat()
    if _parse_aware_utc(normalized_started_at) is None:
        raise ValueError("started_at must be a timezone-aware ISO-8601 timestamp")

    path = _session_envelope_path(normalized_session_id, project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": _SESSION_ENVELOPE_SCHEMA_VERSION,
        "session_id": normalized_session_id,
        "started_at": normalized_started_at,
        "provider": provider.strip() or "unknown",
        "repo_head_before": (
            repo_head_before
            if repo_head_before is not None
            else _resolve_head_commit(project_root)
        ),
        "closeout_path": "artifacts/session-closeout.txt",
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_current_session_id_payload(
        normalized_session_id,
        project_root / _RUNTIME_CURRENT_SESSION_ID_FILE,
    )
    return {**payload, "artifact_path": str(path)}


def read_session_envelope(session_id: str, project_root: Path) -> dict[str, Any] | None:
    """Read and minimally validate the envelope for exactly one session."""
    path = _session_envelope_path(session_id, project_root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != _SESSION_ENVELOPE_SCHEMA_VERSION:
        return None
    if str(payload.get("session_id") or "") != session_id:
        return None
    if _parse_aware_utc(str(payload.get("started_at") or "")) is None:
        return None
    return {**payload, "artifact_path": str(path)}


def assess_session_closeout_binding(
    session_id: str,
    project_root: Path,
    candidate_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assess session ownership and consume-once state before side effects."""
    canonical_path = project_root / "artifacts" / "runtime" / "closeouts" / f"{session_id}.json"
    completion_path = (
        project_root
        / "artifacts"
        / "runtime"
        / "closeout-completions"
        / f"{session_id}.json"
    )
    completion = _read_valid_closeout_completion(
        session_id,
        project_root,
        completion_path,
    )
    if completion is not None:
        return {
            "status": "already_consumed",
            "session_id": session_id,
            "canonical_closeout_path": str(canonical_path),
            "completion_marker_path": str(completion_path),
        }

    # A canonical artifact without its create-last completion marker is a
    # partial prior invocation.  It must be recovered explicitly; treating it
    # as a fresh closeout would re-read the repository-wide legacy closeout
    # file and could bind another task's prose to this session.
    if canonical_path.is_file():
        return {
            "status": "canonical_closeout_incomplete",
            "session_id": session_id,
            "canonical_closeout_path": str(canonical_path),
            "completion_marker_path": str(completion_path),
        }

    envelope = read_session_envelope(session_id, project_root)
    if envelope is None:
        return {"status": "session_envelope_missing", "session_id": session_id}
    if candidate_payload is None:
        return {
            "status": "session_candidate_missing",
            "session_id": session_id,
            "session_envelope_path": envelope["artifact_path"],
        }

    candidate_session_id = str(candidate_payload.get("session_id") or "")
    if candidate_session_id != session_id:
        return {
            "status": "session_candidate_mismatch",
            "session_id": session_id,
            "candidate_session_id": candidate_session_id,
            "session_envelope_path": envelope["artifact_path"],
        }

    schema_ok, schema_reason = _validate_candidate_schema(candidate_payload)
    if not schema_ok:
        return {
            "status": "session_candidate_schema_invalid",
            "session_id": session_id,
            "session_envelope_path": envelope["artifact_path"],
            "schema_reason": schema_reason,
        }

    started_at = _parse_aware_utc(str(envelope.get("started_at") or ""))
    generated_at = _parse_aware_utc(str(candidate_payload.get("generated_at") or ""))
    if generated_at is None:
        return {
            "status": "candidate_generated_at_missing",
            "session_id": session_id,
            "session_envelope_path": envelope["artifact_path"],
        }
    if started_at is None or generated_at < started_at:
        return {
            "status": "candidate_before_session_start",
            "session_id": session_id,
            "session_envelope_path": envelope["artifact_path"],
            "candidate_generated_at": generated_at.isoformat(),
            "session_started_at": started_at.isoformat() if started_at else "",
        }
    return {
        "status": "valid",
        "session_id": session_id,
        "session_envelope_path": envelope["artifact_path"],
        "candidate_generated_at": generated_at.isoformat(),
        "session_started_at": started_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick_latest_candidate(session_id: str, project_root: Path) -> dict[str, Any] | None:
    """
    Load the most recent candidate closeout for session_id.

    Returns the parsed dict, or None if no candidate exists.
    Candidates are stored at:
        artifacts/runtime/closeout_candidates/{session_id}/{timestamp}.json

    Timestamp filenames are lexicographically sortable (YYYYmmddTHHMMSSffffffZ).
    "Latest" means authoring precedence — last written, not most complete.
    """
    candidates_dir = (
        project_root / "artifacts" / "runtime" / "closeout_candidates" / session_id
    )
    if not candidates_dir.is_dir():
        return None

    files = sorted(candidates_dir.glob("*.json"))
    if not files:
        return None

    latest = files[-1]
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_canonical_closeout(
    *,
    session_id: str,
    closed_at: str,
    candidate_payload: dict[str, Any] | None,
    existing_artifacts: frozenset[str],
    runtime_signals: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Pure function: validate + normalize candidate → canonical closeout dict.

    GUARANTEE: never raises. Any input produces a valid canonical dict.
    The worst case is closeout_status = "missing" or "schema_invalid"; a
    canonical result is always assembled. Callers MUST NOT wrap this in
    try/except to suppress the return — the canonical dict is always usable.

    Does NOT perform filesystem IO, timestamp generation, or runtime dispatch.
    All external inputs must be supplied by the caller.

    closeout_status decision order:
        candidate_payload is None          → "missing"
        schema validation fails            → "schema_invalid"
        semantic validation: insufficient  → "content_insufficient"
        semantic validation: inconsistent  → "inconsistent"
        all checks pass                    → "valid"
    """
    if candidate_payload is None:
        return _make_canonical(session_id, closed_at, "missing", None)

    schema_ok, schema_reason = _validate_candidate_schema(candidate_payload)
    if not schema_ok:
        return _make_canonical(session_id, closed_at, "schema_invalid", candidate_payload)

    semantic_status = _run_semantic_validation(
        candidate=candidate_payload,
        existing_artifacts=existing_artifacts,
        runtime_signals=runtime_signals or {},
    )
    return _make_canonical(session_id, closed_at, semantic_status, candidate_payload)


def write_canonical_closeout(canonical: dict[str, Any], project_root: Path) -> Path:
    """
    Write canonical closeout artifact to artifacts/runtime/closeouts/{session_id}.json.
    Creates directory if needed. Returns the written path.
    """
    closeouts_dir = project_root / "artifacts" / "runtime" / "closeouts"
    closeouts_dir.mkdir(parents=True, exist_ok=True)
    path = closeouts_dir / f"{canonical['session_id']}.json"
    path.write_text(json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _generate_session_id() -> str:
    """Generate a new session ID: session-{YYYYmmddTHHMMSS}-{hex6}."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"session-{ts}-{uuid.uuid4().hex[:6]}"


def write_current_session_id(session_id: str, project_root: Path) -> Path:
    """
    Persist session_id for the in-progress session.
    Written by /wrap-up before session end. Overwrites any prior file.
    Returns the path written.
    """
    path = project_root / _CURRENT_SESSION_ID_FILE
    return _write_current_session_id_payload(session_id, path)


def _write_current_session_id_payload(session_id: str, path: Path) -> Path:
    """Write one current-session marker to an explicit lifecycle path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_current_session_id(
    project_root: Path,
    *,
    max_age_seconds: int = _CURRENT_SESSION_ID_STALENESS_SECONDS,
) -> str | None:
    """
    Read the stable session_id written by /wrap-up.

    Returns None if:
    - file does not exist (legacy path — wrap-up was not run)
    - file is malformed JSON or missing required fields
    - written_at is missing or unparseable (cannot assess staleness → reject)
    - file age exceeds max_age_seconds (stale from a prior session)

    Callers must call _generate_session_id() when this returns None.
    """
    paths = (
        project_root / _RUNTIME_CURRENT_SESSION_ID_FILE,
        project_root / _CURRENT_SESSION_ID_FILE,
    )
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session_id = str(data.get("session_id") or "").strip()
            if not session_id:
                continue
            written_at_str = str(data.get("written_at") or "").strip()
            if not written_at_str:
                continue
            written_at = datetime.fromisoformat(written_at_str)
            age_seconds = (datetime.now(timezone.utc) - written_at).total_seconds()
            if age_seconds > max_age_seconds:
                continue
            return session_id
        except Exception:
            continue
    return None


def candidate_timestamp() -> str:
    """
    Generate a lexicographically sortable timestamp string for candidate filenames.
    Format: YYYYmmddTHHMMSSffffffZ
    """
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def write_candidate(
    session_id: str,
    project_root: Path,
    candidate: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> Path:
    """
    Write a candidate closeout for session_id.
    Append-only: each call writes a new timestamped file.
    Called by /wrap-up, not by session_end.
    """
    ts = timestamp or candidate_timestamp()
    candidate_dir = (
        project_root / "artifacts" / "runtime" / "closeout_candidates" / session_id
    )
    candidate_dir.mkdir(parents=True, exist_ok=True)
    path = candidate_dir / f"{ts}.json"
    payload = dict(candidate)
    payload.setdefault("session_id", session_id)
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_closeout_completion_marker(
    session_id: str,
    project_root: Path,
    required_artifacts: list[Path],
) -> Path:
    """Atomically mark a session consumed after all required artifacts exist."""
    missing = [str(path) for path in required_artifacts if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "closeout completion marker requires emitted artifacts: "
            + ", ".join(missing)
        )

    completion_dir = project_root / "artifacts" / "runtime" / "closeout-completions"
    completion_dir.mkdir(parents=True, exist_ok=True)
    path = completion_dir / f"{session_id}.json"
    payload = {
        "session_id": session_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "required_artifacts": [
            str(artifact.relative_to(project_root))
            for artifact in required_artifacts
        ],
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _read_valid_closeout_completion(
    session_id: str,
    project_root: Path,
    path: Path,
) -> dict[str, Any] | None:
    """Return a completion marker only when its identity and artifacts validate."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if str(payload.get("session_id") or "") != session_id:
        return None
    required_artifacts = payload.get("required_artifacts")
    if not isinstance(required_artifacts, list) or not required_artifacts:
        return None
    for raw_path in required_artifacts:
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
        artifact = (project_root / raw_path).resolve()
        try:
            artifact.relative_to(project_root.resolve())
        except ValueError:
            return None
        if not artifact.is_file():
            return None
    return payload


# ---------------------------------------------------------------------------
# Internal: schema validation
# ---------------------------------------------------------------------------

def _validate_candidate_schema(candidate: dict[str, Any]) -> tuple[bool, str]:
    """
    Check that candidate has all required fields with correct types.
    Returns (ok, reason).
    """
    if not isinstance(candidate, dict):
        return False, "candidate is not a dict"

    for field, expected_type in _CANDIDATE_REQUIRED_FIELDS.items():
        if field not in candidate:
            return False, f"missing required field: {field}"
        if not isinstance(candidate[field], expected_type):
            return False, f"field {field!r} has wrong type: expected {expected_type.__name__}"

    # All list elements must be strings
    for list_field in ("tools_used", "artifacts_referenced", "open_risks"):
        for item in candidate.get(list_field, []):
            if not isinstance(item, str):
                return False, f"field {list_field!r} contains non-string element"

    return True, "ok"


# ---------------------------------------------------------------------------
# Internal: semantic validation
# ---------------------------------------------------------------------------

def _run_semantic_validation(
    *,
    candidate: dict[str, Any],
    existing_artifacts: frozenset[str],
    runtime_signals: dict[str, Any],
) -> str:
    """
    Minimal semantic validation. Returns the closeout_status string.

    Does NOT try to prove the candidate is truthful — only detects obvious gaps:
    - content_insufficient: work_summary empty, or no evidence at all
    - inconsistent: artifacts_referenced don't exist, or verifiable tools claimed
                    without corresponding runtime signal
    - valid: passes all checks
    """
    work_summary = (candidate.get("work_summary") or "").strip()
    tools_used = candidate.get("tools_used") or []
    artifacts_referenced = candidate.get("artifacts_referenced") or []

    # content_insufficient: work_summary empty
    if not work_summary:
        return "content_insufficient"

    # content_insufficient: no evidence whatsoever
    if not tools_used and not artifacts_referenced:
        return "content_insufficient"

    # inconsistent: artifacts_referenced files don't exist on disk
    for artifact in artifacts_referenced:
        if artifact and artifact not in existing_artifacts:
            return "inconsistent"

    # inconsistent: verifiable tool claimed but no runtime signal present
    claimed_verifiable = {t.lower() for t in tools_used} & _VERIFIABLE_TOOLS
    if claimed_verifiable:
        tool_signals = set(runtime_signals.get("tools_executed") or [])
        if not tool_signals:
            return "inconsistent"

    return "valid"


# ---------------------------------------------------------------------------
# Internal: canonical builder
# ---------------------------------------------------------------------------

def _make_canonical(
    session_id: str,
    closed_at: str,
    status: str,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Assemble the canonical closeout dict from validated inputs.
    When candidate is None or invalid, fields default to null/empty.
    """
    if candidate and status not in ("missing", "schema_invalid"):
        task_intent = candidate.get("task_intent") or None
        work_summary = candidate.get("work_summary") or None
        tools_used = list(candidate.get("tools_used") or [])
        artifacts_referenced = list(candidate.get("artifacts_referenced") or [])
        open_risks = list(candidate.get("open_risks") or [])
    else:
        task_intent = None
        work_summary = None
        tools_used = []
        artifacts_referenced = []
        open_risks = []

    return {
        "session_id": session_id,
        "closed_at": closed_at,
        "closeout_status": status,
        "task_intent": task_intent,
        "work_summary": work_summary,
        "evidence_summary": {
            "tools_used": tools_used,
            "artifacts_referenced": artifacts_referenced,
        },
        "open_risks": open_risks,
    }
