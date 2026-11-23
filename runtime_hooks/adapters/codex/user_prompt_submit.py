"""Record text-derived provisional levels; stage A emits no context or decisions.

Identifiers are stored only as full SHA-256 hex digests for transcript
correlation, never as raw metadata. Missing, non-string or non-UTF-8 identifiers
have null digests and fixed invalid-identifier error codes. Record filenames use
the first 32 session-digest hex characters; invalid session IDs use
invalid-session.jsonl. Stdin bytes are explicitly decoded as UTF-8, independent
of the configured stdin text encoding; decoding failures use invalid_encoding.

upgrade_additional_loads lists resource names requested by the L0 upgrade path;
it contains NO detector reasons. Only the classifier's fixed load constants,
governance/ARCHITECTURE.md and domain_summary, survive. Detector vetoes and L2
keywords can therefore have no loads.

handler_elapsed_ms is sampled after serialization, directory setup and opening
the record, immediately before substituting the elapsed placeholder and writing.
It excludes Python startup and the final write/flush/close. Native acceptance
must measure total invocation latency. Interpreter launch failure, external
timeout and cancellation are outside what the handler can guarantee. Once the
CLI entry runs, bootstrap/handler Exception and SystemExit failures exit zero
with empty stdout; persistence is best-effort, not guaranteed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

FRAMEWORK_ROOT: Path | None = None
_ALLOWED_UPGRADE_LOADS = frozenset({"governance/ARCHITECTURE.md", "domain_summary"})
_COMMIT = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
_LEVELS = ("L0", "L1", "L2")
_DIAGNOSTICS = {
    "invalid_arguments": "UserPromptSubmit: invalid arguments",
    "bootstrap_error": "UserPromptSubmit: bootstrap failed",
    "write_error": "UserPromptSubmit: record write failed",
}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("invalid_arguments")


def _add_error(record: dict, code: str) -> None:
    """Callers supply only fixed literals, never collaborator or exception text."""
    if code not in record["error_codes"]:
        record["error_codes"].append(code)


def _identifier(value, record: dict, invalid_code: str) -> str | None:
    if not isinstance(value, str):
        _add_error(record, invalid_code)
        return None
    try:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    except UnicodeError:
        _add_error(record, invalid_code)
        return None


def _framework_commit() -> str | None:
    """Read this framework's HEAD, including worktree/common and packed refs."""
    try:
        framework_root = FRAMEWORK_ROOT or Path(__file__).resolve().parents[3]
        git_dir = framework_root / ".git"
        if git_dir.is_file():
            marker = git_dir.read_text(encoding="utf-8").strip()
            if not marker.startswith("gitdir: "):
                return None
            git_dir = (framework_root / marker[8:]).resolve()
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if _COMMIT.fullmatch(head):
            return head.lower()
        if not head.startswith("ref: "):
            return None
        ref = head[5:]
        if not re.fullmatch(r"refs/[A-Za-z0-9._/-]+", ref) or ".." in ref.split("/"):
            return None
        locations = [git_dir]
        common = git_dir / "commondir"
        if common.is_file():
            locations.append((git_dir / common.read_text(encoding="utf-8").strip()).resolve())
        for location in locations:
            loose = location / ref
            if loose.is_file():
                sha = loose.read_text(encoding="utf-8").strip()
                if _COMMIT.fullmatch(sha):
                    return sha.lower()
            packed = location / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    fields = line.split()
                    if len(fields) == 2 and fields[1] == ref and _COMMIT.fullmatch(fields[0]):
                        return fields[0].lower()
    except Exception:
        pass
    return None


def _write_record(project_root: Path, filename: str, record: dict, started: float) -> None:
    directory = project_root.resolve() / "artifacts/runtime/level-floor"
    resolved_directory = directory.resolve()
    # Refuse directory redirects as well as a record symlink escaping the tree.
    if resolved_directory != directory:
        raise ValueError("record_directory_escape")
    path = (directory / filename).resolve()
    if not path.is_relative_to(resolved_directory):
        raise ValueError("record_path_escape")
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        # Serialize and prepare the line before sampling. Only the trusted
        # numeric placeholder substitution remains between the sample and write.
        line = json.dumps(record, ensure_ascii=True) + "\n"
        before, after = line.split('"handler_elapsed_ms": 0.0', 1)
        elapsed = float((perf_counter() - started) * 1000)
        record["handler_elapsed_ms"] = elapsed
        stream.write(f'{before}"handler_elapsed_ms": {elapsed}{after}')


def _diagnostic(code: str) -> None:
    try:
        print(_DIAGNOSTICS[code], file=sys.stderr)
    except (Exception, SystemExit):
        pass


def _empty_record() -> dict:
    return {
        "schema_version": "1.0",
        "recorded_at": None,
        "session_id_sha256": None,
        "turn_id_sha256": None,
        "prompt_sha256": None,
        "prompt_len": None,
        "detector_level": "UNKNOWN",
        "provisional_level": "UNKNOWN",
        "provisional_level_basis": "text_heuristic_report_only",
        "upgrade_additional_loads": [],
        "framework_commit": None,
        "handler_elapsed_ms": 0.0,
        "error_codes": [],
    }


def _read_payload(record: dict) -> tuple[str | None, bool]:
    payload = None
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except UnicodeDecodeError:
        _add_error(record, "invalid_encoding")
    except (Exception, SystemExit):
        _add_error(record, "invalid_json")

    data = payload if isinstance(payload, dict) else {}
    prompt = data.get("prompt")
    prompt = prompt if isinstance(prompt, str) else None
    valid_event = isinstance(payload, dict) and data.get("hook_event_name") == "UserPromptSubmit"
    if not valid_event:
        _add_error(record, "wrong_event")
    record["session_id_sha256"] = _identifier(
        data.get("session_id"), record, "invalid_session_id",
    )
    record["turn_id_sha256"] = _identifier(
        data.get("turn_id"), record, "invalid_turn_id",
    )
    if "prompt" not in data:
        _add_error(record, "missing_prompt")
    elif prompt is None:
        _add_error(record, "non_string_prompt")
    else:
        record["prompt_len"] = len(prompt)
        try:
            record["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        except UnicodeError:
            _add_error(record, "invalid_prompt_encoding")
            prompt = None
    return prompt, valid_event


def _level(value, record: dict) -> str:
    if type(value) is str and value in _LEVELS:
        return value
    _add_error(record, "invalid_level_return")
    return "UNKNOWN"


def _classify(record: dict, prompt: str, detect, upgrade) -> None:
    try:
        level = detect(prompt)
    except (Exception, SystemExit):
        _add_error(record, "classifier_error")
        return
    record["detector_level"] = _level(level, record)
    if record["detector_level"] == "UNKNOWN":
        return
    try:
        provisional, loads = upgrade(level, prompt, risk_level="medium")
    except (Exception, SystemExit):
        _add_error(record, "upgrade_error")
        return
    record["provisional_level"] = _level(provisional, record)
    if not isinstance(loads, list):
        _add_error(record, "invalid_upgrade_load")
        return
    for resource in loads:
        if type(resource) is str and resource in _ALLOWED_UPGRADE_LOADS:
            record["upgrade_additional_loads"].append(resource)
        else:
            _add_error(record, "invalid_upgrade_load")


def main() -> int:
    project_root = None
    started = 0.0
    filename = "invalid-session.jsonl"
    record = None
    try:
        started = perf_counter()
        try:
            parser = _ArgumentParser(description=__doc__, add_help=False)
            parser.add_argument("--project-root", type=Path, required=True)
            args = parser.parse_args()
        except (Exception, SystemExit):
            _diagnostic("invalid_arguments")
            return 0
        project_root = args.project_root
        record = _empty_record()
        # Import/setup output is just as untrusted as classifier diagnostics.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            record["recorded_at"] = datetime.now(timezone.utc).isoformat()
            record["framework_commit"] = _framework_commit()
            prompt, valid_event = _read_payload(record)
            session_digest = record["session_id_sha256"]
            if session_digest is not None:
                filename = session_digest[:32] + ".jsonl"
            if __package__ in (None, ""):
                sys.dont_write_bytecode = True
                sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
            from governance_tools.task_level_detector import (
                apply_upgrade_triggers, detect_task_level,
            )
            if prompt is not None and valid_event:
                _classify(record, prompt, detect_task_level, apply_upgrade_triggers)
    except (Exception, SystemExit):
        _diagnostic("bootstrap_error")
        try:
            if record is None:
                record = _empty_record()
            _add_error(record, "bootstrap_error")
        except (Exception, SystemExit):
            # If record construction itself fails, persistence is unavailable;
            # the zero-exit boundary still applies to the launched CLI entry.
            return 0

    try:
        if project_root is not None:
            _write_record(project_root, filename, record, started)
    except (Exception, SystemExit):
        _add_error(record, "write_error")
        _diagnostic("write_error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
