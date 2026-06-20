from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from governance_tools.checkpoint_memory_audit import audit, format_human

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "test")
    _git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "seed")
    return path


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


def _head_date(repo: Path) -> str:
    return _git(repo, "log", "-1", "--format=%cs")


def _write_memory(repo: Path, *, commit_hash: str, test_evidence: str = "") -> None:
    memory_date = _head_date(repo)
    memory = repo / "memory" / f"{memory_date}.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(
        f"# {memory_date}\n\n"
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test record\n"
        f"  commit: {commit_hash}\n"
        f"  commit_hash: {commit_hash}\n"
        "  session_id: test-session\n"
        "  memory_binding: bound\n"
        f"  test_evidence: {test_evidence}\n"
        "  next_step: none\n"
        "  plan_reconciliation: not_applicable\n",
        encoding="utf-8",
    )


def _write_memory_file(repo: Path, filename: str, *, commit_hash: str, test_evidence: str = "") -> None:
    memory = repo / "memory" / filename
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(
        "# fixture\n\n"
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test record\n"
        f"  commit: {commit_hash}\n"
        f"  commit_hash: {commit_hash}\n"
        "  session_id: test-session\n"
        "  memory_binding: bound\n"
        f"  test_evidence: {test_evidence}\n"
        "  next_step: none\n"
        "  plan_reconciliation: not_applicable\n",
        encoding="utf-8",
    )


def _codes(payload: dict) -> list[str]:
    return [finding["code"] for finding in payload["findings"]]


def test_clean_case_has_zero_findings_and_advisory_invariants(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo), test_evidence="")

    payload = audit(repo, last=1)

    assert payload["claim_class"] == "advisory"
    assert payload["blocking"] is False
    assert payload["summary"]["clean"] is True
    assert payload["summary"]["total"] == 0
    assert payload["findings"] == []


def test_commit_without_memory_fixture(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")

    payload = audit(repo, last=1)

    assert _codes(payload) == ["commit_without_memory"]
    assert payload["blocking"] is False
    assert payload["findings"][0]["severity"] == "advisory"


def test_stale_no_commit_memory_fixture(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash="NO_COMMIT")

    payload = audit(repo, last=1)

    assert "stale_no_commit_memory" in _codes(payload)
    assert payload["summary"]["by_code"]["stale_no_commit_memory"] == 1


def test_stale_no_commit_memory_ignores_unrelated_memory_dates(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo))
    _write_memory_file(repo, "2026-01-01.md", commit_hash="NO_COMMIT")

    payload = audit(repo, last=1)

    assert "stale_no_commit_memory" not in _codes(payload)


def test_unreceipted_validation_fixture(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo)[:12], test_evidence="unit tests PASS")

    payload = audit(repo, last=1)

    assert _codes(payload) == ["unreceipted_validation"]
    assert payload["summary"]["clean"] is False


def test_rollup_memory_divergence_fixture(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo))
    rollup = tmp_path / "rollup.md"
    rollup.write_text("checkpoint commit deadbee\n", encoding="utf-8")

    payload = audit(repo, last=1, rollup_files=[rollup])

    assert _codes(payload) == ["rollup_memory_divergence"]
    assert payload["findings"][0]["subject"] == "deadbee"


def test_consumer_uninstalled_fixture(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo))
    consumer = tmp_path / "consumer"
    (consumer / ".git" / "hooks").mkdir(parents=True)
    (consumer / ".git" / "hooks" / "pre-commit.sample").write_text("sample\n", encoding="utf-8")
    (consumer / ".git" / "hooks" / "pre-push.sample").write_text("sample\n", encoding="utf-8")

    payload = audit(repo, last=1, consumer_repos=[consumer])

    assert _codes(payload) == ["consumer_uninstalled"]


def test_consumer_installed_does_not_emit_uninstalled(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    _write_memory(repo, commit_hash=_head(repo))
    consumer = tmp_path / "consumer"
    (consumer / ".git" / "hooks").mkdir(parents=True)
    (consumer / ".git" / "hooks" / "pre-commit").write_text("MEMORY_WORKFLOW_TOOL=x\n", encoding="utf-8")
    (consumer / ".git" / "hooks" / "pre-push").write_text("hook\n", encoding="utf-8")
    (consumer / "AGENTS.md").write_text("memory_workflow memory/**\n", encoding="utf-8")

    payload = audit(repo, last=1, consumer_repos=[consumer])

    assert payload["summary"]["clean"] is True
    assert "consumer_uninstalled" not in _codes(payload)


def test_cli_json_and_human_outputs_are_advisory(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "governance_tools.checkpoint_memory_audit",
            "--project-root",
            str(repo),
            "--last",
            "1",
            "--format",
            "json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["claim_class"] == "advisory"
    assert payload["blocking"] is False

    human = format_human(payload)
    assert "blocking=false" in human
    assert "commit_without_memory=1" in human
