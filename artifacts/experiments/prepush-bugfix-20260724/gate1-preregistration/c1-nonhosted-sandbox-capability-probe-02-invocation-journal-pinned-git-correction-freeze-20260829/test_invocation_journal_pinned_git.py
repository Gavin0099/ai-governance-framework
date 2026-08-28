from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = Path.cwd().resolve()
MANIFEST = BASE / "invocation-journal-pinned-git-manifest.json"
EXPECTED_COMMIT = "de7a3f05f196895dc55a5e406f2c4ef2f19ed23e"


def load_module():
    path = BASE / "invocation_journal_pinned_git_bootstrap.py"
    spec = importlib.util.spec_from_file_location("c1_probe02_pinned_git_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BOOTSTRAP = load_module()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def formal_paths(manifest: dict) -> list[Path]:
    raw = manifest["derived_paths"]
    return [REPO / raw[key] for key in ("journal_root", "attempt_output_root", "cli_staging_root", "private_root")]


def test_runtime_and_policy_pin_exact_git() -> None:
    manifest = load_manifest()
    runtime = manifest["runtime"]
    policy = json.loads((BASE / "pinned-git-policy.json").read_text(encoding="utf-8"))
    assert runtime["git_executable"] == BOOTSTRAP.EXPECTED_GIT_PATH.as_posix()
    assert runtime["git_executable_bytes"] == BOOTSTRAP.EXPECTED_GIT_BYTES
    assert runtime["git_executable_sha256"] == BOOTSTRAP.EXPECTED_GIT_SHA256
    assert policy["ambient_path_trusted"] is False
    assert policy["bare_git_execution_allowed"] is False
    assert policy["all_git_blob_inventory_and_source_binding_operations_use_adapter"] is True


def test_pinned_adapter_rejects_wrong_prefix_and_command() -> None:
    runner = BOOTSTRAP._pinned_git_runner(REPO)
    with pytest.raises(BOOTSTRAP.JournalError, match="prefix"):
        runner(["git", "rev-parse", "HEAD"], input=b"", capture_output=True, check=False, timeout=30.0)
    prefix = ["git", "--no-replace-objects", "-c", f"safe.directory={REPO}", "-C", str(REPO)]
    with pytest.raises(BOOTSTRAP.JournalError, match="command"):
        runner([*prefix, "status"], input=b"", capture_output=True, check=False, timeout=30.0)
    with pytest.raises(BOOTSTRAP.JournalError, match="subprocess"):
        runner([*prefix, "rev-parse", "HEAD"], input=b"x", capture_output=True, check=False, timeout=30.0)


def test_execute_ignores_malicious_path_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = tmp_path / "fake-git"
    fake.mkdir()
    marker = fake / "fake-git-launched.txt"
    (fake / "git.cmd").write_text(f'@echo launched>"{marker}"\r\n@exit /b 0\r\n', encoding="utf-8")
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")

    with pytest.raises(BOOTSTRAP.JournalError, match="owner authority does not match repository HEAD"):
        BOOTSTRAP.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit="0" * 40,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )

    assert not marker.exists()
    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_all_git_verification_is_adapter_threaded() -> None:
    source = (BASE / "invocation_journal_pinned_git_bootstrap.py").read_text(encoding="utf-8")
    assert '[str(EXPECTED_GIT_PATH), *argv[1:]]' in source
    assert '"git",\n            "--no-replace-objects"' in source
    assert source.count("subprocess.run(") == 2
    assert "_git(repo, git_runner" in source
    assert "_blob(repo, git_runner" in source
    assert 'subprocess.run(\n        [\n            "git"' not in source


def test_source_bindings_match_execution_commit() -> None:
    git = str(BOOTSTRAP.EXPECTED_GIT_PATH)
    manifest = load_manifest()
    for binding in manifest["source_bindings"]:
        oid = subprocess.check_output(
            [git, "--no-replace-objects", "-C", str(REPO), "rev-parse", f'{binding["commit"]}:{binding["path"]}'],
            text=True,
        ).strip()
        payload = subprocess.check_output([git, "--no-replace-objects", "-C", str(REPO), "cat-file", "blob", oid])
        assert binding["commit"] == EXPECTED_COMMIT
        assert oid == binding["git_blob_oid"]
        assert len(payload) == binding["bytes"]
        assert sha256(payload) == binding["sha256"]


def test_frozen_inventory_matches_files_and_blob_oids() -> None:
    git = str(BOOTSTRAP.EXPECTED_GIT_PATH)
    manifest = load_manifest()
    expected = {MANIFEST.name}
    for entry in manifest["frozen_files"]:
        path = BASE / entry["path"]
        payload = path.read_bytes()
        expected.add(entry["path"])
        assert len(payload) == entry["bytes"]
        assert sha256(payload) == entry["sha256"]
        oid = subprocess.check_output([git, "hash-object", str(path)], text=True).strip()
        assert oid == entry["git_blob_oid"]
    actual = {item.name for item in BASE.iterdir() if item.name != "__pycache__"}
    assert actual == expected
    bootstrap = (BASE / BOOTSTRAP.BOOTSTRAP_NAME).read_bytes()
    assert sha256(bootstrap) == manifest["frozen_executor_sha256"]


def test_authority_flags_false_and_roots_absent() -> None:
    manifest = load_manifest()
    assert all(value is False for value in manifest["execution_authority"].values())
    assert all(value is False for value in manifest["authoring_boundary"].values())
    for path in formal_paths(manifest):
        assert not path.exists()


def test_direct_file_execution_rejected_before_runtime_or_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "argv", [str(BASE / BOOTSTRAP.BOOTSTRAP_NAME)])
    with pytest.raises(BOOTSTRAP.JournalError, match="streamed"):
        BOOTSTRAP.execute(
            repo_root=tmp_path,
            owner_authorized_freeze_commit="0" * 40,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )
