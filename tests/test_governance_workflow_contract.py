from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(".github/workflows/governance.yml")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def test_governance_workflow_triggers_on_memory_changes() -> None:
    text = _workflow_text()
    push_section = _section(text, "  push:", "  pull_request:")
    pull_request_section = _section(text, "  pull_request:", "  workflow_dispatch:")

    assert "- 'memory/**'" in push_section
    assert "- 'memory/**'" in pull_request_section


def test_governance_workflow_runs_selective_memory_blocker() -> None:
    text = _workflow_text()
    job_section = _section(text, "  memory-workflow-selective:", "  plan-freshness:")

    assert "name: Memory Workflow Selective Blocker" in job_section
    assert "python -m governance_tools.ci_memory_workflow_check" in job_section
    assert '--base-ref "$BASE_REF"' in job_section
    assert '--head-ref "$HEAD_REF"' in job_section
