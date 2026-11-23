"""Record text-derived provisional levels; stage A emits no context or decisions."""
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

if __package__ in (None, ""):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from governance_tools.task_level_detector import apply_upgrade_triggers, detect_task_level


FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
_SESSION_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
_COMMIT = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("invalid_arguments")


def _redact(message: str, prompt: str | None) -> str:
    if prompt and (prompt in message or any(
        message[index:index + 8] in prompt for index in range(len(message) - 7)
    )):
        return "<redacted>"
    return message


def _exception_error(exc: BaseException, prompt: str | None) -> str:
    try:
        message = " ".join(_redact(str(exc), prompt).split())[:160]
    except Exception:
        message = "<redacted>"
    return f"{type(exc).__name__}: {message}"


def _framework_commit() -> str | None:
    """Read this framework's HEAD, including worktree/common and packed refs."""
    try:
        git_dir = FRAMEWORK_ROOT / ".git"
        if git_dir.is_file():
            marker = git_dir.read_text(encoding="utf-8").strip()
            if not marker.startswith("gitdir: "):
                return None
            git_dir = (FRAMEWORK_ROOT / marker[8:]).resolve()
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
        record["elapsed_ms"] = float((perf_counter() - started) * 1000)
        stream.write(json.dumps(record, ensure_ascii=True) + "\n")


def _diagnostic(message: str) -> None:
    try:
        print(f"UserPromptSubmit: {message}", file=sys.stderr)
    except Exception:
        pass


def main() -> int:
    started = perf_counter()
    try:
        parser = _ArgumentParser(description=__doc__, add_help=False)
        parser.add_argument("--project-root", type=Path, required=True)
        args = parser.parse_args()
    except Exception:
        _diagnostic("invalid arguments")
        return 0

    record = {
        "schema_version": "1.0",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "session_id": None,
        "turn_id": None,
        "prompt_sha256": None,
        "prompt_len": None,
        "detector_level": "UNKNOWN",
        "provisional_level": "UNKNOWN",
        "provisional_level_basis": "text_heuristic_report_only",
        "signals": [],
        "framework_commit": _framework_commit(),
        "elapsed_ms": 0.0,
        "error": None,
    }
    errors = []
    payload = None
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        # Parser diagnostics may quote input; never retain their message or doc.
        errors.append(f"{type(exc).__name__}: invalid_json")

    data = payload if isinstance(payload, dict) else {}
    prompt = data.get("prompt")
    prompt = prompt if isinstance(prompt, str) else None
    valid_event = isinstance(payload, dict) and data.get("hook_event_name") == "UserPromptSubmit"
    if not valid_event:
        errors.append("invalid_hook_payload")
    session_id = data.get("session_id")
    valid_session = (isinstance(session_id, str) and _SESSION_ID.fullmatch(session_id)
                     and ".." not in session_id)
    filename = f"{session_id}.jsonl" if valid_session else "invalid-session.jsonl"
    if valid_session:
        record["session_id"] = _redact(session_id, prompt)
    else:
        errors.append("invalid_session_id")
    turn_id = data.get("turn_id")
    if isinstance(turn_id, str):
        record["turn_id"] = _redact(turn_id, prompt)
    elif isinstance(turn_id, int):
        record["turn_id"] = turn_id

    try:
        if prompt is not None:
            record["prompt_len"] = len(prompt)
            record["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if valid_event:
                # Even unexpected classifier diagnostics must not become context.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    level = detect_task_level(prompt)
                    record["detector_level"] = level
                    provisional, signals = apply_upgrade_triggers(level, prompt, risk_level="medium")
                record["signals"] = [_redact(signal, prompt) for signal in signals]
                record["provisional_level"] = provisional
    except (Exception, SystemExit) as exc:
        record["provisional_level"] = "UNKNOWN"
        errors.append(_exception_error(exc, prompt))
    record["error"] = "; ".join(errors) or None

    try:
        _write_record(args.project_root, filename, record, started)
    except Exception:
        # Paths and OS error messages can contain untrusted input.
        _diagnostic("record write failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
