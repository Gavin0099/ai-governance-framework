from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import governance_tools.composite_workspace_census as census


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(path: Path, *, remote_url: str | None = None) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "--quiet")
    _write(path / "README.md", f"# {path.name}\n")
    _git(path, "add", "README.md")
    _git(
        path,
        "-c",
        "user.name=Composite Census Test",
        "-c",
        "user.email=composite-census@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "initial",
    )
    if remote_url:
        _git(path, "remote", "add", "origin", remote_url)
    return path


def _fake_maturity(status: str, gaps: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        user_facing_status=SimpleNamespace(value=status),
        missing_surfaces=gaps,
        capability_states={
            "repo_governance_instructions": SimpleNamespace(
                state="Present" if "repo_specific_agents_rules" not in gaps else "Missing"
            ),
            "domain_contract": SimpleNamespace(
                state="Present" if "domain_contract" not in gaps else "Missing"
            ),
        },
        claim_ceiling=SimpleNamespace(value="governance_assisted"),
        cannot_claim=["full governance adoption"],
    )


def _patch_maturity(monkeypatch: pytest.MonkeyPatch, states: dict[str, tuple[str, list[str]]]) -> None:
    def fake_build(repo_root: Path) -> SimpleNamespace:
        status, gaps = states[Path(repo_root).name]
        return _fake_maturity(status, gaps)

    monkeypatch.setattr(census, "build_governance_maturity_summary", fake_build)


def _repo_snapshot(repo: Path) -> tuple[str, str]:
    return _git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain=v1")


def test_census_uses_only_explicit_allowlist_and_leads_with_four_plain_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(
        tmp_path / "etoken-system-art",
        remote_url="https://gitlab.example/etoken/system.git",
    )
    server = _make_repo(
        tmp_path / "etoken-server-art",
        remote_url="https://gitlab.example/etoken/server.git",
    )
    client = _make_repo(
        tmp_path / "etoken-client-art",
        remote_url="https://gitlab.example/etoken/client.git",
    )
    ghost = _make_repo(tmp_path / "etoken-dongle")
    _write(
        coordinator / "eToken_System_ART.code-workspace",
        json.dumps({"folders": [{"path": str(ghost)}]}),
    )
    _patch_maturity(
        monkeypatch,
        {
            coordinator.name: ("partial", ["domain_contract"]),
            server.name: ("not_governed", ["repo_specific_agents_rules", "domain_contract"]),
            client.name: ("minimal", ["validator_surface"]),
        },
    )
    before = {path.name: _repo_snapshot(path) for path in (coordinator, server, client, ghost)}

    report = census.build_composite_workspace_census(
        coordinator,
        [server, client],
    )

    assert [Path(member.git_root).name for member in report.members] == [
        coordinator.name,
        client.name,
        server.name,
    ]
    assert ghost.name not in [Path(member.git_root).name for member in report.members]
    assert all(member.membership_status == "unratified" for member in report.members)
    assert all(member.git_identity_status == "resolved" for member in report.members)
    assert report.members[0].governance_status == "partial"
    assert report.members[0].readiness_gaps == ["domain_contract"]
    assert [member.git_identity for member in report.members] == [
        "https://gitlab.example/etoken/system.git",
        "https://gitlab.example/etoken/client.git",
        "https://gitlab.example/etoken/server.git",
    ]

    human = census.format_human(report)
    first_lines = human.splitlines()[:5]
    assert first_lines[0] == "[operator_decision_summary]"
    assert first_lines[1].startswith("1. 這次檢查了什麼：")
    assert first_lines[2].startswith("2. 現在哪些 repo 可用：")
    assert first_lines[3].startswith("3. 哪些 repo 還缺什麼：")
    assert first_lines[4].startswith("4. 下一步應做什麼：")
    assert "沒有從 .code-workspace" in first_lines[1]
    assert "本工具不執行 F-7、commit 或 push" in first_lines[4]

    payload = json.loads(census.format_json(report))
    assert payload["report_only"] is True
    assert payload["authority_model"] == "explicit_allowlist_discovery_only"
    assert payload["operator_decision_summary"]["checked"] == report.operator_decision_summary.checked
    assert [Path(member["git_root"]).name for member in payload["members"]] == [
        coordinator.name,
        client.name,
        server.name,
    ]
    after = {path.name: _repo_snapshot(path) for path in (coordinator, server, client, ghost)}
    assert after == before


def test_census_reports_staged_unstaged_and_untracked_without_modifying_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    sibling = _make_repo(tmp_path / "sibling")
    _patch_maturity(
        monkeypatch,
        {
            coordinator.name: ("partial", []),
            sibling.name: ("partial", []),
        },
    )
    _write(coordinator / "README.md", "unstaged\n")
    _write(coordinator / "staged.txt", "staged\n")
    _git(coordinator, "add", "staged.txt")
    _write(coordinator / "untracked.txt", "untracked\n")
    before = _repo_snapshot(coordinator)

    report = census.build_composite_workspace_census(coordinator, [sibling])

    dirty = report.members[0].dirty_state
    assert dirty is not None
    assert dirty.clean is False
    assert dirty.staged is True
    assert dirty.unstaged is True
    assert dirty.untracked is True
    assert dirty.conflicted is False
    assert _repo_snapshot(coordinator) == before


def test_census_keeps_missing_sibling_visible_without_failing_coordinator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    missing = tmp_path / "missing-sibling"
    _patch_maturity(monkeypatch, {coordinator.name: ("partial", ["domain_contract"])})

    report = census.build_composite_workspace_census(coordinator, [missing])

    assert report.members[0].git_root is not None
    assert report.members[1].git_root is None
    assert report.members[1].membership_status == "discovered_candidate"
    assert report.members[1].errors == ["candidate path is missing or is not a directory"]
    assert "無法檢查" in report.operator_decision_summary.usable_now


def test_census_marks_duplicate_git_root_without_claiming_second_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    nested = coordinator / "nested"
    nested.mkdir()
    _patch_maturity(monkeypatch, {coordinator.name: ("partial", [])})

    report = census.build_composite_workspace_census(coordinator, [nested])

    assert report.members[1].git_root == report.members[0].git_root
    assert report.members[1].membership_status == "duplicate_identity"
    assert any("same Git root already listed" in item for item in report.members[1].errors)


def test_census_rejects_symlink_path_before_git_or_maturity_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    outside = _make_repo(tmp_path / "outside" / "sibling")
    linked = tmp_path / "workspace" / "linked-sibling"
    linked.mkdir(parents=True)

    original_resolve = Path.resolve
    linked_lexical = os.path.normcase(os.path.abspath(os.fspath(linked)))
    outside_resolved = original_resolve(outside)

    def resolve_with_simulated_junction(self: Path, strict: bool = False) -> Path:
        lexical = os.path.normcase(os.path.abspath(os.fspath(self)))
        if lexical == linked_lexical:
            return outside_resolved
        return original_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_with_simulated_junction)

    inspected: list[Path] = []

    def fake_build(repo_root: Path) -> SimpleNamespace:
        inspected.append(Path(repo_root).resolve())
        return _fake_maturity("partial", [])

    monkeypatch.setattr(census, "build_governance_maturity_summary", fake_build)

    report = census.build_composite_workspace_census(coordinator, [linked])

    assert inspected == [coordinator.resolve()]
    assert report.members[1].git_root is None
    assert report.members[1].membership_status == "discovered_candidate"
    assert report.members[1].resolved_path == str(outside.resolve())
    assert report.members[1].errors == [
        "candidate path crosses a symlink or junction boundary; no repository inspection performed"
    ]


def test_same_named_repositories_keep_distinct_git_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    first = _make_repo(
        tmp_path / "left" / "service",
        remote_url="https://gitlab.example/left/service.git",
    )
    second = _make_repo(
        tmp_path / "right" / "service",
        remote_url="https://gitlab.example/right/service.git",
    )
    _patch_maturity(
        monkeypatch,
        {
            coordinator.name: ("partial", []),
            first.name: ("minimal", ["domain_contract"]),
        },
    )

    report = census.build_composite_workspace_census(coordinator, [second, first])

    sibling_members = report.members[1:]
    assert [member.membership_status for member in sibling_members] == [
        "unratified",
        "unratified",
    ]
    assert len({member.git_root for member in sibling_members}) == 2
    assert {member.git_identity for member in sibling_members} == {
        "https://gitlab.example/left/service.git",
        "https://gitlab.example/right/service.git",
    }


def test_different_member_remotes_remain_per_member_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(
        tmp_path / "coordinator",
        remote_url="https://gitlab.example/workspace/coordinator.git",
    )
    sibling = _make_repo(
        tmp_path / "sibling",
        remote_url="https://github.example/workspace/sibling.git",
    )
    _patch_maturity(
        monkeypatch,
        {
            coordinator.name: ("partial", []),
            sibling.name: ("partial", []),
        },
    )

    report = census.build_composite_workspace_census(coordinator, [sibling])

    assert report.members[0].git_identity == (
        "https://gitlab.example/workspace/coordinator.git"
    )
    assert report.members[1].git_identity == "https://github.example/workspace/sibling.git"
    assert report.members[0].git_identity != report.members[1].git_identity


def test_census_reports_ambiguous_remote_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _make_repo(
        tmp_path / "coordinator",
        remote_url="https://gitlab.example/example/repo.git",
    )
    sibling = _make_repo(tmp_path / "sibling")
    _git(coordinator, "remote", "add", "github", "https://github.example/example/repo.git")
    _patch_maturity(
        monkeypatch,
        {
            coordinator.name: ("partial", []),
            sibling.name: ("not_governed", ["domain_contract"]),
        },
    )

    report = census.build_composite_workspace_census(coordinator, [sibling])

    assert report.members[0].git_identity_status == "ambiguous"
    assert report.members[0].git_identity is None
    assert len(report.members[0].remotes) == 2
    assert any("not uniquely resolved" in item for item in report.members[0].warnings)


def test_minimal_real_repo_uses_existing_maturity_summary_for_gaps(tmp_path: Path) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    sibling = _make_repo(tmp_path / "sibling")

    report = census.build_composite_workspace_census(coordinator, [sibling])

    assert report.members[0].governance_status in {"minimal", "not_governed", "partial"}
    assert report.members[0].readiness_gaps
    assert report.members[1].readiness_gaps


def test_cli_returns_success_for_report_with_sibling_gaps_and_two_for_bad_coordinator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    coordinator = _make_repo(tmp_path / "coordinator")
    sibling = tmp_path / "missing-sibling"
    _patch_maturity(monkeypatch, {coordinator.name: ("partial", ["domain_contract"])})

    assert census.main(
        [
            "--coordinator",
            str(coordinator),
            "--sibling",
            str(sibling),
            "--format",
            "human",
        ]
    ) == 0
    assert capsys.readouterr().out.startswith("[operator_decision_summary]\n")

    assert census.main(
        [
            "--coordinator",
            str(tmp_path / "missing-coordinator"),
            "--sibling",
            str(sibling),
            "--format",
            "json",
        ]
    ) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["members"][0]["git_root"] is None


def test_git_runner_rejects_mutating_commands(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")

    with pytest.raises(ValueError, match="non-read-only git command rejected"):
        census._run_git(repo, ["add", "."])
    with pytest.raises(ValueError, match="non-read-only git command rejected"):
        census._run_git(repo, ["remote", "add", "other", "https://example.invalid/repo.git"])
