"""Janitor high-pressure output points to the verified archive/cutover tool.

The pointer is appended after the unchanged §7.4 guidance; it does not
authorize cutover and must be runnable from a consumer's framework submodule.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.memory_janitor import MemoryJanitor

REPO_ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = (
    "governance_tools/active_task_cutover.py",
    "prepare --project-root .",
    "prepare／verify 不修改 active memory",
    "--authorization",
    "--authorized-candidate-sha256",
    "此指引本身不授權 cutover",
)


@pytest.fixture
def janitor(tmp_path: Path) -> MemoryJanitor:
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "01_active_task.md").write_text("x" * 12000, encoding="utf-8")
    return MemoryJanitor(memory)


@pytest.mark.parametrize("status", ["EMERGENCY", "CRITICAL"])
def test_high_pressure_warning_points_to_cutover_tool(janitor, status):
    message = janitor.generate_warning_message(1, 12000, status)
    for fragment in FRAGMENTS:
        assert fragment in message, fragment
    if status == "EMERGENCY":
        # The §7.4 guidance constant is carried unchanged, before the pointer.
        assert message.index(janitor.EMERGENCY_SCOPE_GUIDANCE) < message.index(
            "active_task_cutover.py"
        )


@pytest.mark.parametrize("status", ["SAFE", "WARNING"])
def test_lower_levels_do_not_point_to_cutover_tool(janitor, status):
    assert "active_task_cutover.py" not in janitor.generate_warning_message(1, 1, status)


@pytest.mark.parametrize("chars, status", [(12000, "EMERGENCY"), (10000, "CRITICAL")])
def test_archive_plan_points_to_cutover_tool(janitor, chars, status):
    janitor.active_task_file.write_text("x" * chars, encoding="utf-8")
    report = janitor.create_archive_plan()
    assert f"**當前狀態**: {status}" in report
    for fragment in FRAGMENTS:
        assert fragment in report, fragment
    if status == "EMERGENCY":
        assert janitor.EMERGENCY_SCOPE_GUIDANCE in report


def test_cutover_tool_path_is_relative_to_the_consumer_root(tmp_path: Path) -> None:
    # A consumer with the framework as a submodule at fw/: the pointer must be
    # runnable from the consumer root as printed.
    consumer = tmp_path / "consumer"
    shutil.copytree(
        REPO_ROOT / "governance_tools",
        consumer / "fw" / "governance_tools",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    memory = consumer / "memory"
    memory.mkdir()
    (memory / "01_active_task.md").write_text("x" * 12000, encoding="utf-8")

    plan = subprocess.run(
        [
            sys.executable, "-X", "utf8",
            str(consumer / "fw" / "governance_tools" / "memory_janitor.py"),
            "--memory-root", str(memory), "--plan", "--format", "json",
        ],
        capture_output=True, text=True, encoding="utf-8", cwd=consumer,
    )
    assert plan.returncode == 0, plan.stdout + plan.stderr
    info = json.loads(plan.stdout)["cutover_tool"]
    assert info["path"] == "fw/governance_tools/active_task_cutover.py"
    assert info["framework_relative_path"] == "governance_tools/active_task_cutover.py"
    assert info["modifies_active_memory"]["prepare"] is False
    assert info["modifies_active_memory"]["verify"] is False
    assert info["authorizes_cutover"] is False
    assert "--authorization" in info["cutover_requires"]

    before = (memory / "01_active_task.md").read_bytes()
    prepare = subprocess.run(
        [sys.executable, "-X", "utf8", info["path"], "prepare", "--project-root", ".",
         "--stamp", "20261030_120000"],
        capture_output=True, text=True, encoding="utf-8", cwd=consumer,
    )
    assert prepare.returncode == 0, prepare.stdout + prepare.stderr
    assert (memory / "archive" / "active_task_20261030_120000.md").read_bytes() == before
    assert (memory / "01_active_task.md").read_bytes() == before


def test_plan_json_recommendation_is_unchanged(janitor):
    plan = subprocess.run(
        [
            sys.executable, "-X", "utf8", str(REPO_ROOT / "governance_tools" / "memory_janitor.py"),
            "--memory-root", str(janitor.memory_root), "--plan", "--format", "json",
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    payload = json.loads(plan.stdout)
    assert payload["status"] == "EMERGENCY"
    assert payload["recommendation"] == "verified_archive_and_replacement_state_cutover_required"
    assert payload["cutover_tool"]["framework_relative_path"] == (
        "governance_tools/active_task_cutover.py"
    )
