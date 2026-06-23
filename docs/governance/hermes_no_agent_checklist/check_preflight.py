#!/usr/bin/env python3
"""Read-only preflight for the Hermes no_agent multi-repo checklist package.

This checker verifies that the reviewed package and deployed Hermes script are
still aligned before a manual or scheduled no_agent run. It does not run Hermes,
does not run cron tick, does not install a scheduler, and does not delete
retained artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PACKAGE_DIR / "multi_repo_status.config.json"
EXPECTED_MODE = "hermes-cron-no-agent"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


def _as_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _check_explicit_repo_list(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    repos = config.get("repos")
    if not isinstance(repos, list) or not repos:
        return ["repos must be a non-empty explicit list"]

    for index, repo in enumerate(repos):
        prefix = f"repos[{index}]"
        if not isinstance(repo, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in ("name", "path", "upstream"):
            if not isinstance(repo.get(key), str) or not repo[key].strip():
                errors.append(f"{prefix}.{key} must be a non-empty string")
        path_value = str(repo.get("path", ""))
        if "*" in path_value or "?" in path_value:
            errors.append(f"{prefix}.path must not contain glob patterns")
    return errors


def run_preflight(config_path: Path, hermes_home: Path, venv_path: Path) -> tuple[dict[str, Any], list[str]]:
    config = _load_json(config_path)
    errors: list[str] = []

    if config.get("mode") != EXPECTED_MODE:
        errors.append(f"mode must be {EXPECTED_MODE}")
    if config.get("claim_ceiling") != "observation_only_not_authority":
        errors.append("claim_ceiling must be observation_only_not_authority")

    script = config.get("script")
    if not isinstance(script, dict):
        errors.append("script must be an object")
        script = {}

    script_filename = script.get("filename")
    script_pin = script.get("sha256")
    if not isinstance(script_filename, str) or not script_filename:
        errors.append("script.filename must be a non-empty string")
        script_filename = "multi_repo_status.py"
    if not isinstance(script_pin, str) or len(script_pin) != 64:
        errors.append("script.sha256 must be a 64-character sha256 hex string")
        script_pin = ""
    script_pin = str(script_pin).lower()

    repo_script = (PACKAGE_DIR / script_filename).resolve()
    deployed_script = (hermes_home / "scripts" / script_filename).resolve()
    deployed_config = (hermes_home / "scripts" / config_path.name).resolve()

    repo_script_sha = None
    deployed_script_sha = None
    repo_config_sha = None
    deployed_config_sha = None
    if not repo_script.exists():
        errors.append(f"repo script missing: {repo_script}")
    else:
        repo_script_sha = _sha256(repo_script)
        if repo_script_sha != script_pin:
            errors.append("repo script sha256 does not match config pin")

    if not deployed_script.exists():
        errors.append(f"deployed script missing: {deployed_script}")
    else:
        deployed_script_sha = _sha256(deployed_script)
        if deployed_script_sha != script_pin:
            errors.append("deployed script sha256 does not match config pin")

    if not config_path.exists():
        errors.append(f"repo config missing: {config_path}")
    else:
        repo_config_sha = _sha256(config_path)

    if not deployed_config.exists():
        errors.append(f"deployed config missing: {deployed_config}")
    else:
        deployed_config_sha = _sha256(deployed_config)
        if repo_config_sha is not None and deployed_config_sha != repo_config_sha:
            errors.append("deployed config sha256 does not match repo config")

    if not hermes_home.exists():
        errors.append(f"HERMES_HOME path does not exist: {hermes_home}")
    if not (hermes_home / "scripts").exists():
        errors.append(f"HERMES_HOME scripts dir does not exist: {hermes_home / 'scripts'}")

    python_exe = venv_path / "Scripts" / "python.exe"
    if not python_exe.exists():
        errors.append(f"isolated venv python missing: {python_exe}")

    errors.extend(_check_explicit_repo_list(config))

    report = {
        "ok": not errors,
        "config_path": str(config_path),
        "mode": config.get("mode"),
        "claim_ceiling": config.get("claim_ceiling"),
        "script_filename": script_filename,
        "script_pin": script_pin,
        "repo_script": str(repo_script),
        "repo_script_sha256": repo_script_sha,
        "repo_config": str(config_path),
        "repo_config_sha256": repo_config_sha,
        "deployed_script": str(deployed_script),
        "deployed_script_sha256": deployed_script_sha,
        "deployed_config": str(deployed_config),
        "deployed_config_sha256": deployed_config_sha,
        "hermes_home": str(hermes_home),
        "venv_path": str(venv_path),
        "venv_python": str(python_exe),
        "repo_count": len(config.get("repos", [])) if isinstance(config.get("repos"), list) else 0,
        "errors": errors,
        "claim_ceiling_not_supported": [
            "does not run Hermes cron tick",
            "does not install an OS scheduled task",
            "does not perform retention deletion",
            "does not call provider or LLM paths",
            "does not enforce runtime sandboxing",
        ],
    }
    return report, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to reviewed checklist config JSON.")
    parser.add_argument("--hermes-home", required=True, help="Expected isolated HERMES_HOME path.")
    parser.add_argument("--venv", required=True, help="Expected isolated Python virtual environment path.")
    args = parser.parse_args()

    report, errors = run_preflight(
        config_path=_as_path(args.config),
        hermes_home=_as_path(args.hermes_home),
        venv_path=_as_path(args.venv),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
