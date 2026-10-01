"""Codex hook bridge for one declared required-dependency memory obligation.

This opt-in pilot recognizes a structured event emitted by a prerequisite
checker. Arbitrary nonzero tool results do not create obligations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_DIR = Path("memory/.pending_memory_obligations")
OBSERVATION_DIR = Path("memory/.memory_obligation_observations")
_SESSION_ID = re.compile(r"^[A-Za-z0-9-]{1,100}$")
_HEADING = re.compile(r"^(#{1,6})\s+")
_EVENT_PREFIX = "GOVERNANCE_EVENT_V1 "


def _within_repo(repo: Path, relative: Path) -> Path:
    path = (repo / relative).resolve()
    if not path.is_relative_to(repo):
        raise ValueError(f"path escapes repository: {relative}")
    return path


def _contract(repo: Path, path: Path, trusted_path: Path, trusted_sha256: str) -> dict[str, Any]:
    source = _within_repo(repo, path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("obligation contract must be an object")
    for key in ("event_id", "dependency", "event_type", "event_status"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"missing contract field: {key}")
    headings = data.get("plan_risk_headings")
    if not isinstance(headings, list) or not headings or any(
        not isinstance(heading, str) or not heading.strip() for heading in headings
    ):
        raise ValueError("plan_risk_headings must be nonempty strings")
    if not re.fullmatch(r"[A-Z0-9-]{1,80}", data["event_id"]):
        raise ValueError("event_id must be a safe uppercase identifier")
    producer = data.get("approved_producer")
    if not isinstance(producer, dict) or not isinstance(producer.get("path"), str):
        raise ValueError("approved_producer.path is required")
    if not isinstance(producer.get("sha256"), str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", producer["sha256"]
    ):
        raise ValueError("approved_producer.sha256 must be SHA-256")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", trusted_sha256):
        raise ValueError("trusted producer SHA-256 is invalid")
    if not isinstance(producer.get("blocked_exit_code"), int) or not 1 <= producer["blocked_exit_code"] <= 255:
        raise ValueError("approved_producer.blocked_exit_code must be nonzero")
    source = _within_repo(repo, Path(producer["path"]))
    if source != _within_repo(repo, trusted_path) or producer["sha256"].casefold() != trusted_sha256.casefold():
        raise ValueError("producer identity differs from trusted hook definition")
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest().casefold() != producer["sha256"].casefold():
        raise ValueError("approved producer bytes do not match contract")
    return data


def _state_folder(repo: Path, session_id: str) -> Path:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("missing or invalid Codex session_id")
    return _within_repo(repo, STATE_DIR / session_id)


def _observation_folder(repo: Path, session_id: str) -> Path:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("missing or invalid Codex session_id")
    return _within_repo(repo, OBSERVATION_DIR / session_id)


def _record_observation(repo: Path, session_id: str, turn_id: str,
                        tool_use_id: str, event_id: str, dependency: str) -> Path:
    folder = _observation_folder(repo, session_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.json"
    # Create the evidence before rechecking the producer or writing an
    # obligation. An interrupted registration leaves an unreadable or
    # 'checking' receipt, either of which blocks Stop.
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"session_id": session_id, "turn_id": turn_id,
                   "tool_use_id": tool_use_id, "event_id": event_id,
                   "dependency": dependency, "status": "checking"}, stream)
    return path


def _record_registration_failure(repo: Path, session_id: str, turn_id: str,
                                 tool_use_id: str, contract: dict[str, Any]) -> None:
    # Fall back to the existing obligation store when recognition fails or
    # the independent observation store cannot be written. This state cannot be
    # consumed by PLAN/active-task edits; the failure needs explicit repair.
    folder = _state_folder(repo, session_id)
    folder.mkdir(parents=True, exist_ok=True)
    identity = f"MEM-OBL-REGISTRATION-ERROR-{uuid.uuid4().hex.upper()}"
    with (folder / f"{identity}.json").open("x", encoding="utf-8") as stream:
        json.dump({"id": identity, "event_id": contract["event_id"],
                   "dependency": contract["dependency"],
                   "session_id": session_id, "turn_id": turn_id,
                   "tool_use_id": tool_use_id,
                   "status": "registration_error"}, stream)
        stream.write("\n")


def _finish_observation(path: Path, status: str, obligation_id: str | None = None) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    record["status"] = status
    if obligation_id is not None:
        record["obligation_id"] = obligation_id
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(
            str(value[key])
            for key in ("aggregated_output", "stdout", "output")
            if isinstance(value.get(key), str)
        )
    return ""


def _obligation_id(event_id: str, session_id: str, dependency: str) -> str:
    identity = f"{event_id}\0{session_id}\0{dependency}"
    return "MEM-OBL-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16].upper()


def _recognized_event(response: str, contract: dict[str, Any]) -> bool:
    markers = [line[len(_EVENT_PREFIX):] for line in response.splitlines()
               if line.startswith(_EVENT_PREFIX)]
    if not markers:
        return False
    if len(markers) != 1:
        raise ValueError("expected exactly one governance event in tool result")
    event = json.loads(markers[0])
    expected = {
        "id": contract["event_id"],
        "type": contract["event_type"],
        "dependency": contract["dependency"],
        "status": contract["event_status"],
    }
    if not isinstance(event, dict) or event != expected:
        raise ValueError("governance event does not match declared contract")
    return True


def _shell_segments(command: str) -> list[str]:
    segments = []
    current: list[str] = []
    quote = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote is None and command.startswith("<#", index):
            # PowerShell block comments end at the first #>, including across
            # lines. Keep a token boundary where the comment was removed.
            end = command.find("#>", index + 2)
            current.append(" ")
            index = len(command) if end < 0 else end + 2
            continue
        if quote is None and char == "#" and (
            not current or current[-1].isspace() or current[-1] in "(){}'\""
        ):
            # Do not split a commented ampersand into a checker invocation.
            # A hash inside an unquoted path/token is literal PowerShell text.
            end = command.find("\n", index)
            index = len(command) if end < 0 else end
            continue
        if char == "`" and quote != "'" and index + 1 < len(command):
            current.extend(command[index:index + 2])
            index += 2
            continue
        if char in ("'", '"'):
            if quote == char and command[index:index + 2] == char * 2:
                current.extend(command[index:index + 2])
                index += 2
                continue
            quote = None if quote == char else char if quote is None else quote
        elif char in (";", "\n", "|", "&") and quote is None:
            segments.append("".join(current).strip())
            current.clear()
            index += 1
            continue
        current.append(char)
        index += 1
    segments.append("".join(current).strip())
    return [segment for segment in segments if segment]


def _approved_invocation(repo: Path, command: str, source: Path) -> bool:
    for segment in _shell_segments(command):
        tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', segment)
        if not tokens:
            continue
        first = tokens[0].strip("\"'")
        candidate = None
        executable = Path(first.replace("\\", os.sep)).name.casefold()
        if executable in ("pwsh", "pwsh.exe", "powershell", "powershell.exe"):
            for index, token in enumerate(tokens[:-1]):
                if token.casefold() == "-file":
                    candidate = tokens[index + 1].strip("\"'")
                    break
        elif first != "Write-Output" and first != "Get-Content":
            candidate = first
        if candidate is None:
            continue
        # Invocation candidates may be unrelated programs outside the repo.
        # Compare their resolved identity; only the approved producer is subject
        # to containment and byte verification in _contract/recheck.
        candidate_path = (repo / Path(candidate.replace("\\", os.sep))).resolve()
        if candidate_path == source:
            return True
    return False


def _verified_checker_event(repo: Path, contract: dict[str, Any]) -> tuple[bool, str]:
    source = _within_repo(repo, Path(contract["approved_producer"]["path"]))
    if hashlib.sha256(source.read_bytes()).hexdigest().casefold() != contract["approved_producer"]["sha256"].casefold():
        raise ValueError("approved producer changed before execution")
    try:
        completed = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(source)],
            cwd=repo, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"approved producer could not run: {exc}") from exc
    if hashlib.sha256(source.read_bytes()).hexdigest().casefold() != contract["approved_producer"]["sha256"].casefold():
        raise ValueError("approved producer changed during execution")
    if completed.returncode == 0 and "GOVERNANCE_EVENT_V1" not in completed.stdout:
        return False, ""
    if completed.returncode != contract["approved_producer"]["blocked_exit_code"]:
        raise ValueError(f"approved producer returned unexpected exit {completed.returncode}")
    if not _recognized_event(completed.stdout, contract):
        raise ValueError("approved producer exited blocked without declared event")
    return True, hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()


def _audit(folder: Path, entry: dict[str, Any]) -> None:
    item = {"at": datetime.now(timezone.utc).isoformat(), **entry}
    with (folder / "hook-audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")


def _register(repo: Path, contract: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event.get("hook_event_name") != "PostToolUse" or event.get("tool_name") != "Bash":
        return {}
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return {}
    source = _within_repo(repo, Path(contract["approved_producer"]["path"]))
    session_id = event.get("session_id")
    tool_use_id = event.get("tool_use_id")
    turn_id = event.get("turn_id")
    try:
        approved = _approved_invocation(repo, command, source)
    except (OSError, ValueError):
        # Recognition failed before an observation could be created. Persist
        # unknown registration state rather than letting Stop infer no event.
        if all(isinstance(value, str) and value for value in (session_id, tool_use_id, turn_id)):
            _record_registration_failure(repo, session_id, turn_id, tool_use_id, contract)
        raise
    if not approved:
        return {}
    if not all(isinstance(value, str) and value for value in (session_id, tool_use_id, turn_id)):
        raise ValueError("recognized blocker lacks session, turn, or tool identity")
    try:
        observation = _record_observation(
            repo, session_id, turn_id, tool_use_id,
            contract["event_id"], contract["dependency"],
        )
    except OSError:
        _record_registration_failure(repo, session_id, turn_id, tool_use_id, contract)
        raise
    try:
        blocked, verified_output_sha = _verified_checker_event(repo, contract)
    except (OSError, ValueError, json.JSONDecodeError):
        _finish_observation(observation, "registration_error")
        raise
    if not blocked:
        _finish_observation(observation, "no_blocker")
        return {}
    folder = _state_folder(repo, session_id)
    obligation_id = _obligation_id(contract["event_id"], session_id, contract["dependency"])
    _finish_observation(observation, "blocked", obligation_id)
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "id": obligation_id,
        "event_id": contract["event_id"],
        "type": "blocker",
        "status": "pending",
        "dependency": contract["dependency"],
        "source": "PostToolUse",
        "session_id": session_id,
        "turn_id": turn_id,
        "tool_use_id": tool_use_id,
        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        "verified_producer_sha256": contract["approved_producer"]["sha256"].lower(),
        "verified_output_sha256": verified_output_sha,
        "verified_by": "hook_recheck",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    target = folder / f"{obligation_id}.json"
    already_registered = False
    try:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
    except FileExistsError:
        already_registered = True
        existing = json.loads(target.read_text(encoding="utf-8"))
        if any(existing.get(key) != record[key] for key in (
            "id", "event_id", "dependency", "session_id"
        )):
            raise ValueError(f"obligation identity collision: {obligation_id}")
    instruction = (
        f"Required dependency {contract['dependency']} is blocked. Memory obligation {obligation_id} "
        "is pending. Add one risk line containing both the obligation ID and dependency under "
        "a Risks/風險 heading in PLAN.md, and one line containing both in "
        "memory/01_active_task.md before this turn ends."
    )
    _audit(folder, {
        "event": "PostToolUse",
        "turn_id": turn_id,
        "tool_use_id": tool_use_id,
        "obligation_id": obligation_id,
        "decision": "already_registered" if already_registered else "registered",
    })
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": instruction}}


def _plan_line(plan: str, obligation_id: str, dependency: str, headings: list[str]) -> bool:
    in_risks = False
    heading_depth = 0
    allowed = {heading.strip().casefold() for heading in headings}
    for line in plan.splitlines():
        heading = _HEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if line[heading.end():].strip().casefold() in allowed:
                in_risks, heading_depth = True, depth
            elif in_risks and depth <= heading_depth:
                in_risks = False
        elif in_risks and obligation_id in line and dependency in line:
            return True
    return False


def _active_line(active: str, obligation_id: str, dependency: str) -> bool:
    return any(obligation_id in line and dependency in line for line in active.splitlines())


def _set_status(path: Path, record: dict[str, Any], status: str) -> None:
    if record.get("status") == status:
        return
    updated = dict(record)
    updated["status"] = status
    if status == "resolved":
        updated["resolved_at"] = datetime.now(timezone.utc).isoformat()
    else:
        updated.pop("resolved_at", None)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _pending(repo: Path, session_id: str, contract: dict[str, Any]) -> list[dict[str, Any]]:
    folder = _state_folder(repo, session_id)
    if not folder.exists():
        return []
    plan = _within_repo(repo, Path("PLAN.md")).read_text(encoding="utf-8")
    active = _within_repo(repo, Path("memory/01_active_task.md")).read_text(encoding="utf-8")
    pending = []
    for path in sorted(folder.glob("MEM-OBL-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or record.get("session_id") != session_id or (
            record.get("event_id") != contract["event_id"]
        ) or not isinstance(record.get("id"), str) or path.stem != record["id"]:
            raise ValueError(f"invalid obligation record: {path.name}")
        obligation_id, dependency = record["id"], record.get("dependency")
        if not isinstance(dependency, str) or dependency != contract["dependency"]:
            raise ValueError(f"invalid obligation dependency: {path.name}")
        if record.get("status") == "registration_error":
            pending.append(record)
            continue
        if record.get("status") not in ("pending", "resolved"):
            raise ValueError(f"invalid obligation status: {path.name}")
        resolved = _plan_line(plan, obligation_id, dependency, contract["plan_risk_headings"]) and _active_line(active, obligation_id, dependency)
        _set_status(path, record, "resolved" if resolved else "pending")
        if not resolved:
            pending.append(record)
    return pending


def _observation_failures(repo: Path, session_id: str, contract: dict[str, Any]) -> list[str]:
    folder = _observation_folder(repo, session_id)
    if not folder.exists():
        return []
    if not folder.is_dir():
        raise ValueError("obligation observation path is not a directory")
    failures = []
    for path in sorted(folder.glob("*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("session_id") != session_id or (
            receipt.get("event_id") != contract["event_id"]
        ) or receipt.get("dependency") != contract["dependency"] or not all(
            isinstance(receipt.get(key), str) and receipt[key]
            for key in ("turn_id", "tool_use_id")
        ):
            raise ValueError(f"invalid obligation observation: {path.name}")
        status = receipt.get("status")
        if status in ("checking", "registration_error"):
            failures.append(f"MEMORY_OBLIGATION_REGISTRATION_ERROR:{path.stem}")
        elif status == "blocked":
            obligation_id = receipt.get("obligation_id")
            if not isinstance(obligation_id, str) or obligation_id != _obligation_id(
                contract["event_id"], session_id, contract["dependency"]
            ):
                raise ValueError(f"invalid obligation identity in observation: {path.name}")
            if not (_state_folder(repo, session_id) / f"{obligation_id}.json").is_file():
                failures.append(f"MEMORY_OBLIGATION_STATE_LOST:{obligation_id}")
        elif status != "no_blocker":
            raise ValueError(f"invalid obligation observation status: {path.name}")
    return failures


def _stop(repo: Path, contract: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event.get("hook_event_name") != "Stop":
        return {}
    session_id = event.get("session_id")
    if not isinstance(session_id, str):
        raise ValueError("Stop event lacks session_id")
    unresolved = _pending(repo, session_id, contract)
    observation_failures = _observation_failures(repo, session_id, contract)
    folder = _state_folder(repo, session_id)
    if not unresolved and not observation_failures:
        if folder.exists():
            _audit(folder, {
                "event": "Stop", "turn_id": event.get("turn_id"),
                "stop_hook_active": event.get("stop_hook_active"),
                "pending_ids": [], "decision": "allow_resolved",
            })
        return {}
    ids = ", ".join([record["id"] for record in unresolved] + observation_failures)
    folder.mkdir(parents=True, exist_ok=True)
    required = "BLOCKED: MEMORY_OBLIGATION_UNRESOLVED " + ids
    last_message = event.get("last_assistant_message") or ""
    if event.get("stop_hook_active"):
        if isinstance(last_message, str) and required in last_message:
            _audit(folder, {
                "event": "Stop", "turn_id": event.get("turn_id"),
                "stop_hook_active": True, "pending_ids": [record["id"] for record in unresolved],
                "observation_failures": observation_failures,
                "decision": "allow_honest_blocked_report",
            })
            return {}
        _audit(folder, {
            "event": "Stop", "turn_id": event.get("turn_id"),
            "stop_hook_active": True, "pending_ids": [record["id"] for record in unresolved],
            "observation_failures": observation_failures,
            "decision": "stop_unresolved",
        })
        return {
            "continue": False,
            "stopReason": f"Unresolved memory obligation: {ids}",
            "systemMessage": f"Task completion blocked by unresolved memory obligation: {ids}",
        }
    reason = (
        f"Pending memory obligation: {ids}. Update PLAN.md Risks/風險 and "
        "memory/01_active_task.md; each needs a line containing its obligation ID and "
        f"dependency {contract['dependency']}. If you cannot update them, report exactly "
        f"'{required}' and explain the blocker. Do not claim DONE."
    )
    _audit(folder, {
        "event": "Stop", "turn_id": event.get("turn_id"),
        "stop_hook_active": False, "pending_ids": [record["id"] for record in unresolved],
        "observation_failures": observation_failures,
        "decision": "block",
    })
    return {"decision": "block", "reason": reason}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", choices=("post-tool-use", "stop"), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--approved-producer-path", type=Path, required=True)
    parser.add_argument("--approved-producer-sha256", required=True)
    args = parser.parse_args(argv)
    repo = None
    raw_stdin = b""
    stage = "setup"
    try:
        repo = args.repo_root.resolve(strict=True)
        contract = _contract(repo, args.contract, args.approved_producer_path, args.approved_producer_sha256)
        stage = "payload"
        raw_stdin = sys.stdin.buffer.read()
        event = json.loads(raw_stdin)
        if not isinstance(event, dict):
            raise ValueError("hook payload must be an object")
        stage = "event"
        result = _register(repo, contract, event) if args.event == "post-tool-use" else _stop(repo, contract, event)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if (args.event == "post-tool-use" and repo is not None and raw_stdin
                and os.environ.get("MEM_TRIGGER_CAPTURE_ERRORS") == "1"):
            try:
                folder = _within_repo(repo, Path("memory/.hook_payload_errors"))
                folder.mkdir(parents=True, exist_ok=True)
                identity = uuid.uuid4().hex
                (folder / f"{identity}.stdin.bin").write_bytes(raw_stdin)
                (folder / f"{identity}.error.json").write_text(json.dumps({
                    "stage": stage,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "stdin_bytes": len(raw_stdin),
                    "stdin_sha256": hashlib.sha256(raw_stdin).hexdigest(),
                }, indent=2), encoding="utf-8")
            except OSError:
                pass
        if args.event == "stop":
            result = {"decision": "block", "reason": f"MEMORY_OBLIGATION_STATE_ERROR: {exc}"}
        else:
            result = {"decision": "block", "reason": f"MEMORY_OBLIGATION_REGISTRATION_ERROR: {exc}"}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
