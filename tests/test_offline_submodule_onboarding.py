from __future__ import annotations

import configparser
import io
import subprocess
from pathlib import Path

from governance_tools.offline_submodule_onboarding import (
    SubmoduleSpec,
    onboard_offline_submodules,
)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git -C {repo} {' '.join(args)} failed: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def _init_repo(path: Path, *, filename: str) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Offline Onboarding Test")
    _git(path, "config", "user.email", "offline-onboarding@example.invalid")
    (path / filename).write_text(f"fixture for {filename}\n", encoding="utf-8")
    _git(path, "add", filename)
    _git(path, "commit", "-m", f"Add {filename}")
    return _git(path, "rev-parse", "HEAD").stdout.strip()


def _target_repo(tmp_path: Path) -> Path:
    target = tmp_path / "consumer"
    _init_repo(target, filename="README.md")
    return target


def _staged_gitmodules_urls(repo: Path) -> dict[str, str]:
    text = _git(repo, "show", ":.gitmodules").stdout
    parser = configparser.RawConfigParser(interpolation=None)
    parser.read_file(io.StringIO(text))
    return {
        section.removeprefix('submodule "').removesuffix('"'): parser.get(
            section, "url"
        )
        for section in parser.sections()
    }


def test_dry_run_validates_sources_without_mutating_target(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    framework_head = _init_repo(framework, filename="framework.txt")

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=".governance/framework",
                source=framework,
                expected_head=framework_head,
                canonical_url="ssh://git@example.invalid/governance/framework.git",
            )
        ],
        apply=False,
    )

    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.staged_files == []
    assert not (target / ".gitmodules").exists()
    assert _git(target, "status", "--porcelain=v1").stdout == ""


def test_apply_restages_canonical_gitmodules_and_asserts_all_urls(
    tmp_path: Path,
) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    contract = tmp_path / "contract-source"
    framework_head = _init_repo(framework, filename="framework.txt")
    contract_head = _init_repo(contract, filename="contract.txt")
    framework_path = ".governance/framework"
    contract_path = ".governance/domain-contracts/usb-hub-contract"
    framework_url = "ssh://git@example.invalid/governance/framework.git"
    contract_url = "ssh://git@example.invalid/contracts/usb-hub.git"

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=framework_path,
                source=framework,
                expected_head=framework_head,
                canonical_url=framework_url,
            ),
            SubmoduleSpec(
                role="domain_contract",
                path=contract_path,
                source=contract,
                expected_head=contract_head,
                canonical_url=contract_url,
            ),
        ],
        apply=True,
    )

    assert result.ok is True
    assert result.staged_files == [
        ".gitmodules",
        contract_path,
        framework_path,
    ]
    assert all(item["url_assertions_passed"] for item in result.submodules)

    staged_urls = _staged_gitmodules_urls(target)
    expected = {
        framework_path: (framework, framework_head, framework_url),
        contract_path: (contract, contract_head, contract_url),
    }
    for path, (source, head, canonical_url) in expected.items():
        key = f"submodule.{path}.url"
        nested = target / path
        assert (
            _git(target, "config", "--file", ".gitmodules", "--get", key)
            .stdout.strip()
            == canonical_url
        )
        assert staged_urls[path] == canonical_url
        assert _git(target, "config", "--get", key).stdout.strip() == canonical_url
        assert _git(nested, "remote", "get-url", "origin").stdout.strip() == canonical_url
        assert Path(
            _git(nested, "remote", "get-url", "offline-bundle").stdout.strip()
        ).resolve() == source.resolve()
        assert _git(nested, "rev-parse", "HEAD").stdout.strip() == head
        staged_record = _git(target, "ls-files", "--stage", "--", path).stdout
        assert staged_record.startswith(f"160000 {head} 0\t{path}\n")

    staged_text = _git(target, "show", ":.gitmodules").stdout
    assert str(framework.resolve()) not in staged_text
    assert str(contract.resolve()) not in staged_text


def test_apply_refuses_preexisting_staged_files(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    framework_head = _init_repo(framework, filename="framework.txt")
    staged_file = target / "member-change.txt"
    staged_file.write_text("member work\n", encoding="utf-8")
    _git(target, "add", staged_file.name)

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=".governance/framework",
                source=framework,
                expected_head=framework_head,
                canonical_url="ssh://git@example.invalid/governance/framework.git",
            )
        ],
        apply=True,
    )

    assert result.ok is False
    assert "pre-existing staged files" in result.errors[0]
    assert result.staged_files == [staged_file.name]
    assert not (target / ".gitmodules").exists()


def test_apply_refuses_preexisting_unstaged_gitmodules(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    framework_head = _init_repo(framework, filename="framework.txt")
    original = '[submodule "unrelated"]\n\tpath = unrelated\n\turl = ../unrelated\n'
    (target / ".gitmodules").write_text(original, encoding="utf-8")

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=".governance/framework",
                source=framework,
                expected_head=framework_head,
                canonical_url="ssh://git@example.invalid/governance/framework.git",
            )
        ],
        apply=True,
    )

    assert result.ok is False
    assert "pre-existing .gitmodules changes" in result.errors[0]
    assert result.staged_files == []
    assert (target / ".gitmodules").read_text(encoding="utf-8") == original
    assert not (target / ".governance").exists()


def test_local_canonical_url_is_rejected_without_mutation(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    framework_head = _init_repo(framework, filename="framework.txt")

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=".governance/framework",
                source=framework,
                expected_head=framework_head,
                canonical_url=str(framework),
            )
        ],
        apply=False,
    )

    assert result.ok is False
    assert "must be a remote URL" in result.errors[0]
    assert not (target / ".gitmodules").exists()
    assert _git(target, "status", "--porcelain=v1").stdout == ""


def test_expected_head_mismatch_fails_before_mutation(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    framework = tmp_path / "framework-source"
    _init_repo(framework, filename="framework.txt")

    result = onboard_offline_submodules(
        repo=target,
        specs=[
            SubmoduleSpec(
                role="framework",
                path=".governance/framework",
                source=framework,
                expected_head="0" * 40,
                canonical_url="ssh://git@example.invalid/governance/framework.git",
            )
        ],
        apply=True,
    )

    assert result.ok is False
    assert "source HEAD mismatch" in result.errors[0]
    assert not (target / ".gitmodules").exists()
    assert _git(target, "status", "--porcelain=v1").stdout == ""
