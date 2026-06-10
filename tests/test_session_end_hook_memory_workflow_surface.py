from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

from governance_tools.memory_workflow import MemoryWorkflowDispatchResult
from governance_tools.session_end_hook import run_session_end_hook


_FIXTURE_ROOT = Path(__file__).parent / "_tmp_memory_workflow_surface"


def _reset(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / "memory").mkdir()
    return path


def _run(repo: Path) -> dict:
    return run_session_end_hook(repo)


def test_memory_workflow_surface_present_and_report_only_shape() -> None:
    repo = _reset("shape")

    result = _run(repo)

    assert "memory_workflow" in result
    mw = result["memory_workflow"]
    assert mw["memory_workflow_dispatch_ran"] is True
    assert mw["memory_workflow_status"] in {
        "no_memory_workflow_required",
        "memory_workflow_required",
        "possible_memory_task",
    }
    assert isinstance(mw["memory_authority_guard_ran"], bool)
    assert isinstance(mw["memory_completion_claim_allowed"], bool)
    assert isinstance(mw["memory_workflow_warning_codes"], list)
    assert isinstance(mw["memory_workflow_blocker_codes"], list)
    assert isinstance(mw["memory_workflow_guard_summary"], dict)


def test_governed_memory_task_surface_maps_dispatch_fields() -> None:
    repo = _reset("governed")
    dispatch = MemoryWorkflowDispatchResult(
        status="memory_workflow_required",
        repo_root=str(repo),
        repo_root_resolved=True,
        memory_files_in_diff=["memory/2026-06-10.md"],
        canonical_writer_required=True,
        task_classification="governed_memory_task",
        guard_ran=True,
        guard_summary={
            "non_canonical_writer": 1,
            "active_non_canonical_writer": 1,
            "missing_canonical_memory": 0,
            "unbound_memory": 0,
        },
        completion_claim_allowed=False,
        warnings=[],
        blockers=["active_non_canonical_writer"],
    )

    with patch("governance_tools.session_end_hook.assess_memory_workflow", return_value=dispatch):
        result = _run(repo)

    mw = result["memory_workflow"]
    assert mw["memory_workflow_status"] == "memory_workflow_required"
    assert mw["memory_task_classification"] == "governed_memory_task"
    assert mw["memory_files_in_diff"] == ["memory/2026-06-10.md"]
    assert mw["canonical_writer_required"] is True
    assert mw["memory_authority_guard_ran"] is True
    assert mw["memory_completion_claim_allowed"] is False
    assert mw["memory_workflow_blocker_codes"] == ["active_non_canonical_writer"]
    assert mw["memory_workflow_guard_summary"]["active_non_canonical_writer"] == 1


def test_memory_workflow_dispatch_failure_is_advisory_only() -> None:
    repo = _reset("dispatch_error")

    with patch("governance_tools.session_end_hook.assess_memory_workflow", side_effect=RuntimeError("boom")):
        result = _run(repo)

    assert "ok" in result
    mw = result["memory_workflow"]
    assert mw["memory_workflow_dispatch_ran"] is False
    assert mw["memory_workflow_status"] == "MEMORY_WORKFLOW_DISPATCH_ERROR"
    assert "MEMORY_WORKFLOW_DISPATCH_ERROR" in mw["memory_workflow_warning_codes"]
    assert "boom" in mw["memory_workflow_error"]
