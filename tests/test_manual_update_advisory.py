from __future__ import annotations

import json
import subprocess
from pathlib import Path

from governance_tools.manual_update_advisory import (
    assess_manual_update_advisory,
    format_human,
)
from governance_tools.update_receipt import RECEIPT_RELATIVE_PATH


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(repo: Path, *args: str) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed.stdout.strip()


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")


def _make_framework(repo: Path) -> Path:
    framework = repo / "ai-governance-framework"
    _init_repo(framework)
    _write(framework / "governance_tools" / "__init__.py", "")
    _write(framework / "runtime_hooks" / "__init__.py", "")
    _git(framework, "add", ".")
    _git(framework, "commit", "-m", "framework A")
    return framework


def _advance_framework(framework: Path) -> str:
    _write(framework / "SECOND.txt", "second\n")
    _git(framework, "add", "SECOND.txt")
    _git(framework, "commit", "-m", "framework B")
    return _git(framework, "rev-parse", "HEAD")


def _write_lock(repo: Path, commit: str, *, note: str = "") -> None:
    payload = {"adopted_commit": commit}
    if note:
        payload["note"] = note
    _write(repo / "governance" / "framework.lock.json", json.dumps(payload, indent=2) + "\n")


class _LockConsistency:
    value = "consistent"
    reasons = ["test maturity summary says lock is consistent"]


class _ConsistentSummary:
    lock_consistency = _LockConsistency()


def test_staged_lock_change_with_mismatched_checkout_reports_advisory(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = _make_framework(repo)
    original_head = _git(framework, "rev-parse", "HEAD")
    _write_lock(repo, original_head)
    _git(repo, "add", "governance/framework.lock.json")
    _git(repo, "commit", "-m", "record lock")
    framework_head = _advance_framework(framework)

    _write_lock(repo, original_head, note="manual edit")
    _git(repo, "add", "governance/framework.lock.json")

    report = assess_manual_update_advisory(repo, framework_root=framework)
    rendered = format_human(report)

    assert original_head != framework_head
    assert report.report_only is True
    assert report.advisory_active is True
    assert report.lock_consistency == "inconsistent"
    assert report.touched_update_paths == ["governance/framework.lock.json"]
    assert "framework lock and checkout are not consistent" in rendered
    assert "advisory only; commit is not blocked" in rendered


def test_unrelated_staged_change_does_not_report_existing_lock_drift(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = _make_framework(repo)
    original_head = _git(framework, "rev-parse", "HEAD")
    _write_lock(repo, original_head)
    _git(repo, "add", "governance/framework.lock.json")
    _git(repo, "commit", "-m", "record lock")
    _advance_framework(framework)

    _write(repo / "README.md", "unrelated\n")
    _git(repo, "add", "README.md")

    report = assess_manual_update_advisory(repo, framework_root=framework)

    assert report.advisory_active is False
    assert report.touched_update_paths == []
    assert any("unrelated changes" in item for item in report.cannot_claim)
    assert format_human(report) == ""


def test_staged_dirty_lock_matching_checkout_still_reports_advisory(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = _make_framework(repo)
    framework_head = _git(framework, "rev-parse", "HEAD")
    _write_lock(repo, framework_head)
    _git(repo, "add", "governance/framework.lock.json")
    _git(repo, "commit", "-m", "record lock")

    _write_lock(repo, framework_head, note="metadata only")
    _git(repo, "add", "governance/framework.lock.json")

    report = assess_manual_update_advisory(repo, framework_root=framework)

    assert report.advisory_active is True
    assert report.lock_consistency == "inconsistent"
    assert report.touched_update_paths == ["governance/framework.lock.json"]
    assert "working-tree lock matches checkout HEAD but is not committed" in report.reasons
    assert "framework lock and checkout are not consistent" in format_human(report)


def test_staged_lock_change_without_receipt_reports_advisory_even_when_consistent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = _make_framework(repo)
    framework_head = _git(framework, "rev-parse", "HEAD")
    _write_lock(repo, framework_head)
    _git(repo, "add", "governance/framework.lock.json")
    _git(repo, "commit", "-m", "record lock")

    _write_lock(repo, framework_head, note="manual lock sync")
    _git(repo, "add", "governance/framework.lock.json")
    monkeypatch.setattr(
        "governance_tools.manual_update_advisory.build_governance_maturity_summary",
        lambda *_args, **_kwargs: _ConsistentSummary(),
    )

    report = assess_manual_update_advisory(repo, framework_root=framework)
    rendered = format_human(report)

    assert report.advisory_active is True
    assert report.signal == "missing_update_receipt"
    assert report.lock_consistency == "consistent"
    assert report.update_receipt_status == "missing"
    assert report.touched_update_paths == ["governance/framework.lock.json"]
    assert any("staged without a staged governance/.update-receipt.json" in reason for reason in report.reasons)
    assert "update_receipt_status: missing" in rendered
    assert "staged framework lock change came from updater/F-7 apply path" in report.cannot_claim


def test_staged_lock_change_with_receipt_does_not_report_when_consistent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    framework = _make_framework(repo)
    framework_head = _git(framework, "rev-parse", "HEAD")
    _write_lock(repo, framework_head)
    _write(repo / RECEIPT_RELATIVE_PATH, "{}\n")
    _git(repo, "add", "governance/framework.lock.json", RECEIPT_RELATIVE_PATH)
    _git(repo, "commit", "-m", "record lock and receipt")

    _write_lock(repo, framework_head, note="governed lock sync")
    _write(repo / RECEIPT_RELATIVE_PATH, '{"receipt_type":"ai_governance_update"}\n')
    _git(repo, "add", "governance/framework.lock.json", RECEIPT_RELATIVE_PATH)
    monkeypatch.setattr(
        "governance_tools.manual_update_advisory.build_governance_maturity_summary",
        lambda *_args, **_kwargs: _ConsistentSummary(),
    )

    report = assess_manual_update_advisory(repo, framework_root=framework)

    assert report.advisory_active is False
    assert report.lock_consistency == "consistent"
    assert report.update_receipt_status == "present"
    assert report.touched_update_paths == [
        "governance/.update-receipt.json",
        "governance/framework.lock.json",
    ]
    assert format_human(report) == ""


def test_nonstandard_gitmodules_framework_path_is_treated_as_update_path(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    _init_repo(repo)
    _write(
        repo / ".gitmodules",
        '[submodule "governance-framework"]\n'
        "\tpath = external/ai-governance-framework\n"
        "\turl = https://example.invalid/ai-governance-framework.git\n",
    )
    _write(repo / "external" / "ai-governance-framework" / "README.md", "framework marker\n")
    _git(repo, "add", ".gitmodules", "external/ai-governance-framework/README.md")

    report = assess_manual_update_advisory(repo, include_worktree=False)

    assert report.touched_update_paths == ["external/ai-governance-framework/README.md"]


def test_pre_commit_hook_invokes_manual_update_advisory_as_non_blocking() -> None:
    hook = Path("scripts/hooks/pre-commit").read_text(encoding="utf-8")

    assert 'MANUAL_UPDATE_ADVISORY_TOOL="$FRAMEWORK_ROOT/governance_tools/manual_update_advisory.py"' in hook
    assert '"$MANUAL_UPDATE_ADVISORY_TOOL"' in hook
    assert 'export PYTHONPATH="$FRAMEWORK_ROOT:$PREVIOUS_PYTHONPATH"' in hook
    assert 'export PYTHONPATH="$FRAMEWORK_ROOT"' in hook
    assert "Signal 2 reports staged framework lock" in hook
    assert "--format human || true" in hook
