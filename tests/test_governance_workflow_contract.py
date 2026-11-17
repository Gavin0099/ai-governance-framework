from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


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


@pytest.mark.parametrize(
    ("event_name", "before", "expected"),
    [
        ("workflow_dispatch", "", "HEAD~1|HEAD"),
        ("push", "previous-sha", "previous-sha|current-sha"),
        ("push", "0" * 40, "HEAD~1|HEAD"),
        ("pull_request", "", "base-sha|head-sha"),
    ],
)
def test_selective_memory_blocker_uses_valid_base_for_each_event(
    event_name: str, before: str, expected: str
) -> None:
    steps = yaml.safe_load(_workflow_text())["jobs"]["memory-workflow-selective"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Block current-diff non-canonical memory writer")
    selection = script.split("python -m governance_tools.ci_memory_workflow_check", 1)[0]
    for expression, value in {
        "github.event_name": event_name,
        "github.event.before": before,
        "github.event.pull_request.base.sha": "base-sha",
        "github.event.pull_request.head.sha": "head-sha",
        "github.sha": "current-sha",
    }.items():
        selection = selection.replace("${{ " + expression + " }}", value)
    assert "${{" not in selection
    git_executable = shutil.which("git")
    assert git_executable is not None
    bash_executable = (
        Path(git_executable).resolve().parent.parent / "bin" / "bash.exe"
        if os.name == "nt"
        else "bash"
    )
    completed = subprocess.run(
        [str(bash_executable), "-c", selection + '\nprintf "%s|%s\\n" "$BASE_REF" "$HEAD_REF"'],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == expected


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
    assert "github.event_name != 'push'" in phase_gate_job
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


def test_advisory_job_preserves_failure_visibility_and_setup_policy() -> None:
    import yaml

    jobs = yaml.safe_load(_workflow_text())["jobs"]
    job = jobs["governance-advisory"]
    assert "memory-pressure" not in jobs and "doc-drift" not in jobs
    assert job["continue-on-error"] is True
    setup = next(s for s in job["steps"] if s.get("id") == "setup-python")
    # Pinned to a SHA (#219); the pin itself is checked in
    # test_workflow_supply_chain_hardening so Dependabot bumps don't break this.
    assert setup["uses"].startswith("actions/setup-python@")
    checks = [s for s in job["steps"] if "run" in s]
    assert [s["name"] for s in checks] == ["Check memory pressure", "Check documentation drift"]
    for step in checks:
        assert step["if"] == "${{ !cancelled() && steps.setup-python.outcome == 'success' }}"
        assert not step.get("continue-on-error", False)  # Keep failures visible in the step log.
        assert step["timeout-minutes"] == 5
    assert job["timeout-minutes"] > sum(s["timeout-minutes"] for s in checks)


def _bash_command(script: str, *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    git_executable = shutil.which("git")
    assert git_executable is not None
    bash = (
        Path(git_executable).resolve().parent.parent / "bin" / "bash.exe"
        if os.name == "nt"
        else "bash"
    )
    return subprocess.run(
        [str(bash), "-c", script], cwd=cwd, env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30,
    )


@pytest.fixture
def phase_gate_environment(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    """Execute the real shell orchestration with synthetic downstream checks."""
    def write(relative: str, text: str) -> Path:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    write("scripts/verify_phase_gates.sh", _phase_gate_script_text())
    write("scripts/lib/python.sh", Path("scripts/lib/python.sh").read_text(encoding="utf-8"))
    write("scripts/run-runtime-governance.sh", "#!/bin/bash\nexit 0\n")
    for name in (
        "SYSTEM_PROMPT", "AGENT", "ARCHITECTURE", "HUMAN-OVERSIGHT",
        "REVIEW_CRITERIA", "TESTING", "NATIVE-INTEROP", "PLAN",
    ):
        write(f"governance/{name}.md", "synthetic presence fixture\n")
    write("PLAN.md", "synthetic presence fixture\n")
    calls = tmp_path / "python-calls.jsonl"
    stub = write("python_stub.py", '''\
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["PYTHON_CALLS"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(args) + "\\n")
if args[:2] == ["-m", "pytest"]:
    print("SYNTHETIC PYTEST RESULT")
    sys.exit(int(os.environ.get("PYTEST_EXIT", "0")))
if args[:1] == ["-c"]:
    exec(args[1])
elif args and args[0] == "governance_tools/plan_freshness.py":
    print(json.dumps({"status": "FRESH", "days_since_update": 0}))
elif args and args[0] == "governance_tools/governance_drift_checker.py":
    if "json" in args:
        print(os.environ["DRIFT_JSON"])
    sys.exit(int(os.environ.get("DRIFT_EXIT", "0")))
elif args and args[0] == "governance_tools/drift_gate_policy.py":
    import subprocess
    sys.exit(subprocess.run([sys.executable, os.environ["DRIFT_POLICY"]]).returncode)
''')
    python = write("bin/python", '#!/bin/bash\nexec "$REAL_PYTHON" "$PYTHON_STUB" "$@"\n')
    python.chmod(0o755)
    env = dict(os.environ)
    env.update(
        REAL_PYTHON=Path(sys.executable).as_posix(),
        PYTHON_STUB=stub.as_posix(), PYTHON_CALLS=calls.as_posix(),
        AI_GOVERNANCE_PYTHON=python.as_posix(),
        PATH=str(python.parent) + os.pathsep + env.get("PATH", ""),
        PYTEST_EXIT="0", DRIFT_EXIT="0",
        DRIFT_POLICY=(Path.cwd() / "governance_tools/drift_gate_policy.py").as_posix(),
        DRIFT_JSON=_drift_json("source_commit_recorded", "source_commit is missing"),
    )
    return tmp_path, env, calls


def _drift_json(check: str, detail: str) -> str:
    return json.dumps({"findings": [{"check": check, "severity": "warning", "detail": detail}]})


def _pytest_calls(path: Path) -> list[list[str]]:
    calls = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [args for args in calls if args[:2] == ["-m", "pytest"]]


@pytest.mark.parametrize("pytest_exit", [0, 1])
def test_standalone_phase_gate_runs_pytest_and_propagates_failure(
    phase_gate_environment: tuple[Path, dict[str, str], Path], pytest_exit: int,
) -> None:
    root, env, calls = phase_gate_environment
    env["PYTEST_EXIT"] = str(pytest_exit)
    result = _bash_command("bash scripts/verify_phase_gates.sh", cwd=root, env=env)
    assert result.returncode == pytest_exit, result.stdout + result.stderr
    assert _pytest_calls(calls) == [["-m", "pytest", "tests/", "-q", "--tb=short"]]
    assert ("Phase 完成條件滿足" in result.stdout) is (pytest_exit == 0)


def test_non_pytest_mode_does_not_rerun_tests_or_claim_all_gates_passed(
    phase_gate_environment: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, calls = phase_gate_environment
    env["PYTEST_EXIT"] = "1"
    result = _bash_command("bash scripts/verify_phase_gates.sh --non-pytest-only", cwd=root, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _pytest_calls(calls) == []
    assert "非 pytest" in result.stdout
    assert "不代表全部 Gate 通過" in result.stdout
    assert "Phase 完成條件滿足" not in result.stdout


@pytest.mark.parametrize("failure", ["drift", "drift_critical", "missing_document"])
def test_other_phase_gate_failures_are_not_hidden_by_non_pytest_mode(
    phase_gate_environment: tuple[Path, dict[str, str], Path], failure: str,
) -> None:
    root, env, _ = phase_gate_environment
    if failure == "drift":
        env["DRIFT_EXIT"] = "1"
    elif failure == "drift_critical":
        env["DRIFT_EXIT"] = "2"
    else:
        (root / "governance/ARCHITECTURE.md").unlink()
    result = _bash_command("bash scripts/verify_phase_gates.sh --non-pytest-only", cwd=root, env=env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "未通過" in result.stdout


def test_time_based_drift_advisory_passes_visibly(
    phase_gate_environment: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, _ = phase_gate_environment
    env["DRIFT_EXIT"] = "1"
    env["DRIFT_JSON"] = _drift_json(
        "expansion_boundary", "transitional_key_stale: key='k' age=91d (max=90d)")
    result = _bash_command("bash scripts/verify_phase_gates.sh --non-pytest-only", cwd=root, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ADVISORY expansion_boundary" in result.stdout
    assert "Gate 通過（警告）" in result.stdout


def test_phase_gate_rejects_unknown_options_before_running_checks(
    phase_gate_environment: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, calls = phase_gate_environment
    result = _bash_command("bash scripts/verify_phase_gates.sh --skip-tests", cwd=root, env=env)
    assert result.returncode == 2
    assert not calls.exists()


def test_phase_gate_reuses_only_its_workflow_run_and_same_checkout_settings() -> None:
    jobs = yaml.safe_load(_workflow_text())["jobs"]
    full, phase = jobs["full-test-suite"], jobs["phase-gates"]
    assert phase["needs"] == "full-test-suite"
    assert phase["if"] == "${{ always() && github.event_name != 'push' }}"
    assert full["runs-on"] == phase["runs-on"] == "ubuntu-latest"
    assert not full.get("continue-on-error", False)
    assert not phase.get("continue-on-error", False)
    pins = []
    for job in (full, phase):
        checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
        assert checkout["with"]["ref"] == "${{ github.sha }}"
        assert checkout["with"]["fetch-depth"] == 0
        setup = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/setup-python@"))
        assert setup["with"]["python-version"] == "3.11"
        pins.append((checkout["uses"], setup["uses"]))
        assert next(s for s in job["steps"] if s.get("name") == "Install documented dependencies")["run"] == "pip install -r requirements.txt"
    assert pins[0] == pins[1]  # same action versions in both jobs
    guard = phase["steps"][0]
    assert guard["env"]["FULL_TEST_SUITE_RESULT"] == "${{ needs.full-test-suite.result }}"
    assert not guard.get("continue-on-error", False)
    assert "if" not in guard
    verify = next(s for s in phase["steps"] if s.get("name") == "Verify phase gates")
    assert verify["run"] == "bash scripts/verify_phase_gates.sh --non-pytest-only"
    assert not verify.get("continue-on-error", False)
    test_step = next(s for s in full["steps"] if s.get("name") == "Run full test suite")
    assert "if" not in test_step
    assert not test_step.get("continue-on-error", False)


@pytest.mark.parametrize("upstream", ["success", "failure", "skipped", "cancelled", "", "neutral"])
def test_required_phase_gate_rejects_every_non_success_upstream(
    tmp_path: Path, upstream: str,
) -> None:
    phase = yaml.safe_load(_workflow_text())["jobs"]["phase-gates"]
    guard = phase["steps"][0]
    env = dict(os.environ, FULL_TEST_SUITE_RESULT=upstream)
    result = _bash_command(guard["run"], cwd=tmp_path, env=env)
    assert (result.returncode == 0) is (upstream == "success")


def test_ci_runs_the_complete_suite_once_and_preserves_other_gate_failures(
    phase_gate_environment: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, calls = phase_gate_environment
    jobs = yaml.safe_load(_workflow_text())["jobs"]
    full_test = next(s for s in jobs["full-test-suite"]["steps"] if s.get("name") == "Run full test suite")
    phase = jobs["phase-gates"]
    verify = next(s for s in phase["steps"] if s.get("name") == "Verify phase gates")
    assert _bash_command(full_test["run"], cwd=root, env=env).returncode == 0
    env["FULL_TEST_SUITE_RESULT"] = "success"
    assert _bash_command(phase["steps"][0]["run"], cwd=root, env=env).returncode == 0
    env["DRIFT_EXIT"] = "1"
    result = _bash_command(verify["run"], cwd=root, env=env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert len(_pytest_calls(calls)) == 1
