#!/usr/bin/env python3
"""Write-bounded deploy helper for the Hermes no_agent checklist script.

This helper copies the reviewed checklist script into an explicitly selected
HERMES_HOME/scripts directory after verifying that the repository source still
matches the reviewed config pin. It does not run Hermes, does not run cron tick,
does not install a scheduler, and does not delete retained artifacts.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from check_preflight import DEFAULT_CONFIG, EXPECTED_MODE, _load_json, _sha256, run_preflight


PACKAGE_DIR = Path(__file__).resolve().parent


def _as_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _script_from_config(config: dict[str, Any]) -> tuple[str, str]:
    if config.get("mode") != EXPECTED_MODE:
        raise ValueError(f"config mode must be {EXPECTED_MODE}")
    if config.get("claim_ceiling") != "observation_only_not_authority":
        raise ValueError("claim_ceiling must be observation_only_not_authority")

    script = config.get("script")
    if not isinstance(script, dict):
        raise ValueError("script must be an object")

    filename = script.get("filename")
    pin = script.get("sha256")
    if not isinstance(filename, str) or not filename or "/" in filename or "\\" in filename:
        raise ValueError("script.filename must be a simple non-empty filename")
    if not isinstance(pin, str) or len(pin) != 64:
        raise ValueError("script.sha256 must be a 64-character sha256 hex string")
    return filename, pin.lower()


def deploy(config_path: Path, hermes_home: Path, venv_path: Path) -> tuple[dict[str, Any], int]:
    config = _load_json(config_path)
    filename, pin = _script_from_config(config)

    repo_script = (PACKAGE_DIR / filename).resolve()
    if not repo_script.exists():
        raise FileNotFoundError(f"repo script missing: {repo_script}")

    repo_sha = _sha256(repo_script)
    if repo_sha != pin:
        report = {
            "ok": False,
            "phase": "pre_copy_repo_pin_check",
            "error": "repo script sha256 does not match config pin; refusing deploy",
            "repo_script": str(repo_script),
            "repo_script_sha256": repo_sha,
            "script_pin": pin,
            "claim_ceiling_not_supported": [
                "does not run Hermes cron tick",
                "does not install an OS scheduled task",
                "does not perform retention deletion",
                "does not call provider or LLM paths",
                "does not enforce runtime sandboxing",
            ],
        }
        return report, 1

    scripts_dir = (hermes_home / "scripts").resolve()
    deployed_script = (scripts_dir / filename).resolve()
    deployed_config = (scripts_dir / config_path.name).resolve()
    expected_parent = hermes_home.resolve()
    if expected_parent not in deployed_script.parents:
        raise ValueError("resolved deploy target escaped HERMES_HOME")
    if expected_parent not in deployed_config.parents:
        raise ValueError("resolved config deploy target escaped HERMES_HOME")

    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo_script, deployed_script)
    shutil.copyfile(config_path, deployed_config)

    preflight_report, errors = run_preflight(config_path=config_path, hermes_home=hermes_home, venv_path=venv_path)
    report = {
        "ok": not errors,
        "phase": "post_copy_preflight",
        "pre_copy_repo_script_sha256": repo_sha,
        "script_pin": pin,
        "deployed_script": str(deployed_script),
        "deployed_config": str(deployed_config),
        "write_scope": str(scripts_dir),
        "preflight": preflight_report,
        "errors": errors,
        "claim_ceiling_not_supported": [
            "does not run Hermes cron tick",
            "does not install an OS scheduled task",
            "does not perform retention deletion",
            "does not call provider or LLM paths",
            "does not enforce runtime sandboxing",
        ],
    }
    return report, 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to reviewed checklist config JSON.")
    parser.add_argument("--hermes-home", required=True, help="Explicit deploy target HERMES_HOME path.")
    parser.add_argument("--venv", required=True, help="Expected isolated Python virtual environment path for post-copy preflight.")
    args = parser.parse_args()

    report, code = deploy(
        config_path=_as_path(args.config),
        hermes_home=_as_path(args.hermes_home),
        venv_path=_as_path(args.venv),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
