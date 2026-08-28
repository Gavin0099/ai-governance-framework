from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
REPO = Path.cwd().resolve()
MANIFEST = BASE / "parent-readiness-trusted-bootstrap-manifest.json"
BOOTSTRAP_PATH = BASE / "parent_readiness_trusted_bootstrap.py"


def load_module():
    spec = importlib.util.spec_from_file_location("c1_parent_readiness_bootstrap_test", BOOTSTRAP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BOOTSTRAP = load_module()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_manifest(payloads: dict[str, bytes]) -> dict:
    return {
        "source_bindings": [
            {
                "label": label,
                "commit": BOOTSTRAP.FRAMEWORK_BASE,
                "path": f"bound/{label}.bin",
                "git_blob_oid": hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest(),
                "bytes": len(payload),
                "sha256": sha256(payload),
            }
            for label, payload in payloads.items()
        ]
    }


def source_payloads() -> dict[str, bytes]:
    return {
        "readiness_manifest": b'{"schema":"readiness"}\n',
        "journal_manifest": b'{"schema":"journal"}\n',
        "parent_readiness_probe": b"parent-probe\n",
        "execution_readiness": b"readiness\n",
    }


def git_oid(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def test_direct_file_launch_is_rejected_without_stdout_or_staging(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            str(BOOTSTRAP.EXPECTED_PYTHON_PATH),
            "-I",
            str(BOOTSTRAP_PATH),
            "--repo-root",
            str(tmp_path),
            "--owner-authorized-freeze-commit",
            "1" * 40,
        ],
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert completed.stdout == b""
    assert b"bootstrap must be streamed" in completed.stderr
    assert not BOOTSTRAP._staging_root(tmp_path).exists()


def test_git_uses_pinned_binary_and_disables_replace_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> object:
        observed["argv"] = argv
        observed["path"] = os.environ.get("PATH")
        return types.SimpleNamespace(returncode=0, stderr=b"", stdout=b"ok")

    monkeypatch.setenv("PATH", "C:/malicious-path")
    monkeypatch.setattr(BOOTSTRAP.subprocess, "run", fake_run)
    assert BOOTSTRAP._git(Path("C:/verified-repo"), "rev-parse", "HEAD") == "ok"
    argv = observed["argv"]
    assert isinstance(argv, list)
    assert argv[0] == str(BOOTSTRAP.EXPECTED_GIT_PATH)
    assert argv[1] == "--no-replace-objects"
    assert "C:/malicious-path" not in argv


def test_probe_execute_routes_anchor_check_around_malicious_path_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "d" * 40
    _prepare_execute(monkeypatch, commit)
    monkeypatch.setattr(BOOTSTRAP, "_verify_sources", lambda repo, manifest: source_payloads())
    staging = tmp_path / "stage"
    staging.mkdir()
    malicious_git_called = {"value": False}
    pinned_argv: list[str] = []

    def captured_default(argv: list[str], **kwargs: object) -> object:
        del argv, kwargs
        malicious_git_called["value"] = True
        raise AssertionError("PATH-selected Git executed")

    class Readiness:
        @staticmethod
        def verify_anchor_git_binding(
            repo: Path,
            value: str,
            manifest: dict,
            git_runner=captured_default,
        ) -> None:
            del manifest
            completed = git_runner(
                [
                    "git",
                    "--no-replace-objects",
                    "-c",
                    f"safe.directory={repo.resolve()}",
                    "-C",
                    str(repo.resolve()),
                    "rev-parse",
                    f"{value}:tracked-anchor",
                ],
                input=b"",
                capture_output=True,
                check=False,
                timeout=15.0,
            )
            assert completed.returncode == 0

    class Probe:
        _git = None

        @staticmethod
        def execute(*, repo_root: Path, execution_commit: str) -> dict:
            Readiness.verify_anchor_git_binding(repo_root, execution_commit, {})
            return {"status": "PARENT_READINESS_PASSED"}

    def exact_run(argv: list[str], **kwargs: object) -> object:
        del kwargs
        pinned_argv.extend(argv)
        return types.SimpleNamespace(returncode=0, stderr=b"", stdout=b"bound-oid\n")

    fake_git = tmp_path / "malicious-bin" / "git.exe"
    fake_git.parent.mkdir()
    fake_git.write_bytes(b"must-not-execute")
    monkeypatch.setenv("PATH", str(fake_git.parent))
    monkeypatch.setattr(BOOTSTRAP.subprocess, "run", exact_run)
    monkeypatch.setattr(
        BOOTSTRAP,
        "_materialize_and_import",
        lambda repo, sources: (Probe(), Readiness, staging),
    )

    receipt = BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit=commit)
    assert receipt == {"status": "PARENT_READINESS_PASSED"}
    assert malicious_git_called["value"] is False
    assert pinned_argv[0] == str(BOOTSTRAP.EXPECTED_GIT_PATH)
    assert pinned_argv[1] == "--no-replace-objects"
    assert fake_git.read_bytes() == b"must-not-execute"
    assert not staging.exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda argv: ["git", *argv[2:]], "argv contract mismatch"),
        (lambda argv: [*argv[:-1], "e" * 40 + ":tracked-anchor"], "argv contract mismatch"),
    ],
)
def test_pinned_readiness_git_runner_rejects_argv_drift(
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    commit = "d" * 40
    repo = tmp_path.resolve()
    runner = BOOTSTRAP._pinned_readiness_git_runner(repo, commit)
    argv = [
        "git",
        "--no-replace-objects",
        "-c",
        f"safe.directory={repo}",
        "-C",
        str(repo),
        "rev-parse",
        f"{commit}:tracked-anchor",
    ]
    with pytest.raises(BOOTSTRAP.BootstrapError, match=message):
        runner(
            mutation(argv),
            input=b"",
            capture_output=True,
            check=False,
            timeout=15.0,
        )


def test_dirty_worktree_sources_cannot_replace_bound_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payloads = source_payloads()
    manifest = source_manifest(payloads)
    for label in payloads:
        (tmp_path / f"{label}.bin").write_bytes(b"DIRTY-WORKTREE-CODE")

    def fake_blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
        del repo, commit
        label = Path(path).stem
        payload = payloads[label]
        return git_oid(payload), payload

    monkeypatch.setattr(BOOTSTRAP, "_blob", fake_blob)
    verified = BOOTSTRAP._verify_sources(tmp_path, manifest)
    assert verified == payloads
    assert all(payload != b"DIRTY-WORKTREE-CODE" for payload in verified.values())


@pytest.mark.parametrize("field", ["git_blob_oid", "bytes", "sha256"])
def test_source_binding_rejects_wrong_oid_bytes_or_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    payloads = source_payloads()
    manifest = source_manifest(payloads)
    entry = manifest["source_bindings"][0]
    entry[field] = "0" * 40 if field == "git_blob_oid" else (999 if field == "bytes" else "0" * 64)

    def fake_blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
        del repo, commit
        payload = payloads[Path(path).stem]
        return git_oid(payload), payload

    monkeypatch.setattr(BOOTSTRAP, "_blob", fake_blob)
    with pytest.raises(BOOTSTRAP.BootstrapError, match="source binding mismatch"):
        BOOTSTRAP._verify_sources(tmp_path, manifest)


def test_module_cache_and_sys_path_injection_cannot_select_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "checkout"
    repo.mkdir()
    malicious = tmp_path / "malicious"
    malicious.mkdir()
    (malicious / "execution_readiness.py").write_text("MARKER='path-injected'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(malicious))
    injected = types.ModuleType("execution_readiness")
    injected.MARKER = "cache-injected"
    monkeypatch.setitem(sys.modules, "execution_readiness", injected)
    sources = {
        "execution_readiness": b"MARKER='verified'\n",
        "parent_readiness_probe": (
            b"import execution_readiness\n"
            b"SELECTED=execution_readiness.MARKER\n"
            b"def execute(**kwargs):\n"
            b"    return {'status':'PARENT_READINESS_PASSED','selected':SELECTED}\n"
        ),
    }
    probe, readiness, staging = BOOTSTRAP._materialize_and_import(repo, sources)
    try:
        assert readiness.MARKER == "verified"
        assert probe.SELECTED == "verified"
        assert sys.modules["execution_readiness"] is readiness
    finally:
        BOOTSTRAP._remove_staging(staging)


def test_staging_is_outside_readiness_boundary_and_absent_before_use(tmp_path: Path) -> None:
    repo = tmp_path / "checkout"
    repo.mkdir()
    staging = BOOTSTRAP._staging_root(repo)
    execution_parent = repo / "artifacts/experiments/prepush-bugfix-20260724/gate1-execution"
    with pytest.raises(ValueError):
        staging.relative_to(execution_parent.resolve())
    assert not staging.exists()


def _prepare_execute(monkeypatch: pytest.MonkeyPatch, commit: str) -> None:
    monkeypatch.setattr(BOOTSTRAP, "__file__", "<stdin>")
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setattr(BOOTSTRAP, "_verify_runtime", lambda: None)
    monkeypatch.setattr(
        BOOTSTRAP,
        "_git",
        lambda repo, *args, binary=False: commit if args == ("rev-parse", "HEAD") else b"" if binary else "",
    )
    monkeypatch.setattr(BOOTSTRAP, "_manifest", lambda repo, value: {"schema": BOOTSTRAP.SCHEMA})
    monkeypatch.setattr(BOOTSTRAP, "_verify_inventory", lambda repo, value, manifest: None)


def test_cleanup_completes_before_readiness_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "a" * 40
    _prepare_execute(monkeypatch, commit)
    monkeypatch.setattr(BOOTSTRAP, "_verify_sources", lambda repo, manifest: source_payloads())
    staging = tmp_path / "stage"
    staging.mkdir()
    called = {"readiness": False}

    class Probe:
        _git = None

        @staticmethod
        def execute(**kwargs: object) -> dict:
            del kwargs
            assert not staging.exists()
            called["readiness"] = True
            return {"status": "PARENT_READINESS_PASSED"}

    readiness = types.SimpleNamespace(
        verify_anchor_git_binding=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        BOOTSTRAP,
        "_materialize_and_import",
        lambda repo, sources: (Probe(), readiness, staging),
    )
    receipt = BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit=commit)
    assert receipt == {"status": "PARENT_READINESS_PASSED"}
    assert called["readiness"] is True


def test_cleanup_failure_prevents_readiness_and_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "b" * 40
    _prepare_execute(monkeypatch, commit)
    monkeypatch.setattr(BOOTSTRAP, "_verify_sources", lambda repo, manifest: source_payloads())
    staging = tmp_path / "stage"
    staging.mkdir()
    called = {"readiness": False}

    class Probe:
        _git = None

        @staticmethod
        def execute(**kwargs: object) -> dict:
            del kwargs
            called["readiness"] = True
            return {"status": "PARENT_READINESS_PASSED"}

    monkeypatch.setattr(
        BOOTSTRAP,
        "_materialize_and_import",
        lambda repo, sources: (
            Probe(),
            types.SimpleNamespace(verify_anchor_git_binding=lambda *args, **kwargs: None),
            staging,
        ),
    )
    monkeypatch.setattr(
        BOOTSTRAP,
        "_remove_staging",
        lambda path: (_ for _ in ()).throw(BOOTSTRAP.BootstrapError("cleanup failed")),
    )
    with pytest.raises(BOOTSTRAP.BootstrapError, match="cleanup failed"):
        BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit=commit)
    assert called["readiness"] is False
    assert not staging.exists()


def test_binding_failure_has_zero_staging_sentinel_and_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = "c" * 40
    _prepare_execute(monkeypatch, commit)
    touched = {"materialized": False}
    sentinel = tmp_path / ".c1-probe02-parent-readiness-sentinel"
    receipt = tmp_path / "readiness-receipt.json"
    monkeypatch.setattr(
        BOOTSTRAP,
        "_verify_sources",
        lambda repo, manifest: (_ for _ in ()).throw(BOOTSTRAP.BootstrapError("source binding mismatch")),
    )
    monkeypatch.setattr(
        BOOTSTRAP,
        "_materialize_and_import",
        lambda repo, sources: touched.update(materialized=True),
    )
    with pytest.raises(BOOTSTRAP.BootstrapError, match="source binding mismatch"):
        BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit=commit)
    assert touched["materialized"] is False
    assert not BOOTSTRAP._staging_root(tmp_path).exists()
    assert not sentinel.exists()
    assert not receipt.exists()


def test_manifest_source_bindings_match_framework_base_bytes() -> None:
    manifest = json.loads(MANIFEST.read_bytes())
    for entry in manifest["source_bindings"]:
        payload = (REPO / entry["path"]).read_bytes()
        oid = subprocess.check_output(
            ["git", "--no-replace-objects", "-C", str(REPO), "rev-parse", f"{entry['commit']}:{entry['path']}"],
            text=True,
        ).strip()
        assert entry["commit"] == BOOTSTRAP.FRAMEWORK_BASE
        assert oid == entry["git_blob_oid"]
        assert len(payload) == entry["bytes"]
        assert sha256(payload) == entry["sha256"]


def test_frozen_inventory_matches_files_and_git_blob_oids() -> None:
    manifest = json.loads(MANIFEST.read_bytes())
    expected = {entry["path"] for entry in manifest["frozen_files"]}
    actual = {item.name for item in BASE.iterdir() if item.name != "__pycache__"}
    assert actual == expected | {MANIFEST.name}
    for entry in manifest["frozen_files"]:
        payload = (BASE / entry["path"]).read_bytes()
        assert len(payload) == entry["bytes"]
        assert sha256(payload) == entry["sha256"]
        assert git_oid(payload) == entry["git_blob_oid"]
    bootstrap_entry = next(
        entry for entry in manifest["frozen_files"]
        if entry["path"] == "parent_readiness_trusted_bootstrap.py"
    )
    assert manifest["frozen_executor_sha256"] == bootstrap_entry["sha256"]


def test_authority_and_authoring_boundary_are_all_false() -> None:
    manifest = json.loads(MANIFEST.read_bytes())
    assert manifest["status"] == "FROZEN_NOT_EXECUTED"
    assert set(manifest["execution_authority"].values()) == {False}
    assert set(manifest["authoring_boundary"].values()) == {False}
    binding = manifest["binding_contract"]
    assert binding["readiness_git_module_attribute_substitution_allowed"] is False
    assert binding["readiness_anchor_verifier_receives_pinned_git_runner"] is True
    assert binding["readiness_git_argv_validated_before_launch"] is True


def test_parser_exposes_no_source_or_runtime_override() -> None:
    destinations = {action.dest for action in BOOTSTRAP._parser()._actions}
    assert destinations == {
        "help",
        "repo_root",
        "owner_authorized_freeze_commit",
    }
