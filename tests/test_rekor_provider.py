from __future__ import annotations

import base64
import copy
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

from governance_tools.rekor_provider import (
    RECEIPT_SCHEMA,
    RekorProviderProfile,
    RekorVerificationError,
    decode_base64_file,
    load_frozen_profile,
    rfc6962_leaf_hash,
    rfc6962_node_hash,
    verify_checkpoint,
    verify_inclusion_proof,
    verify_proof_bearing_receipt,
    verify_tuf_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "rekor_v2_provider"

EXPECTED_FIXTURE_BINDINGS = {
    "governance/rekor-tuf-bootstrap-root-v15.json.b64": (
        5630,
        "73747011d0857ada15479a16c4cae0f3ed03aac698b523b97e1de314ac9d9ca8",
    ),
    "tests/fixtures/rekor_v2_provider/timestamp.json.b64": (
        449,
        "d1d60e23687b2868f56add1e40ef301c637752f172172868af68d83b2af4fb1c",
    ),
    "tests/fixtures/rekor_v2_provider/165.snapshot.json.b64": (
        1760,
        "8f784ab614ec62bfdd5f568eb2a2e3011668449ba235ed4eb7befa99f8469933",
    ),
    "tests/fixtures/rekor_v2_provider/14.targets.json.b64": (
        4942,
        "6a697f7f8908c8ab26c11786ecb490b54acec97fa8c802e399f065f8a0cc1acd",
    ),
    "tests/fixtures/rekor_v2_provider/trusted_root.json.b64": (
        6787,
        "6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66",
    ),
    "tests/fixtures/rekor_v2_provider/signing_config_rekor_v2.v0.2.json.b64": (
        1230,
        "0f5f38554e29e770d4d5d6f0e1b51fcbf84f61dc6934530a09b7a901eaad5bee",
    ),
    "tests/fixtures/rekor_v2_provider/checkpoint.txt.b64": (
        643,
        "66b2948086c7e4a519a97924ad343efb75fa26d4f1d05b1feb3242f4280fcafc",
    ),
}


def _fixture(name: str) -> bytes:
    return decode_base64_file(FIXTURES / name)


def _official_tuf_inputs() -> dict[str, bytes | dict[str, bytes]]:
    return {
        "timestamp": _fixture("timestamp.json.b64"),
        "snapshot": _fixture("165.snapshot.json.b64"),
        "targets": _fixture("14.targets.json.b64"),
        "target_payloads": {
            "trusted_root.json": _fixture("trusted_root.json.b64"),
            "signing_config_rekor_v2.v0.2.json": _fixture(
                "signing_config_rekor_v2.v0.2.json.b64"
            ),
        },
    }


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _synthetic_receipt() -> tuple[RekorProviderProfile, dict[str, object]]:
    frozen_profile, _ = load_frozen_profile(ROOT)
    log_private = ed25519.Ed25519PrivateKey.generate()
    log_public_der = log_private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    log_id = hashlib.sha256(log_public_der).digest()
    profile = replace(
        frozen_profile,
        base_url="https://synthetic.invalid",
        log_key_id=base64.b64encode(log_id).decode("ascii"),
        log_public_key_der=log_public_der,
        checkpoint_key_hint=log_id[:4],
    )

    signed_artifact = b"gate1-external-pin-request-v1\x00synthetic-digest-only"
    subject_digest = hashlib.sha256(signed_artifact).digest()
    request_private = ec.generate_private_key(ec.SECP256R1())
    request_public_der = request_private.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    signature = request_private.sign(signed_artifact, ec.ECDSA(hashes.SHA256()))
    canonicalized_body = _canonical(
        {
            "apiVersion": "0.0.2",
            "kind": "hashedrekord",
            "spec": {
                "hashedRekordV002": {
                    "data": {
                        "algorithm": "SHA2_256",
                        "digest": base64.b64encode(subject_digest).decode("ascii"),
                    },
                    "signature": {
                        "content": base64.b64encode(signature).decode("ascii"),
                        "verifier": {
                            "keyDetails": "PKIX_ECDSA_P256_SHA_256",
                            "publicKey": {
                                "rawBytes": base64.b64encode(request_public_der).decode("ascii")
                            },
                        },
                    },
                }
            },
        }
    )
    root_hash = rfc6962_leaf_hash(canonicalized_body)
    signed_checkpoint = (
        b"synthetic.invalid\n1\n" + base64.b64encode(root_hash) + b"\n"
    )
    checkpoint_signature = log_id[:4] + log_private.sign(signed_checkpoint)
    checkpoint = (
        signed_checkpoint
        + b"\n\xe2\x80\x94 synthetic.invalid "
        + base64.b64encode(checkpoint_signature)
        + b"\n"
    )
    receipt: dict[str, object] = {
        "schema": RECEIPT_SCHEMA,
        "providerProfileSha256": profile.source_sha256,
        "subjectSha256": subject_digest.hex(),
        "signedArtifactBase64": base64.b64encode(signed_artifact).decode("ascii"),
        "canonicalizedBodyBase64": base64.b64encode(canonicalized_body).decode("ascii"),
        "logEntry": {
            "logIndex": "0",
            "logId": {"keyId": profile.log_key_id},
            "kindVersion": {"kind": "hashedrekord", "version": "0.0.2"},
            "integratedTime": "0",
            "inclusionPromise": None,
            "inclusionProof": {
                "logIndex": "0",
                "treeSize": "1",
                "hashes": [],
                "checkpoint": {"envelope": checkpoint.decode("utf-8")},
            },
        },
    }
    return profile, receipt


def test_official_fixture_bytes_are_exact() -> None:
    for relative_path, (expected_bytes, expected_sha256) in EXPECTED_FIXTURE_BINDINGS.items():
        raw = decode_base64_file(ROOT / relative_path)
        assert len(raw) == expected_bytes
        assert hashlib.sha256(raw).hexdigest() == expected_sha256


def test_frozen_profile_preserves_claim_ceiling() -> None:
    profile_raw = (ROOT / "governance" / "rekor-v2-provider-profile.json").read_bytes()
    document = json.loads(profile_raw)
    profile, root = load_frozen_profile(ROOT)

    assert profile.base_url == "https://log2025-1.rekor.sigstore.dev"
    assert profile.major_api_version == 2
    assert profile.entry_kind == "hashedrekord"
    assert profile.entry_version == "0.0.2"
    assert len(root) == 5630
    assert document["runtime_connected"] is False
    assert document["write_path_qualified"] is False
    assert (
        document["countability"]["post_mapping_final_head"]
        == "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION"
    )


def test_official_tuf_chain_and_provider_targets_verify() -> None:
    profile, root = load_frozen_profile(ROOT)
    verified = verify_tuf_snapshot(
        profile,
        bootstrap_root=root,
        reference_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
        **_official_tuf_inputs(),
    )

    assert verified.root_version == 15
    assert verified.timestamp_version == 764
    assert verified.snapshot_version == 165
    assert verified.targets_version == 14
    assert verified.target_sha256 == {
        "trusted_root.json": "6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66",
        "signing_config_rekor_v2.v0.2.json": "0f5f38554e29e770d4d5d6f0e1b51fcbf84f61dc6934530a09b7a901eaad5bee",
    }


@pytest.mark.parametrize("field", ["timestamp", "snapshot", "targets"])
def test_tuf_metadata_corruption_fails_closed(field: str) -> None:
    profile, root = load_frozen_profile(ROOT)
    inputs = _official_tuf_inputs()
    corrupted = bytearray(inputs[field])
    corrupted[-2] ^= 1
    inputs[field] = bytes(corrupted)

    with pytest.raises(RekorVerificationError, match="TUF metadata verification failed"):
        verify_tuf_snapshot(
            profile,
            bootstrap_root=root,
            reference_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
            **inputs,
        )


def test_tuf_target_corruption_fails_closed() -> None:
    profile, root = load_frozen_profile(ROOT)
    inputs = _official_tuf_inputs()
    payloads = dict(inputs["target_payloads"])
    payloads["trusted_root.json"] += b"\n"
    inputs["target_payloads"] = payloads

    with pytest.raises(RekorVerificationError, match="trusted_root.json byte length mismatch"):
        verify_tuf_snapshot(
            profile,
            bootstrap_root=root,
            reference_time=datetime(2026, 8, 25, tzinfo=timezone.utc),
            **inputs,
        )


def test_expired_bootstrap_fails_closed() -> None:
    profile, root = load_frozen_profile(ROOT)
    with pytest.raises(RekorVerificationError, match="bootstrap root is expired"):
        verify_tuf_snapshot(
            profile,
            bootstrap_root=root,
            reference_time=datetime(2027, 1, 1, tzinfo=timezone.utc),
            **_official_tuf_inputs(),
        )


def test_official_rekor_v2_checkpoint_signature_verifies() -> None:
    profile, _ = load_frozen_profile(ROOT)
    verified = verify_checkpoint(profile, _fixture("checkpoint.txt.b64"))

    assert verified.origin == "log2025-1.rekor.sigstore.dev"
    assert verified.tree_size == 80_208_523
    assert len(verified.root_hash) == 32
    assert verified.witness_signature_count == 3


def test_checkpoint_signature_corruption_fails_closed() -> None:
    profile, _ = load_frozen_profile(ROOT)
    checkpoint = _fixture("checkpoint.txt.b64")
    prefix = b"\xe2\x80\x94 log2025-1.rekor.sigstore.dev "
    start = checkpoint.index(prefix) + len(prefix)
    end = checkpoint.index(b"\n", start)
    signature = base64.b64decode(checkpoint[start:end])
    corrupted = signature[:-1] + bytes([signature[-1] ^ 1])
    checkpoint = checkpoint[:start] + base64.b64encode(corrupted) + checkpoint[end:]

    with pytest.raises(RekorVerificationError):
        verify_checkpoint(profile, checkpoint)


def test_rfc6962_inclusion_proof_accepts_known_three_leaf_tree() -> None:
    bodies = [b"alpha", b"beta", b"gamma"]
    leaves = [rfc6962_leaf_hash(item) for item in bodies]
    left = rfc6962_node_hash(leaves[0], leaves[1])
    root = rfc6962_node_hash(left, leaves[2])

    assert verify_inclusion_proof(
        canonicalized_body=bodies[1],
        log_index=1,
        tree_size=3,
        proof_hashes=[leaves[0], leaves[2]],
        expected_root=root,
    ) == 2
    assert verify_inclusion_proof(
        canonicalized_body=bodies[2],
        log_index=2,
        tree_size=3,
        proof_hashes=[left],
        expected_root=root,
    ) == 1


def test_rfc6962_inclusion_proof_covers_varied_tree_shapes() -> None:
    def tree_hash(leaves: list[bytes]) -> bytes:
        if len(leaves) == 1:
            return leaves[0]
        split = 1 << (len(leaves) - 1).bit_length() - 1
        return rfc6962_node_hash(tree_hash(leaves[:split]), tree_hash(leaves[split:]))

    def audit_path(leaves: list[bytes], index: int) -> list[bytes]:
        if len(leaves) == 1:
            return []
        split = 1 << (len(leaves) - 1).bit_length() - 1
        if index < split:
            return audit_path(leaves[:split], index) + [tree_hash(leaves[split:])]
        return audit_path(leaves[split:], index - split) + [tree_hash(leaves[:split])]

    for tree_size in range(1, 10):
        bodies = [f"leaf-{index}".encode() for index in range(tree_size)]
        leaves = [rfc6962_leaf_hash(item) for item in bodies]
        root = tree_hash(leaves)
        for index, body in enumerate(bodies):
            proof = audit_path(leaves, index)
            assert verify_inclusion_proof(
                canonicalized_body=body,
                log_index=index,
                tree_size=tree_size,
                proof_hashes=proof,
                expected_root=root,
            ) == len(proof)


@pytest.mark.parametrize("mode", ["missing", "extra", "corrupt"])
def test_rfc6962_inclusion_proof_corruption_fails_closed(mode: str) -> None:
    bodies = [b"alpha", b"beta", b"gamma"]
    leaves = [rfc6962_leaf_hash(item) for item in bodies]
    root = rfc6962_node_hash(rfc6962_node_hash(leaves[0], leaves[1]), leaves[2])
    proof = [leaves[0], leaves[2]]
    if mode == "missing":
        proof = proof[:-1]
    elif mode == "extra":
        proof = proof + [b"x" * 32]
    else:
        proof[0] = b"x" * 32

    with pytest.raises(RekorVerificationError):
        verify_inclusion_proof(
            canonicalized_body=bodies[1],
            log_index=1,
            tree_size=3,
            proof_hashes=proof,
            expected_root=root,
        )


def test_synthetic_proof_bearing_receipt_verifies() -> None:
    profile, receipt = _synthetic_receipt()
    verified = verify_proof_bearing_receipt(profile, receipt)

    assert len(verified.external_record_id) == 64
    assert verified.log_index == 0
    assert verified.tree_size == 1
    assert verified.inclusion_hash_count == 0
    assert verified.subject_sha256 == receipt["subjectSha256"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("profile", "provider profile binding mismatch"),
        ("subject", "signed artifact does not match subject digest"),
        ("log_id", "receipt log key ID mismatch"),
        ("kind", "receipt kind/version mismatch"),
        ("integrated_time", "integratedTime must be zero"),
        ("tree_size", "proof tree size does not match checkpoint"),
        ("body", "hashedrekord digest mismatch"),
        ("signature", "request signature verification failed"),
        ("checkpoint", "checkpoint signature verification failed"),
        ("extra_field", "logEntry fields mismatch"),
    ],
)
def test_receipt_corruption_fails_closed(mutation: str, message: str) -> None:
    profile, original = _synthetic_receipt()
    receipt = copy.deepcopy(original)
    log_entry = receipt["logEntry"]
    assert isinstance(log_entry, dict)
    if mutation == "profile":
        receipt["providerProfileSha256"] = "0" * 64
    elif mutation == "subject":
        receipt["subjectSha256"] = "0" * 64
    elif mutation == "log_id":
        log_entry["logId"]["keyId"] = base64.b64encode(b"x" * 32).decode()
    elif mutation == "kind":
        log_entry["kindVersion"]["kind"] = "rekord"
    elif mutation == "integrated_time":
        log_entry["integratedTime"] = "1"
    elif mutation == "tree_size":
        log_entry["inclusionProof"]["treeSize"] = "2"
    elif mutation in {"body", "signature"}:
        body = json.loads(base64.b64decode(receipt["canonicalizedBodyBase64"]))
        entry = body["spec"]["hashedRekordV002"]
        if mutation == "body":
            entry["data"]["digest"] = base64.b64encode(b"x" * 32).decode()
        else:
            signature = base64.b64decode(entry["signature"]["content"])
            entry["signature"]["content"] = base64.b64encode(signature[:-1] + bytes([signature[-1] ^ 1])).decode()
        receipt["canonicalizedBodyBase64"] = base64.b64encode(_canonical(body)).decode()
    elif mutation == "checkpoint":
        envelope = log_entry["inclusionProof"]["checkpoint"]["envelope"]
        marker = envelope.index("— synthetic.invalid ")
        signature_text = envelope[marker:].split(" ", 2)[2].strip()
        signature = base64.b64decode(signature_text)
        replacement = base64.b64encode(signature[:-1] + bytes([signature[-1] ^ 1])).decode()
        log_entry["inclusionProof"]["checkpoint"]["envelope"] = envelope.replace(signature_text, replacement)
    else:
        log_entry["unexpected"] = True

    with pytest.raises(RekorVerificationError, match=message):
        verify_proof_bearing_receipt(profile, receipt)


def test_verifier_module_has_no_network_or_process_surface() -> None:
    source = (ROOT / "governance_tools" / "rekor_provider.py").read_text(encoding="utf-8")
    assert "urllib" not in source
    assert "requests" not in source
    assert "subprocess" not in source
    assert "http://" not in source
    assert "POST /" not in source
