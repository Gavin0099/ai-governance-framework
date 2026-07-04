from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from governance_tools.memory_workflow import assess_memory_workflow


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework_surface(repo: Path, prefix: str = "") -> None:
    root = repo / prefix if prefix else repo
    _write(root / "governance" / "MEMORY_PROTOCOL.md", "# Memory Protocol\n")
    _write(root / "governance_tools" / "memory_record.py", "# writer\n")
    _write(root / "governance_tools" / "memory_authority_guard.py", "# guard\n")


def _write_canonical_memory(repo: Path) -> None:
    session_id = "test-session"
    _write(
        repo / "artifacts" / "runtime" / "closeouts" / f"{session_id}.json",
        f'{{"session_id": "{session_id}"}}\n',
    )
    _write(
        repo / "memory" / "2026-06-09.md",
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test\n"
        f"  session_id: {session_id}\n"
        "  memory_binding: bound\n"
        "  test_evidence: test\n"
        "  next_step: none\n",
    )


def test_memory_diff_requires_workflow(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=["memory/2026-06-09.md"],
    )

    assert result.status == "memory_workflow_required"
    assert result.task_classification == "governed_memory_task"
    assert result.memory_files_in_diff == ["memory/2026-06-09.md"]
    assert result.canonical_writer_required is True
    assert result.completion_claim_allowed is False


def test_non_memory_diff_does_not_require_workflow(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(tmp_path, changed_files=["README.md"])

    assert result.status == "no_memory_workflow_required"
    assert result.task_classification == "not_memory_task"
    assert result.memory_files_in_diff == []
    assert result.canonical_writer_required is False
    assert result.completion_claim_allowed is True


def test_writer_and_guard_paths_reported(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(tmp_path, changed_files=["memory/2026-06-09.md"])

    assert result.memory_protocol_path == "governance/MEMORY_PROTOCOL.md"
    assert result.canonical_writer_path == "governance_tools/memory_record.py"
    assert result.authority_guard_path == "governance_tools/memory_authority_guard.py"


def test_submodule_consumer_path_supported(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path, "ai-governance-framework")

    result = assess_memory_workflow(tmp_path, changed_files=["memory/2026-06-09.md"])

    assert result.memory_protocol_path == "ai-governance-framework/governance/MEMORY_PROTOCOL.md"
    assert result.canonical_writer_path == "ai-governance-framework/governance_tools/memory_record.py"
    assert result.authority_guard_path == "ai-governance-framework/governance_tools/memory_authority_guard.py"


def test_external_hook_framework_root_path_supported(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    framework = tmp_path / "framework"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, stdout=subprocess.PIPE)
    _make_framework_surface(framework)
    _write(repo / ".git" / "hooks" / "ai-governance-framework-root", str(framework))

    result = assess_memory_workflow(repo, changed_files=["memory/2026-06-09.md"])

    assert result.memory_protocol_path is not None
    assert result.memory_protocol_path.endswith("framework/governance/MEMORY_PROTOCOL.md")
    assert result.canonical_writer_path is not None
    assert result.canonical_writer_path.endswith("framework/governance_tools/memory_record.py")
    assert result.authority_guard_path is not None
    assert result.authority_guard_path.endswith("framework/governance_tools/memory_authority_guard.py")
    assert "canonical writer not found" not in result.warnings


def test_possible_memory_task_is_advisory_without_memory_diff(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=[],
        task_text="please remember this in repo memory",
    )

    assert result.status == "possible_memory_task"
    assert result.task_classification == "possible_memory_task"
    assert result.completion_claim_allowed is True
    assert result.canonical_writer_required is False


def test_personal_preference_memory_phrase_is_currently_keyword_advisory(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=[],
        task_text="remember my editor theme preference is blue",
    )

    assert result.status == "possible_memory_task"
    assert result.task_classification == "possible_memory_task"
    assert result.completion_claim_allowed is True
    assert result.canonical_writer_required is False


def test_reminder_phrase_without_memory_keyword_is_currently_not_memory(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=[],
        task_text="remind me to buy milk next week",
    )

    assert result.status == "no_memory_workflow_required"
    assert result.task_classification == "not_memory_task"
    assert result.completion_claim_allowed is True
    assert result.canonical_writer_required is False


def test_cross_repo_habit_memory_phrase_is_currently_keyword_advisory(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=[],
        task_text="remember across repos that I prefer npm.cmd on Windows",
    )

    assert result.status == "possible_memory_task"
    assert result.task_classification == "possible_memory_task"
    assert result.completion_claim_allowed is True
    assert result.canonical_writer_required is False


def test_run_guard_reports_summary_and_allows_clean_memory_completion(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write_canonical_memory(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=["memory/2026-06-09.md"],
        run_guard_check=True,
    )

    assert result.guard_ran is True
    assert result.guard_summary["non_canonical_writer"] == 0
    assert result.guard_summary["active_non_canonical_writer"] == 0
    assert result.guard_summary["unbound_memory"] == 0
    assert result.guard_summary["test_evidence_provenance_not_found"] == 0
    assert result.blockers == []
    assert result.completion_claim_allowed is True


def test_run_guard_reports_test_evidence_provenance_warning_without_blocking(
    tmp_path: Path,
) -> None:
    _make_framework_surface(tmp_path)
    session_id = "test-session"
    _write(
        tmp_path / "artifacts" / "runtime" / "closeouts" / f"{session_id}.json",
        f'{{"session_id": "{session_id}"}}\n',
    )
    _write(
        tmp_path / "memory" / "2026-06-09.md",
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: test\n"
        f"  session_id: {session_id}\n"
        "  memory_binding: bound\n"
        "  test_evidence: PASS: 67 passed\n"
        "  next_step: none\n",
    )

    result = assess_memory_workflow(
        tmp_path,
        changed_files=["memory/2026-06-09.md"],
        run_guard_check=True,
    )

    assert result.guard_summary["test_evidence_provenance_not_found"] == 1
    assert "test_evidence_provenance_not_found" in result.warnings
    assert result.blockers == []
    assert result.completion_claim_allowed is True


def test_run_guard_reports_active_non_canonical_writer_as_blocker_candidate(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write(
        tmp_path / "memory" / "2026-06-09.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct manual write\n"
        "  commit: abc1234\n",
    )

    result = assess_memory_workflow(
        tmp_path,
        changed_files=["memory/2026-06-09.md"],
        run_guard_check=True,
    )

    assert result.guard_ran is True
    assert result.guard_summary["non_canonical_writer"] == 1
    assert result.guard_summary["active_non_canonical_writer"] == 1
    assert result.blockers == ["active_non_canonical_writer"]
    assert result.completion_claim_allowed is False


def test_strict_completion_check_blocks_memory_diff_without_guard(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)

    result = assess_memory_workflow(
        tmp_path,
        changed_files=["memory/2026-06-09.md"],
        strict_completion_check=True,
    )

    assert "memory_authority_guard_not_run" in result.blockers
    assert result.completion_claim_allowed is False


def test_cli_json_outputs_required_schema(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write_canonical_memory(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_workflow.py",
            "--repo",
            str(tmp_path),
            "--check",
            "--changed-file",
            "memory/2026-06-09.md",
            "--run-guard",
            "--format",
            "json",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "memory_workflow_required"
    assert payload["task_classification"] == "governed_memory_task"
    assert payload["canonical_writer_required"] is True
    assert payload["guard_ran"] is True
    assert payload["guard_summary"]["active_non_canonical_writer"] == 0
    assert payload["completion_claim_allowed"] is True


def test_cli_fail_on_blocker_exits_2_for_active_non_canonical_writer(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write(
        tmp_path / "memory" / "2026-06-09.md",
        "- memory_type: session-derived\n"
        "  what_changed: direct manual write\n"
        "  commit: abc1234\n",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_workflow.py",
            "--repo",
            str(tmp_path),
            "--check",
            "--changed-file",
            "memory/2026-06-09.md",
            "--run-guard",
            "--fail-on-blocker",
            "--format",
            "json",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["blockers"] == ["active_non_canonical_writer"]


def test_cli_fail_on_blocker_allows_clean_canonical_memory(tmp_path: Path) -> None:
    _make_framework_surface(tmp_path)
    _write_canonical_memory(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_workflow.py",
            "--repo",
            str(tmp_path),
            "--check",
            "--changed-file",
            "memory/2026-06-09.md",
            "--run-guard",
            "--fail-on-blocker",
            "--format",
            "json",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["blockers"] == []
    assert payload["completion_claim_allowed"] is True
