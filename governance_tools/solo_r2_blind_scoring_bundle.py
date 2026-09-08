"""Stdlib-only scorer-visible bundle boundary for Solo Evaluation R2.

This module has no controller, ledger, cryptography, key, sealed-package, or
execution-chronology dependency.  Presentation order is derived only from the
explicit presentation entropy accepted by the builder.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping
import unicodedata
from uuid import UUID

from governance_tools.solo_r2_random_domains import (
    RandomDomainError,
    SAMPLING_ROLE,
    presentation_order_bit_from_entropy,
)


BUNDLE_SCHEMA = "solo_blind_scoring_bundle.v2"
BUNDLE_ARTIFACT_TYPE = "blind_scoring_bundle"
BUNDLE_SCHEMA_FAILURE = "BLIND_SCORING_BUNDLE_SCHEMA_FAILURE / STOP"
_SLOTS = frozenset({"R2-SHAKEDOWN", "A1", "A2", "A3", "A4", "A5", "A6"})
_BUNDLE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "rubric_id",
        "presentation_order",
        "outputs",
    }
)
_OUTPUT_KEYS = frozenset({"presentation_key", "output_payload"})
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_LIFECYCLE_IDENTITY_TOKEN = re.compile(r"[0-9a-f]{64}")
_JSON_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-f]{4})", re.IGNORECASE)
_ARM_IDENTITY_TOKEN = re.compile(
    r"(?<![a-z0-9_])(?:control|treatment)(?![a-z0-9_])"
)
# Free-text custody joins observed outside the closed metadata key set.
_ABSOLUTE_CUSTODY_PATH = re.compile(
    r"(?<![a-z0-9_])[a-z]:[/\\]"
    r"|(?<![a-z0-9_\\])\\\\[a-z0-9_.-]+\\"
    r"|(?<![a-z0-9_.:/])/(?:[a-z0-9_.-]+/)+[a-z0-9_.-]+"
)
_EXECUTION_ORDINAL = re.compile(
    r"\b(?:execution|attempt)[ _-]+(?:ordinal[ _-]+)?#?\d+\b"
    r"|\brun(?:[-_]+|\s+(?:ordinal\s+|#))\d+\b"
    r"|\b(?:first|second|1st|2nd)[ _-]+(?:execution|attempt|run)\b"
)
_PERCENT_ASCII_ESCAPE = re.compile(r"%([0-7][0-9a-f])", re.IGNORECASE)
_FORBIDDEN_JOIN_KEYS = (
    "attempt_handle",
    "event_seq",
    "timestamp_utc",
    "filesystem_path",
    "output_hash",
    "attempt_commit",
    "result_branch",
    "arm",
    "skill_identity",
    "first_marker",
    "second_marker",
    "execution_order",
    "sealed_package_digest",
)
_STRUCTURED_JOIN_FIELD = re.compile(
    r"(?<![a-z0-9_])[\"']?(?:"
    + "|".join(re.escape(key) for key in _FORBIDDEN_JOIN_KEYS)
    + r")[\"']?\s*[:=]"
)


class BlindScoringBundleError(RuntimeError):
    """Fail-closed bundle error carrying only one fixed public code."""

    def __init__(self, code: str = BUNDLE_SCHEMA_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail() -> None:
    raise BlindScoringBundleError() from None


def _is_uuid4(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _is_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value)


def _is_scoring_label(value: object) -> bool:
    return type(value) is str and _LOWER_HEX_64.fullmatch(value) is not None


def _require_exact_dict(value: object, keys: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail()
    return value


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _decode_json_ascii_escapes(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        codepoint = int(match.group(1), 16)
        return chr(codepoint) if codepoint <= 0x7F else match.group(0)

    decoded = value
    while True:
        next_value = _JSON_UNICODE_ESCAPE.sub(replace, decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value


def _contains_scorer_forbidden_identity(value: str) -> bool:
    """Detect canonical lifecycle identity material and bounded wrappers."""

    normalized = unicodedata.normalize("NFKC", value)
    views = {
        normalized.casefold(),
        _decode_json_ascii_escapes(normalized).casefold(),
    }
    # Decode bounded ASCII wrappers used by JSON and Markdown link destinations.
    decoded = normalized
    while True:
        unwrapped = _decode_json_ascii_escapes(decoded)
        unwrapped = _PERCENT_ASCII_ESCAPE.sub(
            lambda match: chr(int(match.group(1), 16)), unwrapped
        )
        unwrapped = unwrapped.replace(r"\/", "/")
        unwrapped = unwrapped.replace(r"\-", "-").replace(r"\_", "_")
        if unwrapped == decoded:
            break
        decoded = unwrapped
    views.add(decoded.casefold())
    return any(
        _LIFECYCLE_IDENTITY_TOKEN.search(view) is not None
        or _STRUCTURED_JOIN_FIELD.search(view) is not None
        or _ARM_IDENTITY_TOKEN.search(view) is not None
        or _ABSOLUTE_CUSTODY_PATH.search(view) is not None
        or _EXECUTION_ORDINAL.search(view) is not None
        for view in views
    )


def validate_blind_scoring_bundle(value: object) -> dict[str, Any]:
    """Validate one exact scorer-visible L09 bundle."""

    bundle = _require_exact_dict(value, _BUNDLE_KEYS)
    if (
        bundle["schema_version"] != BUNDLE_SCHEMA
        or bundle["artifact_type"] != BUNDLE_ARTIFACT_TYPE
        or not _is_uuid4(bundle["evaluation_id"])
        or not _is_nonempty_string(bundle["pair_id"])
        or bundle["slot"] not in _SLOTS
        or not _is_nonempty_string(bundle["rubric_id"])
    ):
        _fail()

    presentation = bundle["presentation_order"]
    outputs = bundle["outputs"]
    if (
        type(presentation) is not list
        or len(presentation) != 2
        or any(not _is_scoring_label(label) for label in presentation)
        or len(set(presentation)) != 2
        or type(outputs) is not list
        or len(outputs) != 2
    ):
        _fail()

    output_keys: list[str] = []
    for raw in outputs:
        output = _require_exact_dict(raw, _OUTPUT_KEYS)
        presentation_key = output["presentation_key"]
        output_payload = output["output_payload"]
        if not _is_scoring_label(presentation_key) or not _is_nonempty_string(
            output_payload
        ):
            _fail()
        try:
            output_payload.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            _fail()
        if _contains_scorer_forbidden_identity(output_payload):
            _fail()
        output_keys.append(presentation_key)
    if output_keys != presentation:
        _fail()
    return bundle


def build_blind_scoring_bundle(
    *,
    evaluation_id: str,
    pair_id: str,
    slot: str,
    rubric_id: str,
    outputs_by_label: Mapping[str, str],
    presentation_entropy: bytes,
) -> dict[str, Any]:
    """Build a bundle without accepting execution-order or lifecycle inputs."""

    if not isinstance(outputs_by_label, Mapping) or len(outputs_by_label) != 2:
        _fail()
    labels = list(outputs_by_label)
    if len(labels) != 2 or any(not _is_scoring_label(label) for label in labels):
        _fail()
    labels.sort()
    try:
        order_bit = presentation_order_bit_from_entropy(presentation_entropy)
    except RandomDomainError:
        _fail()
    presentation_order = labels if order_bit == 0 else list(reversed(labels))
    bundle = {
        "schema_version": BUNDLE_SCHEMA,
        "artifact_type": BUNDLE_ARTIFACT_TYPE,
        "evaluation_id": evaluation_id,
        "pair_id": pair_id,
        "slot": slot,
        "rubric_id": rubric_id,
        "presentation_order": presentation_order,
        "outputs": [
            {
                "presentation_key": label,
                "output_payload": outputs_by_label[label],
            }
            for label in presentation_order
        ],
    }
    return validate_blind_scoring_bundle(bundle)


def encode_blind_scoring_bundle(value: object) -> bytes:
    """Encode one validated scorer bundle as canonical UTF-8 plus ASCII LF."""

    bundle = validate_blind_scoring_bundle(value)
    try:
        encoded = json.dumps(
            bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail()
    if encoded.startswith(b"\xef\xbb\xbf") or b"\r" in encoded:
        _fail()
    return encoded + b"\n"


def parse_blind_scoring_bundle(bundle_bytes: object) -> dict[str, Any]:
    """Parse only the exact canonical scorer-bundle representation."""

    if (
        type(bundle_bytes) is not bytes
        or not bundle_bytes.endswith(b"\n")
        or bundle_bytes.startswith(b"\xef\xbb\xbf")
        or b"\r" in bundle_bytes
    ):
        _fail()
    try:
        decoded = bundle_bytes[:-1].decode("utf-8", errors="strict")
        value = json.loads(decoded, object_pairs_hook=_pairs_without_duplicates)
    except BlindScoringBundleError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        _fail()
    bundle = validate_blind_scoring_bundle(value)
    if encode_blind_scoring_bundle(bundle) != bundle_bytes:
        _fail()
    return bundle
