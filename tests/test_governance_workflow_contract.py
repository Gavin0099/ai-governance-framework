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


def test_governance_workflow_keeps_memory_push_filter_and_runs_for_all_main_prs() -> None:
    text = _workflow_text()
    push_section = _section(text, "  push:", "  pull_request:")
    pull_request_section = _section(text, "  pull_request:", "  workflow_dispatch:")

    assert "- 'memory/**'" in push_section
    assert "branches: [main]" in pull_request_section
    assert "paths:" not in pull_request_section


def test_full_test_suite_is_an_independent_job_with_report_only_census() -> None:
    text = _workflow_text()
    job_section = _section(text, "  full-test-suite:", "  memory-workflow-selective:")
    census_build_step = _section(
        text,
        "      - name: Build guard enforcement census (report-only)",
        "      - name: Upload guard enforcement census",
    )
    census_upload_step = _section(
        text,
        "      - name: Upload guard enforcement census",
        "  memory-workflow-selective:",
    )

    assert "name: Full Test Suite" in job_section
    assert "run: python -m pytest tests/ -q --tb=short" in job_section
    assert "if: github.event_name != 'push'" not in job_section
    assert "name: Build guard enforcement census (report-only)" in job_section
    assert "continue-on-error: true" in census_build_step
    assert "continue-on-error: true" in census_upload_step
    assert "python -m governance_tools.guard_enforcement_census" in job_section
    assert "--require-level" not in job_section
    assert "name: guard-enforcement-census" in job_section


def test_governance_workflow_runs_selective_memory_blocker() -> None:
    text = _workflow_text()
    job_section = _section(text, "  memory-workflow-selective:", "  plan-freshness:")

    assert "name: Memory Workflow Selective Blocker" in job_section
    assert "python -m governance_tools.ci_memory_workflow_check" in job_section
    assert '--base-ref "$BASE_REF"' in job_section
    assert '--head-ref "$HEAD_REF"' in job_section


def test_runtime_enforcement_fails_closed_on_inventory_enumeration_and_guard_failures() -> None:
    text = _workflow_text()
    job_section = _section(
        text,
        "  runtime-enforcement:",
        "  bash32-runtime-compatibility:",
    )
    guard_step = _section(
        job_section,
        "      - name: Enforce external tree inventory disclosure guard",
        "      - name: Run runtime governance enforcement",
    )

    assert 'json_list_path="$RUNNER_TEMP/external-tree-inventory-files.zlist"' in guard_step
    assert "if ! git ls-files -z -- '*.json' > \"$json_list_path\"; then" in guard_step
    assert "could not enumerate tracked JSON files" in guard_step
    assert "mapfile" not in guard_step
    assert "while IFS= read -r -d '' json_file; do" in guard_step
    assert 'done < "$json_list_path"' in guard_step
    assert 'json_file_count=$((json_file_count + 1))' in guard_step
    assert '[ "$json_file_count" -eq 0 ]' in guard_step
    assert "found no tracked JSON files; enumeration is invalid" in guard_step
    assert "passed: no tracked JSON files" not in guard_step
    assert "python -m governance_tools.external_tree_inventory_guard" in guard_step
    assert "--repo-root ." in guard_step
    assert "--identity-config governance/external-tree-inventory-guard.json" in guard_step
    assert "--repository-id Gavin0099/ai-governance-framework" not in guard_step
    assert '"${json_files[@]}"' in guard_step
    assert 'guard_status=$?' in guard_step
    assert '[ "$guard_status" -ne 0 ]' in guard_step
    assert 'cat "$report_path"' in guard_step
    assert 'exit "$guard_status"' in guard_step
    assert "continue-on-error" not in guard_step
    assert "External tree inventory guard passed for $json_file_count" in guard_step
    assert job_section.index("external_tree_inventory_guard") < job_section.index(
        "bash scripts/run-runtime-governance.sh --mode ci"
    )


def test_bash32_job_selects_pre_push_object_guard_behaviour() -> None:
    text = _workflow_text()
    job_section = _section(
        text,
        "  bash32-runtime-compatibility:",
        "  interception-ledger-check:",
    )

    assert "Run pre-push prerequisite regressions under Bash 3.2" in job_section
    assert "pre_push_object_guard" in job_section


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

    assert "branches: [main]" in pull_request_section
    assert "paths:" not in pull_request_section


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
