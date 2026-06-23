#!/usr/bin/env python3
"""Dry-run Windows Task Scheduler definition generator.

This script emits reviewer-readable scheduler definitions for the Hermes
no_agent checklist. It first runs the package preflight and refuses to generate
a task definition if the deployed checklist script does not match the reviewed
config pin.

It does not register or install a scheduled task, does not run cron tick, does
not delete retained artifacts, and does not call provider or LLM paths.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import time
from pathlib import Path
from typing import Any

from check_preflight import DEFAULT_CONFIG, run_preflight


TASK_XML_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
PACKAGE_DIR = Path(__file__).resolve().parent


def _as_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _xml_escape_path(path: Path) -> str:
    return str(path)


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _cron_tick_command(python_exe: Path, hermes_home: Path) -> str:
    return (
        f"$env:HERMES_HOME={_ps_single_quote(str(hermes_home))}; "
        f"& {_ps_single_quote(str(python_exe))} -m hermes_cli.main cron tick"
    )


def _preflight_command(config_path: Path, hermes_home: Path, venv_path: Path) -> str:
    checker = PACKAGE_DIR / "check_preflight.py"
    python_exe = venv_path / "Scripts" / "python.exe"
    return subprocess.list2cmdline(
        [
            str(python_exe),
            str(checker),
            "--config",
            str(config_path),
            "--hermes-home",
            str(hermes_home),
            "--venv",
            str(venv_path),
        ]
    )


def _task_query_command(task_name: str) -> str:
    return subprocess.list2cmdline(["schtasks", "/Query", "/TN", task_name])


def _task_delete_command(task_name: str) -> str:
    return subprocess.list2cmdline(["schtasks", "/Delete", "/TN", task_name, "/F"])


def _windows_time(value: str) -> str:
    parsed = time.fromisoformat(value)
    return parsed.strftime("%H:%M:%S")


def _build_task_xml(task_name: str, powershell_command: str, start_time: str) -> str:
    ET.register_namespace("", TASK_XML_NS)
    task = ET.Element(f"{{{TASK_XML_NS}}}Task", {"version": "1.4"})
    registration_info = ET.SubElement(task, f"{{{TASK_XML_NS}}}RegistrationInfo")
    ET.SubElement(registration_info, f"{{{TASK_XML_NS}}}Description").text = (
        "Hermes no_agent checklist cron tick. Observation-only; not governance enforcement."
    )

    triggers = ET.SubElement(task, f"{{{TASK_XML_NS}}}Triggers")
    calendar_trigger = ET.SubElement(triggers, f"{{{TASK_XML_NS}}}CalendarTrigger")
    ET.SubElement(calendar_trigger, f"{{{TASK_XML_NS}}}StartBoundary").text = f"2026-06-23T{start_time}"
    schedule = ET.SubElement(calendar_trigger, f"{{{TASK_XML_NS}}}ScheduleByDay")
    ET.SubElement(schedule, f"{{{TASK_XML_NS}}}DaysInterval").text = "1"
    ET.SubElement(calendar_trigger, f"{{{TASK_XML_NS}}}Enabled").text = "true"

    principals = ET.SubElement(task, f"{{{TASK_XML_NS}}}Principals")
    principal = ET.SubElement(principals, f"{{{TASK_XML_NS}}}Principal", {"id": "Author"})
    ET.SubElement(principal, f"{{{TASK_XML_NS}}}LogonType").text = "InteractiveToken"
    ET.SubElement(principal, f"{{{TASK_XML_NS}}}RunLevel").text = "LeastPrivilege"

    settings = ET.SubElement(task, f"{{{TASK_XML_NS}}}Settings")
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}MultipleInstancesPolicy").text = "IgnoreNew"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}DisallowStartIfOnBatteries").text = "false"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}StopIfGoingOnBatteries").text = "false"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}AllowHardTerminate").text = "true"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}StartWhenAvailable").text = "true"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}RunOnlyIfNetworkAvailable").text = "false"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}Enabled").text = "true"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}Hidden").text = "false"
    ET.SubElement(settings, f"{{{TASK_XML_NS}}}ExecutionTimeLimit").text = "PT10M"

    actions = ET.SubElement(task, f"{{{TASK_XML_NS}}}Actions", {"Context": "Author"})
    exec_action = ET.SubElement(actions, f"{{{TASK_XML_NS}}}Exec")
    ET.SubElement(exec_action, f"{{{TASK_XML_NS}}}Command").text = "powershell.exe"
    ET.SubElement(exec_action, f"{{{TASK_XML_NS}}}Arguments").text = subprocess.list2cmdline(
        ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell_command]
    )

    xml_text = ET.tostring(task, encoding="unicode")
    return xml_text.replace("><", ">\n<")


def generate_definition(
    config_path: Path,
    hermes_home: Path,
    venv_path: Path,
    task_name: str,
    start_time: str,
) -> tuple[dict[str, Any], int]:
    preflight_report, errors = run_preflight(config_path=config_path, hermes_home=hermes_home, venv_path=venv_path)
    if errors:
        return {
            "ok": False,
            "phase": "preflight",
            "errors": errors,
            "preflight": preflight_report,
            "claim_ceiling_not_supported": [
                "does not register or install a scheduled task",
                "does not run Hermes cron tick",
                "does not perform retention deletion",
                "does not call provider or LLM paths",
                "does not enforce runtime sandboxing",
            ],
        }, 1

    python_exe = (venv_path / "Scripts" / "python.exe").resolve()
    start_at = _windows_time(start_time)
    powershell_command = _cron_tick_command(python_exe=python_exe, hermes_home=hermes_home)
    xml_definition = _build_task_xml(task_name=task_name, powershell_command=powershell_command, start_time=start_at)

    task_run_command = subprocess.list2cmdline(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell_command]
    )
    schtasks_command = subprocess.list2cmdline(
        ["schtasks", "/Create", "/TN", task_name, "/SC", "DAILY", "/ST", start_at[:5], "/TR", task_run_command]
    )
    preflight_command = _preflight_command(config_path=config_path, hermes_home=hermes_home, venv_path=venv_path)
    query_command = _task_query_command(task_name=task_name)
    rollback_command = _task_delete_command(task_name=task_name)

    return {
        "ok": True,
        "phase": "dry_run_task_definition",
        "task_name": task_name,
        "schedule_model": "windows_task_scheduler_daily_tick",
        "start_time": start_at,
        "hermes_home": str(hermes_home),
        "venv_python": str(python_exe),
        "powershell_command": powershell_command,
        "schtasks_create_preview": schtasks_command,
        "install_plan_preview": {
            "1_preflight_required": preflight_command,
            "2_create_task": schtasks_command,
            "3_verify_task_registered": query_command,
            "rollback_delete_task": rollback_command,
            "safety_notes": [
                "Run preflight immediately before create.",
                "Do not create the task if preflight fails.",
                "Rollback removes only the named scheduled task.",
                "This generator does not execute any install, verify, rollback, or cron tick command.",
            ],
        },
        "task_xml_preview": xml_definition,
        "preflight": preflight_report,
        "claim_ceiling_not_supported": [
            "does not register or install a scheduled task",
            "does not run Hermes cron tick",
            "does not perform retention deletion",
            "does not call provider or LLM paths",
            "does not enforce runtime sandboxing",
        ],
    }, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to reviewed checklist config JSON.")
    parser.add_argument("--hermes-home", required=True, help="Expected isolated HERMES_HOME path.")
    parser.add_argument("--venv", required=True, help="Expected isolated Python virtual environment path.")
    parser.add_argument("--task-name", default="AI Governance Hermes NoAgent Checklist", help="Reviewer-facing scheduled task name.")
    parser.add_argument("--start-time", default="09:00:00", help="Daily local start time, HH:MM or HH:MM:SS.")
    args = parser.parse_args()

    report, code = generate_definition(
        config_path=_as_path(args.config),
        hermes_home=_as_path(args.hermes_home),
        venv_path=_as_path(args.venv),
        task_name=args.task_name,
        start_time=args.start_time,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
