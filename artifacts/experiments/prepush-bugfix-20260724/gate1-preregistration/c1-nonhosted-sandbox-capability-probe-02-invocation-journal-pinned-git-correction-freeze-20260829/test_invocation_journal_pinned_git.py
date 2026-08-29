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


def load_named_module(name: str, filename: str):
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BOOTSTRAP = load_module()
CHILD = load_named_module(
    "c1_probe02_corrected_child_test", "capability_probe_02_pinned_git_bootstrap.py"
)
DRIVER = load_named_module(
    "c1_probe02_corrected_driver_test", "capability_probe_02_pinned_git_driver.py"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def formal_paths(manifest: dict) -> list[Path]:
    raw = manifest["derived_paths"]
    return [REPO / raw[key] for key in ("journal_root", "attempt_output_root", "cli_staging_root", "private_root")]


def synthetic_worktree(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "checkout"
    common = tmp_path / "source" / ".git"
    gitdir = common / "worktrees" / repo.name
    repo.mkdir(parents=True)
    gitdir.mkdir(parents=True)
    (repo / ".git").write_bytes(f"gitdir: {gitdir.as_posix()}\n".encode())
    (gitdir / "gitdir").write_bytes(f"{(repo / '.git').as_posix()}\n".encode())
    (gitdir / "commondir").write_bytes(b"../..\n")
    return repo.resolve(), common.resolve(), gitdir.resolve()


def identity_runner(
    repo: Path, gitdir: Path, common: Path, overrides: dict[str, Path] | None = None
):
    values = {
        "--show-toplevel": repo,
        "--absolute-git-dir": gitdir,
        "--git-common-dir": common,
    }
    values.update(overrides or {})

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            argv, 0, f"{values[argv[-1]].as_posix()}\n".encode(), b""
        )

    return run


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
    assert policy["checkout_git_entry_type"] == "NON_REPARSE_REGULAR_GITFILE"
    assert policy["checkout_root_reparse_allowed"] is False
    assert policy["git_common_directory"] == "D:/ai-governance-framework/.git"
    assert policy["pinned_git_identity_queries"] == [
        "--show-toplevel", "--absolute-git-dir", "--git-common-dir"
    ]
    assert policy["pinned_git_identity_must_equal_filesystem_contract"] is True


def test_pinned_adapter_rejects_wrong_prefix_and_command() -> None:
    runner = BOOTSTRAP._pinned_git_runner(REPO)
    with pytest.raises(BOOTSTRAP.JournalError, match="prefix"):
        runner(["git", "rev-parse", "HEAD"], input=b"", capture_output=True, check=False, timeout=30.0)
    prefix = ["git", "--no-replace-objects", "-c", f"safe.directory={REPO}", "-C", str(REPO)]
    with pytest.raises(BOOTSTRAP.JournalError, match="command"):
        runner([*prefix, "status"], input=b"", capture_output=True, check=False, timeout=30.0)
    with pytest.raises(BOOTSTRAP.JournalError, match="subprocess"):
        runner([*prefix, "rev-parse", "HEAD"], input=b"x", capture_output=True, check=False, timeout=30.0)


def test_git_environment_is_allowlisted_and_drops_repository_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selectors = {
        "GIT_DIR": "decoy/.git",
        "GIT_WORK_TREE": "decoy",
        "GIT_OBJECT_DIRECTORY": "decoy/objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "decoy/alternate",
        "GIT_COMMON_DIR": "decoy/common",
        "GIT_INDEX_FILE": "decoy/index",
        "GIT_CONFIG_SYSTEM": "decoy/system-config",
        "GIT_CONFIG_GLOBAL": "decoy/global-config",
    }
    for key, value in selectors.items():
        monkeypatch.setenv(key, value)
    environment = BOOTSTRAP._pinned_git_environment()
    for key in selectors:
        assert environment.get(key) != selectors[key]
    assert environment == {
        **{
            key: os.environ[key]
            for key in BOOTSTRAP.INHERITED_GIT_ENVIRONMENT_KEYS
            if os.environ.get(key)
        },
        **BOOTSTRAP.FIXED_GIT_ENVIRONMENT,
    }


def test_outer_child_and_nested_git_environments_drop_ambient_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "C:/hostile")
    monkeypatch.setenv("GIT_DIR", "C:/decoy/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "C:/decoy")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "C:/decoy/objects")
    outer_child = BOOTSTRAP._pinned_child_environment()
    child_git = CHILD._pinned_git_environment()
    child_driver = CHILD._pinned_child_environment("a" * 64)
    driver_git = DRIVER._pinned_git_environment()
    for environment in (outer_child, child_git, child_driver, driver_git):
        assert "PATH" not in environment
        assert "GIT_DIR" not in environment
        assert "GIT_WORK_TREE" not in environment
        assert "GIT_OBJECT_DIRECTORY" not in environment
    assert child_driver["C1_CAPABILITY_EXECUTOR_SHA256"] == "a" * 64


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_accepts_exact_bidirectional_worktree(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, gitdir = synthetic_worktree(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    module._verify_git_directory_identity(repo, identity_runner(repo, gitdir, common))


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_redirected_gitfile_before_git(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, _ = synthetic_worktree(tmp_path)
    decoy = common / "worktrees" / "authorized-decoy"
    decoy.mkdir()
    (repo / ".git").write_bytes(f"gitdir: {decoy.as_posix()}\n".encode())
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    launched = False

    def forbidden(*_: object, **__: object):
        nonlocal launched
        launched = True
        raise AssertionError("Git must not launch for redirected gitfile")

    with pytest.raises(RuntimeError, match="gitfile target mismatch"):
        module._verify_git_directory_identity(repo, forbidden)
    assert launched is False


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_reparse_gitfile_before_git(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, _ = synthetic_worktree(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    real = module._is_reparse_or_symlink
    monkeypatch.setattr(
        module, "_is_reparse_or_symlink",
        lambda path: True if path == repo / ".git" else real(path),
    )
    with pytest.raises(RuntimeError, match="non-reparse regular file"):
        module._verify_git_directory_identity(
            repo, lambda *_args, **_kwargs: pytest.fail("Git launched")
        )


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_reparse_worktree_git_directory(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, gitdir = synthetic_worktree(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    real = module._is_reparse_or_symlink
    monkeypatch.setattr(
        module, "_is_reparse_or_symlink",
        lambda path: True if path == gitdir else real(path),
    )
    with pytest.raises(RuntimeError, match="worktree Git directory must be a non-reparse directory"):
        module._verify_git_directory_identity(
            repo, lambda *_args, **_kwargs: pytest.fail("Git launched")
        )


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_reverse_gitdir_decoy(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, gitdir = synthetic_worktree(tmp_path)
    decoy = tmp_path / "decoy" / ".git"
    decoy.parent.mkdir()
    decoy.write_text("decoy\n", encoding="utf-8")
    (gitdir / "gitdir").write_bytes(f"{decoy.as_posix()}\n".encode())
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    with pytest.raises(RuntimeError, match="reverse gitfile mismatch"):
        module._verify_git_directory_identity(
            repo, lambda *_args, **_kwargs: pytest.fail("Git launched")
        )


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
@pytest.mark.parametrize(
    "selector",
    ["--show-toplevel", "--absolute-git-dir", "--git-common-dir"],
)
def test_git_directory_identity_rejects_pinned_git_identity_disagreement(
    module, selector: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, gitdir = synthetic_worktree(tmp_path)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    observed_decoy = tmp_path / "observed-decoy"
    with pytest.raises(RuntimeError, match="Git directory/worktree identity mismatch"):
        module._verify_git_directory_identity(
            repo,
            identity_runner(repo, gitdir, common, {selector: observed_decoy}),
        )


def test_live_detached_checkout_git_directory_identity_matches() -> None:
    BOOTSTRAP._verify_git_directory_identity(REPO, BOOTSTRAP._pinned_git_runner(REPO))


def test_execute_rejects_git_directory_identity_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    decoy_common = tmp_path / "decoy" / ".git"
    decoy_common.mkdir(parents=True)
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_GIT_COMMON_DIR", decoy_common)
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")

    with pytest.raises(BOOTSTRAP.JournalError, match="gitfile target mismatch"):
        BOOTSTRAP.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit=EXPECTED_COMMIT,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )

    for path in formal_paths(load_manifest()):
        assert not path.exists()


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


def test_execute_ignores_git_dir_and_work_tree_decoy_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git = str(BOOTSTRAP.EXPECTED_GIT_PATH)
    decoy = tmp_path / "authorized-decoy"
    subprocess.run([git, "init", "-q", str(decoy)], check=True)
    subprocess.run([git, "-C", str(decoy), "config", "user.name", "Probe Test"], check=True)
    subprocess.run([git, "-C", str(decoy), "config", "user.email", "probe@example.invalid"], check=True)
    (decoy / "decoy.txt").write_text("decoy\n", encoding="utf-8")
    subprocess.run([git, "-C", str(decoy), "add", "decoy.txt"], check=True)
    subprocess.run([git, "-C", str(decoy), "commit", "-q", "-m", "decoy"], check=True)
    decoy_head = subprocess.check_output([git, "-C", str(decoy), "rev-parse", "HEAD"], text=True).strip()
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(decoy / ".git" / "objects"))
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")

    with pytest.raises(BOOTSTRAP.JournalError, match="owner authority does not match repository HEAD"):
        BOOTSTRAP.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit=decoy_head,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )

    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_all_git_verification_is_adapter_threaded() -> None:
    source = (BASE / "invocation_journal_pinned_git_bootstrap.py").read_text(encoding="utf-8")
    assert '[str(EXPECTED_GIT_PATH), *argv[1:]]' in source
    assert "env=_pinned_git_environment()" in source
    assert '"git",\n            "--no-replace-objects"' in source
    assert source.count("subprocess.run(") == 2
    assert "_git(repo, git_runner" in source
    assert "_blob(repo, git_runner" in source
    assert 'subprocess.run(\n        [\n            "git"' not in source

    child_source = (BASE / "capability_probe_02_pinned_git_bootstrap.py").read_text(
        encoding="utf-8"
    )
    driver_source = (BASE / "capability_probe_02_pinned_git_driver.py").read_text(
        encoding="utf-8"
    )
    for corrected_source in (child_source, driver_source):
        assert "[str(EXPECTED_GIT_PATH), *argv[1:]]" in corrected_source
        assert "env=_pinned_git_environment()" in corrected_source
        assert 'subprocess.run(\n        [\n            "git"' not in corrected_source
        assert corrected_source.index(
            "_verify_git_directory_identity(repo, git_runner)"
        ) < corrected_source.index('_git(repo, git_runner, "rev-parse", "HEAD")')
    assert source.index("_verify_git_directory_identity(repo, git_runner)") < source.index(
        '_git(repo, git_runner, "rev-parse", "HEAD")'
    )
    assert "engine._git = pinned_engine_git" in driver_source
    assert "git_runner=git_runner" in driver_source


def test_outer_journal_launches_corrected_child_with_pinned_git_after_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = tmp_path / "fake-git"
    fake.mkdir()
    marker = fake / "fake-git-launched.txt"
    (fake / "git.cmd").write_text(
        f'@echo launched>"{marker}"\r\n@exit /b 0\r\n', encoding="utf-8"
    )
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "decoy" / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "decoy"))
    environment = BOOTSTRAP._pinned_child_environment()
    journal = tmp_path / "journal-parent" / "attempt"
    journal.parent.mkdir()
    output = tmp_path / "child-output"
    child = (BASE / BOOTSTRAP.CORRECTED_CHILD_NAME).read_bytes()
    result = BOOTSTRAP.run_journaled_child(
        journal_root=journal,
        child_output_root=output,
        commit="0" * 40,
        execution_packet_sha256="1" * 64,
        readiness_review_sha256="2" * 64,
        bootstrap_sha256="3" * 64,
        child_argv=[
            str(BOOTSTRAP.EXPECTED_PYTHON_PATH), "-I", "-",
            "--repo-root", str(REPO),
            "--owner-authorized-freeze-commit", "0" * 40,
            "--owner-authorized-readiness-review-sha256", "2" * 64,
        ],
        child_payload=child,
        cwd=REPO,
        environment=environment,
        timeout=30.0,
        clock=lambda: "2026-08-29T00:00:00Z",
    )
    assert result["status"] == "INVOCATION_CHILD_NONZERO"
    assert (journal / BOOTSTRAP.START_NAME).is_file()
    assert (journal / BOOTSTRAP.OUTCOME_NAME).is_file()
    assert not marker.exists()
    assert not output.exists()
    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_outer_inventory_selects_corrected_child_not_superseded_source() -> None:
    source = (BASE / "invocation_journal_pinned_git_bootstrap.py").read_text(
        encoding="utf-8"
    )
    assert "child = frozen.get(CORRECTED_CHILD_NAME)" in source
    assert 'sources.get("probe02_child_bootstrap")' not in source
    manifest = load_manifest()
    labels = {entry["label"] for entry in manifest["source_bindings"]}
    assert "superseded_probe02_child_bootstrap" in labels
    assert "probe02_child_bootstrap" not in labels


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
