"""Proposed strict semantic-equivalence contract for frozen-route tool inputs.

NOT WIRED INTO ACCEPTANCE. The live route still admits exactly what
``SHELL_WRAPPER_RE`` and ``PATCH_WRAPPER_RE`` admit. Widening what the route
admits is a governance-surface change; this module exists so that change can be
reviewed against a written contract and a test suite instead of being argued
from a diff. Nothing here is called by ``gate3_codex_live_canary`` at runtime.

Why a contract at all
---------------------
Byte-exact acceptance is too brittle: key order, a space after a colon, quoted
keys, the result variable name and a trailing semicolon each fail the route
while changing nothing about what the call does. Broad parse-and-compare is too
loose in the other direction: comparing only the decoded command would admit
inputs carrying sandbox, approval-policy or login fields, which change what the
call is permitted to do.

The contract below takes the narrow middle. An input is equivalent to the
frozen route only if it is one awaited frozen-family call whose object argument
carries exactly the core fields, with the decoded values passing the same
validation the route already applies. Everything else is refused by name, so a
receipt says which rule refused it.

Tolerated cosmetic differences
------------------------------
Whitespace anywhere the grammar allows it; key order; quoted or bare object
keys; the result variable's name; a trailing semicolon; CRLF or LF line
endings.

Refused, each with its own reason code
--------------------------------------
Extra fields of any kind, including execution bounds; privilege, approval or
shell-semantics fields; more than one tool call; a tool outside the route; no
tool call; a non-object argument; a missing core field; and any decoded value
the route's own validation rejects.

The open decision
-----------------
``TOLERATED_FIELDS`` is empty. The corpus evidence says one field dominates the
rejected population by a wide margin: an execution bound, which does not change
which command runs or where, but does change whether it is allowed to finish.
Admitting it is the single highest-leverage relaxation available and it is an
owner decision, not a default. Adding a name to ``TOLERATED_FIELDS`` is a
governance-surface change and must go through review; the tests below pin the
empty default so that change cannot be made silently.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate3_codex_live_canary as live  # noqa: E402

CONTRACT_SCHEMA = "gate3-codex-wrapper-semantic-contract.v1"

# The fields that define what the call does. Both are required, and no other
# field is admitted unless it is listed in TOLERATED_FIELDS.
SEMANTIC_CORE_FIELDS = ("command", "workdir")

# Deliberately empty. See "The open decision" above. Anything added here widens
# what the route admits.
TOLERATED_FIELDS: tuple[str, ...] = ()

REFUSAL_REASONS = (
    "accepted",
    "not_single_frozen_call",
    "argument_not_object",
    "core_field_missing",
    "duplicate_field",
    "extra_field",
    "privilege_affecting_field",
    "value_rejected_by_route",
)

# Which refusal a non-core field earns. Naming these separately keeps a receipt
# honest: an execution bound and a sandbox grant are not the same finding.
PRIVILEGE_AFFECTING_FIELDS = (
    "justification",
    "login",
    "prefix_rule",
    "sandbox_permissions",
)

_OBJECT_ENTRY_RE = re.compile(
    r"\s*(?:(?P<bare>[A-Za-z_$][A-Za-z0-9_$]*)"
    r'|(?P<quoted>"(?:\\.|[^"\\])*"))\s*:\s*(?P<value>.*)\s*',
    re.DOTALL,
)


def _split_top_level(body: str) -> list[str] | None:
    """Split object body on top-level commas, respecting strings and nesting."""
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
    return [segment for segment in segments if segment.strip()]


def _object_fields(argument: str) -> dict[str, str] | None:
    """Return field name to raw value text, or None if not a plain object.

    Returns None rather than a partial result whenever the shape is anything
    the contract is not prepared to reason about, so an unparsed input can
    never be mistaken for one with no extra fields.
    """
    stripped = argument.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    segments = _split_top_level(stripped[1:-1])
    if segments is None:
        return None
    fields: dict[str, str] = {}
    for segment in segments:
        match = _OBJECT_ENTRY_RE.fullmatch(segment)
        if match is None:
            return None
        if match.group("bare") is not None:
            name = match.group("bare")
        else:
            try:
                name = live._decode_js_string(match.group("quoted"), label="key")
            except live.CanaryError:
                return None
        if name in fields:
            # Signalled to the caller as a duplicate rather than silently
            # letting the last value win, which is what JS would do.
            return {"__duplicate__": name}
        fields[name] = match.group("value").strip()
    return fields


def evaluate(source: str, *, expected_workspace: str) -> dict[str, Any]:
    """Judge one tool input against the contract. Never raises on input."""

    def verdict(reason: str, **extra: Any) -> dict[str, Any]:
        return {
            "accepted": reason == "accepted",
            "reason": reason,
            "schema": CONTRACT_SCHEMA,
            **extra,
        }

    rejection_class, _, _ = live._wrapper_rejection_class(source)
    if rejection_class != "single_frozen_call":
        return verdict("not_single_frozen_call", rejection_class=rejection_class)
    markers = live._tool_call_markers(source)
    if len(markers) != 1:
        return verdict("not_single_frozen_call", rejection_class=rejection_class)
    family = markers[0][2]
    argument_result = live._tool_call_argument(source, markers[0])
    if argument_result is None:
        return verdict("argument_not_object", tool_family=family)

    if family == "apply_patch":
        # The route's patch form binds a string, not an object. Reuse its own
        # validation rather than inventing a second notion of a valid patch.
        try:
            patch = live._decode_js_string(argument_result[0].strip(), label="patch")
            live._validate_patch(patch, expected_workspace=expected_workspace)
        except live.CanaryError as error:
            return verdict(
                "value_rejected_by_route",
                tool_family=family,
                detail=str(error),
            )
        return verdict("accepted", tool_family=family)

    fields = _object_fields(argument_result[0])
    if fields is None:
        return verdict("argument_not_object", tool_family=family)
    if "__duplicate__" in fields:
        return verdict("duplicate_field", tool_family=family)
    missing = [name for name in SEMANTIC_CORE_FIELDS if name not in fields]
    if missing:
        return verdict(
            "core_field_missing", tool_family=family, missing=sorted(missing)
        )
    allowed = set(SEMANTIC_CORE_FIELDS) | set(TOLERATED_FIELDS)
    extra = sorted(set(fields) - allowed)
    privileged = [name for name in extra if name in PRIVILEGE_AFFECTING_FIELDS]
    if privileged:
        return verdict(
            "privilege_affecting_field",
            tool_family=family,
            fields=sorted(privileged),
        )
    if extra:
        return verdict("extra_field", tool_family=family, fields=extra)
    try:
        detail = live._validate_shell_command(
            live._decode_js_string(fields["command"], label="command"),
            workdir=live._decode_js_string(fields["workdir"], label="workdir"),
            expected_workspace=expected_workspace,
        )
    except live.CanaryError as error:
        return verdict(
            "value_rejected_by_route", tool_family=family, detail=str(error)
        )
    return verdict("accepted", tool_family=family, detail=detail)
