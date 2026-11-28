"""Opt-in, read-only SessionStart working-state delivery (no gate authority).

Precedence is R2 checkpoint, canonical closeout, then an explicitly supplied
R0/R1 lineage and authority observation. An invalid present source stops delivery;
it never licenses an older source. ``session_id`` optionally selects the *source*
session, not the new SessionStart identity. No identity is created here.

The active-task argument contains the record/summary/authority arguments of
``select_current_active_task``; raw Markdown is never an authority source. Trust
is the existing cooperative local evidence model, not cryptographic attestation.
Only payloads are deterministic; elapsed time is measured per invocation.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from time import perf_counter
from typing import Any

from governance_tools.memory_freshness_guard import _age_days
from governance_tools.memory_janitor import MemoryJanitor
from governance_tools.memory_provenance import git_commit_exists
from memory_pipeline import active_task_round_trip as r0
from memory_pipeline import active_task_supersession as r1
from runtime_hooks.adapters.claude_code import session_lifecycle as claude
from runtime_hooks.core import _canonical_closeout_context as closeout_context
from runtime_hooks.core._bound_session_start import git_toplevel
from runtime_hooks.core._canonical_closeout import (
    _parse_aware_utc,
    is_valid_session_id,
    read_session_envelope,
)

# Bound metadata work before invoking readers that enumerate these directories.
# Exceeding these reader limits falls back; it never samples an older record.
MAX_SOURCE_FILES = 16
MAX_SOURCE_BYTES = claude.MAX_TRUST_JSON_BYTES
_REJECTED_STATES = r0.NON_RESOLVED_STATES | r1.NON_RESOLVED_STATES | {
    "checkpoint_mismatch", "inconsistent", "authority_conflict",
}
_DIRECTIVE = re.compile(
    r"^(?:RULE|MUST|SHALL|SHOULD|POLICY|INSTRUCTIONS?|SYSTEM|DEVELOPER|"
    r"DO\s+NOT|YOU\s+(?:MUST|SHOULD|SHALL)|NEVER|ALWAYS|IGNORE|OVERRIDE|FOLLOW|PLEASE|RUN|EXECUTE|"
    r"DELETE|WRITE|COMMIT|PUSH|INSTALL|READ|LOAD|UPDATE|IMPLEMENT|CONTINUE|"
    r"NEXT\s+(?:STEP|ACTION)|TODO)\b|^(?:請|必須|不得|禁止|務必|執行|繼續|下一步)",
    re.IGNORECASE,
)
_PATH_TOKEN = re.compile(r"(?:[A-Za-z]:)?[\w./\\-]+\.[A-Za-z0-9_]+", re.UNICODE)


class _Reject(ValueError):
    pass


def _check_path(root: Path, path: Path) -> None:
    if not path.is_relative_to(root) or path.resolve() != path:
        raise _Reject("workspace_mismatch")


def _json_paths(root: Path, directory: Path) -> list[Path]:
    _check_path(root, directory)
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise _Reject("invalid_source")
    paths = list(islice(directory.glob("*.json"), MAX_SOURCE_FILES + 1))
    if len(paths) > MAX_SOURCE_FILES:
        raise _Reject("source_budget_exceeded")
    for path in paths:
        _check_path(root, path)
        if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
            raise _Reject("invalid_source")
    return sorted(paths)


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise _Reject("malformed_json") from exc
    if not isinstance(data, dict):
        raise _Reject("invalid_source")
    return data, raw


def _check_states(data: Mapping) -> None:
    for key in ("resolution_state", "state", "closeout_status", "hold_reason"):
        value = data.get(key)
        if isinstance(value, str) and value.lower() in _REJECTED_STATES:
            raise _Reject(value.lower())
    if "resolution_state" in data and data["resolution_state"] != "resolved":
        raise _Reject("unresolved_state")


def _fresh(path: Path, now: datetime, max_age_days: int, timestamp: object = None) -> None:
    age = _age_days(path, now)
    if age < 0 or age > max_age_days:
        raise _Reject("future_timestamp" if age < 0 else "stale_source")
    if timestamp is not None:
        parsed = _parse_aware_utc(timestamp) if isinstance(timestamp, str) else None
        if parsed is None:
            raise _Reject("invalid_timestamp")
        age = (now - parsed).total_seconds() / 86400
        if age < 0 or age > max_age_days:
            raise _Reject("future_timestamp" if age < 0 else "stale_source")


def _bound_envelope(root: Path, sid: object) -> dict:
    if not is_valid_session_id(sid):
        raise _Reject("session_mismatch")
    path = root / "artifacts/runtime/sessions" / sid / "session-envelope.json"
    _check_path(root, path)
    envelope = read_session_envelope(sid, root)
    if envelope is None or envelope.get("schema_version") != "1.1":
        raise _Reject("unverified_session_binding")
    return envelope


def _checkpoint_source(root: Path, sid: str | None, now: datetime, age: int) -> dict | None:
    paths = _json_paths(root, root / claude.CHECKPOINTS_DIR)
    if sid is not None:
        paths = [path for path in paths if path.stem == sid]
    if not paths:
        return None
    records = [(path, *_read_json(path)) for path in paths]
    for path, data, _raw in records:
        if (data.get("session_id") != path.stem or data.get("consumer_root") != str(root)
                or data.get("provider") != claude.PROVIDER):
            raise _Reject("workspace_mismatch")
        if _parse_aware_utc(str(data.get("exited_at", ""))) is None:
            raise _Reject("invalid_timestamp")
    records.sort(key=lambda item: _parse_aware_utc(item[1]["exited_at"]), reverse=True)
    if (len(records) > 1 and _parse_aware_utc(records[0][1]["exited_at"])
            == _parse_aware_utc(records[1][1]["exited_at"])):
        raise _Reject("inconsistent")
    path, checkpoint, _raw = records[0]
    _check_states(checkpoint)
    target = path.stem
    envelope = _bound_envelope(root, target)
    if envelope.get("provider") != claude.PROVIDER:
        raise _Reject("unverified_session_binding")
    _fresh(path, now, age, checkpoint["exited_at"])
    _json_paths(root, root / claude.CANDIDATES_DIR / target)
    releases = _json_paths(root, root / claude.RELEASES_DIR)
    owner = root / claude.OWNER_RECORD
    _check_path(root, owner)
    # R2 may use the current owner or a previous immutable release generation.
    for record_path in ([owner] if owner.exists() else []) + releases:
        record, _ = _read_json(record_path)
        if record.get("session_id") == target:
            _check_states(record)
            if record.get("consumer_root") != str(root):
                raise _Reject("workspace_mismatch")
    readback = claude.build_readback(root, target, "resume")
    if readback["state"] != "checkpointed":
        raise _Reject(readback["state"])
    verified = claude._verified_checkpoint_binding(root, target, checkpoint)
    if verified is None:
        raise _Reject("checkpoint_mismatch")
    identity, raw = verified
    candidate_path = root / identity["relative_path"]
    _fresh(candidate_path, now, age)
    try:
        candidate = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise _Reject("malformed_json") from exc
    if not isinstance(candidate, dict):
        raise _Reject("invalid_source")
    _check_states(candidate)
    if candidate.get("session_id", target) != target:
        raise _Reject("session_mismatch")
    if _parse_aware_utc(checkpoint["exited_at"]) < _parse_aware_utc(envelope["started_at"]):
        raise _Reject("session_mismatch")
    return {"source": "r2_checkpoint", "source_sha256": identity["sha256"],
            "state": "checkpointed", "summary": candidate.get("work_summary"),
            "paths": [path.relative_to(root).as_posix(), identity["relative_path"],
                      *_references(candidate)], "pressure": "NOT_ASSESSED"}


def _canonical_source(root: Path, sid: str | None, now: datetime, age: int) -> dict | None:
    paths = _json_paths(root, root / "artifacts/runtime/closeouts")
    if not paths:
        return None
    records = [(path, *_read_json(path)) for path in paths]
    for _path, data, _raw in records:
        if _parse_aware_utc(str(data.get("closed_at", ""))) is None:
            raise _Reject("invalid_timestamp")
    records.sort(key=lambda item: _parse_aware_utc(item[1]["closed_at"]), reverse=True)
    if (len(records) > 1 and _parse_aware_utc(records[0][1]["closed_at"])
            == _parse_aware_utc(records[1][1]["closed_at"])):
        raise _Reject("inconsistent")
    path, data, raw = records[0]
    _check_states(data)
    # Keep the existing canonical-only loader as the source selection authority.
    # Refuse ambiguous ordering or a changed snapshot rather than substituting it.
    canonical = closeout_context._load_latest_canonical(root)
    if canonical != data:
        raise _Reject("inconsistent")
    context = closeout_context._build_context(canonical)
    if not context["inject"] or context["injection_level"] != "full":
        raise _Reject("unverified_closeout")
    target = data.get("session_id")
    if target != path.stem or (sid is not None and target != sid):
        raise _Reject("session_mismatch")
    envelope = _bound_envelope(root, target)
    _fresh(path, now, age, data["closed_at"])
    if _parse_aware_utc(data["closed_at"]) < _parse_aware_utc(envelope["started_at"]):
        raise _Reject("session_mismatch")
    evidence = data.get("evidence_summary")
    if not isinstance(evidence, dict):
        raise _Reject("invalid_source")
    return {"source": "canonical_closeout", "source_sha256": hashlib.sha256(raw).hexdigest(),
            "state": "valid", "summary": context["work_summary"], "pressure": "NOT_ASSESSED",
            "paths": [path.relative_to(root).as_posix(), *_references(evidence)]}


def _references(data: dict) -> list[str]:
    paths = data.get("artifacts_referenced", [])
    if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
        raise _Reject("invalid_source")
    return paths


def _active_source(root: Path, inputs: Mapping | None, sid: str | None,
                   now: datetime, age: int, reads: list[int]) -> dict:
    path = root / "memory/01_active_task.md"
    _check_path(root, path)
    if inputs is None:
        raise _Reject("unverified_active_task" if path.exists() else "missing_source")
    allowed = {"predecessor_record", "predecessor_summary", "successor_record",
               "successor_summary", "authority_observation"}
    if not isinstance(inputs, Mapping) or set(inputs) - allowed:
        raise _Reject("invalid_active_task_input")
    observation = inputs.get("authority_observation")
    if not isinstance(observation, Mapping):
        raise _Reject("unverified_active_task")
    _check_states(observation)
    _fresh(path, now, age)
    if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise _Reject("invalid_source")
    # Janitor uses builtin open, whereas R1 and metadata readers use Path.open.
    # Count read attempts, including delegated reads, not just distinct names.
    reads[0] += 1
    _lines, _chars, pressure = MemoryJanitor(root / "memory").check_hot_memory_status()
    if pressure in {"CRITICAL", "EMERGENCY"}:
        raise _Reject("memory_pressure_" + pressure.lower())
    try:
        state, projection = r1.select_current_active_task(
            project_root=root, memory_root=root / "memory", logical_name="active_task", **inputs,
        )
    except (ValueError, TypeError) as exc:
        raise _Reject("unverified_active_task") from exc
    if state not in {r1.CURRENT_STATE_BASE, r1.CURRENT_STATE_SUPERSEDED} or not projection:
        raise _Reject(state if state in _REJECTED_STATES else "unresolved_state")
    current = "successor" if state == r1.CURRENT_STATE_SUPERSEDED else "predecessor"
    record = inputs[current + "_record"]
    if sid is not None and record.get("session_id") != sid:
        raise _Reject("session_mismatch")
    if (record.get("memory_binding") != "bound"
            or not git_commit_exists(root, record.get("commit_hash", ""))):
        raise _Reject("unverified_provenance")
    return {"source": "r0_r1_active_task", "source_sha256": hashlib.sha256(projection).hexdigest(),
            "state": state, "summary": inputs[current + "_summary"], "pressure": pressure,
            "paths": ["memory/01_active_task.md"]}


def _existing_path(root: Path, value: str) -> str | None:
    path = root / value.replace("\\", "/")
    try:
        _check_path(root, path)
        if path.exists():
            return path.relative_to(root).as_posix()
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def _project(root: Path, source: dict, max_chars: int) -> str:
    summary = source["summary"]
    if not isinstance(summary, str):
        raise _Reject("no_factual_state")
    clauses = re.split(r"[\n\r;\x85\u2028\u2029]+|(?<=[.!?])\s+", summary)
    facts = [clause.strip().lstrip("-*#> `\t") for clause in clauses]
    summary = "; ".join(fact for fact in facts if fact and not _DIRECTIVE.match(fact))
    # Neither the fact text nor verified_paths advertises phantom/outside paths.
    summary = _PATH_TOKEN.sub(
        lambda match: _existing_path(root, match[0]) or "", summary,
    )
    summary = " ".join(summary.split()).strip()
    if not summary:
        raise _Reject("no_factual_state")
    paths = sorted({value for item in source["paths"] for value in [_existing_path(root, item)] if value})

    def render(text: str) -> str:
        return "\n".join([
            "[WORKING_STATE_DATA]", "format: verified_working_state_data",
            "source: " + source["source"], "source_sha256: " + source["source_sha256"],
            "state: " + source["state"], "active_summary: " + json.dumps(text, ensure_ascii=False),
            "pressure: " + source["pressure"],
            "verified_paths: " + json.dumps(paths, ensure_ascii=False),
        ])

    if len(render(summary)) <= max_chars:
        return render(summary)
    while paths and len(render(summary[:1] + "…")) > max_chars:
        paths.pop()
    if len(render(summary[:1] + "…")) > max_chars:
        raise _Reject("payload_budget_exceeded")
    if len(render(summary)) <= max_chars:
        return render(summary)
    low, high = 1, len(summary)
    while low < high:
        middle = (low + high + 1) // 2
        if len(render(summary[:middle] + "…")) <= max_chars:
            low = middle
        else:
            high = middle - 1
    return render(summary[:low] + "…")


def build_memory_delivery(
    project_root: Path, *, workspace_root: Path | None = None, session_id: str | None = None,
    active_task: Mapping | None = None, max_chars: int = 600, max_age_days: int = 30,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve one bounded verified source; any failure uses original_read_flow.

    ``files_read_count`` counts source-file read attempts, including delegated
    reads (Git's internal object/config access and directory/stat probes excluded).
    Callers may supply an aware ``now`` for deterministic freshness tests. This
    function neither invokes SessionStart gates nor changes their outcomes.
    """
    started = perf_counter()
    reads = [0]
    payload, reason = "", "verification_failed"
    try:
        if (type(max_chars) is not int or max_chars < 1
                or type(max_age_days) is not int or max_age_days < 0):
            raise _Reject("invalid_configuration")
        root = Path(project_root)
        workspace = root if workspace_root is None else Path(workspace_root)
        if (not root.is_absolute() or root.resolve(strict=True) != root
                or not workspace.is_absolute() or workspace.resolve(strict=True) != workspace
                or workspace != root or git_toplevel(str(root)) != root):
            raise _Reject("workspace_mismatch")
        if session_id is not None and not is_valid_session_id(session_id):
            raise _Reject("session_mismatch")
        current_time = now if now is not None else datetime.now(timezone.utc)
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise _Reject("invalid_configuration")

        class ReadPath(type(root)):
            # Local to the call: no global monkeypatch or shared mutable counter.
            def open(self, mode="r", *args, **kwargs):
                _check_path(root, self)
                if mode not in {"r", "rb", "rt"}:
                    raise _Reject("read_only_violation")
                if not self.is_file() or self.stat().st_size > MAX_SOURCE_BYTES:
                    raise _Reject("invalid_source")
                reads[0] += 1
                return super().open(mode, *args, **kwargs)

        bound_root = ReadPath(root)
        source = (_checkpoint_source(bound_root, session_id, current_time, max_age_days)
                  or _canonical_source(bound_root, session_id, current_time, max_age_days)
                  or _active_source(bound_root, active_task, session_id, current_time, max_age_days, reads))
        payload = _project(bound_root, source, max_chars)
        reason = "verified"
    except _Reject as exc:
        reason = str(exc)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, RecursionError, subprocess.SubprocessError):
        reason = "verification_failed"
    inject = bool(payload)
    return {"inject": inject, "payload": payload, "reason": reason,
            "fallback": None if inject else "original_read_flow",
            "telemetry": {"elapsed_ms": round((perf_counter() - started) * 1000, 3),
                          "files_read_count": reads[0], "payload_chars": len(payload),
                          "fallback_to_original_read": not inject}}


def format_platform_envelope(delivery_result: Mapping, platform: str) -> dict:
    """Pure transport formatting; fallback carries no injected context."""
    if platform not in {"claude_code", "codex", "copilot", "vscode_copilot", "copilot_cli", "antigravity"}:
        raise ValueError("Unsupported memory delivery platform")
    inject = delivery_result.get("inject") is True
    payload = delivery_result.get("payload", "")
    if platform in {"copilot", "vscode_copilot", "copilot_cli"}:
        return {"continue": True, **({"additionalContext": payload} if inject else {})}
    if not inject:
        return {}
    if platform == "antigravity":
        return {"injectSteps": [{"systemMessage": {"systemMessage": payload}}]}
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": payload}}
