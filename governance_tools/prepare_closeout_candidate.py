"""Explicit preparation for a pinned submodule consumer; never runs closeout.

R1 establishes consumer/session identity. R2 owns shared text and exclusion.
Git identity is a correctness check, not protection against hostile local code
or concurrent, uncooperative Git/filesystem mutation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import shared_closeout_ownership as ownership
from governance_tools.framework_versioning import load_framework_lock
from runtime_hooks.core._canonical_closeout import (
    assess_session_closeout_binding, build_candidate_artifact,
)

_FIELDS = {"task_intent", "work_summary", "tools_used", "artifacts_referenced", "open_risks"}
_LEGACY = {"checks_run": "CHECKS_RUN", "not_done": "NOT_DONE",
           "recommended_memory_update": "RECOMMENDED_MEMORY_UPDATE"}


class PreparationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PreparationError(message)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], check=True,
                            capture_output=True, encoding="utf-8", timeout=15)
    return result.stdout.strip()


def _root(path: Path) -> Path:
    _require(path.is_absolute(), "absolute root required")
    root = path.resolve(strict=True)
    _require(root.is_dir() and Path(_git(root, "rev-parse", "--show-toplevel")).resolve() == root,
             "root must be the actual Git worktree top-level")
    return root


def _clean_control(root: Path, relative: str) -> Path:
    path = ownership._path(root, relative)
    staged = _git(root, "ls-files", "--stage", "--", relative)
    _require(bool(re.fullmatch(r"100644 [0-9a-f]{40,64} 0\t" + re.escape(relative), staged)),
             f"tracked regular control file required: {relative}")
    _require(not _git(root, "status", "--porcelain=v1", "--", relative),
             f"uncommitted control file: {relative}")
    return path


def validate_framework_binding(consumer_root: Path, framework_root: Path) -> tuple[Path, Path]:
    # R1/R2 also call Git. Reject inherited overrides rather than validating
    # one index here and letting those readers use a different one later.
    overrides = sorted(key for key in os.environ if key.upper().startswith("GIT_"))
    _require(not overrides, "Git environment overrides unsupported: " + ", ".join(overrides))
    consumer, framework = _root(consumer_root), _root(framework_root)
    _require(framework != consumer and framework.is_relative_to(consumer),
             "framework must be a registered consumer submodule")
    _require(Path(__file__).resolve().parents[1] == framework,
             "execute the entry from the registered framework checkout")
    modules = _clean_control(consumer, ".gitmodules")
    _clean_control(consumer, "governance/framework.lock.json")
    registrations = _git(consumer, "config", "--null", "--file", str(modules), "--get-regexp",
                         r"^submodule\..*\.path$")
    matches = []
    for record in registrations.rstrip("\0").split("\0"):
        _, relative = record.split("\n", 1)
        path = ownership._path(consumer, relative)
        if path.resolve() == framework:
            matches.append(relative)
    _require(len(matches) == 1, "framework path must have exactly one submodule registration")
    relative = matches[0]
    staged = _git(consumer, "ls-files", "--stage", "--", relative)
    match = re.fullmatch(r"160000 ([0-9a-f]{40,64}) 0\t" + re.escape(relative), staged)
    _require(match is not None, "unmerged or missing index gitlink")
    oid = match.group(1)
    _require(not _git(consumer, "diff", "--cached", "--name-only", "HEAD", "--", relative),
             "uncommitted gitlink")
    _require(_git(framework, "rev-parse", "HEAD") == oid, "checkout HEAD differs from index gitlink")
    _require(not _git(framework, "status", "--porcelain=v1", "--untracked-files=all"),
             "dirty framework checkout")
    lock = load_framework_lock(consumer)
    _require(isinstance(lock, dict) and lock.get("adopted_commit") == oid,
             "framework lock adopted_commit differs from index gitlink")
    return consumer, framework


def _single_line(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} must be a nonempty string")
    _require(all(ord(c) >= 32 and c not in "\x7f\x85\u2028\u2029" for c in value),
             f"{name} must be a single line without control characters")
    return value


def render_inputs(value: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    """One explicit source for candidate and legacy text, without invented results."""
    _require(isinstance(value, dict) and _FIELDS <= value.keys()
             and not value.keys() - _FIELDS - _LEGACY.keys(), "unexpected or missing input fields")
    candidate = {name: value[name] for name in ("task_intent", "work_summary", "tools_used",
                                               "artifacts_referenced", "open_risks")}
    for name in ("task_intent", "work_summary"):
        _single_line(candidate[name], name)
    for name in ("tools_used", "artifacts_referenced", "open_risks"):
        items = candidate[name]
        _require(isinstance(items, list), f"{name} must be a list")
        for item in items:
            _single_line(item, name)
            _require("," not in item and item.strip().upper() != "NONE",
                     f"{name} contains an unrepresentable legacy list item")
        candidate[name] = list(items)
    text = [f'TASK_INTENT: {candidate["task_intent"]}',
            f'WORK_COMPLETED: {candidate["work_summary"]}',
            'FILES_TOUCHED: ' + (", ".join(candidate["artifacts_referenced"]) or "NONE"),
            'OPEN_RISKS: ' + (", ".join(candidate["open_risks"]) or "NONE")]
    for key, label in _LEGACY.items():
        text.append(label + ": " + _single_line(value.get(key, "NOT PROVIDED"), key))
    return candidate, ("\n".join(text) + "\n").encode("utf-8")


def _preflight_session(root: Path, session_id: str) -> None:
    ownership._identity(root, session_id)
    _require(not ownership._completion(root, session_id), "consumed session cannot prepare")


def _write_payload(path: Path, data: bytes, *, exclusive: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb" if exclusive else "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    _require(path.read_bytes() == data, "payload read-back differs from reserved bytes")


def prepare(consumer_root: Path, framework_root: Path, session_id: str,
            inputs: dict[str, Any]) -> dict[str, Any]:
    root, framework = validate_framework_binding(consumer_root, framework_root)
    _preflight_session(root, session_id)
    candidate, text = render_inputs(inputs)
    for relative in candidate["artifacts_referenced"]:
        ownership._path(root, relative)
    now = datetime.now(timezone.utc)
    relative, payload, data = build_candidate_artifact(
        session_id, candidate, timestamp=now.strftime("%Y%m%dT%H%M%S%fZ"),
        generated_at=now.isoformat(),
    )
    _require(assess_session_closeout_binding(session_id, root, payload)["status"] == "valid",
             "candidate does not bind to the existing session")
    candidate_path = ownership._path(root, relative.as_posix())
    text_path = ownership._path(root, ownership.TEXT)
    identity = {"relative_path": relative.as_posix(), "sha256": hashlib.sha256(data).hexdigest()}
    text_digest = hashlib.sha256(text).hexdigest()
    with ownership.execution_exclusion(root) as lease:
        # Recheck after exclusion; no caller can supply a second root assertion
        # as a substitute for the existing envelope or registered Git identity.
        validate_framework_binding(root, framework)
        _preflight_session(root, session_id)
        prior = ownership._owner(lease)
        _require(prior is None or prior["state"] != "HOLD"
                 or prior["hold_reason"] == "preparation_pending",
                 "closeout recovery HOLD cannot be replaced by preparation")
        existing = sorted(candidate_path.parent.glob("*.json"))
        _require(not existing or candidate_path.name > existing[-1].name,
                 "retry must append a newer candidate; clock/path collision")
        reserved = ownership.acquire_owner(lease, session_id, identity, text_digest)
        # Deliberately no rollback: failed writes retain HOLD and partial bytes.
        _write_payload(ownership._path(root, relative.as_posix()), data, exclusive=True)
        _write_payload(ownership._path(root, ownership.TEXT), text, exclusive=False)
        _require(candidate_path.read_bytes() == data and text_path.read_bytes() == text,
                 "reserved payload changed before confirmation")
        owner = ownership.confirm_prepared(lease, session_id, reserved["generation"])
    return {"status": "PREPARED", "state": owner["state"], "session_id": session_id,
            "consumer_root": str(root), "generation": owner["generation"],
            "candidate_identity": identity, "text_digest": text_digest,
            "closeout_executed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--framework-root", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--input", type=Path, help="JSON input file; omit to read stdin")
    args = parser.parse_args(argv)
    try:
        raw = args.input.read_text(encoding="utf-8-sig") if args.input else sys.stdin.read()
        result = prepare(args.consumer_root, args.framework_root, args.session_id, json.loads(raw))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc),
                          "partial_preparation_may_remain": True}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
