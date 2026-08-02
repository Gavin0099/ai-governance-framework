"""Command line entry point for the single-session calibration probe.

The probe orchestrator takes an injected runner and never starts a session
itself, which is what makes it testable without credentials. This module is the
one place that supplies a real runner, so everything that touches credentials
stays in one reviewable seam.

What this does not do, deliberately:

* It does not admit anything, score anything, or build a packet.
* It does not run a pair. It calls the calibration runner, which refuses any
  authorization other than the calibration one and invokes exactly one session.
* It does not authorize itself. ``--authorization`` must carry the calibration
  authorization string, and both this module and the runner check it.

Usage:
    python gate3_codex_calibration_cli.py \\
        --authorization non_counted_codex_calibration_probe_only \\
        --run-id <id> --out <receipt path> --prompt <file> \\
        --model ... --cli-version ... --comp-hash ... --effort ...
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_calibration as calibration  # noqa: E402
import gate3_codex_calibration_probe as probe  # noqa: E402
import gate3_codex_live_canary as live  # noqa: E402

CALIBRATION_RUNNER = HERE / "gate3_codex_calibration_runner.ps1"
ROUTE_PLAN_SCHEMA = "gate3-codex-calibration-route-plan.v1"


def _route_plan(path: Path) -> None:
    """Pin every executable the runner will load, including the shared file."""
    path.write_bytes(
        live._json_bytes(
            {
                "authorization": calibration.AUTHORIZATION,
                "frozen_route": {
                    "calibration_runner_implementation_sha256": (
                        live._sha256_file(CALIBRATION_RUNNER)
                    ),
                    "credential_common_implementation_sha256": (
                        live._sha256_file(live.DEFAULT_CREDENTIAL_COMMON)
                    ),
                    "launcher_implementation_sha256": live._sha256_file(
                        live.DEFAULT_SESSION_LAUNCHER
                    ),
                },
                "schema": ROUTE_PLAN_SCHEMA,
            }
        )
    )


def _live_runner(prompt_path: Path, codex_command: str) -> probe.Runner:
    """Build a runner that invokes exactly one real calibration session.

    The private tree lives under the user Temp root the runner confines to,
    and is removed whether or not the session succeeded. The rollout is read
    out before removal; nothing else survives the call.
    """

    def run() -> probe.RunnerResult:
        private_root = Path(
            tempfile.mkdtemp(prefix="gate3-calibration-private-")
        ).resolve()
        try:
            workspace = private_root / "workspace"
            workspace.mkdir()
            live._git(workspace, "init", "-q")
            codex_home = private_root / "codex-home"
            codex_home.mkdir()
            private = private_root / "private"
            private.mkdir()
            prompt = private_root / "prompt.txt"
            prompt.write_bytes(prompt_path.read_bytes())
            plan = private_root / "route-plan.json"
            _route_plan(plan)
            receipt = private / "calibration-runner-receipt.json"
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(CALIBRATION_RUNNER),
                    "-Authorization",
                    calibration.AUTHORIZATION,
                    "-CodexCommand",
                    codex_command,
                    "-RoutePlanPath",
                    str(plan),
                    "-Workspace",
                    str(workspace),
                    "-PromptPath",
                    str(prompt),
                    "-CodexHome",
                    str(codex_home),
                    "-StdoutPath",
                    str(private / "session.stdout"),
                    "-StderrPath",
                    str(private / "session.stderr"),
                    "-ExitCodePath",
                    str(private / "session.exit"),
                    "-PrivateReceiptPath",
                    str(receipt),
                ],
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise probe.ProbeError("calibration runner failed closed")
            observed = json.loads(receipt.read_text(encoding="utf-8"))
            if (
                observed.get("session_invocations") != 1
                or observed.get("replacement_sessions") != 0
                or observed.get("authorization") != calibration.AUTHORIZATION
            ):
                raise probe.ProbeError("calibration runner receipt is invalid")
            rollout = live._single_rollout(codex_home)
            return probe.RunnerResult(rollout.read_bytes(), 0)
        finally:
            shutil.rmtree(private_root, ignore_errors=True)

    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--workspace-token", default=live.GENERIC_CONTEXT_TOKEN)
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--model", default=live.DEFAULT_MODEL)
    parser.add_argument("--cli-version", default=live.DEFAULT_CLI_VERSION)
    parser.add_argument("--comp-hash", default=live.DEFAULT_COMP_HASH)
    parser.add_argument("--effort", default=live.DEFAULT_REASONING)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    result: dict[str, object]
    try:
        if args.authorization != calibration.AUTHORIZATION:
            raise probe.ProbeError("calibration authorization is invalid")
        published = probe.orchestrate(
            args.out,
            run_id=args.run_id,
            authorization=args.authorization,
            expected_workspace=args.workspace_token,
            expected_prompt=args.prompt.read_bytes(),
            signed_identity={
                "cli_version": args.cli_version,
                "comp_hash": args.comp_hash,
                "effort": args.effort,
                "model": args.model,
            },
            private_parent=Path(tempfile.gettempdir()),
            runner=_live_runner(args.prompt, args.codex_command),
        )
        result = {
            "public_receipt": str(published.public_receipt),
            "status": "PASS",
        }
    except (probe.ProbeError, live.CanaryError, OSError, ValueError) as exc:
        result = {"error": str(exc), "status": "FAIL"}
        if args.json_out is not None:
            args.json_out.write_text(
                json.dumps(result, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(str(exc), file=sys.stderr)
        return 2
    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(result, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
