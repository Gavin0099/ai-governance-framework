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

Tolerating a field by name alone would not be a small relaxation. An execution
bound admitted by name accepts a negative value, a zero, an absurd value, a
string, or a call expression evaluated at runtime -- none of which are the
frozen route. So a name in ``TOLERATED_FIELDS`` is inert unless
``TOLERATED_FIELD_VALUES`` also carries an exact preregistered integer for it,
and the literal in the input must equal that integer.

The declaration is validated too, not just the input. ``bool`` is a subclass of
``int``, so ``True`` would pass a naive type check and then match a literal
``1``; a negative or zero execution bound is not a bound; and an absurd one is
no different from having none. A declaration that fails validation leaves the
field un-tolerated, so a misconfiguration narrows what is accepted rather than
widening it. The admitted numeric form is plain decimal only: no sign, no
leading zeros, no underscores, no hex, no float.

Two preconditions must be satisfied before any field is tolerated, and neither
is implemented here because neither belongs to a proposal:

* the tolerated value must be preregistered, and absence of the field is
  equivalent only if the CLI default is itself pinned to that same value;
* the value must enter the route and context digests and the A/B identity
  comparison, so the two arms cannot silently differ on it.
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
# what the route admits, and a name alone is not enough to admit a field: it
# must also appear in TOLERATED_FIELD_VALUES with an exact required value.
TOLERATED_FIELDS: tuple[str, ...] = ()

# Exact value required for each tolerated field. A name-only allowance would
# admit any value: for an execution bound that means a negative number, a zero,
# an absurd number, a string, or a call expression evaluated at runtime. None
# means no value has been preregistered, so the field cannot be tolerated even
# if someone adds its name above.
TOLERATED_FIELD_VALUES: dict[str, int | None] = {
    "timeout_ms": None,
}

# Bounds on what may be preregistered, checked on the declaration itself and
# not only on the input. Without this the declaration is the weak link: bool is
# a subclass of int, so True would sail through an isinstance check and then
# match a literal 1; a negative or zero bound is not an execution bound; and an
# absurd bound is indistinguishable from none at all.
#
# This is a contract-level sanity range, not a claim about what the CLI itself
# accepts. Confirming the chosen value against the CLI is part of
# preregistering it.
TOLERATED_FIELD_RANGES: dict[str, tuple[int, int]] = {
    "timeout_ms": (1, 3_600_000),
}

# Wrapper forms whose prefix, suffix and result consumer the route already
# validates end to end. Anything else is not a wrapper this contract will
# reason about, however familiar its middle looks.
VALIDATED_ENVELOPES = (
    "const_await_then_text",
    "direct_await_text",
    "bound_argument_then_direct_await_text",
)

REFUSAL_REASONS = (
    "accepted",
    "not_single_frozen_call",
    "envelope_not_validated",
    "argument_not_object",
    "core_field_missing",
    "duplicate_field",
    "extra_field",
    "privilege_affecting_field",
    "tolerated_field_value_rejected",
    "value_rejected_by_route",
)

# The only numeric form admitted: plain decimal, no sign, no leading zeros, no
# underscores, no hex, no float. A signed or zero-padded literal parses to the
# same number but is not a form the frozen route emits, and admitting more
# spellings than necessary buys nothing.
_INTEGER_LITERAL_RE = re.compile(r"0|[1-9]\d*")


def preregistered_value(name: str) -> int | None:
    """Return the declared value for a field, or None if it is not usable.

    Validates the declaration, not the input. A declaration that fails here
    leaves the field un-tolerated, which is the safe direction: a
    misconfiguration narrows what is accepted rather than widening it.
    """
    value = TOLERATED_FIELD_VALUES.get(name)
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        return None
    bounds = TOLERATED_FIELD_RANGES.get(name)
    if bounds is None:
        return None
    low, high = bounds
    if not low <= value <= high:
        return None
    return value

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
    # Finding one call and reading its argument says nothing about what
    # surrounds it. Without this, a leading statement, a wrong consumer or a
    # truncated input all pass: the middle looks right and nothing checks the
    # rest. Reuse the route's own end-to-end envelope classification.
    envelope = live._tool_input_wrapper_diagnostic(source)["envelope"]
    if envelope not in VALIDATED_ENVELOPES:
        return verdict(
            "envelope_not_validated", tool_family=family, envelope=envelope
        )
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
    for name in sorted(set(fields) & set(TOLERATED_FIELDS)):
        required = preregistered_value(name)
        if required is None:
            return verdict(
                "tolerated_field_value_rejected",
                tool_family=family,
                fields=[name],
                detail="no usable preregistered value",
            )
        literal = fields[name].strip()
        if not _INTEGER_LITERAL_RE.fullmatch(literal) or int(literal) != required:
            return verdict(
                "tolerated_field_value_rejected",
                tool_family=family,
                fields=[name],
                detail="value is not the preregistered integer",
            )
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
