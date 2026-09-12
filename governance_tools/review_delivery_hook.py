"""Antigravity PreToolUse wiring for direct GitHub CLI merge proposals.

The existing Slice 3 function owns every review predicate. This adapter only
routes a supported command, acquires its live snapshot in the same repository
context, reads the caller's existing ledger, and maps the result to deny/ask.
It never executes the proposed command. Shell wrappers/aliases are not covered.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

# Allow an absolute script invocation with Python -I from a consumer workspace.
# Never import framework modules from the proposed command's working directory.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools.review_blocking_findings import assess_blocking_findings
from governance_tools.review_evidence import ACQUISITION_QUERY


def _response(gate: str, reason: str, checks: Any = None) -> dict[str, str]:
    """ask preserves the platform permission check; allow would grant execution."""
    detail = {"REVIEW_GATE": gate, "MERGE_READY": "NOT_EVALUATED" if gate == "PASS" else "NO",
              "reason": reason}
    if gate == "NOT_EVALUATED":
        detail["MERGE_READY"] = "NOT_EVALUATED"
    if checks is not None:
        detail["checks"] = checks
    return {"decision": "ask" if gate in ("PASS", "NOT_EVALUATED") else "deny",
            "reason": json.dumps(detail, ensure_ascii=True, separators=(",", ":"))}


def _merge_target(command: str, gh_executable: str) -> tuple[bool, int | None]:
    """Recognize the bounded direct form, not arbitrary shell programs.

    Bare gh and alternate gh.exe paths are merge-shaped but cannot prove which
    binary the shell will run, so they are denied as unsupported. Commands
    through wrappers, functions or aliases with other names remain outside.
    """
    direct = re.match(
        r"""^\s*(?:&\s*)?(?P<executable>"[^"\r\n]+"|'[^'\r\n]+'|\S+)\s+pr\s+merge(?:\s+|$)""",
        command, flags=re.IGNORECASE | re.DOTALL,
    )
    if direct is not None:
        supplied = direct.group("executable").strip("\"'")
        normalized_supplied = re.sub(r"[\\/]+", "/", supplied).casefold().rstrip("/")
        normalized_configured = re.sub(r"[\\/]+", "/", gh_executable).casefold().rstrip("/")
        basename = re.split(r"[\\/]", supplied)[-1].casefold()
        if basename in {"gh", "gh.exe"} and normalized_supplied != normalized_configured:
            return True, None
    # Windows accepts either separator spelling for the same configured path.
    executable = r"[\\/]".join(re.escape(part) for part in re.split(r"[\\/]", gh_executable))
    prefix = rf"(?:gh(?:\.exe)?|{executable}|\"{executable}\"|'{executable}')"
    match = re.match(rf"^\s*(?:&\s*)?{prefix}\s+pr\s+merge(?:\s+|$)(.*)$", command,
                     flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return False, None
    tokens = match[1].split()
    if not tokens or not re.fullmatch(r"[1-9][0-9]*", tokens[0]):
        return True, None
    number = int(tokens.pop(0))
    if number > 2147483647:  # GraphQL Int input, not a review predicate.
        return True, None
    while tokens:
        option = tokens.pop(0)
        if option in ("--merge", "--squash", "--rebase", "-m", "-s", "-r", "--delete-branch"):
            continue
        if (option == "--match-head-commit" and tokens
                and re.fullmatch(r"[0-9a-fA-F]{40}", tokens[0])):
            tokens.pop(0)
            continue
        return True, None
    return True, number


def acquire_snapshot(gh_executable: str, cwd: str, number: int) -> Any:
    """Read-only GraphQL, with gh's own repository context resolution.

    No shell, merge command, evidence cache, or automatic assessment repair.
    Environment/context are the same as the pending direct gh invocation.
    This is not an audit of executable provenance or repository configuration.
    """
    executable = Path(gh_executable)
    working_directory = Path(cwd)
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("configured gh executable must be an existing absolute path")
    if not working_directory.is_absolute() or not working_directory.is_dir():
        raise ValueError("tool Cwd must be an existing absolute directory")
    completed = subprocess.run(
        [str(executable), "api", "graphql", "-f", "query=" + ACQUISITION_QUERY,
         "-F", "owner={owner}", "-F", "name={repo}", "-F", f"number={number}"],
        cwd=str(working_directory), capture_output=True, text=True, encoding="utf-8",
        errors="strict", timeout=20, check=True, shell=False,
    )
    return json.loads(completed.stdout)


def evaluate_tool_call(event: Any, config: Any, *,
                       acquire: Callable[[str, str, int], Any] = acquire_snapshot) -> dict[str, str]:
    """Consume S1 -> S2 -> S3 through S3's existing entrypoint, without new rules."""
    if not isinstance(event, dict) or not isinstance(event.get("toolCall"), dict):
        return _response("UNKNOWN", "Invalid native tool event")
    tool = event["toolCall"]
    if tool.get("name") != "run_command":
        return _response("NOT_EVALUATED", "Outside run_command; standard permissions apply")
    args = tool.get("args")
    if not isinstance(args, dict) or not isinstance(args.get("CommandLine"), str):
        return _response("UNKNOWN", "Missing CommandLine")
    gh = config.get("gh_executable") if isinstance(config, dict) else None
    if not isinstance(gh, str) or not gh.strip():
        return _response("UNKNOWN", "Missing configured gh_executable")
    relevant, number = _merge_target(args["CommandLine"], gh)
    if not relevant:
        return _response("NOT_EVALUATED", "Outside direct gh pr merge; standard permissions apply")
    if number is None:
        return _response(
            "UNKNOWN",
            "Unsupported direct merge invocation; use the configured absolute executable, PR number, and supported arguments",
        )
    cwd = args.get("Cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        return _response("UNKNOWN", "Missing tool Cwd")
    try:
        snapshot = acquire(gh, cwd, number)
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        checks = assess_blocking_findings(None, None)
        return _response("UNKNOWN", f"Live review acquisition failed: {type(exc).__name__}", checks)

    assessment = None
    ledger = config.get("assessment_path")
    if isinstance(ledger, str) and Path(ledger).is_absolute():
        try:
            assessment = json.loads(Path(ledger).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, UnicodeError):
            pass  # Missing or invalid assessment stays UNKNOWN in the existing gate.
    review_id = assessment.get("review_id") if isinstance(assessment, dict) else None
    checks = assess_blocking_findings(snapshot, review_id, assessment)
    gate = checks["BLOCKING_GATE"]
    return _response(gate, "Review predicates only; CI and owner authorization remain separate", checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="JSON with gh_executable and assessment_path")
    args = parser.parse_args(argv)
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
        event = json.load(sys.stdin)
        result = evaluate_tool_call(event, config)
    except (OSError, ValueError, UnicodeError) as exc:
        result = _response("UNKNOWN", f"Hook input/config failed: {type(exc).__name__}")
    print(json.dumps(result, ensure_ascii=True))
    # Native deny/ask is authoritative. A valid hook response is not a merge exit status.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
