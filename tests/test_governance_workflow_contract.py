from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(".github/workflows/governance.yml")
PHASE_GATE_SCRIPT = Path("scripts/verify_phase_gates.sh")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _phase_gate_script_text() -> str:
    return PHASE_GATE_SCRIPT.read_text(encoding="utf-8")


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


def test_governance_workflow_triggers_on_canonical_governance_surfaces() -> None:
    text = _workflow_text()
    push_section = _section(text, "  push:", "  pull_request:")
    pull_request_section = _section(text, "  pull_request:", "  workflow_dispatch:")
    expected_paths = (
        ".governance/**",
        "AGENTS.md",
        "AGENTS.base.md",
        "baselines/**",
        "contract.yaml",
    )

    for path in expected_paths:
        expected = f"- '{path}'"
        assert expected in push_section
        assert expected in pull_request_section


def test_required_phase_gate_executes_canonical_drift_checker() -> None:
    workflow = _workflow_text()
    phase_gate_job = _section(workflow, "  phase-gates:", "  reviewer-policy-gate:")
    script = _phase_gate_script_text()

    assert "name: Phase Gate Verification" in phase_gate_job
    assert "if: github.event_name != 'push'" in phase_gate_job
    assert "run: bash scripts/verify_phase_gates.sh" in phase_gate_job
    assert "governance_tools/governance_drift_checker.py" in script
    assert "--repo ." in script
    assert "--framework-root ." in script
    assert "bookkeeping consistency, not owner authorization" in script


def test_main_push_runs_non_required_canonical_drift_audit() -> None:
    text = _workflow_text()
    job_section = _section(
        text,
        "  canonical-drift-post-merge:",
        "  phase-gates:",
    )

    assert "name: Canonical Drift Post-Merge Audit" in job_section
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in job_section
    assert (
        "python governance_tools/governance_drift_checker.py "
        "--repo . --framework-root . --format human"
    ) in job_section
