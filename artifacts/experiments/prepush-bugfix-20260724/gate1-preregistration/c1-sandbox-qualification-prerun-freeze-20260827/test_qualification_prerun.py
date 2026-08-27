from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "qualification_prerun_executor", BASE / "qualification_prerun_executor.py"
)
assert SPEC and SPEC.loader
EXECUTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXECUTOR)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict:
    return json.loads((BASE / "qualification-prerun-manifest.json").read_text(encoding="utf-8"))


def test_frozen_files_bind_every_file_except_manifest() -> None:
    frozen = manifest()["frozen_files"]
    expected = {entry["path"] for entry in frozen}
    actual = {
        path.name
        for path in BASE.iterdir()
        if path.is_file() and path.name != "qualification-prerun-manifest.json"
    }
    assert expected == actual
    for entry in frozen:
        path = BASE / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert sha256(path) == entry["sha256"]


def test_manifest_is_unexecuted_and_consumers_are_deferred() -> None:
    value = manifest()
    assert value["execution_authority"] == {
        "authorized": False,
        "hosted_qualification_authorized": False,
        "consumer_amendment_authorized": False,
        "randomization_authorized": False,
    }
    assert value["authoring_boundary"]["hosted_request_executed"] is False
    assert value["authoring_boundary"]["consumer_amendment_created"] is False
    assert value["authoring_boundary"]["randomization_created"] is False


def test_reconciliation_review_is_bound_to_the_actual_post_commit_review() -> None:
    review = manifest()["authority_reconciliation"]
    assert review["review_verdict"] == "APPROVED"
    assert review["review_timing"] == "POST_COMMIT_INDEPENDENT_REVIEW"
    assert review["reviewed_freeze_commit"] == "24e4d661cd080e02fbb2bdf67fef0acf0174a535"
    assert review["review_session"] == "2026-08-27-75"


def test_claim_ceiling_separates_runner_and_machine_wide_policy() -> None:
    ceiling = manifest()["claim_ceiling"]
    assert ceiling["runner_enforced_and_policy_enforced_claims_must_not_be_conflated"] is True
    assert "machine-wide rejection of the bypass flag" in ceiling["does_not_establish"]
    assert "policy enforcement outside the exact qualified runner path" in ceiling["does_not_establish"]


def test_runtime_and_machine_policy_are_exactly_frozen() -> None:
    value = manifest()
    assert value["runtime"]["cli_executable_sha256"] == EXECUTOR.EXPECTED_CLI_SHA256
    assert value["runtime"]["python_executable_sha256"] == EXECUTOR.EXPECTED_PYTHON_SHA256
    assert value["machine_policy"]["requirements_sha256"] == EXECUTOR.EXPECTED_POLICY_SHA256
    assert value["machine_policy"]["receipt_sha256"] == EXECUTOR.EXPECTED_RECEIPT_SHA256


def test_source_bindings_resolve_from_exact_git_blobs() -> None:
    repo = EXECUTOR._repo_root(BASE)
    EXECUTOR._validate_source_bindings(repo, manifest())


def test_frozen_machine_policy_receipt_is_exact_and_bounded() -> None:
    path = BASE / "machine-policy-receipt.json"
    assert path.stat().st_size == 403
    assert sha256(path) == EXECUTOR.EXPECTED_RECEIPT_SHA256
    payload = path.read_text(encoding="utf-8")
    for forbidden in ("authorization", "cookie", "credentials", "username"):
        assert forbidden not in payload.lower()


def test_parser_exposes_no_free_path_or_receipt_digest() -> None:
    actions = {action.dest for action in EXECUTOR._parser()._actions}
    assert actions == {"help", "owner_authorized_freeze_commit", "auth_file"}


@pytest.mark.parametrize(
    "key,value",
    [
        ("qualification_output_root", "../escape"),
        ("cli_staging_root", "C:/outside"),
        ("python_executable", "../python.exe"),
    ],
)
def test_derived_repo_paths_fail_closed(key: str, value: str, tmp_path: Path) -> None:
    data = json.loads(json.dumps(manifest()))
    data["derived_paths"][key] = value
    with pytest.raises(EXECUTOR.ExecutorError):
        EXECUTOR._derived_paths(tmp_path, data)


def test_output_and_staging_roots_must_share_parent(tmp_path: Path) -> None:
    data = json.loads(json.dumps(manifest()))
    data["derived_paths"]["cli_staging_root"] = "elsewhere/staging"
    with pytest.raises(EXECUTOR.ExecutorError, match="share a frozen parent"):
        EXECUTOR._derived_paths(tmp_path, data)


def test_hosted_attempt_flag_is_immediately_before_launcher() -> None:
    source = (BASE / "qualification_prerun_executor.py").read_text(encoding="utf-8")
    flag = 'state["hosted_request_attempted"] = True'
    launch = "completed = run.launcher("
    prepare = "workspace, schema_path, final_path = run.prepare()"
    assert source.index(prepare) < source.index(flag) < source.index(launch)
    between = source[source.index(flag) : source.index(launch)]
    assert between.strip() == flag


def test_cleanup_precedes_pass_terminal() -> None:
    source = (BASE / "qualification_prerun_executor.py").read_text(encoding="utf-8")
    cleanup = 'staging_root.rmdir()'
    passed = 'status="SANDBOXED_RUNNER_QUALIFIED_NOT_RANDOMIZED"'
    assert source.index(cleanup) < source.index(passed)


def test_no_retry_download_or_persistent_policy_surface() -> None:
    source = (BASE / "qualification_prerun_executor.py").read_text(encoding="utf-8")
    for forbidden in (
        "urlopen",
        "requests.",
        "urllib",
        "Set-ExecutionPolicy",
        "maximum_attempts = 2",
        "retry",
    ):
        assert forbidden not in source


def test_exact_cli_staging_is_exclusive_and_non_overwriting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.exe"
    target = tmp_path / "stage" / "codex.exe"
    source.write_bytes(b"exact-cli")
    monkeypatch.setattr(EXECUTOR, "EXPECTED_CLI_BYTES", len(b"exact-cli"))
    monkeypatch.setattr(EXECUTOR, "EXPECTED_CLI_SHA256", hashlib.sha256(b"exact-cli").hexdigest())
    EXECUTOR._raw_copy_exact(source, target)
    assert target.read_bytes() == b"exact-cli"
    with pytest.raises(FileExistsError):
        EXECUTOR._raw_copy_exact(source, target)
    assert target.read_bytes() == b"exact-cli"


def test_wrong_authority_cannot_publish(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    final = tmp_path / "final"
    staging = tmp_path / "staging"
    paths = {
        "qualification_output_root": final,
        "cli_staging_root": staging,
        "python_executable": tmp_path / "python.exe",
        "installed_cli_source": tmp_path / "codex.exe",
        "live_machine_policy": tmp_path / "requirements.toml",
    }
    monkeypatch.setattr(EXECUTOR, "_repo_root", lambda base: tmp_path)
    monkeypatch.setattr(EXECUTOR, "_load_json", lambda path: {"schema": EXECUTOR.MANIFEST_SCHEMA})
    monkeypatch.setattr(EXECUTOR, "_derived_paths", lambda repo, data: paths)
    monkeypatch.setattr(EXECUTOR, "_validate_frozen_files", lambda base, data: None)
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda repo, data: None)
    monkeypatch.setattr(EXECUTOR, "_git", lambda repo, *args, **kwargs: "1" * 40)
    with pytest.raises(EXECUTOR.ExecutorError, match="owner authority"):
        EXECUTOR.execute_qualification(
            owner_authorized_freeze_commit="0" * 40,
            auth_file=tmp_path / "auth.json",
        )
    assert not final.exists()
    assert not staging.exists()


def test_preexisting_staging_is_not_deleted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    final = tmp_path / "final"
    staging = tmp_path / "staging"
    staging.mkdir()
    marker = staging / "owner-data.txt"
    marker.write_text("preserve", encoding="utf-8")
    paths = {
        "qualification_output_root": final,
        "cli_staging_root": staging,
        "python_executable": tmp_path / "python.exe",
        "installed_cli_source": tmp_path / "codex.exe",
        "live_machine_policy": tmp_path / "requirements.toml",
    }

    class Contract:
        @staticmethod
        def build_terminal(**kwargs) -> bytes:
            return (json.dumps({"status": kwargs["status"]}, separators=(",", ":")) + "\n").encode()

    monkeypatch.setattr(EXECUTOR, "_repo_root", lambda base: tmp_path)
    monkeypatch.setattr(EXECUTOR, "_load_json", lambda path: {"schema": EXECUTOR.MANIFEST_SCHEMA})
    monkeypatch.setattr(EXECUTOR, "_derived_paths", lambda repo, data: paths)
    monkeypatch.setattr(EXECUTOR, "_validate_frozen_files", lambda base, data: None)
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda repo, data: None)
    monkeypatch.setattr(EXECUTOR, "_git", lambda repo, *args, **kwargs: "1" * 40)
    monkeypatch.setattr(
        EXECUTOR,
        "_load_surfaces",
        lambda repo, data: (None, None, None, Contract, None, None, None),
    )
    terminal = EXECUTOR.execute_qualification(
        owner_authorized_freeze_commit="1" * 40,
        auth_file=tmp_path / "auth.json",
    )
    assert terminal["status"] == "SANDBOXED_RUNNER_BINDING_MISMATCH"
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_terminal_policy_keeps_consumer_amendment_separate() -> None:
    policy = json.loads((BASE / "terminal-policy.json").read_text(encoding="utf-8"))
    assert policy["consumer_amendment_authorized"] is False
    assert policy["randomization_created"] is False
    assert policy["no_retry_after_any_terminal"] is True
