"""
Regression tests for issue #218.

The CI memory-pressure step reported EMERGENCY as "148/200 lines" although the
trigger was the character count (12057 >= 12000), and told maintainers to run
`memory_janitor.py --execute`, which always fails closed with exit 2.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from governance_tools.memory_janitor import MemoryJanitor, main

REPO = Path(__file__).resolve().parent.parent
J = MemoryJanitor


def _janitor(tmp_path: Path) -> MemoryJanitor:
    return MemoryJanitor(tmp_path / "memory")


@pytest.mark.parametrize(
    "lines, chars, status, triggered, expected",
    [
        # the case from the issue: line count looks fine, characters trigger it
        (148, 12057, "EMERGENCY", ["chars"], "148/250 lines, 12057/12000 chars; triggered by chars"),
        (251, 3000, "EMERGENCY", ["lines"], "251/250 lines, 3000/12000 chars; triggered by lines"),
        (260, 13000, "EMERGENCY", ["lines", "chars"], "triggered by lines + chars"),
        (210, 5000, "CRITICAL", ["lines"], "210/200 lines, 5000/10000 chars; triggered by lines"),
        (50, 10500, "CRITICAL", ["chars"], "50/200 lines, 10500/10000 chars; triggered by chars"),
        (185, 100, "WARNING", ["lines"], "185/180 lines, 100/8000 chars; triggered by lines"),
        (10, 100, "SAFE", [], "Memory status: SAFE (10/180 lines, 100/8000 chars)"),
    ],
)
def test_describe_pressure_names_the_triggering_dimension(tmp_path, lines, chars, status, triggered, expected):
    info = _janitor(tmp_path).describe_pressure(lines, chars, status)
    assert info["triggered_by"] == triggered
    assert expected in info["summary"]


def test_status_and_description_agree_for_real_files(tmp_path):
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "01_active_task.md").write_text("\n".join(["x" * 82] * 148), encoding="utf-8")
    janitor = MemoryJanitor(memory)
    lines, chars, status = janitor.check_hot_memory_status()
    assert (lines, status) == (148, "EMERGENCY")
    assert janitor.describe_pressure(lines, chars, status)["triggered_by"] == ["chars"]


def test_check_json_exposes_summary_and_trigger(tmp_path, capsys):
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "01_active_task.md").write_text("\n".join(["x" * 82] * 148), encoding="utf-8")
    argv = sys.argv
    sys.argv = ["memory_janitor.py", "--memory-root", str(memory), "--check", "--format", "json"]
    try:
        main()
    finally:
        sys.argv = argv
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "EMERGENCY"
    assert payload["triggered_by"] == ["chars"]
    assert "chars; triggered by chars" in payload["summary"]
    assert payload["line_count"] == 148  # existing fields unchanged
    assert payload["hard_limit"] == J.HOT_MEMORY_HARD_LIMIT


# ── the CI step scripts themselves ───────────────────────────────────────────

def _github_step_script() -> str:
    workflow = yaml.safe_load((REPO / ".github/workflows/governance.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["governance-advisory"]["steps"]
    return next(step["run"] for step in steps if step.get("name") == "Check memory pressure")


def _gitlab_step_script() -> str:
    ci = yaml.safe_load((REPO / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    return next(item for item in ci["memory-pressure"]["script"] if "memory_janitor.py" in item)


def _bash_with_python() -> str | None:
    bash = shutil.which("bash")
    if not bash:
        return None
    env = _env()
    probe = subprocess.run(
        [bash, "-c", "python --version && python3 --version"],
        capture_output=True, env=env, timeout=30,
    )
    return bash if probe.returncode == 0 else None


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    return env


def _run_step(script: str, tmp_path: Path, active_task: str) -> subprocess.CompletedProcess:
    bash = _bash_with_python()
    if bash is None:
        pytest.skip("bash with python/python3 not available")
    (tmp_path / "governance_tools").mkdir()
    shutil.copy(REPO / "governance_tools" / "memory_janitor.py", tmp_path / "governance_tools" / "memory_janitor.py")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "01_active_task.md").write_text(active_task, encoding="utf-8")
    return subprocess.run(
        [bash, "-c", script],
        cwd=tmp_path, env=_env(), capture_output=True, text=True, encoding="utf-8",
        timeout=120,
    )


@pytest.mark.parametrize("script_loader", [_github_step_script, _gitlab_step_script], ids=["github", "gitlab"])
def test_ci_step_reports_chars_and_points_to_plan_not_execute(tmp_path, script_loader):
    # 148 lines (< 200) but > 12000 chars: the exact shape from the issue
    done = _run_step(script_loader(), tmp_path, "\n".join(["x" * 82] * 148))
    out = done.stdout + done.stderr

    assert done.returncode == 1, out  # EMERGENCY still fails the advisory step
    assert "148/250 lines" in out and "chars; triggered by chars" in out
    assert "--plan" in out
    assert "separate authorization" in out
    assert "janitor.py --execute'" not in out and "run: python governance_tools/memory_janitor.py --execute" not in out


@pytest.mark.parametrize("script_loader", [_github_step_script, _gitlab_step_script], ids=["github", "gitlab"])
def test_ci_step_critical_stays_non_blocking_and_points_to_plan(tmp_path, script_loader):
    done = _run_step(script_loader(), tmp_path, "\n".join(["x"] * 210))
    out = done.stdout + done.stderr

    assert done.returncode == 0, out
    assert "CRITICAL" in out and "triggered by lines" in out
    assert "--plan" in out
    assert "Run memory_janitor --execute soon" not in out


@pytest.mark.parametrize("script_loader", [_github_step_script, _gitlab_step_script], ids=["github", "gitlab"])
def test_ci_step_safe_memory_is_quiet_and_passes(tmp_path, script_loader):
    done = _run_step(script_loader(), tmp_path, "short\n")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Memory status: SAFE" in done.stdout


def test_execute_still_fails_closed_so_the_old_hint_was_wrong(tmp_path):
    """Pins the premise of #218: --execute is not a usable remediation."""
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "01_active_task.md").write_text("\n".join(["x" * 82] * 148), encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "governance_tools" / "memory_janitor.py"),
         "--memory-root", str(memory), "--execute"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert done.returncode == 2
    assert (memory / "01_active_task.md").read_text(encoding="utf-8").count("\n") == 147
