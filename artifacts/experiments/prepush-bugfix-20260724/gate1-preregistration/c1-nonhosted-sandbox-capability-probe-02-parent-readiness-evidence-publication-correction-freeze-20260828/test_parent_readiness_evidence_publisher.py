from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
PUBLISHER_PATH = BASE / "parent_readiness_evidence_publisher.py"
MANIFEST_PATH = BASE / "parent-readiness-evidence-publication-manifest.json"
POLICY_PATH = BASE / "evidence-publication-policy.json"


def _load():
    spec = importlib.util.spec_from_file_location("c1_readiness_publisher_tested", PUBLISHER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _paths(tmp_path: Path, module):
    base = tmp_path / "evidence-parent"
    base.mkdir()
    root = base / "c1-nonhosted-capability-probe-02-readiness-evidence"
    return {
        "base": base,
        "root": root,
        "start": root / module.START_NAME,
        "receipt": root / module.RECEIPT_NAME,
        "terminal": root / module.TERMINAL_NAME,
        "review": root / module.REVIEW_NAME,
    }


def _receipt(module, commit: str, **updates: object) -> bytes:
    value = {
        "schema": module.RECEIPT_SCHEMA,
        "status": "PARENT_READINESS_PASSED",
        "attempt_id": module.ATTEMPT_ID,
        "execution_commit": commit,
        "sentinel_create_exclusive": True,
        "sentinel_fsync_completed": True,
        "sentinel_readback_exact": True,
        "cleanup_complete": True,
        "formal_attempt_claim_created": False,
        "hosted_requests": 0,
        "auth_payloads": 0,
        "qualification_attempts_consumed": 0,
    }
    value.update(updates)
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _launcher(result):
    calls = []

    def launch(argv, payload, cwd, environment, timeout):
        calls.append((list(argv), payload, cwd, dict(environment), timeout))
        return result

    return launch, calls


def _run(tmp_path: Path, result, *, publisher=None, module=None):
    module = module or _load()
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = _paths(tmp_path, module)
    launcher, calls = _launcher(result)
    outcome = module.run_publisher(
        repo=repo,
        commit="a" * 40,
        paths=paths,
        publisher_sha256="b" * 64,
        trusted_bootstrap=b"trusted-bootstrap",
        launcher=launcher,
        publisher=publisher or module._atomic_publish,
        clock=lambda: "2026-08-28T00:00:00Z",
    )
    return module, repo, paths, calls, outcome


def test_direct_working_tree_execution_is_rejected(tmp_path: Path) -> None:
    module = _load()
    with pytest.raises(module.EvidencePublicationError, match="streamed"):
        module.execute(repo_root=tmp_path, owner_authorized_freeze_commit="a" * 40)


def test_binding_failure_occurs_before_root_or_child(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    root = tmp_path / "must-not-exist"
    launched = False

    def launch(*args, **kwargs):
        nonlocal launched
        launched = True
        raise AssertionError("launcher reached")

    monkeypatch.setattr(module.sys, "argv", ["-"])
    monkeypatch.setitem(module.__dict__, "__file__", "<stdin>")
    monkeypatch.setattr(
        module,
        "_verify_runtime",
        lambda: (_ for _ in ()).throw(module.EvidencePublicationError("binding failed")),
    )
    with pytest.raises(module.EvidencePublicationError, match="binding failed"):
        module.execute(
            repo_root=tmp_path,
            owner_authorized_freeze_commit="a" * 40,
            launcher=launch,
        )
    assert not root.exists()
    assert launched is False


def test_success_publishes_start_then_exact_receipt_without_review(tmp_path: Path) -> None:
    module = _load()
    receipt = _receipt(module, "a" * 40)
    result = module.ChildResult(0, False, receipt, b"")
    module, repo, paths, calls, outcome = _run(tmp_path, result)

    assert outcome["status"] == "PARENT_READINESS_RECEIPT_PUBLISHED_NOT_REVIEWED"
    assert outcome["receipt_sha256"] == _sha256(receipt)
    assert paths["start"].is_file()
    assert paths["receipt"].read_bytes() == receipt
    assert not paths["terminal"].exists()
    assert not paths["review"].exists()
    assert sorted(item.name for item in paths["root"].iterdir()) == [
        module.RECEIPT_NAME,
        module.START_NAME,
    ]
    assert len(calls) == 1
    assert calls[0][0][:3] == [str(module.EXPECTED_PYTHON_PATH), "-I", "-"]
    assert calls[0][1] == b"trusted-bootstrap"
    assert not module._bootstrap_staging(repo).exists()


def test_existing_root_blocks_child_and_preserves_owner(tmp_path: Path) -> None:
    module = _load()
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = _paths(tmp_path, module)
    paths["root"].mkdir()
    owner = paths["root"] / "owner.txt"
    owner.write_bytes(b"winner")
    launcher, calls = _launcher(module.ChildResult(0, False, _receipt(module, "a" * 40), b""))
    with pytest.raises(module.EvidenceRootAlreadyClaimed):
        module.run_publisher(
            repo=repo,
            commit="a" * 40,
            paths=paths,
            publisher_sha256="b" * 64,
            trusted_bootstrap=b"trusted-bootstrap",
            launcher=launcher,
        )
    assert calls == []
    assert owner.read_bytes() == b"winner"


def test_concurrent_loser_cannot_launch_or_clean_winner(tmp_path: Path) -> None:
    module = _load()
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = _paths(tmp_path, module)
    entered = threading.Event()
    release = threading.Event()
    first_result = []

    def first_launcher(argv, payload, cwd, environment, timeout):
        entered.set()
        assert release.wait(5)
        return module.ChildResult(0, False, _receipt(module, "a" * 40), b"")

    def first_invocation():
        first_result.append(
            module.run_publisher(
                repo=repo,
                commit="a" * 40,
                paths=paths,
                publisher_sha256="b" * 64,
                trusted_bootstrap=b"trusted-bootstrap",
                launcher=first_launcher,
            )
        )

    worker = threading.Thread(target=first_invocation)
    worker.start()
    assert entered.wait(5)
    loser_launcher, loser_calls = _launcher(
        module.ChildResult(0, False, _receipt(module, "a" * 40), b"")
    )
    with pytest.raises(module.EvidenceRootAlreadyClaimed):
        module.run_publisher(
            repo=repo,
            commit="a" * 40,
            paths=paths,
            publisher_sha256="b" * 64,
            trusted_bootstrap=b"trusted-bootstrap",
            launcher=loser_launcher,
        )
    assert loser_calls == []
    assert paths["start"].is_file()
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert first_result[0]["status"] == "PARENT_READINESS_RECEIPT_PUBLISHED_NOT_REVIEWED"
    assert paths["receipt"].is_file()


@pytest.mark.parametrize(
    ("result_factory", "expected_stage"),
    [
        (lambda m: m.ChildResult(7, False, b"", b"nonzero-secret"), "transport_result"),
        (lambda m: m.ChildResult(None, True, b"", b"timeout-secret"), "transport_result"),
        (lambda m: m.ChildResult(0, False, b"{}\n", b"stderr-secret"), "transport_result"),
        (lambda m: m.ChildResult(0, False, b"not-json", b""), "receipt_validation"),
        (
            lambda m: m.ChildResult(
                0,
                False,
                _receipt(m, "a" * 40, schema="wrong.schema"),
                b"",
            ),
            "receipt_validation",
        ),
    ],
)
def test_child_failures_publish_bounded_terminal_without_raw_output(
    tmp_path: Path, result_factory, expected_stage: str
) -> None:
    module = _load()
    result = result_factory(module)
    module, _repo, paths, calls, terminal = _run(tmp_path, result)
    assert len(calls) == 1
    assert terminal["status"] == "PARENT_READINESS_PUBLICATION_FAILED"
    assert terminal["failure_stage"] == expected_stage
    assert terminal["raw_stdout_retained"] is False
    assert terminal["raw_stderr_retained"] is False
    assert terminal["transport"]["stdout_sha256"] == _sha256(result.stdout)
    assert terminal["transport"]["stderr_sha256"] == _sha256(result.stderr)
    payload = paths["terminal"].read_bytes()
    assert result.stdout not in payload or not result.stdout
    assert result.stderr not in payload or not result.stderr
    assert paths["start"].is_file()
    assert not paths["receipt"].exists()
    assert not paths["review"].exists()
    assert not any(item.name.endswith(".staging") for item in paths["root"].iterdir())


def test_receipt_publication_denial_produces_terminal(tmp_path: Path) -> None:
    module = _load()

    def publisher(root: Path, name: str, payload: bytes):
        if name == module.RECEIPT_NAME:
            raise PermissionError("receipt denied")
        return module._atomic_publish(root, name, payload)

    result = module.ChildResult(0, False, _receipt(module, "a" * 40), b"")
    module, _repo, paths, _calls, terminal = _run(tmp_path, result, publisher=publisher)
    assert terminal["failure_stage"] == "receipt_publication"
    assert terminal["exception_class"] == "PermissionError"
    assert paths["start"].is_file()
    assert paths["terminal"].is_file()
    assert not paths["receipt"].exists()


def test_terminal_publication_denial_leaves_start_not_zero_evidence(tmp_path: Path) -> None:
    module = _load()

    def publisher(root: Path, name: str, payload: bytes):
        if name in {module.RECEIPT_NAME, module.TERMINAL_NAME}:
            raise PermissionError("publication denied")
        return module._atomic_publish(root, name, payload)

    result = module.ChildResult(0, False, _receipt(module, "a" * 40), b"")
    with pytest.raises(module.TerminalPublicationError, match="durable start remains"):
        _run(tmp_path, result, publisher=publisher, module=module)
    root = tmp_path / "evidence-parent" / "c1-nonhosted-capability-probe-02-readiness-evidence"
    assert (root / module.START_NAME).is_file()
    assert not (root / module.TERMINAL_NAME).exists()
    assert sorted(item.name for item in root.iterdir()) == [module.START_NAME]


def test_start_publication_failure_launches_nothing_and_removes_empty_root(tmp_path: Path) -> None:
    module = _load()
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = _paths(tmp_path, module)
    launcher, calls = _launcher(module.ChildResult(0, False, _receipt(module, "a" * 40), b""))

    def publisher(root: Path, name: str, payload: bytes):
        raise PermissionError("start denied")

    with pytest.raises(PermissionError):
        module.run_publisher(
            repo=repo,
            commit="a" * 40,
            paths=paths,
            publisher_sha256="b" * 64,
            trusted_bootstrap=b"trusted-bootstrap",
            launcher=launcher,
            publisher=publisher,
        )
    assert calls == []
    assert not paths["root"].exists()


def test_manifest_authority_and_policy_remain_false() -> None:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    policy = json.loads(POLICY_PATH.read_bytes())
    assert manifest["framework_base"] == "0872889912ec7bc6f881e59082d726c7fc2db67e"
    assert manifest["source_bindings"][0]["git_blob_oid"] == "595e0111df1b1b8a1927609a12c9e3430a801e08"
    assert all(value is False for value in manifest["execution_authority"].values())
    assert all(value is False for value in manifest["authoring_boundary"].values())
    assert policy["review_packet_created_by_publisher"] is False
    assert policy["review_packet_approval_claim_allowed"] is False
    assert policy["hosted_requests"] == 0


def test_predecessor_sources_match_exact_git_blobs_and_contract() -> None:
    module = _load()
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    repo = next(parent for parent in BASE.parents if (parent / ".git").exists())
    blobs = {}
    for item in manifest["source_bindings"]:
        oid_result = subprocess.run(
            [
                str(module.EXPECTED_GIT_PATH),
                "--no-replace-objects",
                "-C",
                str(repo),
                "rev-parse",
                f"{item['commit']}:{item['path']}",
            ],
            capture_output=True,
            check=True,
            text=True,
        )
        assert oid_result.stderr == ""
        assert oid_result.stdout.strip() == item["git_blob_oid"]
        payload_result = subprocess.run(
            [
                str(module.EXPECTED_GIT_PATH),
                "--no-replace-objects",
                "-C",
                str(repo),
                "cat-file",
                "blob",
                item["git_blob_oid"],
            ],
            capture_output=True,
            check=True,
        )
        assert payload_result.stderr == b""
        assert len(payload_result.stdout) == item["bytes"]
        assert _sha256(payload_result.stdout) == item["sha256"]
        blobs[item["label"]] = payload_result.stdout
    paths = module._evidence_contract(manifest, blobs)
    assert paths["receipt"].name == module.RECEIPT_NAME
    assert paths["review"].name == module.REVIEW_NAME


def test_frozen_inventory_matches_exact_files_and_metadata() -> None:
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    entries = manifest["frozen_files"]
    expected = {item["path"] for item in entries} | {MANIFEST_PATH.name}
    actual = {item.name for item in BASE.iterdir() if item.name != "__pycache__"}
    assert actual == expected
    by_path = {item["path"]: item for item in entries}
    for name, item in by_path.items():
        payload = (BASE / name).read_bytes()
        assert len(payload) == item["bytes"]
        assert _sha256(payload) == item["sha256"]
        completed = subprocess.run(
            ["git", "hash-object", str(BASE / name)],
            capture_output=True,
            check=True,
            text=True,
        )
        assert completed.stdout.strip() == item["git_blob_oid"]
    assert by_path[PUBLISHER_PATH.name]["sha256"] == manifest["frozen_executor_sha256"]


def test_forbidden_raw_and_authority_surfaces_absent() -> None:
    executable = PUBLISHER_PATH.read_text(encoding="utf-8")
    assert "Set-ExecutionPolicy" not in executable
    assert "hosted request" not in executable.lower()
    assert "auth.json" not in executable
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    assert '"parent_readiness_publication_authorized": false' in manifest
    assert '"capability_probe_02_authorized": false' in manifest
