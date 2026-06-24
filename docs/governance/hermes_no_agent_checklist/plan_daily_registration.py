#!/usr/bin/env python3
"""Dry-run planner for a persistent Hermes no_agent daily checklist job.

This tool is intentionally read-only. It runs the existing package preflight,
reads HERMES_HOME/cron/jobs.json, detects whether a matching active checklist
job already exists, and emits reviewer-readable registration commands/checks.

It does not create or edit a Hermes cron job, does not run cron tick, does not
install or uninstall a scheduled task, does not delete retained artifacts, and
does not call provider or LLM paths.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from check_preflight import DEFAULT_CONFIG, run_preflight


DEFAULT_JOB_NAME = "AI Governance Hermes NoAgent Checklist Daily"
DEFAULT_SCHEDULE = "0 9 * * *"
DEFAULT_DELIVER = "local"


def _as_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON at {path}")
    return data


def _safe_jobs_payload(jobs_file: Path) -> tuple[dict[str, Any], list[str]]:
    if not jobs_file.exists():
        return {"jobs": [], "updated_at": None}, []
    try:
        data = _load_json(jobs_file)
    except Exception as exc:
        return {"jobs": [], "updated_at": None}, [f"failed to read jobs.json: {type(exc).__name__}: {exc}"]
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return {"jobs": [], "updated_at": data.get("updated_at")}, ["jobs.json field 'jobs' must be a list"]
    return data, []


def _job_schedule_expr(job: dict[str, Any]) -> str | None:
    schedule = job.get("schedule")
    if isinstance(schedule, dict):
        return schedule.get("expr")
    if isinstance(schedule, str):
        return schedule
    return None


def _is_active_job(job: dict[str, Any]) -> bool:
    if not job.get("enabled", True):
        return False
    state = str(job.get("state") or "scheduled").strip().lower()
    return state not in {"paused", "completed", "disabled"}


def _matching_job(
    job: dict[str, Any],
    *,
    job_name: str,
    schedule: str,
    script_filename: str,
    deliver: str,
) -> bool:
    if not _is_active_job(job):
        return False
    if job.get("name") != job_name:
        return False
    if job.get("no_agent") is not True:
        return False
    if job.get("script") != script_filename:
        return False
    if _job_schedule_expr(job) != schedule:
        return False
    job_deliver = job.get("deliver")
    if isinstance(job_deliver, list):
        return deliver in job_deliver
    return job_deliver == deliver


def _summarize_job(job: dict[str, Any]) -> dict[str, Any]:
    schedule = job.get("schedule") if isinstance(job.get("schedule"), dict) else {}
    repeat = job.get("repeat") if isinstance(job.get("repeat"), dict) else {}
    return {
        "id": job.get("id"),
        "name": job.get("name"),
        "enabled": job.get("enabled", True),
        "state": job.get("state"),
        "schedule_kind": schedule.get("kind"),
        "schedule_expr": schedule.get("expr"),
        "schedule_display": job.get("schedule_display"),
        "next_run_at": job.get("next_run_at"),
        "script": job.get("script"),
        "no_agent": job.get("no_agent"),
        "deliver": job.get("deliver"),
        "repeat_times": repeat.get("times"),
        "repeat_completed": repeat.get("completed"),
        "last_run_at": job.get("last_run_at"),
        "last_status": job.get("last_status"),
    }


def _create_command(
    python_exe: Path,
    schedule: str,
    job_name: str,
    script_filename: str,
    deliver: str,
) -> str:
    return subprocess.list2cmdline(
        [
            str(python_exe),
            "-m",
            "hermes_cli.main",
            "cron",
            "create",
            schedule,
            "--name",
            job_name,
            "--deliver",
            deliver,
            "--script",
            script_filename,
            "--no-agent",
        ]
    )


def plan_registration(
    *,
    config_path: Path,
    hermes_home: Path,
    venv_path: Path,
    job_name: str,
    schedule: str,
    deliver: str,
) -> tuple[dict[str, Any], int]:
    preflight_report, preflight_errors = run_preflight(
        config_path=config_path,
        hermes_home=hermes_home,
        venv_path=venv_path,
    )
    if preflight_errors:
        return {
            "ok": False,
            "phase": "preflight",
            "errors": preflight_errors,
            "preflight": preflight_report,
            "claim_ceiling_not_supported": _non_claims(),
        }, 1

    script_filename = str(preflight_report["script_filename"])
    jobs_file = hermes_home / "cron" / "jobs.json"
    jobs_payload, jobs_errors = _safe_jobs_payload(jobs_file)
    jobs = jobs_payload.get("jobs", [])
    matching_jobs = [
        _summarize_job(job)
        for job in jobs
        if isinstance(job, dict)
        and _matching_job(
            job,
            job_name=job_name,
            schedule=schedule,
            script_filename=script_filename,
            deliver=deliver,
        )
    ]
    active_jobs = [_summarize_job(job) for job in jobs if isinstance(job, dict) and _is_active_job(job)]
    python_exe = (venv_path / "Scripts" / "python.exe").resolve()

    errors = list(jobs_errors)
    if len(matching_jobs) > 1:
        errors.append("multiple matching active checklist jobs exist; review before registering another")

    command = _create_command(
        python_exe=python_exe,
        schedule=schedule,
        job_name=job_name,
        script_filename=script_filename,
        deliver=deliver,
    )

    return {
        "ok": not errors,
        "phase": "dry_run_daily_registration",
        "mode": "read_only_planner",
        "errors": errors,
        "hermes_home": str(hermes_home),
        "venv_python": str(python_exe),
        "jobs_file": str(jobs_file),
        "jobs_file_exists": jobs_file.exists(),
        "jobs_updated_at": jobs_payload.get("updated_at"),
        "active_job_count": len(active_jobs),
        "matching_active_job_count": len(matching_jobs),
        "matching_active_jobs": matching_jobs,
        "already_registered": bool(matching_jobs),
        "recommended_action": (
            "do_not_register_duplicate"
            if matching_jobs
            else "human_may_register_after_review"
        ),
        "human_run_create_command": None if matching_jobs else command,
        "expected_post_registration_checks": [
            "jobs.json contains exactly one active matching checklist job",
            f"name == {job_name!r}",
            "no_agent == true",
            f"script == {script_filename!r}",
            "schedule.kind == 'cron'",
            f"schedule.expr == {schedule!r}",
            f"deliver includes or equals {deliver!r}",
            "repeat.times == null",
            "enabled == true",
            "state == 'scheduled'",
            "next_run_at is present",
        ],
        "preflight": preflight_report,
        "claim_ceiling_not_supported": _non_claims(),
    }, 0 if not errors else 1


def _non_claims() -> list[str]:
    return [
        "does not register or edit a Hermes cron job",
        "does not write HERMES_HOME/cron/jobs.json",
        "does not run Hermes cron tick",
        "does not install or uninstall an OS scheduled task",
        "does not perform retention deletion",
        "does not call provider or LLM paths",
        "does not enforce runtime sandboxing or AI Governance policy",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to reviewed checklist config JSON.")
    parser.add_argument("--hermes-home", required=True, help="Expected isolated HERMES_HOME path.")
    parser.add_argument("--venv", required=True, help="Expected isolated Python virtual environment path.")
    parser.add_argument("--job-name", default=DEFAULT_JOB_NAME, help="Expected persistent Hermes cron job name.")
    parser.add_argument("--schedule", default=DEFAULT_SCHEDULE, help="Expected Hermes cron schedule expression.")
    parser.add_argument("--deliver", default=DEFAULT_DELIVER, help="Expected Hermes cron delivery target.")
    args = parser.parse_args()

    report, code = plan_registration(
        config_path=_as_path(args.config),
        hermes_home=_as_path(args.hermes_home),
        venv_path=_as_path(args.venv),
        job_name=args.job_name,
        schedule=args.schedule,
        deliver=args.deliver,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
