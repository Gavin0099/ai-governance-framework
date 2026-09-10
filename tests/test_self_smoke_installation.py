"""Owner-scoped target declaration -> installation -> F-7 completion checks."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from governance_tools import f7_full_update, hook_installer
from governance_tools.hook_install_validator import validate_self_smoke_dependency
from tests.test_hook_installer import _make_framework, _write
from tests.test_f7_full_update import _init_repo, _git, _update_result


def target(tmp_path, declaration="required"):
    framework = tmp_path / "framework"
    _make_framework(framework)
    manifest = framework / ".governance/version_manifest.yaml"
    if declaration is None:
        manifest.unlink()
    else:
        _write(manifest, f"default_self_smoke_contract_dependency: {declaration}\n")
    return framework


@pytest.mark.parametrize("declaration", [None, "future", "null", "[]", "true"])
def test_unknown_is_not_legacy_or_verified(tmp_path, declaration):
    framework = target(tmp_path, declaration)
    checks, errors = validate_self_smoke_dependency(framework)
    assert checks["self_smoke_dependency_declared"] is False
    assert errors and "UNKNOWN" in errors[0]


def test_missing_and_unreadable_manifest_are_unknown(tmp_path, monkeypatch):
    framework = target(tmp_path)
    manifest = framework / ".governance/version_manifest.yaml"
    manifest.write_text("[invalid yaml", encoding="utf-8")
    assert "UNKNOWN" in validate_self_smoke_dependency(framework)[1][0]
    original = Path.read_text
    def unreadable(path, *args, **kwargs):
        if path == manifest:
            raise PermissionError("fixture")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", unreadable)
    assert "UNKNOWN" in validate_self_smoke_dependency(framework)[1][0]


@pytest.mark.parametrize("hooks_only", [False, True])
@pytest.mark.parametrize("present", [False, True])
def test_required_dependency_reaches_installer_and_cli(tmp_path, hooks_only, present, capsys):
    framework = target(tmp_path)
    if present:
        _write(framework / "contract.yaml", "name: fixture\n")
    repo = tmp_path / "consumer"
    _init_repo(repo)
    args = ["--repo", str(repo), "--framework-root", str(framework),
            "--repository-id", "example.test/consumer", "--format", "json"]
    if hooks_only:
        args.append("--hooks-only")
    exit_code = hook_installer.main(args)
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is present
    assert exit_code == (0 if present else 1)
    assert (repo / ".git/hooks/pre-push").is_file()  # execution != completion
    if not present:
        assert any("runtime dependency" in e for e in result["errors"])


def test_unknown_hook_install_is_incomplete_even_with_contract(tmp_path):
    framework = target(tmp_path, None)
    _write(framework / "contract.yaml", "name: fixture\n")
    repo = tmp_path / "consumer"
    _init_repo(repo)
    result = hook_installer.install_governance_hooks(
        repo, framework, repository_identities=["example.test/consumer"])
    assert not result.ok
    assert any("UNKNOWN" in error for error in result.errors)


@pytest.mark.parametrize("mode", ["--copilot-only", "--copilot-instructions-only", "--identity-config-only"])
def test_non_hook_modes_keep_existing_behavior(tmp_path, mode, capsys):
    framework = target(tmp_path, None)
    repo = tmp_path / "consumer"
    _init_repo(repo)
    args = ["--repo", str(repo), "--framework-root", str(framework), mode, "--format", "json"]
    if mode == "--identity-config-only":
        args += ["--repository-id", "example.test/consumer"]
    assert hook_installer.main(args) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert not (repo / ".git/hooks/pre-push").exists()


def test_explicit_not_applicable_and_non_git_copy(tmp_path):
    framework = target(tmp_path, "not_applicable")
    _init_repo(framework)
    copied = tmp_path / "copy"
    shutil.copytree(framework, copied, ignore=shutil.ignore_patterns(".git"))
    assert validate_self_smoke_dependency(framework) == validate_self_smoke_dependency(copied)
    assert validate_self_smoke_dependency(copied)[1] == []


def test_git_object_without_worktree_file_is_unavailable(tmp_path):
    framework = target(tmp_path)
    _init_repo(framework)
    _write(framework / "contract.yaml", "name: fixture\n")
    _git(framework, "add", ".")
    _git(framework, "commit", "-m", "fixture")
    _git(framework, "sparse-checkout", "set", "--no-cone", "/.governance/", "/scripts/")
    assert _git(framework, "show", "HEAD:contract.yaml")
    assert not (framework / "contract.yaml").exists()
    assert validate_self_smoke_dependency(framework)[0]["framework_file:contract.yaml"] is False


def test_unreadable_contract_does_not_pass_presence_check(tmp_path, monkeypatch):
    framework = target(tmp_path)
    contract = framework / "contract.yaml"
    _write(contract, "name: fixture\n")
    original = Path.open
    def unreadable(path, *args, **kwargs):
        if path == contract:
            raise PermissionError("fixture")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", unreadable)
    assert validate_self_smoke_dependency(framework)[0]["framework_file:contract.yaml"] is False


def test_missing_yaml_parser_returns_unknown_without_breaking_import(tmp_path):
    framework = target(tmp_path)
    result = subprocess.run(
        [sys.executable, "-S", "-c",
         "from pathlib import Path; "
         "from governance_tools.hook_install_validator import validate_self_smoke_dependency; "
         "import sys; print(validate_self_smoke_dependency(Path(sys.argv[1])))",
         str(framework)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "UNKNOWN" in result.stdout


@pytest.mark.parametrize("declaration", [None, "required"])
def test_validator_failure_remains_optional_for_readiness(tmp_path, declaration):
    from tests.test_external_repo_readiness import _make_framework as make_runtime
    from tests.test_external_repo_readiness import _make_target_repo
    from governance_tools.external_repo_readiness import assess_external_repo
    from governance_tools.hook_install_validator import validate_hook_install

    framework = tmp_path / "framework"
    repo = tmp_path / "consumer"
    make_runtime(framework)
    _make_target_repo(repo, framework)
    before = assess_external_repo(repo, framework_root=framework)
    assert before.ready and before.checks["hooks_ready"]
    manifest = framework / ".governance/version_manifest.yaml"
    if declaration is None:
        manifest.unlink()
    else:
        _write(manifest, "default_self_smoke_contract_dependency: required\n")
    validation = validate_hook_install(repo, framework_root=framework)
    assert not validation.valid
    after = assess_external_repo(repo, framework_root=framework)
    assert after.ready == before.ready
    assert after.errors == before.errors
    assert not after.checks["hooks_ready"]
    assert any("Self-smoke hook installation incomplete" in w for w in after.warnings)
    if declaration == "required":
        _write(framework / "contract.yaml", "name: fixture\n")
        assert validate_hook_install(repo, framework_root=framework).valid


def test_required_git_and_plain_directory_use_same_target_bytes(tmp_path):
    framework = target(tmp_path)
    _write(framework / "contract.yaml", "name: fixture\n")
    _init_repo(framework)
    copied = tmp_path / "plain"
    shutil.copytree(framework, copied, ignore=shutil.ignore_patterns(".git"))
    assert validate_self_smoke_dependency(framework) == validate_self_smoke_dependency(copied)
    assert validate_self_smoke_dependency(copied)[1] == []


@pytest.mark.parametrize("present", [False, True])
def test_actual_installer_result_controls_f7_final_status(tmp_path, present):
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = repo / "ai-governance-framework"
    _make_framework(framework)
    _write(framework / ".governance/version_manifest.yaml",
           "default_self_smoke_contract_dependency: required\n")
    if present:
        _write(framework / "contract.yaml", "name: fixture\n")
    _write(repo / ".gitmodules", '[submodule "ai-governance-framework"]\n'
           '\tpath = ai-governance-framework\n'
           '\turl = https://example.invalid/ai-governance-framework.git\n')
    with mock.patch.object(f7_full_update, "update_governance_submodule",
                           return_value=_update_result(repo, ok=True)):
        result = f7_full_update.run_f7_full_update(
            repo_root=repo, framework_root=framework, apply=True,
            submodule_path="ai-governance-framework")
    assert result.ok is present
    if present:
        assert result.f7_final_status != f7_full_update.BLOCKED
    else:
        assert result.f7_final_status == f7_full_update.BLOCKED
        assert result.stages["hook_validator_enforcement"] == f7_full_update.BLOCKED
        assert any("runtime dependency" in e for e in result.errors)
