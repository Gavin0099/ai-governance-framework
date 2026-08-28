from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "qualification_binding_executor", BASE / "qualification_binding_executor.py"
)
assert SPEC and SPEC.loader
EXECUTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXECUTOR)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict:
    return json.loads(
        (BASE / "binding-correction-manifest.json").read_text(encoding="utf-8")
    )


def test_frozen_files_bind_every_file_except_manifest() -> None:
    frozen = manifest()["frozen_files"]
    expected = {entry["path"] for entry in frozen}
    actual = {
        path.name
        for path in BASE.iterdir()
        if path.is_file() and path.name != "binding-correction-manifest.json"
    }
    assert expected == actual
    for entry in frozen:
        path = BASE / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert sha256(path) == entry["sha256"]


def test_freeze_is_unexecuted_and_attempt_01_is_preserved() -> None:
    value = manifest()
    assert value["status"] == "SANDBOX_QUALIFICATION_BINDING_CORRECTION_FROZEN_NOT_EXECUTED"
    assert value["qualification_contract"]["attempt_id"] == EXECUTOR.ATTEMPT_ID
    assert value["qualification_contract"]["attempt_previously_executed"] is False
    assert value["execution_authority"] == {
        "authorized": False,
        "hosted_qualification_authorized": False,
        "consumer_amendment_authorized": False,
        "randomization_authorized": False,
    }


def test_authorized_manifest_is_loaded_only_from_commit_blob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    trusted = {
        "schema": EXECUTOR.MANIFEST_SCHEMA,
        "derived_paths": {"qualification_output_root": "trusted/root"},
    }
    live = BASE / "binding-correction-manifest.json"
    assert live.is_file()
    calls: list[tuple[str, str]] = []

    def commit_blob(repo: Path, commit: str, path: str):
        calls.append((commit, path))
        return "a" * 40, json.dumps(trusted).encode()

    monkeypatch.setattr(EXECUTOR, "_commit_blob", commit_blob)
    value = EXECUTOR._authorized_manifest(tmp_path, "1" * 40)
    assert value["derived_paths"]["qualification_output_root"] == "trusted/root"
    assert calls == [("1" * 40, EXECUTOR.MANIFEST_REPO_PATH)]


@pytest.mark.parametrize(
    "bound_path",
    [
        "/etc/passwd",
        "../../escape",
        "a/../../b",
        "C:/Windows/System32",
        "C:Windows/System32",
        r"\\server\share\payload.py",
        r"\Windows\System32",
    ],
)
def test_bound_paths_reject_posix_and_windows_escape_forms(bound_path: str) -> None:
    with pytest.raises(EXECUTOR.ExecutorError, match="unsafe bound path"):
        EXECUTOR._safe_repo_path(bound_path, label="adversarial path")


def test_drive_qualified_materialization_fails_before_root_creation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "verified-root"
    with pytest.raises(EXECUTOR.ExecutorError, match="unsafe bound path"):
        EXECUTOR._materialize_sources(
            root, {"C:/Windows/System32/poison.py": b"TOKEN='poison'\n"}
        )
    assert not root.exists()


@pytest.mark.parametrize("bound_path", [r"..\..\escape", r"safe\..\..\escape"])
def test_post_join_containment_rejects_windows_separator_traversal(
    tmp_path: Path, bound_path: str
) -> None:
    root = tmp_path / "verified-root"
    with pytest.raises(EXECUTOR.ExecutorError, match="escapes verified root"):
        EXECUTOR._contained_repo_path(root, bound_path, label="materialization")


def test_runner_directory_escape_fails_before_module_import(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    imported = False

    def module_tripwire(*args, **kwargs):
        nonlocal imported
        imported = True
        raise AssertionError("module import was reached")

    monkeypatch.setattr(EXECUTOR, "_module_from_file", module_tripwire)
    with pytest.raises(EXECUTOR.ExecutorError, match="unsafe bound path"):
        EXECUTOR._load_bound_surfaces(
            tmp_path,
            {
                "sandboxed_runner_source": {
                    "directory": "C:/Windows/System32",
                    "legacy_directory": "legacy",
                }
            },
        )
    assert imported is False


@pytest.mark.parametrize(
    "bound_path",
    [
        "surface/sandboxed_runner.py",
        "surface/gate3_route_v2_codex.py",
    ],
)
def test_dirty_worktree_source_cannot_replace_bound_blob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bound_path: str
) -> None:
    trusted = b"TOKEN = 'git-object'\n"
    dirty = tmp_path / bound_path
    dirty.parent.mkdir(parents=True)
    dirty.write_bytes(b"TOKEN = 'dirty-working-tree'\n")
    oid = "b" * 40
    data = {
        "source_bindings": [
            {
                "commit": "2" * 40,
                "path": bound_path,
                "git_blob_oid": oid,
                "bytes": len(trusted),
                "sha256": hashlib.sha256(trusted).hexdigest(),
            }
        ]
    }
    monkeypatch.setattr(
        EXECUTOR, "_commit_blob", lambda repo, commit, path: (oid, trusted)
    )
    result = EXECUTOR._verified_source_blobs(tmp_path, data)
    assert result[bound_path] == trusted
    assert result[bound_path] != dirty.read_bytes()


def test_all_source_blobs_are_verified_before_materialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = b"first\n"
    second = b"second\n"
    bindings = []
    payloads = {"a/one.py": first, "b/two.py": second}
    for index, (path, payload) in enumerate(payloads.items(), start=1):
        bindings.append(
            {
                "commit": "3" * 40,
                "path": path,
                "git_blob_oid": str(index) * 40,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    def commit_blob(repo: Path, commit: str, path: str):
        index = list(payloads).index(path) + 1
        return str(index) * 40, payloads[path]

    monkeypatch.setattr(EXECUTOR, "_commit_blob", commit_blob)
    blobs = EXECUTOR._verified_source_blobs(
        tmp_path, {"source_bindings": bindings}
    )
    root = tmp_path / "materialized"
    assert not root.exists()
    EXECUTOR._materialize_sources(root, blobs)
    assert (root / "a/one.py").read_bytes() == first
    assert (root / "b/two.py").read_bytes() == second


def _write_fake_surfaces(root: Path) -> dict:
    runner_dir = root / "runner"
    legacy_dir = root / "legacy"
    runner_dir.mkdir(parents=True)
    legacy_dir.mkdir(parents=True)
    (runner_dir / "sandboxed_runner.py").write_text(
        "TOKEN='bound-runner'\n"
        "class LaunchResult:\n"
        " def __init__(self, returncode, stdout, stderr, timed_out):\n"
        "  self.returncode=returncode; self.stdout=stdout; self.stderr=stderr; self.timed_out=timed_out\n",
        encoding="utf-8",
    )
    (runner_dir / "preflight_adapter.py").write_text(
        "import sandboxed_runner as runner\nTOKEN=runner.TOKEN\n", encoding="utf-8"
    )
    (runner_dir / "qualification_contract.py").write_text(
        "TOKEN='bound-contract'\n", encoding="utf-8"
    )
    (legacy_dir / "gate3_private_rendering.py").write_text(
        "TOKEN='bound-private'\n", encoding="utf-8"
    )
    (legacy_dir / "gate3_route_v2.py").write_text(
        "import gate3_private_rendering as private_rendering\n"
        "TOKEN=private_rendering.TOKEN\n"
        "def _current_user_only(path, directory): pass\n"
        "def _verify_current_user_only(path, directory): pass\n",
        encoding="utf-8",
    )
    (legacy_dir / "gate3_route_v2_codex.py").write_text(
        "import gate3_route_v2 as route\n"
        "TOKEN=route.TOKEN\n"
        "def _run_contained(*args, **kwargs): raise AssertionError('not launched')\n",
        encoding="utf-8",
    )
    return {
        "sandboxed_runner_source": {
            "directory": "runner",
            "legacy_directory": "legacy",
        }
    }


def test_module_cache_and_sys_path_injection_cannot_select_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data = _write_fake_surfaces(tmp_path)
    poison_dir = tmp_path / "poison"
    poison_dir.mkdir()
    (poison_dir / "sandboxed_runner.py").write_text(
        "TOKEN='poison-path'\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(poison_dir))
    poison = types.ModuleType("sandboxed_runner")
    poison.TOKEN = "poison-cache"
    monkeypatch.setitem(sys.modules, "sandboxed_runner", poison)
    prior_path = list(sys.path)
    surfaces = EXECUTOR._load_bound_surfaces(tmp_path, data)
    _, runner, adapter, _, _, _, _ = surfaces
    assert runner.TOKEN == "bound-runner"
    assert adapter.TOKEN == "bound-runner"
    assert sys.modules["sandboxed_runner"] is poison
    assert sys.path == prior_path


def test_binding_failure_reads_no_auth_creates_no_roots_and_launches_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    final = tmp_path / "final"
    staging = tmp_path / "staging"
    paths = {
        "qualification_output_root": "final",
        "cli_staging_root": "staging",
        "installed_cli_source": str(tmp_path / "codex.exe"),
        "live_machine_policy": str(tmp_path / "requirements.toml"),
        "python_executable": str(tmp_path / "python.exe"),
    }
    data = {"schema": EXECUTOR.MANIFEST_SCHEMA, "derived_paths": paths}

    class AuthTripwire:
        def read_bytes(self):
            raise AssertionError("auth bytes were read")

    def launcher(*args, **kwargs):
        raise AssertionError("hosted launcher was called")

    monkeypatch.setattr(EXECUTOR, "_repo_root", lambda base: tmp_path)
    monkeypatch.setattr(EXECUTOR, "_git", lambda repo, *args, **kwargs: "4" * 40)
    monkeypatch.setattr(EXECUTOR, "_authorized_manifest", lambda repo, commit: data)
    monkeypatch.setattr(
        EXECUTOR,
        "_validate_frozen_files",
        lambda base, value: (_ for _ in ()).throw(EXECUTOR.ExecutorError("binding failed")),
    )
    with pytest.raises(EXECUTOR.ExecutorError, match="binding failed"):
        EXECUTOR.execute_qualification(
            owner_authorized_freeze_commit="4" * 40,
            auth_file=AuthTripwire(),  # type: ignore[arg-type]
            _launcher=launcher,
        )
    assert not final.exists()
    assert not staging.exists()


def test_binding_order_precedes_roots_import_auth_and_hosted_launch() -> None:
    source = (BASE / "qualification_binding_executor.py").read_text(encoding="utf-8")
    start = source.index("def execute_qualification(")
    body = source[start:]
    ordered = [
        '_git(repo, "rev-parse", "HEAD")',
        "_authorized_manifest(repo, freeze_commit)",
        "_validate_frozen_files(base, manifest)",
        "_verified_source_blobs(repo, manifest)",
        'state["bindings_verified"] = True',
        'state["staging_owned"] = True',
        "_materialize_sources(source_root, source_blobs)",
        "_load_bound_surfaces(source_root, manifest)",
        "auth_file.read_bytes()",
        'state["hosted_request_attempted"] = True',
        "completed = run.launcher(",
    ]
    positions = [body.index(token) for token in ordered]
    assert positions == sorted(positions)


def test_loader_never_uses_import_module_or_mutates_sys_path() -> None:
    source = (BASE / "qualification_binding_executor.py").read_text(encoding="utf-8")
    assert "importlib.import_module" not in source
    assert "sys.path.insert" not in source
    assert "sys.path.append" not in source


def test_attempt_output_and_staging_roots_remain_absent() -> None:
    repo = EXECUTOR._repo_root(BASE)
    paths = EXECUTOR._derived_paths(repo, manifest())
    assert not paths["qualification_output_root"].exists()
    assert not paths["cli_staging_root"].exists()


def test_source_bindings_resolve_from_exact_git_blobs() -> None:
    repo = EXECUTOR._repo_root(BASE)
    blobs = EXECUTOR._verified_source_blobs(repo, manifest())
    assert len(blobs) == len(manifest()["source_bindings"])
    assert EXECUTOR.RECEIPT_REPO_PATH in blobs
    assert hashlib.sha256(blobs[EXECUTOR.RECEIPT_REPO_PATH]).hexdigest() == EXECUTOR.EXPECTED_RECEIPT_SHA256


def test_parser_exposes_no_free_path_or_digest_override() -> None:
    actions = {action.dest for action in EXECUTOR._parser()._actions}
    assert actions == {"help", "owner_authorized_freeze_commit", "auth_file"}


def test_no_retry_download_or_persistent_policy_surface() -> None:
    source = (BASE / "qualification_binding_executor.py").read_text(encoding="utf-8")
    for forbidden in (
        "urlopen",
        "requests.",
        "urllib",
        "Set-ExecutionPolicy",
        "maximum_attempts = 2",
        "retry",
    ):
        assert forbidden not in source


def test_terminal_policy_keeps_downstream_actions_unauthorized() -> None:
    policy = json.loads((BASE / "terminal-policy.json").read_text(encoding="utf-8"))
    assert policy["no_retry_after_any_terminal"] is True
    assert policy["consumer_amendment_authorized"] is False
    assert policy["randomization_created"] is False
