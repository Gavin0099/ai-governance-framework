from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

import pytest


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]


def _load() -> ModuleType:
    path = HERE / "rekor_write_probe.py"
    spec = importlib.util.spec_from_file_location("rekor_write_probe_freeze", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PROBE = _load()
HEAD = PROBE._current_head(ROOT)


class FakeTransport:
    def __init__(self, *, response_code: int = 200, response: bytes = b"{}") -> None:
        fixture = ROOT / "tests" / "fixtures" / "rekor_v2_provider"
        self.gets: list[str] = []
        self.posts: list[dict[str, Any]] = []
        self.response_code = response_code
        self.response = response
        self.payloads = {
            "timestamp.json": _decode(fixture / "timestamp.json.b64"),
            "165.snapshot.json": _decode(fixture / "165.snapshot.json.b64"),
            "14.targets.json": _decode(fixture / "14.targets.json.b64"),
            "trusted_root.json": _decode(fixture / "trusted_root.json.b64"),
            "signing_config_rekor_v2.v0.2.json": _decode(
                fixture / "signing_config_rekor_v2.v0.2.json.b64"
            ),
        }

    def get(self, url: str, *, timeout_seconds: int) -> bytes:
        self.gets.append(url)
        return self.payloads[url.rsplit("/", 1)[-1]]

    def post_json(
        self,
        url: str,
        *,
        body: bytes,
        headers: Mapping[str, str],
        timeout_seconds: int,
    ) -> tuple[int, bytes]:
        self.posts.append(
            {"url": url, "body": body, "headers": dict(headers), "timeout": timeout_seconds}
        )
        return self.response_code, self.response


def _decode(path: Path) -> bytes:
    return base64.b64decode(path.read_text(encoding="ascii").strip(), validate=True)


@dataclass
class Verified:
    external_record_id: str = "ab" * 32
    log_index: int = 123
    tree_size: int = 456
    canonicalized_body_sha256: str = "cd" * 32
    checkpoint_signed_text_sha256: str = "ef" * 32
    inclusion_hash_count: int = 8


def _valid_response() -> bytes:
    return json.dumps(
        {
            "logIndex": "123",
            "logId": {"keyId": "unused-by-injected-verifier"},
            "kindVersion": {"kind": "hashedrekord", "version": "0.0.2"},
            "integratedTime": "0",
            "inclusionPromise": None,
            "inclusionProof": {},
            "canonicalizedBody": base64.b64encode(b"{}").decode("ascii"),
        }
    ).encode("utf-8")


def _execute(tmp_path: Path, transport: FakeTransport, *, authority: str = HEAD):
    return PROBE._execute_probe_with_documents(
        framework_root=ROOT,
        freeze_dir=HERE,
        output_dir=tmp_path,
        owner_authorized_commit=authority,
        transport=transport,
        head_reader=lambda _: HEAD,
        receipt_verifier=lambda _profile, _receipt: Verified(),
        now=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
        manifest=json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8")),
        policy=json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8")),
    )


def test_import_has_no_network_or_execution_side_effect() -> None:
    assert PROBE.MANIFEST_PATH == HERE / "write-probe-manifest.json"


def test_committed_executor_is_directly_invocable() -> None:
    result = subprocess.run(
        [sys.executable, str(HERE / "rekor_write_probe.py"), "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--owner-authorized-freeze-commit" in result.stdout


def test_manifest_keeps_execution_unauthorized() -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    assert manifest["execution_authority"]["authorized"] is False
    assert manifest["public_side_effect"]["performed"] is False


def test_authority_mismatch_stops_before_network(tmp_path: Path) -> None:
    transport = FakeTransport()
    terminal = _execute(tmp_path, transport, authority="wrong")
    assert terminal.status == "WRITE_PROBE_AUTHORITY_MISMATCH"
    assert not transport.gets and not transport.posts
    assert terminal.public_append_may_have_occurred is False


def test_repo_internal_terminal_path_is_rejected_before_network() -> None:
    transport = FakeTransport()
    with pytest.raises(PROBE.WriteProbeError, match="outside the framework"):
        _execute(ROOT / "artifacts" / "forbidden-write-probe-output", transport)
    assert not transport.gets and not transport.posts


def test_executor_must_be_in_frozen_files() -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    changed = dict(manifest)
    changed["frozen_files"] = dict(manifest["frozen_files"])
    changed["frozen_files"].pop("rekor_write_probe.py")
    with pytest.raises(PROBE.WriteProbeError, match="executor is not frozen"):
        PROBE.verify_frozen_files(changed, HERE)


def test_frozen_file_corruption_fails_closed(tmp_path: Path) -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    changed = dict(manifest)
    changed["frozen_files"] = dict(manifest["frozen_files"])
    changed["frozen_files"]["README.md"] = {"bytes": 1, "sha256": "00" * 32}
    with pytest.raises(PROBE.WriteProbeError, match="binding mismatch"):
        PROBE.verify_frozen_files(changed, HERE)


def test_success_uses_exact_endpoint_headers_timeout_and_one_post(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_PASSED"
    assert terminal.post_attempt_count == 1
    assert terminal.public_append_attempted is True
    assert terminal.public_append_may_have_occurred is True
    assert len(transport.posts) == 1
    post = transport.posts[0]
    assert post["url"] == "https://log2025-1.rekor.sigstore.dev/api/v2/log/entries"
    assert post["timeout"] == 60
    assert post["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ai-governance-framework-rekor-write-probe/1",
    }
    assert not {"authorization", "cookie", "proxy-authorization"}.intersection(
        key.lower() for key in post["headers"]
    )


def test_request_is_exact_hashedrekord_v002_shape(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())
    _execute(tmp_path, transport)
    body = json.loads(transport.posts[0]["body"])
    assert set(body) == {"hashedRekordRequestV002"}
    entry = body["hashedRekordRequestV002"]
    assert set(entry) == {"digest", "signature"}
    assert set(entry["signature"]) == {"content", "verifier"}
    assert entry["signature"]["verifier"]["keyDetails"] == "PKIX_ECDSA_P256_SHA_256"


def test_provider_rejection_is_single_attempt_and_may_have_appended(tmp_path: Path) -> None:
    transport = FakeTransport(response_code=503, response=b"unavailable")
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_PROVIDER_REJECTED"
    assert len(transport.posts) == 1
    assert terminal.public_append_may_have_occurred is True


def test_invalid_response_fails_closed_after_single_post(tmp_path: Path) -> None:
    transport = FakeTransport(response=b"not-json")
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_RESPONSE_INVALID"
    assert len(transport.posts) == 1
    assert terminal.public_append_may_have_occurred is True


def test_proof_verifier_failure_is_response_invalid_without_retry(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())

    def reject(_profile: Any, _receipt: Mapping[str, Any]) -> Any:
        raise ValueError("synthetic corrupt proof")

    terminal = PROBE._execute_probe_with_documents(
        framework_root=ROOT,
        freeze_dir=HERE,
        output_dir=tmp_path,
        owner_authorized_commit=HEAD,
        transport=transport,
        head_reader=lambda _: HEAD,
        receipt_verifier=reject,
        now=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
        manifest=json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8")),
        policy=json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8")),
    )
    assert terminal.status == "WRITE_PROBE_RESPONSE_INVALID"
    assert len(transport.posts) == 1
    assert terminal.public_append_may_have_occurred is True


def test_terminal_is_aggregate_only(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())
    _execute(tmp_path, transport)
    terminal = json.loads((tmp_path / "rekor-v2-write-probe-terminal.json").read_text())
    serialized = json.dumps(terminal).lower()
    for forbidden in json.loads((HERE / "write-probe-output-policy.json").read_text())[
        "forbidden_fields"
    ]:
        assert f'"{forbidden.lower()}"' not in serialized
    assert terminal["external_record_id"] == "ab" * 32
    proof_path = tmp_path / "rekor-v2-proof-receipt.json"
    proof_raw = proof_path.read_bytes()
    proof = json.loads(proof_raw)
    assert set(proof) == {
        "schema",
        "providerProfileSha256",
        "subjectSha256",
        "signedArtifactBase64",
        "canonicalizedBodyBase64",
        "logEntry",
    }
    assert terminal["proof_receipt_sha256"] == PROBE._sha256(proof_raw)


def test_existing_terminal_forbids_retry_before_network(tmp_path: Path) -> None:
    terminal_path = tmp_path / "rekor-v2-write-probe-terminal.json"
    terminal_path.write_text("{}", encoding="utf-8")
    transport = FakeTransport()
    with pytest.raises(PROBE.WriteProbeError, match="retry is forbidden"):
        _execute(tmp_path, transport)
    assert not transport.gets and not transport.posts


def test_existing_proof_receipt_forbids_retry_before_network(tmp_path: Path) -> None:
    proof_path = tmp_path / "rekor-v2-proof-receipt.json"
    proof_path.write_text("{}", encoding="utf-8")
    transport = FakeTransport()
    with pytest.raises(PROBE.WriteProbeError, match="retry is forbidden"):
        _execute(tmp_path, transport)
    assert not transport.gets and not transport.posts


def test_diagnostic_redacts_sensitive_tokens() -> None:
    assert PROBE._sanitize_diagnostic("signature secret", 240) == "diagnostic redacted by output policy"


def test_header_allowlist_rejects_credentials() -> None:
    headers = {"Authorization": "synthetic-value"}
    with pytest.raises(PROBE.WriteProbeError):
        PROBE._validate_headers(headers, headers)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("url", "https://example.invalid/api/v2/log/entries", "write URL"),
        ("retries_allowed", True, "one POST"),
        ("credentials_allowed", True, "credentials"),
    ],
)
def test_execution_contract_rejects_manifest_drift(field: str, value: Any, message: str) -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    manifest["http"][field] = value

    class Profile:
        base_url = "https://log2025-1.rekor.sigstore.dev"
        entry_kind = "hashedrekord"
        entry_version = "0.0.2"

    with pytest.raises(PROBE.WriteProbeError, match=message):
        PROBE._validate_execution_contract(manifest, Profile())


def test_policy_retains_no_raw_provider_or_request_material() -> None:
    policy = json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8"))
    assert policy["retain_raw_provider_output"] is False
    assert policy["retain_request_body"] is False
    assert policy["retain_normalized_proof_receipt"] is True
    assert policy["retain_signature_in_terminal"] is False
    assert policy["retain_public_key_in_terminal"] is False
    assert policy["retain_canonicalized_body_in_terminal"] is False
    assert policy["retain_bulk_path_listing"] is False
