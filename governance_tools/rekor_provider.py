"""Pure Rekor v2 provider-profile and proof verification primitives.

This module never submits a Rekor entry and is not wired into admission or
runtime governance.  Callers supply already-retained bytes.  TUF metadata is
verified with python-tuf, signatures with cryptography, and inclusion proofs
with the RFC 6962 hash construction.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from tuf.api.metadata import Metadata


PROFILE_SCHEMA = "ai-governance.rekor-provider-profile/1"
RECEIPT_SCHEMA = "ai-governance.rekor-proof-bearing-receipt/1"
_CHECKPOINT_SEPARATOR = b"\n\n\xe2\x80\x94 "


class RekorVerificationError(ValueError):
    """Raised when a frozen provider or proof fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RekorVerificationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_base64(value: Any, field: str) -> bytes:
    _require(isinstance(value, str) and value != "", f"{field} must be non-empty base64")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise RekorVerificationError(f"{field} is invalid base64") from exc


def _parse_time(value: Any, field: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RekorVerificationError(f"{field} is invalid RFC3339") from exc
    return parsed


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{field} must be an object")
    return value


def _canonical_json(value: Any) -> bytes:
    """Canonicalize the restricted JSON shapes used by hashedrekord v0.0.2.

    The accepted body contains objects and strings only, so sorted UTF-8 JSON
    with compact separators is equivalent to RFC 8785 for this schema.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class RekorProviderProfile:
    source_sha256: str
    base_url: str
    operator: str
    major_api_version: int
    entry_kind: str
    entry_version: str
    provider_valid_from: datetime
    log_key_id: str
    log_key_details: str
    log_public_key_der: bytes
    log_key_valid_from: datetime
    checkpoint_key_hint: bytes
    bootstrap_root_version: int
    bootstrap_root_bytes: int
    bootstrap_root_sha256: str
    required_targets: Mapping[str, Mapping[str, Any]]
    request_key_details: str

    @classmethod
    def from_bytes(cls, raw: bytes) -> "RekorProviderProfile":
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RekorVerificationError("provider profile is not valid UTF-8 JSON") from exc
        _require(isinstance(document, dict), "provider profile must be an object")
        _require(document.get("schema") == PROFILE_SCHEMA, "provider profile schema mismatch")
        provider = _mapping(document.get("provider"), "provider")
        log_key = _mapping(document.get("log_key"), "log_key")
        tuf = _mapping(document.get("tuf"), "tuf")
        bootstrap = _mapping(tuf.get("bootstrap_root"), "tuf.bootstrap_root")
        request = _mapping(document.get("request"), "request")
        proof = _mapping(document.get("proof"), "proof")
        retention = _mapping(document.get("retention"), "retention")
        countability = _mapping(document.get("countability"), "countability")

        _require(
            provider.get("base_url") == "https://log2025-1.rekor.sigstore.dev",
            "provider base URL mismatch",
        )
        _require(provider.get("operator") == "sigstore.dev", "provider operator mismatch")
        _require(provider.get("major_api_version") == 2, "only Rekor API v2 is allowed")
        _require(provider.get("entry_kind") == "hashedrekord", "entry kind must be hashedrekord")
        _require(provider.get("entry_version") == "0.0.2", "entry version must be 0.0.2")
        _require(log_key.get("key_details") == "PKIX_ED25519", "log key must be Ed25519")
        _require(request.get("artifact_hash_algorithm") == "SHA2_256", "artifact hash must be SHA2_256")
        _require(
            request.get("signing_key_details") == "PKIX_ECDSA_P256_SHA_256",
            "request key must be ECDSA P-256 SHA-256",
        )
        _require(proof.get("leaf_hash_algorithm") == "RFC6962_SHA256", "unsupported leaf hash")
        _require(proof.get("integrated_time_is_authority") is False, "integrated time cannot be authority")
        _require(proof.get("witness_signatures_are_authority") is False, "witnesses are not frozen authority")
        _require(retention.get("aggregate_only") is True, "retention must be aggregate-only")
        _require(retention.get("retain_bulk_path_listing") is False, "bulk path listing is forbidden")
        _require(retention.get("retain_raw_provider_output") is False, "raw provider output is forbidden")
        _require(
            countability.get("post_mapping_final_head")
            == "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION",
            "D5 countability decision must remain unresolved",
        )
        _require(document.get("runtime_connected") is False, "profile must not claim runtime wiring")
        _require(document.get("write_path_qualified") is False, "profile must not claim write qualification")

        key_der = _decode_base64(log_key.get("raw_spki_der_base64"), "log_key.raw_spki_der_base64")
        key_id_bytes = _decode_base64(log_key.get("key_id"), "log_key.key_id")
        _require(len(key_id_bytes) == 32, "log key ID must contain 32 bytes")
        try:
            hint = bytes.fromhex(str(log_key.get("checkpoint_key_hint_hex")))
        except ValueError as exc:
            raise RekorVerificationError("checkpoint key hint is invalid hex") from exc
        _require(len(hint) == 4 and hint == key_id_bytes[:4], "checkpoint key hint mismatch")

        required_targets = _mapping(tuf.get("required_targets"), "tuf.required_targets")
        _require(set(required_targets) == {"trusted_root.json", "signing_config_rekor_v2.v0.2.json"}, "required TUF target set mismatch")
        _require(tuf.get("client") == "python-tuf", "TUF client must be python-tuf")
        _require(tuf.get("client_version") == "7.0.0", "python-tuf version mismatch")

        return cls(
            source_sha256=_sha256(raw),
            base_url=str(provider.get("base_url")),
            operator=str(provider.get("operator")),
            major_api_version=2,
            entry_kind="hashedrekord",
            entry_version="0.0.2",
            provider_valid_from=_parse_time(provider.get("valid_from"), "provider.valid_from"),
            log_key_id=str(log_key.get("key_id")),
            log_key_details="PKIX_ED25519",
            log_public_key_der=key_der,
            log_key_valid_from=_parse_time(log_key.get("valid_from"), "log_key.valid_from"),
            checkpoint_key_hint=hint,
            bootstrap_root_version=int(bootstrap.get("version")),
            bootstrap_root_bytes=int(bootstrap.get("bytes")),
            bootstrap_root_sha256=str(bootstrap.get("sha256")),
            required_targets=required_targets,
            request_key_details=str(request.get("signing_key_details")),
        )


@dataclass(frozen=True)
class VerifiedTufSnapshot:
    root_version: int
    timestamp_version: int
    snapshot_version: int
    targets_version: int
    trusted_root: Mapping[str, Any]
    signing_config: Mapping[str, Any]
    target_sha256: Mapping[str, str]


@dataclass(frozen=True)
class VerifiedCheckpoint:
    origin: str
    tree_size: int
    root_hash: bytes
    signed_text_sha256: str
    witness_signature_count: int


@dataclass(frozen=True)
class VerifiedReceipt:
    external_record_id: str
    log_index: int
    tree_size: int
    subject_sha256: str
    canonicalized_body_sha256: str
    checkpoint_signed_text_sha256: str
    inclusion_hash_count: int


def decode_base64_file(path: Path) -> bytes:
    """Decode an exact-byte fixture or bootstrap root stored as base64 text."""

    try:
        return base64.b64decode(path.read_text(encoding="ascii").strip(), validate=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise RekorVerificationError(f"cannot decode base64 file: {path}") from exc


def load_frozen_profile(framework_root: Path) -> tuple[RekorProviderProfile, bytes]:
    """Load the tracked provider profile and independently pinned root bytes."""

    profile_path = framework_root / "governance" / "rekor-v2-provider-profile.json"
    try:
        profile_raw = profile_path.read_bytes()
    except OSError as exc:
        raise RekorVerificationError(f"provider profile is unreadable: {profile_path}") from exc
    profile = RekorProviderProfile.from_bytes(profile_raw)
    root_path = framework_root / "governance" / "rekor-tuf-bootstrap-root-v15.json.b64"
    root_raw = decode_base64_file(root_path)
    _require(len(root_raw) == profile.bootstrap_root_bytes, "bootstrap root byte length mismatch")
    _require(_sha256(root_raw) == profile.bootstrap_root_sha256, "bootstrap root digest mismatch")
    return profile, root_raw


def verify_tuf_snapshot(
    profile: RekorProviderProfile,
    *,
    bootstrap_root: bytes,
    timestamp: bytes,
    snapshot: bytes,
    targets: bytes,
    target_payloads: Mapping[str, bytes],
    reference_time: datetime | None = None,
) -> VerifiedTufSnapshot:
    """Verify a complete top-level TUF chain and the required provider targets."""

    _require(len(bootstrap_root) == profile.bootstrap_root_bytes, "bootstrap root byte length mismatch")
    _require(_sha256(bootstrap_root) == profile.bootstrap_root_sha256, "bootstrap root digest mismatch")
    now = reference_time or datetime.now(timezone.utc)
    _require(now.tzinfo is not None, "reference_time must be timezone-aware")

    try:
        root_md = Metadata.from_bytes(bootstrap_root)
        timestamp_md = Metadata.from_bytes(timestamp)
        snapshot_md = Metadata.from_bytes(snapshot)
        targets_md = Metadata.from_bytes(targets)
        root_md.verify_delegate("root", root_md)
        root_md.verify_delegate("timestamp", timestamp_md)
        timestamp_md.signed.snapshot_meta.verify_length_and_hashes(snapshot)
        root_md.verify_delegate("snapshot", snapshot_md)
        snapshot_md.signed.meta["targets.json"].verify_length_and_hashes(targets)
        root_md.verify_delegate("targets", targets_md)
    except Exception as exc:
        raise RekorVerificationError(f"TUF metadata verification failed: {type(exc).__name__}") from exc

    _require(root_md.signed.version == profile.bootstrap_root_version, "bootstrap root version mismatch")
    _require(not root_md.signed.is_expired(now), "bootstrap root is expired")
    _require(not timestamp_md.signed.is_expired(now), "timestamp metadata is expired")
    _require(not snapshot_md.signed.is_expired(now), "snapshot metadata is expired")
    _require(not targets_md.signed.is_expired(now), "targets metadata is expired")
    _require(timestamp_md.signed.snapshot_meta.version == snapshot_md.signed.version, "snapshot version mismatch")
    _require(snapshot_md.signed.meta["targets.json"].version == targets_md.signed.version, "targets version mismatch")
    _require(set(target_payloads) == set(profile.required_targets), "required target payload set mismatch")

    target_digests: dict[str, str] = {}
    for name, expected_any in profile.required_targets.items():
        expected = _mapping(expected_any, f"required target {name}")
        payload = target_payloads[name]
        _require(len(payload) == int(expected.get("bytes")), f"{name} byte length mismatch")
        _require(_sha256(payload) == expected.get("sha256"), f"{name} digest mismatch")
        try:
            target_info = targets_md.signed.targets[name]
            target_info.verify_length_and_hashes(payload)
        except Exception as exc:
            raise RekorVerificationError(f"TUF target verification failed for {name}") from exc
        target_digests[name] = _sha256(payload)

    try:
        trusted_root = json.loads(target_payloads["trusted_root.json"].decode("utf-8"))
        signing_config = json.loads(target_payloads["signing_config_rekor_v2.v0.2.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RekorVerificationError("verified TUF target is not valid UTF-8 JSON") from exc

    matching_logs = [item for item in trusted_root.get("tlogs", []) if item.get("baseUrl") == profile.base_url]
    _require(len(matching_logs) == 1, "trusted root must contain exactly one frozen log")
    trusted_log = matching_logs[0]
    _require(trusted_log.get("hashAlgorithm") == "SHA2_256", "trusted log hash algorithm mismatch")
    _require(_mapping(trusted_log.get("logId"), "trusted log ID").get("keyId") == profile.log_key_id, "trusted log key ID mismatch")
    public_key = _mapping(trusted_log.get("publicKey"), "trusted log public key")
    _require(public_key.get("keyDetails") == profile.log_key_details, "trusted log key details mismatch")
    _require(_decode_base64(public_key.get("rawBytes"), "trusted log rawBytes") == profile.log_public_key_der, "trusted log public key mismatch")
    valid_for = _mapping(public_key.get("validFor"), "trusted log validity")
    _require(_parse_time(valid_for.get("start"), "trusted log validity start") == profile.log_key_valid_from, "trusted log validity start mismatch")

    matching_services = [
        item
        for item in signing_config.get("rekorTlogUrls", [])
        if item.get("url") == profile.base_url and item.get("majorApiVersion") == profile.major_api_version
    ]
    _require(len(matching_services) == 1, "signing config must contain exactly one frozen v2 service")
    service = matching_services[0]
    _require(service.get("operator") == profile.operator, "signing config operator mismatch")
    service_validity = _mapping(service.get("validFor"), "signing config validity")
    _require(_parse_time(service_validity.get("start"), "signing config validity start") == profile.provider_valid_from, "signing config validity start mismatch")

    return VerifiedTufSnapshot(
        root_version=root_md.signed.version,
        timestamp_version=timestamp_md.signed.version,
        snapshot_version=snapshot_md.signed.version,
        targets_version=targets_md.signed.version,
        trusted_root=trusted_root,
        signing_config=signing_config,
        target_sha256=target_digests,
    )


def verify_checkpoint(profile: RekorProviderProfile, checkpoint: bytes) -> VerifiedCheckpoint:
    """Verify a Rekor v2 signed-note checkpoint with the frozen TUF log key."""

    _require(b"\r" not in checkpoint, "checkpoint must use LF line endings")
    separator_at = checkpoint.find(_CHECKPOINT_SEPARATOR)
    _require(separator_at >= 0, "checkpoint signature separator is missing")
    signed_text = checkpoint[: separator_at + 1]
    signature_block = checkpoint[separator_at + 2 :]
    try:
        signed_lines = signed_text.decode("utf-8").splitlines()
        signature_lines = signature_block.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RekorVerificationError("checkpoint is not valid UTF-8") from exc
    _require(len(signed_lines) == 3 and signed_text.endswith(b"\n"), "checkpoint signed text shape mismatch")
    origin, tree_size_text, root_hash_text = signed_lines
    _require(origin == profile.base_url.removeprefix("https://"), "checkpoint origin mismatch")
    try:
        tree_size = int(tree_size_text)
    except ValueError as exc:
        raise RekorVerificationError("checkpoint tree size is invalid") from exc
    _require(tree_size > 0, "checkpoint tree size must be positive")
    root_hash = _decode_base64(root_hash_text, "checkpoint root hash")
    _require(len(root_hash) == 32, "checkpoint root hash must be SHA-256")

    signer = origin
    matching = [line for line in signature_lines if line.startswith(f"— {signer} ")]
    _require(len(matching) == 1, "checkpoint must contain exactly one frozen-log signature")
    signature_blob = _decode_base64(matching[0].split(" ", 2)[2], "checkpoint signature")
    _require(len(signature_blob) == 68, "checkpoint Ed25519 signature blob length mismatch")
    _require(signature_blob[:4] == profile.checkpoint_key_hint, "checkpoint signature key hint mismatch")
    try:
        public_key = serialization.load_der_public_key(profile.log_public_key_der)
        _require(isinstance(public_key, ed25519.Ed25519PublicKey), "checkpoint key is not Ed25519")
        public_key.verify(signature_blob[4:], signed_text)
    except InvalidSignature as exc:
        raise RekorVerificationError("checkpoint signature verification failed") from exc
    except (TypeError, ValueError) as exc:
        raise RekorVerificationError("checkpoint public key is invalid") from exc

    witness_count = sum(1 for line in signature_lines if line.startswith("— ")) - 1
    return VerifiedCheckpoint(
        origin=origin,
        tree_size=tree_size,
        root_hash=root_hash,
        signed_text_sha256=_sha256(signed_text),
        witness_signature_count=witness_count,
    )


def rfc6962_leaf_hash(canonicalized_body: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + canonicalized_body).digest()


def rfc6962_node_hash(left: bytes, right: bytes) -> bytes:
    _require(len(left) == 32 and len(right) == 32, "RFC6962 node hashes must be SHA-256")
    return hashlib.sha256(b"\x01" + left + right).digest()


def verify_inclusion_proof(
    *,
    canonicalized_body: bytes,
    log_index: int,
    tree_size: int,
    proof_hashes: list[bytes],
    expected_root: bytes,
) -> int:
    """Verify an RFC 6962 audit path and return the number of consumed hashes."""

    _require(tree_size > 0, "tree size must be positive")
    _require(0 <= log_index < tree_size, "log index is outside the tree")
    _require(len(expected_root) == 32, "expected root must be SHA-256")
    _require(all(len(item) == 32 for item in proof_hashes), "proof hashes must be SHA-256")

    node = rfc6962_leaf_hash(canonicalized_body)
    fn = log_index
    sn = tree_size - 1
    for sibling in proof_hashes:
        _require(sn != 0, "inclusion proof has extra hashes")
        if fn & 1 or fn == sn:
            node = rfc6962_node_hash(sibling, node)
            while fn != 0 and fn & 1 == 0:
                fn >>= 1
                sn >>= 1
        else:
            node = rfc6962_node_hash(node, sibling)
        fn >>= 1
        sn >>= 1
    _require(sn == 0, "inclusion proof is incomplete")
    _require(node == expected_root, "inclusion proof root mismatch")
    return len(proof_hashes)


def verify_hashedrekord_binding(
    profile: RekorProviderProfile,
    *,
    subject_sha256: str,
    signed_artifact: bytes,
    canonicalized_body: bytes,
) -> None:
    """Verify subject digest, request signature, and exact v0.0.2 body binding."""

    _require(len(subject_sha256) == 64, "subject_sha256 must contain 64 hex characters")
    try:
        subject_digest = bytes.fromhex(subject_sha256)
    except ValueError as exc:
        raise RekorVerificationError("subject_sha256 is invalid hex") from exc
    _require(hashlib.sha256(signed_artifact).digest() == subject_digest, "signed artifact does not match subject digest")
    try:
        body = json.loads(canonicalized_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RekorVerificationError("canonicalized body is not valid UTF-8 JSON") from exc
    _require(_canonical_json(body) == canonicalized_body, "hashedrekord body is not canonical JSON")
    _require(set(body) == {"apiVersion", "kind", "spec"}, "hashedrekord top-level fields mismatch")
    _require(body.get("apiVersion") == profile.entry_version, "hashedrekord API version mismatch")
    _require(body.get("kind") == profile.entry_kind, "hashedrekord kind mismatch")
    spec = _mapping(body.get("spec"), "hashedrekord spec")
    _require(set(spec) == {"hashedRekordV002"}, "hashedrekord spec fields mismatch")
    entry = _mapping(spec.get("hashedRekordV002"), "hashedRekordV002")
    _require(set(entry) == {"data", "signature"}, "hashedRekordV002 fields mismatch")
    data = _mapping(entry.get("data"), "hashedrekord data")
    _require(set(data) == {"algorithm", "digest"}, "hashedrekord data fields mismatch")
    _require(data.get("algorithm") == "SHA2_256", "hashedrekord data algorithm mismatch")
    _require(_decode_base64(data.get("digest"), "hashedrekord digest") == subject_digest, "hashedrekord digest mismatch")

    signature = _mapping(entry.get("signature"), "hashedrekord signature")
    _require(set(signature) == {"content", "verifier"}, "hashedrekord signature fields mismatch")
    signature_bytes = _decode_base64(signature.get("content"), "hashedrekord signature content")
    verifier = _mapping(signature.get("verifier"), "hashedrekord verifier")
    _require(set(verifier) == {"keyDetails", "publicKey"}, "hashedrekord verifier fields mismatch")
    _require(verifier.get("keyDetails") == profile.request_key_details, "request key details mismatch")
    public_key_container = _mapping(verifier.get("publicKey"), "hashedrekord public key")
    _require(set(public_key_container) == {"rawBytes"}, "hashedrekord public key fields mismatch")
    public_key_der = _decode_base64(public_key_container.get("rawBytes"), "hashedrekord public key rawBytes")
    try:
        public_key = serialization.load_der_public_key(public_key_der)
        _require(isinstance(public_key, ec.EllipticCurvePublicKey), "request key is not elliptic-curve")
        _require(isinstance(public_key.curve, ec.SECP256R1), "request key curve is not P-256")
        public_key.verify(signature_bytes, signed_artifact, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise RekorVerificationError("request signature verification failed") from exc
    except (TypeError, ValueError) as exc:
        raise RekorVerificationError("request public key is invalid") from exc


def verify_proof_bearing_receipt(
    profile: RekorProviderProfile,
    receipt: Mapping[str, Any],
) -> VerifiedReceipt:
    """Verify a retained Rekor v2 response without network or filesystem access."""

    _require(receipt.get("schema") == RECEIPT_SCHEMA, "receipt schema mismatch")
    _require(receipt.get("providerProfileSha256") == profile.source_sha256, "provider profile binding mismatch")
    subject_sha256 = str(receipt.get("subjectSha256"))
    signed_artifact = _decode_base64(receipt.get("signedArtifactBase64"), "signedArtifactBase64")
    canonicalized_body = _decode_base64(receipt.get("canonicalizedBodyBase64"), "canonicalizedBodyBase64")
    log_entry = _mapping(receipt.get("logEntry"), "logEntry")
    _require(set(log_entry) == {"logIndex", "logId", "kindVersion", "integratedTime", "inclusionPromise", "inclusionProof"}, "logEntry fields mismatch")
    log_id = _mapping(log_entry.get("logId"), "logId")
    _require(log_id.get("keyId") == profile.log_key_id, "receipt log key ID mismatch")
    kind_version = _mapping(log_entry.get("kindVersion"), "kindVersion")
    _require(kind_version == {"kind": profile.entry_kind, "version": profile.entry_version}, "receipt kind/version mismatch")
    _require(str(log_entry.get("integratedTime")) == "0", "Rekor v2 integratedTime must be zero")
    _require(log_entry.get("inclusionPromise") is None, "Rekor v2 inclusionPromise must be absent")
    try:
        log_index = int(log_entry.get("logIndex"))
    except (TypeError, ValueError) as exc:
        raise RekorVerificationError("receipt log index is invalid") from exc
    _require(log_index >= 0, "receipt log index must be non-negative")

    verify_hashedrekord_binding(
        profile,
        subject_sha256=subject_sha256,
        signed_artifact=signed_artifact,
        canonicalized_body=canonicalized_body,
    )

    proof = _mapping(log_entry.get("inclusionProof"), "inclusionProof")
    checkpoint_container = _mapping(proof.get("checkpoint"), "inclusionProof.checkpoint")
    checkpoint_text = checkpoint_container.get("envelope")
    _require(isinstance(checkpoint_text, str), "checkpoint envelope must be text")
    checkpoint = verify_checkpoint(profile, checkpoint_text.encode("utf-8"))
    try:
        proof_index = int(proof.get("logIndex"))
        proof_tree_size = int(proof.get("treeSize"))
    except (TypeError, ValueError) as exc:
        raise RekorVerificationError("inclusion proof index or tree size is invalid") from exc
    _require(proof_index == log_index, "duplicated proof log index mismatch")
    _require(proof_tree_size == checkpoint.tree_size, "proof tree size does not match checkpoint")
    hashes_value = proof.get("hashes")
    _require(isinstance(hashes_value, list), "inclusion proof hashes must be an array")
    proof_hashes = [_decode_base64(item, "inclusion proof hash") for item in hashes_value]
    consumed = verify_inclusion_proof(
        canonicalized_body=canonicalized_body,
        log_index=log_index,
        tree_size=checkpoint.tree_size,
        proof_hashes=proof_hashes,
        expected_root=checkpoint.root_hash,
    )

    leaf_hash = rfc6962_leaf_hash(canonicalized_body)
    record_material = (
        b"rekor-v2-record\x00"
        + _decode_base64(profile.log_key_id, "profile log key ID")
        + b"\x00"
        + str(log_index).encode("ascii")
        + b"\x00"
        + leaf_hash
    )
    return VerifiedReceipt(
        external_record_id=hashlib.sha256(record_material).hexdigest(),
        log_index=log_index,
        tree_size=checkpoint.tree_size,
        subject_sha256=subject_sha256,
        canonicalized_body_sha256=_sha256(canonicalized_body),
        checkpoint_signed_text_sha256=checkpoint.signed_text_sha256,
        inclusion_hash_count=consumed,
    )
