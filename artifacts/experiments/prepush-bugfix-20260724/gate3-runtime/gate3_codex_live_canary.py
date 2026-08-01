from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import gate3_evidence_chain as chain
import gate3_wrapper_semantic_contract as contract


HERE = Path(__file__).resolve().parent
EXPERIMENT_ROOT = HERE.parent
DEFAULT_CONTRACT = EXPERIMENT_ROOT / "candidate/gate3-protocol-contract-v1.json"
DEFAULT_HARNESS_CONTRACT = (
    EXPERIMENT_ROOT / "candidate/gate3-harness-contract-v1.json"
)
DEFAULT_CANDIDATE_MANIFEST = (
    EXPERIMENT_ROOT
    / "candidate/gate3-preregistration-amendment-v1-candidate-manifest.json"
)
DEFAULT_SKILL_PACKET = EXPERIMENT_ROOT / "skill-packet-bugfix.md"
DEFAULT_SESSION_LAUNCHER = HERE / "gate3_codex_session_launcher.ps1"
DEFAULT_PAIR_RUNNER = HERE / "gate3_codex_pair_runner.ps1"
DEFAULT_TESTS = HERE / "test_gate3_codex_live_canary.py"

SUMMARY_SCHEMA = "gate3-codex-live-canary.v4"
ROUTE_PLAN_SCHEMA = "gate3-codex-live-route-plan.v4"
ROUTE_RECEIPT_SCHEMA = "gate3-codex-live-route-receipt.v4"
CAPTURE_RECEIPT_SCHEMA = "gate3-codex-live-capture-receipt.v2"
BASELINE_RECEIPT_SCHEMA = "gate3-codex-live-baseline-test-receipt.v1"
CREDENTIAL_RECEIPT_SCHEMA = "gate3-codex-credential-runner-receipt.v1"
FAILURE_RECEIPT_SCHEMA = "gate3-codex-live-canary-failure-receipt.v8"
AUTHORIZATION = "non_counted_codex_live_canary_only"
REHEARSAL_KIND = "fresh_live_codex_ab_non_counted_privacy_safe"
EXPECTED_CANDIDATE_MANIFEST_SHA256 = (
    "b0a4163759dc6896b837964286176ecd9030793fcd0a7bc2852baa4888fa0b75"
)
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_COMP_HASH = "3000"
DEFAULT_CLI_VERSION = "0.146.0"
DEFAULT_REASONING = "low"
DEFAULT_PROVIDER = "openai"
DEFAULT_TIMEZONE = "Asia/Taipei"
BASELINE_GIT_IDENTITY = {
    "email": "gate3-canary@example.invalid",
    "name": "Gate3 Canary",
}
PRODUCER_GIT_IDENTITY = {
    "email": "gate3-producer@example.invalid",
    "name": "Gate3 Synthetic Producer",
}
PUBLIC_CONTEXT_TOKENS = {"A": "WORKSPACE_A", "B": "WORKSPACE_B"}
GENERIC_CONTEXT_TOKEN = "WORKSPACE"
SANITIZER_SCHEMA = "gate3-codex-public-evidence-sanitizer.v4"
SANITIZER_RULES = {
    "canonical_jsonl": True,
    "mapping_keys": "redacted_fail_closed_on_collision",
    "replacements": [
        "exact_workspace_to_arm_token",
        "windows_user_path_to_LOCAL_USER_PATH",
        "windows_sid_to_WINDOWS_SID",
        "desktop_hostname_to_LOCAL_HOST",
        "all_windows_absolute_and_device_namespace_forms_to_LOCAL_ABSOLUTE_PATH",
    ],
    "schema": SANITIZER_SCHEMA,
}
CREDENTIAL_CONTRACT = {
    "auth_route": "chatgpt",
    "cleanup_before_publication": True,
    "credential_bytes_public": False,
    "credential_digest_public": False,
    "credential_source_path_public": False,
    "preflight_required": True,
    "private_runtime_root": "user_temp",
    "replacement_sessions": 0,
    "schema": "gate3-codex-credential-contract.v1",
    "secret_storage": "ephemeral_file_cache",
    "session_invocations": 2,
    "temporary_cli_installations": 1,
}
SHELL_WRAPPER_RE = re.compile(
    r'^const r = await tools\.shell_command\(\{command:'
    r'(?P<command>"(?:\\.|[^"\\])*"),workdir:'
    r'(?P<workdir>"(?:\\.|[^"\\])*")\}\); text\(r\)\r?\n?$'
)
PATCH_WRAPPER_RE = re.compile(
    r'^const patch = (?P<patch>"(?:\\.|[^"\\])*");\r?\n'
    r'text\(await tools\.apply_patch\(patch\)\);\r?\n?$'
)
WRAPPER_MISMATCH_RETENTION_LIMIT = 32
FROZEN_TOOL_FAMILIES = ("shell_command", "apply_patch")
# Why a rejected tool input was rejected. These are not interchangeable:
# out_of_route_tool is a route-scope violation, multiple_calls is a shape the
# route does not model, and single_frozen_call is ordinary wrapper variance.
# Collapsing them into one label makes a failure receipt unreadable.
WRAPPER_REJECTION_CLASSES = (
    "single_frozen_call",
    "multiple_calls",
    "out_of_route_tool",
    "no_tool_call",
)
SAFE_TOOL_INPUT_FIELD_NAMES = (
    "command",
    "justification",
    "login",
    "prefix_rule",
    "sandbox_permissions",
    "timeout_ms",
    "workdir",
)
WINDOWS_USER_PATH_RE = re.compile(
    r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'()<>{}\[\]]+"
    r"(?:[\\/]+[^\\/\s\"'()<>{}\[\]]+)*"
)
WINDOWS_SID_RE = re.compile(r"S-\d(?:-\d+){2,}")
DESKTOP_HOST_RE = re.compile(r"(?i)\bDESKTOP-[A-Z0-9]+\b")
BEARER_CREDENTIAL_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-=]{12,}")
OPENAI_SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}")
TOKEN_FIELD_RE = re.compile(
    r"(?i)^(?:access_token|refresh_token|id_token)$"
)
PUBLIC_RUN_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,94}[a-z0-9])?$")
WINDOWS_PATH_COMPONENT = r"[^\\/\s\"'()<>{}\[\],]+"
WINDOWS_NAMESPACE_COMPONENT = r"[^\\/\s\"'()<>\[\],]+"
WINDOWS_ABSOLUTE_PATH_RE = re.compile(
    rf"""
    (?:
        # Win32 device namespaces (\\.\ and \\?\) plus their slash-equivalent
        # spellings. This intentionally covers generic namespace targets such
        # as PhysicalDrive*, Volume{{GUID}}, GLOBALROOT and named pipes.
        (?<![:A-Z0-9_])
        [\\/]{{2,}}[?.][\\/]+
        {WINDOWS_NAMESPACE_COMPONENT}
        (?:[\\/]+{WINDOWS_NAMESPACE_COMPONENT})*
        (?:[\\/]+)?
      |
        # Native NT object-manager namespace spellings equivalent to Win32
        # device paths. Include documented aliases for the DOS-device tree.
        (?<![:A-Z0-9_])
        [\\/]+(?:Device|\?\?|Global\?\?|DosDevices)[\\/]+
        {WINDOWS_NAMESPACE_COMPONENT}
        (?:[\\/]+{WINDOWS_NAMESPACE_COMPONENT})*
        (?:[\\/]+)?
      |
        # Extended UNC: \\?\UNC\server\share or its JSON-escaped form.
        (?<![:A-Z0-9_])
        [\\/]{{2,}}\?[\\/]+UNC[\\/]+
        {WINDOWS_PATH_COMPONENT}[\\/]+{WINDOWS_PATH_COMPONENT}
        (?:[\\/]+{WINDOWS_PATH_COMPONENT})*
      |
        # Extended drive path: \\?\C:\path, including the drive root.
        (?<![:A-Z0-9_])
        [\\/]{{2,}}\?[\\/]+[A-Z]:[\\/]+
        (?:{WINDOWS_PATH_COMPONENT}
        (?:[\\/]+{WINDOWS_PATH_COMPONENT})*)?
      |
        # Conventional UNC: \\server\share, excluding URL-style // after ':'.
        (?<![:A-Z0-9_])
        [\\/]{{2,}}(?![?.][\\/])
        {WINDOWS_PATH_COMPONENT}[\\/]+{WINDOWS_PATH_COMPONENT}
        (?:[\\/]+{WINDOWS_PATH_COMPONENT})*
      |
        # Drive-qualified path, including a bare drive root such as C:\.
        (?<![A-Z0-9_])
        [A-Z]:[\\/]+
        (?:{WINDOWS_PATH_COMPONENT}
        (?:[\\/]+{WINDOWS_PATH_COMPONENT})*)?
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)
SHELL_META_RE = re.compile(
    r"(?:;|&&|\|\||[|<>]|\r|\n|`|\$|%[A-Z_][A-Z0-9_]*%)",
    flags=re.IGNORECASE,
)
COMMAND_RULES = (
    (
        "git_rev_parse",
        re.compile(r"git rev-parse HEAD(?:\^)?", flags=re.IGNORECASE),
    ),
    (
        "git_rev_list_parents",
        re.compile(
            r"git rev-list --parents -n 1 HEAD",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "git_status",
        re.compile(
            r"git status --porcelain=v1 --untracked-files=all",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "git_diff_check",
        re.compile(r"git diff --check", flags=re.IGNORECASE),
    ),
    (
        "git_diff_scoped",
        re.compile(
            r"git diff -- (?:calc\.py|test_calc\.py)"
            r"(?: (?:calc\.py|test_calc\.py))?",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "git_add_scoped",
        re.compile(r"git add calc\.py", flags=re.IGNORECASE),
    ),
    (
        "git_commit",
        re.compile(
            r'git commit -m "[A-Z0-9][A-Z0-9 _.,:()+/\-]{0,119}"',
            flags=re.IGNORECASE,
        ),
    ),
    (
        "baseline_test",
        re.compile(r"python -B test_calc\.py", flags=re.IGNORECASE),
    ),
    (
        "directory_read",
        re.compile(r"Get-ChildItem -Force", flags=re.IGNORECASE),
    ),
    (
        "file_read",
        re.compile(
            r"Get-Content (?:calc\.py|test_calc\.py)",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "file_inventory",
        re.compile(r"rg --files", flags=re.IGNORECASE),
    ),
)
CONTEXT_META_EXPECTED = {
    "history_mode": "legacy",
    "model_provider": DEFAULT_PROVIDER,
    "originator": "Codex Desktop",
    "source": "exec",
    "thread_source": "user",
}
CONTEXT_TURN_EXPECTED = {
    "approval_policy": "never",
    "approvals_reviewer": "user",
    "multi_agent_version": "v1",
    "permission_profile": {"type": "disabled"},
    "personality": "pragmatic",
    "realtime_active": False,
    "sandbox_policy": {"type": "danger-full-access"},
    "summary": "auto",
    "timezone": DEFAULT_TIMEZONE,
}
ANON_MAPPING = {
    "OUT-111111111111": "A",
    "OUT-222222222222": "B",
}
COMMIT_ENV = {
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
}
REGRESSION_SNIPPET = (
    "from calc import add; "
    "raise SystemExit(0 if add(2, 3) == 5 else 1)"
)
TASK_PACKET = b"Repair add() and preserve the regression test.\n"
BASELINE_INSTRUCTION = b"Start from the planted subtraction defect.\n"
NO_SKILL_PACKET = (
    b"No Bug Fix Skill treatment packet is supplied for treatment A.\n"
)
NO_GOVERNANCE_PACKET = (
    b"No additional governance treatment packet is supplied.\n"
)
VALIDATOR_BUNDLE = b"def validate():\n    return True\n"
VALIDATOR_CONFIG = b'{"feedback_available":false,"mode":"live_canary"}\n'
PERMISSIONS = (
    b'{"approval":"explicit_operator_authorization_for_two_non_counted_sessions",'
    b'"network_confinement":"not_technically_enforced; forbidden_by_prompt",'
    b'"sandbox":"operator_authorized_danger_full_access",'
    b'"scope_confinement":"intended_by_frozen_prompt; verified_from_retained_tool_inputs"}\n'
)
BUDGET = b'{"tool_calls":40,"wall_clock_seconds":900}\n'
SCORER_RUBRIC = (
    b"Mechanical canary scorer: verify completion fields only; do not rank arms.\n"
)


class CanaryError(ValueError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: object) -> bytes:
    return chain._json_bytes(value)


def _jsonl_bytes(values: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
        for value in values
    )


def _sanitizer_rules_sha256() -> str:
    return _sha256_bytes(_json_bytes(SANITIZER_RULES))


def _path_text(value: object) -> str:
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str) or not value:
        raise CanaryError("context path is absent")
    return value.replace("/", "\\").rstrip("\\").casefold()


def _same_path(left: object, right: object) -> bool:
    return _path_text(left) == _path_text(right)


def _replace_workspace_text(
    text: str,
    workspace: str | os.PathLike[str],
    replacement: str,
) -> str:
    workspace = os.fspath(workspace)
    variants = {
        workspace,
        workspace.replace("\\", "\\\\"),
        workspace.replace("\\", "/"),
        workspace.replace("/", "\\"),
        workspace.replace("/", "\\\\"),
    }
    result = text
    for candidate in sorted(variants, key=len, reverse=True):
        result = re.sub(
            re.escape(candidate),
            lambda _: replacement,
            result,
            flags=re.IGNORECASE,
        )
    return result


def _sanitize_text(text: str, workspace: str, context_token: str) -> str:
    result = _replace_workspace_text(text, workspace, context_token)
    result = WINDOWS_USER_PATH_RE.sub("<LOCAL_USER_PATH>", result)
    result = WINDOWS_SID_RE.sub("<WINDOWS_SID>", result)
    result = DESKTOP_HOST_RE.sub("<LOCAL_HOST>", result)
    result = WINDOWS_ABSOLUTE_PATH_RE.sub("<LOCAL_ABSOLUTE_PATH>", result)
    return result


def _map_strings(value: Any, transform) -> Any:
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        return [_map_strings(item, transform) for item in value]
    if isinstance(value, dict):
        mapped: dict[Any, Any] = {}
        for key, item in value.items():
            mapped_key = transform(key) if isinstance(key, str) else key
            if mapped_key in mapped:
                raise CanaryError("sanitizer redaction created a mapping-key collision")
            mapped[mapped_key] = _map_strings(item, transform)
        return mapped
    return value


def sanitize_jsonl(
    path: Path,
    *,
    workspace: str,
    context_token: str,
) -> bytes:
    records = _load_jsonl(path, label="source evidence")
    sanitized = [
        _map_strings(
            record,
            lambda text: _sanitize_text(text, workspace, context_token),
        )
        for record in records
    ]
    return _jsonl_bytes(sanitized)


def _string_surfaces(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [
            surface
            for item in value
            for surface in _string_surfaces(item)
        ]
    if isinstance(value, dict):
        surfaces: list[str] = []
        for key, item in value.items():
            if isinstance(key, str):
                surfaces.append(key)
            surfaces.extend(_string_surfaces(item))
        return surfaces
    return []


def _privacy_surfaces(payload: bytes) -> list[str]:
    text = payload.decode("utf-8", errors="ignore")
    try:
        return _string_surfaces(json.loads(text))
    except json.JSONDecodeError:
        pass
    lines = [line for line in text.splitlines() if line.strip()]
    if lines:
        try:
            records = [json.loads(line) for line in lines]
        except json.JSONDecodeError:
            pass
        else:
            return [
                surface
                for record in records
                for surface in _string_surfaces(record)
            ]
    return [text]


def _privacy_violations(payload: bytes) -> list[str]:
    surfaces = _privacy_surfaces(payload)
    checks = {
        "desktop_hostname": DESKTOP_HOST_RE,
        "credential_bearer": BEARER_CREDENTIAL_RE,
        "credential_openai_secret": OPENAI_SECRET_RE,
        "credential_token_field": TOKEN_FIELD_RE,
        "windows_absolute_path": WINDOWS_ABSOLUTE_PATH_RE,
        "windows_sid": WINDOWS_SID_RE,
        "windows_user_path": WINDOWS_USER_PATH_RE,
    }
    return sorted(
        name
        for name, pattern in checks.items()
        if any(pattern.search(surface) for surface in surfaces)
    )


def verify_public_privacy(root: Path) -> int:
    violations: list[str] = []
    files = [path for path in root.rglob("*") if path.is_file()]
    for path in files:
        found = _privacy_violations(path.read_bytes())
        if found:
            violations.append(
                f"{_relative(path, root)}:{','.join(found)}"
            )
    if violations:
        raise CanaryError(
            "public evidence contains private host identifiers: "
            + "; ".join(violations)
        )
    return len(files)


def _load_json(path: Path) -> dict[str, Any]:
    return chain._load_json(path)


def _load_jsonl(
    path: Path | None,
    *,
    label: str,
    raw: bytes | None = None,
) -> list[dict[str, Any]]:
    if raw is None:
        if path is None:
            raise CanaryError(f"{label} has no source")
        raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise CanaryError(f"{label} must be non-empty newline-terminated JSONL")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CanaryError(f"{label} line {index} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise CanaryError(f"{label} line {index} is not an object")
        records.append(value)
    return records


def _world_state_census(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    world_state_records = [
        record for record in records if record.get("type") == "world_state"
    ]
    object_payloads = [
        record["payload"]
        for record in world_state_records
        if isinstance(record.get("payload"), dict)
    ]
    return {
        "full_true_count": sum(
            payload.get("full") is True for payload in object_payloads
        ),
        "object_payload_count": len(object_payloads),
        "raw_count": len(world_state_records),
        "state_object_count": sum(
            isinstance(payload.get("state"), dict)
            for payload in object_payloads
        ),
    }


def _validated_world_states(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    world_state_records = [
        record for record in records if record.get("type") == "world_state"
    ]
    if not world_state_records:
        raise CanaryError("rollout has no world_state baseline")
    payloads = [record.get("payload") for record in world_state_records]
    if any(not isinstance(payload, dict) for payload in payloads):
        raise CanaryError("every world_state payload must be an object")
    world_states = list(payloads)
    if any(
        not isinstance(payload.get("full"), bool)
        or not isinstance(payload.get("state"), dict)
        for payload in world_states
    ):
        raise CanaryError(
            "every world_state must have a boolean full flag and object state"
        )
    full_indices = [
        index
        for index, payload in enumerate(world_states)
        if payload["full"] is True
    ]
    if len(full_indices) != 1:
        raise CanaryError(
            "rollout must contain exactly one full world_state baseline"
        )
    if full_indices[0] != 0:
        raise CanaryError(
            "world_state full baseline must precede every delta"
        )
    return world_states


def _tool_call_tokens(source: str) -> list[tuple[int, int, str, bool]]:
    """Scan for every ``tools.<name>(`` token outside strings and comments.

    Returns ``(start, end, name, preceded_by_await)`` per token. Callers that
    only want frozen-route calls filter with :func:`_tool_call_markers`; the
    unfiltered list is what lets a rejection say whether it was one call, many
    calls, or a tool outside the route at all.
    """
    tokens: list[tuple[int, int, str, bool]] = []
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    slash_literal = False
    slash_character_class = False
    index = 0
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if character in "\r\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if character == "*" and following == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if slash_literal:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "[" and not slash_character_class:
                slash_character_class = True
            elif character == "]" and slash_character_class:
                slash_character_class = False
            elif character == "/" and not slash_character_class:
                slash_literal = False
            index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in {'"', "'", "`"}:
            quote = character
            index += 1
            continue
        if character == "/" and following == "/":
            line_comment = True
            index += 2
            continue
        if character == "/" and following == "*":
            block_comment = True
            index += 2
            continue
        if character == "/":
            slash_literal = True
            slash_character_class = False
            index += 1
            continue
        match = re.match(
            r"tools\.(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\(", source[index:]
        )
        cursor = index
        while cursor and source[cursor - 1].isspace():
            cursor -= 1
        token_end = cursor
        while cursor:
            previous = source[cursor - 1]
            if not (
                previous.isalnum()
                or previous in "_$\u200c\u200d"
                or ord(previous) > 127
            ):
                break
            cursor -= 1
        preceded_by_await = source[cursor:token_end] == "await"
        if match is not None:
            tokens.append(
                (
                    index,
                    index + match.end(),
                    match.group("name"),
                    preceded_by_await,
                )
            )
            index += match.end()
            continue
        index += 1
    return tokens


def _tool_call_markers(source: str) -> list[tuple[int, int, str]]:
    """Frozen-route tool calls only: an awaited shell_command or apply_patch."""
    return [
        (start, end, name)
        for start, end, name, awaited in _tool_call_tokens(source)
        if awaited and name in FROZEN_TOOL_FAMILIES
    ]


def _tool_call_argument(
    source: str,
    marker: tuple[int, int, str],
) -> tuple[str, int] | None:
    _, start, _ = marker
    if start > len(source):
        return None
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(source)):
        character = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'", "`"}:
            quote = character
        elif character in "[{(":
            depth += 1
        elif character in "]}":
            if depth == 0:
                return None
            depth -= 1
        elif character == ")":
            if depth == 0:
                return source[start:index], index + 1
            depth -= 1
    return None


def _top_level_object_fields(argument: str) -> list[str | None] | None:
    stripped = argument.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    body = stripped[1:-1]
    segments: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, character in enumerate(body):
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'", "`"}:
            quote = character
        elif character == "/":
            return None
        elif character in "[{(":
            depth += 1
        elif character in "]})":
            if depth == 0:
                return None
            depth -= 1
        elif character == "," and depth == 0:
            segments.append(body[start:index])
            start = index + 1
    if quote is not None or depth != 0:
        return None
    segments.append(body[start:])
    fields: list[str | None] = []
    for segment in segments:
        if not segment.strip():
            continue
        match = re.match(
            r'^\s*(?:(?P<identifier>[A-Za-z_$][A-Za-z0-9_$]*)|'
            r'(?P<quoted>"(?:\\.|[^"\\])*"))\s*:',
            segment,
        )
        if match is None:
            return None
        if match.group("identifier") is not None:
            fields.append(match.group("identifier"))
            continue
        try:
            decoded = json.loads(match.group("quoted"))
        except (json.JSONDecodeError, TypeError):
            fields.append(None)
        else:
            fields.append(decoded if isinstance(decoded, str) else None)
    return fields


def _wrapper_rejection_class(source: str) -> tuple[str, int, int]:
    """Classify why a tool input is not a frozen-route call.

    Returns the class plus the total ``tools.*`` token count and how many of
    those name a frozen-route family. Tool names outside the route are counted
    but never named: a corpus can carry private MCP tool names, and the class
    is what a reader needs.
    """
    tokens = _tool_call_tokens(source)
    frozen = sum(1 for token in tokens if token[2] in FROZEN_TOOL_FAMILIES)
    if not tokens:
        return "no_tool_call", 0, 0
    if len(tokens) > 1:
        return "multiple_calls", len(tokens), frozen
    if not frozen:
        return "out_of_route_tool", len(tokens), 0
    return "single_frozen_call", len(tokens), frozen


def _tool_input_wrapper_diagnostic(source: str) -> dict[str, Any]:
    rejection_class, token_count, frozen_token_count = (
        _wrapper_rejection_class(source)
    )
    markers = _tool_call_markers(source)
    tool_family = markers[0][2] if len(markers) == 1 else "other"
    argument_result = (
        _tool_call_argument(source, markers[0]) if len(markers) == 1 else None
    )
    marker_prefix = source[: markers[0][0]] if len(markers) == 1 else ""
    const_match = re.fullmatch(
        r"\s*const\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*await\s+",
        marker_prefix,
    )
    direct_match = re.fullmatch(
        r"\s*text\s*\(\s*await\s+",
        marker_prefix,
    )
    bound_match = re.fullmatch(
        r'\s*const\s+(?P<bound>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*'
        r'"(?:\\.|[^"\\])*"\s*;\s*text\s*\(\s*await\s+',
        marker_prefix,
    )
    suffix = source[argument_result[1] :] if argument_result is not None else ""
    const_variable_match = re.fullmatch(
        r"\s*const\s+(?P<result>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*await\s+",
        marker_prefix,
    )
    const_suffix_matches = bool(
        const_variable_match
        and re.fullmatch(
            rf"\s*;\s*text\s*\(\s*{re.escape(const_variable_match.group('result'))}"
            r"\s*\)\s*;?\s*",
            suffix,
        )
    )
    text_suffix_matches = bool(
        argument_result is not None
        and re.fullmatch(r"\s*\)\s*;?\s*", suffix)
    )
    if argument_result is not None and const_match and const_suffix_matches:
        envelope = "const_await_then_text"
    elif argument_result is not None and direct_match and text_suffix_matches:
        envelope = "direct_await_text"
    elif (
        argument_result is not None
        and bound_match
        and argument_result[0].strip() == bound_match.group("bound")
        and text_suffix_matches
    ):
        envelope = "bound_argument_then_direct_await_text"
    else:
        envelope = "other"
    argument = argument_result[0] if argument_result is not None else None
    if argument is None:
        argument_shape = "unparsed"
        fields = None
    else:
        stripped = argument.strip()
        fields = _top_level_object_fields(argument)
        if fields is not None:
            argument_shape = "object"
        elif stripped.startswith("{"):
            argument_shape = "unparsed"
        elif re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", stripped):
            argument_shape = "identifier"
        elif stripped.startswith(('"', "'", "`")):
            argument_shape = "string"
        else:
            argument_shape = "other"
    known_counts = {}
    if fields is not None:
        for name in SAFE_TOOL_INPUT_FIELD_NAMES:
            count = fields.count(name)
            if count:
                known_counts[name] = count
    unknown_count = (
        sum(name not in SAFE_TOOL_INPUT_FIELD_NAMES for name in fields)
        if fields is not None
        else 0
    )
    return {
        "argument_shape": argument_shape,
        "envelope": envelope,
        "field_name_census": {
            "known_field_counts": known_counts,
            "total_field_count": len(fields) if fields is not None else 0,
            "unknown_field_count": unknown_count,
        },
        "frozen_tool_call_token_count": frozen_token_count,
        "rejection_class": rejection_class,
        "tool_call_token_count": token_count,
        "tool_family": tool_family,
    }


CENSUS_STATUSES = (
    "not_attempted",
    "diagnostic_setup_failed",
    "sanitize_failed",
    "parse_attempted",
)


def _empty_rollout_diagnostics() -> dict[str, dict[str, Any]]:
    return {
        arm: {
            # Why a phase left blank by a failed build stayed blank. Without
            # this, "NOT_RUN" cannot distinguish a phase the diagnostic pass
            # never reached from one where the pass itself broke.
            "census_status": {
                "public": "not_attempted",
                "source": "not_attempted",
            },
            "parse_phases": {
                "public": "NOT_RUN",
                "source": "NOT_RUN",
            },
            "public_census": None,
            # True when the public phase was censused from a locally sanitized
            # copy after the build had already failed, rather than from the
            # staged artifact admission would have read.
            "public_phase_from_diagnostic_copy": False,
            "source_census": None,
            "wrapper_mismatch_counts": {
                "public": 0,
                "source": 0,
            },
            "wrapper_mismatches": {
                "public": [],
                "source": [],
            },
        }
        for arm in ("A", "B")
    }


def _failure_rollout_diagnostics(
    diagnostics: object,
) -> dict[str, dict[str, Any]]:
    source = diagnostics if isinstance(diagnostics, dict) else {}
    projected = _empty_rollout_diagnostics()
    for arm in ("A", "B"):
        observed = source.get(arm)
        if not isinstance(observed, dict):
            continue
        phases = observed.get("parse_phases")
        if isinstance(phases, dict):
            for phase in ("source", "public"):
                status = phases.get(phase)
                if status in {"NOT_RUN", "PASS", "FAIL"}:
                    projected[arm]["parse_phases"][phase] = status
        for phase in ("source", "public"):
            census = observed.get(f"{phase}_census")
            if not isinstance(census, dict):
                continue
            values = {
                field: census.get(field)
                for field in (
                    "full_true_count",
                    "object_payload_count",
                    "raw_count",
                    "state_object_count",
                )
            }
            if all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
                for value in values.values()
            ):
                projected[arm][f"{phase}_census"] = values
        if observed.get("public_phase_from_diagnostic_copy") is True:
            projected[arm]["public_phase_from_diagnostic_copy"] = True
        statuses = observed.get("census_status")
        if isinstance(statuses, dict):
            for phase in ("source", "public"):
                status = statuses.get(phase)
                if status in CENSUS_STATUSES:
                    projected[arm]["census_status"][phase] = status
        counts = observed.get("wrapper_mismatch_counts")
        if isinstance(counts, dict):
            for phase in ("source", "public"):
                count = counts.get(phase)
                if (
                    isinstance(count, int)
                    and not isinstance(count, bool)
                    and count >= 0
                ):
                    projected[arm]["wrapper_mismatch_counts"][phase] = count
        mismatches = observed.get("wrapper_mismatches")
        if not isinstance(mismatches, dict):
            continue
        for phase in ("source", "public"):
            entries = mismatches.get(phase)
            if not isinstance(entries, list):
                continue
            for entry in entries[:WRAPPER_MISMATCH_RETENTION_LIMIT]:
                if not isinstance(entry, dict):
                    continue
                ordinal = entry.get("tool_call_ordinal")
                tool_family = entry.get("tool_family")
                envelope = entry.get("envelope")
                argument_shape = entry.get("argument_shape")
                census = entry.get("field_name_census")
                rejection_class = entry.get("rejection_class")
                token_count = entry.get("tool_call_token_count")
                frozen_token_count = entry.get("frozen_tool_call_token_count")
                contract_reason = entry.get("contract_reason")
                if (
                    contract_reason not in contract.REFUSAL_REASONS
                    or rejection_class not in WRAPPER_REJECTION_CLASSES
                    or not isinstance(token_count, int)
                    or isinstance(token_count, bool)
                    or token_count < 0
                    or not isinstance(frozen_token_count, int)
                    or isinstance(frozen_token_count, bool)
                    or frozen_token_count < 0
                    or frozen_token_count > token_count
                ):
                    continue
                if (
                    not isinstance(ordinal, int)
                    or isinstance(ordinal, bool)
                    or ordinal < 1
                    or tool_family
                    not in {"shell_command", "apply_patch", "other"}
                    or envelope
                    not in {
                        "const_await_then_text",
                        "direct_await_text",
                        "bound_argument_then_direct_await_text",
                        "other",
                    }
                    or argument_shape
                    not in {"object", "identifier", "string", "other", "unparsed"}
                    or not isinstance(census, dict)
                ):
                    continue
                known = census.get("known_field_counts")
                total = census.get("total_field_count")
                unknown = census.get("unknown_field_count")
                if not isinstance(known, dict) or not all(
                    name in SAFE_TOOL_INPUT_FIELD_NAMES
                    and isinstance(count, int)
                    and not isinstance(count, bool)
                    and count > 0
                    for name, count in known.items()
                ):
                    continue
                if (
                    not isinstance(total, int)
                    or isinstance(total, bool)
                    or not isinstance(unknown, int)
                    or isinstance(unknown, bool)
                    or unknown < 0
                    or total != sum(known.values()) + unknown
                ):
                    continue
                projected[arm]["wrapper_mismatches"][phase].append(
                    {
                        "argument_shape": argument_shape,
                        "contract_reason": contract_reason,
                        "envelope": envelope,
                        "field_name_census": {
                            "known_field_counts": {
                                name: known[name] for name in sorted(known)
                            },
                            "total_field_count": total,
                            "unknown_field_count": unknown,
                        },
                        "frozen_tool_call_token_count": frozen_token_count,
                        "rejection_class": rejection_class,
                        "tool_call_ordinal": ordinal,
                        "tool_call_token_count": token_count,
                        "tool_family": tool_family,
                    }
                )
    return projected


def _write_json(path: Path, value: object) -> None:
    chain._atomic_write(path, _json_bytes(value))


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=process_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CanaryError(
            f"command failed ({completed.returncode}): "
            f"{' '.join(command)}: {detail}"
        )
    return completed


def _git(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> bytes:
    return _run(
        ["git", "-c", f"safe.directory={repo.resolve().as_posix()}", *args],
        cwd=repo,
        env=env,
    ).stdout


def _expanded_git_identity(identity: dict[str, str]) -> dict[str, str]:
    return {
        "author_email": identity["email"],
        "author_name": identity["name"],
        "committer_email": identity["email"],
        "committer_name": identity["name"],
    }


def _commit_identity(repo: Path, commit: str) -> dict[str, str]:
    raw = _git(
        repo,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%cn%x00%ce%x00",
        commit,
    )
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith(b"\n"):
        raw = raw[:-1]
    parts = raw.split(b"\0")
    if len(parts) != 5 or parts[-1] != b"":
        raise CanaryError("commit identity metadata is malformed")
    try:
        values = [part.decode("utf-8", errors="strict") for part in parts[:4]]
    except UnicodeDecodeError as exc:
        raise CanaryError("commit identity metadata is not UTF-8") from exc
    return dict(
        zip(
            (
                "author_name",
                "author_email",
                "committer_name",
                "committer_email",
            ),
            values,
            strict=True,
        )
    )


def _assert_commit_identity(
    repo: Path,
    commit: str,
    expected: dict[str, str],
) -> dict[str, str]:
    actual = _commit_identity(repo, commit)
    expanded = _expanded_git_identity(expected)
    if actual != expanded:
        raise CanaryError(
            "commit identity is outside frozen synthetic allowlist"
        )
    return expanded


def _verify_bundle_commit_identities(
    bundle: Path,
    *,
    baseline_commit: str,
    output_commit: str,
    producer_identity: dict[str, str],
) -> dict[str, dict[str, str]]:
    with tempfile.TemporaryDirectory(
        prefix="gate3-live-bundle-identity-"
    ) as temp:
        temp_root = Path(temp)
        repo = temp_root / "repo"
        _run(
            ["git", "clone", "--quiet", str(bundle.resolve()), str(repo)],
            cwd=temp_root,
        )
        head = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
        output_graph = (
            _git(repo, "rev-list", "--parents", "-n", "1", output_commit)
            .decode("ascii")
            .strip()
            .split()
        )
        baseline_graph = (
            _git(repo, "rev-list", "--parents", "-n", "1", baseline_commit)
            .decode("ascii")
            .strip()
            .split()
        )
        reachable = {
            value
            for value in _git(repo, "rev-list", "--all")
            .decode("ascii")
            .splitlines()
            if value
        }
        if (
            head != output_commit
            or output_graph != [output_commit, baseline_commit]
            or baseline_graph != [baseline_commit]
            or reachable != {baseline_commit, output_commit}
        ):
            raise CanaryError("bundle commit graph differs from frozen route")
        return {
            "baseline": _assert_commit_identity(
                repo, baseline_commit, BASELINE_GIT_IDENTITY
            ),
            "output": _assert_commit_identity(
                repo, output_commit, producer_identity
            ),
        }


def _implementation_identity(
    repo_root: Path,
    *,
    commit: str | None = None,
    require_clean: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if require_clean and _git(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ):
        raise CanaryError("implementation repository is not clean")
    resolved_commit = (
        commit
        or _git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    )
    if not isinstance(resolved_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", resolved_commit
    ):
        raise CanaryError("implementation commit identity is invalid")
    paths = (
        Path(__file__).resolve(),
        DEFAULT_PAIR_RUNNER,
        DEFAULT_SESSION_LAUNCHER,
        DEFAULT_TESTS,
    )
    files: dict[str, str] = {}
    for path in paths:
        relative = path.resolve().relative_to(repo_root).as_posix()
        committed = _git(repo_root, "show", f"{resolved_commit}:{relative}")
        current = path.read_bytes()
        if committed != current:
            raise CanaryError(
                f"implementation path differs from commit {resolved_commit}: "
                f"{relative}"
            )
        files[relative] = _sha256_bytes(committed)
    return {
        "commit": resolved_commit,
        "files": files,
    }


@contextmanager
def _git_safe_directories(repos: list[Path]):
    keys = ["GIT_CONFIG_COUNT"]
    prior_count = os.environ.get("GIT_CONFIG_COUNT")
    try:
        base = int(prior_count or "0")
    except ValueError as exc:
        raise CanaryError("GIT_CONFIG_COUNT is not an integer") from exc
    for offset, repo in enumerate(repos):
        index = base + offset
        keys.extend(
            [f"GIT_CONFIG_KEY_{index}", f"GIT_CONFIG_VALUE_{index}"]
        )
    prior = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["GIT_CONFIG_COUNT"] = str(base + len(repos))
        for offset, repo in enumerate(repos):
            index = base + offset
            os.environ[f"GIT_CONFIG_KEY_{index}"] = "safe.directory"
            os.environ[f"GIT_CONFIG_VALUE_{index}"] = (
                repo.resolve().as_posix()
            )
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise CanaryError(f"artifact escapes evidence root: {path}") from exc


def _source(relative: object, root: Path) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CanaryError("artifact path is absent")
    path = root.joinpath(*Path(relative).parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise CanaryError("artifact path escapes evidence root") from exc
    if not path.is_file():
        raise CanaryError(f"artifact is missing: {relative}")
    return path


def _retain(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root.joinpath(*relative.split("/"))
    chain._atomic_write(path, payload)
    return {"path": _relative(path, root), "sha256": _sha256_bytes(payload)}


def _artifact_entry(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "path": _relative(path, root),
        "sha256": _sha256_bytes(raw),
    }


def _inventory(root: Path) -> list[dict[str, Any]]:
    summary = root / "canary-summary.json"
    paths = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != summary
    ]
    if any(path.is_symlink() for path in paths):
        raise CanaryError("evidence inventory may not contain symlinks")
    return [_artifact_entry(path, root) for path in paths]


def _create_baseline_repo(work_root: Path) -> tuple[Path, str]:
    repo = work_root / "base"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "user.email", BASELINE_GIT_IDENTITY["email"])
    _git(repo, "config", "user.name", BASELINE_GIT_IDENTITY["name"])
    (repo / "calc.py").write_bytes(b"def add(a, b):\n    return a - b\n")
    (repo / "test_calc.py").write_bytes(
        b"import unittest\n"
        b"from calc import add\n\n"
        b"class CalcTests(unittest.TestCase):\n"
        b"    def test_add(self):\n"
        b"        self.assertEqual(add(2, 3), 5)\n\n"
        b"if __name__ == '__main__':\n"
        b"    unittest.main()\n"
    )
    _git(repo, "add", "calc.py", "test_calc.py")
    _git(repo, "commit", "-q", "-m", "live canary baseline", env=COMMIT_ENV)
    return repo, _git(repo, "rev-parse", "HEAD").decode("ascii").strip()


def _prompt(
    *,
    treatment: str,
    baseline_commit: str,
    skill_packet: bytes,
) -> bytes:
    treatment_text = (
        NO_SKILL_PACKET.decode("utf-8")
        if treatment == "A"
        else skill_packet.decode("utf-8")
    )
    text = f"""This is a non-counted Gate 3 producer-route canary. It is not a formal Gate 3 run and must not be represented as one.

Work only in this fresh context. Do not delegate or create sub-agents. Do not use web search, network access, MCP tools, or read any path outside this workspace.

Tool-shape constraints:
- The current workspace is already a fresh isolated repository at the supplied baseline commit. Do not create a nested work directory or reinitialize git.
- Use `apply_patch` for every file creation or edit.
- Run every git or test command as its own simple tool call.
- Do not use inline PowerShell scripts, `New-Item`, `WriteAllText`, `Set-Content`, command chaining, or shell redirection.
- A semicolon, `&&`, `||`, pipe, or redirection in any shell command makes this canary invalid. In particular, run `git add calc.py` and `git commit -m "..."` as two separate tool calls.
- Shell commands are limited to these exact forms: `git rev-parse HEAD`, `git rev-parse HEAD^`, `git rev-list --parents -n 1 HEAD`, `git status --porcelain=v1 --untracked-files=all`, `git diff --check`, `git diff -- calc.py`, `git diff -- calc.py test_calc.py`, `git add calc.py`, `git commit -m "MESSAGE"`, `python -B test_calc.py`, `Get-ChildItem -Force`, `Get-Content calc.py`, `Get-Content test_calc.py`, and `rg --files`.
- Do not use `..`, environment-variable paths, `git -C`, network Git commands, global Git configuration, destructive Git commands, or any other Python command.

Before editing:
1. Confirm `git rev-parse HEAD` is exactly `{baseline_commit}`.
2. Confirm `git status --porcelain=v1 --untracked-files=all` is empty.
If either check differs, stop without editing.

Task:
Repair add() and preserve the regression test. The baseline test is `python -B test_calc.py` and must fail before the fix and pass after the fix.

Treatment packet:
{treatment_text.rstrip()}

Completion requirements:
- Make the minimal task change.
- Run the baseline test before editing and again after the fix.
- Commit the completed change as exactly one child commit of the supplied baseline.
- Leave the work repository clean with no untracked files.
- In the final response, report the baseline commit, output commit, exact test command, exit code, and whether the worktree is clean.
"""
    return text.encode("utf-8")


def _validate_candidate(repo_root: Path) -> int:
    manifest = repo_root / DEFAULT_CANDIDATE_MANIFEST.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    if _sha256_file(manifest) != EXPECTED_CANDIDATE_MANIFEST_SHA256:
        raise CanaryError("candidate manifest is not the merged reviewed identity")
    result = chain.verify_candidate(repo_root, manifest)
    if result["status"] != "PASS":
        raise CanaryError("candidate verification did not pass")
    return len(result["checks"])


def prepare(
    repo_root: Path,
    staging_root: Path,
    *,
    run_id: str,
    model: str,
    comp_hash: str,
    cli_version: str,
    reasoning: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    staging_root = staging_root.resolve()
    if (
        model,
        comp_hash,
        cli_version,
        reasoning,
    ) != (
        DEFAULT_MODEL,
        DEFAULT_COMP_HASH,
        DEFAULT_CLI_VERSION,
        DEFAULT_REASONING,
    ):
        raise CanaryError("prepare arguments differ from the frozen Codex route")
    if staging_root.exists():
        raise CanaryError(f"staging root already exists: {staging_root}")
    candidate_checks = _validate_candidate(repo_root)
    implementation = _implementation_identity(repo_root, require_clean=True)
    staging_root.mkdir(parents=True)
    try:
        with tempfile.TemporaryDirectory(prefix="gate3-live-baseline-") as temp:
            base_repo, baseline_commit = _create_baseline_repo(Path(temp))
            bundle = staging_root / "inputs" / "baseline.bundle"
            bundle.parent.mkdir(parents=True)
            _git(base_repo, "bundle", "create", str(bundle), "--all")
        skill_packet = (
            repo_root
            / DEFAULT_SKILL_PACKET.relative_to(EXPERIMENT_ROOT.parents[2])
        ).read_bytes()
        common = {
            "baseline_instruction_sha256": _retain(
                staging_root,
                "inputs/baseline-instruction.txt",
                BASELINE_INSTRUCTION,
            ),
            "task_packet_sha256": _retain(
                staging_root, "inputs/task-packet.txt", TASK_PACKET
            ),
            "permissions_sha256": _retain(
                staging_root, "inputs/permissions.json", PERMISSIONS
            ),
            "budget_sha256": _retain(
                staging_root, "inputs/budget.json", BUDGET
            ),
            "harness_contract_sha256": _retain(
                staging_root,
                "inputs/gate3-harness-contract-v1.json",
                (
                    repo_root
                    / DEFAULT_HARNESS_CONTRACT.relative_to(
                        EXPERIMENT_ROOT.parents[2]
                    )
                ).read_bytes(),
            ),
            "scorer_rubric_sha256": _retain(
                staging_root, "inputs/scorer-rubric.txt", SCORER_RUBRIC
            ),
        }
        treatment_inputs: dict[str, dict[str, dict[str, str]]] = {}
        for treatment in ("A", "B"):
            lower = treatment.lower()
            treatment_inputs[treatment] = {
                "treatment_packet_sha256": _retain(
                    staging_root,
                    f"inputs/treatment-{lower}.txt",
                    NO_SKILL_PACKET if treatment == "A" else skill_packet,
                ),
                "governance_instruction_sha256": _retain(
                    staging_root,
                    f"inputs/governance-{lower}.txt",
                    NO_GOVERNANCE_PACKET,
                ),
                "validator_bundle_sha256": _retain(
                    staging_root,
                    f"inputs/validator-{lower}.py",
                    VALIDATOR_BUNDLE,
                ),
                "validator_config_sha256": _retain(
                    staging_root,
                    f"inputs/validator-{lower}.json",
                    VALIDATOR_CONFIG,
                ),
            }
            prompt = _prompt(
                treatment=treatment,
                baseline_commit=baseline_commit,
                skill_packet=skill_packet,
            )
            _retain(
                staging_root,
                f"inputs/producer-prompt-{lower}.txt",
                prompt,
            )
        plan = {
            "authorization": AUTHORIZATION,
            "baseline_bundle_sha256": _sha256_file(bundle),
            "baseline_commit": baseline_commit,
            "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
            "candidate_verification_checks": candidate_checks,
            "common_inputs": common,
            "credential_contract": CREDENTIAL_CONTRACT,
            "context_contract": {
                "current_date": datetime.now().date().isoformat(),
                "meta": CONTEXT_META_EXPECTED,
                "provider": DEFAULT_PROVIDER,
                "public_context_tokens": PUBLIC_CONTEXT_TOKENS,
                "turn": CONTEXT_TURN_EXPECTED,
            },
            "frozen_route": {
                "cli_version": cli_version,
                "comp_hash": comp_hash,
                "launcher_implementation_sha256": _sha256_file(
                    DEFAULT_SESSION_LAUNCHER
                ),
                "pair_runner_implementation_sha256": _sha256_file(
                    DEFAULT_PAIR_RUNNER
                ),
                "model": model,
                "model_build": (
                    f"codex:{model}:comp_hash={comp_hash}:cli={cli_version}"
                ),
                "producer_git_identity": PRODUCER_GIT_IDENTITY,
                "reasoning": reasoning,
            },
            "implementation": implementation,
            "privacy": {
                "public_evidence_only": True,
                "raw_evidence_retained_in_git": False,
                "sanitizer_rules_sha256": _sanitizer_rules_sha256(),
                "sanitizer_schema": SANITIZER_SCHEMA,
            },
            "prompts": {
                treatment: {
                    "path": f"inputs/producer-prompt-{treatment.lower()}.txt",
                    "sha256": _sha256_file(
                        staging_root
                        / "inputs"
                        / f"producer-prompt-{treatment.lower()}.txt"
                    ),
                }
                for treatment in ("A", "B")
            },
            "rehearsal_kind": REHEARSAL_KIND,
            "run_id": run_id,
            "schema": ROUTE_PLAN_SCHEMA,
            "treatment_inputs": treatment_inputs,
        }
        _write_json(staging_root / "route-plan.json", plan)
        return plan
    except BaseException:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise


def _message_text(payload: dict[str, Any]) -> str | None:
    if payload.get("type") != "message" or payload.get("role") != "user":
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"input_text", "text"}:
            value = item.get("text")
            if isinstance(value, str):
                parts.append(value)
    return "".join(parts) if parts else None


def _extract_machine_context(text: str) -> dict[str, Any] | None:
    matches = re.findall(
        r"<environment_context>.*?</environment_context>",
        text,
        flags=re.DOTALL,
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise CanaryError("machine context envelope count is invalid")
    try:
        root = ET.fromstring(matches[0])
    except ET.ParseError as exc:
        raise CanaryError("machine context envelope is invalid XML") from exc
    workspace_roots = [
        item.text or ""
        for item in root.findall("./filesystem/workspace_roots/root")
    ]
    permission = root.find("./filesystem/permission_profile")
    file_system = (
        permission.find("./file_system") if permission is not None else None
    )
    return {
        "current_date": root.findtext("current_date"),
        "cwd": root.findtext("cwd"),
        "file_system_type": (
            file_system.attrib.get("type") if file_system is not None else None
        ),
        "permission_profile_type": (
            permission.attrib.get("type") if permission is not None else None
        ),
        "shell": root.findtext("shell"),
        "timezone": root.findtext("timezone"),
        "workspace_roots": workspace_roots,
    }


def _normalised_context_view(
    value: Any,
    *,
    expected_workspace: str,
) -> Any:
    return _map_strings(
        value,
        lambda text: _replace_workspace_text(
            text, expected_workspace, GENERIC_CONTEXT_TOKEN
        ),
    )


def _instruction_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        raise CanaryError("instruction message content is invalid")
    parts = [
        str(item.get("text"))
        for item in content
        if isinstance(item, dict)
        and item.get("type") in {"input_text", "text"}
        and isinstance(item.get("text"), str)
    ]
    if not parts:
        raise CanaryError("instruction message has no text")
    return "".join(parts)


def _decode_js_string(value: str, *, label: str) -> str:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise CanaryError(f"{label} is not a JSON string") from exc
    if not isinstance(decoded, str):
        raise CanaryError(f"{label} is not text")
    return decoded


def _validate_shell_command(
    command: str,
    *,
    workdir: str,
    expected_workspace: str,
) -> dict[str, Any]:
    if not _same_path(workdir, expected_workspace):
        raise CanaryError("tool workdir differs from frozen workspace")
    if command != command.strip():
        raise CanaryError("shell command is not in canonical form")
    if SHELL_META_RE.search(command):
        raise CanaryError("shell command violates the simple-command contract")
    matched_rule = next(
        (
            rule_name
            for rule_name, pattern in COMMAND_RULES
            if pattern.fullmatch(command)
        ),
        None,
    )
    if matched_rule is None:
        raise CanaryError(
            "shell command differs from every frozen per-command grammar"
        )
    return {
        "command": command,
        "kind": "shell_command",
        "rule": matched_rule,
        "workdir": workdir,
    }


def _patch_target_is_allowed(target: str, expected_workspace: str) -> bool:
    collapsed = re.sub(r"\\+", r"\\", target.strip())
    candidate_text = _path_text(collapsed)
    workspace_text = _path_text(expected_workspace)
    workspace_prefix = workspace_text + "\\"
    if candidate_text.startswith(workspace_prefix):
        candidate_text = candidate_text[len(workspace_prefix) :]
    elif Path(collapsed).is_absolute():
        return False
    return candidate_text in {"calc.py", "test_calc.py"}


def _validate_patch(patch: str, *, expected_workspace: str) -> dict[str, Any]:
    targets = [
        match.group(1)
        for match in re.finditer(
            r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$",
            patch,
            flags=re.MULTILINE,
        )
    ]
    if not targets or not all(
        _patch_target_is_allowed(target, expected_workspace)
        for target in targets
    ):
        raise CanaryError("apply_patch target escapes the frozen task scope")
    return {
        "kind": "apply_patch",
        "patch_sha256": _sha256_bytes(patch.encode("utf-8")),
        "targets": targets,
    }


def _parse_tool_call(
    payload: dict[str, Any],
    *,
    expected_workspace: str,
    mismatch_diagnostic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if payload.get("type") != "custom_tool_call" or payload.get("name") != "exec":
        raise CanaryError("rollout used a tool outside the frozen route")
    source = payload.get("input")
    if not isinstance(source, str):
        raise CanaryError("tool input is absent")
    # Acceptance is the semantic-equivalence contract, not the byte-exact
    # regexes. The regexes stay as the definition of the frozen shape, and a
    # test asserts the contract accepts everything they accept, so this is a
    # widening that cannot narrow what was already admitted.
    verdict = contract.evaluate(source, expected_workspace=expected_workspace)
    if verdict["accepted"]:
        detail = verdict["detail"]
    elif verdict["reason"] == "value_rejected_by_route":
        # The wrapper was fine and the route refused what it carried. Raise the
        # route's own message: a command reaching outside the workspace is a
        # different finding from a wrapper this route does not recognize, and
        # collapsing them would hide the more serious one.
        raise CanaryError(verdict["detail"])
    else:
        if mismatch_diagnostic is not None:
            mismatch_diagnostic.update(_tool_input_wrapper_diagnostic(source))
            # The contract's reason says which rule refused, which the
            # structural classification alone cannot: an extra field and a
            # privilege-affecting field look identical without it.
            mismatch_diagnostic["contract_reason"] = verdict["reason"]
        raise CanaryError("tool input wrapper differs from the frozen route")
    return {
        "call_id": payload.get("call_id"),
        "input_sha256": _sha256_bytes(source.encode("utf-8")),
        "name": payload.get("name"),
        "type": payload.get("type"),
        **detail,
    }


def parse_rollout(
    path: Path | None,
    *,
    source_bytes: bytes | None = None,
    expected_prompt: bytes,
    expected_model: str,
    expected_comp_hash: str,
    expected_cli_version: str,
    expected_reasoning: str,
    expected_workspace: str,
    expected_context_contract: dict[str, Any],
    rollout_diagnostic: dict[str, Any] | None = None,
    parse_phase: str | None = None,
) -> dict[str, Any]:
    if rollout_diagnostic is not None:
        if parse_phase not in {"source", "public"}:
            raise CanaryError("rollout diagnostic parse phase is invalid")
        rollout_diagnostic["parse_phases"][parse_phase] = "FAIL"
    # source_bytes lets a caller parse a rollout it holds in memory. The
    # diagnostic census of the public phase uses it so a sanitized copy of
    # private material never touches the filesystem.
    if source_bytes is None:
        if path is None:
            raise CanaryError("rollout has no source")
        raw = path.read_bytes()
    else:
        raw = source_bytes
    records = _load_jsonl(path, label="rollout", raw=source_bytes)
    if rollout_diagnostic is not None:
        rollout_diagnostic[f"{parse_phase}_census"] = _world_state_census(
            records
        )
    metas = [item["payload"] for item in records if item.get("type") == "session_meta"]
    if not metas:
        raise CanaryError("rollout has no session_meta")
    session_ids = {
        str(meta.get("id") or meta.get("session_id") or "") for meta in metas
    }
    if len(session_ids) != 1 or "" in session_ids:
        raise CanaryError("rollout session identity is absent or inconsistent")
    cli_versions = {str(meta.get("cli_version", "")) for meta in metas}
    if cli_versions != {expected_cli_version}:
        raise CanaryError(
            f"rollout CLI build mismatch: {sorted(cli_versions)}"
        )
    providers = {str(meta.get("model_provider", "")) for meta in metas}
    if providers != {expected_context_contract["provider"]}:
        raise CanaryError("rollout model provider differs from frozen context")
    for meta in metas:
        for field, expected in expected_context_contract["meta"].items():
            if meta.get(field) != expected:
                raise CanaryError(
                    f"session context field {field} differs from frozen context"
                )
        if not _same_path(meta.get("cwd"), expected_workspace):
            raise CanaryError("session_meta cwd differs from frozen workspace")
    contexts = [
        item["payload"] for item in records if item.get("type") == "turn_context"
    ]
    if not contexts:
        raise CanaryError("rollout has no turn_context")
    for context in contexts:
        if context.get("model") != expected_model:
            raise CanaryError(
                f"rollout model mismatch: {context.get('model')!r}"
            )
        if str(context.get("comp_hash")) != expected_comp_hash:
            raise CanaryError(
                f"rollout component hash mismatch: {context.get('comp_hash')!r}"
            )
        if context.get("effort") != expected_reasoning:
            raise CanaryError(
                f"rollout reasoning mismatch: {context.get('effort')!r}"
            )
        if not _same_path(context.get("cwd"), expected_workspace):
            raise CanaryError("turn_context cwd differs from frozen workspace")
        roots = context.get("workspace_roots")
        if (
            not isinstance(roots, list)
            or len(roots) != 1
            or not _same_path(roots[0], expected_workspace)
        ):
            raise CanaryError(
                "turn_context workspace roots differ from frozen workspace"
            )
        for field, expected in expected_context_contract["turn"].items():
            if context.get(field) != expected:
                raise CanaryError(
                    f"turn context field {field} differs from frozen context"
                )
        if context.get("current_date") != expected_context_contract["current_date"]:
            raise CanaryError("turn context date differs from frozen context")
        collaboration = context.get("collaboration_mode")
        expected_collaboration = {
            "mode": "default",
            "settings": {
                "developer_instructions": None,
                "model": expected_model,
                "reasoning_effort": expected_reasoning,
            },
        }
        if collaboration != expected_collaboration:
            raise CanaryError("collaboration context differs from frozen context")
    user_messages = [
        text
        for item in records
        if item.get("type") == "response_item"
        and isinstance(item.get("payload"), dict)
        for text in [_message_text(item["payload"])]
        if text is not None
    ]
    prompt_matches = [
        text for text in user_messages if text.encode("utf-8") == expected_prompt
    ]
    machine_contexts = [
        (text, _extract_machine_context(text))
        for text in user_messages
        if _extract_machine_context(text) is not None
    ]
    unmatched = [
        text
        for text in user_messages
        if text.encode("utf-8") != expected_prompt
        and _extract_machine_context(text) is None
    ]
    if (
        len(prompt_matches) != 1
        or len(machine_contexts) != 1
        or unmatched
        or len(user_messages) != len(prompt_matches) + len(machine_contexts)
    ):
        raise CanaryError(
            "fresh context requires one exact task prompt and exactly one "
            "machine context envelope"
        )
    machine = machine_contexts[0][1]
    if not isinstance(machine, dict):
        raise CanaryError("machine context is absent")
    if (
        not _same_path(machine.get("cwd"), expected_workspace)
        or machine.get("workspace_roots") is None
        or len(machine["workspace_roots"]) != 1
        or not _same_path(machine["workspace_roots"][0], expected_workspace)
        or machine.get("current_date") != expected_context_contract["current_date"]
        or machine.get("timezone") != DEFAULT_TIMEZONE
        or machine.get("shell") != "powershell"
        or machine.get("permission_profile_type") != "disabled"
        or machine.get("file_system_type") != "unrestricted"
    ):
        raise CanaryError("machine context differs from frozen context")
    expected_prompt_text = expected_prompt.decode("utf-8")
    event_user_messages = [
        item.get("payload", {}).get("message")
        for item in records
        if item.get("type") == "event_msg"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("type") == "user_message"
    ]
    if event_user_messages != [expected_prompt_text]:
        raise CanaryError("event user message differs from exact task prompt")
    received_prompt = prompt_matches[0].encode("utf-8")
    developer_texts = [
        _instruction_text(item["payload"])
        for item in records
        if item.get("type") == "response_item"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("type") == "message"
        and item["payload"].get("role") == "developer"
    ]
    if not developer_texts:
        raise CanaryError("rollout has no developer instructions")
    base_instructions = [meta.get("base_instructions") for meta in metas]
    if any(value is None for value in base_instructions):
        raise CanaryError("rollout has no base instructions")
    world_states = _validated_world_states(records)
    calls: list[dict[str, Any]] = []
    tool_call_ordinal = 0
    first_tool_call_error: CanaryError | None = None
    for item in records:
        if item.get("type") != "response_item":
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "tool_search_call":
            raise CanaryError("rollout used tool search despite the frozen route")
        if payload.get("type") in {"custom_tool_call", "function_call"}:
            tool_call_ordinal += 1
            mismatch_diagnostic: dict[str, Any] = {}
            try:
                parsed_call = _parse_tool_call(
                    payload,
                    expected_workspace=expected_workspace,
                    mismatch_diagnostic=mismatch_diagnostic,
                )
            except CanaryError as error:
                # Keep scanning so one authorized pair censuses every rejected
                # wrapper instead of only the first. The original error is
                # re-raised below, so admission is unchanged.
                if mismatch_diagnostic and rollout_diagnostic is not None:
                    counts = rollout_diagnostic["wrapper_mismatch_counts"]
                    counts[parse_phase] += 1
                    retained = rollout_diagnostic["wrapper_mismatches"][parse_phase]
                    if len(retained) < WRAPPER_MISMATCH_RETENTION_LIMIT:
                        retained.append(
                            {
                                **mismatch_diagnostic,
                                "tool_call_ordinal": tool_call_ordinal,
                            }
                        )
                if first_tool_call_error is None:
                    first_tool_call_error = error
                continue
            calls.append(parsed_call)
    if first_tool_call_error is not None:
        raise first_tool_call_error
    timestamps = [
        item.get("timestamp")
        for item in records
        if isinstance(item.get("timestamp"), str)
    ]
    if not timestamps:
        raise CanaryError("rollout has no timestamps")
    context_identity = {
        # What the route was willing to admit is part of what identifies the
        # context. A rollout judged under a different acceptance policy is not
        # the same observation, and this makes that difference visible in the
        # identity digest rather than only in a side field.
        "acceptance_policy": contract.policy(),
        "base_instructions": _normalised_context_view(
            base_instructions, expected_workspace=expected_workspace
        ),
        "developer_instructions": _normalised_context_view(
            developer_texts, expected_workspace=expected_workspace
        ),
        "machine_context": _normalised_context_view(
            machine, expected_workspace=expected_workspace
        ),
        "session_meta": [
            _normalised_context_view(
                {
                    "cli_version": meta.get("cli_version"),
                    "cwd": meta.get("cwd"),
                    **{
                        field: meta.get(field)
                        for field in expected_context_contract["meta"]
                    },
                },
                expected_workspace=expected_workspace,
            )
            for meta in metas
        ],
        "turn_context": [
            _normalised_context_view(
                {
                    field: context.get(field)
                    for field in (
                        "approval_policy",
                        "approvals_reviewer",
                        "collaboration_mode",
                        "comp_hash",
                        "current_date",
                        "cwd",
                        "effort",
                        "model",
                        "multi_agent_version",
                        "permission_profile",
                        "personality",
                        "realtime_active",
                        "sandbox_policy",
                        "summary",
                        "timezone",
                        "workspace_roots",
                    )
                },
                expected_workspace=expected_workspace,
            )
            for context in contexts
        ],
        "world_state": _normalised_context_view(
            world_states, expected_workspace=expected_workspace
        ),
    }
    result = {
        "base_instructions_sha256": _sha256_bytes(
            _json_bytes(context_identity["base_instructions"])
        ),
        "cli_version": expected_cli_version,
        "comp_hash": expected_comp_hash,
        "acceptance_policy_sha256": contract.policy_digest(),
        "context_identity_sha256": _sha256_bytes(_json_bytes(context_identity)),
        "developer_instructions_sha256": _sha256_bytes(
            _json_bytes(context_identity["developer_instructions"])
        ),
        "finished_at": timestamps[-1],
        "history_modes": sorted(
            {json.dumps(meta.get("history_mode"), sort_keys=True) for meta in metas}
        ),
        "model": expected_model,
        "machine_context_count": len(machine_contexts),
        "model_provider": next(iter(providers)),
        "permission_fingerprint": {
            field: contexts[0].get(field)
            for field in (
                "approval_policy",
                "approvals_reviewer",
                "permission_profile",
                "sandbox_policy",
            )
        },
        "prompt_bytes": len(received_prompt),
        "prompt_sha256": _sha256_bytes(received_prompt),
        "reasoning": expected_reasoning,
        "rollout_bytes": len(raw),
        "rollout_sha256": _sha256_bytes(raw),
        "session_id": next(iter(session_ids)),
        "started_at": timestamps[0],
        "tool_calls": len(calls),
        "tool_inventory": calls,
        "turn_count": len(contexts),
        "user_message_count": len(user_messages),
    }
    if rollout_diagnostic is not None:
        rollout_diagnostic["parse_phases"][parse_phase] = "PASS"
    return result


def parse_exec_events(path: Path, *, expected_session_id: str) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise CanaryError(
            "exec event stream must be non-empty newline-terminated JSONL"
        )
    records: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CanaryError(f"exec event line {index} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise CanaryError(f"exec event line {index} is not an object")
        records.append(value)
    started = [
        record
        for record in records
        if record.get("type") == "thread.started"
    ]
    if len(started) != 1:
        raise CanaryError("exec event stream must contain one thread.started")
    thread_id = str(started[0].get("thread_id", ""))
    if not thread_id or thread_id != expected_session_id:
        raise CanaryError("exec thread id differs from saved rollout session id")
    if any(
        record.get("type") in {"error", "turn.failed"} for record in records
    ):
        raise CanaryError("exec event stream reports an error or failed turn")
    completed = [
        record
        for record in records
        if record.get("type") == "turn.completed"
    ]
    if len(completed) != 1:
        raise CanaryError("exec event stream must contain one turn.completed")
    return {
        "bytes": len(raw),
        "event_count": len(records),
        "sha256": _sha256_bytes(raw),
        "thread_id": thread_id,
        "turn_completed": True,
    }


def _run_tests(repo: Path) -> tuple[int, bytes]:
    completed = _run(
        [sys.executable, "-B", "-c", REGRESSION_SNIPPET],
        cwd=repo,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr


def _command_label() -> str:
    return f'{Path(sys.executable).name} -B -c "{REGRESSION_SNIPPET}"'


def _record_baseline_failure(
    staging: Path,
    baseline_bundle: Path,
    baseline_commit: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="gate3-live-baseline-check-") as temp:
        repo = Path(temp) / "repo"
        _run(
            ["git", "clone", "--quiet", str(baseline_bundle), str(repo)],
            cwd=Path(temp),
        )
        head = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
        if head != baseline_commit:
            raise CanaryError("baseline bundle does not resolve to pinned commit")
        exit_code, output = _run_tests(repo)
    if exit_code == 0:
        raise CanaryError("baseline regression unexpectedly passed")
    output_path = staging / "baseline-test-output.txt"
    receipt_path = staging / "baseline-test-receipt.json"
    chain._atomic_write(output_path, output)
    _write_json(
        receipt_path,
        {
            "authorization": AUTHORIZATION,
            "command": _command_label(),
            "exit_code": exit_code,
            "expected_failure": True,
            "linked_commit": baseline_commit,
            "output_path": _relative(output_path, staging),
            "output_sha256": _sha256_file(output_path),
            "schema": BASELINE_RECEIPT_SCHEMA,
        },
    )
    return {
        "path": _relative(receipt_path, staging),
        "sha256": _sha256_file(receipt_path),
    }


def _duration_ms(start: str, finish: str) -> int:
    try:
        first = datetime.fromisoformat(start.replace("Z", "+00:00"))
        last = datetime.fromisoformat(finish.replace("Z", "+00:00"))
        return max(1, int((last - first).total_seconds() * 1000))
    except ValueError as exc:
        raise CanaryError("rollout timestamps are not ISO-8601") from exc


def _method_observations(
    baseline_receipt_sha256: str | None = None,
) -> dict[str, dict[str, Any]]:
    values = {
        name: {"evidence_sha256": [], "observed": False}
        for name in (
            "reproduction_before_first_edit",
            "root_cause_recorded_before_first_edit",
            "failing_regression_before_fix",
            "defect_reintroduction_performed",
            "post_restore_retest_performed",
            "claim_bounded_to_evidence",
        )
    }
    if baseline_receipt_sha256 is not None:
        # The observation must name the retained receipt, or
        # regression_baseline_fail is self-reported.
        values["failing_regression_before_fix"] = {
            "evidence_sha256": [baseline_receipt_sha256],
            "observed": True,
        }
    return values


def _capture_outcome(
    *,
    repo: Path,
    rollout_source: Path,
    exec_events_source: Path,
    prompt_path: Path,
    anon_id: str,
    treatment: str,
    suffix: str,
    staging: Path,
    chain_dir: Path,
    contract_path: Path,
    plan: dict[str, Any],
    randomization_sha: str,
    baseline_receipt: dict[str, str],
    rollout_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    repo = repo.resolve()
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all") != b"":
        raise CanaryError(f"producer {treatment} repository is not clean")
    output_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    parents = (
        _git(repo, "rev-list", "--parents", "-n", "1", output_commit)
        .decode("ascii")
        .strip()
        .split()
    )
    if len(parents) != 2 or parents[1] != plan["baseline_commit"]:
        raise CanaryError(
            f"producer {treatment} output is not exactly one child of baseline"
        )
    git_identity = {
        "baseline": _assert_commit_identity(
            repo,
            plan["baseline_commit"],
            BASELINE_GIT_IDENTITY,
        ),
        "output": _assert_commit_identity(
            repo,
            output_commit,
            plan["frozen_route"]["producer_git_identity"],
        ),
    }
    source_route = parse_rollout(
        rollout_source,
        expected_prompt=prompt_path.read_bytes(),
        expected_model=plan["frozen_route"]["model"],
        expected_comp_hash=plan["frozen_route"]["comp_hash"],
        expected_cli_version=plan["frozen_route"]["cli_version"],
        expected_reasoning=plan["frozen_route"]["reasoning"],
        expected_workspace=str(repo),
        expected_context_contract=plan["context_contract"],
        rollout_diagnostic=rollout_diagnostic,
        parse_phase="source",
    )
    source_exec_events = parse_exec_events(
        exec_events_source, expected_session_id=source_route["session_id"]
    )
    outcome = staging / "outcomes" / suffix
    outcome.mkdir(parents=True)
    rollout_path = outcome / "rollout.jsonl"
    context_token = PUBLIC_CONTEXT_TOKENS[treatment]
    public_rollout = sanitize_jsonl(
        rollout_source,
        workspace=str(repo),
        context_token=context_token,
    )
    chain._atomic_write(rollout_path, public_rollout)
    exec_events_path = outcome / "exec-events.jsonl"
    public_exec_events = sanitize_jsonl(
        exec_events_source,
        workspace=str(repo),
        context_token=context_token,
    )
    chain._atomic_write(exec_events_path, public_exec_events)
    route = parse_rollout(
        rollout_path,
        expected_prompt=prompt_path.read_bytes(),
        expected_model=plan["frozen_route"]["model"],
        expected_comp_hash=plan["frozen_route"]["comp_hash"],
        expected_cli_version=plan["frozen_route"]["cli_version"],
        expected_reasoning=plan["frozen_route"]["reasoning"],
        expected_workspace=context_token,
        expected_context_contract=plan["context_contract"],
        rollout_diagnostic=rollout_diagnostic,
        parse_phase="public",
    )
    exec_events = parse_exec_events(
        exec_events_path, expected_session_id=route["session_id"]
    )
    final_diff = outcome / "final-diff.patch"
    chain._atomic_write(
        final_diff,
        _git(
            repo,
            "diff",
            "--binary",
            "--full-index",
            plan["baseline_commit"],
            output_commit,
            "--",
        ),
    )
    if not final_diff.read_bytes():
        raise CanaryError(f"producer {treatment} produced no diff")
    tracked = [
        item.decode("utf-8")
        for item in _git(
            repo,
            "diff",
            "--name-only",
            "-z",
            plan["baseline_commit"],
            output_commit,
            "--",
        ).split(b"\0")
        if item
    ]
    bundle = outcome / "repo.bundle"
    _git(repo, "bundle", "create", str(bundle), "--all")
    test_exit, test_output = _run_tests(repo)
    if test_exit != 0:
        raise CanaryError(f"producer {treatment} regression test failed")
    test_output_path = outcome / "test-output.txt"
    chain._atomic_write(test_output_path, test_output)
    test_receipt = outcome / "test-receipt.json"
    _write_json(
        test_receipt,
        {
            "command": _command_label(),
            "exit_code": test_exit,
            "linked_commit": output_commit,
            "output_path": _relative(test_output_path, staging),
            "output_sha256": _sha256_file(test_output_path),
            "schema": chain.RECEIPT_SCHEMA,
        },
    )
    receipt_index = [
        {
            "path": _relative(test_receipt, staging),
            "sha256": _sha256_file(test_receipt),
        }
    ]
    receipt_set_sha = _sha256_bytes(_json_bytes(receipt_index))
    head_path = outcome / "live-head.txt"
    status_path = outcome / "live-status.txt"
    chain._atomic_write(head_path, (output_commit + "\n").encode("ascii"))
    chain._atomic_write(status_path, b"")
    capture_receipt = outcome / "live-capture-receipt.json"
    _write_json(
        capture_receipt,
        {
            "authorization": AUTHORIZATION,
            "baseline_commit": plan["baseline_commit"],
            "clean": True,
            "head_path": _relative(head_path, staging),
            "head_sha256": _sha256_file(head_path),
            "git_identity": git_identity,
            "output_commit": output_commit,
            "schema": CAPTURE_RECEIPT_SCHEMA,
            "status_path": _relative(status_path, staging),
            "status_sha256": _sha256_file(status_path),
        },
    )
    route_receipt = outcome / "route-receipt.json"
    _write_json(
        route_receipt,
        {
            "authorization": AUTHORIZATION,
            "expected_model_build": plan["frozen_route"]["model_build"],
            "exec_events": exec_events,
            "exec_events_path": _relative(exec_events_path, staging),
            "exec_events_sha256": _sha256_file(exec_events_path),
            "prompt_path": _relative(prompt_path, staging),
            "prompt_sha256": _sha256_file(prompt_path),
            "public_context_token": context_token,
            "rollout_path": _relative(rollout_path, staging),
            "rollout_sha256": _sha256_file(rollout_path),
            "route": route,
            "schema": ROUTE_RECEIPT_SCHEMA,
            "source_attestation": {
                "acceptance_policy_sha256": source_route[
                    "acceptance_policy_sha256"
                ],
                "context_identity_sha256": source_route[
                    "context_identity_sha256"
                ],
                "exec_events_bytes": len(exec_events_source.read_bytes()),
                "exec_events_sha256": _sha256_file(exec_events_source),
                "exec_thread_id": source_exec_events["thread_id"],
                "rollout_bytes": len(rollout_source.read_bytes()),
                "rollout_sha256": _sha256_file(rollout_source),
                "sanitizer_rules_sha256": _sanitizer_rules_sha256(),
                "source_context_verified": True,
                "source_tool_contract_verified": True,
            },
            "treatment": treatment,
        },
    )
    event_log = outcome / "event-log.jsonl"
    event_lines = [
        {
            "event": "fresh_context_verified",
            "receipt_sha256": _sha256_file(route_receipt),
        },
        {
            "event": "tests_passed",
            "receipt_sha256": _sha256_file(test_receipt),
        },
        {
            "event": "clean_capture",
            "receipt_sha256": _sha256_file(capture_receipt),
        },
    ]
    chain._atomic_write(
        event_log,
        b"".join(
            json.dumps(item, sort_keys=True).encode("utf-8") + b"\n"
            for item in event_lines
        ),
    )
    harness_sha = plan["common_inputs"]["harness_contract_sha256"]["sha256"]
    packet = outcome / "scorer-packet.json"
    _write_json(
        packet,
        {
            "anon_id": anon_id,
            "baseline_commit": plan["baseline_commit"],
            "final_diff_sha256": _sha256_file(final_diff),
            "harness_contract_sha256": harness_sha,
            "output_commit": output_commit,
            "receipt_set_sha256": receipt_set_sha,
            "schema": chain.OUTCOME_PACKET_SCHEMA,
            "scorer_payload": {
                "baseline_test_receipt_sha256": baseline_receipt["sha256"],
                "final_diff_utf8": final_diff.read_text(encoding="utf-8"),
                "test_exit_code": test_exit,
            },
        },
    )
    input_artifacts = {
        **copy.deepcopy(plan["common_inputs"]),
        **copy.deepcopy(plan["treatment_inputs"][treatment]),
        "randomization_record_sha256": {
            "path": "randomization-record.json",
            "sha256": randomization_sha,
        },
    }
    admission = outcome / "admission.json"
    _write_json(
        admission,
        {
            "anon_id": anon_id,
            "baseline_commit": plan["baseline_commit"],
            "baseline_test_receipt": dict(baseline_receipt),
            "event_log": {
                "path": _relative(event_log, staging),
                "sha256": _sha256_file(event_log),
            },
            "final_diff": {
                "path": _relative(final_diff, staging),
                "sha256": _sha256_file(final_diff),
                "tracked_changed_files": tracked,
            },
            "git_bundle": {
                "path": _relative(bundle, staging),
                "sha256": _sha256_file(bundle),
            },
            "input_artifacts": input_artifacts,
            "input_digests": {
                field: entry["sha256"]
                for field, entry in input_artifacts.items()
            },
            "model_build": plan["frozen_route"]["model_build"],
            "output_commit": output_commit,
            "output_packet_sha256": _sha256_file(packet),
            "receipt_set_sha256": receipt_set_sha,
            "receipts": receipt_index,
            "schema": chain.ADMISSION_SCHEMA,
            "treatment": treatment,
            "worktree_clean_at_capture": True,
        },
    )
    metrics = outcome / "metrics.json"
    _write_json(
        metrics,
        {
            "anon_id": anon_id,
            "artifacts": {
                "event_log_sha256": _sha256_file(event_log),
                "output_packet_sha256": _sha256_file(packet),
            },
            "baseline_commit": plan["baseline_commit"],
            "budget_sha256": plan["common_inputs"]["budget_sha256"]["sha256"],
            "completed_under_cap": (
                route["tool_calls"] <= 40
                and _duration_ms(route["started_at"], route["finished_at"])
                <= 900_000
            ),
            "conditional_quality_eligible": True,
            "costs": {
                "changed_files": len(tracked),
                "core_available": True,
                "diff_bytes": len(final_diff.read_bytes()),
                "owner_interventions": 0,
                "retries": 0,
                "rework_count": 0,
                "tokens": {
                    "available": False,
                    "reason": (
                        "raw Codex rollout does not expose a stable aggregate "
                        "token field in this route verifier"
                    ),
                },
                "tool_calls": route["tool_calls"],
                "wall_clock_ms": _duration_ms(
                    route["started_at"], route["finished_at"]
                ),
            },
            "harness_contract_sha256": harness_sha,
            "method_observations": _method_observations(
                baseline_receipt["sha256"]
            ),
            "model_build": plan["frozen_route"]["model_build"],
            "pair_id": plan["run_id"],
            "permissions_sha256": plan["common_inputs"][
                "permissions_sha256"
            ]["sha256"],
            "randomization_record_sha256": randomization_sha,
            "repeat_index": 1,
            "run_id": f"{plan['run_id']}-{treatment.lower()}",
            "schema": chain.METRICS_SCHEMA,
            "scorer_rubric_sha256": plan["common_inputs"][
                "scorer_rubric_sha256"
            ]["sha256"],
            "status": "completed",
            "task_id": "synthetic-calc-live-route-canary",
            "task_packet_sha256": plan["common_inputs"][
                "task_packet_sha256"
            ]["sha256"],
            "timestamps": {
                "finished_at": route["finished_at"],
                "first_edit_at": route["started_at"],
                "started_at": route["started_at"],
            },
        },
    )
    chain.seal_outcome(
        chain_dir, contract_path, packet, metrics, admission, repo
    )
    return {
        "admission_path": _relative(admission, staging),
        "anon_id": anon_id,
        "capture_receipt_path": _relative(capture_receipt, staging),
        "metrics_path": _relative(metrics, staging),
        "output_commit": output_commit,
        "packet_path": _relative(packet, staging),
        "route_receipt_path": _relative(route_receipt, staging),
        "session_id": route["session_id"],
        "treatment": treatment,
    }


def _mechanical_score(
    role: str,
    outcomes: list[dict[str, Any]],
    scorer_rubric_sha: str,
    blind_set_sha: str,
) -> dict[str, Any]:
    return {
        "blind_input_set_sha256": blind_set_sha,
        "independence_declaration": True,
        "model_build": "mechanical-live-canary-verifier-v1",
        "outputs": [
            {
                "anon_id": outcome["anon_id"],
                "claim_mismatch_count": 0,
                "completed_under_cap": True,
                "critical_residuals": 0,
                "major_residuals": 0,
                "no_new_scoped_regression": True,
                "oracle_acceptance": True,
                "original_defect_caught": True,
                "regression_baseline_fail": True,
                "regression_passes_after_fix": True,
                "scope_hygiene": "clean",
                "sensitivity_score": {"caught": 1, "total": 1},
            }
            for outcome in sorted(outcomes, key=lambda value: value["anon_id"])
        ],
        "schema": chain.SCORE_SCHEMA,
        "scorer_context_id": f"mechanical-live-canary-{role}-context",
        "scorer_identity": f"mechanical-live-canary-{role}",
        "scorer_role": role,
        "scorer_rubric_sha256": scorer_rubric_sha,
    }


def _validate_credential_runner_receipt(
    path: Path,
    route_plan_path: Path,
) -> dict[str, Any]:
    plan = _load_json(route_plan_path)
    receipt = _load_json(path)
    expected = {
        "auth_files_removed": True,
        "auth_route": "chatgpt",
        "credential_seed_compare": "PASS",
        "implementation": {
            "launcher_sha256": plan["frozen_route"][
                "launcher_implementation_sha256"
            ],
            "pair_runner_sha256": plan["frozen_route"][
                "pair_runner_implementation_sha256"
            ],
        },
        "login_status": {"A": "PASS", "B": "PASS"},
        "route_plan_sha256": _sha256_file(route_plan_path),
        "schema": CREDENTIAL_RECEIPT_SCHEMA,
        "secret_material_retained": False,
        "session_exit_codes": {"A": 0, "B": 0},
        "session_invocations": 2,
    }
    if receipt != expected:
        raise CanaryError("credential runner receipt is invalid")
    encoded = _json_bytes(receipt)
    if _privacy_violations(encoded):
        raise CanaryError("credential runner receipt contains private material")
    return receipt


def _census_incomplete_arms(
    *,
    sources: dict[str, tuple[Path, Path, Path]],
    staging: Path,
    plan: dict[str, Any],
    rollout_diagnostics: dict[str, dict[str, Any]],
) -> None:
    """Fill in every parse phase an aborted build left at ``NOT_RUN``.

    Two gaps used to survive a failed build. An arm that never got its turn
    was left unparsed entirely, and an arm whose source parse failed never
    reached the public phase, because the public rollout is only produced
    after the source parse succeeds. Either way one authorized pair yielded a
    fraction of the four observations it cost, and the missing ones could only
    be bought with another pair.

    The public phase is censused from bytes sanitized in memory with the
    build's own sanitizer. Nothing is written to disk: a sanitizer's output is
    not the same thing as output proven publishable, so a copy of private
    material is never given a filesystem path it could outlive this call
    through. The bytes are equivalent by construction to the staged artifact
    but are not it, so arms censused this way are flagged; a reader must not
    mistake this for the public rollout admission would have seen.

    Diagnostics only. It writes nothing anywhere, admits nothing, and never
    lets its own failure escape. Its failures are not silent either: each
    phase records a fixed-vocabulary ``census_status``, because a phase left
    at ``NOT_RUN`` with no reason is indistinguishable from a phase nobody
    tried, and one of those is a defect.
    """
    for treatment, (repo, rollout_source, _) in sorted(sources.items()):
        diagnostic = rollout_diagnostics.get(treatment)
        if not isinstance(diagnostic, dict):
            continue
        prompt_path = (
            staging / "inputs" / f"producer-prompt-{treatment.lower()}.txt"
        )
        try:
            common: dict[str, Any] = {
                "expected_prompt": prompt_path.read_bytes(),
                "expected_model": plan["frozen_route"]["model"],
                "expected_comp_hash": plan["frozen_route"]["comp_hash"],
                "expected_cli_version": plan["frozen_route"]["cli_version"],
                "expected_reasoning": plan["frozen_route"]["reasoning"],
                "expected_context_contract": plan["context_contract"],
            }
        except (OSError, KeyError, TypeError, ValueError):
            for phase in ("source", "public"):
                if diagnostic["parse_phases"][phase] == "NOT_RUN":
                    diagnostic["census_status"][phase] = (
                        "diagnostic_setup_failed"
                    )
            continue
        if diagnostic["parse_phases"]["source"] == "NOT_RUN":
            diagnostic["census_status"]["source"] = "parse_attempted"
            try:
                parse_rollout(
                    rollout_source,
                    expected_workspace=str(repo.resolve()),
                    rollout_diagnostic=diagnostic,
                    parse_phase="source",
                    **common,
                )
            except (CanaryError, OSError, KeyError, TypeError, ValueError):
                pass
        if diagnostic["parse_phases"]["public"] != "NOT_RUN":
            continue
        context_token = PUBLIC_CONTEXT_TOKENS.get(treatment)
        if context_token is None:
            diagnostic["census_status"]["public"] = "diagnostic_setup_failed"
            continue
        try:
            sanitized = sanitize_jsonl(
                rollout_source,
                workspace=str(repo.resolve()),
                context_token=context_token,
            )
        except (CanaryError, OSError, KeyError, TypeError, ValueError):
            diagnostic["census_status"]["public"] = "sanitize_failed"
            continue
        diagnostic["public_phase_from_diagnostic_copy"] = True
        diagnostic["census_status"]["public"] = "parse_attempted"
        try:
            parse_rollout(
                None,
                source_bytes=sanitized,
                expected_workspace=context_token,
                rollout_diagnostic=diagnostic,
                parse_phase="public",
                **common,
            )
        except (CanaryError, OSError, KeyError, TypeError, ValueError):
            continue


def _build_orchestrated(
    repo_root: Path,
    staging: Path,
    output_root: Path,
    *,
    arm_a_repo: Path,
    arm_b_repo: Path,
    arm_a_rollout: Path,
    arm_b_rollout: Path,
    arm_a_exec_events: Path,
    arm_b_exec_events: Path,
    credential_runner_receipt: Path,
    rollout_diagnostics: dict[str, dict[str, Any]],
    nonce_hex: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    staging = staging.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise CanaryError(f"output already exists: {output_root}")
    if not staging.is_dir():
        raise CanaryError("prepared staging root is missing")
    plan = _load_json(staging / "route-plan.json")
    if (
        plan.get("schema") != ROUTE_PLAN_SCHEMA
        or plan.get("authorization") != AUTHORIZATION
        or plan.get("rehearsal_kind") != REHEARSAL_KIND
        or plan.get("credential_contract") != CREDENTIAL_CONTRACT
    ):
        raise CanaryError("route plan identity is invalid")
    credential_receipt = _validate_credential_runner_receipt(
        credential_runner_receipt.resolve(),
        staging / "route-plan.json",
    )
    public_credential_receipt = staging / "credential-runner-receipt.json"
    _write_json(public_credential_receipt, credential_receipt)
    _validate_candidate(repo_root)
    contract_path = repo_root / DEFAULT_CONTRACT.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    nonce = nonce_hex or secrets.token_hex(32)
    if len(nonce) != 64 or any(char not in "0123456789abcdef" for char in nonce):
        raise CanaryError("nonce must be 64 lowercase hex characters")
    randomization = staging / "randomization-record.json"
    treatment_digests = {
        treatment: {
            field: entry["sha256"]
            for field, entry in plan["treatment_inputs"][treatment].items()
        }
        for treatment in ("A", "B")
    }
    _write_json(
        randomization,
        {
            "anonymous_ids": sorted(ANON_MAPPING),
            "mapping_commitment_sha256": chain._mapping_commitment(
                ANON_MAPPING, "skill_primary", nonce
            ),
            "pair_id": plan["run_id"],
            "repeat_index": 1,
            "schema": chain.RANDOMIZATION_SCHEMA,
            "study_kind": "skill_primary",
            "task_id": "synthetic-calc-live-route-canary",
            "treatment_inputs": treatment_digests,
        },
    )
    randomization_sha = _sha256_file(randomization)
    chain_dir = staging / "chain"
    chain.commit_randomization(chain_dir, contract_path, randomization)
    baseline_receipt = _record_baseline_failure(
        staging,
        staging / "inputs" / "baseline.bundle",
        plan["baseline_commit"],
    )
    sources = {
        "A": (arm_a_repo, arm_a_rollout, arm_a_exec_events),
        "B": (arm_b_repo, arm_b_rollout, arm_b_exec_events),
    }
    outcomes = []
    with _git_safe_directories([arm_a_repo, arm_b_repo]):
        try:
            for anon_id, treatment in sorted(ANON_MAPPING.items()):
                source_repo, source_rollout, source_exec_events = sources[treatment]
                outcomes.append(
                    _capture_outcome(
                        repo=source_repo,
                        rollout_source=source_rollout,
                        exec_events_source=source_exec_events,
                        prompt_path=staging
                        / "inputs"
                        / f"producer-prompt-{treatment.lower()}.txt",
                        anon_id=anon_id,
                        treatment=treatment,
                        suffix=treatment.lower(),
                        staging=staging,
                        chain_dir=chain_dir,
                        contract_path=contract_path,
                        plan=plan,
                        randomization_sha=randomization_sha,
                        baseline_receipt=baseline_receipt,
                        rollout_diagnostic=rollout_diagnostics[treatment],
                    )
                )
        except CanaryError:
            _census_incomplete_arms(
                sources=sources,
                staging=staging,
                plan=plan,
                rollout_diagnostics=rollout_diagnostics,
            )
            raise
    sessions = {outcome["session_id"] for outcome in outcomes}
    if len(sessions) != 2:
        raise CanaryError("A/B must come from two distinct fresh contexts")
    route_receipts = [
        _load_json(staging / outcome["route_receipt_path"]) for outcome in outcomes
    ]
    if (
        route_receipts[0]["route"]["permission_fingerprint"]
        != route_receipts[1]["route"]["permission_fingerprint"]
    ):
        raise CanaryError("A/B permission fingerprints differ")
    # Both arms must have been judged under the same acceptance policy, and
    # under the policy this process is running. Otherwise a comparison could
    # rest on one arm having been admitted by looser rules than the other.
    policy_digests = {
        receipt[section]["acceptance_policy_sha256"]
        for receipt in route_receipts
        for section in ("route", "source_attestation")
    }
    if policy_digests != {contract.policy_digest()}:
        raise CanaryError("A/B acceptance policies differ")
    if (
        route_receipts[0]["route"]["context_identity_sha256"]
        != route_receipts[1]["route"]["context_identity_sha256"]
        or route_receipts[0]["source_attestation"]["context_identity_sha256"]
        != route_receipts[1]["source_attestation"]["context_identity_sha256"]
    ):
        raise CanaryError("A/B frozen context identities differ")
    chain.close_blind_set(chain_dir, contract_path, "skill_primary")
    close_event = _load_json(chain._event_files(chain_dir)[3])
    for role in ("primary", "second"):
        score = staging / f"mechanical-{role}-score.json"
        _write_json(
            score,
            _mechanical_score(
                role,
                outcomes,
                plan["common_inputs"]["scorer_rubric_sha256"]["sha256"],
                close_event["blind_input_set_sha256"],
            ),
        )
        chain.submit_scorer(chain_dir, contract_path, role, score)
    mapping = staging / "mapping-reveal.json"
    _write_json(
        mapping,
        {
            "mapping": ANON_MAPPING,
            "nonce_hex": nonce,
            "randomization_record_sha256": randomization_sha,
            "schema": chain.MAPPING_SCHEMA,
            "study_kind": "skill_primary",
        },
    )
    chain.release_mapping(chain_dir, contract_path, mapping)
    chain_result = chain.verify_chain(
        chain_dir, contract_path, require_state="mapping_released"
    )
    summary = {
        "artifact_inventory": _inventory(staging),
        "authorization": AUTHORIZATION,
        "baseline_test_receipt": baseline_receipt,
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
        "candidate_verification_checks": plan[
            "candidate_verification_checks"
        ],
        "credential_contract": CREDENTIAL_CONTRACT,
        "credential_runner_receipt": _artifact_entry(
            public_credential_receipt, staging
        ),
        "chain": {
            "event_count": chain_result["event_count"],
            "head_sha256": chain_result["head_sha256"],
            "state": chain_result["state"],
        },
        "frozen_route": plan["frozen_route"],
        "harness_implementation_sha256": _sha256_file(Path(__file__)),
        "implementation": plan["implementation"],
        "launcher_implementation_sha256": _sha256_file(
            DEFAULT_SESSION_LAUNCHER
        ),
        "pair_runner_implementation_sha256": _sha256_file(
            DEFAULT_PAIR_RUNNER
        ),
        "tests_implementation_sha256": _sha256_file(DEFAULT_TESTS),
        "not_claimed": [
            "independent approval",
            "owner signature",
            "canonical promotion",
            "natural bug admission",
            "counted Gate 3 run",
            "Gate 3 start",
            "Skill effectiveness",
            "human or model blind scoring",
            "cryptographic writer authentication",
            "public revalidation of raw-to-sanitized transformation without "
            "private source evidence",
        ],
        "outcomes": sorted(outcomes, key=lambda value: value["anon_id"]),
        "rehearsal_kind": REHEARSAL_KIND,
        "privacy": {
            "public_evidence_only": True,
            "raw_evidence_retained_in_git": False,
            "sanitizer_rules_sha256": _sanitizer_rules_sha256(),
            "sanitizer_schema": SANITIZER_SCHEMA,
        },
        "route_plan_sha256": _sha256_file(staging / "route-plan.json"),
        "run_id": plan["run_id"],
        "schema": SUMMARY_SCHEMA,
    }
    _write_json(staging / "canary-summary.json", summary)
    result = verify(repo_root, staging)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    os.rename(staging, output_root)
    return verify(repo_root, output_root)


def _single_rollout(codex_home: Path) -> Path:
    rollouts = sorted(
        path
        for path in (codex_home / "sessions").rglob("*.jsonl")
        if path.is_file()
    )
    if len(rollouts) != 1:
        raise CanaryError("isolated Codex home did not produce one rollout")
    return rollouts[0]


def _run_private_process(command: list[str], *, label: str) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=False,
    )
    if result.returncode != 0:
        raise CanaryError(f"{label} failed")


def _remove_private_tree(path: Path) -> None:
    if not path.exists():
        return

    def clear_readonly_and_retry(
        function: Any,
        target: str,
        _error: object,
    ) -> None:
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onerror=clear_readonly_and_retry)


def _failure_execution_summary(
    receipt_path: Path | None,
    *,
    pair_started: bool,
) -> dict[str, Any]:
    default = {
        "credential_preflight": "NOT_OBSERVED",
        "login_status": {"A": "NOT_OBSERVED", "B": "NOT_OBSERVED"},
        "runner_receipt_status": "NOT_CREATED",
        "session_exit_codes": {"A": None, "B": None},
        "session_invocations": 0,
    }
    def invalid(status: str) -> dict[str, Any]:
        default["runner_receipt_status"] = status
        if pair_started:
            default["session_invocations"] = None
        return default

    if receipt_path is None:
        return invalid(
            "MISSING_AFTER_RUNNER_START" if pair_started else "NOT_CREATED"
        )
    try:
        if not receipt_path.is_file():
            return invalid(
                "MISSING_AFTER_RUNNER_START"
                if pair_started
                else "NOT_CREATED"
            )
        receipt = _load_json(receipt_path)
        if _privacy_violations(_json_bytes(receipt)):
            return invalid("PRIVACY_REJECTED")
        invocations = receipt.get("session_invocations")
        login_status = receipt.get("login_status")
        exit_codes = receipt.get("session_exit_codes")
        if (
            receipt.get("schema") != CREDENTIAL_RECEIPT_SCHEMA
            or not isinstance(invocations, int)
            or isinstance(invocations, bool)
            or invocations not in {0, 1, 2}
            or not isinstance(login_status, dict)
            or set(login_status) != {"A", "B"}
            or any(
                value not in {"PASS", "FAIL"}
                for value in login_status.values()
            )
            or not isinstance(exit_codes, dict)
            or set(exit_codes) != {"A", "B"}
            or any(
                value is not None
                and (not isinstance(value, int) or isinstance(value, bool))
                for value in exit_codes.values()
            )
            or (
                invocations == 0
                and exit_codes != {"A": None, "B": None}
            )
            or (
                invocations == 1
                and (
                    not isinstance(exit_codes["A"], int)
                    or isinstance(exit_codes["A"], bool)
                    or exit_codes["B"] is not None
                )
            )
            or (
                invocations == 2
                and any(
                    not isinstance(exit_codes[arm], int)
                    or isinstance(exit_codes[arm], bool)
                    for arm in ("A", "B")
                )
            )
            or (
                invocations > 0
                and login_status != {"A": "PASS", "B": "PASS"}
            )
        ):
            return invalid("INVALID")
        return {
            "credential_preflight": (
                "PASS"
                if login_status == {"A": "PASS", "B": "PASS"}
                else "FAIL"
            ),
            "login_status": {
                "A": login_status["A"],
                "B": login_status["B"],
            },
            "runner_receipt_status": "VALID",
            "session_exit_codes": {
                "A": exit_codes["A"],
                "B": exit_codes["B"],
            },
            "session_invocations": invocations,
        }
    except Exception:
        # The private runner receipt is untrusted evidence. This projection is
        # deliberately total so malformed evidence cannot skip cleanup.
        return invalid("INVALID")


def _publish_failure_receipt(
    output_root: Path,
    *,
    run_id: str,
    failure_stage: str,
    execution: dict[str, Any],
    cleanup_status: str,
    residue_classes: list[str],
    success_packet_publication_attempted: bool,
    success_packet_present: bool,
    rollout_diagnostics: object = None,
) -> Path:
    failure_root = output_root.with_name(f"{output_root.name}.failure")
    if failure_root.exists():
        raise CanaryError("failure receipt output already exists")
    public_run_id = run_id if PUBLIC_RUN_ID_RE.fullmatch(run_id) else "REDACTED"
    receipt = {
        "authorization": {
            "counted_gate3_run": False,
            "replacement_sessions": 0,
        },
        "cleanup": {
            "residue_classes": sorted(residue_classes),
            "status": cleanup_status,
        },
        "credential_privacy": {
            "credential_bytes_or_content_retained": False,
            "credential_digest_retained": False,
            "credential_source_path_retained": False,
            "raw_output_retained": False,
        },
        "execution": execution,
        "failure_stage": failure_stage,
        "non_counted": True,
        "run_id": public_run_id,
        "schema": FAILURE_RECEIPT_SCHEMA,
        "scoreable": False,
        "success_packet_admitted": False,
        "success_packet_present": success_packet_present,
        "success_packet_publication_attempted": (
            success_packet_publication_attempted
        ),
    }
    if failure_stage == "packet_build":
        receipt["rollout_diagnostics"] = _failure_rollout_diagnostics(
            rollout_diagnostics
        )
    payload = _json_bytes(receipt)
    if _privacy_violations(payload):
        raise CanaryError("failure receipt contains private material")
    candidate = output_root.parent / (
        f".{output_root.name}.failure-candidate-{secrets.token_hex(8)}"
    )
    candidate_owned = False
    try:
        os.mkdir(candidate)
        candidate_owned = True
        chain._atomic_write(candidate / "failure-receipt.json", payload)
        verify_public_privacy(candidate)
        os.rename(candidate, failure_root)
        candidate_owned = False
    finally:
        if candidate_owned and candidate.exists():
            _remove_private_tree(candidate)
    return failure_root / "failure-receipt.json"


def _orchestrate_impl(
    repo_root: Path,
    output_root: Path,
    *,
    run_id: str,
    _builder: Any,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    if not PUBLIC_RUN_ID_RE.fullmatch(run_id):
        raise CanaryError("run id is not a privacy-safe public identifier")
    if output_root.exists():
        raise CanaryError(f"output already exists: {output_root}")
    failure_root = output_root.with_name(f"{output_root.name}.failure")
    if failure_root.exists():
        raise CanaryError(f"failure output already exists: {failure_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    private_root = Path(tempfile.mkdtemp(prefix="gate3-codex-live-")).resolve()
    public_candidate = (
        output_root.parent
        / f".{output_root.name}.candidate-{secrets.token_hex(8)}"
    )
    private_built = private_root / "public-packet"
    candidate_owned = False
    publication_attempted = False
    published_by_us = False
    succeeded = False
    failure_stage = "setup"
    pair_started = False
    credential_receipt: Path | None = None
    rollout_diagnostics = _empty_rollout_diagnostics()
    try:
        if public_candidate.exists():
            raise CanaryError("public candidate path already exists")
        cli_root = private_root / "cli"
        staging = private_root / "staging"
        raw = private_root / "raw"
        raw.mkdir()
        homes = {
            "A": private_root / "codex-home-a",
            "B": private_root / "codex-home-b",
        }
        repos = {
            "A": private_root / "repo-a",
            "B": private_root / "repo-b",
        }
        for home in homes.values():
            home.mkdir()
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if npm is None:
            raise CanaryError("npm command is unavailable")
        failure_stage = "cli_install"
        _run_private_process(
            [
                npm,
                "install",
                "--prefix",
                str(cli_root),
                f"@openai/codex@{DEFAULT_CLI_VERSION}",
                "--no-save",
                "--no-audit",
                "--no-fund",
            ],
            label="temporary Codex CLI installation",
        )
        codex_command = cli_root / "node_modules" / ".bin" / "codex.cmd"
        if not codex_command.is_file():
            raise CanaryError("temporary Codex CLI entrypoint is missing")
        version_result = subprocess.run(
            [str(codex_command), "--version"],
            capture_output=True,
            check=False,
            text=True,
        )
        if (
            version_result.returncode != 0
            or not re.search(
                rf"(?<![0-9.]){re.escape(DEFAULT_CLI_VERSION)}(?![0-9.])",
                version_result.stdout + version_result.stderr,
            )
        ):
            raise CanaryError("temporary Codex CLI build identity mismatch")
        failure_stage = "route_prepare"
        prepare(
            repo_root,
            staging,
            run_id=run_id,
            model=DEFAULT_MODEL,
            comp_hash=DEFAULT_COMP_HASH,
            cli_version=DEFAULT_CLI_VERSION,
            reasoning=DEFAULT_REASONING,
        )
        baseline_bundle = staging / "inputs" / "baseline.bundle"
        failure_stage = "repository_prepare"
        for treatment in ("A", "B"):
            _run_private_process(
                [
                    "git",
                    "clone",
                    "-q",
                    str(baseline_bundle),
                    str(repos[treatment]),
                ],
                label=f"synthetic repository {treatment} creation",
            )
        paths = {
            treatment: {
                "stdout": raw / f"{treatment.lower()}.stdout.jsonl",
                "stderr": raw / f"{treatment.lower()}.stderr.txt",
                "exit": raw / f"{treatment.lower()}.exit.txt",
            }
            for treatment in ("A", "B")
        }
        credential_receipt = raw / "credential-runner-receipt.json"
        failure_stage = "pair_execution"
        pair_started = True
        pair_result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(DEFAULT_PAIR_RUNNER),
                "-CodexCommand",
                str(codex_command),
                "-RoutePlanPath",
                str(staging / "route-plan.json"),
                "-ArmAWorkspace",
                str(repos["A"]),
                "-ArmBWorkspace",
                str(repos["B"]),
                "-ArmAPromptPath",
                str(staging / "inputs" / "producer-prompt-a.txt"),
                "-ArmBPromptPath",
                str(staging / "inputs" / "producer-prompt-b.txt"),
                "-ArmACodexHome",
                str(homes["A"]),
                "-ArmBCodexHome",
                str(homes["B"]),
                "-ArmAStdoutPath",
                str(paths["A"]["stdout"]),
                "-ArmBStdoutPath",
                str(paths["B"]["stdout"]),
                "-ArmAStderrPath",
                str(paths["A"]["stderr"]),
                "-ArmBStderrPath",
                str(paths["B"]["stderr"]),
                "-ArmAExitCodePath",
                str(paths["A"]["exit"]),
                "-ArmBExitCodePath",
                str(paths["B"]["exit"]),
                "-PrivateReceiptPath",
                str(credential_receipt),
            ],
            capture_output=True,
            check=False,
            text=False,
        )
        if pair_result.returncode != 0:
            raise CanaryError("authorized A/B pair failed")
        failure_stage = "packet_build"
        rollouts = {
            arm: _single_rollout(homes[arm]) for arm in ("A", "B")
        }
        for arm, rollout in rollouts.items():
            if not rollout.is_file():
                continue
            try:
                records = _load_jsonl(rollout, label="rollout census")
            except (CanaryError, OSError):
                continue
            rollout_diagnostics[arm]["source_census"] = (
                _world_state_census(records)
            )
        _builder(
            repo_root,
            staging,
            private_built,
            arm_a_repo=repos["A"],
            arm_b_repo=repos["B"],
            arm_a_rollout=rollouts["A"],
            arm_b_rollout=rollouts["B"],
            arm_a_exec_events=paths["A"]["stdout"],
            arm_b_exec_events=paths["B"]["stdout"],
            credential_runner_receipt=credential_receipt,
            rollout_diagnostics=rollout_diagnostics,
        )
        failure_stage = "candidate_verification"
        os.mkdir(public_candidate)
        candidate_owned = True
        shutil.copytree(
            private_built,
            public_candidate,
            dirs_exist_ok=True,
        )
        verify(repo_root, public_candidate)
        failure_stage = "private_cleanup"
        _remove_private_tree(private_root)
        if private_root.exists():
            raise CanaryError("private runtime cleanup verification failed")
        failure_stage = "success_publication"
        publication_attempted = True
        os.replace(public_candidate, output_root)
        candidate_owned = False
        published_by_us = True
        failure_stage = "post_publication_verification"
        result = verify(repo_root, output_root)
        succeeded = True
        return result
    finally:
        execution = _failure_execution_summary(
            credential_receipt,
            pair_started=pair_started,
        )
        if private_root.exists():
            try:
                _remove_private_tree(private_root)
            except OSError:
                pass
        if not succeeded:
            if candidate_owned:
                try:
                    _remove_private_tree(public_candidate)
                except OSError:
                    pass
            if published_by_us:
                try:
                    _remove_private_tree(output_root)
                except OSError:
                    pass
        residue_classes = []
        if private_root.exists():
            residue_classes.append("private_runtime")
        if not succeeded and candidate_owned and public_candidate.exists():
            residue_classes.append("public_candidate")
        if not succeeded and published_by_us and output_root.exists():
            residue_classes.append("success_output")
        if not succeeded:
            cleanup_status = "PASS" if not residue_classes else "FAIL"
            _publish_failure_receipt(
                output_root,
                run_id=run_id,
                failure_stage=failure_stage,
                execution=execution,
                cleanup_status=cleanup_status,
                residue_classes=residue_classes,
                success_packet_publication_attempted=publication_attempted,
                success_packet_present=output_root.exists(),
                rollout_diagnostics=rollout_diagnostics,
            )
        if residue_classes:
            raise CanaryError("failed runtime artifact cleanup verification")


def _bind_orchestrator(implementation: Any, builder: Any):
    def bound(
        repo_root: Path,
        output_root: Path,
        *,
        run_id: str,
    ) -> dict[str, Any]:
        return implementation(
            repo_root,
            output_root,
            run_id=run_id,
            _builder=builder,
        )

    return bound


orchestrate = _bind_orchestrator(_orchestrate_impl, _build_orchestrated)
del _bind_orchestrator
del _build_orchestrated
del _orchestrate_impl


def _verify_baseline(root: Path, entry: object) -> str:
    if not isinstance(entry, dict):
        raise CanaryError("baseline receipt entry is absent")
    receipt_path = _source(entry.get("path"), root)
    if entry.get("sha256") != _sha256_file(receipt_path):
        raise CanaryError("baseline receipt digest mismatch")
    receipt = _load_json(receipt_path)
    output = _source(receipt.get("output_path"), root)
    if (
        receipt.get("schema") != BASELINE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("expected_failure") is not True
        or not isinstance(receipt.get("exit_code"), int)
        or isinstance(receipt.get("exit_code"), bool)
        or receipt["exit_code"] == 0
        or receipt.get("output_sha256") != _sha256_file(output)
    ):
        raise CanaryError("baseline receipt is invalid")
    return str(receipt.get("linked_commit"))


def _verify_credential_receipt(
    root: Path,
    entry: object,
    route_plan_path: Path,
) -> None:
    if not isinstance(entry, dict):
        raise CanaryError("credential receipt entry is absent")
    receipt_path = _source(entry.get("path"), root)
    if (
        entry.get("bytes") != receipt_path.stat().st_size
        or entry.get("sha256") != _sha256_file(receipt_path)
    ):
        raise CanaryError("credential receipt artifact identity mismatch")
    _validate_credential_runner_receipt(receipt_path, route_plan_path)


def _verify_route_receipt(
    root: Path,
    outcome: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    receipt = _load_json(_source(outcome.get("route_receipt_path"), root))
    if (
        receipt.get("schema") != ROUTE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("treatment") != outcome.get("treatment")
        or receipt.get("expected_model_build")
        != plan["frozen_route"]["model_build"]
    ):
        raise CanaryError("route receipt identity is invalid")
    context_token = plan["context_contract"]["public_context_tokens"][
        outcome["treatment"]
    ]
    source_attestation = receipt.get("source_attestation")
    if (
        receipt.get("public_context_token") != context_token
        or not isinstance(source_attestation, dict)
        or source_attestation.get("sanitizer_rules_sha256")
        != _sanitizer_rules_sha256()
        or source_attestation.get("source_context_verified") is not True
        or source_attestation.get("source_tool_contract_verified") is not True
        or not isinstance(source_attestation.get("rollout_bytes"), int)
        or source_attestation["rollout_bytes"] <= 0
        or not isinstance(source_attestation.get("exec_events_bytes"), int)
        or source_attestation["exec_events_bytes"] <= 0
        or any(
            not isinstance(source_attestation.get(field), str)
            or len(source_attestation[field]) != 64
            for field in (
                "acceptance_policy_sha256",
                "context_identity_sha256",
                "exec_events_sha256",
                "rollout_sha256",
            )
        )
    ):
        raise CanaryError("route source attestation is invalid")
    # A receipt is only readable against the rules that produced it, so
    # verification refuses one that does not name them, or names different
    # ones from the policy doing the verifying.
    running_policy = contract.policy_digest()
    if (
        receipt.get("route", {}).get("acceptance_policy_sha256")
        != running_policy
        or source_attestation["acceptance_policy_sha256"] != running_policy
    ):
        raise CanaryError("route receipt acceptance policy differs")
    prompt = _source(receipt.get("prompt_path"), root)
    rollout = _source(receipt.get("rollout_path"), root)
    exec_events = _source(receipt.get("exec_events_path"), root)
    if (
        receipt.get("prompt_sha256") != _sha256_file(prompt)
        or receipt.get("rollout_sha256") != _sha256_file(rollout)
        or receipt.get("exec_events_sha256") != _sha256_file(exec_events)
    ):
        raise CanaryError("route receipt artifact digest mismatch")
    rebuilt = parse_rollout(
        rollout,
        expected_prompt=prompt.read_bytes(),
        expected_model=plan["frozen_route"]["model"],
        expected_comp_hash=plan["frozen_route"]["comp_hash"],
        expected_cli_version=plan["frozen_route"]["cli_version"],
        expected_reasoning=plan["frozen_route"]["reasoning"],
        expected_workspace=context_token,
        expected_context_contract=plan["context_contract"],
    )
    if receipt.get("route") != rebuilt:
        raise CanaryError("route receipt differs from raw rollout rebuild")
    rebuilt_exec_events = parse_exec_events(
        exec_events, expected_session_id=rebuilt["session_id"]
    )
    if receipt.get("exec_events") != rebuilt_exec_events:
        raise CanaryError("route receipt differs from raw exec event rebuild")
    if rebuilt["session_id"] != outcome.get("session_id"):
        raise CanaryError("outcome session id differs from raw rollout")
    if source_attestation.get("exec_thread_id") != rebuilt["session_id"]:
        raise CanaryError("source exec thread differs from public rollout")
    rebuilt["_source_context_identity_sha256"] = source_attestation[
        "context_identity_sha256"
    ]
    return rebuilt


def _verify_capture(
    root: Path,
    outcome: dict[str, Any],
    admission: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    receipt = _load_json(_source(outcome.get("capture_receipt_path"), root))
    head = _source(receipt.get("head_path"), root)
    status = _source(receipt.get("status_path"), root)
    if (
        receipt.get("schema") != CAPTURE_RECEIPT_SCHEMA
        or receipt.get("authorization") != AUTHORIZATION
        or receipt.get("clean") is not True
        or receipt.get("baseline_commit") != admission["baseline_commit"]
        or receipt.get("output_commit") != admission["output_commit"]
        or receipt.get("output_commit") != outcome.get("output_commit")
        or receipt.get("git_identity")
        != {
            "baseline": _expanded_git_identity(BASELINE_GIT_IDENTITY),
            "output": _expanded_git_identity(
                plan["frozen_route"]["producer_git_identity"]
            ),
        }
        or receipt.get("head_sha256") != _sha256_file(head)
        or receipt.get("status_sha256") != _sha256_file(status)
        or status.read_bytes() != b""
        or head.read_bytes()
        != (str(outcome["output_commit"]) + "\n").encode("ascii")
    ):
        raise CanaryError("live capture receipt is invalid")


def _verify_inventory(root: Path, expected: object) -> None:
    if not isinstance(expected, list) or expected != _inventory(root):
        raise CanaryError("artifact inventory mismatch")


def verify(repo_root: Path, root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    root = root.resolve()
    summary_path = root / "canary-summary.json"
    summary = _load_json(summary_path)
    if summary_path.read_bytes() != _json_bytes(summary):
        raise CanaryError("canary summary is not canonical JSON")
    plan_path = root / "route-plan.json"
    plan = _load_json(plan_path)
    implementation = plan.get("implementation")
    if (
        not isinstance(implementation, dict)
        or summary.get("implementation") != implementation
        or _implementation_identity(
            repo_root,
            commit=implementation.get("commit"),
        )
        != implementation
    ):
        raise CanaryError("implementation commit identity is invalid")
    expected_frozen_route = {
        "cli_version": DEFAULT_CLI_VERSION,
        "comp_hash": DEFAULT_COMP_HASH,
        "launcher_implementation_sha256": _sha256_file(
            DEFAULT_SESSION_LAUNCHER
        ),
        "pair_runner_implementation_sha256": _sha256_file(
            DEFAULT_PAIR_RUNNER
        ),
        "model": DEFAULT_MODEL,
        "model_build": (
            f"codex:{DEFAULT_MODEL}:comp_hash={DEFAULT_COMP_HASH}:"
            f"cli={DEFAULT_CLI_VERSION}"
        ),
        "producer_git_identity": PRODUCER_GIT_IDENTITY,
        "reasoning": DEFAULT_REASONING,
    }
    if (
        summary.get("schema") != SUMMARY_SCHEMA
        or summary.get("authorization") != AUTHORIZATION
        or summary.get("rehearsal_kind") != REHEARSAL_KIND
        or summary.get("candidate_manifest_sha256")
        != EXPECTED_CANDIDATE_MANIFEST_SHA256
        or summary.get("harness_implementation_sha256")
        != _sha256_file(Path(__file__))
        or summary.get("launcher_implementation_sha256")
        != _sha256_file(DEFAULT_SESSION_LAUNCHER)
        or summary.get("pair_runner_implementation_sha256")
        != _sha256_file(DEFAULT_PAIR_RUNNER)
        or summary.get("tests_implementation_sha256")
        != _sha256_file(DEFAULT_TESTS)
        or summary.get("route_plan_sha256") != _sha256_file(plan_path)
        or plan.get("schema") != ROUTE_PLAN_SCHEMA
        or plan.get("frozen_route") != summary.get("frozen_route")
        or plan.get("frozen_route") != expected_frozen_route
        or plan.get("credential_contract") != CREDENTIAL_CONTRACT
        or summary.get("credential_contract") != CREDENTIAL_CONTRACT
        or plan.get("privacy") != summary.get("privacy")
        or plan.get("privacy", {}).get("sanitizer_rules_sha256")
        != _sanitizer_rules_sha256()
        or plan.get("context_contract", {}).get("provider") != DEFAULT_PROVIDER
        or plan.get("context_contract", {}).get("public_context_tokens")
        != PUBLIC_CONTEXT_TOKENS
    ):
        raise CanaryError("canary summary identity is invalid")
    candidate_checks = _validate_candidate(repo_root)
    if summary.get("candidate_verification_checks") != candidate_checks:
        raise CanaryError("candidate verification count mismatch")
    _verify_inventory(root, summary.get("artifact_inventory"))
    public_file_count = verify_public_privacy(root)
    _verify_credential_receipt(
        root,
        summary.get("credential_runner_receipt"),
        plan_path,
    )
    baseline_commit = _verify_baseline(
        root, summary.get("baseline_test_receipt")
    )
    if baseline_commit != plan.get("baseline_commit"):
        raise CanaryError("baseline receipt is not bound to route plan")
    contract_path = repo_root / DEFAULT_CONTRACT.relative_to(
        EXPERIMENT_ROOT.parents[2]
    )
    contract, _ = chain.load_contract(contract_path)
    chain_result = chain.verify_chain(
        root / "chain", contract_path, require_state="mapping_released"
    )
    if summary.get("chain") != {
        "event_count": chain_result["event_count"],
        "head_sha256": chain_result["head_sha256"],
        "state": chain_result["state"],
    }:
        raise CanaryError("chain summary mismatch")
    outcomes = summary.get("outcomes")
    if (
        not isinstance(outcomes, list)
        or len(outcomes) != 2
        or {item.get("anon_id") for item in outcomes} != set(ANON_MAPPING)
    ):
        raise CanaryError("outcome population is invalid")
    routes = []
    for outcome in outcomes:
        packet_path = _source(outcome.get("packet_path"), root)
        metrics_path = _source(outcome.get("metrics_path"), root)
        admission_path = _source(outcome.get("admission_path"), root)
        metrics = chain.validate_metrics(
            _load_json(metrics_path),
            contract,
            packet_sha256=_sha256_file(packet_path),
        )
        admission = chain.validate_admission(
            admission_path,
            packet_path,
            metrics,
            contract,
            root / "chain",
        )
        if (
            admission["anon_id"] != outcome["anon_id"]
            or admission["treatment"] != outcome["treatment"]
            or admission["output_commit"] != outcome["output_commit"]
            or admission["baseline_commit"] != baseline_commit
            or admission["model_build"] != plan["frozen_route"]["model_build"]
        ):
            raise CanaryError("outcome summary mismatch")
        routes.append(_verify_route_receipt(root, outcome, plan))
        _verify_capture(root, outcome, admission, plan)
        bundle_entry = admission.get("git_bundle")
        if not isinstance(bundle_entry, dict):
            raise CanaryError("git bundle admission entry is absent")
        bundle = _source(bundle_entry.get("path"), root)
        if bundle_entry.get("sha256") != _sha256_file(bundle):
            raise CanaryError("git bundle digest mismatch")
        _verify_bundle_commit_identities(
            bundle,
            baseline_commit=baseline_commit,
            output_commit=outcome["output_commit"],
            producer_identity=plan["frozen_route"]["producer_git_identity"],
        )
    if len({route["session_id"] for route in routes}) != 2:
        raise CanaryError("A/B context identities are not distinct")
    if (
        routes[0]["permission_fingerprint"]
        != routes[1]["permission_fingerprint"]
    ):
        raise CanaryError("A/B permission fingerprints differ")
    if (
        routes[0]["context_identity_sha256"]
        != routes[1]["context_identity_sha256"]
        or routes[0]["_source_context_identity_sha256"]
        != routes[1]["_source_context_identity_sha256"]
    ):
        raise CanaryError("A/B public or source context identities differ")
    return {
        "candidate_manifest_sha256": EXPECTED_CANDIDATE_MANIFEST_SHA256,
        "checks": {
            "artifact_inventory": "PASS",
            "baseline_failure_receipt": "PASS",
            "bundle_commit_identity": "PASS",
            "candidate_exact_bytes": "PASS",
            "chain": "PASS",
            "commit_diff_receipt_binding": "PASS",
            "credential_preflight": "PASS",
            "fresh_context_identity": "PASS",
            "model_build_identity": "PASS",
            "privacy_safe_public_evidence": "PASS",
            "prompt_identity": "PASS",
            "tool_input_contract": "PASS",
        },
        "event_count": chain_result["event_count"],
        "model_build": plan["frozen_route"]["model_build"],
        "outcome_count": len(outcomes),
        "public_file_count": public_file_count,
        "status": "PASS",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--repo-root", required=True)
    prep.add_argument("--staging-root", required=True)
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--model", default=DEFAULT_MODEL)
    prep.add_argument("--comp-hash", default=DEFAULT_COMP_HASH)
    prep.add_argument("--cli-version", default=DEFAULT_CLI_VERSION)
    prep.add_argument("--reasoning", default=DEFAULT_REASONING)
    orchestrate_parser = sub.add_parser("orchestrate")
    orchestrate_parser.add_argument("--repo-root", required=True)
    orchestrate_parser.add_argument("--out", required=True)
    orchestrate_parser.add_argument("--run-id", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--repo-root", required=True)
    verify_parser.add_argument("--canary-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                Path(args.repo_root),
                Path(args.staging_root),
                run_id=args.run_id,
                model=args.model,
                comp_hash=args.comp_hash,
                cli_version=args.cli_version,
                reasoning=args.reasoning,
            )
        elif args.command == "orchestrate":
            result = orchestrate(
                Path(args.repo_root),
                Path(args.out),
                run_id=args.run_id,
            )
        else:
            result = verify(
                Path(args.repo_root), Path(args.canary_root)
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CanaryError, chain.EvidenceError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
