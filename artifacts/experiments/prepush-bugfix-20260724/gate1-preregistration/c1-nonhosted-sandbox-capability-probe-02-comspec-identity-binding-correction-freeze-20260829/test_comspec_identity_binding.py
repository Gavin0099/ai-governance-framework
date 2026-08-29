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
MANIFEST = BASE / "comspec-identity-binding-manifest.json"
FROZEN_EXECUTION_CHECKOUT = Path(
    "C:/Users/daish/.codex/visualizations/2026/08/20/"
    "01a01f9a-76de-7b00-8170-409653fa352d/"
    "c1-nonhosted-capability-probe-02-execution"
)
EXPECTED_COMMIT = "0a882464833c9c023272befdc3a258409c4a0f08"
GIT_IMPLEMENTATION = Path("C:/Program Files/Git/mingw64/bin/git.exe")
WHOAMI_IMPLEMENTATION = Path("C:/Windows/System32/whoami.exe")
COMSPEC_IMPLEMENTATION = Path("C:/Windows/System32/cmd.exe")
GIT_LAUNCHERS = (
    Path("C:/Program Files/Git/cmd/git.exe"),
    Path("C:/Program Files/Git/bin/git.exe"),
)


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


def formal_paths_under(repo: Path, manifest: dict) -> list[Path]:
    raw = manifest["derived_paths"]
    return [repo / raw[key] for key in ("journal_root", "attempt_output_root", "cli_staging_root", "private_root")]


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
    policy = json.loads((BASE / "comspec-identity-binding-policy.json").read_text(encoding="utf-8"))
    assert runtime["git_executable"] == BOOTSTRAP.EXPECTED_GIT_PATH.as_posix()
    assert runtime["git_executable_bytes"] == BOOTSTRAP.EXPECTED_GIT_BYTES
    assert runtime["git_executable_sha256"] == BOOTSTRAP.EXPECTED_GIT_SHA256
    for module in (BOOTSTRAP, CHILD, DRIVER):
        assert module.EXPECTED_GIT_PATH == GIT_IMPLEMENTATION
        assert module.EXPECTED_GIT_BYTES == GIT_IMPLEMENTATION.stat().st_size
        assert module.EXPECTED_GIT_SHA256 == sha256(GIT_IMPLEMENTATION.read_bytes())
        assert module.EXPECTED_GIT_PATH not in GIT_LAUNCHERS
    assert policy["git_cmd_launcher_allowed"] is False
    assert policy["git_bin_launcher_allowed"] is False
    assert policy["git_implementation_executed_directly"] is True
    assert manifest["binding_contract"]["owner_approved_checkout_root"] == BOOTSTRAP.EXPECTED_CHECKOUT_ROOT.as_posix()
    assert policy["ambient_path_trusted"] is False
    assert policy["bare_git_execution_allowed"] is False
    assert policy["all_git_blob_inventory_and_source_binding_operations_use_adapter"] is True
    assert policy["checkout_git_entry_type"] == "NON_REPARSE_REGULAR_GITFILE"
    assert policy["owner_approved_checkout_root"] == BOOTSTRAP.EXPECTED_CHECKOUT_ROOT.as_posix()
    assert policy["alternate_valid_worktree_allowed"] is False
    assert policy["checkout_root_reparse_allowed"] is False
    assert policy["git_common_directory"] == "D:/ai-governance-framework/.git"
    assert policy["pinned_git_identity_queries"] == [
        "--show-toplevel", "--absolute-git-dir", "--git-common-dir"
    ]
    assert policy["pinned_git_identity_must_equal_filesystem_contract"] is True


def test_runtime_and_policy_pin_exact_whoami() -> None:
    manifest = load_manifest()
    runtime = manifest["runtime"]
    policy = json.loads(
        (BASE / "comspec-identity-binding-policy.json").read_text(encoding="utf-8")
    )
    assert runtime["whoami_executable"] == DRIVER.EXPECTED_WHOAMI_PATH.as_posix()
    assert runtime["whoami_executable_bytes"] == DRIVER.EXPECTED_WHOAMI_BYTES
    assert runtime["whoami_executable_sha256"] == DRIVER.EXPECTED_WHOAMI_SHA256
    assert DRIVER.EXPECTED_WHOAMI_PATH == WHOAMI_IMPLEMENTATION
    assert DRIVER.EXPECTED_WHOAMI_BYTES == WHOAMI_IMPLEMENTATION.stat().st_size
    assert DRIVER.EXPECTED_WHOAMI_SHA256 == sha256(WHOAMI_IMPLEMENTATION.read_bytes())
    assert policy["whoami_identity_source"] == "EXACT_PATH_BYTES_AND_SHA256"
    assert policy["default_unverified_identity_runner_reachable"] is False
    assert policy["identity_projection_injected_before_readiness_validation"] is True


def test_runtime_and_policy_pin_exact_comspec() -> None:
    manifest = load_manifest()
    runtime = manifest["runtime"]
    policy = json.loads(
        (BASE / "comspec-identity-binding-policy.json").read_text(encoding="utf-8")
    )
    assert runtime["comspec_executable"] == COMSPEC_IMPLEMENTATION.as_posix()
    assert runtime["comspec_executable_bytes"] == COMSPEC_IMPLEMENTATION.stat().st_size
    assert runtime["comspec_executable_sha256"] == sha256(COMSPEC_IMPLEMENTATION.read_bytes())
    for module in (BOOTSTRAP, CHILD, DRIVER):
        assert module.EXPECTED_COMSPEC_PATH == COMSPEC_IMPLEMENTATION
        assert module.EXPECTED_COMSPEC_BYTES == COMSPEC_IMPLEMENTATION.stat().st_size
        assert module.EXPECTED_COMSPEC_SHA256 == sha256(COMSPEC_IMPLEMENTATION.read_bytes())
    assert policy["comspec_identity_source"] == "EXACT_PATH_BYTES_AND_SHA256"
    assert policy["ambient_comspec_inherited"] is False
    assert policy["fixed_comspec_in_all_environments"] is True
    assert policy["outer_comspec_binding_before_git_identity"] is True
    assert policy["outer_comspec_binding_before_journal_claim"] is True
    assert policy["child_comspec_reverified"] is True
    assert policy["driver_comspec_reverified"] is True
    assert policy["engine_comspec_reverified"] is True


def test_all_active_environments_replace_hostile_ambient_comspec(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hostile = tmp_path / "hostile-cmd.exe"
    hostile.write_bytes(b"not cmd")
    monkeypatch.setenv("COMSPEC", str(hostile))
    expected = str(COMSPEC_IMPLEMENTATION)
    environments = [
        BOOTSTRAP._pinned_git_environment(),
        BOOTSTRAP._pinned_child_environment(),
        CHILD._pinned_git_environment(),
        CHILD._pinned_child_environment("3" * 64),
        DRIVER._pinned_git_environment(),
        DRIVER._pinned_identity_environment(),
    ]
    for environment in environments:
        assert environment["COMSPEC"] == expected
        assert environment["COMSPEC"] != str(hostile)
        assert "PATH" not in environment


def test_outer_wrong_comspec_digest_fails_before_git_journal_or_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched = False
    git_bound = False

    def launcher(*args: object, **kwargs: object) -> BOOTSTRAP.ChildResult:
        nonlocal launched
        launched = True
        raise AssertionError("child launcher must be unreachable")

    def git_runner(*args: object, **kwargs: object) -> object:
        nonlocal git_bound
        git_bound = True
        raise AssertionError("Git binding must be unreachable")

    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_COMSPEC_SHA256", "0" * 64)
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
    monkeypatch.setattr(BOOTSTRAP, "_pinned_git_runner", git_runner)
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")
    with pytest.raises(BOOTSTRAP.JournalError, match="COMSPEC binding mismatch"):
        BOOTSTRAP.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit=EXPECTED_COMMIT,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
            launcher=launcher,
        )
    assert launched is False
    assert git_bound is False
    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_comspec_reverification_and_engine_override_are_ordered() -> None:
    outer = (BASE / "invocation_journal_pinned_git_bootstrap.py").read_text(encoding="utf-8")
    child = (BASE / "capability_probe_02_pinned_git_bootstrap.py").read_text(encoding="utf-8")
    driver = (BASE / "capability_probe_02_pinned_git_driver.py").read_text(encoding="utf-8")
    assert outer.index('EXPECTED_COMSPEC_PATH,') < outer.index("git_runner = _pinned_git_runner(repo)")
    assert outer.index('EXPECTED_COMSPEC_PATH,') < outer.index("manifest = _manifest(repo, git_runner, commit)")
    assert outer.index('EXPECTED_COMSPEC_PATH,') < outer.index("run_journaled_child(")
    assert child.index("_verify_runtime()") < child.index("git_runner = _pinned_git_runner(repo)")
    assert driver.index('EXPECTED_COMSPEC_PATH,') < driver.index("identity = readiness_module.identity_projection")
    assert "engine._minimal_environment = pinned_engine_environment" in driver
    assert 'values["COMSPEC"] = str(EXPECTED_COMSPEC_PATH)' in driver
    assert 'if values.get("COMSPEC") != str(EXPECTED_COMSPEC_PATH) or "PATH" in values' in driver


def test_frozen_execution_checkout_identity_is_exact_unmaterialized_contract() -> None:
    manifest = load_manifest()
    policy = json.loads((BASE / "comspec-identity-binding-policy.json").read_text(encoding="utf-8"))
    for module in (BOOTSTRAP, CHILD, DRIVER):
        assert module.EXPECTED_CHECKOUT_ROOT == FROZEN_EXECUTION_CHECKOUT
    assert manifest["binding_contract"]["owner_approved_checkout_root"] == FROZEN_EXECUTION_CHECKOUT.as_posix()
    assert policy["owner_approved_checkout_root"] == FROZEN_EXECUTION_CHECKOUT.as_posix()
    assert manifest["authoring_boundary"]["execution_checkout_created"] is False
    assert policy["configured_checkout_materialized"] is False
    assert not FROZEN_EXECUTION_CHECKOUT.exists()


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
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    module._verify_git_directory_identity(repo, identity_runner(repo, gitdir, common))


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_second_valid_worktree(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    authorized, common, authorized_gitdir = synthetic_worktree(tmp_path)
    alternate = tmp_path / "alternate"
    alternate_gitdir = common / "worktrees" / alternate.name
    alternate.mkdir()
    alternate_gitdir.mkdir()
    (alternate / ".git").write_bytes(
        f"gitdir: {alternate_gitdir.as_posix()}\n".encode()
    )
    (alternate_gitdir / "gitdir").write_bytes(
        f"{(alternate / '.git').as_posix()}\n".encode()
    )
    (alternate_gitdir / "commondir").write_bytes(b"../..\n")
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", authorized)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)

    module._verify_git_directory_identity(
        authorized,
        identity_runner(authorized, authorized_gitdir, common),
    )
    with pytest.raises(RuntimeError, match="owner-approved identity"):
        module._verify_git_directory_identity(
            alternate,
            identity_runner(alternate, alternate_gitdir, common),
        )


@pytest.mark.parametrize("module", [BOOTSTRAP, CHILD, DRIVER])
def test_git_directory_identity_rejects_redirected_gitfile_before_git(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, common, _ = synthetic_worktree(tmp_path)
    decoy = common / "worktrees" / "authorized-decoy"
    decoy.mkdir()
    (repo / ".git").write_bytes(f"gitdir: {decoy.as_posix()}\n".encode())
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
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
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
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
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
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
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
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
    monkeypatch.setattr(module, "EXPECTED_CHECKOUT_ROOT", repo)
    monkeypatch.setattr(module, "EXPECTED_GIT_COMMON_DIR", common)
    observed_decoy = tmp_path / "observed-decoy"
    with pytest.raises(RuntimeError, match="Git directory/worktree identity mismatch"):
        module._verify_git_directory_identity(
            repo,
            identity_runner(repo, gitdir, common, {selector: observed_decoy}),
        )


def test_current_detached_checkout_topology_matches_when_explicitly_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
    BOOTSTRAP._verify_git_directory_identity(REPO, BOOTSTRAP._pinned_git_runner(REPO))


def test_execute_rejects_git_directory_identity_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    decoy_common = tmp_path / "decoy" / ".git"
    decoy_common.mkdir(parents=True)
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
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


def test_execute_rejects_second_worktree_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    alternate = tmp_path / "second-valid-worktree"
    alternate.mkdir()
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")

    with pytest.raises(BOOTSTRAP.JournalError, match="owner-approved identity"):
        BOOTSTRAP.execute(
            repo_root=alternate,
            owner_authorized_freeze_commit=EXPECTED_COMMIT,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
        )

    for path in formal_paths_under(alternate, load_manifest()):
        assert not path.exists()


def test_execute_ignores_malicious_path_before_any_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = tmp_path / "fake-git"
    fake.mkdir()
    marker = fake / "fake-git-launched.txt"
    (fake / "git.cmd").write_text(f'@echo launched>"{marker}"\r\n@exit /b 0\r\n', encoding="utf-8")
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
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
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
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


def test_identity_runner_rejects_wrong_argv_and_subprocess_contract() -> None:
    runner = DRIVER._pinned_identity_runner()
    expected = [str(DRIVER.EXPECTED_WHOAMI_PATH), "/user", "/fo", "csv", "/nh"]
    with pytest.raises(DRIVER.DriverError, match="identity argv mismatch"):
        runner(
            ["whoami", "/user"], input=b"", capture_output=True,
            check=False, timeout=10.0,
        )
    with pytest.raises(DRIVER.DriverError, match="identity subprocess contract mismatch"):
        runner(expected, input=b"x", capture_output=True, check=False, timeout=10.0)


def test_exact_whoami_ignores_hostile_path_and_returns_bounded_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = tmp_path / "fake-whoami"
    fake.mkdir()
    marker = fake / "fake-whoami-launched.txt"
    (fake / "whoami.cmd").write_text(
        f'@echo launched>"{marker}"\r\n@exit /b 0\r\n', encoding="utf-8"
    )
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    runner = DRIVER._pinned_identity_runner()
    completed = runner(
        [str(DRIVER.EXPECTED_WHOAMI_PATH), "/user", "/fo", "csv", "/nh"],
        input=b"", capture_output=True, check=False, timeout=10.0,
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    assert b"S-" in completed.stdout
    assert not marker.exists()


def test_wrong_whoami_digest_fails_before_formal_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(DRIVER, "EXPECTED_WHOAMI_SHA256", "0" * 64)
    monkeypatch.setattr(DRIVER, "EXPECTED_CHECKOUT_ROOT", REPO)
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(DRIVER.__dict__, "__file__", "<stdin>")
    with pytest.raises(DRIVER.DriverError, match="whoami binding mismatch"):
        DRIVER.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit=EXPECTED_COMMIT,
            owner_authorized_readiness_review_sha256="2" * 64,
        )
    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_outer_wrong_whoami_digest_fails_before_journal_or_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched = False

    def launcher(*args: object, **kwargs: object) -> BOOTSTRAP.ChildResult:
        nonlocal launched
        launched = True
        raise AssertionError("child launcher must be unreachable")

    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_WHOAMI_SHA256", "0" * 64)
    monkeypatch.setattr(BOOTSTRAP, "EXPECTED_CHECKOUT_ROOT", REPO)
    monkeypatch.setattr(sys, "argv", ["-"])
    monkeypatch.setitem(BOOTSTRAP.__dict__, "__file__", "<stdin>")
    with pytest.raises(BOOTSTRAP.JournalError, match="whoami binding mismatch"):
        BOOTSTRAP.execute(
            repo_root=REPO,
            owner_authorized_freeze_commit=EXPECTED_COMMIT,
            owner_authorized_execution_packet_sha256="1" * 64,
            owner_authorized_readiness_review_sha256="2" * 64,
            launcher=launcher,
        )
    assert launched is False
    for path in formal_paths(load_manifest()):
        assert not path.exists()


def test_driver_injects_pinned_identity_before_reviewed_readiness() -> None:
    source = (BASE / "capability_probe_02_pinned_git_driver.py").read_text(
        encoding="utf-8"
    )
    identity_call = "identity = readiness_module.identity_projection(runner=_pinned_identity_runner())"
    validation_call = "receipt = readiness_module.validate_reviewed_readiness("
    assert identity_call in source
    assert "identity=identity" in source
    assert source.index(identity_call) < source.index(validation_call)
    assert "_verify_runtime_file(\n        EXPECTED_WHOAMI_PATH" in source


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
    monkeypatch.setenv("COMSPEC", str(tmp_path / "hostile-cmd.exe"))
    environment = BOOTSTRAP._pinned_child_environment()
    assert environment["COMSPEC"] == str(COMSPEC_IMPLEMENTATION)
    assert "PATH" not in environment
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
    assert "predecessor_child_bootstrap" in labels
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
