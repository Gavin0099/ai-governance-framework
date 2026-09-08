from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
import urllib.error
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
        basename = url.rsplit("/", 1)[-1]
        if basename == "16.root.json":
            raise urllib.error.HTTPError(url, 404, "not found", None, None)
        if basename in self.payloads:
            return self.payloads[basename]
        for name in (
            "trusted_root.json",
            "signing_config_rekor_v2.v0.2.json",
        ):
            if basename.endswith(f".{name}"):
                return self.payloads[name]
        raise urllib.error.HTTPError(url, 404, "not found", None, None)

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


def _execute(
    tmp_path: Path,
    transport: FakeTransport,
    *,
    authority: str = HEAD,
    verifier: Any = None,
):
    return PROBE._execute_probe_with_documents(
        framework_root=ROOT,
        freeze_dir=HERE,
        output_dir=tmp_path,
        owner_authorized_commit=authority,
        transport=transport,
        head_reader=lambda _: HEAD,
        receipt_verifier=verifier or (lambda _profile, _receipt: Verified()),
        now=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
        manifest=json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8")),
        policy=json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8")),
    )


def _committed_freeze_fixture(tmp_path: Path, *, schema: str | None = None) -> tuple[Path, Path, str]:
    root = tmp_path / "framework"
    freeze_dir = root / PROBE.FREEZE_RELATIVE_DIR
    freeze_dir.mkdir(parents=True)
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    for name in (*manifest["frozen_files"], "write-probe-manifest.json"):
        shutil.copyfile(HERE / name, freeze_dir / name)
    if schema is not None:
        manifest["schema"] = schema
        (freeze_dir / "write-probe-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "--", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Gate 3 Test",
            "-c",
            "user.email=gate3-test@example.invalid",
            "commit",
            "-q",
            "-m",
            "synthetic committed freeze",
        ],
        cwd=root,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return root, freeze_dir, head


def test_import_has_no_network_or_execution_side_effect() -> None:
    assert PROBE.MANIFEST_PATH == HERE / "write-probe-manifest.json"


def test_execute_probe_loads_committed_freeze_before_authority_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, freeze_dir, head = _committed_freeze_fixture(tmp_path)
    transport = FakeTransport()
    attempted_socket = False

    def deny_socket(*_args: Any, **_kwargs: Any) -> None:
        nonlocal attempted_socket
        attempted_socket = True
        raise AssertionError("network attempted before authority validation")

    monkeypatch.setattr(socket, "create_connection", deny_socket)
    monkeypatch.setattr(socket.socket, "connect", deny_socket)

    terminal = PROBE.execute_probe(
        framework_root=root,
        freeze_dir=freeze_dir,
        output_dir=tmp_path / "output",
        owner_authorized_commit="0" * 40,
        transport=transport,
        head_reader=lambda _: head,
    )

    assert terminal.status == "WRITE_PROBE_AUTHORITY_MISMATCH"
    assert terminal.freeze_commit == head
    assert terminal.post_attempt_count == 0
    assert not terminal.public_append_attempted
    assert (tmp_path / "output" / PROBE.TERMINAL_FILENAME).is_file()
    assert not transport.gets and not transport.posts
    assert not attempted_socket


def test_committed_freeze_schema_failure_retains_precondition_terminal(tmp_path: Path) -> None:
    root, freeze_dir, head = _committed_freeze_fixture(
        tmp_path,
        schema="ai-governance.rekor-v2-write-probe-freeze/1",
    )
    transport = FakeTransport()

    terminal = PROBE.execute_probe(
        framework_root=root,
        freeze_dir=freeze_dir,
        output_dir=tmp_path / "output",
        owner_authorized_commit=head,
        transport=transport,
        head_reader=lambda _: head,
    )

    assert terminal.status == "WRITE_PROBE_PRECONDITION_FAILED"
    assert terminal.freeze_commit == head
    assert terminal.post_attempt_count == 0
    assert not terminal.public_append_attempted
    assert terminal.diagnostic == "committed write-probe manifest schema mismatch"
    assert (tmp_path / "output" / PROBE.TERMINAL_FILENAME).is_file()
    assert not transport.gets and not transport.posts


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
    assert manifest["prior_attempt_binding"] == {
        "freeze_commit": "4d68eaf50f7255f4fc3e9b2331d84ee415013ffb",
        "terminal_status": "WRITE_PROBE_PROVIDER_REJECTED",
        "terminal_bytes": 901,
        "terminal_sha256": "2ca13d0e5149d8b23e879d6e7e8686da2d4f68edd792780032051b6d1b6a8039",
        "http_status_code": 201,
        "post_attempt_count": 1,
        "public_append_attempted": True,
        "public_append_may_have_occurred": True,
        "immutable": True,
        "repair_or_retry_forbidden": True,
    }


def test_response_authority_is_exact_and_drift_fails_closed() -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    PROBE._validate_response_authority(manifest)
    changed = dict(manifest)
    changed["response_contract_authority"] = dict(manifest["response_contract_authority"])
    changed["response_contract_authority"]["commit"] = "0" * 40
    with pytest.raises(PROBE.WriteProbeError, match="response-contract authority"):
        PROBE._validate_response_authority(changed)


def test_retention_policy_drift_fails_closed() -> None:
    policy = json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8"))
    PROBE._validate_retention_policy(policy)
    changed = dict(policy)
    changed["retain_raw_provider_output"] = True
    with pytest.raises(PROBE.WriteProbeError, match="retention policy"):
        PROBE._validate_retention_policy(changed)


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
    assert terminal.http_status_code == 200
    assert terminal.response_bytes == len(_valid_response())
    assert terminal.response_sha256 == PROBE._sha256(_valid_response())
    assert terminal.locator_parse_status == "STRICT_SHAPE_PARSED"
    assert terminal.locator_verification_status == "VERIFIED_PROOF_BOUND"
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


def test_formal_tuf_client_downloads_hash_prefixed_targets(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())
    terminal = _execute(tmp_path, transport)

    assert terminal.status == "WRITE_PROBE_PASSED"
    assert (
        "https://tuf-repo-cdn.sigstore.dev/targets/"
        "6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66."
        "trusted_root.json"
    ) in transport.gets
    assert (
        "https://tuf-repo-cdn.sigstore.dev/targets/"
        "0f5f38554e29e770d4d5d6f0e1b51fcbf84f61dc6934530a09b7a901eaad5bee."
        "signing_config_rekor_v2.v0.2.json"
    ) in transport.gets
    assert "https://tuf-repo-cdn.sigstore.dev/targets/trusted_root.json" not in transport.gets
    assert (
        "https://tuf-repo-cdn.sigstore.dev/targets/signing_config_rekor_v2.v0.2.json"
        not in transport.gets
    )


def test_hash_prefixed_target_404_fails_before_post(tmp_path: Path) -> None:
    class Target404Transport(FakeTransport):
        def get(self, url: str, *, timeout_seconds: int) -> bytes:
            if url.endswith(".trusted_root.json"):
                self.gets.append(url)
                raise urllib.error.HTTPError(url, 404, "not found", None, None)
            return super().get(url, timeout_seconds=timeout_seconds)

    transport = Target404Transport()
    terminal = _execute(tmp_path, transport)

    assert terminal.status == "WRITE_PROBE_PRECONDITION_FAILED"
    assert terminal.post_attempt_count == 0
    assert terminal.public_append_attempted is False
    assert terminal.public_append_may_have_occurred is False
    assert not transport.posts


def test_formal_tuf_client_contract_drift_fails_before_network(tmp_path: Path) -> None:
    manifest = json.loads((HERE / "write-probe-manifest.json").read_text(encoding="utf-8"))
    manifest["tuf_refresh"]["client"]["prefix_targets_with_hash"] = False
    transport = FakeTransport()
    terminal = PROBE._execute_probe_with_documents(
        framework_root=ROOT,
        freeze_dir=HERE,
        output_dir=tmp_path,
        owner_authorized_commit=HEAD,
        transport=transport,
        head_reader=lambda _: HEAD,
        receipt_verifier=lambda _profile, _receipt: Verified(),
        now=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
        manifest=manifest,
        policy=json.loads((HERE / "write-probe-output-policy.json").read_text(encoding="utf-8")),
    )

    assert terminal.status == "WRITE_PROBE_PRECONDITION_FAILED"
    assert not transport.gets and not transport.posts


def test_request_is_exact_hashedrekord_v002_shape(tmp_path: Path) -> None:
    transport = FakeTransport(response=_valid_response())
    _execute(tmp_path, transport)
    body = json.loads(transport.posts[0]["body"])
    assert set(body) == {"hashedRekordRequestV002"}
    entry = body["hashedRekordRequestV002"]
    assert set(entry) == {"digest", "signature"}
    assert set(entry["signature"]) == {"content", "verifier"}
    assert entry["signature"]["verifier"]["keyDetails"] == "PKIX_ECDSA_P256_SHA_256"


def test_http_201_with_valid_proof_passes(tmp_path: Path) -> None:
    transport = FakeTransport(response_code=201, response=_valid_response())
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_PASSED"
    assert terminal.http_status_code == 201
    assert len(transport.posts) == 1


def test_http_202_with_valid_proof_retains_locator_but_fails_closed(tmp_path: Path) -> None:
    transport = FakeTransport(response_code=202, response=_valid_response())
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_UNEXPECTED_STATUS_WITH_VERIFIED_LOCATOR"
    assert terminal.http_status_code == 202
    assert terminal.locator_verification_status == "VERIFIED_PROOF_BOUND"
    assert terminal.external_record_id == "ab" * 32
    assert terminal.log_index == 123
    assert len(transport.posts) == 1


def test_invalid_response_fails_closed_after_single_post(tmp_path: Path) -> None:
    transport = FakeTransport(response=b"not-json")
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_RESPONSE_INVALID"
    assert len(transport.posts) == 1
    assert terminal.public_append_may_have_occurred is True
    assert terminal.http_status_code == 200
    assert terminal.response_bytes == len(b"not-json")
    assert terminal.response_sha256 == PROBE._sha256(b"not-json")
    assert terminal.locator_verification_status == "NOT_VERIFIED"


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
    assert terminal.locator_parse_status == "STRICT_SHAPE_PARSED"
    assert terminal.locator_verification_status == "NOT_VERIFIED"
    assert terminal.external_record_id is None


def test_oversize_response_fails_closed_after_single_post(tmp_path: Path) -> None:
    raw = b"{" + b" " * 1_048_576 + b"}"
    transport = FakeTransport(response=raw)
    terminal = _execute(tmp_path, transport)
    assert terminal.status == "WRITE_PROBE_RESPONSE_INVALID"
    assert terminal.response_bytes == len(raw)
    assert terminal.response_sha256 == PROBE._sha256(raw)
    assert len(transport.posts) == 1


def test_unknown_response_field_fails_closed_before_proof_verification(tmp_path: Path) -> None:
    document = json.loads(_valid_response())
    document["unexpected"] = "synthetic"
    transport = FakeTransport(response=json.dumps(document).encode("utf-8"))
    called = False

    def verifier(_profile: Any, _receipt: Mapping[str, Any]) -> Any:
        nonlocal called
        called = True
        return Verified()

    terminal = _execute(tmp_path, transport, verifier=verifier)
    assert terminal.status == "WRITE_PROBE_RESPONSE_INVALID"
    assert terminal.locator_parse_status == "JSON_OBJECT_PARSED"
    assert called is False


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
    assert set(path.name for path in tmp_path.iterdir()) == {"rekor-v2-write-probe-terminal.json"}
    assert terminal["response_sha256"] == PROBE._sha256(_valid_response())


def test_existing_terminal_forbids_retry_before_network(tmp_path: Path) -> None:
    terminal_path = tmp_path / "rekor-v2-write-probe-terminal.json"
    terminal_path.write_text("{}", encoding="utf-8")
    transport = FakeTransport()
    with pytest.raises(PROBE.WriteProbeError, match="retry is forbidden"):
        _execute(tmp_path, transport)
    assert not transport.gets and not transport.posts


def test_terminal_retention_failure_is_fail_closed_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport(response=_valid_response())

    def reject_retention(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("synthetic retention failure")

    monkeypatch.setattr(PROBE, "_write_terminal_once", reject_retention)
    with pytest.raises(PROBE.WriteProbeError, match="terminal retention failed"):
        _execute(tmp_path, transport)
    assert len(transport.posts) == 1


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
        ("candidate_success_statuses", [200, 201, 202], "candidate success"),
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
    assert policy["retain_normalized_proof_receipt"] is False
    assert policy["retain_signature"] is False
    assert policy["retain_public_key"] is False
    assert policy["retain_canonicalized_body"] is False
    assert policy["retain_checkpoint_envelope"] is False
    assert policy["retain_proof_hash_array"] is False
    assert policy["retain_bulk_path_listing"] is False
