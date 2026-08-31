"""Synthetic-only sealed controller-state boundary for Solo Evaluation R2.

This module owns the secret-bearing representation and AES-256-GCM operations.
It does not write lifecycle events, create the canonical ledger, score, or
authorize unblinding.  Callers must supply an explicit repo-external key path.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from governance_tools.solo_attempt_ledger_v2 import (
    ADOPTED_CONTRACT_SHA256,
    ADOPTED_PROTOCOL_SHA256,
    SLOTS,
)
from governance_tools.solo_r2_random_domains import arm_order_from_entropy


CONTROLLER_STATE_SCHEMA = "solo_sealed_controller_state.v2"
CONTROLLER_ARTIFACT_TYPE = "sealed_controller_state"
SEALED_PACKAGE_SCHEMA = "solo_aead_package.v2"
CONTROLLER_KEY_SCHEMA = "solo_controller_key.v2"

ORDER_FROZEN = "ORDER_FROZEN"
ATTEMPT_BOUND = "ATTEMPT_BOUND"
SCORING_BOUND = "SCORING_BOUND"

KEY_CUSTODY_FAILURE = "KEY_CUSTODY_FAILURE / STOP"
KEY_MATERIAL_FAILURE = "KEY_MATERIAL_FAILURE / STOP"
CONTROLLER_STATE_SCHEMA_FAILURE = "CONTROLLER_STATE_SCHEMA_FAILURE / STOP"
SEALING_FAILURE = "SEALING_FAILURE / STOP"
AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE / STOP"
SEALED_PACKAGE_SCHEMA_FAILURE = "SEALED_PACKAGE_SCHEMA_FAILURE / STOP"

_STATE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "state_phase",
        "realized_order",
        "order_entropy",
        "attempt_bindings",
        "scoring_bindings",
        "presentation_order",
        "attempt_output_refs",
    }
)
_ATTEMPT_BINDING_KEYS = frozenset({"attempt_handle", "arm"})
_SCORING_BINDING_KEYS = frozenset({"scoring_label", "attempt_handle"})
_OUTPUT_REF_KEYS = frozenset({"attempt_handle", "output_ref"})
_AAD_KEYS = frozenset(
    {
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "schema_version",
        "protocol_sha256",
        "contract_sha256",
    }
)
_PACKAGE_KEYS = frozenset(
    {
        "package_schema",
        "artifact_type",
        "key_id",
        "nonce_b64",
        "aad_utf8_b64",
        "ciphertext_b64",
        "tag_b64",
    }
)
_KEY_RECORD_KEYS = frozenset({"schema_version", "key_id", "key_b64"})
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_KEY_ID = re.compile(r"solo-r2-[0-9a-f]{32}\Z")
_AES_KEY_BYTES = 32
_NONCE_BYTES = 12
_TAG_BYTES = 16


class ControllerStateError(RuntimeError):
    """Fail-closed controller error carrying only one fixed public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class _ControllerKey:
    key_id: str
    key_bytes: bytes


@dataclass(frozen=True)
class CustodyBoundary:
    governance_root: Path
    consumer_root: Path
    materialization_root: Path
    execution_root: Path
    scoring_root: Path

    def roots(self) -> tuple[Path, ...]:
        """Return all roots from which controller key material is excluded."""

        return (
            self.governance_root,
            self.consumer_root,
            self.materialization_root,
            self.execution_root,
            self.scoring_root,
        )


@dataclass(frozen=True)
class SealedControllerPackage:
    package_bytes: bytes
    sealed_package_digest: str


@dataclass(frozen=True)
class ValidatedControllerSnapshot:
    """Immutable canonical state bytes approved for sealing."""

    canonical_state_bytes: bytes
    aad_bytes: bytes
    state_sha256: str


def _fail(code: str) -> None:
    raise ControllerStateError(code) from None


def _is_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value)


def _is_uuid4(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _is_lower_hex_64(value: object) -> bool:
    return type(value) is str and _LOWER_HEX_64.fullmatch(value) is not None


def _require_exact_dict(
    value: object, keys: frozenset[str], code: str
) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _decode_canonical_base64(value: object, code: str) -> bytes:
    if type(value) is not str:
        _fail(code)
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        _fail(code)
    if base64.b64encode(decoded).decode("ascii") != value:
        _fail(code)
    return decoded


def _encode_base64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _json_bytes(value: Mapping[str, Any], *, trailing_lf: bool) -> bytes:
    try:
        encoded = json.dumps(
            dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return encoded + (b"\n" if trailing_lf else b"")


def _pairs_hook(code: str):
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(code)
            result[key] = value
        return result

    return reject_duplicates


def _parse_json_object(data: bytes, code: str) -> dict[str, Any]:
    try:
        decoded = data.decode("utf-8", errors="strict")
        value = json.loads(decoded, object_pairs_hook=_pairs_hook(code))
    except ControllerStateError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        _fail(code)
    if type(value) is not dict:
        _fail(code)
    return value


def _validate_attempt_bindings(
    value: object, realized_order: Sequence[str], expected_count: set[int]
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) not in expected_count:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    bindings: list[dict[str, Any]] = []
    handles: set[str] = set()
    arms: list[str] = []
    for raw in value:
        binding = _require_exact_dict(
            raw, _ATTEMPT_BINDING_KEYS, CONTROLLER_STATE_SCHEMA_FAILURE
        )
        handle = binding["attempt_handle"]
        arm = binding["arm"]
        if not _is_lower_hex_64(handle) or arm not in {"CONTROL", "TREATMENT"}:
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
        if handle in handles:
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
        handles.add(handle)
        arms.append(arm)
        bindings.append(binding)
    if len(set(arms)) != len(arms) or arms != list(realized_order[: len(arms)]):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return bindings


def _validate_scoring_bound_components(
    state: Mapping[str, Any], attempt_bindings: Sequence[Mapping[str, Any]]
) -> None:
    scoring_raw = state["scoring_bindings"]
    presentation_raw = state["presentation_order"]
    output_raw = state["attempt_output_refs"]
    if (
        type(scoring_raw) is not list
        or len(scoring_raw) != 2
        or type(presentation_raw) is not list
        or len(presentation_raw) != 2
        or type(output_raw) is not list
        or len(output_raw) != 2
    ):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)

    attempt_handles = {binding["attempt_handle"] for binding in attempt_bindings}
    scoring_handles: set[str] = set()
    labels: set[str] = set()
    for raw in scoring_raw:
        binding = _require_exact_dict(
            raw, _SCORING_BINDING_KEYS, CONTROLLER_STATE_SCHEMA_FAILURE
        )
        label = binding["scoring_label"]
        handle = binding["attempt_handle"]
        if not _is_lower_hex_64(label) or not _is_lower_hex_64(handle):
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
        labels.add(label)
        scoring_handles.add(handle)
    if len(labels) != 2 or scoring_handles != attempt_handles:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    if (
        any(not _is_lower_hex_64(label) for label in presentation_raw)
        or len(set(presentation_raw)) != 2
        or set(presentation_raw) != labels
    ):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)

    output_handles: set[str] = set()
    output_refs: set[str] = set()
    for raw in output_raw:
        binding = _require_exact_dict(
            raw, _OUTPUT_REF_KEYS, CONTROLLER_STATE_SCHEMA_FAILURE
        )
        handle = binding["attempt_handle"]
        output_ref = binding["output_ref"]
        if not _is_lower_hex_64(handle) or not _is_nonempty_string(output_ref):
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
        output_handles.add(handle)
        output_refs.add(output_ref)
    if output_handles != attempt_handles or len(output_refs) != 2:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)


def validate_controller_state(value: object) -> dict[str, Any]:
    """Validate and return one closed, synthetic controller-state object."""

    state = _require_exact_dict(value, _STATE_KEYS, CONTROLLER_STATE_SCHEMA_FAILURE)
    if (
        state["schema_version"] != CONTROLLER_STATE_SCHEMA
        or state["artifact_type"] != CONTROLLER_ARTIFACT_TYPE
        or not _is_uuid4(state["evaluation_id"])
        or not _is_nonempty_string(state["pair_id"])
        or state["slot"] not in SLOTS
    ):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)

    realized_order = state["realized_order"]
    if (
        type(realized_order) is not list
        or len(realized_order) != 2
        or any(type(arm) is not str for arm in realized_order)
        or set(realized_order) != {"CONTROL", "TREATMENT"}
    ):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    entropy = _decode_canonical_base64(
        state["order_entropy"], CONTROLLER_STATE_SCHEMA_FAILURE
    )
    if len(entropy) != 32 or list(arm_order_from_entropy(entropy)) != realized_order:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)

    phase = state["state_phase"]
    if phase == ORDER_FROZEN:
        attempt_bindings = _validate_attempt_bindings(state["attempt_bindings"], realized_order, {0})
        if any(
            type(state[key]) is not list or state[key]
            for key in (
                "scoring_bindings",
                "presentation_order",
                "attempt_output_refs",
            )
        ):
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    elif phase == ATTEMPT_BOUND:
        attempt_bindings = _validate_attempt_bindings(state["attempt_bindings"], realized_order, {1, 2})
        if any(
            type(state[key]) is not list or state[key]
            for key in (
                "scoring_bindings",
                "presentation_order",
                "attempt_output_refs",
            )
        ):
            _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    elif phase == SCORING_BOUND:
        attempt_bindings = _validate_attempt_bindings(state["attempt_bindings"], realized_order, {2})
        _validate_scoring_bound_components(state, attempt_bindings)
    else:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return state


def validate_state_transition(
    previous: object, current: object
) -> ValidatedControllerSnapshot:
    """Validate one forward transition and freeze its exact resulting bytes."""

    old_snapshot = freeze_controller_state(previous)
    new_snapshot = freeze_controller_state(current)
    old = _parse_json_object(
        old_snapshot.canonical_state_bytes, CONTROLLER_STATE_SCHEMA_FAILURE
    )
    new = _parse_json_object(
        new_snapshot.canonical_state_bytes, CONTROLLER_STATE_SCHEMA_FAILURE
    )
    immutable_keys = (
        "schema_version",
        "artifact_type",
        "evaluation_id",
        "pair_id",
        "slot",
        "realized_order",
        "order_entropy",
    )
    if any(old[key] != new[key] for key in immutable_keys):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    old_bindings = old["attempt_bindings"]
    new_bindings = new["attempt_bindings"]
    if new_bindings[: len(old_bindings)] != old_bindings:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    allowed = {
        (ORDER_FROZEN, ATTEMPT_BOUND, 0, 1),
        (ATTEMPT_BOUND, ATTEMPT_BOUND, 1, 2),
        (ATTEMPT_BOUND, SCORING_BOUND, 2, 2),
    }
    transition = (
        old["state_phase"],
        new["state_phase"],
        len(old_bindings),
        len(new_bindings),
    )
    if transition not in allowed:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return new_snapshot


def _build_controller_aad_from_validated(state: Mapping[str, Any]) -> bytes:
    aad = {
        "artifact_type": CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": state["evaluation_id"],
        "pair_id": state["pair_id"],
        "slot": state["slot"],
        "schema_version": CONTROLLER_STATE_SCHEMA,
        "protocol_sha256": ADOPTED_PROTOCOL_SHA256,
        "contract_sha256": ADOPTED_CONTRACT_SHA256,
    }
    if frozenset(aad) != _AAD_KEYS:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return _json_bytes(aad, trailing_lf=False)


def freeze_controller_state(value: object) -> ValidatedControllerSnapshot:
    """Detach one valid mutable state into an immutable canonical snapshot."""

    if type(value) is not dict:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    canonical_state_bytes = _json_bytes(value, trailing_lf=False)
    detached = _parse_json_object(
        canonical_state_bytes, CONTROLLER_STATE_SCHEMA_FAILURE
    )
    validated = validate_controller_state(detached)
    if _json_bytes(validated, trailing_lf=False) != canonical_state_bytes:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return ValidatedControllerSnapshot(
        canonical_state_bytes=canonical_state_bytes,
        aad_bytes=_build_controller_aad_from_validated(validated),
        state_sha256=hashlib.sha256(canonical_state_bytes).hexdigest(),
    )


def _validate_controller_snapshot(
    value: object,
) -> ValidatedControllerSnapshot:
    if type(value) is not ValidatedControllerSnapshot:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    if (
        type(value.canonical_state_bytes) is not bytes
        or type(value.aad_bytes) is not bytes
        or not _is_lower_hex_64(value.state_sha256)
        or hashlib.sha256(value.canonical_state_bytes).hexdigest()
        != value.state_sha256
    ):
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    state = _parse_json_object(
        value.canonical_state_bytes, CONTROLLER_STATE_SCHEMA_FAILURE
    )
    validated = validate_controller_state(state)
    if _json_bytes(validated, trailing_lf=False) != value.canonical_state_bytes:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    if _build_controller_aad_from_validated(validated) != value.aad_bytes:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return value


def build_controller_aad(state: object) -> bytes:
    """Return the exact implementation-local UTF-8 AAD bytes for one state."""

    validated = validate_controller_state(state)
    return _build_controller_aad_from_validated(validated)


def _canonical_root(value: Path, code: str) -> Path:
    if not value.is_absolute():
        _fail(code)
    try:
        resolved = value.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail(code)
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _contains_git_marker(path: Path) -> bool:
    for ancestor in (path, *path.parents):
        marker = ancestor / ".git"
        try:
            marker.stat()
        except FileNotFoundError:
            continue
        except OSError:
            _fail(KEY_CUSTODY_FAILURE)
        else:
            return True
    return False


def _validate_key_path(path: Path | str, boundary: CustodyBoundary) -> Path:
    try:
        supplied = Path(path)
    except (TypeError, ValueError):
        _fail(KEY_CUSTODY_FAILURE)
    if not supplied.is_absolute():
        _fail(KEY_CUSTODY_FAILURE)
    candidate = _canonical_root(supplied, KEY_CUSTODY_FAILURE)
    if not candidate.is_file():
        _fail(KEY_CUSTODY_FAILURE)

    roots: list[Path] = []
    for raw_root in boundary.roots():
        try:
            root_path = Path(raw_root)
        except (TypeError, ValueError):
            _fail(KEY_CUSTODY_FAILURE)
        root = _canonical_root(root_path, KEY_CUSTODY_FAILURE)
        if not root.is_dir():
            _fail(KEY_CUSTODY_FAILURE)
        roots.append(root)

    try:
        lexical = supplied.absolute()
    except OSError:
        _fail(KEY_CUSTODY_FAILURE)
    if any(
        _is_within(candidate, root) or _is_within(lexical, root)
        for root in roots
    ):
        _fail(KEY_CUSTODY_FAILURE)
    if _contains_git_marker(candidate.parent) or _contains_git_marker(lexical.parent):
        _fail(KEY_CUSTODY_FAILURE)
    if not os.access(candidate, os.R_OK):
        _fail(KEY_CUSTODY_FAILURE)
    return candidate


def _require_single_link(file_stat: os.stat_result) -> None:
    if type(file_stat.st_nlink) is not int or file_stat.st_nlink != 1:
        _fail(KEY_CUSTODY_FAILURE)


def _read_custodied_key_file(path: Path | str, boundary: CustodyBoundary) -> bytes:
    """Validate and read one single-link key through the same opened object."""

    key_path = _validate_key_path(path, boundary)
    try:
        path_stat = key_path.stat()
        _require_single_link(path_stat)
        with key_path.open("rb") as key_file:
            opened_stat = os.fstat(key_file.fileno())
            if not os.path.samestat(path_stat, opened_stat):
                _fail(KEY_CUSTODY_FAILURE)
            _require_single_link(opened_stat)
            key_data = key_file.read()
            final_stat = os.fstat(key_file.fileno())
            if (
                not os.path.samestat(opened_stat, final_stat)
                or final_stat.st_size != len(key_data)
                or final_stat.st_size != opened_stat.st_size
                or final_stat.st_mtime_ns != opened_stat.st_mtime_ns
            ):
                _fail(KEY_CUSTODY_FAILURE)
            _require_single_link(final_stat)
    except ControllerStateError:
        raise
    except OSError:
        _fail(KEY_CUSTODY_FAILURE)
    return key_data


def _validate_controller_key(key: object) -> _ControllerKey:
    if type(key) is not _ControllerKey:
        _fail(KEY_MATERIAL_FAILURE)
    if _KEY_ID.fullmatch(key.key_id) is None:
        _fail(KEY_MATERIAL_FAILURE)
    if type(key.key_bytes) is not bytes or len(key.key_bytes) != _AES_KEY_BYTES:
        _fail(KEY_MATERIAL_FAILURE)
    return key


def _load_controller_key(
    path: Path | str,
    *,
    custody_boundary: CustodyBoundary,
    expected_key_id: str | None = None,
) -> _ControllerKey:
    """Load one explicit repo-external controller key without CWD fallback."""

    key_data = _read_custodied_key_file(path, custody_boundary)
    record = _parse_json_object(key_data, KEY_MATERIAL_FAILURE)
    _require_exact_dict(record, _KEY_RECORD_KEYS, KEY_MATERIAL_FAILURE)
    if record["schema_version"] != CONTROLLER_KEY_SCHEMA:
        _fail(KEY_MATERIAL_FAILURE)
    key_bytes = _decode_canonical_base64(record["key_b64"], KEY_MATERIAL_FAILURE)
    key = _validate_controller_key(_ControllerKey(record["key_id"], key_bytes))
    if expected_key_id is not None and key.key_id != expected_key_id:
        _fail(KEY_MATERIAL_FAILURE)
    return key


def seal_controller_state(
    snapshot: ValidatedControllerSnapshot,
    *,
    key_path: Path | str,
    custody_boundary: CustodyBoundary,
) -> SealedControllerPackage:
    """Seal one immutable snapshot; no file or lifecycle write occurs."""

    validated_snapshot = _validate_controller_snapshot(snapshot)
    controller_key = _load_controller_key(
        key_path, custody_boundary=custody_boundary
    )
    aad_bytes = validated_snapshot.aad_bytes
    plaintext_bytes = validated_snapshot.canonical_state_bytes
    try:
        nonce = os.urandom(_NONCE_BYTES)
        if type(nonce) is not bytes or len(nonce) != _NONCE_BYTES:
            _fail(SEALING_FAILURE)
        sealed = AESGCM(controller_key.key_bytes).encrypt(
            nonce, plaintext_bytes, aad_bytes
        )
    except ControllerStateError:
        raise
    except Exception:
        _fail(SEALING_FAILURE)
    if len(sealed) < _TAG_BYTES:
        _fail(SEALING_FAILURE)
    ciphertext, tag = sealed[:-_TAG_BYTES], sealed[-_TAG_BYTES:]
    if len(tag) != _TAG_BYTES:
        _fail(SEALING_FAILURE)
    envelope = {
        "package_schema": SEALED_PACKAGE_SCHEMA,
        "artifact_type": CONTROLLER_ARTIFACT_TYPE,
        "key_id": controller_key.key_id,
        "nonce_b64": _encode_base64(nonce),
        "aad_utf8_b64": _encode_base64(aad_bytes),
        "ciphertext_b64": _encode_base64(ciphertext),
        "tag_b64": _encode_base64(tag),
    }
    package_bytes = _json_bytes(envelope, trailing_lf=True)
    return SealedControllerPackage(
        package_bytes=package_bytes,
        sealed_package_digest=hashlib.sha256(package_bytes).hexdigest(),
    )


def parse_sealed_package(package_bytes: object) -> dict[str, Any]:
    """Validate one exact controller envelope without decrypting it."""

    if type(package_bytes) is not bytes or not package_bytes.endswith(b"\n"):
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    if package_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in package_bytes:
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    envelope = _parse_json_object(
        package_bytes[:-1], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    _require_exact_dict(envelope, _PACKAGE_KEYS, SEALED_PACKAGE_SCHEMA_FAILURE)
    if (
        envelope["package_schema"] != SEALED_PACKAGE_SCHEMA
        or envelope["artifact_type"] != CONTROLLER_ARTIFACT_TYPE
        or type(envelope["key_id"]) is not str
        or _KEY_ID.fullmatch(envelope["key_id"]) is None
    ):
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    nonce = _decode_canonical_base64(
        envelope["nonce_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    aad = _decode_canonical_base64(
        envelope["aad_utf8_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    _decode_canonical_base64(
        envelope["ciphertext_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    tag = _decode_canonical_base64(
        envelope["tag_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    if len(nonce) != _NONCE_BYTES or len(tag) != _TAG_BYTES:
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    if _json_bytes(envelope, trailing_lf=True) != package_bytes:
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    aad_object = _parse_json_object(aad, SEALED_PACKAGE_SCHEMA_FAILURE)
    _require_exact_dict(aad_object, _AAD_KEYS, SEALED_PACKAGE_SCHEMA_FAILURE)
    if _json_bytes(aad_object, trailing_lf=False) != aad:
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    return envelope


def open_controller_package(
    package_bytes: bytes,
    *,
    key_path: Path | str,
    custody_boundary: CustodyBoundary,
    expected_digest: str,
    expected_evaluation_id: str,
    expected_pair_id: str,
    expected_slot: str,
) -> dict[str, Any]:
    """Authenticate and open synthetic state without lifecycle unblinding."""

    envelope = parse_sealed_package(package_bytes)
    controller_key = _load_controller_key(
        key_path,
        custody_boundary=custody_boundary,
        expected_key_id=envelope["key_id"],
    )
    if not _is_lower_hex_64(expected_digest):
        _fail(SEALED_PACKAGE_SCHEMA_FAILURE)
    if hashlib.sha256(package_bytes).hexdigest() != expected_digest:
        _fail(AUTHENTICATION_FAILURE)
    aad = _decode_canonical_base64(
        envelope["aad_utf8_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    aad_object = _parse_json_object(aad, SEALED_PACKAGE_SCHEMA_FAILURE)
    expected_bindings = {
        "artifact_type": CONTROLLER_ARTIFACT_TYPE,
        "evaluation_id": expected_evaluation_id,
        "pair_id": expected_pair_id,
        "slot": expected_slot,
        "schema_version": CONTROLLER_STATE_SCHEMA,
        "protocol_sha256": ADOPTED_PROTOCOL_SHA256,
        "contract_sha256": ADOPTED_CONTRACT_SHA256,
    }
    if aad_object != expected_bindings:
        _fail(AUTHENTICATION_FAILURE)

    nonce = _decode_canonical_base64(
        envelope["nonce_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    ciphertext = _decode_canonical_base64(
        envelope["ciphertext_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    tag = _decode_canonical_base64(
        envelope["tag_b64"], SEALED_PACKAGE_SCHEMA_FAILURE
    )
    try:
        plaintext = AESGCM(controller_key.key_bytes).decrypt(
            nonce, ciphertext + tag, aad
        )
    except (InvalidTag, ValueError, TypeError):
        _fail(AUTHENTICATION_FAILURE)
    except Exception:
        _fail(AUTHENTICATION_FAILURE)

    state = _parse_json_object(plaintext, CONTROLLER_STATE_SCHEMA_FAILURE)
    validated = validate_controller_state(state)
    if any(
        validated[key] != expected_bindings[key]
        for key in ("artifact_type", "evaluation_id", "pair_id", "slot", "schema_version")
    ):
        _fail(AUTHENTICATION_FAILURE)
    if _json_bytes(validated, trailing_lf=False) != plaintext:
        _fail(CONTROLLER_STATE_SCHEMA_FAILURE)
    return validated
