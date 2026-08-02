"""Tests for the calibration probe CLI.

The CLI is the one seam that supplies a real runner, so what matters is that it
cannot be pointed at anything else: a pair authorization must not reach the
orchestrator, and the route plan it writes must pin every executable the runner
will load.

No test here starts a session. The runner is replaced wherever a session would
otherwise happen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_calibration as calibration  # noqa: E402
import gate3_codex_calibration_cli as cli  # noqa: E402
import gate3_codex_calibration_probe as probe  # noqa: E402
import gate3_codex_live_canary as live  # noqa: E402

PAIR_AUTHORIZATION = "non_counted_codex_live_canary_only"


def _prompt(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.txt"
    path.write_bytes(b"calibration prompt\n")
    return path


def test_a_pair_authorization_never_reaches_the_orchestrator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("orchestrate must not be reached")

    monkeypatch.setattr(probe, "orchestrate", explode)
    report = tmp_path / "report.json"
    code = cli.main(
        [
            "--authorization", PAIR_AUTHORIZATION,
            "--run-id", "calibration-test",
            "--out", str(tmp_path / "receipt.json"),
            "--prompt", str(_prompt(tmp_path)),
            "--json-out", str(report),
        ]
    )
    assert code == 2
    parsed = json.loads(report.read_text(encoding="utf-8"))
    assert parsed["status"] == "FAIL"
    assert "authorization is invalid" in parsed["error"]
    assert not (tmp_path / "receipt.json").exists()


def test_the_cli_passes_the_calibration_authorization_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def capture(success_path: Path, **kwargs: object):
        seen.update(kwargs)
        seen["success_path"] = success_path
        return probe.ProbeResult(tmp_path / "private.json", tmp_path / "pub.json")

    monkeypatch.setattr(probe, "orchestrate", capture)
    code = cli.main(
        [
            "--authorization", calibration.AUTHORIZATION,
            "--run-id", "calibration-test",
            "--out", str(tmp_path / "receipt.json"),
            "--prompt", str(_prompt(tmp_path)),
        ]
    )
    assert code == 0
    assert seen["authorization"] == calibration.AUTHORIZATION
    assert seen["expected_prompt"] == b"calibration prompt\n"
    assert set(seen["signed_identity"]) == {
        "cli_version",
        "comp_hash",
        "effort",
        "model",
    }
    assert callable(seen["runner"])


def test_the_route_plan_pins_every_executable(tmp_path: Path) -> None:
    """Including the shared credential file the runner dot-sources."""
    plan_path = tmp_path / "route-plan.json"
    cli._route_plan(plan_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["schema"] == cli.ROUTE_PLAN_SCHEMA
    assert plan["authorization"] == calibration.AUTHORIZATION
    frozen = plan["frozen_route"]
    assert set(frozen) == {
        "calibration_runner_implementation_sha256",
        "credential_common_implementation_sha256",
        "launcher_implementation_sha256",
    }
    assert frozen["calibration_runner_implementation_sha256"] == (
        live._sha256_file(cli.CALIBRATION_RUNNER)
    )
    assert frozen["credential_common_implementation_sha256"] == (
        live._sha256_file(live.DEFAULT_CREDENTIAL_COMMON)
    )
    assert frozen["launcher_implementation_sha256"] == (
        live._sha256_file(live.DEFAULT_SESSION_LAUNCHER)
    )


def test_a_runner_receipt_claiming_two_sessions_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI re-checks the count rather than trusting the runner's exit."""
    receipt = {
        "authorization": calibration.AUTHORIZATION,
        "replacement_sessions": 0,
        "session_invocations": 2,
    }

    class _Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    real_run = cli.subprocess.run

    def fake_run(args, *rest, **kwargs):
        # Intercept only the calibration runner. Everything else, including the
        # workspace git init, must still really happen.
        text = [str(item) for item in args]
        if not any(cli.CALIBRATION_RUNNER.name in item for item in text):
            return real_run(args, *rest, **kwargs)
        for index, item in enumerate(text):
            if item == "-PrivateReceiptPath":
                target = Path(text[index + 1])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(receipt), encoding="utf-8")
        return _Completed()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    runner = cli._live_runner(_prompt(tmp_path), "codex")
    with pytest.raises(probe.ProbeError, match="receipt is invalid"):
        runner()


def test_the_cli_starts_no_session_of_its_own() -> None:
    """Session invocation belongs to the runner script, not to this module."""
    code = chr(10).join(
        line
        for line in Path(cli.__file__).read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "gate3_codex_pair_runner" not in code
    assert str(cli.CALIBRATION_RUNNER.name) in code
